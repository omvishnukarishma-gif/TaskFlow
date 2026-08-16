"""
verify_section2.py -- Live endpoint tests for Section 2 (Algorithms Engine).

Covers:
  - GET /tasks?sort=priority  (insertion sort, low->medium->high ordering)
  - GET /tasks/search?title=...&algo=binary  (default algo)
  - GET /tasks/search?title=...&algo=linear
  - GET /tasks/search?title=<not found>&algo=binary  -> 404
  - GET /tasks/search?title=<not found>&algo=linear  -> 404
  - default algo=binary when algo param omitted
  - steps/algorithm fields present in search response
  - binary steps < linear steps (same target)
  - Section 1 regression: all original CRUD + stats still work

Requires the server to be running at http://127.0.0.1:8000
and the database seeded with at least a few tasks of mixed priorities.
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"
RUN_ID = str(int(time.time()))[-6:]

PASS_LIST = []
FAIL_LIST = []


def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    request = urllib.request.Request(
        url, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request) as resp:
            raw = resp.read()
            hdrs = dict(resp.headers)
            try:
                payload = json.loads(raw)
            except Exception:
                payload = raw.decode()
            return resp.status, payload, hdrs
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = raw.decode()
        return e.code, payload, {}


def check(name, condition, detail=""):
    if condition:
        PASS_LIST.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL_LIST.append(name)
        print(f"  FAIL  {name}  {detail}")


# ===========================================================
print("\n=== FIXTURE SETUP ===")

s, user, _ = req("POST", "/users", {
    "name": "Algo Tester",
    "email": f"algotester_{RUN_ID}@example.com",
})
check("Fixture: create test user", s == 201, str(user))
user_id = user.get("id")

s, proj, _ = req("POST", "/projects", {
    "name": f"Algo Project {RUN_ID}",
    "owner_id": user_id,
})
check("Fixture: create test project", s == 201, str(proj))
proj_id = proj.get("id")

task_ids = {}
for priority, title in [
    ("low",    f"Low Priority Task {RUN_ID}"),
    ("medium", f"Medium Priority Task {RUN_ID}"),
    ("high",   f"High Priority Task {RUN_ID}"),
    ("high",   f"Another High Task {RUN_ID}"),
]:
    s, t, _ = req("POST", "/tasks", {
        "title":       title,
        "priority":    priority,
        "project_id":  proj_id,
    })
    check(f"Fixture: create {priority} task", s == 201, str(t))
    task_ids[title] = t.get("id")

search_target_low    = f"Low Priority Task {RUN_ID}"
search_target_medium = f"Medium Priority Task {RUN_ID}"
search_target_high   = f"High Priority Task {RUN_ID}"


# ===========================================================
print("\n=== 1. GET /tasks?sort=priority ===")

s, tasks, hdrs = req("GET", "/tasks?sort=priority")
check("Sort: HTTP 200", s == 200, f"got {s}")
check("Sort: returns a list", isinstance(tasks, list), str(type(tasks)))
check("Sort: list non-empty", len(tasks) > 0, "empty list")

WEIGHT = {"low": 1, "medium": 2, "high": 3}
weights = [WEIGHT.get(t["priority"], -1) for t in tasks]
is_sorted = all(weights[i] <= weights[i + 1] for i in range(len(weights) - 1))
check("Sort: result is low->medium->high ordered", is_sorted,
      f"priority sequence: {[t['priority'] for t in tasks]}")

priorities_in_result = {t["priority"] for t in tasks}
check("Sort: low tasks present", "low" in priorities_in_result)
check("Sort: medium tasks present", "medium" in priorities_in_result)
check("Sort: high tasks present", "high" in priorities_in_result)

check("Sort: all fixture tasks present in result",
      all(tid in [t["id"] for t in tasks] for tid in task_ids.values()),
      "some fixture task ids missing")


# ===========================================================
print("\n=== 2. Binary search -- found ===")

enc_title = urllib.parse.quote(search_target_low)
s, data, _ = req("GET", f"/tasks/search?title={enc_title}&algo=binary")
check("Binary search: HTTP 200", s == 200, f"got {s}")
check("Binary search: 'tasks' key present", "tasks" in data, str(data))
check("Binary search: 'steps' key present", "steps" in data, str(data))
check("Binary search: 'algorithm' key present", "algorithm" in data, str(data))
check("Binary search: 'count' key present", "count" in data, str(data))
check("Binary search: algorithm == 'binary'", data.get("algorithm") == "binary",
      str(data.get("algorithm")))
check("Binary search: found exactly 1 result", data.get("count") == 1,
      f"count={data.get('count')}")
tasks_in_result = data.get("tasks", [])
check("Binary search: result title matches",
      len(tasks_in_result) > 0 and tasks_in_result[0]["title"] == search_target_low,
      str(tasks_in_result))
check("Binary search: steps > 0", data.get("steps", 0) > 0,
      f"steps={data.get('steps')}")

enc_med = urllib.parse.quote(search_target_medium)
s, data_med, _ = req("GET", f"/tasks/search?title={enc_med}&algo=binary")
check("Binary search medium: found 1", data_med.get("count") == 1,
      f"count={data_med.get('count')}")

enc_high = urllib.parse.quote(search_target_high)
s, data_high, _ = req("GET", f"/tasks/search?title={enc_high}&algo=binary")
check("Binary search high: found 1", data_high.get("count") == 1,
      f"count={data_high.get('count')}")


# ===========================================================
print("\n=== 3. Default algo = binary ===")

s, data_default, _ = req("GET", f"/tasks/search?title={enc_title}")
check("Default algo: HTTP 200", s == 200, f"got {s}")
check("Default algo: algorithm == 'binary'",
      data_default.get("algorithm") == "binary",
      str(data_default.get("algorithm")))
check("Default algo: found the same task",
      data_default.get("count") == 1, f"count={data_default.get('count')}")


# ===========================================================
print("\n=== 4. Linear search -- found ===")

s, data_lin, _ = req("GET", f"/tasks/search?title={enc_title}&algo=linear")
check("Linear search: HTTP 200", s == 200, f"got {s}")
check("Linear search: algorithm == 'linear'",
      data_lin.get("algorithm") == "linear",
      str(data_lin.get("algorithm")))
check("Linear search: found exactly 1 result", data_lin.get("count") == 1,
      f"count={data_lin.get('count')}")
lin_tasks = data_lin.get("tasks", [])
check("Linear search: result title matches",
      len(lin_tasks) > 0 and lin_tasks[0]["title"] == search_target_low,
      str(lin_tasks))
check("Linear search: steps > 0", data_lin.get("steps", 0) > 0,
      f"steps={data_lin.get('steps')}")


# ===========================================================
print("\n=== 5. Binary steps < linear steps ===")

bin_steps = data.get("steps", 9999)
lin_steps = data_lin.get("steps", 0)
check("Binary steps < linear steps",
      bin_steps < lin_steps,
      f"binary={bin_steps}, linear={lin_steps}")
check("Linear steps > 0", lin_steps > 0, f"lin_steps={lin_steps}")


# ===========================================================
print("\n=== 6. Not-found behaviour ===")

ghost = urllib.parse.quote("This Task Does Not Exist XYZ999")

s, nf_bin, _ = req("GET", f"/tasks/search?title={ghost}&algo=binary")
check("Binary not-found: HTTP 404",   s == 404, f"got {s}")

s, nf_lin, _ = req("GET", f"/tasks/search?title={ghost}&algo=linear")
check("Linear not-found: HTTP 404",   s == 404, f"got {s}")


# ===========================================================
print("\n=== 7. Section 1 regression ===")

s, all_tasks, _ = req("GET", "/tasks")
check("Regression: GET /tasks 200", s == 200, f"got {s}")
check("Regression: tasks is a list", isinstance(all_tasks, list))

s, stats, _ = req("GET", "/tasks/stats")
check("Regression: GET /tasks/stats 200", s == 200, f"got {s}")
check("Regression: stats has total", "total" in stats, str(stats))
check("Regression: total = completed + pending",
      stats["total"] == stats["completed"] + stats["pending"])

first_task_id = task_ids.get(search_target_low)
s, one, _ = req("GET", f"/tasks/{first_task_id}")
check("Regression: GET /tasks/{id} 200", s == 200, f"got {s}")
check("Regression: correct task returned",
      one.get("title") == search_target_low, str(one))

s, users_list, _ = req("GET", "/users")
check("Regression: GET /users 200", s == 200, f"got {s}")
s, projs_list, _ = req("GET", "/projects")
check("Regression: GET /projects 200", s == 200, f"got {s}")

s, _, hdrs2 = req("GET", "/tasks")
xpt = hdrs2.get("x-process-time") or hdrs2.get("X-Process-Time")
check("Regression: X-Process-Time header present", xpt is not None,
      f"headers: {list(hdrs2.keys())}")

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
        ch = dict(resp.headers)
except urllib.error.HTTPError as e:
    ch = dict(e.headers)
acao = ch.get("access-control-allow-origin", "")
check("Regression: CORS origin is explicit (not *)",
      acao == "http://localhost:8000", f"got: {acao!r}")

s, _, _ = req("POST", "/tasks", {
    "title": "Bad", "priority": "critical", "project_id": proj_id
})
check("Regression: invalid priority still 422", s == 422, f"got {s}")


# ===========================================================
print("\n=== 8. TEARDOWN ===")

s, _, _ = req("DELETE", f"/users/{user_id}")
check("Teardown: delete test user (cascades projects+tasks)", s == 200, f"got {s}")

s, _, _ = req("GET", f"/tasks/{first_task_id}")
check("Teardown: cascaded task gone (404)", s == 404, f"got {s}")


# ===========================================================
print(f"\n{'='*55}")
print(f"PASSED: {len(PASS_LIST)}  FAILED: {len(FAIL_LIST)}")

if FAIL_LIST:
    print("\nFailed tests:")
    for f in FAIL_LIST:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
    sys.exit(0)
