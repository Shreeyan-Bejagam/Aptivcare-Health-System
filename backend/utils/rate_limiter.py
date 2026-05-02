"""
Rate limiting middleware.

We use slowapi (FastAPI port of flask-limiter) keyed off the remote IP address.
The shared `limiter` instance is imported by routers that want to attach a
`@limiter.limit(...)` decorator to specific endpoints, and by `main.py` which
registers the 429-handler.

The limiter is in-memory; for multi-instance deployments swap the storage URI
to Redis (e.g. `storage_uri="redis://..."`). For the single-instance dev/demo
deployment described in the README, in-memory is correct.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse


limiter = Limiter(key_func=get_remote_address, default_limits=[])


def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Return a JSON 429 with a hint about the limit that was tripped."""

    detail = getattr(exc, "detail", "Too many requests")
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limited", "detail": str(detail)},
        headers={"Retry-After": "60"},
    )
