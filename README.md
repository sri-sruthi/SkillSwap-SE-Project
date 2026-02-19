# SkillSwap-SE-Project

SkillSwap is a peer-to-peer skill exchange platform for a university setting.
It now runs on a **single-account dual-role model**:

- one `student` account can both teach and learn
- teaching/learning capability is derived from skills (`teach` / `learn`)
- admins remain role-based (`admin`)

## Current Stack

- Backend: FastAPI + SQLAlchemy
- DB: PostgreSQL (with SQLite fallback support in some environments)
- Auth: JWT
- Frontend: static HTML/CSS/JS pages served by FastAPI
- Recommendations: ML-based matching APIs (`/recommend/*`)

## Current Project Layout

- App root: `skillswap2/`
- API routes: `skillswap2/app/api/`
- Models: `skillswap2/app/models/`
- Schemas: `skillswap2/app/schemas/`
- Services: `skillswap2/app/services/`
- Static UI: `skillswap2/app/static/`
- Tests/workflow scripts: `skillswap2/tests/`

## Dual-Role Behavior (Current)

- Canonical user role: `student` for end users.
- Capabilities from user skills:
  - teach capability: user has at least one `teach` skill (legacy alias `offer` accepted)
  - learn capability: user has at least one `learn` skill (legacy alias `need` accepted)
- Search/recommendation/session validations use mentor capability-by-skill, not static role labels.

## Recommendations + Session Request Flow (Current)

- Recommendation APIs return mentor cards and now include:
  - `mentor_teaching_skills` (skill IDs + names mentor can teach)
- Recommendations modal session request flow:
  - learner selects a skill from that mentor’s teaching list
  - learner enters free-text learning objective in notes
  - backend enforces `mentor teaches selected skill`

## Main UI Pages

- Landing: `/static/index.html`
- Login/Register: `/static/login.html`, `/static/register.html`
- Skill management: `/static/add-skill.html`
- Search: `/static/search.html`
- AI recommendations: `/static/recommendations.html`
- Sessions: `/static/sessions.html`
- Mentor profile: `/static/mentor-profile.html`
- Admin login/dashboard: `/admin/login`, `/static/admin-dashboard.html`

## Quick Start

From `skillswap2/`:

```bash
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

- `http://localhost:8000/static/index.html`

## Email Notifications (SMTP)

Notification emails are implemented for:
- all session events
- `review_received`

Email delivery is best-effort and does not block core actions (session/review APIs still succeed if SMTP fails).

Configure these env vars in `skillswap2/.env`:

```bash
EMAIL_NOTIFICATIONS_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
EMAIL_FROM=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SMTP_TIMEOUT_SECONDS=8
```

## Smoke/Workflow Tests

From `skillswap2/`:

```bash
python tests/test_dual_role_api_workflow.py
python tests/test_phase3_api_workflow.py
python tests/test_phase5_api_workflow.py
python tests/test_phase6_api_workflow.py
```

Notes:

- `tests/test_phase3_api_workflow.py` now uses fresh temporary users/skill by default and cleans them up.
- `tests/test_phase5_api_workflow.py` now uses fresh temporary users/skill by default and cleans them up.
- To force credential mode, set:
  - `PHASE3_USE_FRESH_USERS=0`
  - `PHASE5_USE_FRESH_USERS=0`

Full smoke suite command (uses project venv binaries):

```bash
PATH="/Users/srisruthi/Downloads/SkillSwap-SE-Project/skillswap2/.venv/bin:$PATH" \
BASE_URL="http://127.0.0.1:8000" \
LEARNER_EMAIL="<LEARNER_EMAIL>" \
LEARNER_PASSWORD="<LEARNER_PASSWORD>" \
MENTOR_EMAIL="<MENTOR_EMAIL>" \
MENTOR_PASSWORD="<MENTOR_PASSWORD>" \
/tmp/run_all_skillswap_tests.sh
```

## Notes

- Repo snapshots are maintained in:
  - `REPO_TREE_CURRENT.txt`
  - `REPO_TREE_CLEAN.txt`
  - `REPO_TREE_NO_GIT_NO_VENV.txt`
  - `REPO_TREE_FULL.txt`
