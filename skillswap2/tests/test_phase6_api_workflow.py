#!/usr/bin/env python3
"""
Phase 6 API workflow test (live server).

Covers:
1) Recommendation health check
2) Personalized recommendations (top-N)
3) Skill-filtered recommendations
4) Recommendation explanation endpoint
5) Model refresh endpoint
6) Edge cases:
   - invalid skill id
   - invalid top_n validation
   - optional no-skill learner check

Usage:
  BASE_URL="http://localhost:8000" \
  LEARNER_EMAIL="<LEARNER_EMAIL>" \
  LEARNER_PASSWORD="<LEARNER_PASSWORD>" \
  python tests/test_phase6_api_workflow.py

Optional:
  LEARNER_TOKEN="..."                  # Skip login
  SKILL_ID=1                           # Otherwise picks first skill from /search/skills
  MENTOR_ID=2                          # Use this mentor for /recommend/explain/{mentor_id}
  NO_SKILLS_TOKEN="..."                # Optional edge check for learner with no "need" skills
"""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
LEARNER_EMAIL = os.getenv("LEARNER_EMAIL", "").strip()
LEARNER_PASSWORD = os.getenv("LEARNER_PASSWORD", "").strip()
LEARNER_TOKEN_ENV = os.getenv("LEARNER_TOKEN", "").strip()
SKILL_ID_ENV = os.getenv("SKILL_ID", "").strip()
MENTOR_ID_ENV = os.getenv("MENTOR_ID", "").strip()
NO_SKILLS_TOKEN_ENV = os.getenv("NO_SKILLS_TOKEN", "").strip()


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    sys.exit(1)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def note(message: str) -> None:
    print(f"[NOTE] {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def request_json(
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    json_body: Optional[Dict[str, Any]] = None,
    form_body: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Any]:
    url = f"{BASE_URL}{path}"
    headers: Dict[str, str] = {}
    data: Optional[bytes] = None

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if json_body is not None and form_body is not None:
        raise ValueError("Use either json_body or form_body, not both")

    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif form_body is not None:
        data = urllib.parse.urlencode(form_body).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(url, method=method, data=data, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return resp.status, {}
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, {"raw": raw}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"raw": raw}
        return e.code, body


def login(email: str, password: str) -> str:
    status, body = request_json(
        "POST",
        "/auth/login",
        json_body={"email": email, "password": password},
    )
    require(status == 200, f"Login failed for {email}: HTTP {status} {body}")
    token = body.get("access_token")
    require(bool(token), f"No access_token in login response for {email}: {body}")
    return token


def get_me(token: str) -> Dict[str, Any]:
    status, body = request_json("GET", "/users/me", token=token)
    require(status == 200, f"/users/me failed: HTTP {status} {body}")
    require("id" in body, f"/users/me missing id: {body}")
    return body


def get_skill_id() -> int:
    if SKILL_ID_ENV:
        try:
            return int(SKILL_ID_ENV)
        except ValueError:
            fail(f"Invalid SKILL_ID='{SKILL_ID_ENV}'. Must be integer.")

    status, body = request_json("GET", "/search/skills")
    require(status == 200, f"/search/skills failed: HTTP {status} {body}")
    require(isinstance(body, list) and len(body) > 0, "No skills found. Add at least one skill first.")
    first_id = body[0].get("id")
    require(isinstance(first_id, int), f"First skill has invalid id: {body[0]}")
    return first_id


def validate_recommendation_item(item: Dict[str, Any]) -> None:
    required_keys = (
        "mentor_id",
        "mentor_name",
        "similarity_score",
        "rating",
        "compatibility_score",
        "rank",
        "total_reviews",
        "explanation",
    )
    for key in required_keys:
        require(key in item, f"Recommendation item missing '{key}': {item}")

    require(isinstance(item["mentor_id"], int), f"mentor_id must be int: {item}")
    require(isinstance(item["mentor_name"], str), f"mentor_name must be str: {item}")
    require(0.0 <= float(item["similarity_score"]) <= 1.0, f"similarity_score out of range: {item}")
    require(0.0 <= float(item["compatibility_score"]) <= 1.0, f"compatibility_score out of range: {item}")
    require(int(item["rank"]) >= 1, f"rank must be >=1: {item}")
    require(int(item["total_reviews"]) >= 0, f"total_reviews must be >=0: {item}")
    if item["rating"] is not None:
        require(0.0 <= float(item["rating"]) <= 5.0, f"rating out of range: {item}")


