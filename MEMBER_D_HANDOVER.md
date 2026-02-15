# Member D Handover - SkillSwap

Date: 2026-02-15  
Prepared by: Sri Sruthi M N

## 1) Important Reality Check (Accounts/Data)

When Member D pulls from GitHub, they get:

- code + docs
- reproducible seed scripts

What they do **not** get automatically:

- your current local runtime DB state (users/sessions/tokens)
- local `.env` secrets (`skillswap2/.env` is not tracked in git)

So after pull, Member D must:

1. run local setup
2. run seed scripts to create shared test accounts/data
3. run regression tests

## 2) Current Architecture Baseline

- End-user role model is dual-role: canonical account role is `student`.
- Teach/learn capability is derived from user skills:
  - teach: `teach` (legacy alias `offer`)
  - learn: `learn` (legacy alias `need`)
- Session validation checks that selected mentor teaches the selected skill.
- Duplicate active session-request guard is enabled.

## 3) Must-Read Docs (in order)

1. `README.md`  
2. `skillswap2/DUAL_ROLE_MIGRATION_HANDOFF.md`  
3. `skillswap2/tests/TEST_RUNBOOK.txt`
4. `MEMBER_D_MASTER_PROMPT.md` (detailed implementation guidance for Modules 8/9/10)

## 4) Module Ownership for Member D

Assumed scope for Member D:

- Module 8: Notification
- Module 9: Admin
- Module 10: Analytics & Reporting

Code areas to focus:

- `skillswap2/app/api/notification.py`
- `skillswap2/app/static/admin-dashboard.html`
- `skillswap2/app/api/review.py` (admin review endpoints exist)
- `skillswap2/app/api/search.py` (trending/search signals)
- `skillswap2/app/models/` (for any new admin/analytics entities)

## 5) Local Setup for Member D (Windows)

PowerShell:

```powershell
cd <YOUR_CLONE_PATH>\SkillSwap-SE-Project\skillswap2
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

CMD:

```bat
cd <YOUR_CLONE_PATH>\SkillSwap-SE-Project\skillswap2
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 6) Branching + Workflow

```powershell
cd <YOUR_CLONE_PATH>\SkillSwap-SE-Project
git checkout -b codex/member-d-module-work
```

Rules:

- Build in small commits by module.
- Keep API changes backward-compatible unless coordinated.
- Do not hardcode role as learner/mentor for user access; use dual-role capability model.

## 7) Test Commands (Required Before PR)

Use PowerShell (Windows) and run suites one by one:

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

Expected: all suites pass.

Notes:

- Phase 3 and Phase 5 workflows now default to fresh temporary users + cleanup, so they are robust even if static credentials are out of tokens.
- Unlike macOS, `/tmp/run_all_skillswap_tests.sh` is not assumed on Windows.

## 7.1) Mandatory Regression Discipline (Explicit Instruction to Member D)

Member D must run regression tests **regularly** so existing flows are not broken.

Minimum cadence:

- after every significant backend/API change
- after every UI flow change touching sessions/recommendations/profile/sidebar
- before every push to remote branch
- before opening PR

Minimum regression set each time:

- `pytest -q`
- `py tests/test_dual_role_api_workflow.py`
- `py tests/test_phase5_api_workflow.py`
- `py tests/test_phase6_api_workflow.py`
- `py tests/test_phase3_api_workflow.py`

If any regression fails, fix before continuing.

## 8) Optional Seed Data for Recommendation/UI Testing

If Member D needs richer mentor data:

```powershell
cd <YOUR_CLONE_PATH>\SkillSwap-SE-Project\skillswap2
py tests/seed_phase6_bulk_profiles.py
```

Or apply SQL seed if they use PostgreSQL and want fixed sample profiles:

- `skillswap2/tests/phase6_seed_data.sql`

## 8.1) Seed Clarification (Must Read)

Those manually created profiles are not fully in the current Python seed.

- `seed_phase6_bulk_profiles.py` creates only the 20 `*.p6@abcuniversity.edu` mentor profiles.
- It does not create `apsara`, `lokhinth`, `harini`, `jeevika`, `kanishma`, `sona` in the older behavior.

`phase6_seed_data.sql` is different:

- It references some existing emails (`apsara`, `harini`, `jeevika`, `lokhinth`) for skill mappings.
- It still does not create those users/profiles/passwords by itself.
- `kanishma` and `sona` are not in that SQL seed.

How Member D knows seeded account passwords:

- For accounts created by `seed_phase6_bulk_profiles.py`, password is:
  - default: `SkillSwap@123`
  - or whatever `SEED_PASSWORD` env var is set to.
- If user already exists, password is unchanged unless:
  - `RESET_EXISTING_PASSWORDS=1` (then it resets to `SEED_PASSWORD`).

Current patch addition:

- `seed_phase6_bulk_profiles.py` now also seeds named accounts for team reproducibility:
  - `apsara@gmail.com`
  - `lokhinth@nitt.edu`
  - `kanishma@abcuniversity.edu`
  - `harini@abcuniversity.edu`
  - `jeevika@abcuniversity.edu`
  - `sona@abcuniversity.edu`
- These deterministic passwords are enforced by default with:
  - `ENFORCE_NAMED_ACCOUNT_PASSWORDS=1`
- All named accounts are set to a single configurable password:
  - `NAMED_SEED_PASSWORD` (defaults to `SEED_PASSWORD`)
- To avoid resetting named-account passwords on a machine:
  - set `ENFORCE_NAMED_ACCOUNT_PASSWORDS=0` before running the seed script.

## 9) Definition of Done (for Member D modules)

- Notification module:
  - inbox list, mark one read, mark all read work end-to-end.
- Admin module:
  - admin login works; moderation actions are protected and logged.
- Analytics module:
  - at least one working dashboard metric set (usage, sessions, token distribution).
- No regression in dual-role flows.
- Full smoke suite passes.
- Documentation updated in same PR.

## 10) PR Checklist Template

Member D should include this in PR description:

- Scope:
  - [ ] Notification
  - [ ] Admin
  - [ ] Analytics
- API changes documented
- UI changes documented
- Test evidence attached (command + output summary)
- Backward compatibility notes
- Risks/known gaps

## 11) Quick Contacts

- Integration owner: Sri Sruthi M N
- Coordinate with:
  - Search/Sessions owner for cross-module API assumptions
  - User/Skill owner for capability-based access checks
