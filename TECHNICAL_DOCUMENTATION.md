# Bridge 2026 Discord Bot - Technical Documentation

## 🏗️ Architecture Overview

The Bridge 2026 feedback system is built with a modern, scalable architecture:

```
┌─────────────────────────────────────────────────────────┐
│                  Discord.py Bot                         │
│  - Dynamic poll creation (2-5 options)                 │
│  - Vote tracking & validation                          │
│  - Error handling & logging                            │
└──────────┬──────────────────────────────────────────────┘
           │
           ├─► Excel Manager (Thread-safe storage)
           │   - Persistent vote records
           │   - Data export (CSV)
           │   - Legacy format support
           │
           └─► Flask Dashboard API
               ├─ /api/polls/create
               ├─ /api/votes/all
               ├─ /api/summary
               ├─ /api/dashboard/overview
               └─ /api/export/csv
                   │
                   ├─► Google Sheets Sync (Colab)
                   │   - Real-time data push
                   │   - Analysis notebooks
                   │
                   └─► Web Dashboard
                       - React-like interface
                       - Live vote log
                       - Poll visualizations
```

## 🚀 Key Improvements

### 1. **Dynamic Multi-Option Polls**
- **Before**: Only 2 hardcoded options
- **After**: 2-5 configurable options per poll
- Validated input with duplicate removal
- Better UX for poll creation

### 2. **Centralized Vote Tracking**
- **PollState class**: Prevents duplicate votes reliably
- **Before**: Inconsistent tracking across systems
- **After**: Single source of truth for vote data

### 3. **Comprehensive Error Handling**
- All async operations wrapped in try-catch
- Structured logging at INFO/WARNING/ERROR levels
- Graceful fallbacks for network/Discord issues
- User-friendly error messages

### 4. **Thread-Safe Excel Operations**
- Threading lock ensures no data corruption
- Async-friendly (non-blocking on writes)
- Automatic column standardization for legacy data
- Fallback readers for multiple formats

### 5. **REST API Endpoints**
Complete set of endpoints for dashboard integration:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Verify API status |
| `/api/polls/create` | POST | Create new poll |
| `/api/polls/stats` | GET | Get poll statistics |
| `/api/votes/all` | GET | Get all votes (filterable) |
| `/api/votes/by-user/<id>` | GET | Get user's votes |
| `/api/summary` | GET | Summary by question |
| `/api/export/csv` | GET | Export to CSV |
| `/api/dashboard/overview` | GET | Dashboard metrics |

### 6. **Enhanced Frontend**
- Modern poll creation interface
- Support for 2-5 options with add/remove buttons
- Real-time vote log with search/filter
- Live statistics updates (5-second refresh)
- Dark/light theme toggle
- Responsive design

### 7. **Google Sheets Integration**
- Direct sync to Google Sheets via gspread
- Automated summary sheet creation
- Colab notebook templates
- JSON snapshot export for offline analysis

## 📊 Data Flow

```
User creates poll (Web UI)
    ↓
POST /api/polls/create with question + options
    ↓
Bot validates & sends to Discord
    ↓
Users vote in Discord
    ↓
PollView handles vote (prevents duplicates)
    ↓
ExcelDataManager logs to Excel (thread-safe)
    ↓
Dashboard polls API for latest data
    ↓
Frontend displays live results
    ↓
Optional: Sync to Google Sheets for analysis
```

## 🔒 Security & Reliability

### Error Handling
- **Duplicate vote prevention**: PollState + Excel validation
- **Rate limiting ready**: Can add Flask-Limiter
- **Input validation**: All parameters checked
- **Logging**: All actions logged for auditing

### Data Integrity
- **Thread-safe**: mutex locks on Excel operations
- **Persistence**: All votes persisted to Excel
- **Backups**: Export to CSV for manual backup
- **Legacy support**: Handles old Excel formats

### Production-Ready
- **Configuration via environment**: No hardcoded values
- **Graceful degradation**: Works without Sheets sync
- **Monitoring**: Comprehensive logging
- **Documentation**: Docstrings on all functions

## 🔧 Configuration

### Environment Variables (`.env`)
```bash
TOKEN=your_discord_bot_token
POLL_CHANNEL_ID=1519291160240066650
RULES_CHANNEL_NAME="📜｜rules"
GOOGLE_SHEETS_ID=optional_for_sheets_sync
```

### Configurable Limits
- Max options per poll: **5** (Discord button limit)
- Min options per poll: **2**
- Vote log pagination: **100** votes per page
- Auto-refresh interval: **5 seconds**

