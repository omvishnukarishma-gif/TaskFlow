"""
run_server.py — Convenience script to start the TaskFlow development server.

Launches uvicorn using the virtual environment in this project directory.
Run from the project root:

    python run_server.py

Or equivalently:

    venv\\Scripts\\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
"""

import os
import sys

# Resolve the venv python relative to this script's own directory so it works
# regardless of where the script is invoked from.
_here = os.path.dirname(os.path.abspath(__file__))
_venv_python = os.path.join(_here, "venv", "Scripts", "python.exe")

if not os.path.isfile(_venv_python):
    # Fall back to the current interpreter (e.g. if running inside the venv already)
    _venv_python = sys.executable

os.execv(_venv_python, [
    _venv_python, "-m", "uvicorn", "backend.main:app",
    "--host", "127.0.0.1", "--port", "8000",
])
