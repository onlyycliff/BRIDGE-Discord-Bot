"""ChannelCache — manages Discord channel and role lookups.

Extracted from bot.py so channel/role caching is independently testable.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ChannelCache:
    """In-memory cache of Discord channels and roles."""

    def __init__(self) -> None:
        self.channels: Dict[int, str] = {}
        self.roles: Dict[int, str] = {}

    def refresh(self, guilds) -> None:
        """Rebuild the cache from the bot's guild list."""
        self.channels.clear()
        self.roles.clear()
        for guild in guilds:
            for ch in guild.text_channels:
                self.channels[ch.id] = ch.name
            for r in guild.roles:
                if not r.is_default():
                    self.roles[r.id] = r.name
        logger.info(
            f"Cached {len(self.channels)} channels and {len(self.roles)} roles"
        )

    def get_channel_name(self, channel_id: int) -> str:
        return self.channels.get(channel_id, "Unknown")

    def get_role_name(self, role_id: int) -> str:
        return self.roles.get(role_id, "Unknown")

    def is_valid_role(self, role_id: int) -> bool:
        return role_id in self.roles
