#!/usr/bin/env python3
"""
Phase 3 API workflow test (live server).

Covers:
1) Token API endpoints
2) Session lifecycle with token deduction/reward
3) Cancel refund flow
4) Insufficient token rejection

Usage:
  BASE_URL="http://localhost:8000" \
  LEARNER_EMAIL="learner@college.edu" \
  LEARNER_PASSWORD="password123" \
  MENTOR_EMAIL="mentor@college.edu" \
  MENTOR_PASSWORD="password123" \
  python tests/test_phase3_api_workflow.py

Optional:
  SKILL_ID=1  # If omitted, script picks first skill from /search/skills
  LEARNER_TOKEN="..." MENTOR_TOKEN="..."  # Skip login and use existing JWTs
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
PHASE3_USE_FRESH_USERS = os.getenv("PHASE3_USE_FRESH_USERS", "1").strip().lower() not in {"0", "false", "no"}
TEMP_EMAIL_DOMAIN = os.getenv("PHASE3_TEMP_EMAIL_DOMAIN", "nitt.edu").strip() or "nitt.edu"
TEMP_PASSWORD = os.getenv("PHASE3_TEMP_PASSWORD", "Password@123")


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
        encoded = urllib.parse.urlencode(form_body)
        data = encoded.encode("utf-8")
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


def get_wallet(token: str) -> Dict[str, Any]:
    status, body = request_json("GET", "/tokens/wallet", token=token)
    require(status == 200, f"/tokens/wallet failed: HTTP {status} {body}")
    require("balance" in body, f"/tokens/wallet missing balance: {body}")
    return body


def get_transactions(token: str) -> Any:
    status, body = request_json("GET", "/tokens/transactions?limit=10", token=token)
    require(status == 200, f"/tokens/transactions failed: HTTP {status} {body}")
    require(isinstance(body, list), f"/tokens/transactions not a list: {body}")
    return body


def get_eligibility(token: str) -> Dict[str, Any]:
    status, body = request_json("GET", "/tokens/eligibility", token=token)
    require(status == 200, f"/tokens/eligibility failed: HTTP {status} {body}")
    for key in ("can_book", "current_balance", "required_balance", "session_cost", "deficit"):
        require(key in body, f"/tokens/eligibility missing key '{key}': {body}")
    return body


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
    learner_email = f"phase3tmp_learner_{suffix}@{TEMP_EMAIL_DOMAIN}"
    mentor_email = f"phase3tmp_mentor_{suffix}@{TEMP_EMAIL_DOMAIN}"
    learner_name = f"Phase3Tmp Learner {suffix}"
    mentor_name = f"Phase3Tmp Mentor {suffix}"
    skill_title = f"Phase3Tmp Skill {suffix}"

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
            "description": "Phase 3 temporary skill for workflow test",
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


def iso_in_hours(hours_ahead: int) -> str:
    dt = datetime.now() + timedelta(hours=hours_ahead)
    dt = dt.replace(microsecond=0)
    return dt.isoformat()


def create_session_at(
    learner_token: str,
    mentor_id: int,
    skill_id: int,
    scheduled_time: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    form_body = {
        "mentor_id": mentor_id,
        "skill_id": skill_id,
        "scheduled_time": scheduled_time,
    }
    if notes:
        form_body["notes"] = notes

    status, body = request_json(
        "POST",
        "/sessions/request",
        token=learner_token,
        form_body=form_body,
    )
    require(status == 200, f"Create session failed: HTTP {status} {body}")
    require("session_id" in body, f"Create session missing session_id: {body}")
    return body


def create_session(learner_token: str, mentor_id: int, skill_id: int, hours_ahead: int) -> Dict[str, Any]:
    return create_session_at(learner_token, mentor_id, skill_id, iso_in_hours(hours_ahead))


def list_my_sessions(token: str) -> list[Dict[str, Any]]:
    status, body = request_json("GET", "/sessions/my", token=token)
    require(status == 200, f"/sessions/my failed: HTTP {status} {body}")
    require(isinstance(body, list), f"/sessions/my response not a list: {body}")
    return body


def _iso_close(a: str, b: str, seconds: int = 60) -> bool:
    try:
        da = datetime.fromisoformat(str(a).replace("Z", "+00:00"))
        db = datetime.fromisoformat(str(b).replace("Z", "+00:00"))
    except Exception:
        return False
    return abs((da - db).total_seconds()) <= seconds


def accept_session(token: str, session_id: int) -> Dict[str, Any]:
    status, body = request_json("PATCH", f"/sessions/{session_id}/accept", token=token)
    require(status == 200, f"Accept session failed: HTTP {status} {body}")
    return body


def complete_session(token: str, session_id: int) -> Dict[str, Any]:
    status, body = request_json("PATCH", f"/sessions/{session_id}/complete", token=token)
    require(status == 200, f"Complete session failed: HTTP {status} {body}")
    return body


def cancel_session(token: str, session_id: int) -> Dict[str, Any]:
    status, body = request_json("PATCH", f"/sessions/{session_id}/cancel", token=token)
    require(status == 200, f"Cancel session failed: HTTP {status} {body}")
    return body


def test_token_endpoints(learner_token: str) -> None:
    print("\n=== Test 1: Token Endpoints ===")
    wallet = get_wallet(learner_token)
    require(isinstance(wallet.get("wallet_id"), int), f"wallet_id invalid: {wallet}")
    require(isinstance(wallet.get("user_id"), int), f"user_id invalid: {wallet}")
    require(isinstance(wallet.get("balance"), int), f"balance invalid: {wallet}")
    require(wallet["balance"] >= 0, f"balance must be non-negative: {wallet}")

    eligibility = get_eligibility(learner_token)
    require(
        eligibility["current_balance"] == wallet["balance"],
        f"Eligibility balance mismatch: wallet={wallet['balance']} eligibility={eligibility}",
    )
    if wallet["balance"] >= int(eligibility["required_balance"]):
        require(eligibility["can_book"] is True, f"Expected can_book=True: {eligibility}")
        require(int(eligibility["deficit"]) == 0, f"Expected deficit=0: {eligibility}")
    else:
        require(eligibility["can_book"] is False, f"Expected can_book=False: {eligibility}")
        require(int(eligibility["deficit"]) > 0, f"Expected positive deficit: {eligibility}")

    txns = get_transactions(learner_token)
    if txns:
        first = txns[0]
        for key in ("transaction_id", "type", "amount", "status", "timestamp"):
            require(key in first, f"Transaction missing key '{key}': {first}")
        require(isinstance(first["transaction_id"], int), f"transaction_id invalid: {first}")
        require(isinstance(first["amount"], int), f"amount invalid: {first}")
        require(first["amount"] > 0, f"amount should be positive: {first}")
        require(str(first["type"]).strip() != "", f"type invalid: {first}")
        require(str(first["status"]).strip() != "", f"status invalid: {first}")

    ok(
        f"Token endpoints verified: balance={wallet['balance']}, "
        f"transactions_returned={len(txns)}"
    )


def test_duplicate_request_guard(learner_token: str, mentor_id: int, skill_id: int) -> None:
    print("\n=== Test 2: Duplicate Request Guard ===")
    duplicate_slot = iso_in_hours(28)

    first = create_session_at(
        learner_token,
        mentor_id,
        skill_id,
        duplicate_slot,
        notes="Duplicate guard test",
    )
    first_id = int(first["session_id"])
    ok(f"First request created: session_id={first_id}")

    second = create_session_at(
        learner_token,
        mentor_id,
        skill_id,
        duplicate_slot,
        notes="Duplicate guard retry",
    )
    second_id = int(second["session_id"])
    require(
        second_id == first_id,
        f"Duplicate guard failed: expected same session_id, got {first_id} and {second_id}",
    )

    sessions = list_my_sessions(learner_token)
    matching_pending = [
        s for s in sessions
        if int(s.get("mentor_id", -1)) == mentor_id
        and int(s.get("skill_id", -1)) == skill_id
        and s.get("status") == "Pending"
        and _iso_close(s.get("scheduled_time", ""), duplicate_slot, seconds=60)
    ]
    require(
        len(matching_pending) == 1,
        f"Expected exactly 1 pending duplicate-guard session, found {len(matching_pending)}: {matching_pending}",
    )
    ok("Duplicate request guard returned same session and prevented duplicate row")

    # Cleanup pending test session to keep remaining tests deterministic.
    cancel_session(learner_token, first_id)
    ok("Duplicate guard test session cleaned up")


def test_session_workflow(learner_token: str, mentor_token: str, mentor_id: int, skill_id: int) -> None:
    print("\n=== Test 3: Session Workflow with Tokens ===")
    learner_before = get_wallet(learner_token)["balance"]
    mentor_before = get_wallet(mentor_token)["balance"]

    status, body = request_json(
        "GET",
        "/sessions/my",
        token=learner_token,
    )
    require(status == 200, f"/sessions/my failed before workflow: HTTP {status} {body}")

    create_resp = create_session(learner_token, mentor_id, skill_id, hours_ahead=30)
    session_id = int(create_resp["session_id"])
    ok(f"Session requested: id={session_id}")

    learner_after_request = get_wallet(learner_token)["balance"]
    require(
        learner_after_request == learner_before,
        f"Learner balance changed on request (expected {learner_before}, got {learner_after_request})",
    )
    ok("No token deduction on session request")

    accept_resp = accept_session(mentor_token, session_id)
    require(accept_resp.get("tokens_deducted") == 10, f"Expected tokens_deducted=10, got {accept_resp}")
    learner_after_accept = get_wallet(learner_token)["balance"]
    require(
        learner_after_accept == learner_before - 10,
        f"Learner balance after accept wrong (expected {learner_before - 10}, got {learner_after_accept})",
    )
    ok("Token deduction on accept verified")

    complete_resp = complete_session(learner_token, session_id)
    require(complete_resp.get("tokens_rewarded") == 10, f"Expected tokens_rewarded=10, got {complete_resp}")
    mentor_after_complete = get_wallet(mentor_token)["balance"]
    require(
        mentor_after_complete == mentor_before + 10,
        f"Mentor balance after complete wrong (expected {mentor_before + 10}, got {mentor_after_complete})",
    )
    ok("Token reward on complete verified")


def test_cancel_refund(learner_token: str, mentor_token: str, mentor_id: int, skill_id: int) -> None:
    print("\n=== Test 4: Cancel Session (Refund) ===")
    create_resp = create_session(learner_token, mentor_id, skill_id, hours_ahead=40)
    session_id = int(create_resp["session_id"])
    ok(f"Second session requested: id={session_id}")

    accept_session(mentor_token, session_id)
    learner_after_accept = get_wallet(learner_token)["balance"]
    ok(f"Balance after accept: learner={learner_after_accept}")

    cancel_resp = cancel_session(learner_token, session_id)
    require(cancel_resp.get("tokens_refunded") == 10, f"Expected tokens_refunded=10, got {cancel_resp}")
    learner_after_cancel = get_wallet(learner_token)["balance"]
    require(
        learner_after_cancel == learner_after_accept + 10,
        f"Refund check failed (expected {learner_after_accept + 10}, got {learner_after_cancel})",
    )
    ok("Refund on cancel verified")


def test_insufficient_tokens(learner_token: str, mentor_token: str, mentor_id: int, skill_id: int) -> None:
    print("\n=== Test 5: Insufficient Tokens ===")
    balance = get_wallet(learner_token)["balance"]
    round_idx = 0

    # Drain learner tokens in deterministic steps of 10 until below booking threshold.
    while balance >= 10:
        round_idx += 1
        create_resp = create_session(learner_token, mentor_id, skill_id, hours_ahead=60 + round_idx)
        sid = int(create_resp["session_id"])
        accept_session(mentor_token, sid)
        balance = get_wallet(learner_token)["balance"]
        ok(f"Drain round {round_idx}: accepted session {sid}, learner balance={balance}")
        if round_idx > 25:
            fail("Safety stop hit while draining tokens.")

    status, body = request_json(
        "POST",
        "/sessions/request",
        token=learner_token,
        form_body={
            "mentor_id": mentor_id,
            "skill_id": skill_id,
            "scheduled_time": iso_in_hours(120),
        },
    )
    require(status == 400, f"Expected HTTP 400 for insufficient tokens, got HTTP {status}: {body}")
    detail = str(body.get("detail", ""))
    require("Insufficient tokens" in detail, f"Expected insufficient-token message, got: {body}")
    ok("Insufficient token rejection verified")


def main() -> None:
    print("==========================================================")
    print("PHASE 3 TESTING: TOKENS + SESSION API INTEGRATION (LIVE)")
    print("==========================================================")
    print(f"Base URL: {BASE_URL}")

    cleanup_context: Dict[str, Any] = {}
    try:
        if PHASE3_USE_FRESH_USERS:
            cleanup_context = provision_fresh_temp_context()
            learner_token = str(cleanup_context["learner_token"])
            mentor_token = str(cleanup_context["mentor_token"])
            mentor_id = int(cleanup_context["mentor_id"])
            skill_id = int(cleanup_context["skill_id"])
            ok(
                "Using fresh temp accounts: "
                f"learner={cleanup_context['learner_email']}, "
                f"mentor={cleanup_context['mentor_email']}, skill_id={skill_id}"
            )
        else:
            learner_token = LEARNER_TOKEN_ENV
            mentor_token = MENTOR_TOKEN_ENV
            if learner_token and mentor_token:
                ok("Using LEARNER_TOKEN and MENTOR_TOKEN from environment (login skipped)")
            else:
                require(LEARNER_EMAIL and LEARNER_PASSWORD, "Set LEARNER_EMAIL and LEARNER_PASSWORD (or LEARNER_TOKEN)")
                require(MENTOR_EMAIL and MENTOR_PASSWORD, "Set MENTOR_EMAIL and MENTOR_PASSWORD (or MENTOR_TOKEN)")
                learner_token = login(LEARNER_EMAIL, LEARNER_PASSWORD)
                mentor_token = login(MENTOR_EMAIL, MENTOR_PASSWORD)
                ok("Learner and mentor login successful")

            mentor_id = int(get_me(mentor_token)["id"])
            skill_id = get_skill_id()
            ok(f"Using mentor_id={mentor_id}, skill_id={skill_id}")

        test_token_endpoints(learner_token)
        test_duplicate_request_guard(learner_token, mentor_id, skill_id)
        test_session_workflow(learner_token, mentor_token, mentor_id, skill_id)
        test_cancel_refund(learner_token, mentor_token, mentor_id, skill_id)
        test_insufficient_tokens(learner_token, mentor_token, mentor_id, skill_id)

        print("\n==========================================")
        print("ALL PHASE 3 API TESTS PASSED")
        print("==========================================")
    finally:
        if PHASE3_USE_FRESH_USERS and cleanup_context:
            cleanup_temp_context(cleanup_context)


if __name__ == "__main__":
    main()
