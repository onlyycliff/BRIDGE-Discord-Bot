"""
Bridge 2026 Flask Dashboard
Main entry point for the web interface and API
"""

import os
import sys
import json
import logging
import asyncio
import atexit
import threading
from pathlib import Path
from datetime import datetime, timezone

_BRIDGE_BOT_DIR = str(Path(__file__).resolve().parent / 'bridge_bot')
if _BRIDGE_BOT_DIR not in sys.path:
    sys.path.insert(0, _BRIDGE_BOT_DIR)


# ---------------------------------------------------------------------------
# Structured logging — configure BEFORE importing modules that trigger
# module-level logging.basicConfig (bot.py, etc.).
# ---------------------------------------------------------------------------
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        obj = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(obj, default=str)


_root_logger = logging.getLogger()
# Remove any handlers added by imported modules (e.g. bot.py)
_root_logger.handlers.clear()
_handler = logging.StreamHandler()
if os.getenv("JSON_LOG", "").lower() in ("1", "true", "yes"):
    _handler.setFormatter(JSONFormatter())
else:
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
_root_logger.setLevel(logging.INFO)
_root_logger.addHandler(_handler)

logger = logging.getLogger(__name__)


from flask import Flask, render_template, redirect, url_for
from dotenv import load_dotenv

from bot import start_bot, bot
from api import api


# ---------------------------------------------------------------------------
# Environment validation
# ---------------------------------------------------------------------------
def _validate_env() -> None:
    """Check that all required env vars are present before starting."""
    required = {
        "TOKEN": "Discord bot token",
        "POLL_CHANNEL_ID": "Default poll channel ID",
        "DATABASE_URL": "PostgreSQL connection string",
    }
    missing = []
    load_dotenv(Path(__file__).resolve().parent / ".env")
    load_dotenv(Path(__file__).resolve().parent / "bridge_bot" / ".env")
    for key, desc in required.items():
        if not os.getenv(key):
            missing.append(f"  {key}  ({desc})")
    if missing:
        logger.error(
            "Missing required environment variables:\n" + "\n".join(missing)
        )
        raise SystemExit(1)
    logger.info("Environment validation passed")


_validate_env()


# ---------------------------------------------------------------------------
# Database startup check (runs in a one-shot event loop)
# ---------------------------------------------------------------------------
def _verify_db() -> None:
    """Run the async DB connectivity check synchronously at startup."""
    from db.session import ensure_db
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(ensure_db(timeout=15.0))
    except RuntimeError as e:
        logger.error(str(e))
        raise SystemExit(1) from e
    finally:
        loop.close()


_verify_db()


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__, template_folder='templates', static_folder='static')
dashboard = app

_bot_started = False
_bot_thread_lock = threading.Lock()


def run_bot_thread():
    try:
        logger.info("Starting Discord bot...")
        start_bot()
    except Exception as e:
        logger.error(f"Bot error: {e}")


def _ensure_bot_started():
    global _bot_started
    if _bot_started:
        return
    with _bot_thread_lock:
        if _bot_started:
            return
        _bot_started = True
        thread = threading.Thread(target=run_bot_thread, daemon=True)
        thread.start()
        logger.info("Bot thread auto-started")


_ensure_bot_started()

dashboard.register_blueprint(api)


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------
def _shutdown():
    logger.info("Shutting down — disposing database engine")
    from db.session import dispose_engine
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(dispose_engine())
    except Exception as e:
        logger.error(f"Error during DB shutdown: {e}")
    finally:
        loop.close()
    logger.info("Shutdown complete")


atexit.register(_shutdown)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@dashboard.route('/')
def home():
    try:
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return f"Error loading dashboard: {e}", 500


@dashboard.route('/create-poll')
def create_poll_redirect():
    return redirect(url_for('home'), 301)


@dashboard.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {error}")
    return {"error": "Endpoint not found"}, 404


@dashboard.errorhandler(500)
def server_error(error):
    logger.error(f"500 error: {error}")
    return {"error": "Internal server error"}, 500


def main():
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting Flask dashboard on http://0.0.0.0:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
