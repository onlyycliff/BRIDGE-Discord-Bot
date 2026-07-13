# Bridge 2026

Discord bot + web dashboard for the Bridge 2026 summer program. Handles interactive polls, industry tour feedback, workshop selection, and coach administration.

## Architecture

```
Discord Bot (bridge_bot/)  ←→  Flask API (api.py)  ←→  PostgreSQL
                                   ↑
                            Dashboard (dashboard.py)
                                   ↑
                          React SPA (frontend/)
```

- **Discord bot** — interactive poll buttons, auto-rule posting, slash commands
- **Flask API** — REST endpoints consumed by both the bot and the dashboard frontend
- **PostgreSQL** — all persistent state via SQLAlchemy 2.0 async + Alembic migrations
- **React SPA** — live dashboard with poll results, vote log, bot status, and coach controls

## Quick start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Node.js 18+ (for the frontend)

### Setup

```bash
# Clone and enter the repo
git clone https://github.com/onlyycliff/BRIDGE-2026.git
cd BRIDGE-2026

# Python dependencies
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Edit .env — at minimum set TOKEN, POLL_CHANNEL_ID, and DATABASE_URL

# Run database migrations
alembic upgrade head

# Seed test data
python scripts/seed_test_data.py

# Start the application (bot + dashboard)
python dashboard.py
```

The dashboard runs at `http://localhost:5000`.

### Frontend (optional)

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies API requests to Flask. The built SPA is served by Flask via `frontend/dist/`.

## Environment variables

| Variable          | Required | Description                                        |
|-------------------|----------|----------------------------------------------------|
| `TOKEN`           | Yes      | Discord bot token (from Discord Developer Portal)  |
| `POLL_CHANNEL_ID` | Yes      | Channel ID where polls are posted                  |
| `DATABASE_URL`    | Yes      | PostgreSQL connection string                       |
| `RULES_CHANNEL_NAME` | No   | Channel name for community guidelines              |
| `FLASK_ENV`       | No       | `development` or `production`                      |
| `FLASK_DEBUG`     | No       | `True` or `False`                                  |

## Commands

| Command | Description |
|---------|-------------|
| `/tour-feedback` | Post a link to the industry tour feedback form |
| Dashboard admin | Manage polls, view responses, export data (coach login required) |

## Project structure

```
├── bridge_bot/          # Discord bot logic
│   ├── bot.py
│   ├── api.py           # Flask API blueprint
│   └── colab_integration.py
├── db/                  # Database layer
│   ├── models.py
│   ├── repository.py
│   ├── session.py
│   └── enums.py
├── alembic/             # Database migrations
├── frontend/            # React dashboard SPA
├── scripts/             # Utility scripts
├── docs/                # Documentation
├── templates/           # Jinja2 templates
├── static/              # Static assets (CSS, JS)
├── dashboard.py         # Flask application entry point
├── tests/               # Unit and integration tests
├── requirements.txt
├── Dockerfile
└── Procfile
```

## Deployment

The application is designed for [Railway](https://railway.app). The `Procfile` and `Dockerfile` are pre-configured. Set the required environment variables in your Railway project dashboard.

```bash
# Deploy using the Railway CLI
railway up
```

## Testing

```bash
# Unit tests (no database needed)
pytest tests/ -m "not integration"

# Integration tests (requires TEST_DATABASE_URL)
pytest tests/ -m integration
```

## License

MIT
