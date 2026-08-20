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

DATABASE_URL = 'postgresql://neondb_owner:npg_Mg9r4CXnuzmd@ep-aged-frost-aycgiw14.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require'


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


@app.route('/health')
def health_check():
    """Health check endpoint for Render / uptime monitors."""
    try:
        db = get_db()
        db_execute(db, "SELECT 1")
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500


def _infer_issue_type(category, title, description):
    """Infer issue_type from category + title/description for existing complaints."""
    text = (title + ' ' + description).lower()
    cat = category.lower()

    if cat == 'electricity':
        if any(kw in text for kw in ['power cut', 'no power', 'power supply']):
            return 'Power Cut'
        if any(kw in text for kw in ['low voltage', 'voltage']):
            return 'Low Voltage'
        if any(kw in text for kw in ['wiring', 'wire']):
            return 'Wiring Issue'
        if any(kw in text for kw in ['switch', 'board issue']):
            return 'Switch/Board Issue'
        return 'Power Cut'  # default for electricity

    if cat == 'water':
        if any(kw in text for kw in ['motor', 'pump not working']):
            return 'Motor/Pump Not Working'
        if any(kw in text for kw in ['leak', 'leakage', 'pipe']):
            return 'Pipe Leakage'
        if any(kw in text for kw in ['tap broken', 'tap']):
            return 'Tap Broken'
        if any(kw in text for kw in ['tank empty', 'overhead tank']):
            return 'Tank Empty'
        if any(kw in text for kw in ['water not coming', 'no water']):
            return 'Water Not Coming'
        return 'Other'

    if cat in ('wi-fi', 'wifi'):
        if any(kw in text for kw in ['router not working', 'router']):
            return 'Router Not Working'
        if any(kw in text for kw in ['slow internet', 'slow']):
            return 'Slow Internet'
        if any(kw in text for kw in ['no network', 'network', 'not working', 'down']):
            return 'No Network'
        if any(kw in text for kw in ['password', 'login']):
            return 'Password/Login Issue'
        return 'Other'

    if cat == 'cleanliness':
        if any(kw in text for kw in ['washroom', 'toilet', 'bathroom cleaning']):
            return 'Washroom Cleaning'
        if any(kw in text for kw in ['garbage', 'trash', 'waste']):
            return 'Garbage Issue'
        if any(kw in text for kw in ['bad smell', 'smell', 'odour']):
            return 'Bad Smell'
        return 'Other'

    if cat == 'plumbing':
        if any(kw in text for kw in ['pipe burst', 'burst pipe']):
            return 'Pipe Burst'
        if any(kw in text for kw in ['tap', 'faucet', 'leak']):
            return 'Tap/Faucet Leak'
        if any(kw in text for kw in ['toilet blocked', 'blocked', 'clogged', 'drain']):
            return 'Blocked Drain'
        if any(kw in text for kw in ['water heater', 'geyser']):
            return 'Water Heater Issue'
        return 'Other'

    if cat == 'carpentry':
        if any(kw in text for kw in ['door', 'door lock', 'broken door']):
            return 'Door Issue'
        if any(kw in text for kw in ['window', 'window lock', 'broken window']):
            return 'Window Issue'
        if any(kw in text for kw in ['furniture', 'chair', 'table', 'bench', 'desk']):
            return 'Furniture Repair'
        if any(kw in text for kw in ['shelf', 'cabinet', 'cupboard']):
            return 'Shelf/Cabinet Issue'
        return 'Other'

    return 'Other'


# ─── SLA helpers ────────────────────────────────────────────────────────────────

# Default SLA hours used when no DB override exists
_DEFAULT_SLA = {
    'Electricity': {'High': 1,  'Medium': 3,  'Low': 6},
    'Water':       {'High': 2,  'Medium': 4,  'Low': 8},
    'Wi-Fi':       {'High': 3,  'Medium': 6,  'Low': 12},
    'Cleanliness': {'High': 6,  'Medium': 12, 'Low': 24},
    'Classroom':   {'High': 2,  'Medium': 6,  'Low': 12},
    'Hostel':      {'High': 4,  'Medium': 8,  'Low': 24},
    'Plumbing':    {'High': 2,  'Medium': 6,  'Low': 12},
    'Carpentry':   {'High': 6,  'Medium': 12, 'Low': 24},
    'Other':       {'High': 6,  'Medium': 12, 'Low': 24},
}

def _seed_default_sla(db):
    """Insert default SLA rows only if the table is completely empty."""
    count = db_execute(db, "SELECT COUNT(*) AS cnt FROM sla_settings").fetchone()['cnt']
    if count > 0:
        return
    for cat, priorities in _DEFAULT_SLA.items():
        for prio, hrs in priorities.items():
            db_execute(db,
                "INSERT INTO sla_settings (category, priority, hours) VALUES (%s, %s, %s) "
                "ON CONFLICT (category, priority) DO NOTHING",
                (cat, prio, hrs)
            )


