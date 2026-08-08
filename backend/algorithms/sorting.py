"""
algorithms/sorting.py — Custom insertion sort implementation.

Rules:
  - NO Python built-in sorted() or list.sort() anywhere in this file.
  - Works on any list of records (dicts or SQLAlchemy model instances).
  - The caller supplies a key function that extracts the comparable value.
  - Returns a NEW list (input is not mutated) plus an exact comparison count.

Public API:
  insertion_sort(records, key)  -> (sorted_list, comparisons)
  insertion_sort_count          -> module-level counter (int), reset per call
"""

from __future__ import annotations
from typing import Any, Callable, List, Tuple

# ---------------------------------------------------------------------------
# Module-level comparison counter — updated on every insertion_sort() call.
# Consumers (routes, check_algorithms) may read this after calling the fn.
# ---------------------------------------------------------------------------
insertion_sort_count: int = 0


def insertion_sort(
    records: List[Any],
    key: Callable[[Any], Any],
) -> Tuple[List[Any], int]:
    """
    Sort *records* in ascending order using insertion sort.

    Parameters
    ----------
    records : list
        The items to sort.  This list is NOT mutated; a shallow copy is made.
    key : callable
        Extracts the comparable value from each record.
        Must return a type that supports < and > operators.

    Returns
    -------
    (sorted_list, comparisons) : tuple
        sorted_list  – new list ordered ascending by key(record)
        comparisons  – total number of element-to-element comparisons made

    Complexity
    ----------
    Best case  : O(n)       — already sorted input
    Average    : O(n²)
    Worst case : O(n²)      — reverse-sorted input
    Space      : O(n)       — one copy of the list
    """
    global insertion_sort_count

    # Work on a shallow copy so callers are not surprised by mutation
    arr: List[Any] = list(records)
    comparisons: int = 0
    n = len(arr)

    for i in range(1, n):
        current = arr[i]
        current_key = key(current)
        j = i - 1

        # Shift elements that are greater than current one position to the right
        while j >= 0:
            comparisons += 1                      # count EVERY comparison
            if key(arr[j]) > current_key:
                arr[j + 1] = arr[j]
                j -= 1
            else:
                break                             # correct position found

        arr[j + 1] = current

    insertion_sort_count = comparisons
    return arr, comparisons
