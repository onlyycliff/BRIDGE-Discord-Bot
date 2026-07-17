"""Analytics handlers — summary, CSV export, data status, dashboard overview."""

import csv
import io
import logging
from datetime import datetime

from flask import jsonify, send_file

from bridge_bot.async_bridge import run_sync as _run
from db.operations import poll_op as _poll_op

logger = logging.getLogger(__name__)


def register_analytics(polls_bp):

    @polls_bp.route('/summary', methods=['GET'])
    def get_summary():
        try:
            summary = _run(_poll_op("get_summary_by_question"))

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
            votes = _run(_poll_op("get_all_votes"))
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
            all_votes = _run(_poll_op("get_all_votes"))
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
            all_votes = _run(_poll_op("get_all_votes"))
            summary = _run(_poll_op("get_summary_by_question"))

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
