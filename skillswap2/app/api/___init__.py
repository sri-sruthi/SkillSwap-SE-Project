# app/api/__init__.py
# This file makes the api directory a Python package

# Import all routers for easy access
from . import auth
from . import users
from . import skill
from . import session
from . import search

__all__ = ["auth", "users", "skill", "session", "search"]