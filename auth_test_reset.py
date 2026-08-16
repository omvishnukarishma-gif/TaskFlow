"""
auth_test_reset.py — Password-reset feature tests for TaskFlow.

Tests:
  1.  forgot-password with unknown email          → 200, generic message, no dev_token
  2.  forgot-password with email that has no password (no hash) → 200, no dev_token
  3.  forgot-password with known+registered email → 200, dev_token present
  4.  reset-password with valid token + new password → 200
  5.  login with NEW password                     → 200 (hash updated)
  6.  login with OLD password                     → 401 (hash replaced)
  7.  reset-password with SAME token again        → 400 (single-use)
  8.  reset-password with garbage token           → 400
  9.  reset-password with new_password < 8 chars  → 422
  10. reset-password missing token field          → 422
  11. GET /auth/me with pre-reset session token   → 401 (sessions invalidated)
  12. forgot-password for email with no password_hash → 200, no dev_token
  13. Multiple forgot-password requests: second replaces first (old token unusable)
  14. Successful login with new password creates a valid session

All HTTP calls use only urllib (no third-party libs).
Requires the server to be running at http://127.0.0.1:8000 with TASKFLOW_ENV != production.
"""

import json
import sqlite3
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE    = "http://127.0.0.1:8000"
UNIQUE  = str(int(time.time()))
EMAIL   = f"testreset_{UNIQUE}@example.com"
NAME    = f"TestReset {UNIQUE}"
OLD_PW  = "OldPassword123!"
NEW_PW  = "NewPassword456!"
BAD_PW  = "short"           # < 8 chars
DB_PATH = "taskflow.db"

results = []


def req(method, path, body=None, token=None):
    url  = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"Content-Type": "application/json"}
    if token:
        hdrs["Authorization"] = "Bearer " + token
    r = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {}), dict(resp.headers)
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, (json.loads(raw) if raw else {}), dict(e.headers)


def check(name, condition, detail=""):
    label = "PASS" if condition else "FAIL"
    print(f"  {label}  {name}: {detail}")
    results.append((name, condition))


# ── Fixture: register a fresh user ───────────────────────────────────────────

print()
print("=== PASSWORD RESET TESTS ===")
print(f"  email: {EMAIL}")
print()

print("--- Fixture: register test user ---")
s, b, _ = req("POST", "/auth/register", {"name": NAME, "email": EMAIL, "password": OLD_PW})
check("Register test user → 201", s == 201, f"status={s}")
if s != 201:
    print("  FATAL: cannot continue without a registered user.")
    import sys; sys.exit(1)

# Keep the session token that was returned at registration (we'll test that
# it is invalidated after password reset).
pre_reset_session_token = b.get("token", "")

# Log in to also obtain a proper login-session token.
s, b, _ = req("POST", "/auth/login", {"email": EMAIL, "password": OLD_PW})
check("Login with old password (fixture) → 200", s == 200, f"status={s}")
login_session_token = b.get("token", "")

# ── 1. forgot-password with UNKNOWN email ────────────────────────────────────

print()
print("--- 1. forgot-password with unknown email ---")
unknown = f"nobody_{UNIQUE}@nowhere.example.com"
s, b, _ = req("POST", "/auth/forgot-password", {"email": unknown})
check("Unknown email → 200",          s == 200,             f"status={s}")
check("Unknown email → generic detail", "detail" in b,      f"keys={list(b)}")
check("Unknown email → no dev_token",  "dev_token" not in b, f"keys={list(b)}")

# ── 2. forgot-password with email that exists but has NO password_hash ───────

print()
print("--- 2. forgot-password with email that has no password hash ---")
# Create a legacy user via /users (no password_hash)
no_pw_email = f"nopw_{UNIQUE}@example.com"
s2u, b2u, _ = req("POST", "/users", {"name": f"NoPw {UNIQUE}", "email": no_pw_email})
if s2u == 201:
    s, b, _ = req("POST", "/auth/forgot-password", {"email": no_pw_email})
    check("No-password email → 200",           s == 200,              f"status={s}")
    check("No-password email → no dev_token",  "dev_token" not in b,  f"keys={list(b)}")
