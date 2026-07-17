import logging
import time
from typing import TYPE_CHECKING, Dict, List, Optional

import discord
from discord.ui import View

from bridge_bot.poll_state import poll_state
from db.enums import QuestionType

if TYPE_CHECKING:
    from bridge_bot.adapter import BotAdapter

logger = logging.getLogger(__name__)

INDIGO = 0x6366F1

_adapter: Optional["BotAdapter"] = None


def set_adapter(adapter: "BotAdapter") -> None:
    global _adapter
    _adapter = adapter


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

            if poll_state.has_voted(self.poll_id, user_id):
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
                if _adapter is not None:
                    opt_id = self.option_map.get(choice)
                    _adapter.record_vote(
                        poll_id=self.poll_id,
                        user_id=user_id,
                        username=user_name,
                        question_id=self.question_id,
                        option_id=opt_id,
                        question_type=QuestionType.single_choice,
                    )
            except Exception as e:
                logger.error(f"Failed to log vote to DB: {e}")

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
