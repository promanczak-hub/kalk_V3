"""Shared retry helper for Supabase calls.

Wraps `.execute()` with exponential backoff for transient transport errors:
- httpx.ConnectError / RemoteProtocolError
- httpcore.ConnectError / ReadError
- WinError 10061 (Windows TCP ephemeral port exhaustion under load)
- "Server disconnected", "Connection reset by peer", timeouts

Production paths (matrix builds, batched fetches) repeatedly hit Supabase
under load and exhaust ephemeral ports on Windows; tests reproduce this
intermittently as well. Use this helper for any direct `.execute()` call
in hot fetch paths.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_TRANSIENT_MARKERS = (
    "winerror 10061",
    "connection refused",
    "connection reset",
    "server disconnected",
    "remoteprotocolerror",
    "connecterror",
    "readerror",
    "readtimeout",
    "writetimeout",
    "timeout",
    "unreachable",
    "nie można nawiązać połączenia",
    "połączenie zostało przerwane",
)


def _is_transient(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    if "connect" in name or "timeout" in name or "protocol" in name:
        return True
    msg = str(exc).lower()
    return any(marker in msg for marker in _TRANSIENT_MARKERS)


def execute_with_retry(query_obj: Any, max_retries: int = 5, base_delay: float = 0.5) -> Any:
    """Execute a Supabase query with exponential backoff on transient transport errors.

    Re-raises immediately on non-transient errors (4xx/5xx responses, schema
    issues, etc.) so genuine failures aren't masked.
    """
    last_exc: BaseException | None = None
    for attempt in range(max_retries):
        try:
            return query_obj.execute()
        except Exception as exc:
            last_exc = exc
            if not _is_transient(exc):
                raise
            if attempt + 1 >= max_retries:
                break
            delay = base_delay * (2**attempt)
            logger.warning(
                "Supabase transient error (attempt %d/%d), retrying in %.1fs: %s: %s",
                attempt + 1,
                max_retries,
                delay,
                type(exc).__name__,
                exc,
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc
