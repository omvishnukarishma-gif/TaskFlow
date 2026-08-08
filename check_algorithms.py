"""
check_algorithms.py — Correctness tests and benchmark for TaskFlow algorithms.

Usage:
    python check_algorithms.py

Output format:
    PASS: <case name>
    FAIL: <case name> — expected <X>, got <Y>

No pytest, unittest, or assert is used.
Exit code 0 = all tests passed, 1 = at least one failure.
"""

import sys
import time
import random

sys.path.insert(0, ".")

from backend.algorithms.sorting import insertion_sort
from backend.algorithms.searching import binary_search, linear_search

# ============================================================
# Tiny helpers
# ============================================================

_pass_count = 0
_fail_count = 0


def _pass(name: str) -> None:
    global _pass_count
    _pass_count += 1
    print(f"PASS: {name}")


def _fail(name: str, expected, got) -> None:
    global _fail_count
    _fail_count += 1
    print(f"FAIL: {name} — expected {expected!r}, got {got!r}")


def check_equal(name: str, expected, got) -> None:
    if expected == got:
        _pass(name)
    else:
        _fail(name, expected, got)


def check_true(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        _pass(name)
    else:
        _fail(name, True, detail or False)


# ============================================================
# Test helpers — record factory
# ============================================================

def make_task(title: str, priority: str, idx: int = 0) -> dict:
    """Create a minimal dict that mimics a Task ORM object."""
    return {"id": idx, "title": title, "priority": priority}


def title_key(t: dict) -> str:
    return t["title"]


def priority_key(t: dict) -> str:
    return t["priority"]


PRIORITY_WEIGHT = {"low": 1, "medium": 2, "high": 3}


def priority_weight_key(t: dict) -> int:
    return PRIORITY_WEIGHT.get(t["priority"], 0)


# ============================================================
# SECTION 1 — insertion_sort correctness
# ============================================================
print("\n--- insertion_sort correctness ---")

# 1. Empty list
result, comps = insertion_sort([], key=title_key)
check_equal("sort: empty list returns empty", [], result)
check_equal("sort: empty list — 0 comparisons", 0, comps)

# 2. Single element
result, comps = insertion_sort([make_task("Alpha", "high")], key=title_key)
check_equal("sort: single element stays in place", ["Alpha"], [r["title"] for r in result])
check_equal("sort: single element — 0 comparisons", 0, comps)

# 3. Already sorted (ascending) — comparisons < n*(n-1)/2
data = [make_task(t, "low") for t in ["Apple", "Banana", "Cherry", "Date", "Elderberry"]]
result, comps = insertion_sort(data, key=title_key)
titles = [r["title"] for r in result]
check_equal("sort: already-sorted order preserved", ["Apple", "Banana", "Cherry", "Date", "Elderberry"], titles)
n = 5
check_true("sort: already-sorted comparisons < worst case", comps < n * (n - 1) // 2,
           f"comps={comps}, worst={n*(n-1)//2}")

# 4. Reverse sorted — worst case, comparisons == n*(n-1)/2
data = [make_task(t, "low") for t in ["Elderberry", "Date", "Cherry", "Banana", "Apple"]]
result, comps = insertion_sort(data, key=title_key)
titles = [r["title"] for r in result]
check_equal("sort: reverse-sorted produces ascending order",
            ["Apple", "Banana", "Cherry", "Date", "Elderberry"], titles)
check_equal("sort: reverse-sorted comparisons == n*(n-1)/2", n * (n - 1) // 2, comps)

# 5. Random order
data = [make_task(t, "medium") for t in ["Mango", "Apple", "Zebra", "Banana", "Kiwi"]]
result, comps = insertion_sort(data, key=title_key)
titles = [r["title"] for r in result]
check_equal("sort: random order — ascending result",
            ["Apple", "Banana", "Kiwi", "Mango", "Zebra"], titles)
check_true("sort: random order — comparisons > 0", comps > 0, f"comps={comps}")

# 6. All same key (duplicates)
data = [make_task("Same", p) for p in ["high", "low", "medium", "high", "low"]]
result, comps = insertion_sort(data, key=title_key)
titles = [r["title"] for r in result]
check_equal("sort: all-same keys — all elements kept", 5, len(titles))
check_true("sort: all-same keys — comparisons >= 0", comps >= 0, f"comps={comps}")

# 7. Priority weight sort — low(1) < medium(2) < high(3)
data = [
    make_task("T5", "high"),
    make_task("T2", "medium"),
    make_task("T1", "low"),
    make_task("T4", "high"),
    make_task("T3", "medium"),
]
result, comps = insertion_sort(data, key=priority_weight_key)
priorities = [r["priority"] for r in result]
# All lows before mediums before highs
low_indices    = [i for i, r in enumerate(result) if r["priority"] == "low"]
medium_indices = [i for i, r in enumerate(result) if r["priority"] == "medium"]
high_indices   = [i for i, r in enumerate(result) if r["priority"] == "high"]
check_true("sort: priority weights — lows come first",
           max(low_indices) < min(medium_indices), f"priorities={priorities}")
check_true("sort: priority weights — mediums before highs",
           max(medium_indices) < min(high_indices), f"priorities={priorities}")

# 8. Input list is NOT mutated
original = [make_task("Z", "high"), make_task("A", "low")]
original_copy = [dict(t) for t in original]
insertion_sort(original, key=title_key)
check_equal("sort: input list not mutated", original_copy, original)

# 9. Two elements — swapped
data = [make_task("Zebra", "low"), make_task("Apple", "low")]
result, comps = insertion_sort(data, key=title_key)
check_equal("sort: two-element swap", ["Apple", "Zebra"], [r["title"] for r in result])
check_equal("sort: two-element swap — 1 comparison", 1, comps)

# 10. Two elements — already in order
data = [make_task("Apple", "low"), make_task("Zebra", "low")]
result, comps = insertion_sort(data, key=title_key)
check_equal("sort: two-element no-swap", ["Apple", "Zebra"], [r["title"] for r in result])
check_equal("sort: two-element no-swap — 1 comparison", 1, comps)


# ============================================================
# SECTION 2 — binary_search correctness
# ============================================================
print("\n--- binary_search correctness ---")

# Pre-sort with our insertion_sort for all binary search tests
tasks_for_search = [
    make_task("Alpha Task",      "high"),
    make_task("Beta Task",       "medium"),
    make_task("Charlie Task",    "low"),
    make_task("Delta Task",      "high"),
    make_task("Epsilon Task",    "medium"),
    make_task("Fix the bug",     "high"),
    make_task("Write tests",     "low"),
    make_task("Deploy to prod",  "medium"),
    make_task("Review PR",       "high"),
    make_task("Update docs",     "low"),
]
sorted_tasks, _ = insertion_sort(tasks_for_search, key=title_key)

# 11. Found — single match
matches, steps = binary_search(sorted_tasks, "Fix the bug", key=title_key)
check_equal("binary: found single match", 1, len(matches))
check_equal("binary: found — correct title", "Fix the bug", matches[0]["title"])
check_true("binary: found — steps > 0", steps > 0, f"steps={steps}")

# 12. Not found
matches, steps = binary_search(sorted_tasks, "Nonexistent Task", key=title_key)
check_equal("binary: not found returns empty list", 0, len(matches))
check_true("binary: not found — steps >= 0", steps >= 0, f"steps={steps}")

# 13. Empty list
matches, steps = binary_search([], "Anything", key=title_key)
check_equal("binary: empty list returns empty", 0, len(matches))
check_equal("binary: empty list — 0 steps", 0, steps)

# 14. Single element — found
single = [make_task("Only Task", "medium")]
matches, steps = binary_search(single, "Only Task", key=title_key)
check_equal("binary: single element found", 1, len(matches))
check_equal("binary: single element found — 1 step", 1, steps)

# 15. Single element — not found
matches, steps = binary_search(single, "Missing", key=title_key)
check_equal("binary: single element not found", 0, len(matches))

# 16. Duplicate keys — all matches returned
dupes = [make_task("Duplicate", p) for p in ["high", "low", "medium"]]
sorted_dupes, _ = insertion_sort(dupes, key=title_key)
matches, steps = binary_search(sorted_dupes, "Duplicate", key=title_key)
check_equal("binary: duplicates — all 3 returned", 3, len(matches))

# 17. First element match
first_sorted = sorted_tasks[0]["title"]
matches, steps = binary_search(sorted_tasks, first_sorted, key=title_key)
check_equal("binary: first element found", 1, len(matches))

# 18. Last element match
last_sorted = sorted_tasks[-1]["title"]
matches, steps = binary_search(sorted_tasks, last_sorted, key=title_key)
check_equal("binary: last element found", 1, len(matches))

# 19. Binary search uses fewer steps than linear for large sorted input
big_titles = [f"Task {i:04d}" for i in range(1000)]
big_data = [make_task(t, "medium") for t in big_titles]
big_sorted, _ = insertion_sort(big_data, key=title_key)
target = "Task 0500"
_, bin_steps = binary_search(big_sorted, target, key=title_key)
_, lin_steps = linear_search(big_data, target, key=title_key)
check_true("binary: fewer steps than linear on 1000 items",
           bin_steps < lin_steps, f"binary={bin_steps}, linear={lin_steps}")


# ============================================================
# SECTION 3 — linear_search correctness
# ============================================================
print("\n--- linear_search correctness ---")

# 20. Found — single match
matches, steps = linear_search(tasks_for_search, "Write tests", key=title_key)
check_equal("linear: found single match", 1, len(matches))
check_equal("linear: steps == len(input)", len(tasks_for_search), steps)

# 21. Not found
matches, steps = linear_search(tasks_for_search, "Ghost Task", key=title_key)
check_equal("linear: not found returns empty", 0, len(matches))
check_equal("linear: not found — steps == len(input)", len(tasks_for_search), steps)

# 22. Empty list
matches, steps = linear_search([], "Any", key=title_key)
check_equal("linear: empty list returns empty", 0, len(matches))
check_equal("linear: empty list — 0 steps", 0, steps)

# 23. Single element — found
matches, steps = linear_search([make_task("Solo", "low")], "Solo", key=title_key)
check_equal("linear: single found", 1, len(matches))
check_equal("linear: single found — 1 step", 1, steps)

# 24. Single element — not found
matches, steps = linear_search([make_task("Solo", "low")], "Nope", key=title_key)
check_equal("linear: single not found", 0, len(matches))
check_equal("linear: single not found — 1 step", 1, steps)

# 25. All elements match (all same title)
all_same = [make_task("Common", "medium") for _ in range(5)]
matches, steps = linear_search(all_same, "Common", key=title_key)
check_equal("linear: all match — 5 results", 5, len(matches))
check_equal("linear: all match — 5 steps", 5, steps)

# 26. Multiple matches
multi = [
    make_task("Alpha", "low"),
    make_task("Beta",  "low"),
    make_task("Alpha", "high"),
    make_task("Gamma", "medium"),
    make_task("Alpha", "medium"),
]
matches, steps = linear_search(multi, "Alpha", key=title_key)
check_equal("linear: multiple matches — 3 results", 3, len(matches))
check_equal("linear: multiple matches — scans all", 5, steps)

# 27. Always scans full list regardless of position
early = [make_task("Target", "low")] + [make_task(f"Z{i}", "high") for i in range(9)]
_, steps_early = linear_search(early, "Target", key=title_key)
check_equal("linear: always scans full list", 10, steps_early)


# ============================================================
# SECTION 4 — Integration check (sort + search together)
# ============================================================
print("\n--- integration: sort then binary search ---")

mixed = [
    make_task("Zap",    "high"),
    make_task("Alpha",  "low"),
    make_task("Middle", "medium"),
    make_task("Bravo",  "high"),
    make_task("Alpha",  "medium"),   # duplicate title
]
sorted_mixed, sort_comps = insertion_sort(mixed, key=title_key)
sorted_titles = [r["title"] for r in sorted_mixed]

# Verify sorted order is ascending
is_sorted = all(sorted_titles[i] <= sorted_titles[i+1] for i in range(len(sorted_titles)-1))
check_true("integration: insertion_sort produces ascending titles", is_sorted, str(sorted_titles))

# Binary search finds both "Alpha" entries
matches, bin_steps = binary_search(sorted_mixed, "Alpha", key=title_key)
check_equal("integration: binary finds both Alpha duplicates", 2, len(matches))

# Linear search on original also finds both "Alpha"
matches_lin, lin_steps = linear_search(mixed, "Alpha", key=title_key)
check_equal("integration: linear also finds both Alpha duplicates", 2, len(matches_lin))

check_true("integration: binary fewer steps than linear for Alpha",
           bin_steps < lin_steps, f"binary={bin_steps}, linear={lin_steps}")


# ============================================================
# SECTION 5 — Benchmark
# ============================================================
print("\n--- benchmark ---")

SIZES = [10, 500, 3000]
BENCHMARK_RESULTS = {}   # saved for README generation

random.seed(42)

_WORDS = [
    "alpha","beta","gamma","delta","epsilon","zeta","eta","theta","iota","kappa",
    "lambda","mu","nu","xi","omicron","pi","rho","sigma","tau","upsilon",
    "phi","chi","psi","omega","task","fix","build","deploy","test","review",
]

def _random_title(idx: int) -> str:
    """Generate a reasonably varied title to avoid all-equal keys."""
    return f"{random.choice(_WORDS)}-{idx:05d}"

def _random_priority() -> str:
    return random.choice(["low", "medium", "high"])

for n in SIZES:
    records = [make_task(_random_title(i), _random_priority(), i) for i in range(n)]
    random.shuffle(records)

    # --- insertion sort ---
    t0 = time.perf_counter()
    sorted_records, sort_comps = insertion_sort(records, key=title_key)
    sort_time_ms = (time.perf_counter() - t0) * 1000

    # --- binary search (target near middle of sorted list) ---
    mid_idx = n // 2
    target = sorted_records[mid_idx]["title"]

    t0 = time.perf_counter()
    bin_matches, bin_steps = binary_search(sorted_records, target, key=title_key)
    bin_time_us = (time.perf_counter() - t0) * 1_000_000

    # --- linear search (same target, unsorted original) ---
    t0 = time.perf_counter()
    lin_matches, lin_steps = linear_search(records, target, key=title_key)
    lin_time_us = (time.perf_counter() - t0) * 1_000_000

    BENCHMARK_RESULTS[n] = {
        "sort_comparisons": sort_comps,
        "sort_time_ms":     round(sort_time_ms, 3),
        "binary_steps":     bin_steps,
        "binary_time_us":   round(bin_time_us, 3),
        "linear_steps":     lin_steps,
        "linear_time_us":   round(lin_time_us, 3),
    }

    print(f"\n  n={n}")
    print(f"    insertion_sort : {sort_comps:>10,} comparisons  | {sort_time_ms:.3f} ms")
    print(f"    binary_search  : {bin_steps:>10,} steps         | {bin_time_us:.1f} µs")
    print(f"    linear_search  : {lin_steps:>10,} steps         | {lin_time_us:.1f} µs")
    print(f"    binary/linear step ratio: {bin_steps}/{lin_steps} "
          f"= {bin_steps/lin_steps:.4f}  ({lin_steps/max(bin_steps,1):.1f}x fewer steps)")

    # Sanity: binary found the target
    check_true(f"benchmark n={n}: binary finds target",
               len(bin_matches) > 0, f"target={target!r}")
    # Sanity: linear found the same target
    check_true(f"benchmark n={n}: linear finds same target",
               len(lin_matches) > 0, f"target={target!r}")
    # Sanity: binary fewer steps
    check_true(f"benchmark n={n}: binary steps < linear steps",
               bin_steps < lin_steps, f"binary={bin_steps}, linear={lin_steps}")

# Write benchmark results to a file for README consumption
import json
with open("benchmark_results.json", "w") as f:
    json.dump(BENCHMARK_RESULTS, f, indent=2)
print("\n  Benchmark results written to benchmark_results.json")


# ============================================================
# Summary
# ============================================================
print(f"\n{'='*55}")
print(f"Results: {_pass_count} passed, {_fail_count} failed")
if _fail_count == 0:
    print("ALL TESTS PASSED")
    sys.exit(0)
else:
    print("SOME TESTS FAILED — see FAIL lines above")
    sys.exit(1)
