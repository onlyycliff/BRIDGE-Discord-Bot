"""Discord bot — event handlers and entry point.

Module-level globals are replaced by ``BotContext`` and ``ChannelCache``.
Poll orchestration lives in ``poll_orchestrator.py``; embeds in ``embeds.py``.
"""

import logging
import os
from datetime import datetime

import discord
from discord.ext import commands
from dotenv import load_dotenv

from bridge_bot.channel_cache import ChannelCache
from bridge_bot.context import BotContext
from bridge_bot.embeds import build_rules_embed

logger = logging.getLogger(__name__)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=os.getenv("BOT_PREFIX", "!"),
    intents=intents,
    help_command=None,
)

ctx = BotContext()
channel_cache = ChannelCache()
ctx.channel_cache = channel_cache

RULES_CHANNEL_NAME = os.getenv(
    "RULES_CHANNEL_NAME", "\U0001f4dc\uff5crules"
)
ctx.rules_channel_name = RULES_CHANNEL_NAME


@bot.event
async def on_ready():
    ctx.bot = bot
    ctx.start_time = datetime.now()
    logger.info(f"Bridge Bot online as {bot.user}")

    channel_cache.set_bot(bot)
    channel_cache.refresh(bot.guilds)
    ctx.available_channels = channel_cache.channels
    ctx.available_roles = channel_cache.roles

    try:
        from db.session import get_session
        from db.poll_repository import PollRepository
        from bridge_bot.poll_state import poll_state

        async def _get_active_poll_ids():
            async with get_session() as session:
                return await PollRepository(session).get_active_poll_ids()

        async def _is_active(poll_id):
            async with get_session() as session:
                return await PollRepository(session).is_poll_active_in_db(poll_id)

        async def _has_voted(poll_id, user_id):
            async with get_session() as session:
                return await PollRepository(session).has_user_voted_in_db(poll_id, user_id)

        poll_state.set_db_checkers(
            is_active_fn=_is_active,
            has_voted_fn=_has_voted,
        )
        active_ids = await _get_active_poll_ids()
        poll_state.rehydrate(active_ids)
        logger.info(f"Rehydrated {len(active_ids)} active polls from DB")
    except Exception as e:
        logger.error(f"Failed to rehydrate poll state from DB: {e}")

    try:
        for guild in bot.guilds:
            rules_channel = discord.utils.get(
                guild.text_channels, name=RULES_CHANNEL_NAME
            )

            if not rules_channel:
                logger.warning(
                    f"Rules channel '{RULES_CHANNEL_NAME}' not found in {guild.name}"
                )
                continue

            rules_posted = False
            try:
                async for message in rules_channel.history(limit=20):
                    if (
                        message.author == bot.user
                        and "Bridge 2026 Community Guidelines"
                        in message.embeds[0].title
                        if message.embeds
                        else False
                    ):
                        rules_posted = True
                        break
            except Exception as e:
                logger.error(f"Error checking message history: {e}")
                continue

            if not rules_posted:
                try:
                    embed = build_rules_embed()
                    msg = await rules_channel.send(embed=embed)
                    await msg.pin()
                    logger.info(
                        f"Rules posted and pinned in #{rules_channel.name}"
                    )
                except Exception as e:
                    logger.error(f"Failed to post rules: {e}")
            else:
                logger.info(f"Rules already posted in #{rules_channel.name}")

    except Exception as e:
        logger.error(f"Error in on_ready event: {e}")


def start_bot() -> None:
    token = os.getenv("TOKEN")
    if not token:
        logger.error("Discord bot token not found in environment variables")
        raise ValueError("Missing TOKEN environment variable")

    channel_id_str = os.getenv("POLL_CHANNEL_ID")
    if not channel_id_str:
        logger.error("POLL_CHANNEL_ID not set in environment variables")
        raise ValueError("Missing POLL_CHANNEL_ID environment variable")

    ctx.channel_id = int(channel_id_str)
    logger.info("Starting Bridge Bot...")
    bot.run(token)


# Re-export for adapter.py (which accesses these via lazy import)
# These will be removed when adapter.py is updated to use BotContext
def __getattr__(name):
    if name == "start_time":
        return ctx.start_time
    if name == "available_channels":
        return channel_cache.channels
    if name == "available_roles":
        return channel_cache.roles
    if name == "CHANNEL_ID":
        return ctx.channel_id
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    start_bot()
