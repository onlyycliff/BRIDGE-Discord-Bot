"""PollOrchestrator — poll lifecycle management.

Extracted from bot.py. Owns ``send_poll`` and ``end_poll_and_send_results``.
Receives a ``BotContext`` instead of accessing module-level globals.
"""

import logging
from typing import List, Optional

import discord

from bridge_bot.context import BotContext
from bridge_bot.embeds import build_poll_embed, build_results_embed
from bridge_bot.poll_view import PollView
from db.operations import poll_op as _poll_op

logger = logging.getLogger(__name__)


async def send_poll(
    ctx: BotContext,
    question: str,
    options: List[str],
    channel_id: Optional[int] = None,
    role_ids: Optional[List[int]] = None,
    max_votes_per_option: Optional[int] = None,
    description: str = "",
    poll_type: str = "poll",
) -> bool:
    try:
        target_channel_id = channel_id or ctx.channel_id
        if target_channel_id is None:
            logger.error(
                "POLL_CHANNEL_ID not configured and no channel_id provided"
            )
            return False

        if not question or not options or len(options) < 2:
            logger.error(
                f"Invalid poll parameters - Question: {question}, Options: {options}"
            )
            return False

        if len(options) > 5:
            logger.warning(f"Poll has {len(options)} options, limiting to 5")
            options = options[:5]

        channel = await ctx.channel_cache.resolve(target_channel_id)
        if not channel:
            logger.error(
                f"Poll channel not found: {target_channel_id}"
            )
            return False

        if role_ids:
            valid_roles = [
                rid for rid in role_ids if int(rid) in ctx.available_roles
            ]
            if valid_roles:
                mention_str = " ".join(f"<@&{rid}>" for rid in valid_roles)
                await channel.send(mention_str)

        view = PollView(question, options, max_votes_per_option, description)
        embed = build_poll_embed(question, options, description)

        msg = await channel.send(embed=embed, view=view)
        view.channel_id = channel.id
        view.message_id = msg.id

        try:
            guild_id = channel.guild.id if channel.guild else 0
            result = await _poll_op(
                "add_poll_metadata",
                poll_id=view.poll_id,
                question=question,
                options=list(options),
                channel_id=channel.id,
                message_id=msg.id,
                guild_id=guild_id,
                description=description,
                poll_type=poll_type,
            )
            if result:
                view.question_id = result["question_id"]
                view.option_map = result["option_map"]
        except Exception as e:
            logger.error(f"Failed to save poll metadata to DB: {e}")

        logger.info(
            f"Poll created - Question: {question}, Options: {len(options)}, "
            f"Poll ID: {view.poll_id}, Message ID: {msg.id}"
        )
        return True

    except discord.Forbidden:
        logger.error(
            f"Permission denied sending poll to channel {target_channel_id}"
        )
        return False
    except discord.HTTPException as e:
        logger.error(f"Discord HTTP error sending poll: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Error sending poll: {e}", exc_info=True)
        return False


async def end_poll_and_send_results(ctx: BotContext, poll_id: int) -> bool:
    from bridge_bot.poll_state import poll_state

    try:
        await _poll_op("end_poll", poll_id)
        poll_state.end_poll(poll_id)

        stats = await _poll_op("get_poll_stats", poll_id)
        if not stats:
            logger.warning(
                f"No stats found for poll {poll_id}, sending basic end message"
            )
            return False

        meta = await _poll_op("get_poll_metadata", poll_id)
        channel_id = meta.get("channel_id") if meta else None

        if not channel_id:
            logger.warning(
                f"No channel_id found for poll {poll_id}, cannot send results"
            )
            return False

        channel = await ctx.channel_cache.resolve(channel_id)
        if not channel:
            logger.error(
                f"Channel {channel_id} not found for poll results"
            )
            return False

        embed = build_results_embed(
            question=stats.get("question", "Unknown Question"),
            choices=stats.get("choices", {}),
            voters_by_choice=stats.get("voters_by_choice", {}),
            total_votes=stats.get("total_votes", 0),
        )

        await channel.send(embed=embed)
        logger.info(
            f"Poll results sent to channel {channel_id} for poll {poll_id}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Error sending poll results for {poll_id}: {e}", exc_info=True
        )
        return False
