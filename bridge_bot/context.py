"""BotContext — dataclass holding bot state.

Replaces module-level globals in bot.py. Injected into extracted modules
so they can access bot state without importing globals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class BotContext:
    """Shared state for the Discord bot subsystem."""

    bot: object = None  # discord.ext.commands.Bot — avoid import at module level
    channel_id: Optional[int] = None
    start_time: Optional[datetime] = None
    available_channels: Dict[int, str] = field(default_factory=dict)
    available_roles: Dict[int, str] = field(default_factory=dict)
    rules_channel_name: str = "\U0001f4dc\uff5crules"
