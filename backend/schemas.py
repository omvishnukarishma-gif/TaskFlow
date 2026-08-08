"""
schemas.py — Pydantic v2 request/response schemas.

Design notes:
- All "Create" schemas validate incoming data.
- All "Out" schemas are used for serialisation (from_attributes=True).
- priority uses Literal so FastAPI returns 422 automatically on bad values.
- due_date is Optional[str]; the custom validator enforces YYYY-MM-DD format
  when a value is provided.
- email uses EmailStr-style regex validation via a custom validator.
- Field(min_length=...) provides the Pydantic Field constraint requirement.
"""

import re
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="User display name")
    email: str = Field(..., min_length=5, max_length=255, description="Unique e-mail address")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email address format")
        return v.lower().strip()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


# ---------------------------------------------------------------------------
# Project schemas
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: Optional[str] = Field(None, description="Optional description")
    owner_id: int = Field(..., gt=0, description="ID of the owning user")


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    owner_id: Optional[int] = Field(None, gt=0)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    owner_id: int


# ---------------------------------------------------------------------------
# Task schemas
# ---------------------------------------------------------------------------

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, description="Optional details")
    priority: Literal["low", "medium", "high"] = Field(
        "medium", description="Task priority — low | medium | high"
    )
    due_date: Optional[str] = Field(
        None, description="ISO date string YYYY-MM-DD or null"
    )
    completed: bool = Field(False, description="Whether the task is done")
    project_id: int = Field(..., gt=0, description="ID of the owning project")

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: Optional[str]) -> Optional[str]:
        """Enforce YYYY-MM-DD format when a value is supplied."""
        if v is None:
            return v
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("due_date must be in YYYY-MM-DD format or null")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high"]] = None
    due_date: Optional[str] = None
    completed: Optional[bool] = None
    project_id: Optional[int] = Field(None, gt=0)

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("due_date must be in YYYY-MM-DD format or null")
        return v


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str]
    priority: str
    due_date: Optional[str]
    completed: bool
    project_id: int


# ---------------------------------------------------------------------------
# Statistics schema
# ---------------------------------------------------------------------------

class PriorityBreakdown(BaseModel):
    low: int
    medium: int
    high: int


class TaskStats(BaseModel):
    total: int
    completed: int
    pending: int
    by_priority: PriorityBreakdown
    completion_rate: float  # 0.0 – 100.0
