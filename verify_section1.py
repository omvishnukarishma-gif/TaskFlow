"""
verify_section1.py — Automated acceptance-criteria tests for Section 1.

Uses a unique RUN_ID suffix on every email so the script is idempotent
across repeated runs without needing to flush the database.
"""

import sys
import json
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"

# Unique suffix per run — prevents email-collision failures on re-run
RUN_ID = str(int(time.time()))[-6:]

PASS = []
FAIL = []


def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as resp:
            raw = resp.read()
            response_headers = dict(resp.headers)
            try:
                payload = json.loads(raw)
            except Exception:
                payload = raw.decode()
            return resp.status, payload, response_headers
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = raw.decode()
        return e.code, payload, {}


def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL  {name}  {detail}")


# ──────────────────────────────────────────────
print("\n=== 1. USER CRUD ===")

test_email   = f"testuser_{RUN_ID}@example.com"
upd_email    = f"updated_{RUN_ID}@example.com"

s, d, _ = req("POST", "/users", {"name": "Test User", "email": test_email})
check("POST /users → 201", s == 201, f"got {s}")
check("User has id", isinstance(d.get("id"), int), str(d))
user_id = d.get("id")

s, d, _ = req("GET", "/users")
check("GET /users → 200", s == 200, f"got {s}")
check("Users list non-empty", isinstance(d, list) and len(d) > 0, str(d))

s, d, _ = req("GET", f"/users/{user_id}")
check("GET /users/{id} → 200", s == 200, f"got {s}")
check("User email matches", d.get("email") == test_email, str(d))

s, d, _ = req("PUT", f"/users/{user_id}", {"name": "Updated Name", "email": upd_email})
check("PUT /users/{id} → 200", s == 200, f"got {s}")
check("Name updated", d.get("name") == "Updated Name", str(d))

# Duplicate email → 400
s, d, _ = req("POST", "/users", {"name": "Dup", "email": upd_email})
check("Duplicate email → 400", s == 400, f"got {s}: {d}")

# Invalid email → 422
s, d, _ = req("POST", "/users", {"name": "Bad", "email": "notanemail"})
check("Invalid email → 422", s == 422, f"got {s}")

# 404
s, d, _ = req("GET", "/users/99999")
check("GET /users/99999 → 404", s == 404, f"got {s}")


# ──────────────────────────────────────────────
print("\n=== 2. PROJECT CRUD ===")

s, d, _ = req("POST", "/projects", {"name": "Test Project", "description": "Desc", "owner_id": user_id})
check("POST /projects → 201", s == 201, f"got {s}")
check("Project has id", isinstance(d.get("id"), int), str(d))
project_id = d.get("id")

s, d, _ = req("POST", "/projects", {"name": "Bad Project", "owner_id": 99999})
check("Invalid owner_id → 404", s == 404, f"got {s}: {d}")

s, d, _ = req("GET", "/projects")
check("GET /projects → 200", s == 200, f"got {s}")
check("Projects list non-empty", isinstance(d, list) and len(d) > 0, str(d))

s, d, _ = req("GET", f"/projects/{project_id}")
check("GET /projects/{id} → 200", s == 200, f"got {s}")
check("Project name matches", d.get("name") == "Test Project", str(d))

s, d, _ = req("PUT", f"/projects/{project_id}", {"name": "Renamed Project"})
check("PUT /projects/{id} → 200", s == 200, f"got {s}")
check("Name updated", d.get("name") == "Renamed Project", str(d))

s, d, _ = req("GET", "/projects/99999")
check("GET /projects/99999 → 404", s == 404, f"got {s}")


# ──────────────────────────────────────────────
print("\n=== 3. TASK CRUD ===")

s, d, _ = req("POST", "/tasks", {
    "title": "Test task", "description": "A test task",
    "priority": "high", "due_date": "2026-12-01",
    "completed": False, "project_id": project_id,
})
check("POST /tasks → 201", s == 201, f"got {s}")
check("Task has id", isinstance(d.get("id"), int), str(d))
check("Priority stored", d.get("priority") == "high", str(d))
check("due_date stored", d.get("due_date") == "2026-12-01", str(d))
task_id = d.get("id")

s, d2, _ = req("POST", "/tasks", {
    "title": "No due date task", "priority": "low",
    "due_date": None, "completed": False, "project_id": project_id,
})
check("Task with null due_date → 201", s == 201, f"got {s}")
check("due_date is null in response", d2.get("due_date") is None, str(d2))
task_id2 = d2.get("id")

s, d, _ = req("POST", "/tasks", {"title": "Bad priority", "priority": "urgent", "project_id": project_id})
check("Invalid priority → 422", s == 422, f"got {s}: {d}")

s, d, _ = req("POST", "/tasks", {"title": "Bad date", "priority": "medium", "due_date": "01/12/2026", "project_id": project_id})
check("Bad due_date format → 422", s == 422, f"got {s}: {d}")

