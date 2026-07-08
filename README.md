# CIRS — Complaint/Issue Resolution System

> **Empower every voice. Resolve issues faster, together.**

CIRS is a lightweight, collaborative complaint management platform designed for educational institutions. It replaces chaotic paper trails, scattered emails, and ignored grievances with a streamlined, transparent, and data-driven resolution system.

---

## 📈 Pitch Deck

### The Problem

In most colleges and hostels, issue reporting is broken:

- **Fragmented communication** — Complaints get lost in WhatsApp groups, email chains, and sticky notes.
- **Duplicate reports** — 10 students report the same broken Wi-Fi separately, wasting admin time.
- **No transparency** — Students never know if their complaint was even seen, let alone acted upon.
- **No prioritization** — A leaking pipe affecting 50 students gets the same attention as a minor issue affecting 1.
- **Zero accountability** — No audit trail of who did what and when.

### The Solution

CIRS is a **single source of truth** for campus issue management that:

- **Surface duplicates automatically** — Our Jaccard similarity algorithm detects when a complaint already exists and encourages students to join it instead of creating a new one. This amplifies voice through numbers.
- **Prioritizes by impact** — Priority auto-escalates from Low → Medium → High based on how many students are affected. Admins always know what to fix first.
- **Provides full transparency** — Every complaint has an activity log showing exactly when status changes happened and who made them.
- **Empowers students** — Users can join any open complaint to show they're affected. No more being ignored.
- **Streamlines admin workflow** — Filter by status and category, bulk-update statuses inline, and focus on what matters.

### Why CIRS?

| Problem | Before CIRS | With CIRS |
|---------|-------------|-----------|
| Duplicate complaints | 10 separate reports, no coordination | 1 complaint, 10 joined users — amplified voice |
| Priority awareness | Guesswork | Auto-calculated based on affected user count |
| Status tracking | Students chase admins | Self-service dashboard with real-time updates |
| Admin workload | Scattered inboxes | Centralized, filterable, sortable dashboard |
| Accountability | None | Full activity history with timestamps |

### Target Audience

- 🏫 **Colleges & Universities** — Hostel wardens, facilities departments, student affairs
- 🏢 **Corporate Campuses** — Office facility management teams
- 🏘️ **Residential Communities** — Apartment complexes, housing societies
- 🏨 **Hostels & Dormitories** — Student accommodation facilities

### Competitive Advantages

- **PostgreSQL-powered** — Production-ready database with auto-scaling on Render
- **Zero external API dependencies** — No API keys, no monthly subscriptions
- **CSRF-protected** — Built-in security against common web attacks
- **Dead simple deployment** — Set `DATABASE_URL`, `pip install -r requirements.txt`, `python app.py`

### Roadmap / Future Vision

| Phase | Feature | Impact |
|-------|---------|--------|
| 🟢 Now | Core submission, duplicate detection, admin management | Immediate value |
| 🔵 Soon | Email notifications on status changes | Proactive communication |
| 🟣 Next | Dashboard analytics (resolution times, category trends) | Data-driven decisions |
| 🟡 Later | Anonymous reporting option | Encourages sensitive reports |
| 🟠 Future | Mobile app / PWA | Access from anywhere |
| 🔴 Advanced | AI-powered auto-assignment and resolution suggestions | Maximum efficiency |

---

## Table of Contents

