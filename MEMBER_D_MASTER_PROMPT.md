# Master Prompt for Member D (Krishna Midula K) - SkillSwap

Use this prompt when asking an AI assistant to help build Modules 8, 9, and 10.

---

## Context

You are assisting Member D on the SkillSwap codebase located at:
- `skillswap2/`

Tech stack:
- Backend: FastAPI + SQLAlchemy
- DB: PostgreSQL-targeted (with SQLite fallback in local environments)
- Frontend: static HTML/CSS/JS (Bootstrap + vanilla JS)
- Auth: JWT bearer token

Current implemented areas are already stable (sessions, tokens, reviews, recommendations, dual-role flow).  
Your job is to **add** Module 8/9/10 functionality without breaking existing flows.

---

## Ground Truth (Current Code - Must Follow)

### 1) Dual-role user behavior

- End users are effectively dual-role.
- Capability comes from `user_skills.skill_type`:
  - teaching: `teach` (legacy alias `offer`)
  - learning: `learn` (legacy alias `need`)
- Never gate teaching/learning by `user.role == "mentor"` or `"learner"`.
- `user.role` is used for admin authorization (`admin`) and general end-user role (`student` in current register flow).

### 2) Existing notification implementation

Current notification model exists:
- `skillswap2/app/models/notification.py`

Current notification API exists:
- `GET /notifications/my`
- `PATCH /notifications/{notification_id}/read`
- `PATCH /notifications/read-all`

Session API already emits notification records using `_create_notification(...)` in:
- `skillswap2/app/api/session.py`

Current event types in session flows include:
- `session_requested`
- `session_confirmed`
- `session_declined`
- `session_completed`
- `session_cancelled`
- `session_reschedule_requested`
- `session_reschedule_accepted`
- `session_reschedule_declined`

### 3) Existing admin-like endpoints

There is no dedicated `app/api/admin.py` yet, but `review.py` has admin-protected endpoints:
- `GET /reviews/admin/all`
- `POST /reviews/admin/recalculate`

### 4) Router wiring in `main.py`

Currently included routers:
- `auth`, `users`, `skill`, `session`, `search`, `review`, `notification`, `token`, `recommendation`

No `admin` or `analytics` router is included yet.

---

## Your Scope (Member D)

### Module 8: Notification Enhancements

Enhance existing notification functionality with minimal breakage:

Recommended additions:
1. Add unread count endpoint:
   - `GET /notifications/unread-count`
2. Optionally add a small service layer:
   - `skillswap2/app/services/notification_service.py`
   - Use it for create/list/mark-read logic to reduce duplication.
3. Keep existing endpoints backward compatible (`/my`, `/read-all`, etc.).
4. Maintain current session-triggered notification behavior.
5. Add frontend unread count display (e.g., in top nav/sidebar of key pages).

### Module 9: Admin Module

Create admin APIs in:
- `skillswap2/app/api/admin.py`

Suggested endpoints:
- `GET /admin/users`
- `GET /admin/users/{user_id}`
- `PATCH /admin/users/{user_id}/block`
- `PATCH /admin/users/{user_id}/unblock`
- `GET /admin/sessions`
- `GET /admin/reports`
- `POST /admin/reports/{report_id}/resolve`
- `GET /admin/stats/overview`

Create required models/schemas/services if needed:
- `skillswap2/app/models/report.py`
- `skillswap2/app/models/admin_log.py`
- `skillswap2/app/schemas/report.py`
- `skillswap2/app/services/admin_service.py`

Important:
- Every `/admin/*` endpoint must verify:
  - authenticated user
  - `current_user.role == "admin"`

### Module 10: Analytics & Reporting

Create:
- `skillswap2/app/api/analytics.py`
- `skillswap2/app/services/analytics_service.py`
- `skillswap2/app/schemas/analytics.py`

Suggested endpoints:
- `GET /analytics/overview`
- `GET /analytics/users`
- `GET /analytics/sessions`
- `GET /analytics/skills/popular`
- `GET /analytics/tokens`
- `GET /analytics/ratings`
- `GET /analytics/export` (CSV/JSON)

Use aggregate queries only; do not expose sensitive user details unnecessarily.

---

## Mandatory Integration Steps

1. Add new routers in:
- `skillswap2/app/main.py`

2. If new models are added:
- export them in `skillswap2/app/models/__init__.py`
- generate/apply Alembic migration

3. Keep existing endpoints stable where already used by frontend/tests.

4. Do not remove dual-role compatibility (`teach/learn` + alias handling).

---

## Coding Rules to Enforce

1. Authentication pattern:
```python
from app.utils.security import get_current_user
```

2. Admin check pattern:
```python
if (current_user.role or "").lower() != "admin":
    raise HTTPException(status_code=403, detail="Admin access required")
```

3. Transaction safety:
```python
try:
    # db writes
    db.commit()
except Exception:
    db.rollback()
    raise
```

4. Preserve API behavior unless explicitly versioned.

---

## Testing Discipline (Windows-friendly)

Before push and before PR, run:

```powershell
cd <YOUR_CLONE_PATH>\SkillSwap-SE-Project\skillswap2
.\.venv\Scripts\Activate.ps1

$env:BASE_URL = "http://127.0.0.1:8000"
$env:LEARNER_EMAIL = "<LEARNER_EMAIL>"
$env:LEARNER_PASSWORD = "<LEARNER_PASSWORD>"
$env:MENTOR_EMAIL = "<MENTOR_EMAIL>"
$env:MENTOR_PASSWORD = "<MENTOR_PASSWORD>"

pytest -q
py tests/test_dual_role_api_workflow.py
py tests/test_phase5_api_workflow.py
py tests/test_phase6_api_workflow.py
py tests/test_phase3_api_workflow.py
```

If any regression fails, fix first.

---

## Deliverables Checklist

- Module 8 notification enhancements implemented and tested
- Module 9 admin APIs + minimal usable dashboard controls
- Module 10 analytics endpoints + dashboard charts/export
- New migrations for any added tables
- `main.py` router inclusion updated
- No regression in existing dual-role/session/token/review/recommendation flows
- Docs updated in same PR

---

## Final Guardrail

If you are about to add logic like:
```python
if user.role == "mentor":
```
stop and redesign it using capability-by-skill (`user_skills.skill_type`) unless the check is strictly for admin role authorization.
