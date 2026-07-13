import os
import re
import logging
import asyncio
import time
import csv
import io
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import requests
from flask import Blueprint, jsonify, request, send_file
from bot import send_poll, end_poll_and_send_results, poll_state, bot
from db.repository import (
    end_poll as db_end_poll,
    get_all_polls,
    get_all_votes,
    get_poll_metadata,
    get_poll_stats,
    get_summary_by_question,
)


def _run(coro):
    """Run an async DB coroutine synchronously for Flask route handlers."""
    return asyncio.run(coro)

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__, url_prefix='/api')

MENTION_PATTERN = re.compile(r'@(everyone|here)', re.IGNORECASE)

_rate_limit_store: Dict[str, float] = {}
RATE_LIMIT_WINDOW = 1.0

def _check_rate_limit(key: str) -> bool:
    now = time.time()
    last = _rate_limit_store.get(key)
    if last and now - last < RATE_LIMIT_WINDOW:
        return False
    _rate_limit_store[key] = now
    return True

def _sanitize_mentions(text: str) -> str:
    return MENTION_PATTERN.sub('\u200b@\\1', text)

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
        from bot import available_channels, bot
        channels = [{"id": str(cid), "name": name} for cid, name in available_channels.items()]
        if not channels and bot.is_ready():
            for guild in bot.guilds:
                for ch in guild.text_channels:
                    channels.append({"id": str(ch.id), "name": ch.name})
        channels.sort(key=lambda c: c["name"])
        return jsonify(channels), 200
    except Exception as e:
        logger.error(f"Error listing channels: {e}")
        return jsonify({"error": str(e)}), 500


@api.route('/discord/roles', methods=['GET'])
def list_roles():
    try:
        from bot import available_roles, bot
        roles = [{"id": str(rid), "name": name} for rid, name in available_roles.items()]
        if not roles and bot.is_ready():
            for guild in bot.guilds:
                for r in guild.roles:
                    if not r.is_default():
                        roles.append({"id": str(r.id), "name": r.name})
        roles.sort(key=lambda r: r["name"])
        return jsonify(roles), 200
    except Exception as e:
        logger.error(f"Error listing roles: {e}")
        return jsonify({"error": str(e)}), 500


