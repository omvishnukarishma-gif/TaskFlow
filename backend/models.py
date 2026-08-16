"""
models.py — SQLAlchemy ORM models.

Hierarchy: User ──1:M──> Project ──1:M──> Task

All relationships use back_populates (not the deprecated backref).
Priority is constrained at the DB level via CheckConstraint.
due_date is stored as a nullable String ("YYYY-MM-DD"), never a DATE column.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    # Nullable so existing users without passwords remain valid rows.
    # Populated via POST /auth/register.
    password_hash = Column(String(255), nullable=True)

    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    # One user owns many projects
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    # One user may have many sessions (one per login)
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    # One user may have many password-reset tokens (one per reset request)
    reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


class Session(Base):
    """
    Opaque session token tied to a user.

    token     — secrets.token_urlsafe(32), used as the bearer credential
    user_id   — FK to users.id (cascade-deletes when user is deleted)
    created_at — stored as ISO-8601 text for portability with SQLite
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    token = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(String(30), nullable=False)   # ISO-8601 text

    user = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session id={self.id} user_id={self.user_id}>"


class PasswordResetToken(Base):
    """
    Single-use, time-limited password-reset token.

    token_hash  — SHA-256 hex digest of the raw token sent to the user.
                  The raw token is NEVER stored; only its hash is persisted.
    user_id     — FK to users.id; cascade-deletes when the user is deleted.
    created_at  — ISO-8601 UTC text, informational only.
    expires_at  — ISO-8601 UTC text; verified as a timezone-aware datetime at
                  use time (NOT compared lexically).
    used        — set to True after one successful password reset; prevents reuse.
    """
    __tablename__ = "password_reset_tokens"

    id         = Column(Integer,     primary_key=True, index=True, autoincrement=True)
    token_hash = Column(String(64),  nullable=False, unique=True, index=True)
    user_id    = Column(Integer,     ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(String(30),  nullable=False)  # ISO-8601 UTC text
    expires_at = Column(String(30),  nullable=False)  # ISO-8601 UTC text
    used       = Column(Boolean,     nullable=False, default=False)

    user = relationship("User", back_populates="reset_tokens")

    def __repr__(self) -> str:
        return f"<PasswordResetToken id={self.id} user_id={self.user_id} used={self.used}>"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Many-to-one: project belongs to a user
    owner = relationship("User", back_populates="projects")
    # One project has many tasks
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(10), nullable=False, default="medium")
    due_date = Column(String(20), nullable=True)   # stored as "YYYY-MM-DD" text or NULL
    completed = Column(Boolean, nullable=False, default=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="ck_tasks_priority",
        ),
    )

    # Many-to-one: task belongs to a project
    project = relationship("Project", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r} priority={self.priority!r}>"
