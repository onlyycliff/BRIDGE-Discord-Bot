"""Adapter — focused interfaces between the API layer and the Discord bot.

Five interfaces, each independently substitutable:
  - PollAdapter: poll lifecycle (send, end, state)
  - BotStatus: read-only bot state (ready, latency, avatar, start time)
  - ChannelDirectory: channel and role listing (delegates to ChannelCache)
  - EventLoopBridge: sync→async bridging (schedule coroutine, get loop)
  - VoteRecorder: vote persistence (in-memory dedup + DB)

BotAdapter is a composite ABC that extends all five. RealBotAdapter
implements the composite; StubBotAdapter provides test doubles.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Focused interfaces
# ---------------------------------------------------------------------------

class PollAdapter(ABC):
    """Poll lifecycle: send, end, state queries."""

    @abstractmethod
    async def send_poll(
        self,
        question: str,
        options: List[str],
        channel_id: Optional[int] = None,
        role_ids: Optional[List[int]] = None,
        max_votes_per_option: Optional[int] = None,
        description: str = '',
        poll_type: str = 'poll',
    ) -> bool:
        ...

    @abstractmethod
    async def end_poll_and_send_results(self, poll_id: int) -> bool:
        ...

    @abstractmethod
    def is_poll_active(self, poll_id: int) -> bool:
        ...

    @abstractmethod
    def end_poll_in_state(self, poll_id: int) -> bool:
        ...


class BotStatus(ABC):
    """Read-only bot state."""

    @abstractmethod
    def is_bot_ready(self) -> bool:
        ...

    @abstractmethod
    def get_bot_latency_ms(self) -> float:
        ...

    @abstractmethod
    def get_bot_avatar_url(self) -> str:
        ...

    @abstractmethod
    def get_bot_start_time(self) -> Optional[datetime]:
        ...


class ChannelDirectory(ABC):
    """Channel and role listing. Delegates to ChannelCache."""

    @abstractmethod
    def list_channels(self) -> List[Dict[str, str]]:
        ...

    @abstractmethod
    def list_roles(self) -> List[Dict[str, str]]:
        ...


class EventLoopBridge(ABC):
    """Sync→async bridging for the Discord bot's event loop."""

    @abstractmethod
    def schedule_coroutine(self, coro) -> object:
        """Schedule an async coroutine on the bot's event loop from a sync context."""
        ...

    @abstractmethod
    def get_event_loop(self):
        """Return the bot's event loop, or None."""
        ...


class VoteRecorder(ABC):
    """Vote persistence: in-memory dedup + database write."""

    @abstractmethod
    def record_vote(
        self,
        poll_id: int,
        user_id: int,
        username: str,
        question_id: int,
        option_id: int | None,
        question_type,
    ) -> bool:
        """Record a vote in both the in-memory cache and the database.

        Returns True if the vote was new, False if the user already voted.
        """
        ...


# ---------------------------------------------------------------------------
# Composite interface (backward compat)
# ---------------------------------------------------------------------------

class BotAdapter(PollAdapter, BotStatus, ChannelDirectory, EventLoopBridge, VoteRecorder):
    """Composite ABC extending all five focused interfaces.

    Existing code that depends on ``BotAdapter`` continues to work.
    New code should depend on the specific interface it needs.
    """
    pass


# ---------------------------------------------------------------------------
# Production adapter (composite)
# ---------------------------------------------------------------------------

