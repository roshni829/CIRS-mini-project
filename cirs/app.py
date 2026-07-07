import os
import re
import sqlite3
from datetime import timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "cirs-mini-project-fixed-secret-key"
app.permanent_session_lifetime = timedelta(hours=3)
csrf = CSRFProtect(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
DATABASE_URL = os.environ.get('DATABASE_URL')


# ─── Database layer (supports PostgreSQL + SQLite fallback) ─────────────────────

if DATABASE_URL:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    def get_db():
        if 'db' not in g:
            g.db = psycopg2.connect(DATABASE_URL)
            g.db._is_postgres = True
        return g.db

    def close_db(exception=None):
        db = g.pop('db', None)
        if db is not None:
            db.close()

    def db_execute(db, sql, params=None):
        """Execute a query, converting SQLite dialect to PostgreSQL."""
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

else:
    def get_db():
        if 'db' not in g:
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
        return g.db

    def close_db(exception=None):
        db = g.pop('db', None)
        if db is not None:
            db.close()

    def db_execute(db, sql, params=None):
        if params:
            return db.execute(sql, params)
        return db.execute(sql)


app.teardown_appcontext(close_db)


def init_db():
    db = get_db()
    # Use SERIAL for PostgreSQL, INTEGER for SQLite fallback
    id_type = "SERIAL" if DATABASE_URL else "INTEGER"
    statements = [
        f"""CREATE TABLE IF NOT EXISTS users (
            id          {id_type} PRIMARY KEY,
            name        TEXT    NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'user',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        f"""CREATE TABLE IF NOT EXISTS complaints (
            id          {id_type} PRIMARY KEY,
            title       TEXT    NOT NULL,
            description TEXT    NOT NULL,
            category    TEXT    NOT NULL,
            location    TEXT    NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'Pending',
            priority    TEXT    NOT NULL DEFAULT 'Low',
            created_by  INTEGER NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS complaint_users (
            id            {id_type} PRIMARY KEY,
            complaint_id  INTEGER NOT NULL,
            user_id       INTEGER NOT NULL,
            role_in_complaint TEXT NOT NULL DEFAULT 'joined',
            joined_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(complaint_id, user_id)
        )""",
        f"""CREATE TABLE IF NOT EXISTS complaint_history (
            id            {id_type} PRIMARY KEY,
            complaint_id  INTEGER NOT NULL,
            user_id       INTEGER NOT NULL,
            action        TEXT    NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )""",
    ]
    for sql in statements:
        db_execute(db, sql)
    db.commit()


# ─── Seed demo data ─────────────────────────────────────────────────────────────

def seed_demo_data():
    db = get_db()
    existing = db_execute(db, "SELECT COUNT(*) FROM users").fetchone()[0]
    if existing > 0:
        return

    db_execute(db,
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        ('Student One', 'student1@gmail.com', generate_password_hash('password123'), 'user')
    )
    db_execute(db,
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        ('Student Two', 'student2@gmail.com', generate_password_hash('password123'), 'user')
    )
    db_execute(db,
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        ('Admin User', 'admin@gmail.com', generate_password_hash('admin123'), 'admin')
    )
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
                "SELECT COUNT(*) FROM complaint_users WHERE complaint_id = ?",
                (row['id'],)
            ).fetchone()[0]
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


def update_priority(complaint_id):
    db = get_db()
    count = db_execute(db,
        "SELECT COUNT(*) FROM complaint_users WHERE complaint_id = ?",
        (complaint_id,)
    ).fetchone()[0]
    new_priority = calculate_priority(count)
    db_execute(db,
        "UPDATE complaints SET priority = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_priority, complaint_id)
    )
    db.commit()


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

    return render_template('user_dashboard.html', my_complaints=my_complaints, joined=joined, open_complaints=open_complaints)


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
        complaint_id = cursor.fetchone()[0]
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
        flash('Complaint submitted.', 'success')
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
    complaint_id = cursor.fetchone()[0]
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
    flash('Complaint submitted.', 'success')
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
        flash('You have already joined this complaint.', 'info')
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
        flash('You joined this complaint.', 'success')

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
    return render_template('admin_dashboard.html', complaints=complaints,
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
        flash('Complaint not found.', 'danger')
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

    return render_template('complaint_detail.html', complaint=complaint,
                           affected_users=affected_users, affected_count=affected_count,
                           history=history)


@app.route('/complaint/<int:complaint_id>/status', methods=['POST'])
@admin_required
def update_status(complaint_id):
    new_status = request.form['status']
    if new_status not in ['Pending', 'In Progress', 'Resolved']:
        flash('Invalid status.', 'danger')
        return redirect(url_for('admin_dashboard'))

    db = get_db()
    db_execute(db,
        "UPDATE complaints SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_status, complaint_id)
    )
    # Add history entry
    admin_name = session.get('name', 'Admin')
    db_execute(db,
        "INSERT INTO complaint_history (complaint_id, user_id, action) VALUES (?, ?, ?)",
        (complaint_id, session['user_id'], admin_name + ' changed status to ' + new_status)
    )
    db.commit()
    flash('Status updated.', 'success')
    return redirect(url_for('admin_dashboard'))


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
