"""Poll create/end handlers."""

import logging
import re

from flask import jsonify, request

from bridge_bot.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

_MENTION_PATTERN = re.compile(r'@(everyone|here)', re.IGNORECASE)
_message_rate_limiter = RateLimiter(window_seconds=1.0, max_hits=1)


def _check_rate_limit(key: str) -> bool:
    return _message_rate_limiter.allow(key)


def _sanitize_mentions(text: str) -> str:
    return _MENTION_PATTERN.sub('\u200b@\\1', text)


def register_create_end(polls_bp):

    @polls_bp.route('/polls/create', methods=['POST'])
    def create_poll():
        try:
            from bridge_bot.api import get_bot_adapter
            _bot_adapter = get_bot_adapter()

            if not _check_rate_limit('create_poll'):
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

    @polls_bp.route('/polls/<int:poll_id>/end', methods=['POST'])
    def end_poll(poll_id: int):
        try:
            from bridge_bot.api import get_bot_adapter
            _bot_adapter = get_bot_adapter()

            data = request.get_json(silent=True) or {}
            send_results = data.get('send_results', False)

            if not _bot_adapter.end_poll_in_state(poll_id):
                return jsonify({"error": "Poll not found or already ended"}), 404

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
