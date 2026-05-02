"""
Health check endpoint.

Returns enough information for an external uptime probe (or Railway's healthcheck)
to know whether the FastAPI process AND its SQLite handle are usable. Does not
exercise the LiveKit / Anthropic upstreams — those have their own status pages
and we don't want a transient hiccup there to fail our probe.
"""

from __future__ import annotations

from fastapi import APIRouter

from config import settings
from database.connection import get_db
from utils.debug_runtime import debug_log

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    db_ok = True
    try:
        db = get_db()
        async with db.execute("SELECT 1") as cursor:
            await cursor.fetchone()
    except Exception:                                                   
        db_ok = False
                      
    debug_log(
        run_id="baseline",
        hypothesis_id="H5",
        location="api/health.py:health",
        message="health_checked",
        data={
            "db_ok": db_ok,
            "livekit_configured": settings.livekit_configured,
            "voice_pipeline_configured": settings.voice_pipeline_configured,
        },
    )
               

    return {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "livekit_configured": settings.livekit_configured,
        "voice_pipeline_configured": settings.voice_pipeline_configured,
        "websocket_voice_configured": settings.websocket_voice_configured,
    }
