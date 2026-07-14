"""BotAdapter — the seam between the API layer and the Discord bot.

One interface, two adapters: RealBotAdapter (production) and StubBotAdapter (tests).
The API layer depends only on this module. Deleting it would force api.py to
inline all bot access — concentrating complexity in the wrong place.
"""

from __future__ import annotations

import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


class BotAdapter(ABC):
    """Interface that api.py depends on. Each method is a deliberate seam."""

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

    @abstractmethod
    def list_channels(self) -> List[Dict[str, str]]:
        ...

    @abstractmethod
    def list_roles(self) -> List[Dict[str, str]]:
        ...

    @abstractmethod
    def schedule_coroutine(self, coro) -> object:
        """Schedule an async coroutine on the bot's event loop from a sync context."""
        ...

    @abstractmethod
    def get_event_loop(self):
        """Return the bot's event loop, or None."""
        ...


class RealBotAdapter(BotAdapter):
    """Production adapter — delegates to bridge_bot.bot internals."""

    def __init__(self):
        import bridge_bot.bot as _bot_mod
        self._bot = _bot_mod.bot
        self._poll_state = _bot_mod.poll_state
        self._send_poll = _bot_mod.send_poll
        self._end_poll_and_send_results = _bot_mod.end_poll_and_send_results
        self._channels = _bot_mod.available_channels
        self._roles = _bot_mod.available_roles
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
            question, options,
            channel_id=channel_id, role_ids=role_ids,
            max_votes_per_option=max_votes_per_option,
            description=description, poll_type=poll_type,
        )

    async def end_poll_and_send_results(self, poll_id: int) -> bool:
        return await self._end_poll_and_send_results(poll_id)

    def is_poll_active(self, poll_id: int) -> bool:
        return self._poll_state.is_active(poll_id)

    def end_poll_in_state(self, poll_id: int) -> bool:
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
        return self._bot_mod.start_time

    def list_channels(self) -> List[Dict[str, str]]:
        channels = [
            {"id": str(cid), "name": name}
            for cid, name in self._channels.items()
        ]
        if not channels and self._bot.is_ready():
            for guild in self._bot.guilds:
                for ch in guild.text_channels:
                    channels.append({"id": str(ch.id), "name": ch.name})
        channels.sort(key=lambda c: c["name"])
        return channels

    def list_roles(self) -> List[Dict[str, str]]:
        roles = [
            {"id": str(rid), "name": name}
            for rid, name in self._roles.items()
        ]
        if not roles and self._bot.is_ready():
            for guild in self._bot.guilds:
                for r in guild.roles:
                    if not r.is_default():
                        roles.append({"id": str(r.id), "name": r.name})
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


class StubBotAdapter(BotAdapter):
    """Test double — returns canned data, no Discord connection needed."""

    def __init__(self):
        self._poll_active: Dict[int, bool] = {}
        self._send_poll_calls: List[dict] = []
        self._end_poll_calls: List[int] = []
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
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def get_event_loop(self):
        return None
