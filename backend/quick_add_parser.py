"""
quick_add_parser.py — Deterministic AI Quick-Add parser.

This module simulates a structured LLM prompt exchange using a system role
and a user role, but implements the parsing entirely offline with pure Python.
No network calls, no API keys, no external dependencies.

Role structure
--------------
SYSTEM ROLE:
    Defines the parser's rules — priority detection, date extraction,
    title generation, and fallback behaviour.

USER ROLE:
    Contains the raw free-text description from the user.

The function parse_quick_add(description) returns a ParseResult dataclass
representing what the "LLM" would have produced given those roles.

Priority rules (evaluated in this exact order):
    HIGH  keywords: "urgent", "asap"
    LOW   keywords: "whenever", "low priority"
    DEFAULT:        "medium"
    Rule: if BOTH high and low keywords are present, HIGH wins.

Keyword stripping:
    ALL occurrences of ALL priority keywords are removed from the title,
    regardless of which priority was selected.
    Keywords removed: "urgent", "asap", "whenever", "low priority"

Due-date matching (search the lower-cased description in THIS order,
first match wins):
    1.  today
    2.  tomorrow
    3.  next week
    4.  next monday
    5.  next tuesday
    6.  next wednesday
    7.  next thursday
    8.  next friday
    9.  next saturday
    10. next sunday
    11. monday
    12. tuesday
    13. wednesday
    14. thursday
    15. friday
    16. saturday
    17. sunday

"next <weekday>" is matched as a single phrase before the bare weekday,
so a bare weekday never overrides a "next <weekday>" that is present.

Title generation:
    1. Start from the ORIGINAL-CASED description.
    2. Remove every occurrence of all priority keywords (case-insensitive).
    3. Remove every occurrence of the matched due-date phrase (case-insensitive).
    4. Collapse runs of whitespace to a single space.
    5. Call .strip().
    6. If the result is empty or whitespace-only: use "Untitled task".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# System role — defines the deterministic rules this parser follows.
# This string is NOT sent to any LLM; it documents the parser's behaviour
# in the same vocabulary as a real prompt would use.
# ---------------------------------------------------------------------------
SYSTEM_ROLE: str = """
You are a task-extraction assistant.
Given a plain-text task description (user role), extract:
  - priority: "high" | "medium" | "low"
  - due_date_hint: the matched date phrase (lower-case) or null
  - title: the cleaned task title

Priority rules:
  HIGH  if "urgent" or "asap" present (case-insensitive).
  LOW   if "whenever" or "low priority" present (case-insensitive).
  MEDIUM otherwise.
  If both HIGH and LOW keywords appear, HIGH wins.

Strip ALL of these keywords from the title: urgent, asap, whenever, low priority.

Due-date matching order (first match wins, case-insensitive):
  today, tomorrow, next week,
  next monday, next tuesday, next wednesday, next thursday,
  next friday, next saturday, next sunday,
  monday, tuesday, wednesday, thursday, friday, saturday, sunday.

