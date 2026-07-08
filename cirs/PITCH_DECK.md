# CIRS — Complaint/Issue Resolution System
## 🎯 One-Page Executive Pitch Deck

---

## ❗ The Problem

In colleges and hostels, issue reporting is broken:

| Issue | Impact |
|-------|--------|
| 🗣️ **Fragmented communication** | Complaints lost in WhatsApp groups, emails, sticky notes |
| 🔁 **Duplicate reports** | 10 students report the same issue separately → wasted admin time |
| 👁️ **Zero transparency** | Students never know if their complaint was seen or acted upon |
| 📊 **No prioritization** | A leaking pipe affecting 50 students = same priority as a flickering bulb |
| 📝 **No accountability** | No audit trail of who did what and when |

---

## 💡 The Solution — CIRS

**A lightweight, collaborative complaint management platform** that replaces chaos with a transparent, data-driven resolution system.

### Core Innovation

> *"A complaint is common, but each user's relationship to that complaint is personal."*

The system treats complaints as shared issues while keeping **each user's view private**:

| User | Sees |
|------|------|
| **Student 1** (creator) | "Wi-Fi not working" under **My Raised Complaints** |
| **Student 2** (joined) | Same complaint under **My Joined Complaints** |
| **Admin** | One complaint with **affected users = 2**, status controls |

---

## ✨ Key Features

### 🧑‍🎓 For Students
| Feature | How It Works |
|---------|-------------|
| **Submit complaints** | Title, category, location, description |
| **Smart duplicate detection** | Jaccard similarity algorithm (~40% threshold) catches duplicates → join instead of re-reporting |
| **Join complaints** | One-click to show you're affected → amplifies voice through numbers |
| **Personal dashboard** | 3 sections: Raised / Joined / Available — each student sees only their data |
| **Real-time tracking** | Status updates poll every 10 seconds — no chasing admins |

### 👨‍💼 For Admins
| Feature | How It Works |
|---------|-------------|
| **Centralized dashboard** | All complaints in one filterable, sortable table |
| **Smart filtering** | By status (Pending / In Progress / Resolved) + category |
| **Inline status updates** | Change status directly from the table |
| **Priority auto-calculation** | Low (0–2) → Medium (3–5) → High (6+) based on affected count |
| **Full activity history** | Every action timestamped — complete audit trail |

### 🔄 Duplicate Detection Algorithm
```
Input: "Wi-Fi down in Block A"
Existing: "Wi-Fi not working in Block A"
→ Jaccard Similarity = 50% → Match found → Modal appears
→ Student can JOIN the existing complaint instead of creating a duplicate
```

---

## 🛠 Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| **Language** | Python 3.14+ | Industry-standard, taught in CS curricula |
| **Framework** | Flask 3.0 | Lightweight, minimal dependencies |
| **Frontend** | HTML5 + CSS3 + Vanilla JS | No build step, instant load |
| **Database** | SQLite / PostgreSQL | Zero-config local; PostgreSQL via `DATABASE_URL` for production |
| **Auth** | Werkzeug + Flask-WTF | PBKDF2-SHA256 hashing, CSRF protection |
| **Total dependencies** | **3 pip packages** | Flask, Flask-Session, Werkzeug |

---

## 🗄 Database Design (4 Tables)

```
┌─────────┐     ┌──────────────┐     ┌──────────────────┐
│  users  │──1:N→│  complaints  │──1:N→│complaint_history │
└─────────┘     └──────┬───────┘     └──────────────────┘
                       │ N:M
                  ┌────┴────┐
                  │complaint_users│
                  │(role_in_complaint: creator/joined)│
                  └─────────────┘
```

- `affected_users` always calculated via `COUNT(*)` — never stored, never out of sync
- `UNIQUE(complaint_id, user_id)` — prevents double-joining
- `complaint_history` — timestamped audit trail for every action

---

## 🔒 Security

| Feature | Implementation |
|---------|----------------|
| Password hashing | PBKDF2-SHA256 (Werkzeug) |
| CSRF protection | Flask-WTF on every form |
| Session auth | 3-hour signed cookies |
| Role separation | `@login_required` + `@admin_required` decorators |
| Admin isolation | Admin redirected away from student routes |

---

## 🚀 30-Second Demo Script

```
1. Login as Student One → Submit "Wi-Fi not working"
2. Login as Student Two → See it in "Open" → Click "Join"
3. Login as Admin → See 1 complaint, affected = 2 → Change status to "In Progress"
4. Login as Student One → See status updated in real-time
```

**Demo accounts:** `student1@gmail.com` / `password123` | `admin@gmail.com` / `admin123`

---

## 📊 Impact Numbers

| Metric | Before CIRS | With CIRS |
|--------|-------------|-----------|
| Duplicate complaints | 10 separate reports | 1 complaint, 10 joined users |
| Priority awareness | Guesswork | Auto-calculated by affected count |
| Status tracking | Students chase admins | Self-service dashboard |
| Admin workload | Scattered inboxes | Centralized, filterable dashboard |
| Accountability | None | Full audit trail with timestamps |

---

## 🗺 Future Roadmap

| Phase | Feature | Timeline |
|-------|---------|----------|
| 🟢 **Now** | Core submission, duplicate detection, admin dashboard | ✅ Complete |
| 🔵 **Soon** | Email notifications, image uploads | Next |
| 🟣 **Next** | Analytics dashboard, PDF/Excel export | Near future |
| 🟡 **Later** | Anonymous reporting, mobile PWA | Future |

---

## 🏁 Deployment

```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

- **3 commands** to go from zero to running
- **Zero infrastructure** — SQLite local, PostgreSQL via env var for production
- **Zero cloud costs** — Runs on any machine with Python

---

## ✅ Why CIRS Wins

| ✅ **Smart duplicate detection** amplifies student voice |
| ✅ **Auto-priority** ensures critical issues get attention first |
| ✅ **Full transparency** with timestamped activity history |
| ✅ **Role-based data isolation** — each user sees only their relevant data |
| ✅ **Production-ready security** — CSRF, hashed passwords, session auth |
| ✅ **Zero infrastructure** — 3 dependencies, runs anywhere |

---

*Built with Python • Flask • SQLite • Vanilla JS*
