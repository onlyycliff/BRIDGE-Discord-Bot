import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

from bridge_bot.poll_state import poll_state
from bridge_bot.poll_view import PollView, INDIGO
from db.repository import (
    add_poll_metadata,
    end_poll,
    get_poll_metadata,
    get_poll_stats,
)

logger = logging.getLogger(__name__)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=os.getenv("BOT_PREFIX", "!"), intents=intents, help_command=None)

start_time = None

CHANNEL_ID: Optional[int] = None
RULES_CHANNEL_NAME = os.getenv("RULES_CHANNEL_NAME", "\U0001f4dc\uff5crules")

available_channels: Dict[int, str] = {}
available_roles: Dict[int, str] = {}


async def send_poll(
    question: str,
    options: List[str],
    channel_id: Optional[int] = None,
    role_ids: Optional[List[int]] = None,
    max_votes_per_option: Optional[int] = None,
    description: str = '',
    poll_type: str = "poll",
) -> bool:
    try:
        target_channel_id = channel_id or CHANNEL_ID
        if target_channel_id is None:
            logger.error("POLL_CHANNEL_ID not configured and no channel_id provided")
            return False

        if not question or not options or len(options) < 2:
            logger.error(f"Invalid poll parameters - Question: {question}, Options: {options}")
            return False

        if len(options) > 5:
            logger.warning(f"Poll has {len(options)} options, limiting to 5")
            options = options[:5]

        channel = bot.get_channel(target_channel_id)
        if not channel:
            try:
                channel = await bot.fetch_channel(target_channel_id)
            except Exception:
                logger.error(f"Poll channel not found (via fetch): {target_channel_id}")
                return False

        if role_ids:
            valid_roles = [rid for rid in role_ids if int(rid) in available_roles]
            if valid_roles:
                mention_str = " ".join(f"<@&{rid}>" for rid in valid_roles)
                await channel.send(mention_str)

        view = PollView(question, options, max_votes_per_option, description)

        embed_desc = description if description else "Vote by clicking a button below."
        embed = discord.Embed(
            title=f"\U0001f4ca {question}",
            description=embed_desc,
            color=INDIGO
        )

        for option in options:
            embed.add_field(
                name=option,
                value="0 votes (0%)\n\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591",
                inline=False
            )

        embed.set_footer(text="BRIDGE 2026 VII \u2022 Summer Program \u2022 \U0001f517 View on Dashboard")
        embed.timestamp = datetime.now()

        msg = await channel.send(embed=embed, view=view)
        view.channel_id = channel.id
        view.message_id = msg.id

        try:
            guild_id = channel.guild.id if channel.guild else 0
            result = await add_poll_metadata(
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

        logger.info(f"Poll created - Question: {question}, Options: {len(options)}, Poll ID: {view.poll_id}, Message ID: {msg.id}")
        return True

    except discord.Forbidden:
        logger.error(f"Permission denied sending poll to channel {target_channel_id}")
        return False
    except discord.HTTPException as e:
        logger.error(f"Discord HTTP error sending poll: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Error sending poll: {e}", exc_info=True)
        return False


async def end_poll_and_send_results(poll_id: int) -> bool:
    try:
        poll_state.end_poll(poll_id)
        await end_poll(poll_id)

        stats = await get_poll_stats(poll_id)
        if not stats:
            logger.warning(f"No stats found for poll {poll_id}, sending basic end message")
            return False

        meta = await get_poll_metadata(poll_id)
        channel_id = meta.get('channel_id') if meta else None

        if not channel_id:
            logger.warning(f"No channel_id found for poll {poll_id}, cannot send results")
            return False

        channel = bot.get_channel(channel_id)
        if not channel:
            try:
                channel = await bot.fetch_channel(channel_id)
            except Exception:
                logger.error(f"Channel {channel_id} not found for poll results")
                return False

        question = stats.get('question', 'Unknown Question')
        choices = stats.get('choices', {})
        voters_by_choice = stats.get('voters_by_choice', {})
        total_votes = stats.get('total_votes', 0)

        embed = discord.Embed(
            title=f"\U0001f4ca Poll Results \u2014 {question}",
            description="The poll has ended. Here are the final results.",
            color=INDIGO
        )

        sorted_choices = sorted(choices.items(), key=lambda x: x[1], reverse=True)

        for choice, count in sorted_choices:
            voters = voters_by_choice.get(choice, [])
            voter_text = ", ".join(voters) if voters else "*(no voters)*"
            pct = int((count / max(total_votes, 1)) * 100)
            bar_count = int((count / max(total_votes, 1)) * 10)
            bar = "\u2588\u2588" * bar_count + "\u2591\u2591" * (10 - bar_count)
            embed.add_field(
                name=f"{choice} \u2014 {count} votes ({pct}%)",
                value=f"{bar}\n{voter_text}",
                inline=False
            )

        embed.set_footer(text=f"Total Votes: {total_votes} \u2022 BRIDGE 2026 VII")
        embed.timestamp = datetime.now()

        await channel.send(embed=embed)
        logger.info(f"Poll results sent to channel {channel_id} for poll {poll_id}")
        return True

    except Exception as e:
        logger.error(f"Error sending poll results for {poll_id}: {e}", exc_info=True)
        return False


def build_rules_embed() -> discord.Embed:
    embed = discord.Embed(
        title="\u2726 Bridge 2026 Community Guidelines \u2726",
        description=(
            '*"Success. Hardwork. Inspire. Navigate. Empower." \u2014 SHINE \U0001f31f*\n\n'
            "Welcome to the Bridge 2026 Discord! This is your space to grow, connect, and thrive. "
            "Please read and follow these guidelines to keep our community strong."
        ),
        color=INDIGO,
    )

    embed.add_field(
        name="1. Respect & Kindness",
        value=(
            "1.1 Treat every member with kindness, empathy, and respect. We grow together.\n"
            "1.2 Use inclusive and welcoming language. Hate speech, slurs, or discriminatory language will not be tolerated.\n"
            "1.3 Disagreements are okay \u2014 personal attacks are not. Critique ideas, never people."
        ),
        inline=False,
    )

    embed.add_field(
        name="2. Communication",
        value=(
            "2.1 Keep conversations appropriate and constructive. No harassment or hostile behavior.\n"
            "2.2 Be mindful of others' boundaries. If someone sets one, respect it.\n"
            "2.3 Post in the correct channels. Off-topic messages slow things down for everyone."
        ),
        inline=False,
    )

    embed.add_field(
        name="3. Academic Excellence",
        value=(
            "3.1 Support your fellow Bridge members academically. Share resources and encourage each other.\n"
            "3.2 Academic dishonesty \u2014 including sharing exam answers or doing someone else's work \u2014 is strictly prohibited."
        ),
        inline=False,
    )

    embed.add_field(
        name="4. Professional Conduct",
        value=(
            "4.1 Represent Bridge 2026 with professionalism in all spaces \u2014 online and in person.\n"
            "4.2 Networking opportunities and event info shared here are for Bridge members only. Do not share outside the server without permission."
        ),
        inline=False,
    )

    embed.add_field(
        name="5. Content & Posting",
        value=(
            "5.1 No NSFW, explicit, or inappropriate content of any kind.\n"
            "5.2 No spam, excessive tagging, or irrelevant links.\n"
            "5.3 Do not @everyone or @here unless you are an admin."
        ),
        inline=False,
    )

    embed.add_field(
        name="6. Feedback & Forms",
        value=(
            "6.1 Official feedback forms will be posted by admins in #feedback-forum. Fill them out honestly \u2014 your voice shapes this program.\n"
            "6.2 All feedback should be constructive and respectful."
        ),
        inline=False,
    )

    embed.add_field(
        name="7. Self-Care & Community",
        value=(
            "7.1 Check in on each other. If a fellow Bridge member seems to be struggling, be a resource, not a bystander.\n"
            "7.2 This is a judgment-free space. We all come from different backgrounds \u2014 lead with curiosity, not assumptions."
        ),
        inline=False,
    )

    embed.add_field(
        name="8. Consequences",
        value=(
            "8.1 Minor violations will result in a warning from an admin.\n"
            "8.2 Repeated or serious violations may result in removal from the server.\n"
            "8.3 Admins have final say in all moderation decisions."
        ),
        inline=False,
    )

    embed.set_footer(text="BRIDGE 2026 VII \u2022 Summer Program \u2022 \U0001f309")
    return embed


@bot.event
async def on_ready():
    global start_time
    start_time = datetime.now()
    logger.info(f"Bridge Bot online as {bot.user}")

    available_channels.clear()
    available_roles.clear()
    for guild in bot.guilds:
        for ch in guild.text_channels:
            available_channels[ch.id] = ch.name
        for r in guild.roles:
            if not r.is_default():
                available_roles[r.id] = r.name
    logger.info(f"Cached {len(available_channels)} channels and {len(available_roles)} roles")

    try:
        from db.repository import get_active_poll_ids, is_poll_active_in_db, has_user_voted_in_db
        poll_state.set_db_checkers(
            is_active_fn=is_poll_active_in_db,
            has_voted_fn=has_user_voted_in_db,
        )
        active_ids = await get_active_poll_ids()
        poll_state.rehydrate(active_ids)
        logger.info(f"Rehydrated {len(active_ids)} active polls from DB")
    except Exception as e:
        logger.error(f"Failed to rehydrate poll state from DB: {e}")

    try:
        for guild in bot.guilds:
            rules_channel = discord.utils.get(guild.text_channels, name=RULES_CHANNEL_NAME)

            if not rules_channel:
                logger.warning(f"Rules channel '{RULES_CHANNEL_NAME}' not found in {guild.name}")
                continue

            rules_posted = False
            try:
                async for message in rules_channel.history(limit=20):
                    if message.author == bot.user and "Bridge 2026 Community Guidelines" in message.embeds[0].title if message.embeds else False:
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
                    logger.info(f"Rules posted and pinned in #{rules_channel.name}")
                except Exception as e:
                    logger.error(f"Failed to post rules: {e}")
            else:
                logger.info(f"Rules already posted in #{rules_channel.name}")

    except Exception as e:
        logger.error(f"Error in on_ready event: {e}")


def start_bot() -> None:
    global CHANNEL_ID

    token = os.getenv("TOKEN")
    if not token:
        logger.error("Discord bot token not found in environment variables")
        raise ValueError("Missing TOKEN environment variable")

    channel_id_str = os.getenv("POLL_CHANNEL_ID")
    if not channel_id_str:
        logger.error("POLL_CHANNEL_ID not set in environment variables")
        raise ValueError("Missing POLL_CHANNEL_ID environment variable")

    CHANNEL_ID = int(channel_id_str)
    logger.info("Starting Bridge Bot...")
    bot.run(token)


if __name__ == "__main__":
    start_bot()
