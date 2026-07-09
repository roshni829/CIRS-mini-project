# CIRS — Demo Database Reference

This document describes all the demo data seeded automatically when the application starts for the first time. Use these credentials and data points to explore all features of the system.

---

## Demo Credentials

| Role    | Name          | Email                  | Password     |
|---------|---------------|------------------------|--------------|
| Admin   | Admin User    | admin@cirs.com         | admin123     |
| Student | Student One   | student1@cirs.com      | student123   |
| Student | Student Two   | student2@cirs.com      | student123   |
| Student | Student Three | student3@cirs.com      | student123   |

---

## Demo Complaints

### C1 — Wi-Fi not working in Hostel Block A

| Field            | Value                          |
|------------------|-------------------------------|
| Title            | Wi-Fi not working in Hostel Block A |
| Description      | The Wi-Fi network has been down since yesterday. Students are unable to access the internet for online classes. |
| Category         | Wi-Fi                         |
| Issue Type       | No Network                    |
| Location         | Hostel Block A                |
| Status           | In Progress                   |
| Priority         | Medium                        |
| Created By       | Student One                   |
| Joined By        | Student Two, Student Three    |
| Dependency       | Depends on C2 (confirmed)     |

---

### C2 — Electricity failure in Hostel Block A

| Field            | Value                          |
|------------------|-------------------------------|
| Title            | Electricity failure in Hostel Block A |
| Description      | Power supply is unavailable in Hostel Block A. Lights and fans are not working. |
| Category         | Electricity                   |
| Issue Type       | Power Cut                     |
| Location         | Hostel Block A                |
| Status           | Pending                       |
| Priority         | Low                           |
| Created By       | Student One                   |
| Note             | Parent issue — resolving this auto-resolves C1 and C3 |

---

### C3 — Water motor not working

| Field            | Value                          |
|------------------|-------------------------------|
| Title            | Water motor not working       |
| Description      | Motor is not running and water is not coming to the overhead tank. |
| Category         | Water                         |
| Issue Type       | Motor/Pump Not Working        |
| Location         | Hostel Block A                |
| Status           | Pending                       |
| Priority         | Low                           |
| Created By       | Student Two                   |
| Dependency       | Depends on C2 (suggested)     |

---

### C4 — Water leakage near bathroom

| Field            | Value                          |
|------------------|-------------------------------|
| Title            | Water leakage near bathroom   |
| Description      | The tap in the ground floor boys washroom is continuously leaking. Water is being wasted. |
| Category         | Water                         |
| Issue Type       | Pipe Leakage                  |
| Location         | Academic Block                |
| Status           | In Progress                   |
| Priority         | Low                           |
| Created By       | Student Three                 |
| Joined By        | Student One                   |

---

### C5 — Projector bulb fuse in Room 201

| Field            | Value                          |
|------------------|-------------------------------|
| Title            | Projector bulb fuse in Room 201 |
| Description      | The projector bulb in classroom 201 has fused. Unable to conduct presentations. |
| Category         | Classroom                     |
| Issue Type       | Other                         |
| Location         | Room 201                      |
| Status           | **Resolved**                  |
| Priority         | Low                           |
| Created By       | Student Two                   |
| Resolution Notes | Replaced the projector bulb. Working normally now. |

---

### C6 — Slow internet in Computer Lab

| Field            | Value                          |
|------------------|-------------------------------|
| Title            | Slow internet in Computer Lab |
| Description      | The internet speed in the computer lab is extremely slow. Unable to load websites and access lab resources. |
| Category         | Wi-Fi                         |
| Issue Type       | Slow Internet                 |
| Location         | Computer Lab                  |
| Status           | Pending                       |
| Priority         | Medium                        |
| Created By       | Student Three                 |
| Joined By        | Student One, Student Two, Admin User |
| Dependency       | Depends on C2 (suggested)     |

---

## Dependency Map

```
C1 (Wi-Fi not working)       ──[confirmed]──► C2 (Electricity failure)
C3 (Water motor not working) ──[suggested]──► C2 (Electricity failure)
C6 (Slow internet, Comp Lab) ──[suggested]──► C2 (Electricity failure)
```

- **Confirmed dependency**: Resolving C2 automatically resolves C1.
- **Suggested dependencies**: Admin can confirm or ignore the C3 → C2 and C6 → C2 links from the dashboard.
- C6 → C2 is Medium confidence because the locations differ (Computer Lab vs Hostel Block A).

### Auto-resolve behaviour

| Action                                        | Effect                                          |
|-----------------------------------------------|-------------------------------------------------|
| Admin resolves C2                             | C1 is automatically set to Resolved             |
| Admin confirms C3 → C2, then resolves C2      | C1 and C3 are both auto-resolved                |
| Admin confirms C6 → C2, then resolves C2      | C1 and C6 are both auto-resolved                |
| Admin ignores C3 → C2                         | C3 is unaffected when C2 is resolved            |
| Admin ignores C6 → C2                         | C6 is unaffected when C2 is resolved            |

---

## Default SLA Settings

These are the pre-loaded resolution time targets (editable from Admin → SLA Settings):

| Category    | High Priority | Medium Priority | Low Priority |
|-------------|---------------|-----------------|--------------|
| Electricity | 1 hour        | 3 hours         | 6 hours      |
| Water       | 2 hours       | 4 hours         | 8 hours      |
| Wi-Fi       | 3 hours       | 6 hours         | 12 hours     |
| Cleanliness | 6 hours       | 12 hours        | 24 hours     |
| Classroom   | 2 hours       | 6 hours         | 12 hours     |
| Hostel      | 4 hours       | 8 hours         | 24 hours     |
| Other       | 6 hours       | 12 hours        | 24 hours     |

---

## Priority Rules

Priority is automatically calculated based on the number of affected users:

| Affected Users | Priority |
|----------------|----------|
| 6 or more      | High     |
| 3 – 5          | Medium   |
| 1 – 2          | Low      |

---

## Activity Timeline

Each complaint has a full activity timeline. Demo data includes:

- Complaint created
- Student joined
- Status changed to In Progress
- Dependency confirmed
- Issue resolved (with resolution notes on C5)

---

## Quick Feature Walkthrough

| Feature                    | How to test                                                                 |
|----------------------------|-----------------------------------------------------------------------------|
| Student login              | Login as student1@cirs.com / student123                                     |
| Submit new complaint       | Student dashboard → Submit Issue                                            |
| Join existing complaint    | Student dashboard → Join an existing complaint                              |
| Admin status update        | Login as admin@cirs.com / admin123 → Update status on any complaint         |
| Auto-resolve dependents    | Resolve C2 — C1 gets auto-resolved automatically                           |
| Confirm/ignore dependency  | Admin dashboard → Suggested Linked Issues section                           |
| SLA settings               | Admin sidebar → SLA Settings → change hours per category                   |
| Complaint detail & timeline | Click any complaint title to see full history and dependencies             |
