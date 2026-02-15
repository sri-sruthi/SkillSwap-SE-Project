#!/usr/bin/env python3
"""
Phase 5 API workflow test (live server).

Covers:
1) Review submission endpoint
2) Mentor reviews + rating summary
3) Eligibility + learner reviews
4) Edge cases:
   - duplicate review
   - reviewing pending session
   - invalid rating (422)
   - mentor trying to review

Usage:
  BASE_URL="http://localhost:8000" \
  LEARNER_EMAIL="learner@university.edu" \
  LEARNER_PASSWORD="<password>" \
  MENTOR_EMAIL="mentor@university.edu" \
  MENTOR_PASSWORD="<password>" \
  python tests/test_phase5_api_workflow.py

Optional:
  LEARNER_TOKEN="..." MENTOR_TOKEN="..."   # Skip login
  SKILL_ID=1                               # Otherwise picks first /search/skills skill
  COMPLETED_SESSION_ID=123                 # Use existing completed session instead of creating one
"""

from __future__ import annotations

import json
import os
import random
import string
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Ensure `app` package is importable for optional DB cleanup.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
LEARNER_EMAIL = os.getenv("LEARNER_EMAIL", "").strip()
LEARNER_PASSWORD = os.getenv("LEARNER_PASSWORD", "").strip()
MENTOR_EMAIL = os.getenv("MENTOR_EMAIL", "").strip()
MENTOR_PASSWORD = os.getenv("MENTOR_PASSWORD", "").strip()
LEARNER_TOKEN_ENV = os.getenv("LEARNER_TOKEN", "").strip()
MENTOR_TOKEN_ENV = os.getenv("MENTOR_TOKEN", "").strip()
SKILL_ID_ENV = os.getenv("SKILL_ID", "").strip()
COMPLETED_SESSION_ID_ENV = os.getenv("COMPLETED_SESSION_ID", "").strip()
PHASE5_USE_FRESH_USERS = os.getenv("PHASE5_USE_FRESH_USERS", "1").strip().lower() not in {"0", "false", "no"}
TEMP_EMAIL_DOMAIN = os.getenv("PHASE5_TEMP_EMAIL_DOMAIN", "nitt.edu").strip() or "nitt.edu"
TEMP_PASSWORD = os.getenv("PHASE5_TEMP_PASSWORD", "Password@123")


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    sys.exit(1)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def random_suffix(n: int = 8) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(n))


def request_json(
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    json_body: Optional[Dict[str, Any]] = None,
    form_body: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Any]:
    url = f"{BASE_URL}{path}"
    headers = {}
    data = None

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
        with urllib.request.urlopen(req, timeout=20) as resp:
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


def register_user(name: str, email: str, password: str) -> None:
    status, body = request_json(
        "POST",
        "/auth/register",
        json_body={
            "name": name,
            "email": email,
            "password": password,
            "role": "student",
        },
    )
    require(status == 200, f"Register failed for {email}: HTTP {status} {body}")


def get_me(token: str) -> Dict[str, Any]:
    status, body = request_json("GET", "/users/me", token=token)
    require(status == 200, f"/users/me failed: HTTP {status} {body}")
    require("id" in body and "role" in body, f"/users/me missing id/role: {body}")
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
    skill_id = body[0].get("id")
    require(isinstance(skill_id, int), f"First skill has invalid id: {body[0]}")
    return skill_id


def get_skill_id_by_title(token: str, title: str) -> int:
    status, body = request_json("GET", "/skills/", token=token)
    require(status == 200, f"/skills/ failed: HTTP {status} {body}")
    require(isinstance(body, list), f"/skills/ response not list: {body}")
    wanted = title.strip().lower()
    for item in body:
        label = str(item.get("name") or item.get("title") or "").strip().lower()
        if label == wanted:
            sid = item.get("id")
            require(isinstance(sid, int), f"Invalid skill id for {title}: {item}")
            return sid
    fail(f"Could not find temp skill '{title}' in /skills/ response")
    return -1


