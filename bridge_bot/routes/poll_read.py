"""Poll read handlers — list, detail, stats."""

import logging

from flask import jsonify, request

from bridge_bot.async_bridge import run_sync as _run
from db.operations import poll_op as _poll_op

logger = logging.getLogger(__name__)


def register_read(polls_bp):

    @polls_bp.route('/polls', methods=['GET'])
    def list_polls():
        try:
            from bridge_bot.api import get_bot_adapter
            _bot_adapter = get_bot_adapter()

            polls = _run(_poll_op("get_all_polls"))
            for p in polls:
                p['active'] = _bot_adapter.is_poll_active(p.get('poll_id'))
            return jsonify(polls), 200
        except Exception as e:
            logger.error(f"Error listing polls: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @polls_bp.route('/polls/<int:poll_id>', methods=['GET'])
    def get_poll_detail(poll_id: int):
        try:
            from bridge_bot.api import get_bot_adapter
            _bot_adapter = get_bot_adapter()

            stats = _run(_poll_op("get_poll_stats", poll_id))
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

    @polls_bp.route('/polls/stats', methods=['GET'])
    def get_poll_stats_route():
        try:
            poll_id = request.args.get('poll_id', type=int)

            if not poll_id:
                return jsonify({"error": "poll_id parameter required"}), 400

            stats = _run(_poll_op("get_poll_stats", poll_id))

            if not stats:
                return jsonify({"error": f"Poll {poll_id} not found"}), 404

            return jsonify(stats), 200

        except Exception as e:
            logger.error(f"Error getting poll stats: {e}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500
