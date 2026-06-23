# Bridge 2026 Discord Bot — Setup Instructions

## Files in this folder
- `bot.py` — the main bot code
- `.env` — where you put your secret token (never share this)
- `requirements.txt` — libraries the bot needs

---

## Step 1 — Install the libraries
Open your VS Code terminal and run:
```
pip install -r requirements.txt
```

---

## Step 2 — Add your bot token
1. Go to https://discord.com/developers/applications
2. Click your Bridge 2026 app
3. Go to the Bot tab
4. Click "Reset Token" and copy it
5. Open the `.env` file and replace `paste_your_bot_token_here` with your token

Example:
```
TOKEN=MTExMjM0NTY3ODkwMTIzNDU2.GabCde.xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Step 3 — Make sure your bot has the right permissions
When inviting your bot via the OAuth2 URL Generator, check:
- Send Messages
- Embed Links
- Read Message History
- Manage Messages (needed to delete old rules on restart)

---

## Step 4 — Set up your #rules channel
1. Create a text channel in Discord named exactly: `rules`
2. Go to Edit Channel → Permissions → Members role
3. Turn OFF "Send Messages" so only the bot can post

---

## Step 5 — Run the bot
In VS Code terminal:
```
python bot.py
```

You should see:
```
Bridge Bot is online as Bridge2026Bot#XXXX
Rules posted in #rules in Bridge 2026
```

Every time you restart the bot it will delete the old rules message and post a fresh one.

---

## Changing the rules channel name
If your channel is not named `rules`, open `bot.py` and change line 10:
```python
RULES_CHANNEL_NAME = "rules"  # Change this to match your channel name
```

---

## Keeping the bot running 24/7
Your bot only runs while your laptop is on. To keep it always online:
1. Go to https://railway.app
2. Create a new project → Deploy from GitHub
3. Push your bot folder to a private GitHub repo
4. Add your TOKEN as an environment variable in Railway
5. Railway runs it for free 24/7
