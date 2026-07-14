"""
Bridge 2026 Flask Dashboard
Main entry point for the web interface and API
"""

import os
import sys
import json
import logging
import atexit
import threading
from pathlib import Path
from datetime import datetime, timezone


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


from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import check_password_hash
from dotenv import load_dotenv

from bridge_bot.bot import start_bot
from bridge_bot.api import api


class CoachUser(UserMixin):
    """Thin adapter — adds Flask-Login behavior to a Coach model instance.

    The model layer stays pure (no Flask dependency). This adapter lives
    in the web layer where it belongs.
    """
    def __init__(self, coach):
        self.id = coach.id
        self.email = coach.email
        self.name = coach.name
        self.password_hash = coach.password_hash
        self.created_at = coach.created_at


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
# Database startup check
# ---------------------------------------------------------------------------
def _verify_db() -> None:
    """Run the async DB connectivity check synchronously at startup."""
    from db.session import ensure_db
    from bridge_bot.async_bridge import run_sync
    try:
        run_sync(ensure_db(timeout=15.0))
    except RuntimeError as e:
        logger.error(str(e))
        raise SystemExit(1) from e


_verify_db()


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24).hex())
dashboard = app

_REACT_DIST = str(Path(__file__).resolve().parent / 'frontend' / 'dist')
if os.path.isdir(_REACT_DIST):
    app.register_static = True
else:
    app.register_static = False

# ---------------------------------------------------------------------------
# Flask-Login setup
# ---------------------------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_coach(coach_id: str):
    from sqlalchemy import select
    from db.session import get_factory
    from db.models import Coach as CoachModel
    from bridge_bot.async_bridge import run_sync
    try:
        factory = get_factory()
        async def _load():
            async with factory() as session:
                stmt = select(CoachModel).where(CoachModel.id == int(coach_id))
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        coach = run_sync(_load())
        if coach is None:
            return None
        return CoachUser(coach)
    except Exception:
        return None

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

        from bridge_bot.adapter import RealBotAdapter
        from bridge_bot.api import set_bot_adapter
        set_bot_adapter(RealBotAdapter())


_ensure_bot_started()

dashboard.register_blueprint(api)


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------
def _shutdown():
    logger.info("Shutting down — disposing database engine")
    from db.session import dispose_engine
    from bridge_bot.async_bridge import run_sync, shutdown as bridge_shutdown
    try:
        run_sync(dispose_engine())
    except Exception as e:
        logger.error(f"Error during DB shutdown: {e}")
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.run_until_complete(bridge_shutdown())
    except Exception:
        pass
    logger.info("Shutdown complete")


atexit.register(_shutdown)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@dashboard.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        from db.repository import get_coach_by_email
        from bridge_bot.async_bridge import run_sync
        coach = run_sync(get_coach_by_email(email))

        if coach and check_password_hash(coach.password_hash, password):
            login_user(CoachUser(coach))
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))

        return render_template('login.html', error="Invalid email or password")

    return render_template('login.html')


@dashboard.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@dashboard.route('/feedback/<int:tour_id>')
def feedback_form(tour_id: int):
    try:
        from db.repository import get_tour
        from bridge_bot.async_bridge import run_sync
        tour = run_sync(get_tour(tour_id))

        if not tour:
            return "Tour not found", 404

        return render_template('feedback_form.html', tour=tour)
    except Exception as e:
        logger.error(f"Error loading feedback form: {e}")
        return f"Error loading feedback form: {e}", 500


@dashboard.route('/')
@login_required
def home():
    try:
        from flask import send_from_directory
        if os.path.isdir(_REACT_DIST):
            return send_from_directory(_REACT_DIST, 'index.html')
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return f"Error loading dashboard: {e}", 500


@dashboard.route('/assets/<path:filename>')
def react_assets(filename):
    from flask import send_from_directory
    assets_dir = os.path.join(_REACT_DIST, 'assets')
    if os.path.isfile(os.path.join(assets_dir, filename)):
        return send_from_directory(assets_dir, filename)
    return "Not found", 404


@dashboard.route('/favicon.svg')
def react_favicon():
    from flask import send_from_directory
    if os.path.isfile(os.path.join(_REACT_DIST, 'favicon.svg')):
        return send_from_directory(_REACT_DIST, 'favicon.svg')
    return "Not found", 404


@dashboard.route('/create-poll')
@login_required
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