def provision_fresh_temp_context() -> Dict[str, Any]:
    suffix = random_suffix()
    learner_email = f"phase5tmp_learner_{suffix}@{TEMP_EMAIL_DOMAIN}"
    mentor_email = f"phase5tmp_mentor_{suffix}@{TEMP_EMAIL_DOMAIN}"
    learner_name = f"Phase5Tmp Learner {suffix}"
    mentor_name = f"Phase5Tmp Mentor {suffix}"
    skill_title = f"Phase5Tmp Skill {suffix}"

    register_user(learner_name, learner_email, TEMP_PASSWORD)
    register_user(mentor_name, mentor_email, TEMP_PASSWORD)

    learner_token = login(learner_email, TEMP_PASSWORD)
    mentor_token = login(mentor_email, TEMP_PASSWORD)
    mentor_id = int(get_me(mentor_token)["id"])

    status, body = request_json(
        "POST",
        "/skills/",
        token=mentor_token,
        form_body={
            "title": skill_title,
            "description": "Phase 5 temporary skill for workflow test",
            "category": "General",
            "proficiency_level": "Advanced",
            "skill_type": "teach",
        },
    )
    require(status == 200, f"Failed to create temp skill: HTTP {status} {body}")
    skill_id = get_skill_id_by_title(mentor_token, skill_title)

    return {
        "learner_token": learner_token,
        "mentor_token": mentor_token,
        "mentor_id": mentor_id,
        "skill_id": skill_id,
        "learner_email": learner_email,
        "mentor_email": mentor_email,
        "skill_title": skill_title,
    }


def cleanup_temp_context(context: Dict[str, Any]) -> None:
    emails = [e for e in [context.get("learner_email"), context.get("mentor_email")] if e]
    if not emails:
        return

    try:
        from sqlalchemy import or_
        from app.database import SessionLocal
        from app import models
    except Exception as exc:
        print(f"[WARN] Cleanup skipped (import error): {exc}")
        return

    db = SessionLocal()
    try:
        users = db.query(models.User).filter(models.User.email.in_(emails)).all()
        user_ids = [u.id for u in users]
        if not user_ids:
            print("[OK] Cleanup: temp users already absent")
            return

        db.query(models.Session).filter(
            or_(
                models.Session.learner_id.in_(user_ids),
                models.Session.mentor_id.in_(user_ids),
            )
        ).delete(synchronize_session=False)

        db.query(models.Recommendation).filter(
            or_(
                models.Recommendation.learner_id.in_(user_ids),
                models.Recommendation.mentor_id.in_(user_ids),
            )
        ).delete(synchronize_session=False)

        db.query(models.Notification).filter(
            or_(
                models.Notification.recipient_id.in_(user_ids),
                models.Notification.actor_id.in_(user_ids),
            )
        ).delete(synchronize_session=False)

        db.query(models.Review).filter(
            or_(
                models.Review.learner_id.in_(user_ids),
                models.Review.mentor_id.in_(user_ids),
            )
        ).delete(synchronize_session=False)
        db.query(models.MentorRating).filter(
            models.MentorRating.mentor_id.in_(user_ids)
        ).delete(synchronize_session=False)

        wallet_rows = db.query(models.TokenWallet.id).filter(
            models.TokenWallet.user_id.in_(user_ids)
        ).all()
        wallet_ids = [wid for (wid,) in wallet_rows]
        if wallet_ids:
            db.query(models.TokenTransaction).filter(
                models.TokenTransaction.wallet_id.in_(wallet_ids)
            ).delete(synchronize_session=False)

        db.query(models.TokenWallet).filter(
            models.TokenWallet.user_id.in_(user_ids)
        ).delete(synchronize_session=False)
        db.query(models.UserSkill).filter(
            models.UserSkill.user_id.in_(user_ids)
        ).delete(synchronize_session=False)
        db.query(models.UserProfile).filter(
            models.UserProfile.user_id.in_(user_ids)
        ).delete(synchronize_session=False)
        db.query(models.User).filter(
            models.User.id.in_(user_ids)
        ).delete(synchronize_session=False)

        skill_title = context.get("skill_title")
        if skill_title:
            db.query(models.Skill).filter(
                models.Skill.title == skill_title
            ).delete(synchronize_session=False)

        db.commit()
        print("[OK] Cleanup: temporary users and related data removed")
    except Exception as exc:
        db.rollback()
        print(f"[WARN] Cleanup failed: {exc}")
    finally:
        db.close()


