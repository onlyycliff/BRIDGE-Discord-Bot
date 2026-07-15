import logging

from flask import Blueprint, jsonify, request
from flask_login import login_user as flask_login_user, current_user
from werkzeug.security import check_password_hash

from bridge_bot.auth import CoachUser
from bridge_bot.async_bridge import run_sync as _run
from bridge_bot.rate_limiter import RateLimiter
from db.repository import get_coach_by_email

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

_login_rate_limiter = RateLimiter(window_seconds=300, max_hits=10)


@auth_bp.route('/auth/login', methods=['POST'])
def auth_login():
    ip = request.remote_addr or "unknown"
    if not _login_rate_limiter.allow(ip):
        logger.warning(f"Rate limited login attempt from {ip}")
        return jsonify({"error": "Too many login attempts. Please try again later."}), 429

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        coach = _run(get_coach_by_email(email))
        if not coach or not check_password_hash(coach.password_hash, password):
            return jsonify({"error": "Invalid email or password"}), 401

        flask_login_user(CoachUser(coach))
        return jsonify({
            "success": True,
            "user": {"name": coach.name, "email": coach.email},
        }), 200
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "Login failed"}), 500


@auth_bp.route('/auth/me', methods=['GET'])
def auth_me():
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "user": {"name": current_user.name, "email": current_user.email},
        }), 200
    return jsonify({"authenticated": False}), 401
