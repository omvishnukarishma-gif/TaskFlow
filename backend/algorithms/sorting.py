"""
Custom insertion sort implementation for TaskFlow.

Section 2 requirements:
- No Python built-in sorted() or list.sort().
- insertion_sort() mutates the input list in place.
- insertion_sort() returns None.
- insertion_sort_count() is a separate counting wrapper.
"""

from typing import Any, Callable, List


def insertion_sort(
    records: List[Any],
    key: Callable[[Any], Any],
) -> None:
    """
    Sort records in place using insertion sort.

    The list supplied by the caller is directly mutated.

    Best case: O(n)
    Average case: O(n²)
    Worst case: O(n²)
    """
    for i in range(1, len(records)):
        current = records[i]
        current_key = key(current)

        j = i - 1

        while j >= 0 and key(records[j]) > current_key:
            records[j + 1] = records[j]
            j -= 1

        records[j + 1] = current


def insertion_sort_count(
    records: List[Any],
    key: Callable[[Any], Any],
) -> int:
    """
    Sort records in place using insertion sort and return
    the number of element-to-element comparisons.

    The returned value is ONLY an integer.
    """
    comparisons = 0

    for i in range(1, len(records)):
        current = records[i]
        current_key = key(current)

        j = i - 1

        while j >= 0:
            comparisons += 1

            if key(records[j]) > current_key:
                records[j + 1] = records[j]
                j -= 1
            else:
                break

        records[j + 1] = current

    return comparisons