## 📈 Performance Metrics

### Design Choices
1. **Excel over Database**: 
   - Easier to inspect/modify
   - Works offline
   - Export-friendly

2. **Thread locks over async writes**:
   - Simpler error handling
   - Prevents data races
   - Small overhead acceptable

3. **5-second dashboard refresh**:
   - Real-time feel without hammering API
   - Balanced UX/server load

## 🧪 Testing Checklist

- [ ] Poll creation with 2 options
- [ ] Poll creation with 5 options (max)
- [ ] Duplicate vote prevention
- [ ] Excel logging (check responses.xlsx)
- [ ] API /health endpoint
- [ ] Dashboard loads all sections
- [ ] Vote log search/filter
- [ ] CSV export
- [ ] Google Sheets sync (if configured)
- [ ] Colab snapshot generation

## 🚨 Known Limitations & Future Work

### Current Limitations
1. No user authentication (relies on Discord auth)
2. No rate limiting (can add Flask-Limiter)
3. No database (Excel is file-based)
4. No poll editing/deletion (can add)
5. No poll scheduling (can add)

### Possible Improvements
1. **Database migration**: PostgreSQL for scale
2. **WebSocket updates**: Real-time without polling
3. **User analytics**: Track voting patterns
4. **A/B testing**: Automatic winner selection
5. **Scheduled polls**: Cron-based automation
6. **Poll analytics**: Sentiment analysis on options

## 📚 Code Organization

```
bridge_bot/
├── bot.py              # Discord bot core (300+ lines)
│   ├── PollState       # Vote tracking class
│   ├── PollView        # Discord UI components
│   └── send_poll()     # Async poll creation
├── excel_manager.py    # Excel operations (200+ lines)
│   ├── ExcelDataManager
│   └── Thread-safe I/O
├── api.py             # Flask API endpoints (250+ lines)
│   ├── REST routes
│   └── Data transformation
├── colab_integration.py # Google Sheets sync (200+ lines)
│   ├── ColabIntegration
│   └── Sheet sync methods
└── __init__.py        # Package exports

dashboard.py           # Flask app entry point
templates/
├── index.html         # Poll creation UI
└── dashboard.html     # Dashboard UI (live results)
static/
├── js/dashboard-api.js  # Frontend logic
├── css/style.css
└── css/animations.css
```

## 🎯 Developer Guide

### Adding a New Feature

1. **Bot Feature** (Discord interaction):
   - Add method to `PollView` class
   - Log events with `logger.info/error`
   - Catch exceptions and handle gracefully

2. **API Endpoint** (data access):
   - Add route to `bridge_bot/api.py`
   - Use ExcelDataManager for data
   - Return JSON with proper status codes
   - Document in table above

3. **Dashboard Feature** (UI update):
   - Add HTML section to `templates/dashboard.html`
   - Add fetch/update logic to `dashboard-api.js`
   - Style with CSS variables (--color-*)

### Adding Logging

```python
import logging
logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Detailed diagnostic info")
logger.info("Important state change")
logger.warning("Something unexpected")
logger.error("Operation failed")
```

### Making Thread-Safe Changes

```python
from threading import Lock
lock = Lock()

with lock:
    # Critical section
    # Read/modify Excel or shared state
```

## 📞 Support & Debugging

### Common Issues

**Problem**: Bot not sending polls
```
Solution: Check TOKEN and POLL_CHANNEL_ID in .env
         Check bot has Send Messages permission
         Check channel ID is correct (should be integer)
```

**Problem**: Votes not saving to Excel
```
Solution: Check responses.xlsx is writable
         Check no permission errors in logs
         Verify ExcelDataManager thread lock isn't stuck
```

**Problem**: Dashboard not updating
```
Solution: Check API health: curl http://localhost:5000/api/health
         Check browser console for JS errors
         Verify Excel file exists and has data
```

### Enable Debug Logging

```python
# In dashboard.py
logging.basicConfig(level=logging.DEBUG)
# Now see all messages including debug-level
```

## 📖 References

- Discord.py docs: https://discordpy.readthedocs.io/
- Flask API guide: https://flask.palletsprojects.com/
- Pandas Excel: https://pandas.pydata.org/docs/reference/api/pandas.ExcelWriter.html
- gspread: https://docs.gspread.org/

---

**Last Updated**: 2026-07-02  
**Version**: 2.0.0  
**Status**: Production-ready with multi-option polls