else:
    check("No-password email → 200",          False, f"SKIPPED (could not create user: {s2u})")
    check("No-password email → no dev_token", False, "SKIPPED")

# ── 3. forgot-password with known registered email ───────────────────────────

print()
print("--- 3. forgot-password with known registered email ---")
s, b, _ = req("POST", "/auth/forgot-password", {"email": EMAIL})
check("Known email → 200",            s == 200,            f"status={s}")
check("Known email → detail present", "detail" in b,       f"keys={list(b)}")
check("Known email → dev_token present", "dev_token" in b, f"keys={list(b)}")

raw_token = b.get("dev_token", "")

# ── 4. reset-password with valid token + new password ────────────────────────

print()
print("--- 4. reset-password: valid token + new password ---")
s, b, _ = req("POST", "/auth/reset-password", {
    "token": raw_token,
    "new_password": NEW_PW,
})
check("Valid reset → 200",            s == 200,    f"status={s}")
check("Valid reset → detail present", "detail" in b, f"body={b}")

# ── 5. Login with NEW password ───────────────────────────────────────────────

print()
print("--- 5. Login with new password after reset ---")
s, b, _ = req("POST", "/auth/login", {"email": EMAIL, "password": NEW_PW})
check("Login with new password → 200", s == 200, f"status={s}")
new_session_token = b.get("token", "")
check("New session token obtained",    bool(new_session_token), f"token={'present' if new_session_token else 'MISSING'}")

# ── 6. Login with OLD password must fail ─────────────────────────────────────

print()
print("--- 6. Login with old password after reset (must fail) ---")
s, b, _ = req("POST", "/auth/login", {"email": EMAIL, "password": OLD_PW})
check("Login with old password → 401", s in (400, 401, 403), f"status={s}")

# ── 7. Replay the same token → must be rejected (single-use) ─────────────────

print()
print("--- 7. Replay used token → 400 ---")
s, b, _ = req("POST", "/auth/reset-password", {
    "token": raw_token,
    "new_password": "AnotherNew789!",
})
check("Used token → 400", s == 400, f"status={s}")

# ── 8. Garbage token → 400 ───────────────────────────────────────────────────

print()
print("--- 8. Garbage token → 400 ---")
s, b, _ = req("POST", "/auth/reset-password", {
    "token": "thisisnotarealtoken_garbage",
    "new_password": "SomePass999!",
})
check("Garbage token → 400", s == 400, f"status={s}")

# ── 9. new_password too short → 422 (Pydantic validation) ────────────────────

print()
print("--- 9. new_password < 8 chars → 422 ---")
s, b, _ = req("POST", "/auth/reset-password", {
    "token": "anytoken",
    "new_password": BAD_PW,
})
check("Short password → 422", s == 422, f"status={s}")

# ── 10. Missing token field → 422 ────────────────────────────────────────────

print()
print("--- 10. Missing token field → 422 ---")
s, b, _ = req("POST", "/auth/reset-password", {"new_password": NEW_PW})
check("Missing token → 422", s == 422, f"status={s}")

# ── 11. Pre-reset session token must be invalidated ─────────────────────────

print()
print("--- 11. Pre-reset session tokens invalidated ---")
# Both the registration-time token and the login-session token obtained
# before the reset should now return 401.
s_reg, _, _ = req("GET", "/auth/me", token=pre_reset_session_token)
check("Pre-reset register token → 401", s_reg in (401, 403),
      f"status={s_reg}")

s_log, _, _ = req("GET", "/auth/me", token=login_session_token)
check("Pre-reset login token → 401",    s_log in (401, 403),
      f"status={s_log}")