def check_eligibility(token: str) -> Dict[str, Any]:
    status, body = request_json("GET", "/tokens/eligibility", token=token)
    require(status == 200, f"/tokens/eligibility failed: HTTP {status} {body}")
    return body


def list_my_sessions(token: str) -> list[Dict[str, Any]]:
    status, body = request_json("GET", "/sessions/my", token=token)
    require(status == 200, f"/sessions/my failed: HTTP {status} {body}")
    require(isinstance(body, list), f"/sessions/my response not list: {body}")
    return body


def get_session_review(token: str, session_id: int) -> Any:
    status, body = request_json("GET", f"/reviews/session/{session_id}", token=token)
    require(status == 200, f"/reviews/session/{session_id} failed: HTTP {status} {body}")
    return body


def find_completed_unreviewed_session_id(token: str, learner_id: int) -> Optional[int]:
    sessions = list_my_sessions(token)
    for session in sessions:
        if int(session.get("learner_id", -1)) != learner_id:
            continue
        if session.get("status") != "Completed":
            continue
        sid = int(session.get("id", -1))
        if sid <= 0:
            continue
        review = get_session_review(token, sid)
        if not review:
            return sid
    return None


def find_non_completed_session_id(token: str, learner_id: int) -> Optional[int]:
    sessions = list_my_sessions(token)
    for session in sessions:
        if int(session.get("learner_id", -1)) != learner_id:
            continue
        if session.get("status") != "Completed":
            sid = int(session.get("id", -1))
            if sid > 0:
                return sid
    return None


def iso_in_hours(hours_ahead: int) -> str:
    dt = datetime.now() + timedelta(hours=hours_ahead)
    return dt.replace(microsecond=0).isoformat()


def create_session(learner_token: str, mentor_id: int, skill_id: int, hours_ahead: int) -> int:
    status, body = request_json(
        "POST",
        "/sessions/request",
        token=learner_token,
        form_body={
            "mentor_id": mentor_id,
            "skill_id": skill_id,
            "scheduled_time": iso_in_hours(hours_ahead),
        },
    )
    require(status == 200, f"Create session failed: HTTP {status} {body}")
    require("session_id" in body, f"Create session response missing session_id: {body}")
    return int(body["session_id"])


def create_session_optional(
    learner_token: str, mentor_id: int, skill_id: int, hours_ahead: int
) -> Tuple[Optional[int], int, Any]:
    status, body = request_json(
        "POST",
        "/sessions/request",
        token=learner_token,
        form_body={
            "mentor_id": mentor_id,
            "skill_id": skill_id,
            "scheduled_time": iso_in_hours(hours_ahead),
        },
    )
    if status == 200 and "session_id" in body:
        return int(body["session_id"]), status, body
    return None, status, body


def find_pending_session_id(learner_token: str, learner_id: int) -> Optional[int]:
    status, body = request_json("GET", "/sessions/my", token=learner_token)
    if status != 200 or not isinstance(body, list):
        return None
    for session in body:
        if (
            session.get("status") == "Pending"
            and int(session.get("learner_id", -1)) == learner_id
            and session.get("id") is not None
        ):
            return int(session["id"])
    return None


def accept_session(mentor_token: str, session_id: int) -> Dict[str, Any]:
    status, body = request_json("PATCH", f"/sessions/{session_id}/accept", token=mentor_token)
    require(status == 200, f"Accept session {session_id} failed: HTTP {status} {body}")
    return body


def complete_session(learner_token: str, session_id: int) -> Dict[str, Any]:
    status, body = request_json("PATCH", f"/sessions/{session_id}/complete", token=learner_token)
    require(status == 200, f"Complete session {session_id} failed: HTTP {status} {body}")
    return body