def get_sla_hours(category, priority):
    """Return SLA hours for a category/priority from DB, falling back to defaults."""
    try:
        db = get_db()
        row = db_execute(db,
            "SELECT hours FROM sla_settings WHERE category = %s AND priority = %s",
            (category, priority)
        ).fetchone()
        if row:
            return row['hours']
    except Exception:
        pass
    return _DEFAULT_SLA.get(category, {}).get(priority, 6)


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
            issue_type  TEXT    DEFAULT '',
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
        """CREATE TABLE IF NOT EXISTS sla_settings (
            id          SERIAL PRIMARY KEY,
            category    TEXT    NOT NULL,
            priority    TEXT    NOT NULL,
            hours       INTEGER NOT NULL DEFAULT 6,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, priority)
        )""",
    ]
    for sql in statements:
        db_execute(db, sql)

    def _run_migration(sql, params=None):
        """Run a single migration statement in its own savepoint so a failure
        doesn't abort the whole transaction (PostgreSQL behaviour)."""
        try:
            db_execute(db, "SAVEPOINT migration_sp")
            if params:
                db_execute(db, sql, params)
            else:
                db_execute(db, sql)
            db_execute(db, "RELEASE SAVEPOINT migration_sp")
        except Exception:
            db_execute(db, "ROLLBACK TO SAVEPOINT migration_sp")

    # Migration: add resolution_notes column if missing
    _run_migration("ALTER TABLE complaints ADD COLUMN resolution_notes TEXT DEFAULT ''")

    # Migration: add confidence column to complaint_dependencies
    _run_migration("ALTER TABLE complaint_dependencies ADD COLUMN confidence TEXT DEFAULT 'Medium'")

    # Migration: add issue_type column to complaints
    _run_migration("ALTER TABLE complaints ADD COLUMN issue_type TEXT DEFAULT ''")

    # Migration: add assigned_to column
    _run_migration("ALTER TABLE complaints ADD COLUMN assigned_to INTEGER REFERENCES users(id)")

    # Migration: add technician_status column
    _run_migration("ALTER TABLE complaints ADD COLUMN technician_status TEXT DEFAULT 'Not Assigned'")

    db.commit()

    # Migration: infer issue_type for existing complaints where it's empty
    try:
        rows = db_execute(db,
            "SELECT id, category, title, description FROM complaints WHERE issue_type IS NULL OR issue_type = ''"
        ).fetchall()
        for row in rows:
            inferred = _infer_issue_type(row['category'], row['title'], row['description'])
            if inferred:
                db_execute(db, "UPDATE complaints SET issue_type = %s WHERE id = %s", (inferred, row['id']))
        if rows:
            db.commit()
    except Exception:
        db.rollback()

    # Seed default SLA settings if table is empty
    _seed_default_sla(db)

    db.commit()


# ─── Seed demo data ─────────────────────────────────────────────────────────────

def seed_demo_data():
    db = get_db()

    # ── Always ensure demo users exist (idempotent via ON CONFLICT) ───────
    demo_users = [
        ('Student One', 'student1@cirs.com', generate_password_hash('student123'), 'user'),
        ('Student Two', 'student2@cirs.com', generate_password_hash('student123'), 'user'),
        ('Student Three', 'student3@cirs.com', generate_password_hash('student123'), 'user'),
        ('Admin User', 'admin@cirs.com', generate_password_hash('admin123'), 'admin'),
        ('Plumbing Technician', 'plumber@cirs.com', generate_password_hash('tech123'), 'technician'),
        ('Electrical Technician', 'electrician@cirs.com', generate_password_hash('tech123'), 'technician'),
        ('Carpentry Technician', 'carpenter@cirs.com', generate_password_hash('tech123'), 'technician'),
    ]
    for name, email, password, role in demo_users:
        db_execute(db,
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (email) DO NOTHING",
            (name, email, password, role)
        )

    # Always ensure admin user has correct role and password (fixes login issues)
    db_execute(db,
        "UPDATE users SET name = ?, password = ?, role = ? WHERE email = ?",
        ('Admin User', generate_password_hash('admin123'), 'admin', 'admin@cirs.com')
    )
    db.commit()

    # Fetch user IDs (whether just inserted or pre-existing)
    def _user_id(email):
        return db_execute(db, "SELECT id FROM users WHERE email = ?", (email,)).fetchone()['id']

    s1 = _user_id('student1@cirs.com')
    s2 = _user_id('student2@cirs.com')
    s3 = _user_id('student3@cirs.com')
    a1 = _user_id('admin@cirs.com')

    # Only seed complaint demo data if complaints table is empty
    existing = db_execute(db, "SELECT COUNT(*) AS cnt FROM complaints").fetchone()['cnt']
    if existing > 0:
        return

    def _insert(sql, params):
        """Insert a row and return the generated ID."""
        cur = db_execute(db, sql + " RETURNING id", params)
        return getattr(cur, '_lastrowid', None) or cur.fetchone()[0]

    # ── Create 6 complaints ───────────────────────────────────────────────

    def _make_complaint(title, desc, cat, itype, loc, status, priority, creator_id, creator_name):
        cid = _insert(
            "INSERT INTO complaints (title, description, category, issue_type, location, status, priority, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, desc, cat, itype, loc, status, priority, creator_id))
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
        'Wi-Fi', 'No Network', 'Hostel Block A', 'In Progress', 'Medium', s1, 'Student One')
    _join(c1, s2, 'Student Two')
    _join(c1, s3, 'Student Three')
    _set_status(c1, 'In Progress', 'Admin User')
    _set_priority(c1, 3)
    db.commit()

    # ── C2: Electricity failure (Student One) ────────────────────────────────
    c2 = _make_complaint(
        'Electricity failure in Hostel Block A',
        'Power supply is unavailable in Hostel Block A. Lights and fans are not working.',
        'Electricity', 'Power Cut', 'Hostel Block A', 'Pending', 'Low', s1, 'Student One')
    db.commit()

    # ── C3: Water motor not working (Student Two) ──────────────────────────
    c3 = _make_complaint(
        'Water motor not working',
        'Motor is not running and water is not coming to the overhead tank.',
        'Water', 'Motor/Pump Not Working', 'Hostel Block A', 'Pending', 'Low', s2, 'Student Two')
    db.commit()

    # ── C4: Leaking tap (Student Three) ────────────────────────────────────
    c4 = _make_complaint(
        'Water leakage near bathroom',
        'The tap in the ground floor boys washroom is continuously leaking. Water is being wasted.',
        'Water', 'Pipe Leakage', 'Academic Block', 'In Progress', 'Low', s3, 'Student Three')
    _join(c4, s1, 'Student One')
    _set_status(c4, 'In Progress', 'Admin User')
    _set_priority(c4, 2)
    db.commit()

    # ── C5: Projector bulb fuse (Student Two) — RESOLVED ───────────────────
    c5 = _make_complaint(
        'Projector bulb fuse in Room 201',
        'The projector bulb in classroom 201 has fused. Unable to conduct presentations.',
        'Classroom', 'Other', 'Room 201', 'Resolved', 'Low', s2, 'Student Two')
    _set_status(c5, 'Resolved', 'Admin User', 'Replaced the projector bulb. Working normally now.')
    db.commit()

    # ── C6: Slow internet in Computer Lab (Student Three) ──────────────────
    c6 = _make_complaint(
        'Slow internet in Computer Lab',
        'The internet speed in the computer lab is extremely slow. Unable to load websites and access lab resources.',
        'Wi-Fi', 'Slow Internet', 'Computer Lab', 'Pending', 'Medium', s3, 'Student Three')
    _join(c6, s1, 'Student One')
    _join(c6, s2, 'Student Two')
    _join(c6, a1, 'Admin User')  # Admin also joined to show they're affected
    _set_priority(c6, 4)
    db.commit()

    # ── Dependencies ───────────────────────────────────────────────────────

    # Dep 1: C3 (Water motor) → C2 (Electricity) — SUGGESTED
    # Water motor depends on electricity: issue_type rule, same location
    db_execute(db,
        "INSERT INTO complaint_dependencies (complaint_id, depends_on_complaint_id, reason, status, confidence) "
        "VALUES (?, ?, ?, 'suggested', ?)",
        (c3, c2, 'Water supply may require motor or pump, and motor requires electricity.', 'High'))

    # Dep 2: C1 (Wi-Fi not working) → C2 (Electricity) — CONFIRMED
    # Wi-Fi router needs power: issue_type rule, same location
    db_execute(db,
        "INSERT INTO complaint_dependencies (complaint_id, depends_on_complaint_id, reason, status, confidence) "
        "VALUES (?, ?, ?, 'confirmed', ?)",
        (c1, c2, 'Router or network equipment may require electricity.', 'High'))
    db_execute(db,
        "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
        (c1, a1, 'Admin User confirmed dependency with Electricity failure in Hostel Block A'))

    # Dep 3: C6 (Slow internet in Computer Lab) → C2 (Electricity) — SUGGESTED
    # Network equipment in the lab may rely on the same power infrastructure
    db_execute(db,
        "INSERT INTO complaint_dependencies (complaint_id, depends_on_complaint_id, reason, status, confidence) "
        "VALUES (?, ?, ?, 'suggested', ?)",
        (c6, c2, 'Network equipment in the lab may rely on the same power infrastructure. Location differs — admin should verify.', 'Medium'))

    db.commit()


