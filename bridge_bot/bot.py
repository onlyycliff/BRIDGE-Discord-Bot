import pandas as pd
from datetime import datetime
import time
import discord
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize the bot with the required intents
intents = discord.Intents.default()
intents.message_content = True

user_votes = {}

bot = commands.Bot(command_prefix="!", intents=intents)

CHANNEL_ID = 1519291160240066650

# Create a view for the poll
class PollView(View):
    def __init__(self, question, option1, option2):
        super().__init__()
        self.question = question
        self.option1 = option1
        self.option2 = option2
        
        self.votes = {
            option1: 0,
            option2: 0
        }
        
        # Generate a unique poll ID
        self.poll_id = int(time.time())
        
        #Update button labels depending on the question
        self.children[0].label = option1
        self.children[1].label = option2
    
    async def handle_vote(self, interaction, choice):
        user_id = interaction.user.id
        
        user_votes.setdefault(self.poll_id, set())
        
        if user_id in user_votes[self.poll_id]:
            await interaction.response.send_message("You have already voted in this poll.", ephemeral=True)
            return

        user_votes[self.poll_id].add(user_id)
        
        self.votes[choice] += 1
        
        embed = interaction.message.embeds[0]
        
        embed.set_field_at(
            index=0,
            name=f"🔹 {self.option1}",
            value=f"{self.votes[self.option1]} votes",
            inline=True
        )
        embed.set_field_at(
            index=1,
            name=f"🔸 {self.option2}",
            value=f"{self.votes[self.option2]} votes",
            inline=True
        )
        
        await interaction.response.send_message(f"You voted for **{choice}**", ephemeral=True)
        
        
        data = {
            "Poll ID": self.poll_id,
            "User": str(interaction.user.display_name),
            "User_ID": user_id,
            "Choice": str(choice),
            "Question": self.question,
            "Time": datetime.now()
        }
        
        df = pd.DataFrame([data])
        
        try:
            existing = pd.read_excel("responses.xlsx")
            df = pd.concat([existing, df], ignore_index=True)
        except FileNotFoundError:
            pass
        
        file_path = "responses.xlsx"
        
        #Limit sheet name to 31 chars (Excel rule)
        sheet_name = f"{self.question[:31]}-{self.poll_id}"
        
        
        try:
            with pd.ExcelWriter(file_path, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
        except FileNotFoundError:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)

        print("Saved:", data)
        
# Define the buttons for the poll
    @discord.ui.button(label="temp1", style=discord.ButtonStyle.primary)
    async def option1_button(self, interaction: discord.Interaction, button: Button):
        await self.handle_vote(interaction, self.option1)

    @discord.ui.button(label="temp2", style=discord.ButtonStyle.success)
    async def option2_button(self, interaction: discord.Interaction, button: Button):
        await self.handle_vote(interaction, self.option2)

# Send a poll to the specified channel
async def send_poll(question, option1, option2):
    channel = bot.get_channel(CHANNEL_ID)
    
    if channel:
        view = PollView(question, option1, option2)
        
        embed = discord.Embed(
            title=f"📊 {question}",
            description=f"Vote by clicking a button below.",
            color = 0xFFD700
        )
        
        embed.add_field(name=f"🔹 {option1}", value="0 votes", inline=True)
        embed.add_field(name=f"🔸 {option2}", value="0 votes", inline=True)
        

        
        embed.set_footer(text="BRIDGE 2026 Feedback System")
        embed.timestamp = datetime.now()
        
        await channel.send(embed=embed, view=view)

        

RULES_CHANNEL_NAME = "📜｜rules"  # Change this if your channel is named differently
GOLD = 0xFFD700


def build_rules_embed():
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
    print(f"Bridge Bot is online as {bot.user}")

    for guild in bot.guilds:
        rules_channel = discord.utils.get(guild.text_channels, name=RULES_CHANNEL_NAME)

        if rules_channel:
            # Check if bot already posted rules
            already_posted = False
            async for message in rules_channel.history(limit=20):
                if message.author == bot.user:
                    already_posted = True
                    break

            if not already_posted:
                embed = build_rules_embed()
                msg = await rules_channel.send(embed=embed)
                await msg.pin()
                print(f"Rules posted and pinned in #{rules_channel.name}")
            else:
                print("Rules already posted, skipping.")
        else:
            print(f"Could not find channel '{RULES_CHANNEL_NAME}'")

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return
    
    message = reaction.message
    
    if message.author != bot.user:
        return
    
    if "📊" not in message.content:
        return
    
    user_id = user.id
    message_id = message.id
    
    #Creates a dictionary to store user votes
    if message_id not in user_votes:
        user_votes[message_id] = {}
        
    if user_id in user_votes[message_id]:
        print(f"User {user_id} has already voted on message {message_id}")
        return

    user_votes[message_id][user_id] = str(reaction.emoji)

    print(f"user: {str(user)},\n reaction: {str(reaction.emoji)},\n message: {message.content}")
    
def start_bot():
    bot.run(os.getenv("TOKEN"))
