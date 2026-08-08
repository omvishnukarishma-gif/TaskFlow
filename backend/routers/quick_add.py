"""
routers/quick_add.py — POST /tasks/quick-add endpoint.

Processing order (strictly enforced):
  1. Validate the incoming request (Pydantic — description + project_id).
  2. Verify the project exists in the database (→ 404 if not).
  3. Parse the description with the deterministic parser.
  4. Validate the generated task data through TaskCreate Pydantic schema.
  5. Persist to the tasks table only after all validation succeeds.

No LLM feature flag is implemented — the deterministic parser IS the
implementation as required by the specification.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.models import Project, Task
from backend.quick_add_parser import parse_quick_add, resolve_due_date
from backend.schemas import TaskCreate, TaskOut

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
        "it to the tasks table. Works completely offline — no API keys needed."
    ),
)
def quick_add_task(
    payload: QuickAddRequest,
    db: Session = Depends(get_db),
):
    """
    STEP 1 — Request is already validated by Pydantic (QuickAddRequest).

    STEP 2 — Verify the project exists.
    """
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {payload.project_id} not found",
        )

    """
    STEP 3 — Parse the description with the deterministic parser.
    The parser applies system-role rules to the user-role message.
    """
    parsed = parse_quick_add(payload.description)

    # Resolve the hint to a concrete date (if present)
    resolved_date = resolve_due_date(parsed.due_date_hint)

    """
    STEP 4 — Validate through TaskCreate Pydantic schema.
    This ensures the generated priority/due_date are spec-compliant
    before we touch the database.
    """
    task_data = TaskCreate(
        title=parsed.title,
        description=None,        # quick-add doesn't provide a description field
        priority=parsed.priority,
        due_date=resolved_date,
        completed=False,
        project_id=payload.project_id,
    )

    """
    STEP 5 — Persist to the existing tasks table.
    Only reached if all prior validation passes.
    """
    task = Task(
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        due_date=task_data.due_date,
        completed=task_data.completed,
        project_id=task_data.project_id,
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