s, d, _ = req("POST", "/tasks", {"title": "Ghost task", "priority": "medium", "project_id": 99999})
check("Invalid project_id → 404", s == 404, f"got {s}: {d}")

s, d, _ = req("GET", "/tasks")
check("GET /tasks → 200", s == 200, f"got {s}")
check("Tasks list non-empty", isinstance(d, list) and len(d) > 0, str(d))

s, d, _ = req("GET", f"/tasks/{task_id}")
check("GET /tasks/{id} → 200", s == 200, f"got {s}")
check("Task title matches", d.get("title") == "Test task", str(d))

s, d, _ = req("PUT", f"/tasks/{task_id}", {"title": "Updated task", "completed": True})
check("PUT /tasks/{id} → 200", s == 200, f"got {s}")
check("Title updated", d.get("title") == "Updated task", str(d))
check("Completed updated", d.get("completed") is True, str(d))

s, d, _ = req("GET", "/tasks/99999")
check("GET /tasks/99999 → 404", s == 404, f"got {s}")


# ──────────────────────────────────────────────
print("\n=== 4. STATISTICS (SQL aggregation) ===")

s, d, _ = req("GET", "/tasks/stats")
check("GET /tasks/stats → 200", s == 200, f"got {s}")
check("Stats has 'total'",          "total"           in d, str(d))
check("Stats has 'completed'",      "completed"       in d, str(d))
check("Stats has 'pending'",        "pending"         in d, str(d))
check("Stats has 'by_priority'",    "by_priority"     in d, str(d))
check("Stats has 'completion_rate'","completion_rate" in d, str(d))
check("total = completed + pending",
      d.get("total") == d.get("completed", 0) + d.get("pending", 0), str(d))
check("by_priority has low/medium/high",
      all(k in d.get("by_priority", {}) for k in ["low", "medium", "high"]), str(d))

s, d2, _ = req("GET", f"/tasks/stats?project_id={project_id}")
check("Stats filtered by project → 200", s == 200, f"got {s}")
check("Filtered stats total > 0", d2.get("total", 0) > 0, str(d2))


# ──────────────────────────────────────────────
print("\n=== 5. MIDDLEWARE: X-Process-Time header ===")

s, d, hdrs = req("GET", "/tasks")
xt = hdrs.get("x-process-time") or hdrs.get("X-Process-Time")
check("X-Process-Time header present", xt is not None, f"headers: {list(hdrs.keys())}")
check("X-Process-Time looks like ms", xt is not None and "ms" in xt, f"value: {xt}")


# ──────────────────────────────────────────────
print("\n=== 6. PERSISTENCE (data survives across requests) ===")

s, created, _ = req("POST", "/tasks", {"title": "Persistence check task", "priority": "medium", "project_id": project_id})
tid = created.get("id")
s2, fetched, _ = req("GET", f"/tasks/{tid}")
check("Persisted task retrievable",
      s2 == 200 and fetched.get("title") == "Persistence check task", str(fetched))


# ──────────────────────────────────────────────
print("\n=== 7. DELETE ===")

s, d, _ = req("DELETE", f"/tasks/{task_id2}")
check("DELETE /tasks/{id} → 200", s == 200, f"got {s}")
s, d, _ = req("GET", f"/tasks/{task_id2}")
check("Deleted task → 404", s == 404, f"got {s}")

s, d, _ = req("DELETE", f"/projects/{project_id}")
check("DELETE /projects/{id} → 200", s == 200, f"got {s}")

s, d, _ = req("DELETE", f"/users/{user_id}")
check("DELETE /users/{id} → 200", s == 200, f"got {s}")

s, d, _ = req("GET", f"/tasks/{task_id}")
check("Cascade: task deleted with project → 404", s == 404, f"got {s}")


# ──────────────────────────────────────────────
print("\n=== 8. CORS ===")

# Use one of the explicitly allowed origins
cors_req = urllib.request.Request(
    BASE + "/tasks",
    headers={
        "Origin": "http://localhost:8000",
        "Access-Control-Request-Method": "GET",
    },
    method="OPTIONS",
)
try:
    with urllib.request.urlopen(cors_req) as resp:
        cors_hdrs = dict(resp.headers)
        acao = cors_hdrs.get("access-control-allow-origin", "")
        check("CORS allow-origin header present", bool(acao), f"headers: {list(cors_hdrs.keys())}")
        check("CORS origin is explicit (not *)", acao == "http://localhost:8000", f"acao={acao!r}")
except urllib.error.HTTPError as e:
    cors_hdrs = dict(e.headers)
    acao = cors_hdrs.get("access-control-allow-origin", "")
    check("CORS allow-origin header present", bool(acao), f"status={e.code} headers={list(cors_hdrs.keys())}")
    check("CORS origin is explicit (not *)", acao == "http://localhost:8000", f"acao={acao!r}")


# ──────────────────────────────────────────────
print("\n" + "=" * 50)
print(f"PASSED: {len(PASS)}  FAILED: {len(FAIL)}")
if FAIL:
    print("\nFailed tests:")
    for f in FAIL:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
    sys.exit(0)
