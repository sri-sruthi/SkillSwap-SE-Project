"""CRUD package exports with lazy module loading.

This avoids importing optional runtime dependencies (e.g. schema extras)
during unrelated unit-test collection.
"""

from importlib import import_module

__all__ = ["user", "skill", "session", "search", "token", "review"]


def __getattr__(name):
    if name in __all__:
        return import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
