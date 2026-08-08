"""
routers/users.py — CRUD endpoints for User resources.

Endpoints:
  POST   /users          — create a user (201)
  GET    /users          — list all users (200)
  GET    /users/{id}     — get single user (200 | 404)
  PUT    /users/{id}     — full update (200 | 404)
  DELETE /users/{id}     — delete (200 | 404)

Duplicate email returns 400.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.dependencies import get_db
from backend.models import User
from backend.schemas import UserCreate, UserOut

router = APIRouter()


def _get_user_or_404(user_id: int, db: Session) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return user


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Create a new user. Returns 400 if the email is already registered."""
    user = User(name=payload.name, email=payload.email)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{payload.email}' is already registered",
        )
    return user


@router.get("", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)):
    """Return all users."""
    return db.query(User).all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Return a single user by ID."""
    return _get_user_or_404(user_id, db)


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserCreate, db: Session = Depends(get_db)):
    """Replace a user's name and/or email."""
    user = _get_user_or_404(user_id, db)
    user.name = payload.name
    user.email = payload.email
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{payload.email}' is already registered",
        )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete a user (and cascade-delete their projects and tasks)."""
    user = _get_user_or_404(user_id, db)
    db.delete(user)
    db.commit()
    return {"detail": "deleted"}
