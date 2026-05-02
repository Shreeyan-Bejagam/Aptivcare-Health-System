"""
ASGI application entry (spec layout).

The canonical ``app`` instance is still assembled in the repository-root ``main.py``
for backwards-compatible ``uvicorn main:app`` invocations. Import from here when you
prefer ``uvicorn app.main:app`` instead.
"""

from __future__ import annotations

from main import app

__all__ = ["app"]
