"""
test_parser_offline.py — Offline unit tests for the deterministic parser.

Tests ONLY the parser logic — no server, no database required.
Output: PASS/FAIL format, no pytest/unittest/assert.
"""
import sys
sys.path.insert(0, ".")

from backend.quick_add_parser import parse_quick_add

_pass = 0
_fail = 0

def check(name, expected, got):
    global _pass, _fail
    if expected == got:
        _pass += 1
        print(f"PASS: {name}")
    else:
        _fail += 1
        print(f"FAIL: {name} — expected {expected!r}, got {got!r}")

def check_result(name, description, exp_title, exp_priority, exp_hint):
    r = parse_quick_add(description)
    check(f"{name} — title",          exp_title,    r.title)
    check(f"{name} — priority",       exp_priority, r.priority)
    check(f"{name} — due_date_hint",  exp_hint,     r.due_date_hint)


# ============================================================
# MANDATORY REGRESSION CASES (exact spec requirements)
# ============================================================
print("\n--- Mandatory regression cases ---")

check_result(
    "Regression 1",
    "This is urgent, mark it ASAP please",
    "This is , mark it  please",
    "high",
    None,
)

check_result(
    "Regression 2 (whitespace only)",
    " ",
    "Untitled task",
    "medium",
    None,
)

check_result(
    "Regression 3",
    "Finish the report next Friday, it's urgent",
    "Finish the report , it's",
    "high",
    "next friday",
)

check_result(
    "Regression 4",
    "tomorrow review tomorrow",
    "review",
    "medium",
    "tomorrow",
)


# ============================================================
# ADDITIONAL EDGE CASES
# ============================================================
print("\n--- Edge cases ---")

# Both high and low keywords -> HIGH wins
check_result(
    "high+low -> high",
    "finish this urgent task whenever",
    "finish this  task",   # "urgent" removed -> double space; "whenever" removed
    "high",
    None,
)

# Repeated priority keywords — all removed from title
check_result(
    "repeated high keywords",
    "urgent fix this urgent bug asap",
    "fix this  bug",   # leading "urgent " stripped; middle "urgent " leaves double space
    "high",
    None,
)

# Repeated due-date phrase — all occurrences removed
check_result(
    "repeated date phrase",
    "tomorrow do this tomorrow",
    "do this",
    "medium",
    "tomorrow",
)

# "next Friday" -> hint is "next friday", NOT "friday"
check_result(
    "next Friday vs friday",
    "submit report next Friday",
    "submit report",
    "medium",
    "next friday",
)

# bare friday (no "next" prefix)
check_result(
    "bare friday",
    "submit report friday",
    "submit report",
    "medium",
    "friday",
)

# no keywords -> medium + null
check_result(
    "no keywords",
    "Buy milk from the store",
    "Buy milk from the store",
    "medium",
    None,
)

# empty string
check_result(
    "empty string",
    "",
    "Untitled task",
    "medium",
    None,
)

# whitespace only
check_result(
    "whitespace only (spaces)",
    "     ",
    "Untitled task",
    "medium",
    None,
)

# original casing preserved
r = parse_quick_add("Deploy THE App ASAP next Monday")
check("casing: 'Deploy THE App' preserved in title",
      True, r.title.startswith("Deploy THE App"))
check("casing: priority high", "high", r.priority)
check("casing: hint is 'next monday'", "next monday", r.due_date_hint)

# .strip() applied — leading/trailing spaces after removal
check_result(
    "strip applied",
    "urgent ",
    "Untitled task",
    "high",
    None,
)

# low priority keyword
check_result(
    "low priority keyword",
    "clean up the inbox whenever",
    "clean up the inbox",
    "low",
    None,
)

# "low priority" as two-word phrase
check_result(
    "low priority phrase",
    "This is a low priority task",
    "This is a  task",   # "low priority" removed -> double space
    "low",
    None,
)

# asap alone
check_result(
    "asap alone",
    "ASAP fix login bug",
    "fix login bug",
    "high",
    None,
)

# today
check_result(
    "today",
    "finish slides today",
    "finish slides",
    "medium",
    "today",
)

# tomorrow
check_result(
    "tomorrow",
    "call John tomorrow",
    "call John",
    "medium",
    "tomorrow",
)

# next week
check_result(
    "next week",
    "plan sprint next week",
    "plan sprint",
    "medium",
    "next week",
)

# next monday specifically
check_result(
    "next monday",
    "submit report next monday",
    "submit report",
    "medium",
    "next monday",
)

# "next monday" present — should NOT match bare "monday"
r = parse_quick_add("meet team next monday")
check("next monday -> hint is 'next monday' not 'monday'",
      "next monday", r.due_date_hint)

# bare wednesday
check_result(
    "bare wednesday",
    "dentist appointment wednesday",
    "dentist appointment",
    "medium",
    "wednesday",
)

# urgent with today
check_result(
    "urgent today",
    "urgent deploy today",
    "deploy",
    "high",
    "today",
)

# "whenever" keyword
check_result(
    "whenever",
    "clean the garage whenever you can",
    "clean the garage  you can",   # "whenever" removed -> double space
    "low",
    None,
)

# ASAP (uppercase) — case-insensitive match
check_result(
    "ASAP uppercase",
    "ASAP deploy hotfix",
    "deploy hotfix",
    "high",
    None,
)

# all keywords together — high wins, all stripped
check_result(
    "all keywords + date",
    "urgent asap whenever next friday",
    "Untitled task",
    "high",
    "next friday",
)


# ============================================================
# Summary
# ============================================================
print(f"\n{'='*50}")
print(f"Results: {_pass} passed, {_fail} failed")
if _fail == 0:
    print("ALL PARSER TESTS PASSED")
    sys.exit(0)
else:
    sys.exit(1)
