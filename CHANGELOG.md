# Changelog - Bridge 2026 Bot

## [2.0.0] - 2026-07-02 - Major Refactor & Enhancement

### 🚀 New Features

#### Multi-Option Poll Support
- Polls now support **2-5 options** (was limited to 2)
- Configurable poll options via web interface
- Better UX with add/remove option buttons
- Dynamic Discord button generation

#### Comprehensive Dashboard
- **Poll Results Section**: Visual breakdown with progress bars
- **Vote Log Section**: Complete vote history with search/filter
- **Live Control Section**: Real-time poll creation and preview
- **Auto-refresh**: Data updates every 5 seconds
- **Export to CSV**: Download all poll data
- **Dark/Light Theme**: Theme toggle button

#### REST API Endpoints
- `/api/health` - Health check
- `/api/polls/create` - Create new poll
- `/api/polls/stats` - Get poll statistics
- `/api/votes/all` - Get all votes with filters
- `/api/votes/by-user/<id>` - Get user's votes
- `/api/summary` - Summary by question
- `/api/export/csv` - Export data to CSV
- `/api/dashboard/overview` - Dashboard metrics

#### Google Sheets Integration
- Direct sync to Google Sheets via gspread
- Automated summary sheet generation
- Colab notebook templates for analysis
- JSON snapshot export

### 🔧 Improvements

#### Code Quality
- **Comprehensive Logging**: All operations logged at INFO/WARNING/ERROR levels
- **Type Hints**: Full type annotations on functions for better IDE support
- **Error Handling**: Try-catch blocks on all async operations
- **Docstrings**: Detailed documentation on all classes and functions
- **Code Organization**: Modular design with clear separation of concerns

#### Bot Core (bot.py)
- New `PollState` class for centralized vote tracking
- Dynamic `PollView` supports 2-5 options
- Improved embed generation with better formatting
- Better rules posting with duplicate prevention
- Graceful handling of missing channels/permissions

#### Excel Manager (excel_manager.py)
- Input validation on all vote submissions
- Improved error handling and logging
- Better fallback for legacy Excel formats
- Cleaner data standardization
- Performance: Thread-safe with minimal locking

#### Dashboard (dashboard.py)
- Proper error handling and logging
- Removed unsafe asyncio.run usage
- Better threading for bot startup
- Comprehensive docstrings

#### API (api.py) - NEW FILE
- Proper async handling for Discord operations
- Comprehensive input validation
- Consistent JSON response format
- Better error messages
- Query parameter filtering support

### 🔒 Security & Reliability

#### Error Handling
- No unhandled exceptions in critical paths
- User-friendly error messages
- Detailed logging for debugging
- Graceful fallbacks for network issues

#### Data Integrity
- Thread-safe Excel operations with mutex locks
- Duplicate vote prevention with validation
- Persistent storage of all votes
- CSV export for data backup

#### Configuration
- Environment variables for all secrets
- No hardcoded values
- `.env.example` provided
- Configurable limits and timeouts

### 📊 Data & Performance

#### Storage
- Excel file (responses.xlsx) for persistence
- CSV export capability
- JSON snapshots for Colab
- Automatic column standardization

#### Performance
- 5-second auto-refresh interval (tunable)
- Browser tab awareness (pause refresh when hidden)
- Efficient filtering and search
- Minimal API payload sizes

### 📚 Documentation

#### New Files
- `TECHNICAL_DOCUMENTATION.md` - Complete architecture guide
- `QUICKSTART.md` - 5-minute setup guide
- `.env.example` - Configuration template
- Improved code comments throughout

#### Comprehensive Coverage
- Architecture diagrams
- API endpoint table
- Data flow visualization
- Configuration guide
- Troubleshooting section
- Developer guide

### 📦 Dependencies

#### Added
- `gspread>=5.0.0` - Google Sheets integration
- `google-auth-oauthlib>=1.0.0` - Google authentication
- Version pins on existing packages

#### Updated
- discord.py to >=2.0.0
- pandas to >=1.3.0
- flask to >=2.0.0

### 🐛 Bug Fixes

- Fixed vote tracking inconsistency between systems
- Fixed Excel file locking issues on Windows
- Fixed missing error handling in poll creation
- Fixed rules posting duplicating on restart
- Fixed Unicode encoding issues in logging

### ⚡ Performance Improvements

- Thread-safe operations don't block bot
- Excel writes use efficient pandas operations
- Dashboard only refreshes visible sections
- API queries optimized with filters

### 🧪 Testing

All functionality tested:
- ✓ Poll creation with 2-5 options
- ✓ Duplicate vote prevention
- ✓ Excel persistence
- ✓ API health check
- ✓ Dashboard loading
- ✓ Vote log search/filter
- ✓ CSV export
- ✓ Theme toggle

### 📋 Breaking Changes

- **API**: Old `/submit` endpoint removed (replaced with `/api/polls/create`)
- **Excel**: May auto-standardize column names on first run
- **Environment**: Requires POLL_CHANNEL_ID now (was hardcoded)

### 🔄 Migration Guide

If upgrading from 1.0:

1. Backup `responses.xlsx`
2. Update dependencies: `pip install -r requirements.txt`
3. Create `.env` from `.env.example`
4. Update Discord bot permissions
5. Run new version

Excel data is automatically migrated.

### 🎯 Known Limitations

- No database (file-based Excel)
- No user authentication
- No rate limiting (can add Flask-Limiter)
- No poll editing/deletion
- No poll scheduling

### 🚀 Future Roadmap

- [ ] Database migration (PostgreSQL)
- [ ] WebSocket real-time updates
- [ ] User analytics
- [ ] Poll scheduling
- [ ] Sentiment analysis
- [ ] A/B testing automation
- [ ] Mobile app
- [ ] Notification system

### 📞 Support

For issues, questions, or suggestions:
1. Check `TECHNICAL_DOCUMENTATION.md`
2. Review `QUICKSTART.md`
3. Check logs for errors
4. Consult troubleshooting section

---

## [1.0.0] - Previous Release

- Initial release with basic 2-option polls
- Simple Excel logging
- Manual dashboard
- Legacy reaction voting

---

**Current Version**: 2.0.0  
**Release Date**: 2026-07-02  
**Status**: Production-ready  
**Last Updated**: 2026-07-02
