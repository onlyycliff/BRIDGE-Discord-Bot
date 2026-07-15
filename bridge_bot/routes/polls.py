import logging
import csv
import io
from datetime import datetime

from flask import Blueprint, jsonify, request, send_file

from bridge_bot.adapter import BotAdapter
from bridge_bot.async_bridge import run_sync as _run
from bridge_bot.validators import check_rate_limit, sanitize_mentions
from db.repository import (
    end_poll as db_end_poll,
    get_all_polls,
    get_all_votes,
    get_poll_stats,
    get_summary_by_question,
)

logger = logging.getLogger(__name__)

polls_bp = Blueprint('polls', __name__)

_bot_adapter: BotAdapter = None


def set_bot_adapter(adapter: BotAdapter) -> None:
    global _bot_adapter
    _bot_adapter = adapter


@polls_bp.route('/polls/create', methods=['POST'])
def create_poll():
    try:
        if not check_rate_limit('create_poll'):
            return jsonify({"error": "Rate limited. Please wait before creating another poll."}), 429

        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        question = data.get('question', '').strip()[:200]
        description = data.get('description', '').strip()[:1000]
        options = data.get('options', [])
        channel_id = data.get('channel_id')
        role_ids = data.get('role_ids')
        max_votes_per_option = data.get('max_votes_per_option')
        poll_type = data.get('poll_type', 'poll')

        question = sanitize_mentions(question)
        description = sanitize_mentions(description)

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

        if not _bot_adapter.is_bot_ready():
            logger.warning("Bot not ready for poll creation")
            return jsonify({"error": "Bot not connected to Discord"}), 503

        loop = _bot_adapter.get_event_loop()
        if not loop or loop.is_closed():
            logger.error("Event loop not available or closed")
            return jsonify({"error": "Bot event loop unavailable"}), 503

        logger.info(f"Scheduling poll: {question} with options: {options}")
        future = _bot_adapter.schedule_coroutine(
            _bot_adapter.send_poll(
                question, options, channel_id=channel_id, role_ids=role_ids,
                max_votes_per_option=max_votes_per_option, description=description,
                poll_type=poll_type,
            )
        )

        try:
            success = future.result(timeout=10)
        except Exception:
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


@polls_bp.route('/polls', methods=['GET'])
def list_polls():
    try:
        polls = _run(get_all_polls())
        for p in polls:
            p['active'] = _bot_adapter.is_poll_active(p.get('poll_id'))
        return jsonify(polls), 200
    except Exception as e:
        logger.error(f"Error listing polls: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@polls_bp.route('/polls/<int:poll_id>', methods=['GET'])
def get_poll_detail(poll_id: int):
    try:
        stats = _run(get_poll_stats(poll_id))
        if not stats:
            return jsonify({"error": "Poll not found"}), 404

        is_active = _bot_adapter.is_poll_active(poll_id)

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


@polls_bp.route('/polls/<int:poll_id>/end', methods=['POST'])
def end_poll(poll_id: int):
    try:
        data = request.get_json(silent=True) or {}
        send_results = data.get('send_results', False)

        if not _bot_adapter.end_poll_in_state(poll_id):
            return jsonify({"error": "Poll not found or already ended"}), 404

        try:
            _run(db_end_poll(poll_id))
        except Exception as e:
            logger.error(f"Failed to close poll {poll_id} in DB: {e}")

        if send_results:
            try:
                future = _bot_adapter.schedule_coroutine(
                    _bot_adapter.end_poll_and_send_results(poll_id)
                )
                if future is not None:
                    logger.info(f"Scheduled results message for poll {poll_id}")
            except Exception as e:
                logger.error(f"Failed to schedule results for poll {poll_id}: {e}")

        logger.info(f"Poll {poll_id} ended via API")
        return jsonify({"success": True, "message": f"Poll {poll_id} ended"}), 200
    except Exception as e:
        logger.error(f"Error ending poll: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@polls_bp.route('/polls/stats', methods=['GET'])
def get_poll_stats_route():
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


@polls_bp.route('/votes', methods=['GET'])
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


@polls_bp.route('/votes/all', methods=['GET'])
def get_every_vote():
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


@polls_bp.route('/votes/by-user/<int:user_id>', methods=['GET'])
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


@polls_bp.route('/summary', methods=['GET'])
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


@polls_bp.route('/export/csv', methods=['GET'])
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


@polls_bp.route('/data/status', methods=['GET'])
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
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@polls_bp.route('/dashboard/overview', methods=['GET'])
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