def ensure_completed_session(
    learner_token: str,
    mentor_token: str,
    learner_id: int,
    mentor_id: int,
    skill_id: int,
) -> int:
    if COMPLETED_SESSION_ID_ENV:
        try:
            sid = int(COMPLETED_SESSION_ID_ENV)
        except ValueError:
            fail(f"Invalid COMPLETED_SESSION_ID='{COMPLETED_SESSION_ID_ENV}'")
        ok(f"Using provided completed session id={sid}")
        return sid

    eligibility = check_eligibility(learner_token)
    if eligibility.get("can_book") is not True:
        existing_sid = find_completed_unreviewed_session_id(learner_token, learner_id)
        if existing_sid is not None:
            ok(f"Using existing completed unreviewed session id={existing_sid}")
            return existing_sid
        fail(
            f"Learner cannot book session now (balance={eligibility.get('current_balance')}, "
            f"required={eligibility.get('required_balance')}), and no completed-unreviewed "
            "session is available. Use a learner with >=10 tokens or provide COMPLETED_SESSION_ID."
        )

    sid = create_session(learner_token, mentor_id, skill_id, hours_ahead=36)
    ok(f"Created session request id={sid}")

    accept_resp = accept_session(mentor_token, sid)
    require(accept_resp.get("status") == "Confirmed", f"Session not confirmed: {accept_resp}")
    ok(f"Accepted session id={sid}")

    complete_resp = complete_session(learner_token, sid)
    require(complete_resp.get("status") == "Completed", f"Session not completed: {complete_resp}")
    ok(f"Completed session id={sid}")
    return sid


def test_submit_review(learner_token: str, session_id: int) -> Dict[str, Any]:
    print("\n=== Test 1: Submit Review ===")
    status, body = request_json(
        "POST",
        "/reviews/",
        token=learner_token,
        json_body={
            "session_id": session_id,
            "rating": 5,
            "comment": "Excellent mentor!",
        },
    )
    require(status == 201, f"Submit review failed: HTTP {status} {body}")
    for key in ("review_id", "session_id", "rating", "mentor_new_average", "mentor_total_reviews", "message"):
        require(key in body, f"Review response missing key '{key}': {body}")
    require(body["session_id"] == session_id, f"Wrong session_id in review response: {body}")
    require(body["rating"] == 5, f"Wrong rating in review response: {body}")
    ok(f"Review submitted: review_id={body['review_id']}, mentor_avg={body['mentor_new_average']}")
    return body


def test_get_mentor_reviews(learner_token: str, mentor_id: int, expected_review_id: int) -> None:
    print("\n=== Test 2: Get Mentor Reviews ===")
    status, body = request_json("GET", f"/reviews/mentor/{mentor_id}", token=learner_token)
    require(status == 200, f"/reviews/mentor/{mentor_id} failed: HTTP {status} {body}")
    require(isinstance(body, list), f"Mentor reviews not a list: {body}")
    require(
        any(item.get("review_id") == expected_review_id for item in body),
        f"Expected review {expected_review_id} not found: {body}",
    )
    ok(f"Mentor reviews loaded: count={len(body)}")


def test_get_mentor_rating(mentor_id: int) -> None:
    print("\n=== Test 3: Get Mentor Rating Summary ===")
    status, body = request_json("GET", f"/reviews/rating/{mentor_id}")
    require(status == 200, f"/reviews/rating/{mentor_id} failed: HTTP {status} {body}")
    for key in ("mentor_id", "average_rating", "total_reviews", "rating_distribution", "rating_distribution_percentage"):
        require(key in body, f"Mentor rating summary missing key '{key}': {body}")
    require(body["mentor_id"] == mentor_id, f"Wrong mentor_id in rating response: {body}")
    require(body["total_reviews"] >= 1, f"Expected at least 1 review, got: {body}")
    ok(f"Mentor rating summary loaded: avg={body['average_rating']}, total={body['total_reviews']}")


