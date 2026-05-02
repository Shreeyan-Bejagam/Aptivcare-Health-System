"""
LiveKit voice agent worker.

This module spins up a `VoicePipelineAgent` configured with:

    Deepgram STT (when DEEPGRAM_API_KEY is set) else OpenAI STT
        -> OpenAI LLM (tool calling)
            -> Cartesia TTS (when CARTESIA_* is set) else OpenAI TTS

It hooks into the agent's lifecycle to (a) append every spoken turn to the
session row in SQLite (so the transcript can be reviewed mid-call and used by
the post-call summariser) and (b) keep a running tally of audio time and
characters spoken for the cost breakdown.

Two ways to run it:
  * Embedded — main.py launches `run_worker_in_background()` as an asyncio task
    so a single process serves HTTP + the agent. This is what the README
    documents and what most demo deployments will use.
  * Standalone — `python -m agent.voice_agent dev` (or `start`) goes through
    LiveKit's `cli.run_app()` for production scale-out across worker pods.

Both code paths share `entrypoint(...)`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm as agent_llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, silero

try:
    from livekit.plugins import deepgram as deepgram_plugin
except ImportError:                    
    deepgram_plugin = None                            

try:
    from livekit.plugins import cartesia as cartesia_plugin
except ImportError:                    
    cartesia_plugin = None                            

from config import settings
from database.connection import init_db
from database.migrations import run_migrations
from database.models import TranscriptTurn

from .transcript_store import append_transcript_turn
from .state import AgentSessionState
from .system_prompt import SYSTEM_PROMPT
from .tools.registry import build as build_tool_context

logger = logging.getLogger("mykare.agent")


                                                                              


def _resolve_session_id(ctx: JobContext) -> str:
    """Pull the session id out of room metadata (set by /api/sessions)."""
    metadata = ctx.room.metadata or ""
    if metadata:
        try:
            decoded = json.loads(metadata)
            if isinstance(decoded, dict) and decoded.get("session_id"):
                return str(decoded["session_id"])
        except json.JSONDecodeError:
            pass
                                                                                
    return ctx.room.name


async def entrypoint(ctx: JobContext) -> None:
    """Per-room entrypoint invoked by LiveKit when an agent is dispatched."""

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("Agent connected to room=%s", ctx.room.name)

    session_id = _resolve_session_id(ctx)
    state = AgentSessionState(session_id=session_id, room=ctx.room)

                                                      
    vad = silero.VAD.load()
    if settings.deepgram_configured and deepgram_plugin is not None:
        stt = deepgram_plugin.STT(
            model=settings.DEEPGRAM_MODEL,
            language="en-US",
            api_key=settings.DEEPGRAM_API_KEY,
        )
        logger.info("Using Deepgram streaming STT (%s).", settings.DEEPGRAM_MODEL)
    else:
        stt = openai.STT(
            model=settings.OPENAI_STT_MODEL,
            language="en",
        )
        if not settings.deepgram_configured:
            logger.warning(
                "DEEPGRAM_API_KEY is empty — falling back to OpenAI STT for this call."
            )

    if settings.cartesia_configured and cartesia_plugin is not None:
        tts = cartesia_plugin.TTS(
            model=settings.CARTESIA_TTS_MODEL,
            voice=settings.CARTESIA_VOICE_ID,
            api_key=settings.CARTESIA_API_KEY,
        )
        logger.info("Using Cartesia streaming TTS (%s).", settings.CARTESIA_TTS_MODEL)
    else:
        tts = openai.TTS(
            model=settings.OPENAI_TTS_MODEL,
            voice=settings.OPENAI_TTS_VOICE,
        )
        if not settings.cartesia_configured:
            logger.warning(
                "Cartesia is not fully configured (need CARTESIA_API_KEY + "
                "CARTESIA_VOICE_ID) — falling back to OpenAI TTS for this call."
            )

    llm_inst = openai.LLM(model=settings.OPENAI_LLM_MODEL)

    today = datetime.now().strftime("%A %d %B %Y")
    initial_chat_ctx = agent_llm.ChatContext().append(
        role="system",
        text=f"{SYSTEM_PROMPT}\n\nToday's date is {today}.",
    )

    fnc_ctx = build_tool_context(state)

    pipeline = VoicePipelineAgent(
        vad=vad,
        stt=stt,
        llm=llm_inst,
        tts=tts,
        chat_ctx=initial_chat_ctx,
        fnc_ctx=fnc_ctx,
                                                                        
        min_endpointing_delay=0.6,
    )

                                                                        
                                                                        
                                                                        

    def _on_user_speech(msg: agent_llm.ChatMessage) -> None:
        text = (msg.content or "").strip() if isinstance(msg.content, str) else ""
        if not text:
            return
        state.metrics.turn_count += 1
        state.conversation_history.append({"role": "user", "content": text})
        asyncio.create_task(
            append_transcript_turn(
                session_id,
                TranscriptTurn(
                    role="user",
                    content=text,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ),
            )
        )

    def _on_agent_speech(msg: agent_llm.ChatMessage) -> None:
        text = (msg.content or "").strip() if isinstance(msg.content, str) else ""
        if not text:
            return
        state.metrics.cartesia_chars += len(text)
        state.metrics.turn_count += 1
        state.conversation_history.append({"role": "assistant", "content": text})
        asyncio.create_task(
            append_transcript_turn(
                session_id,
                TranscriptTurn(
                    role="assistant",
                    content=text,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ),
            )
        )

    pipeline.on("user_speech_committed", _on_user_speech)
    pipeline.on("agent_speech_committed", _on_agent_speech)

                                                                        
                                                     
                                                                        

    def _on_metrics(metrics: Any) -> None:
        try:
            if hasattr(metrics, "input_tokens"):
                state.metrics.claude_input_tokens += int(metrics.input_tokens or 0)
            if hasattr(metrics, "output_tokens"):
                state.metrics.claude_output_tokens += int(metrics.output_tokens or 0)
            if hasattr(metrics, "audio_duration"):
                state.metrics.deepgram_seconds += float(metrics.audio_duration or 0.0)
        except Exception:                
            logger.debug("Could not parse metrics frame", exc_info=True)

    pipeline.on("metrics_collected", _on_metrics)

                                                                             
    participant = await ctx.wait_for_participant()
    logger.info("Participant joined: identity=%s", participant.identity)

    pipeline.start(ctx.room, participant)

                                                                     
    await pipeline.say(
        "Hi, this is Aarav from AptivCare. How can I help you today?",
        allow_interruptions=True,
    )


                                                                              


_BACKGROUND_TASK: asyncio.Task | None = None


async def _run_worker_async() -> None:
    """Run the LiveKit Worker in the current event loop until cancelled."""

                                                                               
    from livekit.agents import Worker

    options = WorkerOptions(
        entrypoint_fnc=entrypoint,
        ws_url=settings.LIVEKIT_URL,
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
    )
    worker = Worker(options)
    try:
        await worker.run()
    except asyncio.CancelledError:
        logger.info("LiveKit worker cancelled, shutting down.")
        await worker.aclose()
        raise


def start_background_worker() -> asyncio.Task:
    """Schedule the worker as an asyncio task on the current loop."""

    global _BACKGROUND_TASK
    if _BACKGROUND_TASK is not None and not _BACKGROUND_TASK.done():
        return _BACKGROUND_TASK
    loop = asyncio.get_event_loop()
    _BACKGROUND_TASK = loop.create_task(_run_worker_async(), name="livekit-worker")
    logger.info("LiveKit agent worker scheduled in background.")
    return _BACKGROUND_TASK


async def stop_background_worker() -> None:
    """Cancel and await the background worker, if any."""
    global _BACKGROUND_TASK
    if _BACKGROUND_TASK is None:
        return
    _BACKGROUND_TASK.cancel()
    try:
        await _BACKGROUND_TASK
    except (asyncio.CancelledError, Exception):                
        pass
    finally:
        _BACKGROUND_TASK = None


                                                                              


async def _standalone_prelude() -> None:
    """Initialise the DB so tools have somewhere to read/write."""
    await init_db()
    await run_migrations()


def _main_standalone() -> None:
    asyncio.get_event_loop().run_until_complete(_standalone_prelude())
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            ws_url=settings.LIVEKIT_URL,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        )
    )


if __name__ == "__main__":
    _main_standalone()
