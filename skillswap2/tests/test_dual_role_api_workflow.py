#!/usr/bin/env python3
"""
Dual-role API workflow smoke test (live server).

Covers:
1) Register/login two student users
2) Each user adds one teaching skill and one learning skill
3) /users/me reflects can_teach + can_learn for both users
4) Each user alternates learner/mentor across two sessions
5) Token economy balances out after reciprocal sessions

Usage:
  BASE_URL="http://localhost:8000" python tests/test_dual_role_api_workflow.py
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
from typing import Any, Dict, Optional, Tuple


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    sys.exit(1)


def ok(message: str) -> None:
    print(f"[OK] {message}")


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
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return resp.status, {}
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, {"raw": raw}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"raw": raw}
        return exc.code, body


def random_suffix(n: int = 8) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(n))


def iso_in_hours(hours: int) -> str:
    return (datetime.now() + timedelta(hours=hours)).replace(microsecond=0).isoformat()


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
    require(status == 200, f"Register failed ({email}): HTTP {status} {body}")


def login_user(email: str, password: str) -> str:
    status, body = request_json(
        "POST",
        "/auth/login",
        json_body={"email": email, "password": password},
    )
    require(status == 200, f"Login failed ({email}): HTTP {status} {body}")
    token = body.get("access_token")
    require(bool(token), f"No access_token for {email}: {body}")
    return str(token)


def get_me(token: str) -> Dict[str, Any]:
    status, body = request_json("GET", "/users/me", token=token)
    require(status == 200, f"/users/me failed: HTTP {status} {body}")
    return body


def add_skill(token: str, title: str, skill_type: str) -> None:
    normalized_type = skill_type.strip().lower()
    is_teaching_type = normalized_type in {"teach", "offer"}
    status, body = request_json(
        "POST",
        "/skills/",
        token=token,
        form_body={
            "title": title,
            "description": f"{title} description",
            "category": "General",
            "proficiency_level": "Intermediate" if is_teaching_type else "Beginner",
            "skill_type": skill_type,
        },
    )
    require(status == 200, f"Add skill failed ({title}/{skill_type}): HTTP {status} {body}")


def get_skill_id_by_name(name: str) -> int:
    status, body = request_json("GET", "/skills/")
    require(status == 200, f"/skills/ failed: HTTP {status} {body}")
    require(isinstance(body, list), f"/skills/ did not return list: {body}")
    for item in body:
        if str(item.get("name", "")).strip().lower() == name.strip().lower():
            sid = item.get("id")
            require(isinstance(sid, int), f"Skill id invalid for {name}: {item}")
            return sid
    fail(f"Could not find skill id for '{name}'")
    return -1


def wallet_balance(token: str) -> int:
    status, body = request_json("GET", "/tokens/wallet", token=token)
    require(status == 200, f"/tokens/wallet failed: HTTP {status} {body}")
    bal = body.get("balance")
    require(isinstance(bal, int), f"Wallet balance invalid: {body}")
    return bal


def request_session_at(token: str, mentor_id: int, skill_id: int, scheduled_time: str, notes: str) -> int:
    status, body = request_json(
        "POST",
        "/sessions/request",
        token=token,
        form_body={
            "mentor_id": mentor_id,
            "skill_id": skill_id,
            "scheduled_time": scheduled_time,
            "notes": notes,
        },
    )
    require(status == 200, f"Session request failed: HTTP {status} {body}")
    sid = body.get("session_id")
    require(isinstance(sid, int), f"session_id missing/invalid: {body}")
    return sid


def request_session(token: str, mentor_id: int, skill_id: int, hours: int, notes: str) -> int:
    return request_session_at(token, mentor_id, skill_id, iso_in_hours(hours), notes)


def list_my_sessions(token: str) -> list[Dict[str, Any]]:
    status, body = request_json("GET", "/sessions/my", token=token)
    require(status == 200, f"/sessions/my failed: HTTP {status} {body}")
    require(isinstance(body, list), f"/sessions/my response not list: {body}")
    return body


def _iso_close(a: str, b: str, seconds: int = 60) -> bool:
    try:
        da = datetime.fromisoformat(str(a).replace("Z", "+00:00"))
        db = datetime.fromisoformat(str(b).replace("Z", "+00:00"))
    except Exception:
        return False
    return abs((da - db).total_seconds()) <= seconds


def patch_session(token: str, session_id: int, action: str) -> None:
    status, body = request_json("PATCH", f"/sessions/{session_id}/{action}", token=token)
    require(status == 200, f"Session action {action} failed on {session_id}: HTTP {status} {body}")


def main() -> None:
    print(f"[INFO] BASE_URL={BASE_URL}")
    suffix = random_suffix()
    password = "Password@123"

    user_a = {
        "name": f"Dual A {suffix}",
        "email": f"dual_a_{suffix}@example.edu",
    }
    user_b = {
        "name": f"Dual B {suffix}",
        "email": f"dual_b_{suffix}@example.edu",
    }

    python_skill = f"Python Dual {suffix}"
    js_skill = f"JavaScript Dual {suffix}"

    print("\n=== 1) Register + Login ===")
    register_user(user_a["name"], user_a["email"], password)
    register_user(user_b["name"], user_b["email"], password)
    token_a = login_user(user_a["email"], password)
    token_b = login_user(user_b["email"], password)
    me_a = get_me(token_a)
    me_b = get_me(token_b)
    ok("Both users registered and logged in")

    print("\n=== 2) Add teach + learn skills for both (alias compatibility) ===")
    add_skill(token_a, python_skill, "offer")
    add_skill(token_a, js_skill, "need")
    add_skill(token_b, js_skill, "teach")
    add_skill(token_b, python_skill, "learn")
    ok("Dual-role skills added")

    print("\n=== 3) Verify can_teach/can_learn flags ===")
    me_a = get_me(token_a)
    me_b = get_me(token_b)
    require(me_a.get("can_teach") is True, f"User A can_teach not true: {me_a}")
    require(me_a.get("can_learn") is True, f"User A can_learn not true: {me_a}")
    require(me_b.get("can_teach") is True, f"User B can_teach not true: {me_b}")
    require(me_b.get("can_learn") is True, f"User B can_learn not true: {me_b}")
    ok("Capability flags are correct for both users")

    print("\n=== 4) Duplicate request guard ===")
    user_a_id = int(me_a["id"])
    user_b_id = int(me_b["id"])
    python_id = get_skill_id_by_name(python_skill)
    js_id = get_skill_id_by_name(js_skill)

    duplicate_slot = iso_in_hours(28)
    dup_1 = request_session_at(token_a, user_b_id, js_id, duplicate_slot, "Duplicate guard test")
    dup_2 = request_session_at(token_a, user_b_id, js_id, duplicate_slot, "Duplicate guard test retry")
    require(dup_2 == dup_1, f"Duplicate guard failed: expected same session_id, got {dup_1} and {dup_2}")

    sessions_a = list_my_sessions(token_a)
    matching_pending = [
        s for s in sessions_a
        if int(s.get("mentor_id", -1)) == user_b_id
        and int(s.get("skill_id", -1)) == js_id
        and s.get("status") == "Pending"
        and _iso_close(s.get("scheduled_time", ""), duplicate_slot, seconds=60)
    ]
    require(
        len(matching_pending) == 1,
        f"Expected 1 pending duplicate-guard session, found {len(matching_pending)}: {matching_pending}",
    )
    ok("Duplicate request guard returned same session and prevented duplicate row")

    # Cleanup pending test session so reciprocal flow remains deterministic.
    patch_session(token_a, dup_1, "cancel")

    print("\n=== 5) Reciprocal sessions (role swap) ===")
    a_bal_before = wallet_balance(token_a)
    b_bal_before = wallet_balance(token_b)

    # A learns JavaScript from B
    s1 = request_session(token_a, user_b_id, js_id, 30, "A learning JS from B")
    patch_session(token_b, s1, "accept")
    patch_session(token_a, s1, "complete")

    # B learns Python from A
    s2 = request_session(token_b, user_a_id, python_id, 34, "B learning Python from A")
    patch_session(token_a, s2, "accept")
    patch_session(token_b, s2, "complete")

    a_bal_after = wallet_balance(token_a)
    b_bal_after = wallet_balance(token_b)

    require(a_bal_after == a_bal_before, f"User A balance mismatch: {a_bal_before} -> {a_bal_after}")
    require(b_bal_after == b_bal_before, f"User B balance mismatch: {b_bal_before} -> {b_bal_after}")
    ok("Reciprocal sessions completed and wallet balances reconciled")

    print("\n=== 6) Recommendation endpoint sanity ===")
    status_a, recs_a = request_json("GET", "/recommend/?top_n=5", token=token_a)
    status_b, recs_b = request_json("GET", "/recommend/?top_n=5", token=token_b)
    require(status_a == 200, f"Recommendations for A failed: HTTP {status_a} {recs_a}")
    require(status_b == 200, f"Recommendations for B failed: HTTP {status_b} {recs_b}")
    require(isinstance(recs_a, list), f"Recommendations A not list: {recs_a}")
    require(isinstance(recs_b, list), f"Recommendations B not list: {recs_b}")
    ok("Recommendation endpoint returned valid responses")

    print("\n[SUCCESS] Dual-role workflow passed end-to-end.")


if __name__ == "__main__":
    main()
