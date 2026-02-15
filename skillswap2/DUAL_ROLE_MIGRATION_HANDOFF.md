# SkillSwap Dual-Role Migration Handoff

## Status

Dual-role migration is active and aligned with the running codebase.

- End-user account role: `student`
- Admin role: `admin`
- Teach/learn behavior determined by skills, not static learner/mentor accounts
- Legacy aliases remain accepted:
  - `offer` -> `teach`
  - `need` -> `learn`

## Completed Scope

1. Capability-based user model
- `/users/me` exposes `can_teach` and `can_learn`.
- UI role behavior uses these capability flags.

2. Skill alias compatibility + dedupe handling
- Skill APIs normalize aliases.
- Duplicate alias rows are collapsed in relevant outputs.

3. Session validation hardening
- Session creation validates:
  - mentor exists
  - skill exists
  - mentor teaches selected skill
- Duplicate active request guard added for same learner+mentor+skill+time window.

4. Recommendations flow updates
- Recommendation API responses include mentor teaching skills:
  - `mentor_teaching_skills: [{id, name}]`
- Recommendations request modal uses mentor-specific skill dropdown.
- Learner free-text goal remains in notes.

5. Public mentor profile improvements
- `/users/public/{mentor_id}` returns `teaching_skills`.
- Mentor profile page renders those skills.

6. Sidebar/profile consistency fixes
- Sessions page no longer renders duplicate dual-role profile sections.
- “My Ratings & Reviews” button visibility is capability-based (`can_teach` only).

7. Landing page alignment with dual-role objective
- Single CTA (`Create Student Account`).
- Action-oriented cards:
  - `I can teach`
  - `I want to learn`
- AI copy retained in compact glassy badge format.

## Key Files Touched (Dual-Role + Recent UI/API Fixes)

- `app/api/skill.py`
- `app/api/search.py`
- `app/api/session.py`
- `app/api/users.py`
- `app/api/recommendation.py`
- `app/schemas/recommendation.py`
- `app/static/recommendations.html`
- `app/static/mentor-profile.html`
- `app/static/sessions.html`
- `app/static/search.html`
- `app/static/index.html`

## Verification Summary

1. Dual-role live API smoke
- `tests/test_dual_role_api_workflow.py` -> passed end-to-end.

2. Phase 3 workflow
- `tests/test_phase3_api_workflow.py` now provisions fresh temporary learner/mentor users and a temporary teach-skill by default.
- Script performs automatic DB cleanup of temporary users + related rows after test run.
- Still supports credential mode via `PHASE3_USE_FRESH_USERS=0`.

3. Phase 5 workflow
- `tests/test_phase5_api_workflow.py` now provisions fresh temporary learner/mentor users and a temporary teach-skill by default.
- Script performs automatic DB cleanup of temporary users + related rows after test run.
- Still supports credential mode via `PHASE5_USE_FRESH_USERS=0`.

4. Phase 6 workflow
- `tests/test_phase6_api_workflow.py` passes.
- Recommendation payload includes `mentor_teaching_skills` and supports modal skill selection.

## Remaining Practical Notes

- Some legacy naming still appears in old comments/messages (`mentor/learner` wording), but behavior is capability-based.
- Worktree can be intentionally dirty during iteration; avoid assuming clean git state.

## Suggested Ongoing Checks

From `skillswap2/`:

```bash
python3 -m py_compile app/api/recommendation.py app/api/session.py app/api/users.py
python tests/test_dual_role_api_workflow.py
python tests/test_phase3_api_workflow.py
python tests/test_phase5_api_workflow.py
python tests/test_phase6_api_workflow.py
```

For the combined smoke suite:

```bash
PATH="/Users/srisruthi/Downloads/SkillSwap-SE-Project/skillswap2/.venv/bin:$PATH" \
BASE_URL="http://127.0.0.1:8000" \
LEARNER_EMAIL="<LEARNER_EMAIL>" \
LEARNER_PASSWORD="<LEARNER_PASSWORD>" \
MENTOR_EMAIL="<MENTOR_EMAIL>" \
MENTOR_PASSWORD="<MENTOR_PASSWORD>" \
/tmp/run_all_skillswap_tests.sh
```
