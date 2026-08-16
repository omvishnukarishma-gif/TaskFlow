"""Focused authentication tests against the running TaskFlow server.

Schema (from /openapi.json):
  RegisterRequest: { name, email, password }
  LoginRequest:    { email, password }
  AuthResponse:    { token, user_id, user_name, user_email, message }

/auth/me  and /auth/logout use Authorization: Bearer <token>
"""
import urllib.request
import urllib.error
import json
import time

BASE = "http://127.0.0.1:8000"
UNIQUE = str(int(time.time()))
EMAIL = "testauth_" + UNIQUE + "@example.com"
DISPLAY_NAME = "TestAuth " + UNIQUE
PASSWORD = "SecurePass123!"
WRONG_PASSWORD = "WrongPassword999!"

results = []

def req(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}, dict(resp.headers)
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else {}, dict(e.headers)

def check(name, condition, detail):
    label = "PASS" if condition else "FAIL"
    print("  " + label + "  " + name + ": " + str(detail))
    results.append(condition)

print()
print("=== FOCUSED AUTHENTICATION TESTS ===")
print("  email: " + EMAIL)
print()

# ── 1. Register new unique user ──────────────────────────────────────────────
print("--- 1. Register new unique user ---")
status, body, hdrs = req("POST", "/auth/register", {
    "name": DISPLAY_NAME,
    "email": EMAIL,
    "password": PASSWORD
})
reg_ok = status == 201
detail_str = str(body.get("detail", ""))[:120] if isinstance(body, dict) else str(body)[:120]
check("POST /auth/register -> 201", reg_ok,
      "status=" + str(status) + " " + (str(list(body.keys())) if isinstance(body, dict) else detail_str))

if not reg_ok:
    print("  NOTE: Register failed with: " + detail_str)

# Token comes from register response
register_token = None
if reg_ok and isinstance(body, dict):
    register_token = body.get("token")
    check("Register response has token", register_token is not None,
          "token=" + ("present" if register_token else "MISSING"))
    check("Register response has user_id", "user_id" in body,
          "user_id=" + str(body.get("user_id")))
    check("Register user_email matches", body.get("user_email") == EMAIL,
          "user_email=" + str(body.get("user_email")))

# ── 2. Duplicate email registration must be rejected ─────────────────────────
print()
print("--- 2. Duplicate email must be rejected ---")
status2, body2, _ = req("POST", "/auth/register", {
    "name": "Dup User " + UNIQUE,
    "email": EMAIL,
    "password": "AnotherPass456!"
})
dup_ok = status2 in (400, 409, 422)
detail2 = str(body2.get("detail", body2))[:120] if isinstance(body2, dict) else str(body2)[:120]
check("Duplicate email -> 400/409/422", dup_ok,
      "status=" + str(status2) + " detail=" + detail2)

# ── 3. Login with correct password must succeed ──────────────────────────────
print()
print("--- 3. Login with correct password ---")
status3, body3, hdrs3 = req("POST", "/auth/login", {
    "email": EMAIL,
    "password": PASSWORD
})
login_ok = status3 == 200
check("POST /auth/login -> 200", login_ok,
      "status=" + str(status3) + " keys=" + str(list(body3.keys()) if isinstance(body3, dict) else body3))

session_token = None
if login_ok and isinstance(body3, dict):
    session_token = body3.get("token")
    check("Login response has token", session_token is not None,
          "token=" + ("present" if session_token else "MISSING"))
    check("Login response has user_id", "user_id" in body3,
          "user_id=" + str(body3.get("user_id")))
    check("Login user_email matches", body3.get("user_email") == EMAIL,
          "user_email=" + str(body3.get("user_email")))

# ── 4. Login with wrong password must fail ───────────────────────────────────
print()
print("--- 4. Login with wrong password ---")
status4, body4, _ = req("POST", "/auth/login", {
    "email": EMAIL,
    "password": WRONG_PASSWORD
})
wrong_pw_ok = status4 in (400, 401, 403)
detail4 = str(body4.get("detail", body4))[:120] if isinstance(body4, dict) else str(body4)[:120]
check("Wrong password -> 400/401/403", wrong_pw_ok,
      "status=" + str(status4) + " detail=" + detail4)

# ── 5. Successful login creates a session ────────────────────────────────────
print()
print("--- 5. Session created on login ---")
check("Session token obtained from login", session_token is not None,
      "token=" + ("present" if session_token else "MISSING"))

# ── 6. Verify session behavior — /auth/me with valid token ───────────────────
print()
print("--- 6. Session verification with /auth/me ---")
if session_token:
    status6, body6, _ = req("GET", "/auth/me", token=session_token)
    me_ok = status6 == 200
    check("GET /auth/me with valid token -> 200", me_ok,
          "status=" + str(status6) + " body=" + str(body6)[:120])
    if me_ok and isinstance(body6, dict):
        has_correct_user = (body6.get("user_email") == EMAIL or
                            body6.get("email") == EMAIL or
                            body6.get("user_name") == DISPLAY_NAME or
                            body6.get("name") == DISPLAY_NAME)
        check("/auth/me returns correct user info", has_correct_user,
              "user_email=" + str(body6.get("user_email")) +
              " email=" + str(body6.get("email")) +
              " user_name=" + str(body6.get("user_name")))
else:
    check("GET /auth/me with valid token -> 200", False, "SKIPPED - no session token")
    check("/auth/me returns correct user info", False, "SKIPPED - no session token")

# 6b. /auth/me WITHOUT token must return 401
print()
print("--- 6b. /auth/me without token must be rejected ---")
status6b, body6b, _ = req("GET", "/auth/me")
no_token_ok = status6b in (401, 403)
detail6b = str(body6b.get("detail", body6b))[:80] if isinstance(body6b, dict) else str(body6b)[:80]
check("GET /auth/me without token -> 401/403", no_token_ok,
      "status=" + str(status6b) + " detail=" + detail6b)

# ── 7. Logout must invalidate the session ────────────────────────────────────
print()
print("--- 7. Logout invalidates session ---")
if session_token:
    status7, body7, _ = req("POST", "/auth/logout", token=session_token)
    logout_ok = status7 in (200, 204)
    check("POST /auth/logout -> 200/204", logout_ok,
          "status=" + str(status7) + " body=" + str(body7)[:80])

    # After logout, /auth/me with the same token must fail
    status7b, body7b, _ = req("GET", "/auth/me", token=session_token)
    invalidated_ok = status7b in (401, 403)
    detail7b = str(body7b.get("detail", body7b))[:80] if isinstance(body7b, dict) else str(body7b)[:80]
    check("POST-LOGOUT /auth/me rejected -> 401/403", invalidated_ok,
          "status=" + str(status7b) + " detail=" + detail7b)
else:
    check("POST /auth/logout -> 200/204", False, "SKIPPED - no session token")
    check("POST-LOGOUT /auth/me rejected -> 401/403", False, "SKIPPED - no session token")

# ── Summary ───────────────────────────────────────────────────────────────────
print()
passed = sum(1 for r in results if r)
failed = sum(1 for r in results if not r)
print("=" * 54)
print("Auth tests: " + str(passed) + " passed, " + str(failed) + " failed")
if failed == 0:
    print("ALL AUTH TESTS PASSED")
else:
    print("FAILURES: " + str(failed))
