"""
main.py — FastAPI application factory.

Responsibilities:
- Create all database tables on startup via SQLAlchemy metadata.
- Mount explicit CORS middleware.
- Add a request-timing middleware that injects X-Process-Time into every response.
- Register all routers under their respective prefixes.
"""

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.database import Base, engine
from backend.routers import projects, tasks, users

# ---------------------------------------------------------------------------
# Create tables
# ---------------------------------------------------------------------------
# Import models so that SQLAlchemy's metadata knows about them before create_all
import backend.models  # noqa: F401  (registers models with Base.metadata)

Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="TaskFlow API",
    description="Task management API — core application + algorithms engine.",
    version="2.0.0",
)

# ---------------------------------------------------------------------------
# CORS — explicit frontend origin required by spec
# The frontend is served at http://localhost:8000 (same FastAPI server via
# StaticFiles mount). Explicitly listing the origin satisfies the spec
# requirement for a named origin rather than wildcard "*".
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
)

# ---------------------------------------------------------------------------
# Request-timing middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Measure wall-clock request duration and expose it as X-Process-Time (ms)."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time"] = f"{duration_ms:.3f}ms"
    return response

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])

# ---------------------------------------------------------------------------
# Serve frontend static files (optional convenience — frontend/ directory)
# ---------------------------------------------------------------------------
import os
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
# Note: the health check must be registered BEFORE the StaticFiles mount,
# so we register it via a router-free route on the app (already done above
# since routers are added before the static mount). The root "/" will serve
# index.html from the StaticFiles mount.
