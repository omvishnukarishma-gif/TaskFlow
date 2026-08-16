
"""
check_algorithms.py — Section 2 correctness checks for TaskFlow.

Run:
    python check_algorithms.py

No pytest, unittest, or assert is used.
"""

import sys

sys.path.insert(0, ".")

from backend.algorithms.sorting import insertion_sort, insertion_sort_count
from backend.algorithms.searching import (
    binary_search,
    linear_search,
    binary_search_count,
    linear_search_count,
)


def title_key(record):
    return record["title"]


def make_task(title):
    return {
        "title": title,
        "priority": "medium",
        "due_date": None,
    }


passed = 0
failed = 0


def check(case_name, result, expected):
    global passed, failed

    if result == expected:
        print(f"PASS: {case_name}")
        passed += 1
    else:
        print(
            f"FAIL: {case_name} — expected {expected}, got {result}"
        )
        failed += 1


def check_true(case_name, condition, expected=True):
    global passed, failed

    if condition == expected:
        print(f"PASS: {case_name}")
        passed += 1
    else:
        print(
            f"FAIL: {case_name} — expected {expected}, got {condition}"
        )
        failed += 1


# ============================================================
# 1. insertion_sort — empty list
# ============================================================

records = []

result = insertion_sort(records, key=title_key)

check(
    "insertion_sort empty list stays empty",
    records,
    [],
)

check(
    "insertion_sort returns None",
    result,
    None,
)


# ============================================================
# 2. insertion_sort — single element
# ============================================================

records = [make_task("Only Task")]

insertion_sort(records, key=title_key)

check(
    "insertion_sort single element unchanged",
    records[0]["title"],
    "Only Task",
)


# ============================================================
# 3. insertion_sort — normal sorting
# ============================================================

records = [
    make_task("Charlie"),
    make_task("Alpha"),
    make_task("Bravo"),
]

insertion_sort(records, key=title_key)

check(
    "insertion_sort sorts records in place",
    [record["title"] for record in records],
    ["Alpha", "Bravo", "Charlie"],
)


# ============================================================
# 4. binary_search — first index
# ============================================================

records = [
    make_task("Alpha"),
    make_task("Bravo"),
    make_task("Charlie"),
    make_task("Delta"),
    make_task("Echo"),
]

index = binary_search(
    records,
    "Alpha",
    key=title_key,
)

check(
    "binary_search finds first index",
    index,
    0,
)


# ============================================================
# 5. binary_search — middle index
# ============================================================

index = binary_search(
    records,
    "Charlie",
    key=title_key,
)

check(
    "binary_search finds middle index",
    index,
    2,
)


# ============================================================
# 6. binary_search — last index
# ============================================================

index = binary_search(
    records,
    "Echo",
    key=title_key,
)

check(
    "binary_search finds last index",
    index,
    4,
)


# ============================================================
# 7. binary_search — not found
# ============================================================

index = binary_search(
    records,
    "Missing",
    key=title_key,
)

check(
    "binary_search returns -1 when absent",
    index,
    -1,
)


# ============================================================
# 8. linear_search — first match
# ============================================================

records = [
    make_task("Alpha"),
    make_task("Bravo"),
    make_task("Charlie"),
]

index = linear_search(
    records,
    "Bravo",
    key=title_key,
)

check(
    "linear_search finds matching index",
    index,
    1,
)


# ============================================================
# 9. linear_search — not found
# ============================================================

index = linear_search(
    records,
    "Missing",
    key=title_key,
)

check(
    "linear_search returns -1 when absent",
    index,
    -1,
)


# ============================================================
# 10. insertion_sort_count
# ============================================================

records = [
    make_task("Charlie"),
    make_task("Alpha"),
    make_task("Bravo"),
]

count = insertion_sort_count(
    records,
    key=title_key,
)

check(
    "insertion_sort_count sorts the list",
    [record["title"] for record in records],
    ["Alpha", "Bravo", "Charlie"],
)

check_true(
    "insertion_sort_count returns plain int",
    type(count) == int,
)

check_true(
    "insertion_sort_count returns positive count",
    count > 0,
)


# ============================================================
# 11. binary_search_count
# ============================================================

records = [
    make_task("Alpha"),
    make_task("Bravo"),
    make_task("Charlie"),
    make_task("Delta"),
    make_task("Echo"),
]

result = binary_search_count(
    records,
    "Charlie",
    key=title_key,
)

check(
    "binary_search_count returns dictionary",
    type(result),
    dict,
)

check(
    "binary_search_count correct index",
    result["index"],
    2,
)

check_true(
    "binary_search_count comparison_count is int",
    type(result["comparison_count"]) == int,
)

check_true(
    "binary_search_count comparison_count > 0",
    result["comparison_count"] > 0,
)


# ============================================================
# 12. linear_search_count — absent value
# ============================================================

result = linear_search_count(
    records,
    "Missing",
    key=title_key,
)

check(
    "linear_search_count absent index",
    result["index"],
    -1,
)

check(
    "linear_search_count absent comparisons equals list length",
    result["comparison_count"],
    len(records),
)

check_true(
    "linear_search_count comparison_count is int",
    type(result["comparison_count"]) == int,
)


# ============================================================
# Summary
# ============================================================

print()
print("=" * 55)
print(f"Results: {passed} passed, {failed} failed")

if failed == 0:
    print("ALL REQUIRED ALGORITHM CHECKS PASSED")
    sys.exit(0)
else:
    print("SOME ALGORITHM CHECKS FAILED")
    sys.exit(1)
