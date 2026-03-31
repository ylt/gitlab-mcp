"""Custom server session with cleanup callbacks for per-session resource management."""

import logging
from fastmcp.server.low_level import MiddlewareServerSession

logger = logging.getLogger(__name__)


class GitLabServerSession(MiddlewareServerSession):
    """Server session with cleanup callbacks for per-session resource management.

    Subclasses FastMCP's MiddlewareServerSession to add an on_cleanup() hook
    that fires when the session ends. This enables per-session resources
    (like ActionCableManager WebSocket connections) to be deterministically
    cleaned up when a client disconnects.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cleanup_callbacks: list = []

    def on_cleanup(self, callback):
        """Register an async callback to run when this session ends."""
        self._cleanup_callbacks.append(callback)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for cb in self._cleanup_callbacks:
            try:
                await cb()
            except Exception as e:
                logger.warning("Session cleanup callback failed: %s", e)
        return await super().__aexit__(exc_type, exc_val, exc_tb)
