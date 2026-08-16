"""
algorithms/searching.py — Custom binary and linear search implementations.

Section 2 requirements:
- No Python built-in sorted() or list.sort().
- binary_search() works on an already-sorted list.
- linear_search() works on any list.
- Both return the INDEX of the first/located matching record.
- -1 means "not found".
- Separate *_count functions return comparison information.
"""

from __future__ import annotations

from typing import Any, Callable, List, Dict


def binary_search(
    sorted_records: List[Any],
    target_value: Any,
    key: Callable[[Any], Any],
) -> int:
    """
    Search for target_value in a list already sorted by key.

    Returns:
        index of a matching record
        -1 if the target is not found
    """

    low = 0
    high = len(sorted_records) - 1

    while low <= high:
        mid = (low + high) // 2
        mid_value = key(sorted_records[mid])

        if mid_value == target_value:
            return mid

        if mid_value < target_value:
            low = mid + 1
        else:
            high = mid - 1

    return -1


def linear_search(
    records: List[Any],
    target_value: Any,
    key: Callable[[Any], Any],
) -> int:
    """
    Scan records from left to right.

    Returns:
        index of the first matching record
        -1 if the target is not found
    """

    for index, record in enumerate(records):
        if key(record) == target_value:
            return index

    return -1


def binary_search_count(
    sorted_records: List[Any],
    target_value: Any,
    key: Callable[[Any], Any],
) -> Dict[str, int]:
    """
    Binary search with comparison counting.

    One comparison is counted per loop iteration (each probe of the mid element).

    Returns exactly:
        {
            "index": <found index or -1>,
            "comparison_count": <number of comparisons>
        }
    """

    low = 0
    high = len(sorted_records) - 1
    comparisons = 0

    while low <= high:
        mid = (low + high) // 2
        mid_value = key(sorted_records[mid])

        # Count one comparison per probe of the mid element.
        comparisons += 1

        if mid_value == target_value:
            return {
                "index": mid,
                "comparison_count": comparisons,
            }
        elif mid_value < target_value:
            low = mid + 1
        else:
            high = mid - 1

    return {
        "index": -1,
        "comparison_count": comparisons,
    }


def linear_search_count(
    records: List[Any],
    target_value: Any,
    key: Callable[[Any], Any],
) -> Dict[str, int]:
    """
    Linear search with comparison counting.

    Returns exactly:
        {
            "index": <found index or -1>,
            "comparison_count": <number of comparisons>
        }

    For an absent value, comparison_count equals len(records).
    """

    comparisons = 0

    for index, record in enumerate(records):
        comparisons += 1

        if key(record) == target_value:
            return {
                "index": index,
                "comparison_count": comparisons,
            }

    return {
        "index": -1,
        "comparison_count": comparisons,
    }