class RealBotAdapter(BotAdapter):
    """Production adapter — delegates to bridge_bot.bot internals."""

    def __init__(self):
        import bridge_bot.bot as _bot_mod
        from bridge_bot.poll_orchestrator import send_poll, end_poll_and_send_results
        self._bot = _bot_mod.bot
        self._poll_state = _bot_mod.poll_state
        self._send_poll = send_poll
        self._end_poll_and_send_results = end_poll_and_send_results
        self._ctx = _bot_mod.ctx
        self._bot_mod = _bot_mod

    async def send_poll(
        self,
        question: str,
        options: List[str],
        channel_id: Optional[int] = None,
        role_ids: Optional[List[int]] = None,
        max_votes_per_option: Optional[int] = None,
        description: str = '',
        poll_type: str = 'poll',
    ) -> bool:
        return await self._send_poll(
            self._ctx,
            question, options,
            channel_id=channel_id, role_ids=role_ids,
            max_votes_per_option=max_votes_per_option,
            description=description, poll_type=poll_type,
        )

    async def end_poll_and_send_results(self, poll_id: int) -> bool:
        return await self._end_poll_and_send_results(self._ctx, poll_id)

    def is_poll_active(self, poll_id: int) -> bool:
        return self._poll_state.is_active(poll_id)

    def end_poll_in_state(self, poll_id: int) -> bool:
        from db.operations import poll_op
        from bridge_bot.async_bridge import run_sync
        try:
            result = run_sync(poll_op("end_poll", poll_id))
            if not result:
                return False
        except Exception as e:
            logger.error(f"Failed to close poll {poll_id} in DB: {e}")
            return False
        return self._poll_state.end_poll(poll_id)

    def is_bot_ready(self) -> bool:
        return self._bot.is_ready()

    def get_bot_latency_ms(self) -> float:
        if self._bot.is_ready() and hasattr(self._bot, 'latency'):
            return round(self._bot.latency * 1000, 1)
        return 0

    def get_bot_avatar_url(self) -> str:
        if self._bot.is_ready() and self._bot.user and self._bot.user.avatar:
            return str(self._bot.user.avatar.url)
        return ''

    def get_bot_start_time(self) -> Optional[datetime]:
        return self._ctx.start_time

    def list_channels(self) -> List[Dict[str, str]]:
        channels = [
            {"id": str(cid), "name": name}
            for cid, name in self._ctx.available_channels.items()
        ]
        channels.sort(key=lambda c: c["name"])
        return channels

    def list_roles(self) -> List[Dict[str, str]]:
        roles = [
            {"id": str(rid), "name": name}
            for rid, name in self._ctx.available_roles.items()
        ]
        roles.sort(key=lambda r: r["name"])
        return roles

    def schedule_coroutine(self, coro):
        import asyncio
        loop = self._bot.loop
        if not loop or loop.is_closed():
            return None
        return asyncio.run_coroutine_threadsafe(coro, loop)

    def get_event_loop(self):
        return self._bot.loop

    def record_vote(
        self,
        poll_id: int,
        user_id: int,
        username: str,
        question_id: int,
        option_id: int | None,
        question_type,
    ) -> bool:
        if not self._poll_state.record_vote(poll_id, user_id):
            return False
        from db.session import get_session
        from db.poll_repository import PollRepository
        from bridge_bot.async_bridge import run_sync
        try:
            async def _add_vote():
                async with get_session() as session:
                    return await PollRepository(session).add_vote(
                        username=username,
                        user_id=user_id,
                        question_id=question_id,
                        option_id=option_id,
                        question_type=question_type,
                    )
            run_sync(_add_vote())
        except Exception as e:
            logger.error(f"Failed to persist vote to DB: {e}")
        return True


# ---------------------------------------------------------------------------
# Test double (composite)
# ---------------------------------------------------------------------------

class StubBotAdapter(BotAdapter):
    """Test double — returns canned data, no Discord connection needed."""

    def __init__(self):
        self._poll_active: Dict[int, bool] = {}
        self._send_poll_calls: List[dict] = []
        self._end_poll_calls: List[int] = []
        self._record_vote_calls: List[dict] = []
        self._user_votes: Dict[int, set] = {}
        self._channels: List[Dict[str, str]] = []
        self._roles: List[Dict[str, str]] = []

    async def send_poll(
        self,
        question: str,
        options: List[str],
        channel_id: Optional[int] = None,
        role_ids: Optional[List[int]] = None,
        max_votes_per_option: Optional[int] = None,
        description: str = '',
        poll_type: str = 'poll',
    ) -> bool:
        self._send_poll_calls.append({
            "question": question,
            "options": options,
            "channel_id": channel_id,
            "role_ids": role_ids,
            "max_votes_per_option": max_votes_per_option,
            "description": description,
            "poll_type": poll_type,
        })
        return True

    async def end_poll_and_send_results(self, poll_id: int) -> bool:
        self._end_poll_calls.append(poll_id)
        self._poll_active[poll_id] = False
        return True

    def is_poll_active(self, poll_id: int) -> bool:
        return self._poll_active.get(poll_id, False)

    def end_poll_in_state(self, poll_id: int) -> bool:
        if poll_id in self._poll_active:
            self._poll_active[poll_id] = False
            return True
        return False

    def is_bot_ready(self) -> bool:
        return True

    def get_bot_latency_ms(self) -> float:
        return 42.0

    def get_bot_avatar_url(self) -> str:
        return "https://example.com/avatar.png"

    def get_bot_start_time(self) -> Optional[datetime]:
        return datetime(2026, 7, 14, 10, 0, 0)

    def list_channels(self) -> List[Dict[str, str]]:
        return self._channels or [
            {"id": "111", "name": "general"},
            {"id": "222", "name": "polls"},
        ]

    def list_roles(self) -> List[Dict[str, str]]:
        return self._roles or [
            {"id": "333", "name": "Coach"},
            {"id": "444", "name": "Student"},
        ]

    def schedule_coroutine(self, coro):
        import asyncio
        import concurrent.futures
        loop = asyncio.new_event_loop()
        f = concurrent.futures.Future()
        try:
            result = loop.run_until_complete(coro)
            f.set_result(result)
        except Exception as e:
            f.set_exception(e)
        finally:
            loop.close()
        return f

    def get_event_loop(self):
        import asyncio
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.new_event_loop()

    def record_vote(
        self,
        poll_id: int,
        user_id: int,
        username: str,
        question_id: int,
        option_id: int | None,
        question_type,
    ) -> bool:
        voters = self._user_votes.setdefault(poll_id, set())
        if user_id in voters:
            return False
        voters.add(user_id)
        self._record_vote_calls.append({
            "poll_id": poll_id,
            "user_id": user_id,
            "username": username,
            "question_id": question_id,
            "option_id": option_id,
            "question_type": question_type,
        })
        return True