def test_review_eligibility_after_submission(learner_token: str, session_id: int) -> None:
    print("\n=== Test 4: Review Eligibility (After Submit) ===")
    status, body = request_json("GET", f"/reviews/eligibility/{session_id}", token=learner_token)
    require(status == 200, f"/reviews/eligibility/{session_id} failed: HTTP {status} {body}")
    require(body.get("can_review") is False, f"Expected can_review=false after submit, got: {body}")
    reason = str(body.get("reason", ""))
    require("already" in reason.lower(), f"Expected 'already reviewed' reason, got: {body}")
    ok("Eligibility check correctly blocks duplicate review")


def test_get_my_reviews(learner_token: str, expected_session_id: int) -> None:
    print("\n=== Test 5: Get Learner My Reviews ===")
    status, body = request_json("GET", "/reviews/learner/my-reviews", token=learner_token)
    require(status == 200, f"/reviews/learner/my-reviews failed: HTTP {status} {body}")
    require(isinstance(body, list), f"My reviews response not a list: {body}")
    require(any(item.get("session_id") == expected_session_id for item in body), f"Expected session {expected_session_id} in my reviews, got: {body}")
    ok(f"My reviews loaded: count={len(body)}")


def test_edge_duplicate_review(learner_token: str, session_id: int) -> None:
    print("\n=== Edge 5a: Duplicate Review Rejection ===")
    status, body = request_json(
        "POST",
        "/reviews/",
        token=learner_token,
        json_body={"session_id": session_id, "rating": 4, "comment": "Second try"},
    )
    require(status == 400, f"Expected 400 for duplicate review, got HTTP {status}: {body}")
    reason = str(body.get("detail", ""))
    require("already" in reason.lower(), f"Expected duplicate-review message, got: {body}")
    ok("Duplicate review correctly rejected")


def test_edge_pending_session_review(
    learner_token: str,
    learner_id: int,
    mentor_id: int,
    skill_id: int,
    prepared_pending_session_id: Optional[int] = None,
) -> None:
    print("\n=== Edge 5b: Review Pending Session ===")
    sid = prepared_pending_session_id
    if sid is None:
        sid = find_pending_session_id(learner_token, learner_id)
    if sid is None:
        sid = find_non_completed_session_id(learner_token, learner_id)
    if sid is None:
        sid, status, body = create_session_optional(learner_token, mentor_id, skill_id, hours_ahead=48)
        if sid is None:
            detail = str(body.get("detail", "")) if isinstance(body, dict) else str(body)
            if status == 400 and "insufficient tokens" in detail.lower():
                fail(
                    "Cannot run non-completed-session edge case: learner has insufficient tokens "
                    "and no existing non-completed session. Use a learner with >=10 tokens."
                )
            fail(f"Unable to prepare pending session for edge test: HTTP {status} {body}")

    status, body = request_json(
        "POST",
        "/reviews/",
        token=learner_token,
        json_body={"session_id": sid, "rating": 5, "comment": "Should fail"},
    )
    require(status == 400, f"Expected 400 for pending session review, got HTTP {status}: {body}")
    reason = str(body.get("detail", ""))
    require("completed" in reason.lower(), f"Expected completed-session message, got: {body}")
    ok("Pending session review correctly rejected")


def test_edge_invalid_rating(learner_token: str, session_id: int) -> None:
    print("\n=== Edge 5c: Invalid Rating Validation ===")
    status, body = request_json(
        "POST",
        "/reviews/",
        token=learner_token,
        json_body={"session_id": session_id, "rating": 6},
    )
    require(status == 422, f"Expected 422 for invalid rating, got HTTP {status}: {body}")
    ok("Invalid rating correctly rejected with validation error")


def test_edge_mentor_cannot_review(mentor_token: str, session_id: int) -> None:
    print("\n=== Edge 5d: Mentor Cannot Review ===")
    status, body = request_json(
        "POST",
        "/reviews/",
        token=mentor_token,
        json_body={"session_id": session_id, "rating": 5, "comment": "Mentor self-review"},
    )
    require(status == 400, f"Expected 400 when non-learner participant tries to review, got HTTP {status}: {body}")
    reason = str(body.get("detail", ""))
    require("learner" in reason.lower(), f"Expected learner-participant message, got: {body}")
    ok("Non-learner participant review attempt correctly rejected")