def test_health() -> Dict[str, Any]:
    print("\n=== Test 1: API Health Check ===")
    status, body = request_json("GET", "/recommend/health")
    require(status == 200, f"/recommend/health failed: HTTP {status} {body}")
    require(body.get("service") == "recommendation", f"Unexpected service name: {body}")
    require("status" in body, f"Health response missing status: {body}")

    if body.get("status") != "operational":
        fail(
            f"Recommendation health is not operational: {body}. "
            "If error says no skills found, add at least one skill record first."
        )

    require(body.get("model_ready") is True, f"Model should be ready after health check: {body}")
    require(isinstance(body.get("vocabulary_size"), int), f"Invalid vocabulary_size: {body}")
    require(body["vocabulary_size"] > 0, f"Vocabulary size must be > 0: {body}")
    ok(f"Health check OK: model_ready={body['model_ready']}, vocabulary_size={body['vocabulary_size']}")
    return body


def test_get_recommendations(learner_token: str) -> List[Dict[str, Any]]:
    print("\n=== Test 2: Get Recommendations ===")
    status, body = request_json("GET", "/recommend/?top_n=5", token=learner_token)
    require(status == 200, f"/recommend failed: HTTP {status} {body}")
    require(isinstance(body, list), f"/recommend response is not list: {body}")
    require(len(body) <= 5, f"/recommend returned >5 items: {len(body)}")
    require(len(body) > 0, "No recommendations returned. Ensure learner has 'need' skills and mentors have 'offer' skills.")

    for idx, rec in enumerate(body, start=1):
        validate_recommendation_item(rec)
        require(int(rec["rank"]) == idx, f"Expected rank {idx}, got {rec['rank']}")
        if idx > 1:
            prev = float(body[idx - 2]["compatibility_score"])
            curr = float(rec["compatibility_score"])
            require(prev >= curr, "Recommendations not sorted by compatibility descending")

    top = body[0]
    ok(
        "Recommendations returned: "
        f"count={len(body)}, top_mentor={top['mentor_name']}, top_score={top['compatibility_score']}"
    )
    return body


def test_get_recommendations_by_skill(learner_token: str, skill_id: int) -> List[Dict[str, Any]]:
    print("\n=== Test 2b: Get Recommendations By Skill ===")
    status, body = request_json("GET", f"/recommend/by-skill/{skill_id}?top_n=3", token=learner_token)
    require(status == 200, f"/recommend/by-skill/{skill_id} failed: HTTP {status} {body}")
    require(isinstance(body, list), f"/recommend/by-skill response is not list: {body}")
    require(len(body) <= 3, f"/recommend/by-skill returned >3 items: {len(body)}")

    for idx, rec in enumerate(body, start=1):
        validate_recommendation_item(rec)
        require(int(rec["rank"]) == idx, f"Expected rank {idx}, got {rec['rank']}")

    ok(f"By-skill recommendations loaded: skill_id={skill_id}, count={len(body)}")
    return body


def test_explain(learner_token: str, mentor_id: int) -> None:
    print("\n=== Test 3: Explain Recommendation ===")
    status, body = request_json("GET", f"/recommend/explain/{mentor_id}", token=learner_token)
    require(status == 200, f"/recommend/explain/{mentor_id} failed: HTTP {status} {body}")

    required_keys = (
        "mentor_id",
        "mentor_name",
        "similarity_score",
        "rating_score",
        "activity_score",
        "compatibility_score",
        "weight_similarity",
        "weight_rating",
        "weight_activity",
        "explanation",
    )
    for key in required_keys:
        require(key in body, f"Explain response missing '{key}': {body}")

    sim = float(body["similarity_score"])
    rating_score = body["rating_score"]
    activity = float(body["activity_score"])
    compatibility = float(body["compatibility_score"])
    w_sim = float(body["weight_similarity"])
    w_rating = float(body["weight_rating"])
    w_activity = float(body["weight_activity"])

    require(0.0 <= sim <= 1.0, f"similarity_score out of range: {body}")
    require(0.0 <= activity <= 1.0, f"activity_score out of range: {body}")
    require(0.0 <= compatibility <= 1.0, f"compatibility_score out of range: {body}")
    require(math.isclose(w_sim + w_rating + w_activity, 1.0, abs_tol=1e-6), f"Weights do not sum to 1: {body}")

    normalized_rating = 3.5 / 5.0 if rating_score is None else float(rating_score) / 5.0
    expected = w_sim * sim + w_rating * normalized_rating + w_activity * activity
    require(
        abs(expected - compatibility) <= 0.02,
        (
            "Compatibility formula mismatch. "
            f"expected~{expected:.4f}, actual={compatibility:.4f}, body={body}"
        ),
    )

    ok(
        f"Explain endpoint OK for mentor_id={mentor_id}: "
        f"compatibility={compatibility}, weights=({w_sim},{w_rating},{w_activity})"
    )


