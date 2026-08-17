"""
Shared FastAPI dependencies for the API layer.

Endpoints import `get_db` from here rather than directly from
`url_shortener.db.session`. This indirection is cheap now but pays off
later: if you ever need to swap session behavior for API routes
specifically (e.g. a read-replica session for GET endpoints, or request-
scoped auth context), you change it in one place instead of hunting
through every endpoint file's imports.
"""

from url_shortener.db.session import get_db

__all__ = ["get_db"]