@api.route('/polls/create', methods=['POST'])
def create_poll():
    try:
        if not _check_rate_limit('create_poll'):
            return jsonify({"error": "Rate limited. Please wait before creating another poll."}), 429

        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        question = data.get('question', '').strip()[:200]
        description = data.get('description', '').strip()[:1000]
        options = data.get('options', [])
        channel_id = data.get('channel_id')
        role_ids = data.get('role_ids')
        max_votes_per_option = data.get('max_votes_per_option')

        question = _sanitize_mentions(question)
        description = _sanitize_mentions(description)

        if not question:
            return jsonify({"error": "Question is required"}), 400

        if not isinstance(options, list) or len(options) < 2:
            return jsonify({"error": "At least 2 options are required"}), 400

        if len(options) > 5:
            return jsonify({"error": "Maximum 5 options allowed"}), 400

        options = [opt.strip()[:100] for opt in options if opt.strip()]
        options = list(dict.fromkeys(options))

        if len(options) < 2:
            return jsonify({"error": "Need at least 2 unique options"}), 400

        if channel_id is not None:
            try:
                channel_id = int(channel_id)
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid channel_id"}), 400

        if role_ids is not None:
            if not isinstance(role_ids, list):
                return jsonify({"error": "role_ids must be a list"}), 400
            try:
                role_ids = [int(rid) for rid in role_ids]
            except (ValueError, TypeError):
                return jsonify({"error": "role_ids must contain valid integers"}), 400

        if max_votes_per_option is not None:
            try:
                max_votes_per_option = int(max_votes_per_option)
            except (ValueError, TypeError):
                return jsonify({"error": "max_votes_per_option must be an integer"}), 400
            if max_votes_per_option < 1:
                return jsonify({"error": "max_votes_per_option must be at least 1"}), 400

        if not bot or not bot.is_ready():
            logger.warning("Bot not ready for poll creation")
            return jsonify({"error": "Bot not connected to Discord"}), 503

        loop = bot.loop
        if not loop or loop.is_closed():
            logger.error("Event loop not available or closed")
            return jsonify({"error": "Bot event loop unavailable"}), 503

        logger.info(f"Scheduling poll: {question} with options: {options}")
        future = asyncio.run_coroutine_threadsafe(
            send_poll(question, options, channel_id=channel_id, role_ids=role_ids,
                      max_votes_per_option=max_votes_per_option, description=description),
            loop
        )

        try:
            success = future.result(timeout=10)
        except asyncio.TimeoutError:
            logger.error(f"Timeout scheduling poll: {question}")
            return jsonify({"error": "Poll creation timed out"}), 504

        if not success:
            logger.warning(f"Poll creation returned False for: {question}")
            return jsonify({"error": "Failed to send poll to Discord - check logs"}), 500

        logger.info(f"Poll created successfully: {question} with {len(options)} options")
        return jsonify({
            "success": True,
            "message": "Poll sent successfully",
            "question": question,
            "options": options
        }), 201

    except Exception as e:
        logger.error(f"Error creating poll: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@api.route('/polls', methods=['GET'])
def list_polls():
    try:
        polls = _run(get_all_polls())
        try:
            from bot import poll_state
            for p in polls:
                p['active'] = poll_state.is_active(p.get('poll_id'))
        except Exception:
            for p in polls:
                p['active'] = False
        return jsonify(polls), 200
    except Exception as e:
        logger.error(f"Error listing polls: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api.route('/polls/<int:poll_id>', methods=['GET'])
def get_poll_detail(poll_id: int):
    try:
        stats = _run(get_poll_stats(poll_id))
        if not stats:
            return jsonify({"error": "Poll not found"}), 404

        is_active = poll_state.is_active(poll_id)

        options_list = [
            {"name": choice, "votes": count}
            for choice, count in stats.get("choices", {}).items()
        ]

        return jsonify({
            "poll_id": poll_id,
            "question": stats.get("question", "Unknown"),
            "options": options_list,
            "total_votes": stats.get("total_votes", 0),
            "active": is_active,
            "voters_by_choice": stats.get("voters_by_choice", {})
        }), 200
    except Exception as e:
        logger.error(f"Error getting poll detail: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api.route('/polls/<int:poll_id>/end', methods=['POST'])
def end_poll(poll_id: int):
    try:
        data = request.get_json(silent=True) or {}
        send_results = data.get('send_results', False)

        if not poll_state.end_poll(poll_id):
            return jsonify({"error": "Poll not found or already ended"}), 404

        try:
            _run(db_end_poll(poll_id))
        except Exception as e:
            logger.error(f"Failed to close poll {poll_id} in DB: {e}")

        if send_results:
            try:
                loop = bot.loop
                if loop and not loop.is_closed():
                    asyncio.run_coroutine_threadsafe(
                        end_poll_and_send_results(poll_id),
                        loop
                    )
                    logger.info(f"Scheduled results message for poll {poll_id}")
            except Exception as e:
                logger.error(f"Failed to schedule results for poll {poll_id}: {e}")

        logger.info(f"Poll {poll_id} ended via API")
        return jsonify({"success": True, "message": f"Poll {poll_id} ended"}), 200
    except Exception as e:
        logger.error(f"Error ending poll: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api.route('/votes', methods=['GET'])
def get_votes_paginated():
    try:
        votes = _run(get_all_votes())
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 25, type=int)
        question_filter = request.args.get("question")
        username_filter = request.args.get("username")

        if question_filter:
            votes = [v for v in votes if question_filter.lower() in str(v.get("Question", "")).lower()]
        if username_filter:
            votes = [v for v in votes if username_filter.lower() in str(v.get("Username", "")).lower()]

        mapped = []
        for v in votes:
            mapped.append({
                "timestamp": v.get("Timestamp", ""),
                "username": v.get("Username", ""),
                "user_id": v.get("User_ID", ""),
                "question": v.get("Question", ""),
                "choice": v.get("Choice", ""),
                "poll_id": v.get("Poll_ID", "")
            })

        total = len(mapped)
        start = (page - 1) * limit
        end = start + limit
        page_votes = mapped[start:end] if start < total else []

        return jsonify({
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": max(1, (total + limit - 1) // limit),
            "votes": page_votes
        }), 200
    except Exception as e:
        logger.error(f"Error getting votes: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api.route('/bot-status', methods=['GET'])
def get_bot_status():
    try:
        from bot import bot, poll_state, start_time

        online = bot is not None and bot.is_ready()

        uptime_str = "N/A"
        if online and start_time:
            elapsed = datetime.now() - start_time
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours}h {minutes}m {seconds}s"

        all_votes = _run(get_all_votes())
        total_votes = len(all_votes)

        today = datetime.now().strftime("%Y-%m-%d")
        votes_today = sum(
            1 for v in all_votes
            if str(v.get("Timestamp", "")).startswith(today)
        )

        avatar_url = str(bot.user.avatar.url) if online and bot.user and bot.user.avatar else ""

        return jsonify({
            "online": online,
            "uptime": uptime_str,
            "votes_total": total_votes,
            "votes_today": votes_today,
            "last_command": "N/A",
            "latency_ms": round(bot.latency * 1000, 1) if online and hasattr(bot, "latency") else 0,
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


@api.route('/polls/stats', methods=['GET'])
def get_poll_stats():
    try:
        poll_id = request.args.get('poll_id', type=int)

        if not poll_id:
            return jsonify({"error": "poll_id parameter required"}), 400

        stats = _run(get_poll_stats(poll_id))

        if not stats:
            return jsonify({"error": f"Poll {poll_id} not found"}), 404

        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Error getting poll stats: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@api.route('/votes/all', methods=['GET'])
def get_all_votes():
    try:
        votes = _run(get_all_votes())

        question_filter = request.args.get('question')
        username_filter = request.args.get('username')
        limit = request.args.get('limit', type=int)

        if question_filter:
            votes = [v for v in votes if question_filter.lower() in str(v.get('Question', '')).lower()]

        if username_filter:
            votes = [v for v in votes if username_filter.lower() in str(v.get('Username', '')).lower()]

        if limit:
            votes = votes[-limit:]

        return jsonify({
            "total": len(votes),
            "votes": votes
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving votes: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@api.route('/votes/by-user/<int:user_id>', methods=['GET'])
def get_user_votes(user_id: int):
    try:
        votes = _run(get_all_votes())
        user_votes = [v for v in votes if v.get('User_ID') == user_id]

        return jsonify({
            "user_id": user_id,
            "vote_count": len(user_votes),
            "votes": user_votes
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving user votes: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@api.route('/summary', methods=['GET'])
def get_summary():
    try:
        summary = _run(get_summary_by_question())

        if not summary:
            return jsonify({"summary": {}, "total_questions": 0}), 200

        return jsonify({
            "summary": summary,
            "total_questions": len(summary)
        }), 200

    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@api.route('/export/csv', methods=['GET'])
def export_csv():
    try:
        votes = _run(get_all_votes())
        if not votes:
            return jsonify({"error": "No data to export"}), 404

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "Timestamp", "Username", "User_ID", "Question", "Choice", "Poll_ID",
        ])
        writer.writeheader()
        for v in votes:
            writer.writerow({
                "Timestamp": v.get("Timestamp", ""),
                "Username": v.get("Username", ""),
                "User_ID": v.get("User_ID", ""),
                "Question": v.get("Question", ""),
                "Choice": v.get("Choice", ""),
                "Poll_ID": v.get("Poll_ID", ""),
            })

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            as_attachment=True,
            download_name="poll_feedback.csv",
            mimetype="text/csv",
        )

    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@api.route('/data/status', methods=['GET'])
def get_data_status():
    try:
        all_votes = _run(get_all_votes())
        total_records = len(all_votes)

        last_timestamp = "N/A"
        if total_records > 0:
            timestamps = [v.get('Timestamp', '') for v in all_votes if v.get('Timestamp')]
            if timestamps:
                last_timestamp = max(timestamps)

        return jsonify({
            "total_records": total_records,
            "last_timestamp": last_timestamp,
            "storage": "postgresql",
            "status": "healthy"
        }), 200
    except Exception as e:
        logger.error(f"Error getting data status: {e}")
        return jsonify({"error": str(e)}), 500


@api.route('/dashboard/overview', methods=['GET'])
def get_dashboard_overview():
    try:
        all_votes = _run(get_all_votes())
        summary = _run(get_summary_by_question())

        total_votes = len(all_votes) if all_votes else 0
        unique_voters = len(set(v.get('User_ID') for v in all_votes if v.get('User_ID'))) if all_votes else 0
        active_polls = len(summary) if summary else 0

        engagement_rate = "0%"
        if total_votes > 0 and unique_voters > 0:
            try:
                engagement_rate = f"{(unique_voters / total_votes * 100):.1f}%"
            except (TypeError, ZeroDivisionError):
                engagement_rate = "N/A"

        return jsonify({
            "total_votes": total_votes,
            "unique_voters": unique_voters,
            "active_polls": active_polls,
            "engagement_rate": engagement_rate,
            "last_updated": datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error getting dashboard overview: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@api.route('/github/profile', methods=['GET'])
def github_profile():
    try:
        username = os.getenv("GITHUB_USERNAME", "onlyycliff")
        user_resp = requests.get(f"https://api.github.com/users/{username}", timeout=10)
        repos_resp = requests.get(f"https://api.github.com/users/{username}/repos?sort=updated&per_page=10", timeout=10)
        if user_resp.status_code != 200:
            return jsonify({"error": "Failed to fetch GitHub profile"}), 502

        user = user_resp.json()
        repos = repos_resp.json() if repos_resp.status_code == 200 else []

        return jsonify({
            "login": user.get("login"),
            "name": user.get("name"),
            "avatar_url": user.get("avatar_url"),
            "bio": user.get("bio"),
            "location": user.get("location"),
            "blog": user.get("blog"),
            "public_repos": user.get("public_repos", 0),
            "followers": user.get("followers", 0),
            "following": user.get("following", 0),
            "repos": [
                {
                    "name": r.get("name"),
                    "description": r.get("description"),
                    "language": r.get("language"),
                    "stars": r.get("stargazers_count", 0),
                    "url": r.get("html_url")
                }
                for r in repos
            ]
        }), 200

    except requests.RequestException as e:
        logger.error(f"Error fetching GitHub profile: {e}")
        return jsonify({"error": "GitHub API request failed"}), 502
    except Exception as e:
        logger.error(f"Error in github_profile: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500
