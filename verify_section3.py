"""
verify_section3.py — Live endpoint tests for Section 3: AI Quick-Add.

Tests:
  - POST /tasks/quick-add basic valid request -> 201 + real DB row
  - database persistence (GET /tasks/{id} after quick-add)
  - task appears in GET /tasks list
  - task visible in GET /tasks/stats
  - nonexistent project -> 422
  - malformed request (missing description) -> 422
  - empty description -> Untitled task
  - whitespace-only description -> Untitled task
  - high priority keywords
  - low priority keywords
  - medium default (no keywords)
  - repeated priority keywords stripped
  - next weekday date phrase
  - bare weekday date phrase
  - repeated date phrase removed
  - title fallback when only keywords given
  - all four mandatory regression cases (via live endpoint)
  - integration: quick-added task visible in GET /tasks/{id}, list, stats

Requires server running at http://127.0.0.1:8000
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
            try:
                payload = json.loads(raw)
            except Exception:
                payload = raw.decode()
            return resp.status, payload
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = raw.decode()
        return e.code, payload


def check(name, condition, detail=""):
    if condition:
        PASS_LIST.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL_LIST.append(name)
        print(f"  FAIL  {name}  — {detail}" if detail else f"  FAIL  {name}")


def qa(description, project_id):
    """POST to /tasks/quick-add."""
    return req("POST", "/tasks/quick-add",
               {"description": description, "project_id": project_id})


# ──────────────────────────────────────────────
# Fixture
# ──────────────────────────────────────────────
print("\n=== FIXTURE ===")

s, user = req("POST", "/users", {
    "name": "QA Tester",
    "email": f"qatester_{RUN_ID}@example.com",
})
check("Fixture: create user", s == 201, str(user))
uid = user.get("id")

s, proj = req("POST", "/projects", {
    "name": f"QA Project {RUN_ID}",
    "owner_id": uid,
})
check("Fixture: create project", s == 201, str(proj))
pid = proj.get("id")

created_task_ids = []   # track all quick-added task ids for cleanup/integration


# ──────────────────────────────────────────────
# 1. Basic valid quick-add -> 201
# ──────────────────────────────────────────────
print("\n=== 1. Valid quick-add -> 201 ===")

s, t = qa("Buy groceries", pid)
check("Valid quick-add -> 201", s == 201, f"got {s}: {t}")
check("Returns task id",   isinstance(t.get("id"), int),   str(t))
check("Returns title",     isinstance(t.get("title"), str), str(t))
check("Returns priority",  t.get("priority") in ("low","medium","high"), str(t))
check("Returns project_id matches", t.get("project_id") == pid, str(t))
check("completed is False", t.get("completed") is False, str(t))
basic_task_id = t.get("id")
created_task_ids.append(basic_task_id)


# ──────────────────────────────────────────────
# 2. Database persistence
# ──────────────────────────────────────────────
print("\n=== 2. Database persistence ===")

s, fetched = req("GET", f"/tasks/{basic_task_id}")
check("Persisted: GET /tasks/{id} -> 200",        s == 200,       f"got {s}")
check("Persisted: title matches",
      fetched.get("title") == "Buy groceries",   str(fetched))
check("Persisted: same project_id",
      fetched.get("project_id") == pid,          str(fetched))


# ──────────────────────────────────────────────
# 3. Task visible in GET /tasks list
# ──────────────────────────────────────────────
print("\n=== 3. Visible in task list ===")

s, all_tasks = req("GET", "/tasks")
check("List: GET /tasks -> 200", s == 200, f"got {s}")
task_ids_in_list = [t["id"] for t in all_tasks]
check("List: quick-added task present", basic_task_id in task_ids_in_list,
      f"id={basic_task_id} not in {task_ids_in_list[:5]}...")


# ──────────────────────────────────────────────
# 4. Visible in project stats
# ──────────────────────────────────────────────
print("\n=== 4. Visible in project stats ===")

s, stats = req("GET", f"/tasks/stats?project_id={pid}")
check("Stats: GET /tasks/stats -> 200", s == 200, f"got {s}")
check("Stats: total >= 1 for this project",
      stats.get("total", 0) >= 1, str(stats))


# ──────────────────────────────────────────────
# 5. Non-existent project -> 422
# ──────────────────────────────────────────────
print("\n=== 5. Nonexistent project -> 422 ===")

s, d = qa("Some task", 99999)
check("Nonexistent project -> 422", s == 422, f"got {s}: {d}")


# ──────────────────────────────────────────────
# 6. Malformed request -> 422
# ──────────────────────────────────────────────
print("\n=== 6. Malformed request -> 422 ===")

# Missing description field
s, d = req("POST", "/tasks/quick-add", {"project_id": pid})
check("Missing description -> 422", s == 422, f"got {s}")

# Missing project_id
s, d = req("POST", "/tasks/quick-add", {"description": "some task"})
check("Missing project_id -> 422", s == 422, f"got {s}")

# Empty body
s, d = req("POST", "/tasks/quick-add", {})
check("Empty body -> 422", s == 422, f"got {s}")


# ──────────────────────────────────────────────
# 7. Empty description -> Untitled task
# ──────────────────────────────────────────────
print("\n=== 7. Empty / whitespace description ===")

s, t = qa("", pid)
check("Empty description -> 201",       s == 201, f"got {s}")
check("Empty description -> Untitled task",
      t.get("title") == "Untitled task", f"title={t.get('title')!r}")
created_task_ids.append(t.get("id"))

s, t = qa("   ", pid)
check("Whitespace description -> 201",  s == 201, f"got {s}")
check("Whitespace description -> Untitled task",
      t.get("title") == "Untitled task", f"title={t.get('title')!r}")
created_task_ids.append(t.get("id"))


# ──────────────────────────────────────────────
# 8. High priority
# ──────────────────────────────────────────────
print("\n=== 8. High priority ===")

s, t = qa("Fix login bug urgent", pid)
check("urgent -> 201", s == 201, f"got {s}")
check("urgent -> priority high", t.get("priority") == "high",
      f"priority={t.get('priority')!r}")
check("urgent -> keyword stripped from title",
      "urgent" not in t.get("title","").lower(),
      f"title={t.get('title')!r}")
created_task_ids.append(t.get("id"))

s, t = qa("ASAP deploy hotfix", pid)
check("ASAP -> 201", s == 201, f"got {s}")
check("ASAP -> priority high", t.get("priority") == "high",
      f"priority={t.get('priority')!r}")
check("ASAP -> stripped from title",
      "asap" not in t.get("title","").lower(),
      f"title={t.get('title')!r}")
created_task_ids.append(t.get("id"))


# ──────────────────────────────────────────────
# 9. Low priority
# ──────────────────────────────────────────────
print("\n=== 9. Low priority ===")

s, t = qa("Clean desk whenever", pid)
check("whenever -> 201", s == 201, f"got {s}")
check("whenever -> priority low", t.get("priority") == "low",
      f"priority={t.get('priority')!r}")
check("whenever -> stripped from title",
      "whenever" not in t.get("title","").lower(),
      f"title={t.get('title')!r}")
created_task_ids.append(t.get("id"))

s, t = qa("This is a low priority errand", pid)
check("low priority -> 201", s == 201, f"got {s}")
check("low priority -> priority low", t.get("priority") == "low",
      f"priority={t.get('priority')!r}")
created_task_ids.append(t.get("id"))


# ──────────────────────────────────────────────
# 10. Medium default
# ──────────────────────────────────────────────
print("\n=== 10. Medium default ===")

s, t = qa("Read the documentation", pid)
check("no keywords -> 201",       s == 201, f"got {s}")
check("no keywords -> medium",    t.get("priority") == "medium",
      f"priority={t.get('priority')!r}")
check("no keywords -> title unchanged",
      t.get("title") == "Read the documentation",
      f"title={t.get('title')!r}")
created_task_ids.append(t.get("id"))


# ──────────────────────────────────────────────
# 11. Repeated priority keywords stripped
# ──────────────────────────────────────────────
print("\n=== 11. Repeated priority keywords stripped ===")

s, t = qa("urgent fix this urgent bug asap", pid)
check("repeated urgent/asap -> 201", s == 201, f"got {s}")
check("repeated -> high priority",   t.get("priority") == "high",
      f"priority={t.get('priority')!r}")
title = t.get("title", "")
check("all 'urgent' occurrences stripped", "urgent" not in title.lower(),
      f"title={title!r}")
check("all 'asap' occurrences stripped", "asap" not in title.lower(),
      f"title={title!r}")
created_task_ids.append(t.get("id"))


# ──────────────────────────────────────────────
# 12. Next weekday
# ──────────────────────────────────────────────
print("\n=== 12. Next weekday ===")

s, t = qa("Submit report next friday", pid)
check("next friday -> 201", s == 201, f"got {s}")
check("next friday -> due_date_hint is 'next friday'",
      t.get("due_date_hint") == "next friday",
      f"hint={t.get('due_date_hint')!r}")
check("next friday -> phrase stripped from title",
      "next friday" not in t.get("title","").lower(),
      f"title={t.get('title')!r}")
# due_date should be set (a resolved YYYY-MM-DD date)
check("next friday -> due_date set",
      t.get("due_date") is not None,
      f"due_date={t.get('due_date')!r}")
created_task_ids.append(t.get("id"))


# ──────────────────────────────────────────────
# 13. Bare weekday
# ──────────────────────────────────────────────
print("\n=== 13. Bare weekday ===")

s, t = qa("Dentist appointment wednesday", pid)
check("bare wednesday -> 201", s == 201, f"got {s}")
check("bare wednesday -> hint is 'wednesday'",
      t.get("due_date_hint") == "wednesday",
      f"hint={t.get('due_date_hint')!r}")
check("bare wednesday -> phrase stripped",
      "wednesday" not in t.get("title","").lower(),
      f"title={t.get('title')!r}")
created_task_ids.append(t.get("id"))

# "next wednesday" should produce hint="next wednesday", not "wednesday"
s, t = qa("Team sync next wednesday", pid)
check("next wednesday -> hint is 'next wednesday' not 'wednesday'",
      t.get("due_date_hint") == "next wednesday",
      f"hint={t.get('due_date_hint')!r}")
created_task_ids.append(t.get("id"))


# ──────────────────────────────────────────────
# 14. Repeated date phrase
# ──────────────────────────────────────────────
print("\n=== 14. Repeated date phrase ===")

s, t = qa("tomorrow review tomorrow", pid)
check("repeated tomorrow -> 201", s == 201, f"got {s}")
check("repeated tomorrow -> title is 'review'",
      t.get("title") == "review",
      f"title={t.get('title')!r}")
check("repeated tomorrow -> hint is 'tomorrow'",
      t.get("due_date_hint") == "tomorrow",
      f"hint={t.get('due_date_hint')!r}")
created_task_ids.append(t.get("id"))


# ──────────────────────────────────────────────
# 15. Title fallback
# ──────────────────────────────────────────────
print("\n=== 15. Title fallback ===")

s, t = qa("urgent asap", pid)
check("only keywords -> 201", s == 201, f"got {s}")
check("only keywords -> Untitled task",
      t.get("title") == "Untitled task",
      f"title={t.get('title')!r}")
created_task_ids.append(t.get("id"))


# ──────────────────────────────────────────────
# 16. Four mandatory regression cases (live endpoint)
# ──────────────────────────────────────────────
print("\n=== 16. Mandatory regression cases (live) ===")

# Case 1
s, t = qa("This is urgent, mark it ASAP please", pid)
check("Reg1 -> 201", s == 201, f"got {s}")
check("Reg1 -> title",
      t.get("title") == "This is , mark it  please",
      f"title={t.get('title')!r}")
check("Reg1 -> priority high",  t.get("priority") == "high",
      f"priority={t.get('priority')!r}")
check("Reg1 -> due_date_hint null", t.get("due_date_hint") is None,
      f"hint={t.get('due_date_hint')!r}")
created_task_ids.append(t.get("id"))

# Case 2 (whitespace)
s, t = qa(" ", pid)
check("Reg2 -> 201", s == 201, f"got {s}")
check("Reg2 -> title Untitled task",
      t.get("title") == "Untitled task",
      f"title={t.get('title')!r}")
check("Reg2 -> priority medium", t.get("priority") == "medium",
      f"priority={t.get('priority')!r}")
check("Reg2 -> due_date_hint null", t.get("due_date_hint") is None,
      f"hint={t.get('due_date_hint')!r}")
created_task_ids.append(t.get("id"))

# Case 3
s, t = qa("Finish the report next Friday, it's urgent", pid)
check("Reg3 -> 201", s == 201, f"got {s}")
check("Reg3 -> title",
      t.get("title") == "Finish the report , it's",
      f"title={t.get('title')!r}")
check("Reg3 -> priority high",  t.get("priority") == "high",
      f"priority={t.get('priority')!r}")
check("Reg3 -> due_date_hint 'next friday'",
      t.get("due_date_hint") == "next friday",
      f"hint={t.get('due_date_hint')!r}")
created_task_ids.append(t.get("id"))

# Case 4
s, t = qa("tomorrow review tomorrow", pid)
# Already tested in section 14; record result again for completeness
check("Reg4 -> 201", s == 201, f"got {s}")
check("Reg4 -> title 'review'",
      t.get("title") == "review",
      f"title={t.get('title')!r}")
check("Reg4 -> priority medium", t.get("priority") == "medium",
      f"priority={t.get('priority')!r}")
check("Reg4 -> due_date_hint 'tomorrow'",
      t.get("due_date_hint") == "tomorrow",
      f"hint={t.get('due_date_hint')!r}")
created_task_ids.append(t.get("id"))


# ──────────────────────────────────────────────
# 17. Integration: quick-added task in same tasks table
# ──────────────────────────────────────────────
print("\n=== 17. Integration: same tasks table ===")

# All quick-added task IDs must be accessible via normal GET /tasks/{id}
s, all_tasks2 = req("GET", "/tasks")
all_ids = [t["id"] for t in all_tasks2]
for tid in created_task_ids:
    if tid is not None:
        check(f"Integration: task {tid} in GET /tasks",
              tid in all_ids, f"ids={all_ids[:10]}...")

# Sort endpoint also sees quick-added tasks
s, sorted_tasks = req("GET", "/tasks?sort=priority")
check("Integration: sort endpoint returns quick-added tasks",
      s == 200 and len(sorted_tasks) >= len(created_task_ids),
      f"got {len(sorted_tasks)} tasks")

# Stats for our project should reflect all quick-added tasks
s, pstats = req("GET", f"/tasks/stats?project_id={pid}")
check("Integration: project stats total matches created count",
      pstats.get("total", 0) == len([t for t in created_task_ids if t is not None]),
      f"stats.total={pstats.get('total')}, created={len(created_task_ids)}")


# ──────────────────────────────────────────────
# 18. Teardown
# ──────────────────────────────────────────────
print("\n=== 18. Teardown ===")

s, _ = req("DELETE", f"/users/{uid}")
check("Teardown: delete test user (cascades)", s == 200, f"got {s}")


# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────
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
