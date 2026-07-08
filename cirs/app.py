import os
import re
from datetime import timedelta
from functools import wraps

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "cirs-mini-project-fixed-secret-key"
app.permanent_session_lifetime = timedelta(hours=3)
csrf = CSRFProtect(app)

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required. "
        "Set it to your PostgreSQL connection string, e.g.: "
        "postgresql://user:password@host:port/dbname"
    )


# ─── Database layer (PostgreSQL only) ──────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(DATABASE_URL)
    return g.db


def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def db_execute(db, sql, params=None):
    """Execute a query, converting ? placeholders to %s for psycopg2."""
    pg_sql = sql.replace('?', '%s')
    pg_sql = pg_sql.replace('INSERT OR IGNORE INTO', 'INSERT INTO')

    cur = db.cursor(cursor_factory=RealDictCursor)
    if params:
        cur.execute(pg_sql, params)
    else:
        cur.execute(pg_sql)

    # Map .lastrowid for code that uses RETURNING id
    if pg_sql.strip().upper().startswith("INSERT") and "RETURNING" in pg_sql.upper():
        row = cur.fetchone()
        cur._lastrowid = row['id'] if row else None
    else:
        cur._lastrowid = None
    return cur


app.teardown_appcontext(close_db)


def init_db():
    db = get_db()
    statements = [
        """CREATE TABLE IF NOT EXISTS users (
            id          SERIAL PRIMARY KEY,
            name        TEXT    NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'user',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS complaints (
            id          SERIAL PRIMARY KEY,
            title       TEXT    NOT NULL,
            description TEXT    NOT NULL,
            category    TEXT    NOT NULL,
            location    TEXT    NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'Pending',
            priority    TEXT    NOT NULL DEFAULT 'Low',
            resolution_notes TEXT DEFAULT '',
            created_by  INTEGER NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )""",
        """CREATE TABLE IF NOT EXISTS complaint_users (
            id            SERIAL PRIMARY KEY,
            complaint_id  INTEGER NOT NULL,
            user_id       INTEGER NOT NULL,
            role_in_complaint TEXT NOT NULL DEFAULT 'joined',
            joined_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(complaint_id, user_id)
        )""",
        """CREATE TABLE IF NOT EXISTS complaint_history (
            id            SERIAL PRIMARY KEY,
            complaint_id  INTEGER NOT NULL,
            user_id       INTEGER NOT NULL,
            action        TEXT    NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )""",
        """CREATE TABLE IF NOT EXISTS complaint_dependencies (
            id                      SERIAL PRIMARY KEY,
            complaint_id            INTEGER NOT NULL,
            depends_on_complaint_id INTEGER NOT NULL,
            reason                  TEXT    NOT NULL,
            status                  TEXT    NOT NULL DEFAULT 'suggested',
            confidence              TEXT    NOT NULL DEFAULT 'Medium',
            created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id),
            FOREIGN KEY (depends_on_complaint_id) REFERENCES complaints(id)
        )""",
    ]
    for sql in statements:
        db_execute(db, sql)

    # Migration: add resolution_notes column if missing
    try:
        db_execute(db, "ALTER TABLE complaints ADD COLUMN resolution_notes TEXT DEFAULT ''")
    except Exception:
        pass

    # Migration: add confidence column to complaint_dependencies
    try:
        db_execute(db, "ALTER TABLE complaint_dependencies ADD COLUMN confidence TEXT DEFAULT 'Medium'")
    except Exception:
        pass

    db.commit()


# ─── Seed demo data ─────────────────────────────────────────────────────────────