# ─── Always ensure demo dependency exists ───────────────────────────────────────

def _ensure_demo_complaint(db, title, desc, cat, itype, loc, creator_id, creator_name):
    """Find existing complaint by title or create one. Returns complaint id."""
    existing = db_execute(db, "SELECT id FROM complaints WHERE title = ?", (title,)).fetchone()
    if existing:
        # Update issue_type to match demo expectations
        db_execute(db, "UPDATE complaints SET category = ?, issue_type = ?, location = ? WHERE id = ?",
                   (cat, itype, loc, existing['id']))
        return existing['id']

    # Create complaint
    cur = db_execute(db,
        "INSERT INTO complaints (title, description, category, issue_type, location, status, priority, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'Pending', 'Low', ?) RETURNING id",
        (title, desc, cat, itype, loc, creator_id))
    cid = getattr(cur, '_lastrowid', None) or cur.fetchone()['id']
    # Add creator
    db_execute(db,
        "INSERT INTO complaint_users (complaint_id, user_id, role_in_complaint) VALUES (?, ?, 'creator') "
        "ON CONFLICT DO NOTHING",
        (cid, creator_id))
    db_execute(db,
        "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
        (cid, creator_id, creator_name + ' created complaint'))
    return cid


def seed_demo_dependency():
    """Always ensure ALL demo complaints and the key dependency exist."""
    db = get_db()

    # Get user ids
    admin = db_execute(db, "SELECT id FROM users WHERE email = ?", ('admin@cirs.com',)).fetchone()
    s1_row = db_execute(db, "SELECT id FROM users WHERE email = ?", ('student1@cirs.com',)).fetchone()
    s2_row = db_execute(db, "SELECT id FROM users WHERE email = ?", ('student2@cirs.com',)).fetchone()
    s3_row = db_execute(db, "SELECT id FROM users WHERE email = ?", ('student3@cirs.com',)).fetchone()
    if not admin or not s1_row or not s2_row or not s3_row:
        return  # Users not seeded yet

    a1 = admin['id']
    s1 = s1_row['id']
    s2 = s2_row['id']
    s3 = s3_row['id']

    # Helper: ensure a complaint_user record exists with history
    def _ensure_joined(cid, uid, role, uname):
        cur = db_execute(db,
            "INSERT INTO complaint_users (complaint_id, user_id, role_in_complaint) VALUES (?, ?, ?) "
            "ON CONFLICT DO NOTHING",
            (cid, uid, role))
        if cur.rowcount and cur.rowcount > 0:
            db_execute(db,
                "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
                (cid, uid, uname + ' joined complaint'))

    # ── Ensure all 6 demo complaints exist ────────────────────────────────

    c1 = _ensure_demo_complaint(db,
        'Wi-Fi not working in Hostel Block A',
        'The Wi-Fi network has been down since yesterday. Students are unable to access the internet for online classes.',
        'Wi-Fi', 'No Network', 'Hostel Block A', s1, 'Student One')

    c2 = _ensure_demo_complaint(db,
        'Electricity failure in Hostel Block A',
        'Power supply is unavailable in Hostel Block A. Lights and fans are not working.',
        'Electricity', 'Power Cut', 'Hostel Block A', s1, 'Student One')

    c3 = _ensure_demo_complaint(db,
        'Water motor not working',
        'Motor is not running and water is not coming to the overhead tank.',
        'Water', 'Motor/Pump Not Working', 'Hostel Block A', s2, 'Student Two')

    c4 = _ensure_demo_complaint(db,
        'Water leakage near bathroom',
        'The tap in the ground floor boys washroom is continuously leaking. Water is being wasted.',
        'Water', 'Pipe Leakage', 'Academic Block', s3, 'Student Three')

    c5 = _ensure_demo_complaint(db,
        'Projector bulb fuse in Room 201',
        'The projector bulb in classroom 201 has fused. Unable to conduct presentations.',
        'Classroom', 'Other', 'Room 201', s2, 'Student Two')

    c6 = _ensure_demo_complaint(db,
        'Slow internet in Computer Lab',
        'The internet speed in the computer lab is extremely slow. Unable to load websites and access lab resources.',
        'Wi-Fi', 'Slow Internet', 'Computer Lab', s3, 'Student Three')

    db.commit()

    # ── Ensure join records ───────────────────────────────────────────────
    _ensure_joined(c1, s2, 'joined', 'Student Two')
    _ensure_joined(c1, s3, 'joined', 'Student Three')
    _ensure_joined(c4, s1, 'joined', 'Student One')
    _ensure_joined(c6, s1, 'joined', 'Student One')
    _ensure_joined(c6, s2, 'joined', 'Student Two')
    _ensure_joined(c6, a1, 'joined', 'Admin User')
    db.commit()

    # ── Set correct statuses and priorities ────────────────────────────────
    # C1: In Progress, Medium (3 joined)
    cur = db_execute(db, "UPDATE complaints SET status = 'In Progress', priority = 'Medium' WHERE id = ? AND status = 'Pending'", (c1,))
    if cur.rowcount:
        db_execute(db,
            "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
            (c1, a1, 'Admin User changed status to In Progress'))
    # C4: In Progress
    cur = db_execute(db, "UPDATE complaints SET status = 'In Progress' WHERE id = ? AND status = 'Pending'", (c4,))
    if cur.rowcount:
        db_execute(db,
            "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
            (c4, a1, 'Admin User changed status to In Progress'))
    # C5: Resolved with notes
    cur = db_execute(db,
        "UPDATE complaints SET status = 'Resolved', resolution_notes = ?, priority = 'Low' WHERE id = ? AND status = 'Pending'",
        ('Replaced the projector bulb. Working normally now.', c5))
    if cur.rowcount:
        db_execute(db,
            "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
            (c5, a1, 'Admin User resolved issue: Replaced the projector bulb. Working normally now.'))
    # C6: Medium priority (4 joined)
    cur = db_execute(db, "UPDATE complaints SET priority = 'Medium' WHERE id = ? AND priority = 'Low'", (c6,))
    db.commit()

    # ── Ensure the key demo dependency (C3 → C2, SUGGESTED) ───────────────
    existing_dep = db_execute(db,
        "SELECT id FROM complaint_dependencies WHERE complaint_id = ? AND depends_on_complaint_id = ?",
        (c3, c2)
    ).fetchone()

    if not existing_dep:
        db_execute(db,
            "INSERT INTO complaint_dependencies (complaint_id, depends_on_complaint_id, reason, status, confidence) "
            "VALUES (?, ?, ?, 'suggested', ?)",
            (c3, c2, 'Water supply may require motor or pump, and motor requires electricity.', 'High'))
        db.commit()

    # ── Ensure the confirmed dependency (C1 → C2, CONFIRMED) ───────────────
    existing_confirmed = db_execute(db,
        "SELECT id FROM complaint_dependencies WHERE complaint_id = ? AND depends_on_complaint_id = ?",
        (c1, c2)
    ).fetchone()

    if not existing_confirmed:
        db_execute(db,
            "INSERT INTO complaint_dependencies (complaint_id, depends_on_complaint_id, reason, status, confidence) "
            "VALUES (?, ?, ?, 'confirmed', ?)",
            (c1, c2, 'Router or network equipment may require electricity.', 'High'))
        db_execute(db,
            "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
            (c1, a1, 'Admin User confirmed dependency with Electricity failure in Hostel Block A'))
        db.commit()

    # ── Ensure the suggested dependency (C6 → C2, SUGGESTED) ───────────────
    existing_c6_c2 = db_execute(db,
        "SELECT id FROM complaint_dependencies WHERE complaint_id = ? AND depends_on_complaint_id = ?",
        (c6, c2)
    ).fetchone()

    if not existing_c6_c2:
        db_execute(db,
            "INSERT INTO complaint_dependencies (complaint_id, depends_on_complaint_id, reason, status, confidence) "
            "VALUES (?, ?, ?, 'suggested', ?)",
            (c6, c2, 'Network equipment in the lab may rely on the same power infrastructure. Location differs — admin should verify.', 'Medium'))
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
    hours = get_sla_hours(category, priority)
    if hours == 1:
        return '1 hour'
    return f'{hours} hours'


