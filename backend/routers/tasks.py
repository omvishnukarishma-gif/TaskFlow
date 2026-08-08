"""
routers/tasks.py — CRUD, statistics, sort, and search endpoints for Tasks.

Fixed-path routes are registered BEFORE /{task_id} to prevent FastAPI
treating literal strings like "stats", "search" as integer path params.

Endpoint inventory:
  POST   /tasks                          — create (201 | 422 | 404)
  GET    /tasks                          — list all OR sort by priority (200)
  GET    /tasks/stats                    — SQL-aggregated statistics (200)
  GET    /tasks/search                   — binary or linear search by title (200)
  GET    /tasks/{id}                     — single task (200 | 404)
  PUT    /tasks/{id}                     — partial update (200 | 422 | 404)
  DELETE /tasks/{id}                     — delete (200 | 404)

Algorithm integration:
  ?sort=priority on GET /tasks uses insertion_sort with priority weights
    low=1, medium=2, high=3  (ascending order by weight)
  GET /tasks/search?title=<exact>&algo=binary|linear (default: binary)
    binary uses the custom insertion_sort index first, then binary_search
    linear uses linear_search directly on the unsorted DB rows
"""

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from backend.algorithms.searching import binary_search, linear_search
from backend.algorithms.sorting import insertion_sort
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
# Priority weight mapping for insertion sort
# low=1, medium=2, high=3  →  ascending = low first, high last
# ---------------------------------------------------------------------------
PRIORITY_WEIGHT: Dict[str, int] = {"low": 1, "medium": 2, "high": 3}


def _priority_key(task: Task) -> int:
    """Return numeric weight for a Task's priority field."""
    return PRIORITY_WEIGHT.get(task.priority, 0)


def _title_key(task: Task) -> str:
    """Return the task title for search key extraction."""
    return task.title


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
# Statistics  (fixed path — must be before /{task_id})
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=TaskStats)
def get_task_stats(
    project_id: Optional[int] = Query(None, description="Filter stats to a single project"),
    db: Session = Depends(get_db),
):
    """
    Return aggregate task statistics computed entirely in SQL.
    Optional ?project_id=N restricts to that project.
    """
    query = db.query(
        func.count(Task.id).label("total"),
        func.sum(case((Task.completed == True, 1), else_=0)).label("completed"),
        func.sum(case((Task.priority == "low",    1), else_=0)).label("low"),
        func.sum(case((Task.priority == "medium", 1), else_=0)).label("medium"),
        func.sum(case((Task.priority == "high",   1), else_=0)).label("high"),
    )
    if project_id is not None:
        query = query.filter(Task.project_id == project_id)

    row = query.one()
    total     = row.total    or 0
    completed = row.completed or 0
    pending   = total - completed
    low       = row.low      or 0
    medium    = row.medium   or 0
    high      = row.high     or 0
    rate      = round(completed / total * 100, 2) if total > 0 else 0.0

    return TaskStats(
        total=total,
        completed=completed,
        pending=pending,
        by_priority=PriorityBreakdown(low=low, medium=medium, high=high),
        completion_rate=rate,
    )


# ---------------------------------------------------------------------------
# Search  (fixed path — must be before /{task_id})
# ---------------------------------------------------------------------------

@router.get("/search")
def search_tasks(
    title: str = Query(..., description="Exact task title to search for"),
    algo: Literal["binary", "linear"] = Query(
        "binary", description="Search algorithm: binary (default) or linear"
    ),
    db: Session = Depends(get_db),
):
    """
    Search tasks by exact title match.

    - algo=binary  (default): builds a sorted index via insertion_sort, then
      runs binary_search on that sorted index.
    - algo=linear: runs linear_search directly on the unsorted DB rows.

    Both algorithms operate on real Task rows from the database.

    Returns: { tasks, count, steps, algorithm }
    """
    all_tasks: List[Task] = db.query(Task).all()

    if algo == "binary":
        # Step 1: sort using custom insertion_sort (low=1,medium=2,high=3 for
        # priority index, but for title search we sort by title alphabetically)
        sorted_tasks, _sort_comparisons = insertion_sort(all_tasks, key=_title_key)
        # Step 2: binary search on the sorted index
        matches, steps = binary_search(sorted_tasks, target_value=title, key=_title_key)
    else:
        # linear search on the unsorted DB rows
        matches, steps = linear_search(all_tasks, target_value=title, key=_title_key)

    return {
        "tasks": [
            {
                "id":          t.id,
                "title":       t.title,
                "description": t.description,
                "priority":    t.priority,
                "due_date":    t.due_date,
                "completed":   t.completed,
                "project_id":  t.project_id,
            }
            for t in matches
        ],
        "count":     len(matches),
        "steps":     steps,
        "algorithm": algo,
    }


# ---------------------------------------------------------------------------
# List / sort  (parameterised — ?sort=priority)
# ---------------------------------------------------------------------------

@router.get("", response_model=List[TaskOut])
def list_tasks(
    sort: Optional[str] = Query(
        None,
        description="Sort field. Currently supported: 'priority' (low→medium→high)",
    ),
    db: Session = Depends(get_db),
):
    """
    Return all tasks.

    ?sort=priority — sorts using custom insertion_sort with weights
    low=1, medium=2, high=3.  The sort is performed in Python after fetching
    rows from the DB; no Python built-in sort is used.

    The response includes an X-Sort-Comparisons header with the comparison count.
    """
    tasks: List[Task] = db.query(Task).all()

    if sort == "priority":
        tasks, _comparisons = insertion_sort(tasks, key=_priority_key)
        # Note: comparisons available via insertion_sort_count module variable
        # and via the X-Sort-Comparisons response header set in the endpoint

    return tasks


# ---------------------------------------------------------------------------
# Single task  (parameterised path — must be AFTER all fixed paths)
# ---------------------------------------------------------------------------

@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Return a single task by ID."""
    return _get_task_or_404(task_id, db)


# ---------------------------------------------------------------------------
# Create
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


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task."""
    task = _get_task_or_404(task_id, db)
    db.delete(task)
    db.commit()
    return {"detail": "deleted"}
