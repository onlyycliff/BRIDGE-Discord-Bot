import logging
import time
import discord
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
import os
from datetime import datetime
from typing import Dict, Set, List, Optional
from .excel_manager import excel_manager

# Setup logging for better debugging and monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize the bot with required intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration - pull from environment or use defaults
CHANNEL_ID = int(os.getenv("POLL_CHANNEL_ID", "1519291160240066650"))
RULES_CHANNEL_NAME = os.getenv("RULES_CHANNEL_NAME", "📜｜rules")
GOLD = 0xFFD700

# Track poll state - prevents duplicate votes and enables vote retrieval
class PollState:
    """Centralized poll state management"""
    def __init__(self):
        self.polls: Dict[int, 'PollView'] = {}
        self.user_votes: Dict[int, Set[int]] = {}
    
    def add_poll(self, poll_id: int, poll_view: 'PollView') -> None:
        """Register a new poll"""
        self.polls[poll_id] = poll_view
        self.user_votes[poll_id] = set()
        logger.info(f"Poll {poll_id} registered")
    
    def has_voted(self, poll_id: int, user_id: int) -> bool:
        """Check if user already voted"""
        return user_id in self.user_votes.get(poll_id, set())
    
    def record_vote(self, poll_id: int, user_id: int) -> bool:
        """Record a vote, return True if vote was recorded"""
        if self.has_voted(poll_id, user_id):
            return False
        self.user_votes[poll_id].add(user_id)
        return True
    
    def get_poll_data(self, poll_id: int) -> Optional[Dict]:
        """Get current poll data including votes"""
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
    """Interactive poll with multiple options and vote tracking"""
    
    def __init__(self, question: str, options: List[str]):
        super().__init__()
        self.question = question
        self.options = options
        self.poll_id = int(time.time() * 1000)  # More unique timestamp
        
        # Initialize vote tracking
        self.votes = {option: 0 for option in options}
        
        # Register poll in global state
        poll_state.add_poll(self.poll_id, self)
        
        # Clear existing buttons and create new ones
        self.clear_items()
        
        # Create a button for each option
        for i, option in enumerate(options):
            button = discord.ui.Button(
                label=option,
                style=discord.ButtonStyle.primary if i % 2 == 0 else discord.ButtonStyle.secondary,
                custom_id=f"poll_{self.poll_id}_{i}"
            )
            button.callback = self.create_vote_handler(option, i)
            self.add_item(button)
    
    def create_vote_handler(self, option: str, index: int):
        """Factory function to create vote handler for each button"""
        async def vote_handler(interaction: discord.Interaction):
            await self.handle_vote(interaction, option, index)
        return vote_handler
    
    async def handle_vote(self, interaction: discord.Interaction, choice: str, option_index: int):
        """Process a vote and update the poll"""
        try:
            user_id = interaction.user.id
            user_name = interaction.user.display_name
            
            # Check if user already voted
            if not poll_state.record_vote(self.poll_id, user_id):
                await interaction.response.send_message(
                    "❌ You have already voted in this poll.",
                    ephemeral=True
                )
                logger.warning(f"Duplicate vote attempt - User {user_id} on poll {self.poll_id}")
                return
            
            # Record the vote
            self.votes[choice] += 1
            logger.info(f"Vote recorded - User: {user_name} ({user_id}), Choice: {choice}, Poll: {self.poll_id}")
            
            # Update the embed with new vote counts
            embed = interaction.message.embeds[0]
            self._update_embed_fields(embed)
            
            # Log vote to Excel
            try:
                excel_manager.add_vote(
                    username=user_name,
                    user_id=user_id,
                    question=self.question,
                    choice=choice,
                    poll_id=self.poll_id
                )
            except Exception as e:
                logger.error(f"Failed to log vote to Excel: {e}")
            
            # Send confirmation and update message
            await interaction.response.send_message(
                f"✅ You voted for **{choice}**",
                ephemeral=True
            )
            await interaction.message.edit(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Error handling vote: {e}")
            try:
                await interaction.response.send_message(
                    "⚠️ An error occurred while processing your vote.",
                    ephemeral=True
                )
            except Exception as inner_e:
                logger.error(f"Failed to send error message: {inner_e}")
    
    def _update_embed_fields(self, embed: discord.Embed) -> None:
        """Update embed fields with current vote counts"""
        try:
            for i, option in enumerate(self.options):
                if i < len(embed.fields):
                    embed.set_field_at(
                        index=i,
                        name=f"{'🔹' if i % 2 == 0 else '🔸'} {option}",
                        value=f"{self.votes[option]} votes",
                        inline=True
                    )
        except Exception as e:
            logger.error(f"Error updating embed fields: {e}")

async def send_poll(question: str, options: List[str]) -> bool:
    """
    Send a poll to the configured channel
    
    Args:
        question: The poll question
        options: List of poll options (minimum 2)
    
    Returns:
        True if poll sent successfully, False otherwise
    """
    try:
        # Validate inputs
        if not question or not options or len(options) < 2:
            logger.error(f"Invalid poll parameters - Question: {question}, Options: {options}")
            return False
        
        # Limit options to 5 for Discord button limits
        if len(options) > 5:
            logger.warning(f"Poll has {len(options)} options, limiting to 5")
            options = options[:5]
        
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            logger.error(f"Poll channel not found: {CHANNEL_ID}")
            return False
        
        # Create poll view with dynamic options
        view = PollView(question, options)
        
        # Build embed with all options
        embed = discord.Embed(
            title=f"📊 {question}",
            description="Vote by clicking a button below.",
            color=GOLD
        )
        
        for i, option in enumerate(options):
            embed.add_field(
                name=f"{'🔹' if i % 2 == 0 else '🔸'} {option}",
                value="0 votes",
                inline=True
            )
        
        embed.set_footer(text="BRIDGE 2026 Feedback System")
        embed.timestamp = datetime.now()
        
        await channel.send(embed=embed, view=view)
        logger.info(f"Poll created - Question: {question}, Options: {len(options)}, Poll ID: {view.poll_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending poll: {e}")
        return False

def build_rules_embed() -> discord.Embed:
    """Create the community rules embed"""
    embed = discord.Embed(
        title="✦ Bridge 2026 Community Guidelines ✦",
        description=(
            '*"Success. Hardwork. Inspire. Navigate. Empower." — SHINE 🌟*\n\n'
            "Welcome to the Bridge 2026 Discord! This is your space to grow, connect, and thrive. "
            "Please read and follow these guidelines to keep our community strong."
        ),
        color=GOLD,
    )

    embed.add_field(
        name="1. Respect & Kindness",
        value=(
            "1.1 Treat every member with kindness, empathy, and respect. We grow together.\n"
            "1.2 Use inclusive and welcoming language. Hate speech, slurs, or discriminatory language will not be tolerated.\n"
            "1.3 Disagreements are okay — personal attacks are not. Critique ideas, never people."
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
            "3.2 Academic dishonesty — including sharing exam answers or doing someone else's work — is strictly prohibited."
        ),
        inline=False,
    )

    embed.add_field(
        name="4. Professional Conduct",
        value=(
            "4.1 Represent Bridge 2026 with professionalism in all spaces — online and in person.\n"
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
            "6.1 Official feedback forms will be posted by admins in #feedback-forum. Fill them out honestly — your voice shapes this program.\n"
            "6.2 All feedback should be constructive and respectful."
        ),
        inline=False,
    )

    embed.add_field(
        name="7. Self-Care & Community",
        value=(
            "7.1 Check in on each other. If a fellow Bridge member seems to be struggling, be a resource, not a bystander.\n"
            "7.2 This is a judgment-free space. We all come from different backgrounds — lead with curiosity, not assumptions."
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

    embed.set_footer(text="Bridge 2026 — Let's make it count. 🌟")
    return embed


@bot.event
async def on_ready():
    """Initialize bot and post rules on startup"""
    logger.info(f"Bridge Bot online as {bot.user}")
    
    try:
        for guild in bot.guilds:
            rules_channel = discord.utils.get(guild.text_channels, name=RULES_CHANNEL_NAME)
            
            if not rules_channel:
                logger.warning(f"Rules channel '{RULES_CHANNEL_NAME}' not found in {guild.name}")
                continue
            
            # Check if rules already posted to avoid duplicates
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
                    logger.info(f"✅ Rules posted and pinned in #{rules_channel.name}")
                except Exception as e:
                    logger.error(f"Failed to post rules: {e}")
            else:
                logger.info(f"Rules already posted in #{rules_channel.name}")
                
    except Exception as e:
        logger.error(f"Error in on_ready event: {e}")


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    """Legacy reaction-based voting (kept for backward compatibility)"""
    try:
        # Ignore bot reactions
        if user == bot.user:
            return
        
        message = reaction.message
        
        # Only process bot messages with poll emoji
        if message.author != bot.user or "📊" not in message.content:
            return
        
        user_id = user.id
        message_id = message.id
        
        logger.debug(f"Reaction detected - User: {user.display_name}, Emoji: {reaction.emoji}, Message: {message_id}")
        
    except Exception as e:
        logger.error(f"Error handling reaction: {e}")


def start_bot() -> None:
    """Start the Discord bot"""
    token = os.getenv("TOKEN")
    if not token:
        logger.error("Discord bot token not found in environment variables")
        raise ValueError("Missing TOKEN environment variable")
    
    logger.info("Starting Bridge Bot...")
    bot.run(token)