def get_dynamic_expected_time(category, priority, status):
    """Return dynamic expected resolution time that changes based on status."""
    if status == 'Resolved':
        return 'Completed (0 Hours)'

    base_hours = get_sla_hours(category, priority)

    if status == 'In Progress':
        remaining = max(1, base_hours // 2)
        return f'{remaining} Hours Remaining'

    # Pending or default
    return f'{base_hours} Hours Remaining'


def get_sla_time(category, priority):
    """Return original SLA time text."""
    return get_expected_resolution_time(category, priority)


def timeline_event_name(action):
    """Map raw history action text to a cleaner timeline event name."""
    lower = action.lower()
    if 'created' in lower:
        return 'Issue Reported'
    if 'joined' in lower:
        return 'Joined Existing Issue'
    if 'confirmed dependency' in lower:
        return 'Dependency Confirmed'
    if 'ignored dependency' in lower:
        return 'Dependency Ignored'
    if 'resolved issue' in lower or lower.startswith('resolved') or 'marked issue resolved' in lower:
        return 'Verified & Resolved'
    if 'changed status to' in lower:
        if 'in progress' in lower:
            return 'Status: In Progress'
        if 'pending' in lower:
            return 'Status: Pending'
        if 'resolved' in lower:
            return 'Verified & Resolved'
        return 'Status Updated'
    if 'linked issues need review' in lower:
        return 'Linked Issues Notice'
    if 'assigned issue to' in lower or 'reassigned issue' in lower:
        return 'Technician Assigned'
    if 'started work' in lower:
        return 'Work Started'
    if 'marked work completed' in lower:
        return 'Work Completed'
    if 'note:' in lower:
        return 'Work Note Added'
    if 'needs review' in lower:
        return 'Marked for Review'
    return action


def timeline_event_color(event_name):
    """Return a hex color for a timeline event based on its type."""
    colors = {
        'Issue Reported': '#2563eb',
        'Joined Existing Issue': '#3b82f6',
        'Dependency Suggested': '#f59e0b',
        'Dependency Confirmed': '#16a34a',
        'Dependency Ignored': '#6b7280',
        'Verified & Resolved': '#16a34a',
        'Status: Pending': '#f59e0b',
        'Status: In Progress': '#3b82f6',
        'Status Updated': '#6b7280',
        'Linked Issues Notice': '#dc2626',
        'Technician Assigned': '#8b5cf6',
        'Work Started': '#f97316',
        'Work Completed': '#22c55e',
        'Work Note Added': '#a855f7',
        'Marked for Review': '#6366f1',
    }
    return colors.get(event_name, '#9ca3af')


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

def _location_matches(loc1, loc2):
    """Check if first word of two locations match."""
    if not loc1 or not loc2:
        return False
    return loc1.lower().split()[0] == loc2.lower().split()[0]


def _adjust_confidence(base_conf, location_matches):
    """Same location keeps base; different location caps at Medium."""
    if location_matches:
        return base_conf
    return 'Medium' if base_conf == 'High' else base_conf


def _location_note(location_matches):
    """Return a location suffix for the reason text."""
    if location_matches:
        return ''
    return ' Location differs. Admin should verify before confirming.'


# ── Issue-type-based dependency rules ──────────────────────────────────────

DEPENDENCY_RULES = [
    # Rule 1: Electricity (Power Cut) → Water (Motor/Pump, Tank Empty, Water Not Coming)
    {
        'parent_cat': 'Electricity',
        'parent_type': 'Power Cut',
        'child_cat': 'Water',
        'child_types': ['Motor/Pump Not Working'],
        'reason': 'Water supply may require motor or pump, and motor requires electricity.',
        'confidence': 'High',
    },
    {
        'parent_cat': 'Electricity',
        'parent_type': 'Power Cut',
        'child_cat': 'Water',
        'child_types': ['Tank Empty', 'Water Not Coming'],
        'reason': 'Water supply may require motor or pump, and motor requires electricity.',
        'confidence': 'Medium',
    },
    # Rule 2: Electricity (Power Cut) → Wi-Fi (Router Not Working, No Network)
    {
        'parent_cat': 'Electricity',
        'parent_type': 'Power Cut',
        'child_cat': 'Wi-Fi',
        'child_types': ['Router Not Working', 'No Network'],
        'reason': 'Router or network equipment may require electricity.',
        'confidence': 'High',
    },
    # Rule 3: Water (Water Not Coming, Tank Empty) → Cleanliness (Washroom Cleaning, Bad Smell)
    {
        'parent_cat': 'Water',
        'parent_type': 'Water Not Coming',
        'child_cat': 'Cleanliness',
        'child_types': ['Washroom Cleaning', 'Bad Smell'],
        'reason': 'Cleaning may depend on water availability.',
        'confidence': 'Medium',
    },
    {
        'parent_cat': 'Water',
        'parent_type': 'Tank Empty',
        'child_cat': 'Cleanliness',
        'child_types': ['Washroom Cleaning', 'Bad Smell'],
        'reason': 'Cleaning may depend on water availability.',
        'confidence': 'Medium',
    },
]


# ── Negative rules (independent — do NOT suggest dependency) ───────────────

NEGATIVE_RULES = [
    ('Water', 'Pipe Leakage'),
    ('Water', 'Tap Broken'),
    ('Wi-Fi', 'Slow Internet'),
    ('Wi-Fi', 'Password/Login Issue'),
]


def check_single_dependency(child_complaint, parent_complaint):
    """
    Check if child_complaint depends on parent_complaint using issue_type rules.
    Returns (reason_with_location, confidence) or None.
    """
    parent_cat = parent_complaint.get('category', '')
    parent_type = parent_complaint.get('issue_type', '')
    child_cat = child_complaint.get('category', '')
    child_type = child_complaint.get('issue_type', '')

    # Check negative rules first: if child matches, no dependency
    if (child_cat, child_type) in NEGATIVE_RULES:
        return None

    loc_match = _location_matches(
        child_complaint.get('location', ''),
        parent_complaint.get('location', '')
    )

    for rule in DEPENDENCY_RULES:
        if (rule['parent_cat'] == parent_cat and
            rule['parent_type'] == parent_type and
            rule['child_cat'] == child_cat and
            child_type in rule['child_types']):

            confidence = _adjust_confidence(rule['confidence'], loc_match)
            reason = rule['reason'] + _location_note(loc_match)
            return (reason, confidence)

    return None


def find_dependency_suggestions(complaint_id):
    """
    After a complaint is created, find possible dependencies in BOTH directions:
      1. New complaint depends on existing complaint (child → parent)
      2. Existing complaint depends on new complaint (parent ← child)
    Uses issue-type-based rules with confidence levels.
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

    inserted_count = 0
    for c_id, parent_id, reason, confidence in suggestions:
        try:
            db_execute(db,
                "INSERT INTO complaint_dependencies (complaint_id, depends_on_complaint_id, reason, status, confidence) "
                "VALUES (?, ?, ?, 'suggested', ?)",
                (c_id, parent_id, reason, confidence)
            )
            inserted_count += 1
        except Exception as e:
            print(f"Dependency insert error: {e}")

    if suggestions:
        db.commit()
        print(f"Dependency suggestions inserted: {inserted_count}")


# ─── Jinja2 filters ──────────────────────────────────────────────────────────────

def format_datetime(value, fmt='%d %b %Y, %I:%M %p'):
    """Format a datetime value for display."""
    if value is None:
        return '-'
    return value.strftime(fmt)


def format_date(value, fmt='%d %b %Y'):
    """Format a date-only display from a datetime."""
    if value is None:
        return '-'
    return value.strftime(fmt)


def format_time(value, fmt='%I:%M %p'):
    """Format a time-only datetime value. Handles both datetime objects and strings."""
    return format_datetime(value, fmt)


app.jinja_env.filters['format_datetime'] = format_datetime
app.jinja_env.filters['format_date'] = format_date
app.jinja_env.filters['format_time'] = format_time

# ─── Issue ID formatter ───────────────────────────────────────────────────────

def format_issue_id(complaint_id):
    """Format complaint ID as CIRS-2026-XXX."""
    from datetime import datetime
    year = datetime.now().year
    return f'CIRS-{year}-{complaint_id:03d}'


def current_date():
    """Return current date formatted."""
    from datetime import datetime
    return datetime.now().strftime('%d %b %Y')


# ─── Make helpers available in templates ────────────────────────────────────────

app.jinja_env.globals.update(
    get_expected_resolution_time=get_expected_resolution_time,
    get_dynamic_expected_time=get_dynamic_expected_time,
    get_sla_time=get_sla_time,
    current_date=current_date,
)
app.jinja_env.filters['timeline_event'] = timeline_event_name
app.jinja_env.filters['timeline_color'] = timeline_event_color
app.jinja_env.filters['issue_id'] = format_issue_id


def alert_class(category):
    """Map Flask flash categories to CSS alert classes."""
    mapping = {
        'success': 'green',
        'danger': 'red',
        'warning': 'amber',
        'info': 'blue',
    }
    return mapping.get(category, 'blue')


app.jinja_env.filters['alert_class'] = alert_class


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


def technician_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if session.get('role') != 'technician':
            flash('Technician access required.', 'danger')
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
            if user['role'] == 'technician':
                return redirect(url_for('technician_dashboard'))
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

    # Helper to resolve technician name
    def _resolve_technician(complaint):
        if complaint.get('assigned_to'):
            tech = db_execute(db, "SELECT name FROM users WHERE id = ?", (complaint['assigned_to'],)).fetchone()
            return tech['name'] if tech else None
        return None

    # Complaints Raised by Me (where user is creator)
    my_complaints_raw = db_execute(db,
        "SELECT c.*, cu.joined_at AS created_on, "
        "(SELECT COUNT(*) FROM complaint_users cu2 WHERE cu2.complaint_id = c.id) AS affected_users "
        "FROM complaints c JOIN complaint_users cu ON c.id = cu.complaint_id AND cu.user_id = ? AND cu.role_in_complaint = 'creator' "
        "ORDER BY c.created_at DESC",
        (user_id,)
    ).fetchall()

    my_complaints = []
    for c in my_complaints_raw:
        c_dict = dict(c)
        c_dict['technician_name'] = _resolve_technician(c)
        my_complaints.append(c_dict)

    # Complaints I Joined (where user is joined)
    joined_raw = db_execute(db,
        "SELECT c.*, cu.joined_at AS joined_on, "
        "(SELECT COUNT(*) FROM complaint_users cu2 WHERE cu2.complaint_id = c.id) AS affected_users "
        "FROM complaints c JOIN complaint_users cu ON c.id = cu.complaint_id "
        "WHERE cu.user_id = ? AND cu.role_in_complaint = 'joined' ORDER BY cu.joined_at DESC",
        (user_id,)
    ).fetchall()

    joined = []
    for c in joined_raw:
        c_dict = dict(c)
        c_dict['technician_name'] = _resolve_technician(c)
        joined.append(c_dict)

    # Open complaints: unresolved, user hasn't created or joined
    open_complaints_raw = db_execute(db,
        "SELECT c.*, u.name AS creator_name, "
        "(SELECT COUNT(*) FROM complaint_users cu WHERE cu.complaint_id = c.id) AS affected_users "
        "FROM complaints c JOIN users u ON c.created_by = u.id "
        "WHERE c.status != 'Resolved' "
        "AND c.id NOT IN (SELECT complaint_id FROM complaint_users WHERE user_id = ?) "
        "ORDER BY c.created_at DESC",
        (user_id,)
    ).fetchall()

    open_complaints = []
    for c in open_complaints_raw:
        c_dict = dict(c)
        c_dict['technician_name'] = _resolve_technician(c)
        open_complaints.append(c_dict)

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
        issue_type = request.form.get('issue_type', '').strip()
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
                'issue_type': issue_type,
                'location': location
            }
            return render_template('submit_complaint.html', show_similar_modal=True, similar=similar)

        db = get_db()
        cursor = db_execute(db,
            "INSERT INTO complaints (title, description, category, issue_type, location, status, priority, created_by) "
            "VALUES (?, ?, ?, ?, ?, 'Pending', 'Low', ?) RETURNING id",
            (title, description, category, issue_type, location, session['user_id'])
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
    issue_type = pending.get('issue_type', '')
    cursor = db_execute(db,
        "INSERT INTO complaints (title, description, category, issue_type, location, status, priority, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'Pending', 'Low', ?) RETURNING id",
        (pending['title'], pending['description'], pending['category'], issue_type, pending['location'], session['user_id'])
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


# ─── Technician routes ────────────────────────────────────────────────────────────

@app.route('/technician')
@technician_required
def technician_dashboard():
    db = get_db()
    user_id = session['user_id']

    assigned_complaints = db_execute(db,
        "SELECT c.*, u.name AS creator_name, "
        "(SELECT COUNT(*) FROM complaint_users cu WHERE cu.complaint_id = c.id) AS affected_users "
        "FROM complaints c JOIN users u ON c.created_by = u.id "
        "WHERE c.assigned_to = ? "
        "ORDER BY "
        "  CASE c.priority "
        "    WHEN 'High' THEN 1 "
        "    WHEN 'Medium' THEN 2 "
        "    WHEN 'Low' THEN 3 "
        "  END, c.created_at DESC",
        (user_id,)
    ).fetchall()

    # Split into current work and completed work for template
    current_work = [c for c in assigned_complaints if c['technician_status'] in ('Assigned', 'Work Started')]
    completed_work = [c for c in assigned_complaints if c['technician_status'] == 'Work Completed']

    return render_template('technician_dashboard.html',
                           current_work=current_work, completed_work=completed_work)


@app.route('/complaint/<int:complaint_id>/start-work', methods=['POST'])
@technician_required
def technician_start_work(complaint_id):
    db = get_db()
    complaint = db_execute(db, "SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if not complaint or complaint['assigned_to'] != session['user_id']:
        flash('You are not assigned to this issue.', 'danger')
        return redirect(url_for('technician_dashboard'))

    if complaint['technician_status'] != 'Assigned':
        flash('Cannot start work from current status.', 'warning')
        return redirect(url_for('technician_dashboard'))

    db_execute(db,
        "UPDATE complaints SET technician_status = 'Work Started', status = 'In Progress', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (complaint_id,)
    )
    tech_name = session.get('name', 'Technician')
    db_execute(db,
        "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
        (complaint_id, session['user_id'], f'Technician {tech_name} started work')
    )
    db.commit()
    flash('Work started.', 'success')
    return redirect(url_for('technician_dashboard'))


@app.route('/complaint/<int:complaint_id>/add-note', methods=['POST'])
@technician_required
def technician_add_note(complaint_id):
    note = request.form.get('note', '').strip()
    if not note:
        flash('Please enter a work note.', 'warning')
        return redirect(url_for('technician_dashboard'))

    db = get_db()
    complaint = db_execute(db, "SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if not complaint or complaint['assigned_to'] != session['user_id']:
        flash('You are not assigned to this issue.', 'danger')
        return redirect(url_for('technician_dashboard'))

    tech_name = session.get('name', 'Technician')
    db_execute(db,
        "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
        (complaint_id, session['user_id'], f'Technician {tech_name} note: {note}')
    )
    db.commit()
    flash('Work note added.', 'success')
    return redirect(url_for('technician_dashboard'))


@app.route('/complaint/<int:complaint_id>/mark-completed', methods=['POST'])
@technician_required
def technician_mark_completed(complaint_id):
    db = get_db()
    complaint = db_execute(db, "SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if not complaint or complaint['assigned_to'] != session['user_id']:
        flash('You are not assigned to this issue.', 'danger')
        return redirect(url_for('technician_dashboard'))

    if complaint['technician_status'] not in ('Work Started', 'Assigned'):
        flash('Cannot mark work completed from current status.', 'warning')
        return redirect(url_for('technician_dashboard'))

    db_execute(db,
        "UPDATE complaints SET technician_status = 'Work Completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (complaint_id,)
    )
    tech_name = session.get('name', 'Technician')
    db_execute(db,
        "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
        (complaint_id, session['user_id'], f'Technician {tech_name} marked work completed')
    )
    db.commit()
    flash('Work marked as completed. Awaiting admin verification.', 'success')
    return redirect(url_for('technician_dashboard'))


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

    # Get all technicians for assign dropdown
    technicians = db_execute(db,
        "SELECT id, name FROM users WHERE role = 'technician' ORDER BY name"
    ).fetchall()

    # Resolve technician names for complaints
    complaint_list = []
    for c in complaints:
        c_dict = dict(c)
        if c_dict.get('assigned_to'):
            tech = db_execute(db, "SELECT name FROM users WHERE id = ?", (c_dict['assigned_to'],)).fetchone()
            c_dict['technician_name'] = tech['name'] if tech else None
        else:
            c_dict['technician_name'] = None
        complaint_list.append(c_dict)

    # Summary counts
    total_pending = db_execute(db, "SELECT COUNT(*) AS cnt FROM complaints WHERE status = 'Pending'").fetchone()['cnt']
    total_in_progress = db_execute(db, "SELECT COUNT(*) AS cnt FROM complaints WHERE status = 'In Progress'").fetchone()['cnt']
    total_work_completed = db_execute(db, "SELECT COUNT(*) AS cnt FROM complaints WHERE technician_status = 'Work Completed'").fetchone()['cnt']
    total_resolved = db_execute(db, "SELECT COUNT(*) AS cnt FROM complaints WHERE status = 'Resolved'").fetchone()['cnt']
    total_deps = len(suggested_deps)

    # Pre-filter for Needs Attention section
    needs_assign = [c for c in complaints if c['assigned_to'] is None]
    needs_verify = [c for c in complaints if c['technician_status'] == 'Work Completed']

    # Recent activity logs (last 20 entries across all complaints)
    recent_logs = db_execute(db,
        "SELECT ch.*, u.name AS user_name, c.title AS complaint_title "
        "FROM complaint_history ch "
        "JOIN users u ON ch.user_id = u.id "
        "JOIN complaints c ON ch.complaint_id = c.id "
        "ORDER BY ch.created_at DESC LIMIT 20"
    ).fetchall()

    return render_template('admin_dashboard.html', complaints=complaint_list,
                           suggested_deps=suggested_deps,
                           technicians=technicians,
                           status_filter=status_filter, category_filter=category_filter,
                           total_pending=total_pending, total_in_progress=total_in_progress,
                           total_work_completed=total_work_completed, total_resolved=total_resolved,
                           total_deps=total_deps, recent_logs=recent_logs,
                           needs_assign=needs_assign, needs_verify=needs_verify)


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

    # Get assigned technician info
    assigned_technician = None
    if complaint['assigned_to']:
        tech = db_execute(db, "SELECT id, name FROM users WHERE id = ?", (complaint['assigned_to'],)).fetchone()
        if tech:
            assigned_technician = {'id': tech['id'], 'name': tech['name']}

    # Get all technicians for admin assign dropdown
    all_technicians = []
    if session.get('role') == 'admin':
        all_technicians = db_execute(db, "SELECT id, name FROM users WHERE role = 'technician' ORDER BY name").fetchall()

    # Check if current user is the assigned technician
    is_assigned_technician = (complaint['assigned_to'] == session.get('user_id'))

    return render_template('complaint_detail.html', complaint=complaint,
                           affected_users=affected_users, affected_count=affected_count,
                           history=history,
                           suggested_deps=suggested_deps,
                           confirmed_deps=confirmed_deps,
                           has_linked_children=has_linked_children,
                           assigned_technician=assigned_technician,
                           all_technicians=all_technicians,
                           is_assigned_technician=is_assigned_technician)


@app.route('/complaint/<int:complaint_id>/status', methods=['POST'])
@admin_required
def update_status(complaint_id):
    new_status = request.form['status']
    if new_status not in ['Pending', 'In Progress', 'Resolved', 'Needs Review']:
        flash('Invalid status.', 'danger')
        return redirect(url_for('admin_dashboard'))

    db = get_db()
    complaint = db_execute(db, "SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if not complaint:
        flash('Issue not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    resolution_notes = request.form.get('resolution_notes', '').strip()

    # If resolving without technician completing work, require explanation
    if new_status == 'Resolved' and complaint['technician_status'] != 'Work Completed':
        if not resolution_notes:
            flash('Please provide resolution notes explaining why this issue was resolved directly.', 'warning')
            return redirect(request.referrer or url_for('admin_dashboard'))

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

    # If resolving a parent complaint, mark confirmed dependents as 'Needs Review'
    if new_status == 'Resolved':
        linked_children = db_execute(db,
            "SELECT cd.complaint_id, c.title AS child_title "
            "FROM complaint_dependencies cd "
            "JOIN complaints c ON cd.complaint_id = c.id "
            "WHERE cd.depends_on_complaint_id = %s AND cd.status = 'confirmed' "
            "AND c.status != 'Resolved'",
            (complaint_id,)
        ).fetchall()
        if linked_children:
            for child in linked_children:
                db_execute(db,
                    "UPDATE complaints SET status = 'Needs Review', updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = %s",
                    (child['complaint_id'],)
                )
                db_execute(db,
                    "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (%s, %s, %s)",
                    (child['complaint_id'], session['user_id'],
                     f"Parent issue #{complaint_id} was resolved — this linked issue needs review")
                )
            child_titles = ', '.join(c['child_title'] for c in linked_children)
            flash(f'Parent issue resolved. {len(linked_children)} linked issue(s) moved to Needs Review: {child_titles}', 'info')

    db.commit()
    flash('Status updated.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/complaint/<int:complaint_id>/assign-technician', methods=['POST'])
@admin_required
def assign_technician(complaint_id):
    technician_id = request.form.get('technician_id')
    if not technician_id:
        flash('Please select a technician.', 'warning')
        return redirect(request.referrer or url_for('admin_dashboard'))

    db = get_db()
    complaint = db_execute(db, "SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    if not complaint:
        flash('Issue not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    technician = db_execute(db, "SELECT id, name FROM users WHERE id = ? AND role = 'technician'", (technician_id,)).fetchone()
    if not technician:
        flash('Invalid technician.', 'danger')
        return redirect(url_for('admin_dashboard'))

    admin_name = session.get('name', 'Admin')

    old_tech_name = None
    if complaint['assigned_to']:
        old_tech = db_execute(db, "SELECT name FROM users WHERE id = ?", (complaint['assigned_to'],)).fetchone()
        old_tech_name = old_tech['name'] if old_tech else None

    # Update assignment
    db_execute(db,
        "UPDATE complaints SET assigned_to = ?, technician_status = 'Assigned', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (technician_id, complaint_id)
    )

    # Add history
    new_tech_name = technician['name']
    if old_tech_name:
        action = f'Admin reassigned issue from {old_tech_name} to {new_tech_name}'
    else:
        action = f'Admin assigned issue to {new_tech_name}'

    db_execute(db,
        "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
        (complaint_id, session['user_id'], action)
    )
    db.commit()
    flash(f'Technician assigned: {new_tech_name}', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))


# ─── SLA Settings Route ─────────────────────────────────────────────────────────

@app.route('/admin/sla', methods=['GET', 'POST'])
@admin_required
def sla_settings():
    db = get_db()
    categories = ['Electricity', 'Water', 'Wi-Fi', 'Cleanliness', 'Classroom', 'Hostel', 'Plumbing', 'Carpentry', 'Other']
    priorities = ['High', 'Medium', 'Low']

    if request.method == 'POST':
        updated = 0
        for cat in categories:
            for prio in priorities:
                field = f'hours_{cat}_{prio}'
                val = request.form.get(field, '').strip()
                if val.isdigit() and int(val) > 0:
                    db_execute(db,
                        "INSERT INTO sla_settings (category, priority, hours, updated_at) "
                        "VALUES (%s, %s, %s, CURRENT_TIMESTAMP) "
                        "ON CONFLICT (category, priority) DO UPDATE SET hours = EXCLUDED.hours, updated_at = CURRENT_TIMESTAMP",
                        (cat, prio, int(val))
                    )
                    updated += 1
        db.commit()
        flash(f'SLA settings updated ({updated} entries saved).', 'success')
        return redirect(url_for('sla_settings'))

    # Load current settings into a nested dict: {category: {priority: hours}}
    rows = db_execute(db, "SELECT category, priority, hours FROM sla_settings").fetchall()
    current = {}
    for row in rows:
        current.setdefault(row['category'], {})[row['priority']] = row['hours']

    # Fill defaults for any missing entries
    for cat in categories:
        for prio in priorities:
            if prio not in current.get(cat, {}):
                current.setdefault(cat, {})[prio] = _DEFAULT_SLA.get(cat, {}).get(prio, 6)

    return render_template('sla_settings.html', categories=categories,
                           priorities=priorities, current=current)


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
    seed_demo_dependency()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
