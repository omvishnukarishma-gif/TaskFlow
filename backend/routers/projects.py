"""
routers/projects.py — CRUD endpoints for Project resources.

Endpoints:
  POST   /projects          — create (201 | 404 if owner not found)
  GET    /projects          — list all (200)
  GET    /projects/{id}     — single (200 | 404)
  PUT    /projects/{id}     — full/partial update (200 | 404)
  DELETE /projects/{id}     — delete (200 | 404)
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.models import Project, User
from backend.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter()


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return project


def _verify_owner(owner_id: int, db: Session) -> None:
    if db.get(User, owner_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {owner_id} not found",
        )


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    """Create a project. Returns 404 if the specified owner does not exist."""
    _verify_owner(payload.owner_id, db)
    project = Project(
        name=payload.name,
        description=payload.description,
        owner_id=payload.owner_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    """Return all projects."""
    return db.query(Project).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Return a single project by ID."""
    return _get_project_or_404(project_id, db)


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)
):
    """Partially update a project. Only supplied fields are changed."""
    project = _get_project_or_404(project_id, db)
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    if payload.owner_id is not None:
        _verify_owner(payload.owner_id, db)
        project.owner_id = payload.owner_id
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project (and cascade-delete its tasks)."""
    project = _get_project_or_404(project_id, db)
    db.delete(project)
    db.commit()
    return {"detail": "deleted"}