def seed_demo_data():
    db = get_db()
    existing = db_execute(db, "SELECT COUNT(*) AS cnt FROM users").fetchone()['cnt']
    if existing > 0:
        return

    def _insert(sql, params):
        """Insert a row and return the generated ID."""
        cur = db_execute(db, sql + " RETURNING id", params)
        return getattr(cur, '_lastrowid', None) or cur.fetchone()[0]

    # ── Create 4 users ────────────────────────────────────────────────────
    s1 = _insert("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                  ('Student One', 'student1@cirs.com', generate_password_hash('student123'), 'user'))
    s2 = _insert("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                  ('Student Two', 'student2@cirs.com', generate_password_hash('student123'), 'user'))
    s3 = _insert("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                  ('Student Three', 'student3@cirs.com', generate_password_hash('student123'), 'user'))
    a1 = _insert("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                  ('Admin User', 'admin@cirs.com', generate_password_hash('admin123'), 'admin'))
    db.commit()

    # ── Create 6 complaints ───────────────────────────────────────────────

    def _make_complaint(title, desc, cat, loc, status, priority, creator_id, creator_name):
        cid = _insert(
            "INSERT INTO complaints (title, description, category, location, status, priority, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, desc, cat, loc, status, priority, creator_id))
        db_execute(db,
            "INSERT INTO complaint_users (complaint_id, user_id, role_in_complaint) VALUES (?, ?, 'creator')",
            (cid, creator_id))
        db_execute(db,
            "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
            (cid, creator_id, f'{creator_name} created complaint'))
        return cid

    def _join(complaint_id, user_id, user_name):
        db_execute(db,
            "INSERT INTO complaint_users (complaint_id, user_id, role_in_complaint) VALUES (?, ?, 'joined') "
            "ON CONFLICT DO NOTHING",
            (complaint_id, user_id))
        db_execute(db,
            "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
            (complaint_id, user_id, f'{user_name} joined complaint'))

    def _set_status(complaint_id, new_status, admin_name, notes=''):
        if notes:
            db_execute(db,
                "UPDATE complaints SET status = ?, resolution_notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_status, notes, complaint_id))
        else:
            db_execute(db,
                "UPDATE complaints SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_status, complaint_id))
        action = f'{admin_name} changed status to {new_status}'
        if new_status == 'Resolved' and notes:
            action = f'{admin_name} resolved issue: {notes}'
        db_execute(db,
            "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
            (complaint_id, a1, action))

    def _set_priority(cid, affected_count):
        pri = 'High' if affected_count >= 6 else 'Medium' if affected_count >= 3 else 'Low'
        db_execute(db,
            "UPDATE complaints SET priority = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (pri, cid))

    # ── C1: Wi-Fi not working (Student One) ────────────────────────────────
    c1 = _make_complaint(
        'Wi-Fi not working in Hostel Block A',
        'The Wi-Fi network has been down since yesterday. Students are unable to access the internet for online classes.',
        'Wi-Fi', 'Hostel Block A', 'In Progress', 'Medium', s1, 'Student One')
    _join(c1, s2, 'Student Two')
    _join(c1, s3, 'Student Three')
    _set_status(c1, 'In Progress', 'Admin User')
    _set_priority(c1, 3)
    db.commit()

    # ── C2: Electricity issue (Student One) ────────────────────────────────
    c2 = _make_complaint(
        'Electricity issue in Hostel Block A',
        'Power supply is unavailable in Hostel Block A. Lights and fans are not working.',
        'Electricity', 'Hostel Block A', 'Pending', 'Low', s1, 'Student One')
    db.commit()

    # ── C3: Water motor not working (Student Two) ──────────────────────────
    c3 = _make_complaint(
        'Water motor not working',
        'Motor is not running and water is not coming to the overhead tank.',
        'Water', 'Hostel Block A', 'Pending', 'Low', s2, 'Student Two')
    db.commit()

    # ── C4: Leaking tap (Student Three) ────────────────────────────────────
    c4 = _make_complaint(
        'Leaking tap in Boys Washroom',
        'The tap in the ground floor boys washroom is continuously leaking. Water is being wasted.',
        'Water', 'Academic Block', 'In Progress', 'Low', s3, 'Student Three')
    _join(c4, s1, 'Student One')
    _set_status(c4, 'In Progress', 'Admin User')
    _set_priority(c4, 2)
    db.commit()

    # ── C5: Projector bulb fuse (Student Two) — RESOLVED ───────────────────
    c5 = _make_complaint(
        'Projector bulb fuse in Room 201',
        'The projector bulb in classroom 201 has fused. Unable to conduct presentations.',
        'Classroom', 'Room 201', 'Resolved', 'Low', s2, 'Student Two')
    _set_status(c5, 'Resolved', 'Admin User', 'Replaced the projector bulb. Working normally now.')
    db.commit()

    # ── C6: Slow internet in Computer Lab (Student Three) ──────────────────
    c6 = _make_complaint(
        'Slow internet in Computer Lab',
        'The internet speed in the computer lab is extremely slow. Unable to load websites and access lab resources.',
        'Wi-Fi', 'Computer Lab', 'Pending', 'Medium', s3, 'Student Three')
    _join(c6, s1, 'Student One')
    _join(c6, s2, 'Student Two')
    _join(c6, a1, 'Admin User')  # Admin also joined to show they're affected
    _set_priority(c6, 4)
    db.commit()

    # ── Dependencies ───────────────────────────────────────────────────────

    # Dep 1: C3 (Water motor) → C2 (Electricity) — SUGGESTED
    # Water motor depends on electricity: motor keyword, same location (Hostel Block A)
    db_execute(db,
        "INSERT INTO complaint_dependencies (complaint_id, depends_on_complaint_id, reason, status, confidence) "
        "VALUES (?, ?, ?, 'suggested', ?)",
        (c3, c2, 'This issue may require electricity. Equipment needs power supply.', 'High'))

    # Dep 2: C1 (Wi-Fi not working) → C2 (Electricity) — CONFIRMED
    # Wi-Fi router needs power
    db_execute(db,
        "INSERT INTO complaint_dependencies (complaint_id, depends_on_complaint_id, reason, status, confidence) "
        "VALUES (?, ?, ?, 'confirmed', ?)",
        (c1, c2, 'Router or network equipment may require electricity.', 'High'))
    db_execute(db,
        "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
        (c1, a1, 'Admin User confirmed dependency with Electricity issue in Hostel Block A'))

    db.commit()


# ─── Similarity logic ───────────────────────────────────────────────────────────

def tokenize(text):
    return set(re.findall(r'[a-zA-Z0-9]+', text.lower()))


def compute_similarity(title1, desc1, title2, desc2):
    words1 = tokenize(title1 + ' ' + desc1)
    words2 = tokenize(title2 + ' ' + desc2)
    if not words1 or not words2:
        return 0.0
    common = words1 & words2
    total = words1 | words2
    return len(common) / len(total)


def find_similar_complaints(title, description, category, location):
    db = get_db()
    rows = db_execute(db,
        "SELECT * FROM complaints WHERE status != 'Resolved'"
    ).fetchall()

    similar = []
    for row in rows:
        cat_match = row['category'].lower() == category.lower()
        loc_match = row['location'].lower() == location.lower()
        sim = compute_similarity(title, description, row['title'], row['description'])

        if cat_match and loc_match:
            sim = max(sim, 0.5)
        elif cat_match or loc_match:
            sim = max(sim, 0.3)

        if sim >= 0.4:
            count = db_execute(db,
                "SELECT COUNT(*) AS cnt FROM complaint_users WHERE complaint_id = ?",
                (row['id'],)
            ).fetchone()['cnt']
            similar.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'category': row['category'],
                'location': row['location'],
                'status': row['status'],
                'priority': row['priority'],
                'affected_users': count,
                'similarity': round(sim * 100, 0)
            })

    similar.sort(key=lambda x: x['similarity'], reverse=True)
    return similar


def calculate_priority(affected_count):
    if affected_count >= 6:
        return 'High'
    elif affected_count >= 3:
        return 'Medium'
    else:
        return 'Low'


def get_expected_resolution_time(category, priority):
    """Return expected resolution time text based on category and priority."""
    mapping = {
        'Electricity': {'High': '1 hour', 'Medium': '3 hours', 'Low': '6 hours'},
        'Water': {'High': '2 hours', 'Medium': '4 hours', 'Low': '8 hours'},
        'Wi-Fi': {'High': '3 hours', 'Medium': '6 hours', 'Low': '12 hours'},
        'Cleanliness': {'High': '6 hours', 'Medium': '12 hours', 'Low': '24 hours'},
        'Classroom': {'High': '2 hours', 'Medium': '6 hours', 'Low': '12 hours'},
        'Hostel': {'High': '4 hours', 'Medium': '8 hours', 'Low': '24 hours'},
        'Other': {'High': '6 hours', 'Medium': '12 hours', 'Low': '24 hours'},
    }
    return mapping.get(category, {}).get(priority, 'N/A')


def update_priority(complaint_id):
    db = get_db()
    count = db_execute(db,
        "SELECT COUNT(*) AS cnt FROM complaint_users WHERE complaint_id = ?",
        (complaint_id,)
    ).fetchone()['cnt']
    new_priority = calculate_priority(count)
    db_execute(db,
        "UPDATE complaints SET priority = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_priority, complaint_id)
    )
    db.commit()


# ─── Dependency Suggestion Logic ───────────────────────────────────────────────

def check_single_dependency(child_complaint, parent_complaint):
    """
    Cause-based keyword check: does child_complaint depend on parent_complaint?
    Uses Category + Cause Keywords rules.
    Location is used as a confidence booster, not a mandatory rule.
    Returns (reason, confidence) or None.
    """
    child_text = (child_complaint['title'] + ' ' + child_complaint['description']).lower()
    parent_category = parent_complaint['category'].lower()
    child_category = child_complaint['category'].lower()

    # Location match check (first word of location) — used as confidence modifier
    child_loc_first = child_complaint['location'].lower().split()[0] if child_complaint['location'] else ''
    parent_loc_first = parent_complaint['location'].lower().split()[0] if parent_complaint['location'] else ''
    location_matches = bool(child_loc_first) and bool(parent_loc_first) and child_loc_first == parent_loc_first

    # Helper: adjust confidence based on location match
    def adjust_confidence(base_conf):
        """Same location keeps base confidence; different location caps at Medium."""
        if location_matches:
            return base_conf
        return 'Medium' if base_conf == 'High' else base_conf

    # ── PARENT: Electricity ────────────────────────────────────────────
    if parent_category == 'electricity':
        # Water with leak/pipe/tap keywords → independent plumbing (NO dependency)
        if child_category == 'water':
            plumbing_kw = ['leak', 'leakage', 'pipe', 'pipeline', 'tap broken', 'valve', 'blockage']
            if any(kw in child_text for kw in plumbing_kw):
                return None  # Independent plumbing issue
            if 'tank has water' in child_text or 'water stored' in child_text:
                return None  # Not electricity-related

        # High confidence: motor/pump/router/projector/lab computer
        high_kw = ['motor', 'pump', 'router', 'projector', 'lab computer', 'computer lab']
        if any(kw in child_text for kw in high_kw):
            return ('This issue may require electricity. Equipment needs power supply.', adjust_confidence('High'))

        # Wi-Fi power-related keywords
        if child_category == 'wi-fi':
            wifi_power_kw = ['router off', 'no power', 'router not working', 'wifi not working']
            if any(kw in child_text for kw in wifi_power_kw):
                return ('Router or network equipment may require electricity.', adjust_confidence('High'))
            # Wi-Fi independent keywords → no dependency
            wifi_independent_kw = ['slow internet', 'password issue', 'login issue', 'slow', 'password']
            if any(kw in child_text for kw in wifi_independent_kw):
                return None

        # Medium confidence: general dependency hints
        medium_kw = [
            'water not coming', 'tank empty', 'overhead tank', 'bore motor', 'refill',
            'no supply', 'no power'
        ]
        if any(kw in child_text for kw in medium_kw):
            return ('This issue may depend on electricity supply. Admin should verify.', 'Medium')

    # ── PARENT: Water ──────────────────────────────────────────────────
    elif parent_category == 'water':
        water_kw = ['cleaning', 'washroom', 'bathroom', 'toilet', 'hygiene', 'flushing']
        if any(kw in child_text for kw in water_kw):
            return ('This issue may depend on water availability.', 'Medium')

    # ── PARENT: Wi-Fi ──────────────────────────────────────────────────
    elif parent_category == 'wi-fi':
        wifi_kw = ['online class', 'lab internet', 'internet', 'network', 'online']
        if any(kw in child_text for kw in wifi_kw):
            return ('This issue may depend on Wi-Fi or network connectivity.', 'Medium')

    return None


def find_dependency_suggestions(complaint_id):
    """
    After a complaint is created, find possible dependencies in BOTH directions:
      1. New complaint depends on existing complaint (child → parent)
      2. Existing complaint depends on new complaint (parent ← child)
    Uses cause-based keyword rules with confidence levels.
    """
    db = get_db()

    new_complaint = db_execute(db, "SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if not new_complaint:
        return

    # Find all unresolved complaints (excluding self)
    existing = db_execute(db,
        "SELECT * FROM complaints WHERE id != ? AND status != 'Resolved'",
        (complaint_id,)
    ).fetchall()

    # Collect already-linked pairs to avoid duplicates
    linked_rows = db_execute(db,
        "SELECT complaint_id, depends_on_complaint_id FROM complaint_dependencies WHERE complaint_id = ? OR depends_on_complaint_id = ?",
        (complaint_id, complaint_id)
    ).fetchall()
    already_linked = set()
    for row in linked_rows:
        already_linked.add((row['complaint_id'], row['depends_on_complaint_id']))

    suggestions = []

    for existing_c in existing:
        # Direction 1: New complaint depends on existing complaint
        if (complaint_id, existing_c['id']) not in already_linked:
            result = check_single_dependency(new_complaint, existing_c)
            if result:
                reason, confidence = result
                suggestions.append((complaint_id, existing_c['id'], reason, confidence))
                already_linked.add((complaint_id, existing_c['id']))

        # Direction 2: Existing complaint depends on new complaint
        # Skip if we already suggested the reverse direction (circular prevention)
        if (existing_c['id'], complaint_id) not in already_linked and (complaint_id, existing_c['id']) not in already_linked:
            result = check_single_dependency(existing_c, new_complaint)
            if result:
                reason, confidence = result
                suggestions.append((existing_c['id'], complaint_id, reason, confidence))
                already_linked.add((existing_c['id'], complaint_id))

    for c_id, parent_id, reason, confidence in suggestions:
        try:
            db_execute(db,
                "INSERT INTO complaint_dependencies (complaint_id, depends_on_complaint_id, reason, status, confidence) "
                "VALUES (?, ?, ?, 'suggested', ?)",
                (c_id, parent_id, reason, confidence)
            )
        except Exception:
            pass

    if suggestions:
        db.commit()


# ─── Jinja2 filters ──────────────────────────────────────────────────────────────

def format_datetime(value, fmt='%d %b %Y, %I:%M %p'):
    """Format a datetime value for display."""
    if value is None:
        return '-'
    return value.strftime(fmt)


def format_time(value, fmt='%I:%M %p'):
    """Format a time-only datetime value. Handles both datetime objects and strings."""
    return format_datetime(value, fmt)


app.jinja_env.filters['format_datetime'] = format_datetime
app.jinja_env.filters['format_time'] = format_time

# ─── Make helpers available in templates ────────────────────────────────────────

app.jinja_env.globals.update(get_expected_resolution_time=get_expected_resolution_time)


# ─── Auth helpers ───────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ─── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']

        if not name or not email or not password:
            flash('Please enter all required fields.', 'danger')
            return render_template('register.html')

        db = get_db()
        existing = db_execute(db, "SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('login'))

        hashed = generate_password_hash(password)
        db_execute(db,
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, hashed, 'user')
        )
        db.commit()
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        db = get_db()
        user = db_execute(db, "SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session.permanent = True
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ─── User routes ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def user_dashboard():
    # Redirect admin to their dashboard
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    db = get_db()
    user_id = session['user_id']

    # Complaints Raised by Me (where user is creator)
    my_complaints = db_execute(db,
        "SELECT c.*, cu.joined_at AS created_on, "
        "(SELECT COUNT(*) FROM complaint_users cu2 WHERE cu2.complaint_id = c.id) AS affected_users "
        "FROM complaints c JOIN complaint_users cu ON c.id = cu.complaint_id AND cu.user_id = ? AND cu.role_in_complaint = 'creator' "
        "ORDER BY c.created_at DESC",
        (user_id,)
    ).fetchall()

    # Complaints I Joined (where user is joined)
    joined = db_execute(db,
        "SELECT c.*, cu.joined_at AS joined_on, "
        "(SELECT COUNT(*) FROM complaint_users cu2 WHERE cu2.complaint_id = c.id) AS affected_users "
        "FROM complaints c JOIN complaint_users cu ON c.id = cu.complaint_id "
        "WHERE cu.user_id = ? AND cu.role_in_complaint = 'joined' ORDER BY cu.joined_at DESC",
        (user_id,)
    ).fetchall()

    # Open complaints: unresolved, user hasn't created or joined
    open_complaints = db_execute(db,
        "SELECT c.*, u.name AS creator_name, "
        "(SELECT COUNT(*) FROM complaint_users cu WHERE cu.complaint_id = c.id) AS affected_users "
        "FROM complaints c JOIN users u ON c.created_by = u.id "
        "WHERE c.status != 'Resolved' "
        "AND c.id NOT IN (SELECT complaint_id FROM complaint_users WHERE user_id = ?) "
        "ORDER BY c.created_at DESC",
        (user_id,)
    ).fetchall()

    # Get confirmed dependencies for all complaint IDs visible to user
    all_complaint_ids = set()
    for c in my_complaints:
        all_complaint_ids.add(c['id'])
    for c in joined:
        all_complaint_ids.add(c['id'])
    for c in open_complaints:
        all_complaint_ids.add(c['id'])

    confirmed_deps = {}
    if all_complaint_ids:
        placeholders = ','.join('?' * len(all_complaint_ids))
        dep_rows = db_execute(db,
            f"SELECT cd.*, c1.title AS complaint_title, c2.title AS parent_title "
            f"FROM complaint_dependencies cd "
            f"JOIN complaints c1 ON cd.complaint_id = c1.id "
            f"JOIN complaints c2 ON cd.depends_on_complaint_id = c2.id "
            f"WHERE cd.complaint_id IN ({placeholders}) AND cd.status = 'confirmed'",
            tuple(all_complaint_ids)
        ).fetchall()
        for row in dep_rows:
            cid = row['complaint_id']
            if cid not in confirmed_deps:
                confirmed_deps[cid] = []
            confirmed_deps[cid].append(row)

    return render_template('user_dashboard.html', my_complaints=my_complaints, joined=joined,
                           open_complaints=open_complaints, confirmed_deps=confirmed_deps)


@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit_complaint():
    # Redirect admin to their dashboard
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    similar = None

    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form['description'].strip()
        category = request.form['category']
        location = request.form['location'].strip()

        if not title or not description or not category or not location:
            flash('Please enter all required fields.', 'danger')
            return render_template('submit_complaint.html')

        similar = find_similar_complaints(title, description, category, location)

        if similar:
            session['pending_complaint'] = {
                'title': title,
                'description': description,
                'category': category,
                'location': location
            }
            return render_template('submit_complaint.html', show_similar_modal=True, similar=similar)

        db = get_db()
        cursor = db_execute(db,
            "INSERT INTO complaints (title, description, category, location, status, priority, created_by) "
            "VALUES (?, ?, ?, ?, 'Pending', 'Low', ?) RETURNING id",
            (title, description, category, location, session['user_id'])
        )
        complaint_id = getattr(cursor, '_lastrowid', None) or cursor.fetchone()[0]
        # Add creator as an affected user with role_in_complaint='creator'
        db_execute(db,
            "INSERT INTO complaint_users (complaint_id, user_id, role_in_complaint) VALUES (?, ?, 'creator') "
            "ON CONFLICT DO NOTHING",
            (complaint_id, session['user_id'])
        )
        # Add history entry
        creator_name = session.get('name', 'User')
        db_execute(db,
            "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
            (complaint_id, session['user_id'], creator_name + ' created complaint')
        )
        db.commit()
        # Run dependency suggestion logic
        find_dependency_suggestions(complaint_id)
        flash('Issue submitted successfully.', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('submit_complaint.html')


@app.route('/create-new', methods=['POST'])
@login_required
def create_new_complaint():
    # Redirect admin to their dashboard
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    pending = session.pop('pending_complaint', None)
    if not pending:
        flash('No pending complaint found.', 'warning')
        return redirect(url_for('submit_complaint'))

    db = get_db()
    cursor = db_execute(db,
        "INSERT INTO complaints (title, description, category, location, status, priority, created_by) "
        "VALUES (?, ?, ?, ?, 'Pending', 'Low', ?) RETURNING id",
        (pending['title'], pending['description'], pending['category'], pending['location'], session['user_id'])
    )
    complaint_id = getattr(cursor, '_lastrowid', None) or cursor.fetchone()[0]
    # Add creator as an affected user with role_in_complaint='creator'
    db_execute(db,
        "INSERT INTO complaint_users (complaint_id, user_id, role_in_complaint) VALUES (?, ?, 'creator') "
        "ON CONFLICT DO NOTHING",
        (complaint_id, session['user_id'])
    )
    # Add history entry
    creator_name = session.get('name', 'User')
    db_execute(db,
        "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
        (complaint_id, session['user_id'], creator_name + ' created complaint')
    )
    db.commit()
    # Run dependency suggestion logic
    find_dependency_suggestions(complaint_id)
    flash('Issue submitted successfully.', 'success')
    return redirect(url_for('user_dashboard'))


@app.route('/join/<int:complaint_id>', methods=['POST'])
@login_required
def join_complaint(complaint_id):
    # Redirect admin to their dashboard
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    db = get_db()
    user_id = session['user_id']

    cursor = db_execute(db,
        "INSERT INTO complaint_users (complaint_id, user_id, role_in_complaint) VALUES (?, ?, 'joined') "
        "ON CONFLICT DO NOTHING",
        (complaint_id, user_id)
    )
    if cursor.rowcount == 0:
        flash('You have already joined this issue.', 'info')
    else:
        db.commit()
        update_priority(complaint_id)
        # Add history entry
        user_name = session.get('name', 'User')
        db_execute(db,
            "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
            (complaint_id, user_id, user_name + ' joined complaint')
        )
        db.commit()
        flash('You joined this issue.', 'success')

    return redirect(url_for('user_dashboard'))


# ─── Admin routes ───────────────────────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()

    status_filter = request.args.get('status', '')
    category_filter = request.args.get('category', '')

    query = (
        "SELECT c.*, u.name AS creator_name, "
        "(SELECT COUNT(*) FROM complaint_users cu WHERE cu.complaint_id = c.id) AS affected_users "
        "FROM complaints c JOIN users u ON c.created_by = u.id "
    )
    params = []
    conditions = []

    if status_filter:
        conditions.append("c.status = ?")
        params.append(status_filter)
    if category_filter:
        conditions.append("c.category = ?")
        params.append(category_filter)

    if conditions:
        query += "WHERE " + " AND ".join(conditions) + " "

    query += (
        "ORDER BY "
        "  CASE c.priority "
        "    WHEN 'High' THEN 1 "
        "    WHEN 'Medium' THEN 2 "
        "    WHEN 'Low' THEN 3 "
        "  END, c.created_at DESC"
    )

    complaints = db_execute(db, query, params).fetchall()

    # Fetch suggested dependencies for admin
    suggested_deps = db_execute(db,
        "SELECT cd.*, c1.title AS complaint_title, c2.title AS parent_title "
        "FROM complaint_dependencies cd "
        "JOIN complaints c1 ON cd.complaint_id = c1.id "
        "JOIN complaints c2 ON cd.depends_on_complaint_id = c2.id "
        "WHERE cd.status = 'suggested' "
        "ORDER BY cd.created_at DESC"
    ).fetchall()

    return render_template('admin_dashboard.html', complaints=complaints,
                           suggested_deps=suggested_deps,
                           status_filter=status_filter, category_filter=category_filter)


@app.route('/complaint/<int:complaint_id>')
@login_required
def complaint_detail(complaint_id):
    db = get_db()
    complaint = db_execute(db,
        "SELECT c.*, u.name AS creator_name "
        "FROM complaints c JOIN users u ON c.created_by = u.id "
        "WHERE c.id = ?",
        (complaint_id,)
    ).fetchone()

    if not complaint:
        flash('Issue not found.', 'danger')
        return redirect(url_for('login'))

    affected_users = db_execute(db,
        "SELECT u.id, u.name, u.email, cu.joined_at, cu.role_in_complaint "
        "FROM complaint_users cu JOIN users u ON cu.user_id = u.id "
        "WHERE cu.complaint_id = ? ORDER BY cu.joined_at",
        (complaint_id,)
    ).fetchall()

    affected_count = len(affected_users)

    # Get activity history
    history = db_execute(db,
        "SELECT ch.*, u.name AS user_name "
        "FROM complaint_history ch JOIN users u ON ch.user_id = u.id "
        "WHERE ch.complaint_id = ? ORDER BY ch.created_at ASC",
        (complaint_id,)
    ).fetchall()

    # Get suggested dependencies (for admin)
    suggested_deps = db_execute(db,
        "SELECT cd.*, c1.title AS complaint_title, c2.title AS parent_title "
        "FROM complaint_dependencies cd "
        "JOIN complaints c1 ON cd.complaint_id = c1.id "
        "JOIN complaints c2 ON cd.depends_on_complaint_id = c2.id "
        "WHERE cd.complaint_id = ? AND cd.status = 'suggested'",
        (complaint_id,)
    ).fetchall()

    # Get confirmed dependencies (for all users)
    confirmed_deps = db_execute(db,
        "SELECT cd.*, c1.title AS complaint_title, c2.title AS parent_title "
        "FROM complaint_dependencies cd "
        "JOIN complaints c1 ON cd.complaint_id = c1.id "
        "JOIN complaints c2 ON cd.depends_on_complaint_id = c2.id "
        "WHERE cd.complaint_id = ? AND cd.status = 'confirmed'",
        (complaint_id,)
    ).fetchall()

    # Check if this is a parent of any confirmed dependency (for status update warning)
    has_linked_children = db_execute(db,
        "SELECT COUNT(*) AS cnt FROM complaint_dependencies "
        "WHERE depends_on_complaint_id = ? AND status = 'confirmed'",
        (complaint_id,)
    ).fetchone()['cnt']

    return render_template('complaint_detail.html', complaint=complaint,
                           affected_users=affected_users, affected_count=affected_count,
                           history=history,
                           suggested_deps=suggested_deps,
                           confirmed_deps=confirmed_deps,
                           has_linked_children=has_linked_children)


@app.route('/complaint/<int:complaint_id>/status', methods=['POST'])
@admin_required
def update_status(complaint_id):
    new_status = request.form['status']
    if new_status not in ['Pending', 'In Progress', 'Resolved']:
        flash('Invalid status.', 'danger')
        return redirect(url_for('admin_dashboard'))

    db = get_db()
    resolution_notes = request.form.get('resolution_notes', '').strip()

    if new_status == 'Resolved' and resolution_notes:
        db_execute(db,
            "UPDATE complaints SET status = ?, resolution_notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_status, resolution_notes, complaint_id)
        )
    else:
        db_execute(db,
            "UPDATE complaints SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_status, complaint_id)
        )

    # Add history entry
    admin_name = session.get('name', 'Admin')
    action = admin_name + ' changed status to ' + new_status
    if new_status == 'Resolved' and resolution_notes:
        action = admin_name + ' resolved issue: ' + resolution_notes
    db_execute(db,
        "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
        (complaint_id, session['user_id'], action)
    )

    # Check if resolving a parent complaint with linked children
    if new_status == 'Resolved':
        linked_children = db_execute(db,
            "SELECT cd.*, c.title AS child_title FROM complaint_dependencies cd "
            "JOIN complaints c ON cd.complaint_id = c.id "
            "WHERE cd.depends_on_complaint_id = ? AND cd.status = 'confirmed'",
            (complaint_id,)
        ).fetchall()
        if linked_children:
            msgs = []
            for child in linked_children:
                msgs.append(child['child_title'])
            db_execute(db,
                "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
                (complaint_id, session['user_id'], 'Parent issue resolved. Linked issues need review.')
            )
            flash('Linked issue needs review: ' + ', '.join(msgs), 'warning')

    db.commit()
    flash('Status updated.', 'success')
    return redirect(url_for('admin_dashboard'))


# ─── Dependency Routes ──────────────────────────────────────────────────────────

@app.route('/complaint/<int:complaint_id>/dependency/<int:dep_id>/confirm', methods=['POST'])
@admin_required
def confirm_dependency(complaint_id, dep_id):
    db = get_db()
    dep = db_execute(db,
        "SELECT cd.*, c.title AS parent_title FROM complaint_dependencies cd "
        "JOIN complaints c ON cd.depends_on_complaint_id = c.id "
        "WHERE cd.id = ? AND cd.complaint_id = ?",
        (dep_id, complaint_id)
    ).fetchone()

    if not dep:
        flash('Dependency not found.', 'danger')
        return redirect(request.referrer or url_for('admin_dashboard'))

    db_execute(db,
        "UPDATE complaint_dependencies SET status = 'confirmed' WHERE id = ?",
        (dep_id,)
    )
    admin_name = session.get('name', 'Admin')
    db_execute(db,
        "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
        (complaint_id, session['user_id'], admin_name + ' confirmed dependency with ' + dep['parent_title'])
    )
    db.commit()
    flash('Dependency confirmed.', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))


@app.route('/complaint/<int:complaint_id>/dependency/<int:dep_id>/ignore', methods=['POST'])
@admin_required
def ignore_dependency(complaint_id, dep_id):
    db = get_db()
    dep = db_execute(db,
        "SELECT * FROM complaint_dependencies WHERE id = ? AND complaint_id = ?",
        (dep_id, complaint_id)
    ).fetchone()

    if not dep:
        flash('Dependency not found.', 'danger')
        return redirect(request.referrer or url_for('admin_dashboard'))

    db_execute(db,
        "UPDATE complaint_dependencies SET status = 'ignored' WHERE id = ?",
        (dep_id,)
    )
    admin_name = session.get('name', 'Admin')
    db_execute(db,
        "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
        (complaint_id, session['user_id'], admin_name + ' ignored dependency suggestion')
    )
    db.commit()
    flash('Dependency ignored.', 'info')
    return redirect(request.referrer or url_for('admin_dashboard'))


# ─── API Routes ────────────────────────────────────────────────────────────────

@app.route('/api/my-complaints')
def api_my_complaints():
    if 'user_id' not in session:
        return jsonify({'complaints': []})

    db = get_db()
    user_id = session['user_id']

    complaints = db_execute(db,
        "SELECT c.id, c.title, c.status, "
        "(SELECT COUNT(*) FROM complaint_users cu2 WHERE cu2.complaint_id = c.id) AS affected_users "
        "FROM complaints c "
        "JOIN complaint_users cu ON c.id = cu.complaint_id "
        "WHERE cu.user_id = ? "
        "GROUP BY c.id",
        (user_id,)
    ).fetchall()

    return jsonify({'complaints': [dict(c) for c in complaints]})


# ─── Main ───────────────────────────────────────────────────────────────────────

# Initialize database for both local and Render
with app.app_context():
    init_db()
    seed_demo_data()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
