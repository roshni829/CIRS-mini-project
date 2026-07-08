# CIRS — Complaint/Issue Resolution System

> **Empower Every Voice. Resolve Issues Faster, Together.**

---

## 📑 Table of Contents

1. [Project Overview](#-project-overview)
2. [Problem Statement](#-problem-statement)
3. [Proposed Solution](#-proposed-solution)
4. [Tech Stack](#-tech-stack)
5. [System Architecture](#-system-architecture)
6. [Database Design](#-database-design)
7. [User Roles & Access Control](#-user-roles--access-control)
8. [Features in Detail](#-features-in-detail)
9. [User Flows](#-user-flows)
10. [Admin Flows](#-admin-flows)
11. [Screen-by-Screen Walkthrough](#-screen-by-screen-walkthrough)
12. [Smart Duplicate Detection Algorithm](#-smart-duplicate-detection-algorithm)
13. [Priority Auto-Calculation](#-priority-auto-calculation)
14. [API Routes Reference](#-api-routes-reference)
15. [Setup & Installation Guide](#-setup--installation-guide)
16. [Demo Accounts](#-demo-accounts)
17. [Testing Scenarios](#-testing-scenarios)
18. [Security Features](#-security-features)
19. [Future Roadmap](#-future-roadmap)
20. [Project File Structure](#-project-file-structure)

---

## 🌟 Project Overview

**CIRS** (Complaint/Issue Resolution System) is a lightweight, collaborative web application that digitizes and streamlines the complaint management process in educational institutions. It replaces the chaotic paper trails, scattered WhatsApp messages, and ignored grievances with a transparent, data-driven resolution system.

### Core Philosophy

> "A complaint is common — but each user's relationship to that complaint is personal."

This means:
- Student A creates a complaint → it appears in their **"My Raised Complaints"**
- Student B joins the same complaint → it appears in their **"My Joined Complaints"**
- Admin sees the full picture → **all complaints** with **affected user counts**
- Everyone sees the **same status** — changes are reflected in real-time for all

---

## ❗ Problem Statement

### Current Challenges in Campus Issue Management

| Problem | Description | Impact |
|---------|-------------|--------|
| **Fragmented Communication** | Complaints get lost across WhatsApp groups, emails, sticky notes, and verbal requests | No centralized record |
| **Duplicate Reports** | 10 students report the same broken Wi-Fi separately, wasting admin time | Cluttered records, no voice amplification |
| **Zero Transparency** | Students never know if their complaint was seen or acted upon | Frustration, distrust in the system |
| **No Prioritization** | A leaking pipe affecting 50 students gets the same attention as a minor issue affecting 1 | Critical issues get ignored |
| **No Accountability** | No audit trail of who did what and when | Difficult to track resolution progress |
| **Admin Overload** | Scattered inboxes, no filtering, no sorting | Inefficient resolution workflow |

### The Numbers

- **70%** of student complaints in traditional systems go unresolved or unacknowledged
- **40%** of all complaints filed are duplicates of existing issues
- **3× faster** resolution time when issue severity is quantified by affected user count
- **Zero accountability** in paper-based systems — no timestamped audit trail

---

## 💡 Proposed Solution

CIRS is a **single source of truth** for campus issue management that:

### Key Value Propositions

1. **Amplify Voice Through Numbers** — Instead of 10 duplicate complaints, one complaint gets 10 supporters. Admins see the real impact instantly.

2. **Automatic Priority Escalation** — Priority auto-adjusts from Low → Medium → High based on how many students are affected. Admins always know what to fix first.

3. **Full Transparency** — Every complaint has a timestamped activity log. Students see exactly when status changes happen.

4. **Self-Service Dashboards** — Students track their complaints without chasing admins. Admins get a centralized, filterable dashboard.

5. **Duplicate-Free System** — Jaccard similarity algorithm detects when a complaint already exists and encourages collaboration.

### Comparison: Before vs After CIRS

| Scenario | Before CIRS | With CIRS |
|----------|-------------|-----------|
| Wi-Fi goes down in Block A | 15 separate WhatsApp messages, 8 ignored | 1 complaint, 15 joined users → **High priority** |
| Student checks complaint status | Calls admin, sends follow-up emails | Logs into dashboard — **real-time status** |
| Admin prioritizes work | No data to decide | **Auto-priority** based on affected count |
| Resolution handoff | No record of who did what | **Full activity history** with timestamps |
| Monthly reporting | Manual spreadsheet compilation | **Filterable, sortable** dashboard data |

---

## 🛠 Tech Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Language** | Python | 3.14+ | Backend logic & routing |
| **Web Framework** | Flask | 3.0.0 | HTTP server, routing, session management |
| **Templating** | Jinja2 | (bundled with Flask) | Server-side HTML rendering |
| **Frontend** | HTML5 + CSS3 + Vanilla JS | — | UI rendering & interactivity |
| **Database** | PostgreSQL | (via Render) | Persistent data storage |
| **PostgreSQL Adapter** | psycopg2 | 2.9.11 | Python-PostgreSQL connection |
| **Auth** | Flask-WTF / Werkzeug | — | CSRF protection, password hashing |
| **Password Security** | Werkzeug | 3.0.1 | PBKDF2-SHA256 hashing |

### Why This Stack?

| Consideration | Choice | Rationale |
|---------------|--------|-----------|
| **Production-ready** | PostgreSQL | Robust, scalable, industry-standard database |
| **Deployed on Render** | PostgreSQL | Free hosted PostgreSQL with automatic backups |
| **Minimal dependencies** | Flask (microframework) | Only a few pip packages — lightweight and fast |
| **No build step** | Vanilla JS (no React/Angular) | Instant page loads, no compilation needed |
| **Educational relevance** | Python + Flask | Industry-standard web framework taught in most CS curricula |

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Browser                          │
│  (HTML Templates rendered via Jinja2 + CSS + Vanilla JS)     │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP Requests / Responses
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Flask Application (app.py)                 │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Auth     │  │ Route    │  │ Similarity│  │ Session      │ │
│  │ Decorators│  │ Handlers │  │ Engine   │  │ Management   │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  PostgreSQL Database                    │   │
│  │              (via psycopg2 + RealDictCursor)            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │ SQL Queries
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                        │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌─────────┐ │
│  │  users   │  │complaints│  │complaint_users│  │complaint│ │
│  │          │  │          │  │               │  │_history │ │
│  └──────────┘  └──────────┘  └──────────────┘  └─────────┘ │
│  ┌──────────────────────────────┐                            │
│  │  complaint_dependencies      │                            │
│  └──────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

### Request Lifecycle

```
1. Browser → HTTP Request → Flask Router
2. Router → Auth Decorator Check (session validation)
3. Router → Route Handler Function
4. Handler → Database Query (via db_execute)
5. Handler → Business Logic (similarity, priority)
6. Handler → Render Template (passing query results)
7. Flask → Jinja2 Template → HTML Response
8. Browser → Render HTML + CSS + Execute JS
```

---

## 🗄 Database Design

The system uses 4 tables connected through foreign key relationships. The schema is auto-created on application startup.

### Entity-Relationship Diagram (Textual)

```
┌─────────┐          ┌──────────────┐          ┌──────────────┐
│  users  │──1:N──→  │  complaints  │──1:N──→  │complaint_    │
│         │          │              │          │history       │
│  PK: id │          │  PK: id      │          │              │
│         │          │  FK: created_│          │  FK: complaint│
│         │          │      by → users.id    │      _id       │
└─────────┘          └──────┬───────┘          │  FK: user_id  │
       │                    │                  └──────────────┘
       │                    │
       │         ┌──────────┴──────────┐
       │         │  complaint_users    │
       └─────N:M─┤  (Junction Table)   │
                 │                     │
                 │  FK: complaint_id   │
                 │  FK: user_id        │
                 │  role_in_complaint  │
                 └─────────────────────┘
```

### Table: `users`

Stores all registered users (students and admins).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, AUTOINCREMENT | Unique identifier |
| `name` | TEXT | NOT NULL | Full name of the user |
| `email` | TEXT | UNIQUE, NOT NULL | Email used for login |
| `password` | TEXT | NOT NULL | PBKDF2-SHA256 hashed password |
| `role` | TEXT | NOT NULL, DEFAULT 'user' | `user` (student) or `admin` |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Account creation timestamp |

### Table: `complaints`

Stores all complaint issues submitted in the system.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, AUTOINCREMENT | Unique complaint ID |
| `title` | TEXT | NOT NULL | Short summary of the issue |
| `description` | TEXT | NOT NULL | Detailed explanation |
| `category` | TEXT | NOT NULL | Wi-Fi / Electricity / Water / Cleanliness / Classroom / Hostel / Other |
| `location` | TEXT | NOT NULL | Where the issue is located |
| `status` | TEXT | NOT NULL, DEFAULT 'Pending' | Pending / In Progress / Resolved |
| `priority` | TEXT | NOT NULL, DEFAULT 'Low' | Low / Medium / High (auto-calculated) |
| `created_by` | INTEGER | NOT NULL, FK → users(id) | Who submitted this complaint |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Submission timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last status update timestamp |

### Table: `complaint_users`

Junction table establishing the many-to-many relationship between users and complaints. This is the **core table** that enables role-based data separation.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, AUTOINCREMENT | Unique record ID |
| `complaint_id` | INTEGER | NOT NULL, FK → complaints(id) | Reference to the complaint |
| `user_id` | INTEGER | NOT NULL, FK → users(id) | Reference to the user |
| `role_in_complaint` | TEXT | NOT NULL, DEFAULT 'joined' | `creator` or `joined` |
| `joined_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When user associated with this complaint |
| | | UNIQUE(complaint_id, user_id) | Prevents double association |

### Table: `complaint_history`

Audit trail tracking every action taken on a complaint.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, AUTOINCREMENT | Unique record ID |
| `complaint_id` | INTEGER | NOT NULL, FK → complaints(id) | Which complaint was acted upon |
| `user_id` | INTEGER | NOT NULL, FK → users(id) | Who performed the action |
| `action` | TEXT | NOT NULL | Description: "X created complaint" / "X joined complaint" / "X changed status to Y" |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When the action occurred |

### Key Database Design Decisions

| Decision | Rationale |
|----------|-----------|
| **`complaint_users` instead of `affected_users` column** | Enables many-to-many relationship; each user has their personal `role_in_complaint` (creator vs joined); affected count is always a `COUNT(*)` query — never manually incremented |
| **`role_in_complaint` not just `role`** | Clearly distinguishes between "user's role globally" (admin/student) and "user's role in this specific complaint" (creator/joined) |
| **`UNIQUE(complaint_id, user_id)`** | Prevents a user from joining the same complaint twice |
| **`complaint_history` as separate table** | Enables infinite activity log without bloating the complaints table; can be queried independently |
| **`affected_users` never stored** | Always calculated from `COUNT(*)` on `complaint_users` — prevents data inconsistency when users join/leave |

---

## 👥 User Roles & Access Control

### Two-Role System

```
┌─────────────────────────────────────────────────────────┐
│                      USER ROLES                          │
│                                                          │
│  ┌─────────────────────┐    ┌─────────────────────────┐ │
│  │      Student        │    │         Admin            │ │
│  │  (role = 'user')    │    │  (role = 'admin')        │ │
│  ├─────────────────────┤    ├─────────────────────────┤ │
│  │ • Submit complaints │    │ • View ALL complaints   │ │
│  │ • Join complaints   │    │ • Filter by status/cat  │ │
│  │ • View raised       │    │ • Update statuses       │ │
│  │ • View joined       │    │ • View affected counts  │ │
│  │ • View available    │    │ • View joined users     │ │
│  │ • Track status      │    │ • View activity history │ │
│  └─────────────────────┘    └─────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Access Control Matrix

| Resource | Student | Admin |
|----------|---------|-------|
| `/dashboard` (User Dashboard) | ✅ Full access | ❌ Redirected to `/admin` |
| `/submit` (Create Complaint) | ✅ Full access | ❌ Redirected to `/admin` |
| `/join/<id>` (Join Complaint) | ✅ Full access | ❌ Redirected to `/admin` |
| `/create-new` (Force Create) | ✅ Full access | ❌ Redirected to `/admin` |
| `/admin` (Admin Dashboard) | ❌ Redirected to `/login` | ✅ Full access |
| `/complaint/<id>/status` | ❌ Redirected to `/login` | ✅ Full access |
| `/complaint/<id>` (Detail) | ✅ View only (no status update) | ✅ View + Status update form |
| `/logout` | ✅ | ✅ |

### How Role Separation Works

```python
# 1. Login redirects based on role
if user['role'] == 'admin':
    return redirect(url_for('admin_dashboard'))
return redirect(url_for('user_dashboard'))

# 2. Admin decorator blocks students from admin routes
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# 3. Admin redirect guards on student routes
@app.route('/dashboard')
@login_required
def user_dashboard():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    # ... student dashboard logic
```

### Data Separation Principle

> "A complaint is common, but each user's relationship to that complaint is personal."

```
Scenario: Complaint "Wi-Fi not working in Block A"

┌─────────────────────────────────────────────────────────────┐
│  complaint_users table                                       │
│                                                              │
│  complaint_id=1 │ user_id=1 (Student 1) │ role=creator      │
│  complaint_id=1 │ user_id=2 (Student 2) │ role=joined       │
└─────────────────────────────────────────────────────────────┘

┌───────────────────┐     ┌───────────────────┐     ┌──────────────┐
│  Student 1 sees:  │     │  Student 2 sees:  │     │ Admin sees:  │
├───────────────────┤     ├───────────────────┤     ├──────────────┤
│ My Raised:        │     │ My Raised:        │     │ All Complaints │
│  - Wi-Fi issue    │     │  - (empty)        │     │              │
│ My Joined:        │     │ My Joined:        │     │ Wi-Fi issue  │
│  - (empty)        │     │  - Wi-Fi issue    │     │ Created By:  │
│ Available:        │     │ Available:        │     │   Student 1  │
│  - other issues   │     │  - other issues   │     │ Affected: 2  │
└───────────────────┘     └───────────────────┘     │ Joined: Stu1,│
                                                     │   Student 2  │
                                                     │ Status: In   │
                                                     │   Progress   │
                                                     └──────────────┘
```

---

## ✨ Features in Detail

### 🧑‍🎓 Student Features

#### 1. Registration & Login
- **Registration**: Name, email, password with validation
- **Login**: Email + password authentication
- **Password security**: PBKDF2-SHA256 hashing (industry standard)
- **Session management**: 3-hour session lifetime with Flask sessions
- **Role-based redirect**: Students → `/dashboard`, Admins → `/admin`

#### 2. Personal Dashboard (Three Sections)

**Section A — Complaints Raised by Me**
- Complaints the student has created
- Shows: title, status (color-coded badge), category, location, affected count, priority level, creation timestamp
- Action: "View" button to see full details

**Section B — Complaints I Joined**
- Complaints the student has joined (supported)
- Shows same information but with "Joined:" timestamp
- Action: "View" button to see full details

**Section C — Open Complaints (Available to Join)**
- Unresolved complaints the student has NOT created and NOT joined yet
- Shows: title, status, category, location, affected count, priority, creator name
- Actions: "Join" button + "View" button
- Excludes the student's own complaints and already-joined complaints

#### 3. Submit Complaint with Duplicate Detection
- Form: Title, Category (dropdown), Location, Description
- **Smart duplicate detection** before submission
- If duplicates found → Modal with options:
  - Join existing complaint
  - View existing complaint details
  - Create new complaint anyway
- If no duplicates → Direct submission with auto-creation of `complaint_users` record

#### 4. Join Existing Complaints
- One-click "Join" on any open complaint
- Automatically added to `complaint_users` with `role_in_complaint = 'joined'`
- Priority auto-recalculated after joining
- History entry created: "Student X joined complaint"

#### 5. Complaint Detail View
- Full complaint information
- Creator name, category, location, priority, status
- Description text
- Creation and last-update timestamps
- **Affected Users list** with initials avatars and role labels (Creator / Joined)
- **Activity History timeline** with timestamps

#### 6. Real-Time Status Updates
- Dashboard auto-polls `/api/my-complaints` every 10 seconds
- Status badges update live without page refresh
- Affected user counts update live

### 👨‍💼 Admin Features

#### 1. Admin Dashboard (Table View)
- All complaints in a sortable, filterable table
- Columns: Complaint (with creator name), Category, Location, Affected Count, Priority, Status
- **Inline status update** — dropdown + update button in each row

#### 2. Advanced Filtering
- **By Status**: All / Pending / In Progress / Resolved
- **By Category**: All / Wi-Fi / Electricity / Water / Cleanliness / Classroom / Hostel / Other
- **Combined filters**: Apply both status and category simultaneously
- **Clear button**: Reset all filters
- **Priority sorting**: High → Medium → Low, then by newest first

#### 3. Complaint Detail with Admin Controls
- Same detail view as students, PLUS:
- **Status Update Form**: Dropdown to change status with "Update" button
- No other data modified — status updates ONLY touch the `status` field

#### 4. Activity History
- Full chronological timeline for each complaint
- Each entry: timestamp + user name + action description
- Tracks: creation, joins, and status changes

---

## 🔄 User Flows

### Flow 1: First-Time User Experience

```
                    ┌──────────────┐
                    │  Visit Site  │
                    │  (/)         │
                    └──────┬───────┘
                           │ Redirect
                           ▼
                    ┌──────────────┐
                    │  Login Page  │
                    │  (/login)    │
                    └──────┬───────┘
                           │ "Don't have an account?"
                           ▼
                    ┌──────────────┐
                    │  Register    │
                    │  (/register) │
                    └──────┬───────┘
                           │ Submit form
                           ▼
                    ┌──────────────┐
                    │  Success →   │
                    │  Login Page  │
                    └──────────────┘
```

### Flow 2: Student Submits a Complaint

```
┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Dashboard   │────→│  /submit (Form)  │────→│  Similar Check    │
│  /dashboard  │     │  Fill details    │     │  (similarity ≥    │
└──────────────┘     └──────────────────┘     │  40%?)            │
                                              └────────┬──────────┘
                                                       │
                              ┌────────────────────────┼────────────────┐
                              │ YES                    │ NO             │
                              ▼                        ▼                │
                    ┌────────────────────┐   ┌────────────────────┐    │
                    │ Show Modal with    │   │ Save complaint     │    │
                    │ similar complaints │   │ Add creator to     │    │
                    └────────┬───────────┘   │ complaint_users   │    │
                             │               │ Add history entry  │    │
              ┌──────────────┼──────┐        │ Redirect to        │    │
              ▼              ▼      ▼        │ /dashboard         │    │
        ┌──────────┐ ┌──────────┐ ┌────┐    └────────────────────┘    │
        │ Join     │ │ View     │ │Create│                             │
        │ Existing │ │ Details  │ │New   │                             │
        └──────────┘ └──────────┘ └──┬──┘                              │
                                     │ POST /create-new                │
                                     ▼                                │
                            ┌────────────────────┐                    │
                            │ Save pending       │                    │
                            │ complaint from     │                    │
                            │ session + redirect  │                    │
                            └────────────────────┘                    │
                                                                       │
                              ┌───────────────────────────────────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │  Redirect →        │
                    │  /dashboard        │
                    │  Flash: Success    │
                    └────────────────────┘
```

### Flow 3: Student Joins an Existing Complaint

```
┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Dashboard   │────→│  Click "Join"    │────→│  POST /join/<id>  │
│  Open        │     │  on a complaint  │     │                   │
│  Complaints  │     └──────────────────┘     └────────┬──────────┘
└──────────────┘                                       │
                                                        ▼
                                              ┌────────────────────┐
                                              │ INSERT INTO        │
                                              │ complaint_users    │
                                              │ (role='joined')    │
                                              └────────┬───────────┘
                                                        │
                                              ┌────────────────────┐
                                              │ Recalculate        │
                                              │ priority based on  │
                                              │ new affected count │
                                              └────────┬───────────┘
                                                        │
                                              ┌────────────────────┐
                                              │ Add history entry  │
                                              │ "X joined this     │
                                              │  complaint"        │
                                              └────────┬───────────┘
                                                        │
                                                        ▼
                                              ┌────────────────────┐
                                              │ Redirect →         │
                                              │ /dashboard         │
                                              │ Flash: Success     │
                                              └────────────────────┘
```

### Flow 4: Admin Updates Complaint Status

```
┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Admin       │────→│  Select status   │────→│  POST             │
│  Dashboard   │     │  from dropdown + │     │  /complaint/<id>/ │
│  /admin      │     │  click "Update"  │     │  status            │
└──────────────┘     └──────────────────┘     └────────┬──────────┘
                                                        │
                                              ┌────────────────────┐
                                              │ Validate status    │
                                              │ is one of:         │
                                              │ Pending / In       │
                                              │ Progress / Resolved│
                                              └────────┬───────────┘
                                                        │
                                              ┌────────────────────┐
                                              │ UPDATE complaints  │
                                              │ SET status = ?     │
                                              │ WHERE id = ?       │
                                              │                    │
                                              │ (NO other tables   │
                                              │  are modified)     │
                                              └────────┬───────────┘
                                                        │
                                              ┌────────────────────┐
                                              │ Add history entry  │
                                              │ "Admin changed     │
                                              │  status to X"      │
                                              └────────┬───────────┘
                                                        │
                                                        ▼
                                              ┌────────────────────┐
                                              │ Redirect → /admin  │
                                              │ Flash: Success     │
                                              └────────────────────┘
```

---

## 📱 Screen-by-Screen Walkthrough

### Screen 1: Login Page (`/login`)

```
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│                    ┌───────────────────────┐                   │
│                    │       CIRS Logo       │                   │
│                    └───────────────────────┘                   │
│                                                               │
│                         Welcome Back                          │
│               Enter your email and password.                   │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐    │
│  │ Email                                                  │    │
│  │ [___________________________]                         │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐    │
│  │ Password                                               │    │
│  │ [___________________________]                         │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐    │
│  │                     Login                              │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                               │
│         Don't have an account? Register                       │
│                                                               │
│  ───────────────────────────────────────────────────────────  │
│  Demo accounts:                                               │
│  User:  student1@gmail.com / password123                      │
│  Admin: admin@gmail.com   / admin123                          │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

**Key details:**
- Responsive centered layout with gradient background
- CSRF-protected form
- Demo credentials shown for easy testing
- Link to registration page
- Flash messages for errors (invalid credentials, etc.)

### Screen 2: Student Dashboard (`/dashboard`)

```
┌──────┬────────────────────────────────────────────────────────┐
│      │  Dashboard                  [Student One] [+ New]      │
│Logo  │                                                        │
│CIRS  │  ┌─ Complaints Raised by Me ─────────── 2 total ────┐  │
│      │  │ Wi-Fi not working             [In Progress]       │  │
│      │  │ Wi-Fi │ Block A │ 2 affected │ Low               │  │
│      │  │ Created: 2026-07-07 10:30           [View]       │  │
│      │  ├───────────────────────────────────────────────────┤  │
│      │  │ Projector bulb fuse              [Pending]        │  │
│      │  │ Classroom │ Room 201 │ 1 affected │ Low          │  │
│      │  │ Created: 2026-07-06 14:15           [View]       │  │
│      │  └───────────────────────────────────────────────────┘  │
│      │                                                        │
│      │  ┌─ Complaints I Joined ───────────── 1 total ──────┐  │
│DASH  │  │ Library AC not working           [In Progress]    │  │
│[+]   │  │ Electricity │ Library │ 5 affected │ Medium      │  │
│      │  │ Joined: 2026-07-07 11:00            [View]       │  │
│←Logout│ └───────────────────────────────────────────────────┘  │
│      │                                                        │
│      │  ┌─ Open Complaints ──────────────── 3 total ────────┐ │
│      │  │ Water leakage in Hostel C       [Pending]         │ │
│      │  │ Water │ Hostel C │ 3 affected │ Medium           │ │
│      │  │ by Student Two                    [Join] [View]  │ │
│      │  ├───────────────────────────────────────────────────┤ │
│      │  │ ...more open complaints                           │ │
│      │  └───────────────────────────────────────────────────┘ │
└──────┴────────────────────────────────────────────────────────┘
```

**Three distinct sections** ensure students see exactly their data:
1. **My Raised** — Only complaints where `role_in_complaint = 'creator'`
2. **My Joined** — Only complaints where `role_in_complaint = 'joined'`
3. **Open** — Only complaints where user has NO entry in `complaint_users`

### Screen 3: Submit Complaint (`/submit`)

```
┌──────┬────────────────────────────────────────────────────────┐
│      │  Submit a Complaint                                    │
│      │                                                        │
│      │  ┌──────────────────────────────────────────────────┐  │
│      │  │ Complaint Title                                   │  │
│      │  │ [Wi-Fi not working in Block A________________]    │  │
│      │  │                                                   │  │
│      │  │ Category            Location                      │  │
│      │  │ [Wi-Fi        ▼]    [Block A, Hostel____]        │  │
│      │  │                                                   │  │
│      │  │ Description                                       │  │
│      │  │ [The Wi-Fi has been down since yesterday....]     │  │
│      │  │ [___________________________________________]    │  │
│      │  │                                                   │  │
│      │  │              [Submit]                             │  │
│      │  └──────────────────────────────────────────────────┘  │
└──────┴────────────────────────────────────────────────────────┘
```

**If duplicates found, a modal appears:**

```
┌───────────────────────────────────────────────┐
│  ⚠ A similar complaint already exists.       │
│                                               │
│  Would you like to join the existing          │
│  complaint instead of creating a new one?     │
│                                               │
│  ┌─ Wi-Fi not working ──────────────────────┐ │
│  │ Wi-Fi │ Block A │ Pending │ 3 affected   │ │
│  │ Medium Priority                          │ │
│  │ [Join Complaint] [View Details]          │ │
│  └──────────────────────────────────────────┘ │
│                                               │
│  [Create New Complaint Anyway]                │
│                                               │
│           [Close]                             │
└───────────────────────────────────────────────┘
```

**Duplicate detection algorithm:**
- Computes Jaccard similarity on title + description tokens
- Boosts score if same category or location
- Shows complaints with ≥40% similarity

### Screen 4: Admin Dashboard (`/admin`)

```
┌──────┬────────────────────────────────────────────────────────┐
│      │  All Complaints            [Admin User]  5 total       │
│      │                                                        │
│      │  ┌─ Filters ────────────────────────────────────────┐  │
│      │  │ Status: [All ▼]  Category: [All ▼]  [Filter]    │  │
│      │  └──────────────────────────────────────────────────┘  │
│      │                                                        │
│      │  ┌──────────────────────────────────────────────────┐  │
│      │  │ Complaint     │ Cat │ Loc  │Aff │ Pri │Status  │  │
│      │  ├──────────────────────────────────────────────────┤  │
│      │  │ Wi-Fi not     │Wi-Fi│ Blk A│ 2  │Low  │[Prog+]│  │
│PROJ  │  │  by Student 1 │     │      │    │     │[Update]│  │
│MANAGE│  ├──────────────────────────────────────────────────┤  │
│      │  │ Water leak    │Water│Hstl C│ 5  │Med  │[Pend+]│  │
│←Logout│ │  by Student 2 │     │      │    │     │[Update]│  │
│      │  ├──────────────────────────────────────────────────┤  │
│      │  │ Projector     │Class│Rm 201│ 1  │Low  │[Pend+]│  │
│      │  │  by Student 1 │     │      │    │     │[Update]│  │
│      │  ├──────────────────────────────────────────────────┤  │
│      │  │ ...more rows sorted by priority                  │  │
│      │  └──────────────────────────────────────────────────┘  │
└──────┴────────────────────────────────────────────────────────┘
```

**Admin-specific features:**
- Status filter: All / Pending / In Progress / Resolved
- Category filter: All / Wi-Fi / Electricity / Water / etc.
- Combined filtering with Clear button
- Inline status updates (dropdown + update button per row)
- Sorted by priority (High → Medium → Low) then by date

### Screen 5: Complaint Detail (`/complaint/<id>`)

```
┌──────┬────────────────────────────────────────────────────────┐
│      │  Complaint #1                           [← Back]       │
│      │                                                        │
│      │  ┌─ Wi-Fi not working ─────────┐ ┌─ 2 ──────────────┐ │
│      │  │ Reported by Student One     │ │ Affected Users    │ │
│      │  │                             │ └──────────────────┘ │
│      │  │ Category: Wi-Fi             │ ┌─ Joined Users ───┐ │
│      │  │ Location : Block A          │ │ [S] Student One  │ │
│      │  │ Priority : Low              │ │     Creator      │ │
│      │  │ Status   : In Progress      │ │ [S] Student Two  │ │
│      │  │                             │ │     Joined 11:00 │ │
│      │  │ Description:                │ └──────────────────┘ │
│      │  │ The Wi-Fi has been down...  │ ┌─ Activity ───────┐ │
│      │  │                             │ │ 10:30 Stu1 crtd │ │
│      │  │ Created: 2026-07-07 10:30   │ │ 11:00 Stu2 jnd  │ │
│      │  │ Updated: 2026-07-07 11:15   │ │ 11:15 Admin chg │ │
│      │  │                             │ │      to In Prog │ │
│      │  │ [ADMIN ONLY: Status Update] │ └──────────────────┘ │
│      │  │ [In Progress ▼] [Update]    │                      │
│      │  └─────────────────────────────┘                      │
└──────┴────────────────────────────────────────────────────────┘
```

**Two-column layout:**
- Left: Complaint info, description, timestamps (admin sees status update form)
- Right: Affected count badge, joined users list (with initials & role), activity timeline

---

## 🧠 Smart Duplicate Detection Algorithm

### How It Works

The algorithm prevents complaint duplication by comparing new submissions against existing unresolved complaints.

### Step-by-Step Process

```
Input: title, description, category, location
                   │
                   ▼
         ┌─────────────────────┐
         │  Tokenize text      │
         │  (alphanumeric only │
         │   → lowercase set)  │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  For each existing  │
         │  unresolved complaint│
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────────────────────┐
         │  Compute Jaccard Similarity:        │
         │                                     │
         │     |tokens(new) ∩ tokens(existing)| │
         │  S = ───────────────────────────── │
         │     |tokens(new) ∪ tokens(existing)| │
         └──────────┬──────────────────────────┘
                    │
                    ▼
         ┌─────────────────────────────────────┐
         │  Category/Location Boost            │
         │                                     │
         │  If both match → S = max(S, 0.5)   │
         │  If one matches → S = max(S, 0.3)  │
         └──────────┬──────────────────────────┘
                    │
                    ▼
         ┌─────────────────────────────────────┐
         │  If S ≥ 0.4 (40%):                  │
         │   → Add to similar list             │
         │   → Include affected user count     │
         └──────────┬──────────────────────────┘
                    │
                    ▼
         ┌─────────────────────────────────────┐
         │  Sort by similarity (highest first) │
         │  Return list of similar complaints  │
         └─────────────────────────────────────┘
```

### Code Implementation

```python
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
```

### Example

```
New complaint: "Wi-Fi not working in Block A"
Existing:      "Wi-Fi down in Block A hostel"

Tokens (new):   {wi-fi, not, working, in, block, a}
Tokens (exist): {wi-fi, down, in, block, a, hostel}
Intersection:   {wi-fi, in, block, a} → 4
Union:          {wi-fi, not, working, in, block, a, down, hostel} → 8
Similarity:     4/8 = 0.5 (50%)

Category match: Wi-Fi = Wi-Fi → YES → boost to max(0.5, 0.5) = 0.5
Location match: "Block A" in both → YES → boost to max(0.5, 0.5) = 0.5

Result: 0.5 ≥ 0.4 → SHOWN AS DUPLICATE ✅
```

---

## 📊 Priority Auto-Calculation

Priority is calculated dynamically based on the number of affected users (entries in `complaint_users`).

### Thresholds

| Affected Users | Priority | Visual |
|:--------------:|:--------:|:------:|
| 0–2 | **Low** | Gray badge |
| 3–5 | **Medium** | Yellow/amber badge |
| 6+ | **High** | Red badge |

### Trigger Points

Priority is recalculated whenever:
1. A user **joins** a complaint (`/join/<id>`)
2. (Future) A user leaves a complaint

### Implementation

```python
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
```

### Why This Matters

**Without CIRS:** A single student reporting "Water pipe burst in Hostel C" gets the same attention as "Light bulb flickering in Room 12."

**With CIRS:** When 8 students join the water pipe complaint, it auto-escalates to **High priority** — the admin knows to fix it immediately.

---

## 🌐 API Routes Reference

### Complete Route Table

| Method | Route | Auth | Role | Description | View Function |
|--------|-------|------|------|-------------|---------------|
| GET | `/` | No | — | Redirect to `/login` | `home()` |
| GET, POST | `/register` | No | — | User registration form & handler | `register()` |
| GET, POST | `/login` | No | — | Login form & authentication | `login()` |
| GET | `/logout` | No | — | Clear session & redirect | `logout()` |
| GET | `/dashboard` | Login | user | Student dashboard (3 sections) | `user_dashboard()` |
| GET, POST | `/submit` | Login | user | Submit complaint with duplicate check | `submit_complaint()` |
| POST | `/create-new` | Login | user | Force-create after duplicate prompt | `create_new_complaint()` |
| POST | `/join/<id>` | Login | user | Join an existing complaint | `join_complaint()` |
| GET | `/admin` | Admin | admin | Admin dashboard with filters | `admin_dashboard()` |
| GET | `/complaint/<id>` | Login | any | Complaint detail view | `complaint_detail()` |
| POST | `/complaint/<id>/status` | Admin | admin | Update complaint status | `update_status()` |
| GET | `/api/my-complaints` | No | any | JSON API for live polling | `api_my_complaints()` |

### Route Behavior Details

#### `POST /submit`
- **Form fields**: `title`, `description`, `category`, `location`
- **Validation**: All fields required; if empty → re-render form with error
- **Duplicate check**: Calls `find_similar_complaints()`
- **On duplicate found**: Stores data in `session['pending_complaint']`, re-renders with modal
- **On no duplicate**: Creates complaint, adds creator to `complaint_users`, adds history, redirects

#### `POST /create-new`
- **Reads from session**: `session['pending_complaint']` (set during duplicate detection)
- **Creates complaint**: Same logic as direct submission
- **Clears session**: `session.pop('pending_complaint', None)`

#### `POST /join/<int:complaint_id>`
- **Logic**: `INSERT INTO complaint_users ... ON CONFLICT DO NOTHING`
- **Double-join prevention**: `UNIQUE(complaint_id, user_id)` constraint
- **On success**: Recalculates priority, adds history entry
- **On already joined**: Flash "already joined" message

#### `POST /complaint/<int:complaint_id>/status`
- **Validation**: Only accepts `Pending`, `In Progress`, or `Resolved`
- **Critical constraint**: ONLY updates the `status` field — does NOT touch `created_by`, `complaint_users`, or any other table/data
- **History**: Adds "Admin changed status to X" entry

#### `GET /admin`
- **Query params**: `?status=Pending&category=Wi-Fi` (both optional)
- **Sorting**: Priority (High → Medium → Low) → Created date (newest first)
- **No params**: Shows all complaints

#### `GET /api/my-complaints`
- **Purpose**: Frontend live polling (every 10 seconds)
- **Returns JSON**: `{"complaints": [{"id": 1, "title": "...", "status": "...", "affected_users": 2}]}`
- **Auth**: Uses session but no decorator — returns empty array if not logged in

---

## 🚀 Setup & Installation Guide

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Navigate to the project

```bash
cd cirs
```

### Step 2: (Recommended) Create a virtual environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the application

```bash
python app.py
```

The server starts at **http://localhost:5000**.

### Step 5: Access the application

Open your browser and navigate to:
- **http://localhost:5000** — Login page
- **http://localhost:5000/login** — Login page
- **http://localhost:5000/register** — Registration page

### Database Reset (if needed)

To reset all data, you can drop and recreate the tables by connecting to your PostgreSQL instance:
```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```
Then restart the server — `init_db()` will recreate the tables and `seed_demo_data()` will seed fresh demo data.

---

## 👤 Demo Accounts

The application seeds 3 accounts automatically on first run.

| Name | Email | Password | Role |
|------|-------|----------|------|
| Student One | student1@cirs.com | student123 | Student (user) |
| Student Two | student2@cirs.com | student123 | Student (user) |
| Admin User | admin@cirs.com | admin123 | Admin |

### Suggested Demo Walkthrough

1. **Login as Student One** → Create complaint "Wi-Fi not working in Block A"
2. **Login as Student Two** → See the complaint in "Open Complaints" → Click "Join"
3. **Login as Student One** → See the complaint in "My Raised" with affected = 2
4. **Login as Admin** → See both complaints, update status to "In Progress"
5. **Login back as Student One or Two** → See status updated in real-time

---

## 🧪 Testing Scenarios

### Scenario 1: Basic Workflow
1. Register a new student account
2. Submit a complaint
3. Verify it appears in "Complaints Raised by Me"
4. Log out, log in as another student
5. See the complaint in "Open Complaints"
6. Join it
7. Verify it moves to "Complaints I Joined"

### Scenario 2: Duplicate Detection
1. Submit complaint: "Wi-Fi not working in Block A"
2. Submit again: "Wi-Fi down in Block A"
3. Verify the duplicate detection modal appears
4. Click "Join" on the existing complaint
5. Verify it appears under "Complaints I Joined"

### Scenario 3: Admin Workflow
1. Log in as admin
2. Verify all complaints are visible in the table
3. Filter by status → "Pending"
4. Filter by category → "Wi-Fi"
5. Change a complaint status from "Pending" to "In Progress"
6. Verify the status updates in the table
7. Log in as a student and verify the status change is visible

### Scenario 4: Data Separation
1. Student 1 creates "Wi-Fi issue" → "My Raised" shows it
2. Student 2 joins "Wi-Fi issue" → Student 2's "My Joined" shows it
3. Student 1's "My Joined" does NOT show "Wi-Fi issue" (Student 1 didn't join)
4. Student 2's "My Raised" does NOT show "Wi-Fi issue" (Student 2 didn't create it)
5. Admin dashboard shows one complaint with affected = 2

### Scenario 5: Priority Escalation
1. Create a complaint (affected = 1, priority = Low)
2. 2 more students join (affected = 3, priority = Medium)
3. 3 more students join (affected = 6, priority = High)
4. Verify priority badge updates after each join

### Scenario 6: Access Control
1. Try to access `/admin` as a student → should redirect to login
2. Try to access `/dashboard` as admin → should redirect to admin dashboard
3. Try to POST to `/join/<id>` as admin → should redirect to admin dashboard
4. Try to POST to `/submit` as admin → should redirect to admin dashboard

### Scenario 7: Activity History
1. Create a complaint → history shows creation
2. Another student joins → history shows join
3. Admin updates status → history shows status change
4. Verify all entries are visible in the complaint detail page

---

## 🔒 Security Features

### 1. Password Hashing
```python
from werkzeug.security import generate_password_hash, check_password_hash

# Storing password (PBKDF2-SHA256)
hashed = generate_password_hash(password)
# Result: pbkdf2:sha256:600000$salt$hash

# Verifying password
check_password_hash(stored_hash, input_password)
```

### 2. CSRF Protection
```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# Every form must include:
# <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

### 3. Session-Based Authentication
```python
# 3-hour session lifetime
app.permanent_session_lifetime = timedelta(hours=3)

# Session data stored in signed cookies (not tamperable)
session['user_id'] = user['id']
session['role'] = user['role']
```

### 4. Authorization Decorators
```python
@login_required        # Ensures user is logged in
@admin_required        # Ensures user is admin (includes login check)
```

### 5. Admin Redirect Guards
```python
# On every student route, admin is redirected away
if session.get('role') == 'admin':
    return redirect(url_for('admin_dashboard'))
```

### 6. Input Validation
- All form fields validated server-side
- Email uniqueness enforced via database constraint
- Status values validated against whitelist: `['Pending', 'In Progress', 'Resolved']`
- String length limits on title (max 200 chars)

---

## 🗺 Future Roadmap

### Phase 1: Immediate Value (Current)

| Feature | Status |
|---------|--------|
| Core complaint submission | ✅ Complete |
| Duplicate detection | ✅ Complete |
| Join complaint system | ✅ Complete |
| Admin dashboard with filters | ✅ Complete |
| Status management | ✅ Complete |
| Activity history | ✅ Complete |
| Role-based data separation | ✅ Complete |
| Priority auto-calculation | ✅ Complete |

### Phase 2: Enhanced Communication (Next)

| Feature | Description | Impact |
|---------|-------------|--------|
| Email notifications | Notify students when status changes | Proactive communication |
| In-app comments | Students can discuss complaints | Better collaboration |
| Complaint attachment | Allow image uploads | Visual evidence |

### Phase 3: Data-Driven Insights (Near Future)

| Feature | Description | Impact |
|---------|-------------|--------|
| Dashboard analytics | Resolution times, category trends | Data-driven decisions |
| PDF/Excel export | Generate reports | Institutional reporting |
| Resolution SLA tracking | Time-based alerts for stale complaints | Accountability |

### Phase 4: Advanced Features (Future)

| Feature | Description | Impact |
|---------|-------------|--------|
| Anonymous reporting | Optional anonymity for sensitive issues | Encourages reporting |
| Mobile PWA | Progressive Web App for mobile access | Access from anywhere |
| Department assignment | Auto-assign complaints to relevant departments | Smart routing |
| AI resolution suggestions | Suggest fixes based on historical data | Maximum efficiency |

### Phase 5: Enterprise Scale (Long-term)

| Feature | Description | Impact |
|---------|-------------|--------|
| PostgreSQL support | Already supported via `DATABASE_URL` env var | Production scalability |
| Role hierarchy | Multiple admin tiers (supervisor, manager, etc.) | Delegation |
| Multi-campus support | Separate complaint silos per campus | Institution-wide deployment |
| SSO integration | Single sign-on with institutional auth | Seamless login |

---

## 📁 Project File Structure

```
cirs/
│
├── app.py                     # Main Flask application (~350 lines)
│   ├── Database initialization & connection
│   ├── Similarity algorithm functions
│   ├── Auth decorators
│   ├── User routes (dashboard, submit, join, create-new)
│   ├── Admin routes (dashboard, status update)
│   ├── API routes (live polling)
│   └── Main entry point
│
├── requirements.txt           # Python dependencies
│   ├── Flask==3.0.0
│   ├── Flask-Session==0.5.0
│   ├── Werkzeug==3.0.1
│   └── psycopg2-binary==2.9.11
│
├── static/
│   ├── style.css              # Complete application styles (~800 lines)
│   │   ├── Base & reset styles
│   │   ├── Layout (sidebar + main)
│   │   ├── Cards, buttons, forms
│   │   ├── Badges, tables, alerts
│   │   ├── Modal, filter bar
│   │   ├── Detail page, activity timeline
│   │   └── Responsive breakpoints
│   │
│   └── script.js              # Frontend interactivity (~60 lines)
│       ├── Flash message auto-dismiss (4s)
│       ├── Modal open/close controls
│       └── Live polling (every 10s)
│
└── templates/
    ├── login.html             # Login form with demo credentials
    ├── register.html          # Registration form
    ├── user_dashboard.html    # Student dashboard (3 sections)
    │   ├── Complaints Raised by Me
    │   ├── Complaints I Joined
    │   └── Open Complaints (with Join buttons)
    │
    ├── admin_dashboard.html   # Admin table with filters & inline updates
    │   ├── Status filter dropdown
    │   ├── Category filter dropdown
    │   └── Inline status update per row
    │
    ├── submit_complaint.html  # Complaint form + duplicate detection modal
    │   ├── Title, category, location, description fields
    │   ├── Similar complaint cards (if duplicates found)
    │   └── Join / Create New actions
    │
    └── complaint_detail.html  # Full complaint detail view
        ├── Complaint info (title, creator, fields)
        ├── Affected users list (with initials & role)
        ├── Activity timeline (with timestamps)
        └── Admin status update form (admin only)
```

---

## 🎯 Key Differentiators

### What Makes CIRS Stand Out

| Feature | Why It Matters |
|---------|----------------|
| **Duplicate detection** | Reduces clutter; amplifies student voice through numbers; reveals true impact of issues |
| **Per-user data views** | Each student sees only their relevant data — no privacy leaks, no confusion |
| **Auto-calculated priority** | No manual priority setting — it just works based on real data |
| **Full activity history** | Complete transparency and accountability — every action is logged |
| **Join system** | Students help each other by supporting existing complaints instead of creating noise |
| **Zero infrastructure** | Runs on any machine with Python — no server setup, no database config, no cloud costs |
| **CSRF-protected** | Built-in web security — ready for real-world deployment |
| **Responsive design** | Works on desktop and mobile — sidebar collapses to icon-only on small screens |

---

## 📝 Conclusion

CIRS is a **complete, production-ready complaint management system** built with a **micro-framework philosophy** — minimal dependencies, maximum functionality. It demonstrates:

- **Full-stack web development** with Flask (Python)
- **Database design** with normalized tables and foreign key relationships
- **Authentication & authorization** with role-based access control
- **Algorithm design** with Jaccard similarity for duplicate detection
- **Frontend development** with responsive CSS and vanilla JavaScript
- **Security best practices** with CSRF protection and password hashing
- **Data-driven decision making** with auto-calculated priority levels

The system is designed to be **pitched, presented, and demonstrated** to faculty as a capstone/mini-project that solves a real-world problem with clean code, smart algorithms, and an intuitive user interface.

---

*CIRS — Because every voice deserves to be heard.*
