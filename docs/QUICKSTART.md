# Quick Start Guide - Bridge 2026 Bot

## ⚡ 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create `.env` File
```bash
TOKEN=your_discord_bot_token_here
POLL_CHANNEL_ID=your_channel_id
RULES_CHANNEL_NAME="📜｜rules"
```

### 3. Run the Bot
```bash
python dashboard.py
```

Dashboard opens at: `http://localhost:5000`

## 🎯 Creating Polls

### Via Web Dashboard
1. Go to http://localhost:5000/create-poll
2. Enter question
3. Add 2-5 options
4. Click "Create Poll"
5. Poll appears in Discord!

### Poll Features
✅ 2-5 options supported  
✅ Prevents duplicate votes  
✅ Real-time vote counting  
✅ Tracks who voted what  
✅ Persists to Excel  

## 📊 Viewing Results

### Dashboard
- **Poll Results**: Visual breakdown by choice
- **Vote Log**: All votes with timestamps
- **Export**: Download as CSV

### Google Sheets (Optional)
1. Set `GOOGLE_SHEETS_ID` in .env
2. Run sheet sync
3. View live data in Sheets

## 🔑 API Endpoints

Quick test:
```bash
# Check health
curl http://localhost:5000/api/health

# Get all votes
curl http://localhost:5000/api/votes/all

# Get summary
curl http://localhost:5000/api/summary
```

## 📈 Features

| Feature | Status |
|---------|--------|
| Multi-option polls | ✅ Live |
| Vote tracking | ✅ Live |
| Dashboard | ✅ Live |
| Excel export | ✅ Live |
| CSV export | ✅ Live |
| Google Sheets sync | ✅ Optional |
| Colab notebooks | ✅ Optional |

## ❓ Troubleshooting

**Bot won't start**
- Check TOKEN in .env
- Check Discord bot permissions
- Run in Python 3.8+

**Polls not showing up**
- Verify POLL_CHANNEL_ID
- Check bot has Send Messages permission
- Check logs for errors

**Votes not saving**
- Check responses.xlsx is writable
- Close Excel if open
- Check disk space

## 📚 More Info

- Detailed docs: See `TECHNICAL_DOCUMENTATION.md`
- Architecture: Scroll down in technical docs
- API reference: All endpoints documented
- Python source: Well-commented in `bridge_bot/`

## 🚀 Next Steps

1. ✅ Run the bot locally
2. ✅ Create a test poll
3. ✅ Vote in Discord
4. ✅ Check dashboard
5. ✅ View results

Enjoy your feedback system! 🎉
