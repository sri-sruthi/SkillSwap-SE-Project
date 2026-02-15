# Phase 6 Testing Guide (Recommendations + ML)

This guide reflects the current implementation, including mentor teaching-skill payloads used by the recommendations session-request modal.

## 1) Prerequisites

```bash
cd /Users/srisruthi/Downloads/SkillSwap-SE-Project/skillswap2
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 2) Health + API Checks

Set token:

```bash
TOKEN="<JWT_TOKEN>"
```

Health:

```bash
curl http://localhost:8000/recommend/health
```

Top-N recommendations:

```bash
curl -X GET "http://localhost:8000/recommend/?top_n=5" \
  -H "Authorization: Bearer $TOKEN"
```

By-skill recommendations:

```bash
curl -X GET "http://localhost:8000/recommend/by-skill/1?top_n=3" \
  -H "Authorization: Bearer $TOKEN"
```

Explain recommendation:

```bash
curl -X GET "http://localhost:8000/recommend/explain/2" \
  -H "Authorization: Bearer $TOKEN"
```

Refresh model:

```bash
curl -X POST "http://localhost:8000/recommend/refresh" \
  -H "Authorization: Bearer $TOKEN"
```

## 3) Response Shape Check (Current)

Recommendation items should include:

- `mentor_id`
- `mentor_name`
- `similarity_score`
- `rating`
- `compatibility_score`
- `rank`
- `total_reviews`
- `explanation`
- `mentor_teaching_skills` (array of `{id, name}`)

Example quick check:

```bash
curl -X GET "http://localhost:8000/recommend/?top_n=1" \
  -H "Authorization: Bearer $TOKEN"
```

## 4) Automated Workflow Script

```bash
cd /Users/srisruthi/Downloads/SkillSwap-SE-Project/skillswap2
BASE_URL="http://localhost:8000" \
LEARNER_EMAIL="<LEARNER_EMAIL>" \
LEARNER_PASSWORD="<LEARNER_PASSWORD>" \
python tests/test_phase6_api_workflow.py
```

Optional env vars:

- `LEARNER_TOKEN`
- `SKILL_ID`
- `MENTOR_ID`
- `NO_SKILLS_TOKEN`

## 5) Frontend Manual Checks

Open:

```text
http://localhost:8000/static/recommendations.html
```

Verify:

1. Recommendation cards render rank, mentor, score, explanation.
2. `Request Session` modal loads.
3. Modal skill selector shows only skills the selected mentor teaches.
4. Free-text notes field remains available for learner goals.
5. Submitting request succeeds when selected skill is from mentor list.
6. If mentor has no teaching skills, request is disabled with clear message.

## 6) Edge Cases

Invalid skill:

```bash
curl -X GET "http://localhost:8000/recommend/by-skill/99999999?top_n=3" \
  -H "Authorization: Bearer $TOKEN"
```

Expected: `404`.

Invalid `top_n`:

```bash
curl -X GET "http://localhost:8000/recommend/?top_n=11" \
  -H "Authorization: Bearer $TOKEN"
```

Expected: `422`.

## 7) Success Criteria

Phase 6 is good when:

- health endpoint is operational (`model_ready=true`)
- recommendations are ranked and non-empty (for eligible learner data)
- by-skill and explain endpoints work
- refresh endpoint works
- recommendation payload includes mentor teaching-skill IDs/names
- recommendations modal can request sessions without skill-mismatch failures