# The NEW session obtained after reset should still be valid.
s_new, _, _ = req("GET", "/auth/me", token=new_session_token)
check("Post-reset new session token → 200", s_new == 200, f"status={s_new}")

# ── 12. Expired token → 400 (injected directly into DB) ──────────────────────

print()
print("--- 12. Expired token → 400 ---")
try:
    import hashlib

    expired_raw   = "expiredtoken_test_" + UNIQUE
    expired_hash  = hashlib.sha256(expired_raw.encode()).hexdigest()
    now_utc       = datetime.now(timezone.utc)
    expired_at    = (now_utc - timedelta(minutes=30)).isoformat()

    # Look up the user id from the DB
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = ?", (EMAIL,))
    row  = c.fetchone()
    if row:
        uid = row[0]
        c.execute(
            "INSERT INTO password_reset_tokens "
            "(token_hash, user_id, created_at, expires_at, used) "
            "VALUES (?, ?, ?, ?, 0)",
            (expired_hash, uid, (now_utc - timedelta(hours=1)).isoformat(), expired_at),
        )
        conn.commit()
    conn.close()

    s, b, _ = req("POST", "/auth/reset-password", {
        "token": expired_raw,
        "new_password": "ShouldFail123!",
    })
    check("Expired token → 400", s == 400, f"status={s}")
except Exception as exc:
    check("Expired token → 400", False, f"ERROR: {exc}")

# ── 13. Second forgot-password request replaces first token ──────────────────

print()
print("--- 13. Second forgot-password request obsoletes first ---")
# Request #1
s1, b1, _ = req("POST", "/auth/forgot-password", {"email": EMAIL})
first_token = b1.get("dev_token", "")
check("First forgot-password → 200 + dev_token", s1 == 200 and bool(first_token),
      f"status={s1} dev_token={'present' if first_token else 'MISSING'}")

# Request #2
s2, b2, _ = req("POST", "/auth/forgot-password", {"email": EMAIL})
second_token = b2.get("dev_token", "")
check("Second forgot-password → 200 + dev_token", s2 == 200 and bool(second_token),
      f"status={s2} dev_token={'present' if second_token else 'MISSING'}")

# The first token should now be unusable (deleted by second request)
if first_token:
    s_old, _, _ = req("POST", "/auth/reset-password", {
        "token": first_token,
        "new_password": "FirstToken123!",
    })
    check("First token after second request → 400", s_old == 400, f"status={s_old}")

# ── 14. Use second token successfully ────────────────────────────────────────

print()
print("--- 14. Use second token for a successful reset ---")
if second_token:
    s, b, _ = req("POST", "/auth/reset-password", {
        "token": second_token,
        "new_password": OLD_PW,   # reset back to original for cleanup tidiness
    })
    check("Second token reset → 200", s == 200, f"status={s}")
    # Confirm login with the restored password
    s_l, _, _ = req("POST", "/auth/login", {"email": EMAIL, "password": OLD_PW})
    check("Login with restored password → 200", s_l == 200, f"status={s_l}")
else:
    check("Second token reset → 200", False, "SKIPPED (no second token)")
    check("Login with restored password → 200", False, "SKIPPED")

# ── Cleanup: delete the test user (and legacy no-pw user) ────────────────────

print()
print("--- Cleanup ---")
# Find the test user's id and delete via /users
s_u, body_u, _ = req("GET", "/users")
if s_u == 200 and isinstance(body_u, list):
    for u in body_u:
        if u.get("email") in (EMAIL, no_pw_email):
            sd, _, _ = req("DELETE", f"/users/{u['id']}")
            check(f"Deleted user {u['email']}", sd == 200, f"status={sd}")

# ── Summary ───────────────────────────────────────────────────────────────────

print()
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
print("=" * 54)
print(f"Reset tests: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL RESET TESTS PASSED")
else:
    print(f"FAILURES: {failed}")
    for name, ok in results:
        if not ok:
            print(f"  FAIL  {name}")
    import sys; sys.exit(1)
