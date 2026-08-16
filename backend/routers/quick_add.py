"""
routers/quick_add.py — POST /tasks/quick-add endpoint.

Processing order (strictly enforced):
  1. Validate the incoming request (Pydantic — description + project_id).
  2. Verify the project exists in the database (→ 422 if not found).
  3. Build the role-based message structure (system + user roles).
  4. Parse the description with the deterministic parser.
  5. Persist to the tasks table only after all validation succeeds.

Role-based structure
--------------------
The endpoint constructs an explicit role-based messages list before parsing:

  messages = [
      {"role": "system", "content": SYSTEM_ROLE},
      {"role": "user",   "content": description},
  ]

This mirrors the structure of a real LLM prompt exchange.
The deterministic parser then applies the system-role rules to the
user-role message entirely offline — no network calls, no API keys.

The due_date field stores the raw parser hint (e.g. "next friday",
"tomorrow") exactly as matched — no calendar resolution is performed.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.models import Project, Task
from backend.quick_add_parser import SYSTEM_ROLE, parse_quick_add
from backend.schemas import TaskOut

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

class QuickAddRequest(BaseModel):
    """
    Quick-add request body.

    'description' maps to the USER ROLE in the prompt structure.
    The SYSTEM ROLE is defined in quick_add_parser.SYSTEM_ROLE and
    describes the deterministic parsing rules applied to the description.
    """
    description: str = Field(
        ...,
        description="Free-text task description (the user role message).",
    )
    project_id: int = Field(
        ...,
        gt=0,
        description="ID of the project this task belongs to.",
    )


# ---------------------------------------------------------------------------
# Response schema (extends TaskOut with parser metadata)
# ---------------------------------------------------------------------------

class QuickAddOut(TaskOut):
    """TaskOut plus the parser's due_date_hint for transparency."""
    due_date_hint: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=QuickAddOut,
    status_code=status.HTTP_201_CREATED,
    summary="Quick-add a task from free-text",
    description=(
        "Parse a natural-language description into a structured task using "
        "the deterministic parser (system + user role structure), then persist "
        "it to the tasks table. Works completely offline — no API keys needed. "
        "The due_date field stores the raw parser hint as-is (e.g. 'next friday')."
    ),
)
def quick_add_task(
    payload: QuickAddRequest,
    db: Session = Depends(get_db),
):
    """
    STEP 1 — Request is already validated by Pydantic (QuickAddRequest).

    STEP 2 — Verify the project exists → 422 if not found.
    """
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Project {payload.project_id} not found",
        )

    """
    STEP 3 — Build the role-based message structure.
    The system role encodes all parsing rules.
    The user role is the raw free-text description from the caller.
    This mirrors the structure of a real LLM prompt exchange.
    """
    messages: List[dict] = [
        {"role": "system", "content": SYSTEM_ROLE},
        {"role": "user",   "content": payload.description},
    ]

    """
    STEP 4 — Parse the description with the deterministic parser.
    The parser applies the system-role rules to the user-role message.
    The due_date_hint is stored raw — no calendar resolution.
    """
    parsed = parse_quick_add(messages[1]["content"])

    """
    STEP 5 — Persist to the existing tasks table.
    due_date stores the raw hint string exactly as returned by the parser
    (e.g. "next friday", "tomorrow", "monday") or None if no date was found.
    Only reached if all prior validation passes.
    """
    task = Task(
        title=parsed.title,
        description=None,          # quick-add doesn't provide a separate description
        priority=parsed.priority,
        due_date=parsed.due_date_hint,   # raw hint, not a resolved YYYY-MM-DD date
        completed=False,
        project_id=payload.project_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Return the persisted task plus the hint for transparency
    return QuickAddOut(
        id=task.id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        due_date=task.due_date,
        completed=task.completed,
        project_id=task.project_id,
        due_date_hint=parsed.due_date_hint,
    )