1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Database Schema](#database-schema)
5. [Features](#features)
   - [User Features](#user-features)
   - [Admin Features](#admin-features)
   - [Smart Duplicate Detection](#smart-duplicate-detection)
6. [Setup & Installation](#setup--installation)
7. [Running the Application](#running-the-application)
8. [Demo Accounts](#demo-accounts)
9. [Application Routes](#application-routes)
10. [How It Works](#how-it-works)
11. [API / Route Details](#api--route-details)
12. [Contributing / Development](#contributing--development)
13. [License](#license)

---

## Overview

**CIRS** (Complaint/Issue Resolution System) is a lightweight, self-contained web application that allows students to:

- Submit complaints (Wi-Fi, Electricity, Water, Cleanliness, Classroom, Hostel, Other)
- Find and join existing complaints instead of creating duplicates
- Track the status of their complaints (Pending → In Progress → Resolved)
- See how many other students are affected by the same issue

Administrators can:

- View all complaints with filtering by status and category
- Update complaint statuses
- See affected user counts with auto-calculated priority levels
- View complaint history/activity logs

The system uses **text similarity matching** to automatically detect duplicate complaints when a user submits a new one, encouraging collaboration over duplicate submissions.

---

## Tech Stack

| Technology   | Version    | Purpose                        |
|--------------|------------|--------------------------------|
| Python       | 3.14+      | Application logic              |
| Flask        | 3.0.0      | Web framework                  |
| Werkzeug     | 3.0.1      | Password hashing & utilities   |
| Flask-WTF    | (bundled)  | CSRF protection                |
| PostgreSQL   | —          | Database (via Render)          |
| psycopg2     | 2.9.11     | PostgreSQL adapter             |
| HTML5/CSS3   | —          | Frontend templates (Jinja2)    |
| Vanilla JS   | —          | Client-side interactivity      |

### Dependencies (from `requirements.txt`)

```
Flask==3.0.0
Flask-Session==0.5.0
Werkzeug==3.0.1
psycopg2-binary==2.9.11
```

---

## Project Structure

```
cirs/                           # Main application package
├── app.py                      # Flask application (routes, DB, auth, logic)
├── requirements.txt            # Python dependencies
├── flask_out.txt               # Server log output
├── flask_pid.txt               # Server process ID
├── static/
│   ├── style.css               # All application styles
│   └── script.js               # Frontend JavaScript (flash messages, modals)
└── templates/
    ├── login.html              # Login page
    ├── register.html           # Registration page
    ├── user_dashboard.html     # Student dashboard
    ├── admin_dashboard.html    # Admin dashboard
    ├── submit_complaint.html   # Complaint submission form + similar complaints modal
    └── complaint_detail.html   # Detailed view of a single complaint
```

---

## Database Schema

The application uses **PostgreSQL** with 5 tables (`users`, `complaints`, `complaint_users`, `complaint_history`, `complaint_dependencies`), all auto-created on first run via `init_db()`.

### `users`

| Column     | Type      | Constraints              | Description              |
|------------|-----------|--------------------------|--------------------------|
| id         | INTEGER   | PRIMARY KEY AUTOINCREMENT | Unique user ID           |
| name       | TEXT      | NOT NULL                 | Full name                |
| email      | TEXT      | UNIQUE NOT NULL          | Email (login credential) |
| password   | TEXT      | NOT NULL                 | Hashed password          |
| role       | TEXT      | NOT NULL DEFAULT 'user'  | `user` or `admin`        |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation time    |

### `complaints`

| Column      | Type      | Constraints              | Description                      |
|-------------|-----------|--------------------------|----------------------------------|
| id          | INTEGER   | PRIMARY KEY AUTOINCREMENT | Unique complaint ID              |
| title       | TEXT      | NOT NULL                 | Short title of the issue         |
| description | TEXT      | NOT NULL                 | Detailed description             |
| category    | TEXT      | NOT NULL                 | Wi-Fi, Electricity, Water, etc.  |
| location    | TEXT      | NOT NULL                 | Where the issue is located       |
| status      | TEXT      | NOT NULL DEFAULT 'Pending' | Pending / In Progress / Resolved |
| priority    | TEXT      | NOT NULL DEFAULT 'Low'   | Low / Medium / High              |
| created_by  | INTEGER   | NOT NULL                 | FK → users.id                    |
| created_at  | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time                    |
| updated_at  | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time                 |

### `complaint_users` (Many-to-Many join table)

| Column       | Type      | Constraints                          | Description                        |
|--------------|-----------|--------------------------------------|------------------------------------|
| id           | INTEGER   | PRIMARY KEY AUTOINCREMENT            | Unique record ID                   |
| complaint_id | INTEGER   | NOT NULL                             | FK → complaints.id                 |
| user_id      | INTEGER   | NOT NULL                             | FK → users.id                      |
| role         | TEXT      | NOT NULL DEFAULT 'joined'            | `creator` or `joined`              |
| joined_at    | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP            | When the user joined               |
|              |           | UNIQUE(complaint_id, user_id)        | Prevents duplicate joins           |

### `complaint_history` (Activity Log)

| Column       | Type      | Constraints              | Description                     |
|--------------|-----------|--------------------------|---------------------------------|
| id           | INTEGER   | PRIMARY KEY AUTOINCREMENT | Unique record ID                |
| complaint_id | INTEGER   | NOT NULL                 | FK → complaints.id              |
| user_id      | INTEGER   | NOT NULL                 | FK → users.id (who acted)       |
| action       | TEXT      | NOT NULL                 | Description of the action taken |
| created_at   | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When the action occurred        |

---

## Features

### User Features

- **Registration & Login** — Sign up with name, email, and password. Passwords are hashed with Werkzeug.
- **Dashboard** — Three sections:
  1. **Complaints Raised by Me** — Complaints the user created.
  2. **Complaints I Joined** — Complaints the user joined (supported).
  3. **Open Complaints** — Unresolved complaints the user hasn't yet joined, with a "Join" button.
- **Submit Complaint** — Form with title, category (dropdown), location, and description.
- **Duplicate Detection** — Before a complaint is submitted, the system checks for similar unresolved complaints using text similarity, category/location matching.
  - If similar complaints are found (≥40% similarity), a modal appears showing them.
  - The user can **join** an existing complaint instead of creating a new one, or proceed to create anyway.
- **Join Complaints** — Users can join any open complaint to show they're affected.
- **View Complaint Details** — See full info, affected users list, and activity history.
- **Priority Auto-Calculation** — Priority automatically updates based on affected user count:
  - 0–2 affected → **Low**
  - 3–5 affected → **Medium**
  - 6+ affected → **High**

### Admin Features

- **Admin Dashboard** — Table view of all complaints with:
  - Status filtering (Pending / In Progress / Resolved)
  - Category filtering (Wi-Fi, Electricity, Water, etc.)
  - Combined filters with "Clear" button
  - Sorting by priority (High → Medium → Low) then by creation date
- **Inline Status Updates** — Change complaint status directly from the table via dropdown.
- **Complaint Detail View** — Same as user view but with an additional status update form.
- **Activity Log** — View full history of actions on each complaint.

### Smart Duplicate Detection

The similarity algorithm works as follows:

1. **Tokenization** — Both the new complaint's title+description and each existing complaint's title+description are broken into lowercase alphanumeric tokens.
2. **Jaccard Similarity** — `|common_tokens| / |total_tokens|` is computed.
3. **Category/Location Boost** — If both category and location match, similarity is boosted to at least 50%. If one matches, it's boosted to at least 30%.
4. **Threshold** — Complaints with ≥40% similarity are shown as duplicates.
5. **Exclusion** — Resolved complaints are excluded from duplicate matching.

---

## Setup & Installation

### Prerequisites

- **Python 3.14+** (3.8+ should also work)
- **pip** (Python package installer)

### Step 1: Clone or navigate to the project

```bash
cd cirs
```

### Step 2: Create a virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running the Application

Set your `DATABASE_URL` environment variable to your PostgreSQL connection string, then:

```bash
set DATABASE_URL=postgresql://user:password@host:port/dbname
python app.py
```

The server will start on **http://localhost:5000** (available on all network interfaces).

On first run, the application will:
1. Auto-create all 5 PostgreSQL tables (`CREATE TABLE IF NOT EXISTS`).
2. Seed demo accounts and complaints (see below).

> **Note:** This app requires PostgreSQL. Set the `DATABASE_URL` environment variable to your Render PostgreSQL connection string before starting.

### Stopping the server

Press `Ctrl+C` in the terminal.

---

## Demo Accounts

The application seeds the following accounts automatically on first run.

| Role  | Email               | Password     | Name          |
|-------|---------------------|--------------|---------------|
| User  | student1@cirs.com   | student123   | Student One   |
| User  | student2@cirs.com   | student123   | Student Two   |
| Admin | admin@cirs.com      | admin123     | Admin User    |

You can also **register new accounts** from the login page.

---

## Application Routes

| Route                          | Method   | Auth Required | Role    | Description                         |
|--------------------------------|----------|---------------|---------|-------------------------------------|
| `/`                            | GET      | No            | —       | Redirects to /login                 |
| `/register`                    | GET/POST | No            | —       | User registration                   |
| `/login`                       | GET/POST | No            | —       | User login                          |
| `/logout`                      | GET      | No            | —       | Logout & clear session              |
| `/dashboard`                   | GET      | Yes           | user    | User dashboard                      |
| `/submit`                      | GET/POST | Yes           | user    | Submit new complaint                |
| `/create-new`                  | POST     | Yes           | user    | Force-create after duplicate prompt |
| `/join/<complaint_id>`         | POST     | Yes           | user    | Join an existing complaint          |
| `/admin`                       | GET      | Yes           | admin   | Admin dashboard with filters        |
| `/complaint/<complaint_id>`    | GET      | Yes           | any     | Complaint detail view               |
| `/complaint/<id>/status`       | POST     | Yes           | admin   | Update complaint status             |

---

## How It Works

### Authentication Flow

1. User visits `/login` or `/register`.
2. On successful login, user ID, name, email, and role are stored in Flask session.
3. Protected routes check `session['user_id']` via the `@login_required` decorator.
4. Admin routes additionally check `session['role'] == 'admin'` via `@admin_required`.
5. Logout clears the session.

### Complaint Submission Flow

1. User fills out the complaint form at `/submit`.
2. On POST, the system calls `find_similar_complaints()` to check for duplicates.
3. **If similar complaints found** — The form re-renders with a modal overlay showing similar complaints. The complaint data is stored in `session['pending_complaint']`.
   - User can click **"Join Complaint"** → joins the existing complaint.
   - User can click **"Create New Complaint Anyway"** → posts to `/create-new` which reads from `session['pending_complaint']`.
   - User can click **"View Details"** → views the existing complaint.
4. **If no similar complaints** — The complaint is saved directly with:
   - Creator automatically added to `complaint_users` with role `creator`.
   - History entry created.
   - Priority set to `Low` initially.

### Priority Calculation

When a user joins a complaint, `update_priority()` recalculates:
- **High** — 6 or more affected users
- **Medium** — 3 to 5 affected users
- **Low** — 0 to 2 affected users

### Admin Filtering

The admin dashboard supports query string filtering:
- `?status=Pending` — Filter by status
- `?category=Wi-Fi` — Filter by category
- `?status=Pending&category=Wi-Fi` — Combined filters
- No query params = show all

---

## API / Route Details

### `POST /register`

**Form fields:**
- `name` — Full name (required)
- `email` — Email address (required, must be unique)
- `password` — Password (required)

**Validation:** Checks for empty fields, duplicate email. On success, redirects to `/login` with a success flash message.

### `POST /login`

**Form fields:**
- `email` — Email address (required)
- `password` — Password (required)

**Validation:** Checks credentials against hashed password. On success, sets session variables and redirects:
- Admin → `/admin`
- User → `/dashboard`

### `POST /submit`

**Form fields:**
- `title` — Complaint title (required, max 200 chars)
- `description` — Detailed description (required)
- `category` — One of: Wi-Fi, Electricity, Water, Cleanliness, Classroom, Hostel, Other
- `location` — Location string (required)

**Returns:** Either redirects to `/dashboard` on success, or re-renders the form with a similar-complaint modal.

### `POST /create-new`

No form fields. Reads `session['pending_complaint']` (set during a previous `/submit` attempt with duplicates found). Creates the complaint and redirects to `/dashboard`.

### `POST /join/<complaint_id>`

No form fields. Adds the current user to `complaint_users` with role `joined`. Recalculates priority. Redirects to `/dashboard`.

### `POST /complaint/<id>/status`

**Form fields:**
- `status` — One of: `Pending`, `In Progress`, `Resolved`

**Validation:** Only admin users can access. Validates status is one of the three allowed values. Creates history entry. Redirects to `/admin`.

---

## Frontend Details

### Styling (`static/style.css`)

- **Layout:** Flexbox-based sidebar + main content area.
- **Responsive:** On screens ≤768px, the sidebar collapses to icon-only (56px width).
- **Color palette:** Neutral grays with blue (`#2563eb`) as primary action color.
- **Components:** Cards, buttons (primary/success/danger variants), badges (status/priority), modals, filter bars, tables, alerts, form controls.
- **Typography:** Segoe UI with system font fallbacks, 14px base size.

### JavaScript (`static/script.js`)

- **Flash message auto-dismiss:** Alerts fade out after 4 seconds.
- **Modal control:** Open/close by ID, close on overlay click, close via `.close-modal` buttons.
- **No external dependencies** — Pure vanilla JavaScript.

### Templates (Jinja2)

All templates use:
- **CSRF protection** — Every form includes `{{ csrf_token() }}`.
- **Flash messages** — Displayed via `get_flashed_messages(with_categories=true)`.
- **Session info** — User name displayed in sidebar footer and top bar.
- **Dynamic badges** — Color-coded by status and priority using CSS classes.

---

## CSRF Protection

The application uses **Flask-WTF** CSRF protection. Every form must include:

```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

All POST routes are CSRF-protected. This applies to:
- Login / Register forms
- Complaint submission
- Joining complaints
- Status updates

---

## Database

- **Engine:** PostgreSQL (hosted on Render)
- **Connection:** Via `DATABASE_URL` environment variable
- **Auto-creation:** Tables are created on application startup via `init_db()` (uses `CREATE TABLE IF NOT EXISTS`).
- **Demo data:** Seeded on first run via `seed_demo_data()` (checks if any users exist first).
- **Persistence:** Data survives restarts and redeploys — the PostgreSQL database is a separate service on Render.

To reset the database: connect to your PostgreSQL instance and run:
```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```
Then restart the server.

---

## Security Notes

- **Passwords** are hashed using Werkzeug's `generate_password_hash()` (PBKDF2-SHA256).
- **CSRF protection** on all forms.
- **Session-based auth** with Flask's signed session cookies.
- **Secret key** generated randomly at startup via `os.urandom(24).hex()`.
- **Note:** The current configuration uses a development server. For production, use a proper WSGI server (Gunicorn, Waitress, etc.) and set a fixed secret key.

---

## Contributing / Development

### Adding a new category

In `app.py`, the categories are hardcoded in:
1. The `/submit` route template (the `<select>` dropdown options).
2. The admin filter dropdown in `admin_dashboard.html`.
3. The `category_filter` logic in the admin route.

### Modifying the similarity threshold

In `app.py`, change the threshold in `find_similar_complaints()`:

```python
if sim >= 0.4:  # Change 0.4 to your desired threshold (0.0 - 1.0)
```

### Adding a new priority tier

1. Update `calculate_priority()` in `app.py`.
2. Add corresponding badge styling in `style.css`.
3. Update all badge rendering in templates.

---

## License

This project is provided for educational and demonstration purposes.
