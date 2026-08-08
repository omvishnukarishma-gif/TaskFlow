"""
seed.py — Populate the database with sample data for development and testing.

Run from the project root:
    python seed.py          (using system python with the shared venv active)
    <venv>/python seed.py

Idempotent: checks for existing data before inserting to avoid duplicates.
"""

import sys
import os

# Make sure the backend package is importable when run from project root
sys.path.insert(0, os.path.dirname(__file__))

from backend.database import Base, SessionLocal, engine
import backend.models  # noqa: F401 — registers models with metadata

from backend.models import Project, Task, User

# Create tables if they don't exist yet
Base.metadata.create_all(bind=engine)


def seed() -> None:
    db = SessionLocal()
    try:
        # ----------------------------------------------------------------
        # Skip if already seeded
        # ----------------------------------------------------------------
        if db.query(User).count() > 0:
            print("Database already has data — skipping seed.")
            return

        # ----------------------------------------------------------------
        # Users
        # ----------------------------------------------------------------
        alice = User(name="Alice Johnson", email="alice@example.com")
        bob   = User(name="Bob Smith",    email="bob@example.com")
        carol = User(name="Carol White",  email="carol@example.com")
        db.add_all([alice, bob, carol])
        db.flush()  # get auto-generated IDs without committing

        # ----------------------------------------------------------------
        # Projects
        # ----------------------------------------------------------------
        website   = Project(name="Website Redesign",    description="Modernise the company website.",          owner_id=alice.id)
        mobile    = Project(name="Mobile App",          description="Build a cross-platform mobile app.",      owner_id=alice.id)
        backend_p = Project(name="Backend API",         description="RESTful API for the mobile application.", owner_id=bob.id)
        marketing = Project(name="Marketing Campaign",  description="Q3 social media campaign planning.",      owner_id=carol.id)
        db.add_all([website, mobile, backend_p, marketing])
        db.flush()

        # ----------------------------------------------------------------
        # Tasks
        # ----------------------------------------------------------------
        tasks = [
            # Website Redesign
            Task(title="Design homepage mockup",   description="Create wireframes for the new homepage layout.",   priority="high",   due_date="2026-08-15", completed=False, project_id=website.id),
            Task(title="Write copy for about page", description="Craft engaging copy for the About Us section.",   priority="medium", due_date="2026-08-20", completed=False, project_id=website.id),
            Task(title="Set up CI/CD pipeline",    description="Configure GitHub Actions for automated deploys.",  priority="high",   due_date="2026-08-10", completed=True,  project_id=website.id),
            Task(title="SEO audit",                description="Run an SEO audit and fix critical issues.",         priority="low",    due_date=None,         completed=False, project_id=website.id),

            # Mobile App
            Task(title="Define API contract",      description="Document all REST endpoints for the mobile app.", priority="high",   due_date="2026-08-12", completed=True,  project_id=mobile.id),
            Task(title="Implement login screen",   description="Build the user authentication UI.",                priority="high",   due_date="2026-08-18", completed=False, project_id=mobile.id),
            Task(title="Write unit tests",         description="Achieve 80% test coverage for the core modules.", priority="medium", due_date="2026-08-25", completed=False, project_id=mobile.id),

            # Backend API
            Task(title="Set up database schema",   description="Create tables, indexes, and relationships.",      priority="high",   due_date="2026-08-08", completed=True,  project_id=backend_p.id),
            Task(title="Add JWT authentication",   description="Implement token-based auth for all endpoints.",   priority="high",   due_date="2026-08-14", completed=False, project_id=backend_p.id),
            Task(title="Write API documentation",  description="Use Swagger/OpenAPI for full endpoint docs.",     priority="low",    due_date="2026-09-01", completed=False, project_id=backend_p.id),

            # Marketing Campaign
            Task(title="Draft social media calendar", description="Plan posts for Aug–Sep across all platforms.", priority="medium", due_date="2026-08-11", completed=True,  project_id=marketing.id),
            Task(title="Design banner ads",           description="Create 5 banner ad variants for paid campaigns.", priority="medium", due_date="2026-08-22", completed=False, project_id=marketing.id),
            Task(title="Negotiate influencer deals",  description="Reach out to 10 micro-influencers.",            priority="low",    due_date=None,         completed=False, project_id=marketing.id),
        ]

        db.add_all(tasks)
        db.commit()

        print(f"Seeded: {db.query(User).count()} users, "
              f"{db.query(Project).count()} projects, "
              f"{db.query(Task).count()} tasks.")

    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
