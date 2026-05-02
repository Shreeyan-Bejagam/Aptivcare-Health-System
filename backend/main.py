"""FastAPI entrypoint for AptivCare Assistant."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from agent.voice_agent import start_background_worker, stop_background_worker
from api.router import router as api_router
from config import settings
from database.connection import close_db, init_db
from database.migrations import run_migrations
from utils.debug_runtime import debug_log
from utils.logger import configure_logging
from utils.rate_limiter import limiter, rate_limit_exceeded_handler

configure_logging()
logger = logging.getLogger("mykare.main")

_BASE_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "microphone=(self), camera=(), geolocation=()",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for key, value in _BASE_SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)

        if request.url.path in {"/api/health", "/api/sessions"}:
            debug_log(
                run_id="baseline",
                hypothesis_id="H4",
                location="main.py:SecurityHeadersMiddleware.dispatch",
                message="security_headers_applied",
                data={
                    "path": request.url.path,
                    "has_csp": "Content-Security-Policy" in response.headers,
                    "has_hsts": "Strict-Transport-Security" in response.headers,
                    "has_x_frame_options": "X-Frame-Options" in response.headers,
                    "status_code": response.status_code,
                },
            )

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    debug_log(
        run_id="baseline",
        hypothesis_id="H2",
        location="main.py:lifespan:start",
        message="lifespan_starting",
        data={"livekit_configured": settings.livekit_configured},
    )

    logger.info("Starting AptivCare Assistant backend.")
    await init_db()
    await run_migrations()

    if settings.livekit_configured:
        try:
            start_background_worker()
        except Exception:
            logger.exception("Could not start LiveKit agent worker.")
    else:
        logger.warning(
            "LiveKit credentials are not configured. "
            "The voice agent worker will NOT start. "
            "Fill in LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and LIVEKIT_URL "
            "in backend/.env and restart."
        )

    try:
        yield
    finally:
        logger.info("Shutting down.")
        await stop_background_worker()
        await close_db()


app = FastAPI(
    title="AptivCare Assistant",
    version="1.0.0",
    description="Voice AI front-desk for a healthcare clinic.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


def _cors_allow_origins() -> list[str]:
    raw = (settings.FRONTEND_ORIGIN or "").strip()
    return [part.strip() for part in raw.split(",") if part.strip()]


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,
)

app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "name": "AptivCare Assistant",
        "version": app.version,
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )
