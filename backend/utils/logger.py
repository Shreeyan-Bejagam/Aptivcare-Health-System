"""
Centralised logging configuration.

We use the stdlib `logging` module with a single line-formatter that's compact
enough for tail-friendly local development but still includes enough context
(`name`, `levelname`, timestamp) to be useful in aggregated production logs.

All modules should obtain a logger via `logging.getLogger("mykare.<area>")` so
log records share the `mykare` namespace and can be filtered as a group.
"""

from __future__ import annotations

import logging
import logging.config
import sys

from config import settings

_CONFIGURED = False


def configure_logging() -> None:
    """Apply the project-wide logging configuration. Idempotent."""

    global _CONFIGURED
    if _CONFIGURED:
        return

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": (
                        "%(asctime)s.%(msecs)03d "
                        "%(levelname)-7s "
                        "%(name)s :: %(message)s"
                    ),
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "default",
                    "level": settings.LOG_LEVEL,
                },
            },
            "loggers": {
                "mykare": {
                    "handlers": ["console"],
                    "level": settings.LOG_LEVEL,
                    "propagate": False,
                },
                                                                                   
                "livekit": {"handlers": ["console"], "level": "INFO", "propagate": False},
                "livekit.agents": {"handlers": ["console"], "level": "INFO", "propagate": False},
                "uvicorn": {"handlers": ["console"], "level": "INFO", "propagate": False},
                "uvicorn.access": {
                    "handlers": ["console"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
            "root": {"handlers": ["console"], "level": "WARNING"},
        }
    )

    _CONFIGURED = True
