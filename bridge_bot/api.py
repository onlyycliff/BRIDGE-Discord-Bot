import logging
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user

from bridge_bot.adapter import BotAdapter, StubBotAdapter
from bridge_bot.async_bridge import run_sync as _run
from bridge_bot.routes.polls import polls_bp
from bridge_bot.routes.tours import tours_bp
from bridge_bot.routes.auth import auth_bp
from db.session import get_session
from db.poll_repository import PollRepository

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__, url_prefix='/api')

_bot_adapter: BotAdapter = StubBotAdapter()

PUBLIC_ROUTES = {
    "api.health_check",
    "api.tours.submit_feedback",
    "api.tours.github_profile",
    "api.auth.auth_login",
    "api.auth.auth_me",
}


@api.before_request
def require_auth():
    if request.method == "OPTIONS":
        return None
    if request.endpoint in PUBLIC_ROUTES:
        return None
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401
    return None


def get_bot_adapter() -> BotAdapter:
    """Return the current bot adapter instance."""
    return _bot_adapter


def set_bot_adapter(adapter: BotAdapter) -> None:
    """Called by dashboard.py after the bot thread starts."""
    global _bot_adapter
    _bot_adapter = adapter


@api.route('/health', methods=['GET'])
def health_check():
    try:
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api.route('/discord/channels', methods=['GET'])
def list_channels():
    try:
        channels = _bot_adapter.list_channels()
        return jsonify(channels), 200
    except Exception as e:
        logger.error(f"Error listing channels: {e}")
        return jsonify({"error": str(e)}), 500


@api.route('/discord/roles', methods=['GET'])
def list_roles():
    try:
        roles = _bot_adapter.list_roles()
        return jsonify(roles), 200
    except Exception as e:
        logger.error(f"Error listing roles: {e}")
        return jsonify({"error": str(e)}), 500


@api.route('/bot-status', methods=['GET'])
def get_bot_status():
    try:
        online = _bot_adapter.is_bot_ready()

        uptime_str = "N/A"
        start_time = _bot_adapter.get_bot_start_time()
        if online and start_time:
            elapsed = datetime.now() - start_time
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours}h {minutes}m {seconds}s"

        async def _get_votes():
            async with get_session() as session:
                return await PollRepository(session).get_all_votes()
        all_votes = _run(_get_votes())
        total_votes = len(all_votes)

        today = datetime.now().strftime("%Y-%m-%d")
        votes_today = sum(
            1 for v in all_votes
            if str(v.get("Timestamp", "")).startswith(today)
        )

        avatar_url = _bot_adapter.get_bot_avatar_url()

        return jsonify({
            "online": online,
            "uptime": uptime_str,
            "votes_total": total_votes,
            "votes_today": votes_today,
            "last_command": "N/A",
            "latency_ms": _bot_adapter.get_bot_latency_ms(),
            "avatar_url": avatar_url
        }), 200
    except Exception as e:
        logger.error(f"Error getting bot status: {e}", exc_info=True)
        return jsonify({
            "online": False,
            "uptime": "N/A",
            "votes_total": 0,
            "votes_today": 0,
            "last_command": "N/A",
            "latency_ms": 0,
            "avatar_url": ""
        }), 200


api.register_blueprint(polls_bp)
api.register_blueprint(tours_bp)
api.register_blueprint(auth_bp)
