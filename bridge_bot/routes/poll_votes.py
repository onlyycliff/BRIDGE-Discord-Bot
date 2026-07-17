"""Vote retrieval handlers — paginated, all, by-user."""

import logging

from flask import jsonify, request

from bridge_bot.async_bridge import run_sync as _run
from db.operations import poll_op as _poll_op

logger = logging.getLogger(__name__)


def register_votes(polls_bp):

    @polls_bp.route('/votes', methods=['GET'])
    def get_votes_paginated():
        try:
            votes = _run(_poll_op("get_all_votes"))
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
            votes = _run(_poll_op("get_all_votes"))

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
            votes = _run(_poll_op("get_all_votes"))
            user_votes = [v for v in votes if v.get('User_ID') == user_id]

            return jsonify({
                "user_id": user_id,
                "vote_count": len(user_votes),
                "votes": user_votes
            }), 200

        except Exception as e:
            logger.error(f"Error retrieving user votes: {e}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500