def main() -> None:
    print("==========================================================")
    print("PHASE 5 TESTING: REVIEWS API + INTEGRATION (LIVE)")
    print("==========================================================")
    print(f"Base URL: {BASE_URL}")

    temp_context: Optional[Dict[str, Any]] = None
    try:
        learner_token = LEARNER_TOKEN_ENV
        mentor_token = MENTOR_TOKEN_ENV
        skill_id: int

        if PHASE5_USE_FRESH_USERS:
            temp_context = provision_fresh_temp_context()
            learner_token = str(temp_context["learner_token"])
            mentor_token = str(temp_context["mentor_token"])
            skill_id = int(temp_context["skill_id"])
            ok(
                "Using fresh temporary users and skill "
                f"(domain={TEMP_EMAIL_DOMAIN}, skill_id={skill_id})"
            )
        else:
            if learner_token and mentor_token:
                ok("Using LEARNER_TOKEN and MENTOR_TOKEN from environment (login skipped)")
            else:
                require(LEARNER_EMAIL and LEARNER_PASSWORD, "Set LEARNER_EMAIL and LEARNER_PASSWORD (or LEARNER_TOKEN)")
                require(MENTOR_EMAIL and MENTOR_PASSWORD, "Set MENTOR_EMAIL and MENTOR_PASSWORD (or MENTOR_TOKEN)")
                learner_token = login(LEARNER_EMAIL, LEARNER_PASSWORD)
                mentor_token = login(MENTOR_EMAIL, MENTOR_PASSWORD)
                ok("Learner and mentor login successful")
            skill_id = get_skill_id()

        learner_me = get_me(learner_token)
        mentor_me = get_me(mentor_token)
        learner_role = (learner_me.get("role") or "").lower()
        mentor_role = (mentor_me.get("role") or "").lower()
        require(learner_role != "admin", f"LEARNER token cannot be admin: {learner_me}")
        require(mentor_role != "admin", f"MENTOR token cannot be admin: {mentor_me}")

        mentor_id = int(mentor_me["id"])
        learner_id = int(learner_me["id"])
        require(mentor_id != learner_id, "LEARNER and MENTOR tokens resolved to the same user")
        ok(f"Using learner_id={learner_id}, mentor_id={mentor_id}, skill_id={skill_id}")

        pending_session_for_edge: Optional[int] = None
        eligibility = check_eligibility(learner_token)
        if eligibility.get("can_book") is True:
            pending_session_for_edge, status, body = create_session_optional(
                learner_token, mentor_id, skill_id, hours_ahead=30
            )
            if pending_session_for_edge is not None:
                ok(f"Prepared pending session id={pending_session_for_edge} for edge test")
            else:
                ok(f"Could not pre-create pending session (HTTP {status}); edge test will fallback")
        else:
            ok("Learner cannot pre-create pending session now; edge test will try existing pending session")

        completed_session_id = ensure_completed_session(
            learner_token,
            mentor_token,
            learner_id,
            mentor_id,
            skill_id,
        )
        submit_resp = test_submit_review(learner_token, completed_session_id)
        test_get_mentor_reviews(learner_token, mentor_id, int(submit_resp["review_id"]))
        test_get_mentor_rating(mentor_id)
        test_review_eligibility_after_submission(learner_token, completed_session_id)
        test_get_my_reviews(learner_token, completed_session_id)
        test_edge_duplicate_review(learner_token, completed_session_id)
        test_edge_pending_session_review(
            learner_token,
            learner_id,
            mentor_id,
            skill_id,
            prepared_pending_session_id=pending_session_for_edge,
        )
        test_edge_invalid_rating(learner_token, completed_session_id)
        test_edge_mentor_cannot_review(mentor_token, completed_session_id)

        print("\n==========================================")
        print("ALL PHASE 5 API TESTS PASSED")
        print("==========================================")
    finally:
        if temp_context:
            cleanup_temp_context(temp_context)


if __name__ == "__main__":
    main()
