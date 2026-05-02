"""
Re-export of the summary endpoint.

The actual handler lives next to the session POST endpoint in `api/sessions.py`
(they share token-related concerns). This module exists so the router tree
matches the file layout described in the spec; it forwards the same APIRouter.
"""

from .sessions import router                           
