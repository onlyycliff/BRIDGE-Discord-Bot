import logging
import time
import os
from datetime import datetime
from typing import Dict, Set, List, Optional

import discord
from db.enums import QuestionType
from discord.ext import commands
from discord.ui import View
from dotenv import load_dotenv

from db.repository import (
    add_vote as db_add_vote,
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
INDIGO = 0x6366F1

available_channels: Dict[int, str] = {}
available_roles: Dict[int, str] = {}


class PollState:
    """Centralized poll state management"""
    def __init__(self):
        self.polls: Dict[int, 'PollView'] = {}
        self.user_votes: Dict[int, Set[int]] = {}
        self.active: Dict[int, bool] = {}

    def add_poll(self, poll_id: int, poll_view: 'PollView') -> None:
        self.polls[poll_id] = poll_view
        self.user_votes[poll_id] = set()
        self.active[poll_id] = True
        logger.info(f"Poll {poll_id} registered")

    def has_voted(self, poll_id: int, user_id: int) -> bool:
        return user_id in self.user_votes.get(poll_id, set())

    def record_vote(self, poll_id: int, user_id: int) -> bool:
        if self.has_voted(poll_id, user_id):
            return False
        self.user_votes[poll_id].add(user_id)
        return True

    def end_poll(self, poll_id: int) -> bool:
        if poll_id in self.active:
            self.active[poll_id] = False
            logger.info(f"Poll {poll_id} ended")
            return True
        return False

    def is_active(self, poll_id: int) -> bool:
        return self.active.get(poll_id, False)

    def get_poll_data(self, poll_id: int) -> Optional[Dict]:
        poll = self.polls.get(poll_id)
        if not poll:
            return None
        return {
            "poll_id": poll_id,
            "question": poll.question,
            "options": poll.options,
            "votes": poll.votes,
            "total_votes": sum(poll.votes.values()),
            "voters": list(self.user_votes.get(poll_id, set()))
        }


poll_state = PollState()


class PollView(View):
    """Interactive poll with progress bars and vote tracking"""

    def __init__(self, question: str, options: List[str], max_votes_per_option: Optional[int] = None, description: str = ''):
        super().__init__(timeout=None)
        self.question = question
        self.options = options
        self.description = description
        self.poll_id = int(time.time() * 1000)
        self.max_votes_per_option = max_votes_per_option
        self.channel_id: Optional[int] = None
        self.message_id: Optional[int] = None
        self.question_id: Optional[int] = None
        self.option_map: Dict[str, int] = {}

        self.votes = {option: 0 for option in options}
        self.buttons = []

        poll_state.add_poll(self.poll_id, self)

        self.clear_items()

        button_styles = [
            discord.ButtonStyle.primary,
            discord.ButtonStyle.success,
            discord.ButtonStyle.danger,
            discord.ButtonStyle.secondary,
            discord.ButtonStyle.primary,
        ]
        for i, option in enumerate(options):
            style = button_styles[i % len(button_styles)]
            button = discord.ui.Button(
                label=option,
                style=style,
                custom_id=f"poll_{self.poll_id}_{i}"
            )
            button.callback = self.create_vote_handler(option, i)
            self.buttons.append(button)
            self.add_item(button)

    def create_vote_handler(self, option: str, index: int):
        async def vote_handler(interaction: discord.Interaction):
            await self.handle_vote(interaction, option)
        return vote_handler

    async def handle_vote(self, interaction: discord.Interaction, choice: str):
        try:
            if interaction.user.bot:
                return

            user_id = interaction.user.id
            user_name = interaction.user.display_name

            if not poll_state.is_active(self.poll_id):
                await interaction.response.send_message(
                    "This poll has ended. Voting is no longer available.",
                    ephemeral=True
                )
                return

            if self.max_votes_per_option is not None and self.votes[choice] >= self.max_votes_per_option:
                await interaction.response.send_message(
                    f"\u274c The limit of **{self.max_votes_per_option}** votes for **{choice}** has been reached.",
                    ephemeral=True
                )
                logger.warning(f"Vote limit reached - Option {choice} on poll {self.poll_id}")
                return

            if not poll_state.record_vote(self.poll_id, user_id):
                await interaction.response.send_message(
                    "\u274c You have already voted in this poll.",
                    ephemeral=True
                )
                logger.warning(f"Duplicate vote attempt - User {user_id} on poll {self.poll_id}")
                return

            self.votes[choice] += 1
            logger.info(f"Vote recorded - User: {user_name} ({user_id}), Choice: {choice}, Poll: {self.poll_id}")

            if not interaction.message.embeds:
                logger.error("No embeds found in poll message")
                return
            embed = interaction.message.embeds[0]
            self._update_embed_fields(embed)

            try:
                opt_id = self.option_map.get(choice)
                await db_add_vote(
                    username=user_name,
                    user_id=user_id,
                    question_id=self.question_id,
                    option_id=opt_id,
                    question_type=QuestionType.single_choice,
                )
            except Exception as e:
                logger.error(f"Failed to log vote to DB: {e}")

            # Send confirmation embed with standings
            confirm_embed = discord.Embed(
                title="\u2705 Vote Recorded",
                description=f"You voted for **{choice}**",
                color=INDIGO
            )
            confirm_embed.add_field(name="Question", value=self.question, inline=False)
            confirm_embed.add_field(name="Your Choice", value=choice, inline=True)
            confirm_embed.add_field(name="Total Votes", value=str(sum(self.votes.values())), inline=True)

            total_conf = sum(self.votes.values())
            bar_lines = []
            for opt in self.options:
                v = self.votes.get(opt, 0)
                pct = int((v / max(total_conf, 1)) * 100)
                filled = int((v / max(total_conf, 1)) * 10)
                bar = "\u2588\u2588" * filled + "\u2591\u2591" * (10 - filled)
                bar_lines.append(f"{bar} {v} votes ({pct}%)")
            confirm_embed.add_field(
                name="Current Standings",
                value="\n".join(bar_lines),
                inline=False
            )

            self._refresh_button_states()
            await interaction.response.send_message(embed=confirm_embed, ephemeral=True)
            await interaction.message.edit(embed=embed, view=self)

        except discord.errors.InteractionResponded:
            logger.warning("Interaction already responded for poll vote")
        except discord.errors.NotFound:
            logger.warning("Interaction not found (stale token) for poll vote")
        except Exception as e:
            logger.error(f"Error handling vote: {e}")
            try:
                await interaction.response.send_message(
                    "\u26a0\ufe0f An error occurred while processing your vote.",
                    ephemeral=True
                )
            except Exception:
                pass

    def _make_progress_bar(self, votes: int, total: int, width: int = 10) -> str:
        pct = votes / max(total, 1)
        filled = int(pct * width)
        empty = width - filled
        block = '\u2588'
        space = '\u2591'
        return f"{block * filled}{space * empty} {votes} vote{'s' if votes != 1 else ''} ({int(pct * 100)}%)"

    def _update_embed_fields(self, embed: discord.Embed) -> None:
        try:
            total = sum(self.votes.values())
            for i, option in enumerate(self.options):
                if i < len(embed.fields):
                    embed.set_field_at(
                        index=i,
                        name=option,
                        value=self._make_progress_bar(self.votes[option], total),
                        inline=False
                    )
        except Exception as e:
            logger.error(f"Error updating embed fields: {e}")

    def _refresh_button_states(self) -> None:
        if self.max_votes_per_option is None:
            return
        state_changed = False
        for i, option in enumerate(self.options):
            if i < len(self.buttons):
                is_full = self.votes.get(option, 0) >= self.max_votes_per_option
                if self.buttons[i].disabled != is_full:
                    self.buttons[i].disabled = is_full
                    state_changed = True
        if state_changed:
            logger.info(f"Button states updated for poll {self.poll_id}")


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

