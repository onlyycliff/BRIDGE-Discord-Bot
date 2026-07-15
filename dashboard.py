"""
Bridge 2026 Flask Dashboard
App factory pattern — create_app() is the single entry point.
"""

import os
import json
import logging
import atexit
import threading
from pathlib import Path
from datetime import datetime, timezone

from flask import Flask, redirect, send_from_directory
from flask_login import LoginManager, logout_user, current_user
from dotenv import load_dotenv


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


def _configure_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    if os.getenv("JSON_LOG", "").lower() in ("1", "true", "yes"):
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
    root.setLevel(logging.INFO)
    root.addHandler(handler)


# ---------------------------------------------------------------------------
# Environment validation
# ---------------------------------------------------------------------------
def _validate_env() -> None:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    load_dotenv(Path(__file__).resolve().parent / "bridge_bot" / ".env")
    required = {
        "TOKEN": "Discord bot token",
        "POLL_CHANNEL_ID": "Default poll channel ID",
        "DATABASE_URL": "PostgreSQL connection string",
    }
    missing = []
    for key, desc in required.items():
        if not os.getenv(key):
            missing.append(f"  {key}  ({desc})")
    if missing:
        raise SystemExit(
            "Missing required environment variables:\n" + "\n".join(missing)
        )


# ---------------------------------------------------------------------------
# Database startup check
# ---------------------------------------------------------------------------
def _verify_db() -> None:
    from db.session import ensure_db
    from bridge_bot.async_bridge import run_sync
    run_sync(ensure_db(timeout=15.0))


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
_REACT_DIST = str(Path(__file__).resolve().parent / "frontend" / "dist")


def create_app() -> Flask:
    """Create and configure the Flask application.

    Side effects (env validation, DB check) run inside this function,
    not at module import time. The module-level ``app = create_app()``
    call exists only for gunicorn compatibility.
    """
    _configure_logging()
    logger = logging.getLogger(__name__)

    _validate_env()
    logger.info("Environment validation passed")

    try:
        _verify_db()
    except RuntimeError as exc:
        logger.error(str(exc))
        raise SystemExit(1) from exc
    logger.info("Database verification passed")

    app = Flask(__name__)

    secret_key = os.getenv("FLASK_SECRET_KEY")
    if not secret_key:
        if os.getenv("FLASK_ENV") == "production":
            logger.error(
                "FLASK_SECRET_KEY is not set — sessions will be invalid on "
                "every restart. Set it in your environment."
            )
        secret_key = os.urandom(24).hex()
    app.secret_key = secret_key

    from flask_cors import CORS
    CORS(
        app,
        origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
        supports_credentials=True,
    )

    app.react_dist = _REACT_DIST  # type: ignore[attr-defined]

    # ---- Flask-Login ---------------------------------------------------
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"

    from bridge_bot.auth import CoachUser

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

    # ---- API blueprint -------------------------------------------------
    from bridge_bot.api import api
    app.register_blueprint(api)

    # ---- SPA routes ----------------------------------------------------
    _register_spa_routes(app)

    # ---- Error handlers ------------------------------------------------
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"404 error: {error}")
        return {"error": "Endpoint not found"}, 404

    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"500 error: {error}")
        return {"error": "Internal server error"}, 500

    # ---- Graceful shutdown ---------------------------------------------
    def _shutdown():
        logger.info("Shutting down — disposing database engine")
        from db.session import dispose_engine
        from bridge_bot.async_bridge import run_sync, shutdown as bridge_shutdown
        try:
            run_sync(dispose_engine())
        except Exception as exc:
            logger.error(f"Error during DB shutdown: {exc}")
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.run_until_complete(bridge_shutdown())
        except Exception:
            pass
        logger.info("Shutdown complete")

    atexit.register(_shutdown)

    return app


# ---------------------------------------------------------------------------
# SPA static routes
# ---------------------------------------------------------------------------
def _register_spa_routes(app: Flask) -> None:
    react_dist = _REACT_DIST

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect("/")
        try:
            if os.path.isdir(react_dist):
                return send_from_directory(react_dist, "index.html")
        except Exception as exc:
            logging.getLogger(__name__).error(f"Error loading login: {exc}")
        return "Frontend not built", 500

    @app.route("/logout")
    def logout():
        logout_user()
        return redirect("/login")

    @app.route("/feedback/<int:tour_id>")
    def feedback_form(tour_id: int):
        try:
            if os.path.isdir(react_dist):
                return send_from_directory(react_dist, "index.html")
        except Exception as exc:
            logging.getLogger(__name__).error(f"Error loading feedback form: {exc}")
        return "Frontend not built", 500

    @app.route("/")
    def home():
        try:
            if os.path.isdir(react_dist):
                return send_from_directory(react_dist, "index.html")
        except Exception as exc:
            logging.getLogger(__name__).error(f"Error loading dashboard: {exc}")
            return f"Error loading dashboard: {exc}", 500
        return "Frontend not built", 500

    @app.route("/assets/<path:filename>")
    def react_assets(filename):
        assets_dir = os.path.join(react_dist, "assets")
        if os.path.isfile(os.path.join(assets_dir, filename)):
            return send_from_directory(assets_dir, filename)
        return "Not found", 404

    @app.route("/favicon.svg")
    def react_favicon():
        if os.path.isfile(os.path.join(react_dist, "favicon.svg")):
            return send_from_directory(react_dist, "favicon.svg")
        return "Not found", 404

    @app.route("/create-poll")
    def create_poll_redirect():
        return redirect("/", 301)

    @app.route("/<path:path>")
    def catch_all(path):
        file_path = os.path.join(react_dist, path)
        if os.path.isfile(file_path):
            return send_from_directory(react_dist, path)
        if os.path.isdir(react_dist):
            return send_from_directory(react_dist, "index.html")
        return "Frontend not built", 500


# ---------------------------------------------------------------------------
# Module-level app for gunicorn (BOT_START defaults to false here)
# ---------------------------------------------------------------------------
app = create_app()


# ---------------------------------------------------------------------------
# CLI entry point — starts bot when BOT_START=true
# ---------------------------------------------------------------------------
def _start_bot_thread() -> None:
    from bridge_bot.bot import start_bot
    from bridge_bot.adapter import RealBotAdapter
    from bridge_bot.api import set_bot_adapter
    from bridge_bot.poll_view import set_adapter as set_poll_view_adapter

    def _run():
        try:
            logging.getLogger(__name__).info("Starting Discord bot...")
            start_bot()
        except Exception as exc:
            logging.getLogger(__name__).error(f"Bot error: {exc}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    adapter = RealBotAdapter()
    set_bot_adapter(adapter)
    set_poll_view_adapter(adapter)
    logging.getLogger(__name__).info("Bot thread started")


if __name__ == "__main__":
    if os.getenv("BOT_START", "").lower() in ("1", "true", "yes"):
        _start_bot_thread()

    port = int(os.getenv("PORT", 5000))
    logging.getLogger(__name__).info(
        f"Starting Flask dashboard on http://0.0.0.0:{port}"
    )
    app.run(debug=False, host="0.0.0.0", port=port)
