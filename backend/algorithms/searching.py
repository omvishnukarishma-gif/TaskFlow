"""
algorithms/searching.py — Binary search and linear search implementations.

Rules:
  - NO Python built-in sorted() or list.sort() anywhere in this file.
  - binary_search requires a PRE-SORTED list (caller must sort first).
  - linear_search works on any list in any order.
  - Both use exact string matching (case-sensitive) on the extracted key value.
  - Both return (list_of_matching_records, step_count).

Public API:
  binary_search(sorted_records, target_value, key)  -> (matches, steps)
  linear_search(records,        target_value, key)  -> (matches, steps)
  binary_search_count  : int  (updated after every binary_search call)
  linear_search_count  : int  (updated after every linear_search call)
"""

from __future__ import annotations
from typing import Any, Callable, List, Tuple

# ---------------------------------------------------------------------------
# Module-level step counters — updated on every call.
# ---------------------------------------------------------------------------
binary_search_count: int = 0
linear_search_count: int = 0


def binary_search(
    sorted_records: List[Any],
    target_value: str,
    key: Callable[[Any], Any],
) -> Tuple[List[Any], int]:
    """
    Binary search on a pre-sorted list for records whose key == target_value.

    Pre-condition: sorted_records MUST already be sorted ascending by key.
                   Call insertion_sort() first if unsure.

    Parameters
    ----------
    sorted_records : list
        A list already sorted ascending by key(record).
    target_value : str
        The exact value to search for.
    key : callable
        Extracts the comparable string value from each record.

    Returns
    -------
    (matches, steps) : tuple
        matches – all records whose key exactly equals target_value
        steps   – number of comparisons performed (including expansion)

    Complexity
    ----------
    Best case  : O(1)       — target at midpoint
    Average    : O(log n)
    Worst case : O(log n + k)  where k = number of matching records
    """
    global binary_search_count

    arr = sorted_records
    n = len(arr)
    steps: int = 0
    matches: List[Any] = []

    if n == 0:
        binary_search_count = steps
        return matches, steps

    lo: int = 0
    hi: int = n - 1

    while lo <= hi:
        steps += 1
        mid = (lo + hi) // 2
        mid_val = key(arr[mid])

        if mid_val == target_value:
            # Found one match — now expand left and right to collect duplicates
            matches.append(arr[mid])

            # Expand left
            left = mid - 1
            while left >= 0:
                steps += 1
                if key(arr[left]) == target_value:
                    matches.append(arr[left])
                    left -= 1
                else:
                    break

            # Expand right
            right = mid + 1
            while right < n:
                steps += 1
                if key(arr[right]) == target_value:
                    matches.append(arr[right])
                    right += 1
                else:
                    break

            break  # done — all matches collected

        elif mid_val < target_value:
            lo = mid + 1
        else:
            hi = mid - 1

    binary_search_count = steps
    return matches, steps


def linear_search(
    records: List[Any],
    target_value: str,
    key: Callable[[Any], Any],
) -> Tuple[List[Any], int]:
    """
    Linear search — scan every record in order, collect exact key matches.

    Parameters
    ----------
    records : list
        The items to search.  No ordering requirement.
    target_value : str
        The exact value to search for.
    key : callable
        Extracts the comparable string value from each record.

    Returns
    -------
    (matches, steps) : tuple
        matches – all records whose key exactly equals target_value
        steps   – number of elements examined (always == len(records))

    Complexity
    ----------
    Best case  : O(1)  — first element matches (but we scan all for completeness)
    Average    : O(n)
    Worst case : O(n)
    """
    global linear_search_count

    steps: int = 0
    matches: List[Any] = []

    for record in records:
        steps += 1
        if key(record) == target_value:
            matches.append(record)

    linear_search_count = steps
    return matches, steps