Title: start from original text, remove priority keywords + date phrase,
collapse whitespace, .strip(). If empty → "Untitled task".
""".strip()

# ---------------------------------------------------------------------------
# Priority keyword tables
# ---------------------------------------------------------------------------
_HIGH_KEYWORDS = ["urgent", "asap"]
_LOW_KEYWORDS  = ["whenever", "low priority"]
_ALL_PRIORITY_KEYWORDS = _HIGH_KEYWORDS + _LOW_KEYWORDS  # order matters for stripping

# ---------------------------------------------------------------------------
# Due-date phrase table — ORDER IS AUTHORITATIVE (first match wins)
# "next <weekday>" entries MUST appear before bare weekday entries.
# ---------------------------------------------------------------------------
_DATE_PHRASES = [
    "today",
    "tomorrow",
    "next week",
    "next monday",
    "next tuesday",
    "next wednesday",
    "next thursday",
    "next friday",
    "next saturday",
    "next sunday",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

# Weekday name → isoweekday() value (Monday=1 … Sunday=7)
_WEEKDAY_NUM = {
    "monday": 1, "tuesday": 2, "wednesday": 3,
    "thursday": 4, "friday": 5, "saturday": 6, "sunday": 7,
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class ParseResult:
    title: str
    priority: str            # "low" | "medium" | "high"
    due_date_hint: Optional[str]  # matched phrase (lower-case) or None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_quick_add(description: str) -> ParseResult:
    """
    Parse a free-text task description into structured fields.

    Simulates the output of the system+user role prompt exchange without
    any network calls.

    Parameters
    ----------
    description : str
        Raw user input from the quick-add text box.

    Returns
    -------
    ParseResult
        title          – cleaned, cased title
        priority       – "low" | "medium" | "high"
        due_date_hint  – matched date phrase (lower-case) or None
    """
    # ----------------------------------------------------------------
    # Build the "user role" message (for documentation / logging)
    # ----------------------------------------------------------------
    user_role_message = description  # kept as-is; the original text is the prompt

    # ----------------------------------------------------------------
    # Step 1 — Priority detection (on lower-cased text)
    # ----------------------------------------------------------------
    lower = description.lower()
    has_high = any(kw in lower for kw in _HIGH_KEYWORDS)
    has_low  = any(kw in lower for kw in _LOW_KEYWORDS)

    if has_high:
        priority = "high"
    elif has_low:
        priority = "low"
    else:
        priority = "medium"

    # ----------------------------------------------------------------
    # Step 2 — Due-date detection (on lower-cased text, first match wins)
    # ----------------------------------------------------------------
    due_date_hint: Optional[str] = None
    for phrase in _DATE_PHRASES:
        if phrase in lower:
            due_date_hint = phrase   # store the exact matched phrase, lower-case
            break

    # ----------------------------------------------------------------
    # Step 3 — Title generation from ORIGINAL-CASED description
    # ----------------------------------------------------------------
    title = _build_title(description, due_date_hint)

    return ParseResult(
        title=title,
        priority=priority,
        due_date_hint=due_date_hint,
    )


def _build_title(description: str, due_date_hint: Optional[str]) -> str:
    """
    Build the cleaned task title.

    Removal is case-insensitive but the original casing of the remaining
    words is preserved.
    """
    result = description

    # Remove ALL occurrences of ALL priority keywords (case-insensitive)
    for kw in _ALL_PRIORITY_KEYWORDS:
        # "low priority" is a two-word phrase — match it literally.
        # Single-word keywords: whole-word match to avoid partial hits.
        if " " in kw:
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
        else:
            pattern = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        result = pattern.sub("", result)

    # Remove ALL occurrences of the matched due-date phrase (case-insensitive)
    if due_date_hint:
        phrase_pattern = re.compile(re.escape(due_date_hint), re.IGNORECASE)
        result = phrase_pattern.sub("", result)

    # Spec requires ONLY .strip() — do NOT collapse internal whitespace.
    # The mandatory regression cases show that double-spaces left by removed
    # keywords are intentional (e.g. "mark it  please" with two spaces).
    result = result.strip()

    # Fallback for empty result
    if not result:
        result = "Untitled task"

    return result


# ---------------------------------------------------------------------------
# Utility: compute actual due date from a hint phrase
# (used by the route to store a concrete YYYY-MM-DD if desired)
# ---------------------------------------------------------------------------

def resolve_due_date(hint: Optional[str], today: Optional[date] = None) -> Optional[str]:
    """
    Convert a due_date_hint phrase to a concrete ISO date string.

    Returns None if hint is None or unrecognised.
    """
    if hint is None:
        return None

    if today is None:
        today = date.today()

    if hint == "today":
        return today.isoformat()

    if hint == "tomorrow":
        return (today + timedelta(days=1)).isoformat()

    if hint == "next week":
        # Start of next week (next Monday)
        days_ahead = 7 - today.isoweekday() + 1   # days until next Monday
        if days_ahead == 0:
            days_ahead = 7
        return (today + timedelta(days=days_ahead)).isoformat()

    # "next <weekday>"
    if hint.startswith("next "):
        weekday_name = hint[5:]  # strip "next "
        if weekday_name in _WEEKDAY_NUM:
            target_dow = _WEEKDAY_NUM[weekday_name]  # 1=Mon … 7=Sun
            current_dow = today.isoweekday()
            days_ahead = (target_dow - current_dow) % 7
            if days_ahead == 0:
                days_ahead = 7  # "next monday" when today IS monday → 7 days ahead
            return (today + timedelta(days=days_ahead)).isoformat()

    # bare weekday
    if hint in _WEEKDAY_NUM:
        target_dow = _WEEKDAY_NUM[hint]
        current_dow = today.isoweekday()
        days_ahead = (target_dow - current_dow) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (today + timedelta(days=days_ahead)).isoformat()

    return None