def test_refresh(learner_token: str) -> None:
    print("\n=== Test 4: Refresh Recommendation Model ===")
    status, body = request_json("POST", "/recommend/refresh", token=learner_token)
    require(status == 200, f"/recommend/refresh failed: HTTP {status} {body}")
    require(body.get("status") == "ready", f"Refresh status should be 'ready': {body}")
    require(isinstance(body.get("vocabulary_size"), int), f"Invalid vocabulary_size: {body}")
    require(body["vocabulary_size"] > 0, f"Vocabulary size should be > 0 after refresh: {body}")
    ok(f"Refresh successful: vocabulary_size={body['vocabulary_size']}")


def test_edge_invalid_skill(learner_token: str) -> None:
    print("\n=== Edge 5b: Invalid Skill ID ===")
    status, body = request_json("GET", "/recommend/by-skill/99999999?top_n=3", token=learner_token)
    require(status == 404, f"Expected 404 for invalid skill id, got HTTP {status}: {body}")
    ok("Invalid skill id correctly rejected")


def test_edge_invalid_top_n(learner_token: str) -> None:
    print("\n=== Edge: Invalid top_n Validation ===")
    status, body = request_json("GET", "/recommend/?top_n=11", token=learner_token)
    require(status == 422, f"Expected 422 for top_n=11, got HTTP {status}: {body}")
    ok("top_n validation works (1-10)")


def test_edge_no_skill_learner(no_skills_token: str) -> None:
    print("\n=== Edge 5a: Learner With No 'need' Skills (Optional) ===")
    status, body = request_json("GET", "/recommend/?top_n=5", token=no_skills_token)

    # Current API behavior should be 200 with empty list.
    # Accept 400 too if implementation changes to explicit validation.
    require(status in (200, 400), f"Unexpected status for no-skill learner: HTTP {status} {body}")
    if status == 200:
        require(isinstance(body, list), f"Expected list for HTTP 200 no-skill case: {body}")
        require(len(body) == 0, f"Expected empty recommendation list for no-skill learner, got: {body}")
        ok("No-skill learner correctly gets empty recommendation list")
    else:
        require("detail" in body, f"Expected detail in 400 response: {body}")
        ok(f"No-skill learner correctly rejected with message: {body.get('detail')}")


def main() -> None:
    print("=" * 58)
    print("PHASE 6 TESTING: RECOMMENDATIONS API + ML INTEGRATION")
    print("=" * 58)
    print(f"Base URL: {BASE_URL}")

    if LEARNER_TOKEN_ENV:
        learner_token = LEARNER_TOKEN_ENV
        ok("Using LEARNER_TOKEN from environment")
    else:
        if not (LEARNER_EMAIL and LEARNER_PASSWORD):
            fail("Provide LEARNER_TOKEN or LEARNER_EMAIL + LEARNER_PASSWORD")
        learner_token = login(LEARNER_EMAIL, LEARNER_PASSWORD)
        ok("Learner login successful")

    me = get_me(learner_token)
    role = (me.get("role") or "").lower()
    if role == "admin":
        fail(f"Provided token is admin; use a student account for recommendations: {me}")
    if role != "student":
        note(f"Token role is '{role}' (canonical end-user role is 'student').")

    skill_id = get_skill_id()
    ok(f"Using skill_id={skill_id}")

    test_health()
    recs = test_get_recommendations(learner_token)
    test_get_recommendations_by_skill(learner_token, skill_id)

    if MENTOR_ID_ENV:
        try:
            explain_mentor_id = int(MENTOR_ID_ENV)
        except ValueError:
            fail(f"Invalid MENTOR_ID='{MENTOR_ID_ENV}'. Must be integer.")
    else:
        explain_mentor_id = int(recs[0]["mentor_id"])
    test_explain(learner_token, explain_mentor_id)

    test_refresh(learner_token)
    test_edge_invalid_skill(learner_token)
    test_edge_invalid_top_n(learner_token)

    if NO_SKILLS_TOKEN_ENV:
        test_edge_no_skill_learner(NO_SKILLS_TOKEN_ENV)
    else:
        note("Skipping optional no-skill learner edge test (NO_SKILLS_TOKEN not provided).")

    print("\n" + "=" * 42)
    print("ALL PHASE 6 API TESTS PASSED")
    print("=" * 42)


if __name__ == "__main__":
    main()
