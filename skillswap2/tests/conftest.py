"""Pytest bootstrap for project imports."""

from pathlib import Path
import sys

# Ensure project root (skillswap2/) is on sys.path so `import app` works
PROJECT_ROOT = Path(__file__).resolve().parents[1]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

