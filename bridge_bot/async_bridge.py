"""AsyncBridge — one place to bridge sync Flask routes with async DB calls.

Replaces the duplicate asyncio.run() helpers in api.py and dashboard.py.
Owns a single background event loop so we don't create/destroy loops per request.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import Future
from typing import Any, Coroutine, Optional

logger = logging.getLogger(__name__)

_loop: Optional[asyncio.AbstractEventLoop] = None
_thread: Optional[threading.Thread] = None
_lock = threading.Lock()


def _ensure_loop() -> asyncio.AbstractEventLoop:
    """Lazily start a background event loop (once)."""
    global _loop, _thread
    with _lock:
        if _loop is not None and _loop.is_running():
            return _loop
        _loop = asyncio.new_event_loop()
        _thread = threading.Thread(target=_loop.run_forever, daemon=True, name="async-bridge")
        _thread.start()
        logger.info("AsyncBridge event loop started")
        return _loop


def run_sync(coro: Coroutine) -> Any:
    """Run an async coroutine from a synchronous context (Flask routes).

    Submits the coroutine to the bridge event loop and blocks until done.
    """
    loop = _ensure_loop()
    future: Future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)


def get_loop() -> Optional[asyncio.AbstractEventLoop]:
    """Return the bridge event loop, or None if not started."""
    return _loop


async def shutdown() -> None:
    """Dispose the event loop on application exit."""
    global _loop, _thread
    with _lock:
        if _loop is not None:
            _loop.call_soon_threadsafe(_loop.stop)
            if _thread is not None:
                _thread.join(timeout=5)
            _loop = None
            _thread = None
            logger.info("AsyncBridge event loop shut down")
