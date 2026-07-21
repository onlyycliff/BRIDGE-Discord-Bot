"""Embeds — Discord embed construction.

Pure functions that take data and return ``discord.Embed`` objects.
Extracted from bot.py so embed logic is independently testable.
"""

from datetime import datetime
from typing import Dict, List

import discord

INDIGO = 0x6366F1


def build_poll_embed(
    question: str,
    options: List[str],
    description: str = "",
) -> discord.Embed:
    embed_desc = description if description else "Vote by clicking a button below."
    embed = discord.Embed(
        title=f"\U0001f4ca {question}",
        description=embed_desc,
        color=INDIGO,
    )
    for option in options:
        embed.add_field(
            name=option,
            value="0 votes (0%)\n\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591\u2591",
            inline=False,
        )
    embed.set_footer(
        text="BRIDGE 2026 VII \u2022 Summer Program \u2022 \U0001f517 View on Dashboard"
    )
    embed.timestamp = datetime.now()
    return embed


def build_results_embed(
    question: str,
    choices: Dict[str, int],
    voters_by_choice: Dict[str, List[str]],
    total_votes: int,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"\U0001f4ca Poll Results \u2014 {question}",
        description="The poll has ended. Here are the final results.",
        color=INDIGO,
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
            inline=False,
        )

    embed.set_footer(text=f"Total Votes: {total_votes} \u2022 BRIDGE 2026 VII")
    embed.timestamp = datetime.now()
    return embed


def build_tour_feedback_embed(
    tour_name: str,
    form_url: str,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"\U0001f3eb {tour_name} \u2014 Feedback",
        description=(
            f"Please share your feedback about the **{tour_name}** industry tour.\n\n"
            f"\U0001f449 [**Click here to fill out the feedback form**]({form_url})"
        ),
        color=INDIGO,
    )
    embed.set_footer(
        text="BRIDGE 2026 VII \u2022 Summer Program \u2022 \U0001f517 View on Dashboard"
    )
    embed.timestamp = datetime.now()
    return embed


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
