"""
routers/tasks.py — CRUD + statistics endpoints for Task resources.

Endpoints:
  POST   /tasks           — create (201 | 422 | 404)
  GET    /tasks           — list all (200)
  GET    /tasks/stats     — SQL-aggregated statistics (200)
  GET    /tasks/{id}      — single (200 | 404)
  PUT    /tasks/{id}      — partial update (200 | 422 | 404)
  DELETE /tasks/{id}      — delete (200 | 404)

Statistics are computed entirely in SQL using func.count / func.sum —
not by fetching rows and counting in Python.

IMPORTANT: /tasks/stats and any other fixed-path routes MUST be registered
BEFORE /{task_id} to prevent FastAPI interpreting "stats" as an integer id.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.models import Project, Task
from backend.schemas import (
    PriorityBreakdown,
    TaskCreate,
    TaskOut,
    TaskStats,
    TaskUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_task_or_404(task_id: int, db: Session) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return task


def _verify_project(project_id: int, db: Session) -> None:
    if db.get(Project, project_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )


# ---------------------------------------------------------------------------
# Statistics — must come BEFORE /{task_id} route
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=TaskStats)
def get_task_stats(
    project_id: Optional[int] = Query(None, description="Filter stats to a single project"),
    db: Session = Depends(get_db),
):
    """
    Return aggregate task statistics computed entirely in SQL.

    Optional query param: ?project_id=N  restricts to that project.
    """
    query = db.query(
        func.count(Task.id).label("total"),
        func.sum(case((Task.completed == True, 1), else_=0)).label("completed"),
        func.sum(case((Task.priority == "low", 1), else_=0)).label("low"),
        func.sum(case((Task.priority == "medium", 1), else_=0)).label("medium"),
        func.sum(case((Task.priority == "high", 1), else_=0)).label("high"),
    )

    if project_id is not None:
        query = query.filter(Task.project_id == project_id)

    row = query.one()

    total = row.total or 0
    completed = row.completed or 0
    pending = total - completed
    low = row.low or 0
    medium = row.medium or 0
    high = row.high or 0
    completion_rate = round((completed / total * 100), 2) if total > 0 else 0.0

    return TaskStats(
        total=total,
        completed=completed,
        pending=pending,
        by_priority=PriorityBreakdown(low=low, medium=medium, high=high),
        completion_rate=completion_rate,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    """Create a task. Pydantic validates priority and due_date before DB write."""
    _verify_project(payload.project_id, db)
    task = Task(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
        completed=payload.completed,
        project_id=payload.project_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=List[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    """Return all tasks."""
    return db.query(Task).all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Return a single task by ID."""
    return _get_task_or_404(task_id, db)


@router.put("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    """Partially update a task. Only supplied fields are written."""
    task = _get_task_or_404(task_id, db)
    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.due_date is not None:
        task.due_date = payload.due_date
    if payload.completed is not None:
        task.completed = payload.completed
    if payload.project_id is not None:
        _verify_project(payload.project_id, db)
        task.project_id = payload.project_id
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task."""
    task = _get_task_or_404(task_id, db)
    db.delete(task)
    db.commit()
    return {"detail": "deleted"}
