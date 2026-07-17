"""ChannelCache — single module for channel and role resolution.

Owns the in-memory cache of Discord channels and roles, and provides
the ``resolve()`` method used by poll_orchestrator to find channels
for sending messages. Falls back to ``bot.fetch_channel()`` when the
cache misses.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ChannelCache:
    """In-memory cache of Discord channels and roles.

    The interface is the test surface: ``resolve()`` checks the cache
    first, then falls back to the Discord API. Deleting this module
    would force every consumer to inline bot.get_channel() / bot.fetch_channel(),
    concentrating resolution logic in the wrong place.
    """

    def __init__(self) -> None:
        self.channels: Dict[int, str] = {}
        self.roles: Dict[int, str] = {}
        self._bot = None

    def set_bot(self, bot) -> None:
        """Inject the Discord bot for API fallback in resolve()."""
        self._bot = bot

    async def refresh(self, guilds) -> None:
        """Rebuild the cache from the bot's guild list.

        Calls ``guild.fetch_channels()`` to force a full channel list
        from the Discord API before caching, avoiding lazy-load gaps.
        """
        self.channels.clear()
        self.roles.clear()
        for guild in guilds:
            await guild.fetch_channels()
            for ch in guild.text_channels:
                self.channels[ch.id] = ch.name
            for r in guild.roles:
                if not r.is_default():
                    self.roles[r.id] = r.name
        logger.info(
            f"Cached {len(self.channels)} channels and {len(self.roles)} roles"
        )

    async def resolve(self, channel_id: int):
        """Resolve a channel by ID: cache first, then Discord API fallback.

        Returns the Discord Channel object, or None if not found.
        """
        if self._bot is None:
            logger.error("ChannelCache.resolve called without bot — call set_bot() first")
            return None

        channel = self._bot.get_channel(channel_id)
        if channel:
            return channel

        try:
            channel = await self._bot.fetch_channel(channel_id)
            return channel
        except Exception:
            logger.error(f"Channel {channel_id} not found via cache or API fetch")
            return None

    def get_channel_name(self, channel_id: int) -> str:
        return self.channels.get(channel_id, "Unknown")

    def get_role_name(self, role_id: int) -> str:
        return self.roles.get(role_id, "Unknown")

    def is_valid_role(self, role_id: int) -> bool:
        return role_id in self.roles
