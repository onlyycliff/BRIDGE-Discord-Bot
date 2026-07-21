import logging
import os
from datetime import datetime

import requests
from flask import Blueprint, jsonify, request

from bridge_bot.async_bridge import run_sync as _run
from db.operations import tour_op as _tour_op

logger = logging.getLogger(__name__)

tours_bp = Blueprint('tours', __name__)


@tours_bp.route('/tours', methods=['GET'])
def list_tours():
    try:
        tours = _run(_tour_op("get_all_tours"))
        return jsonify(tours), 200
    except Exception as e:
        logger.error(f"Error listing tours: {e}")
        return jsonify({"error": str(e)}), 500


@tours_bp.route('/tours', methods=['POST'])
def create_tour():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        name = data.get('name', '').strip()
        date_str = data.get('date', '').strip()
        company = data.get('company', '').strip()

        if not name:
            return jsonify({"error": "name is required"}), 400
        if not date_str:
            return jsonify({"error": "date is required"}), 400
        if not company:
            return jsonify({"error": "company is required"}), 400

        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({"error": "Invalid date format. Use ISO 8601 (e.g. 2026-07-29)"}), 400

        from bridge_bot.forms.google_forms_client import create_tour_feedback_form
        try:
            form_result = _run(create_tour_feedback_form(name))
        except Exception as e:
            logger.error(f"Google Form creation failed for tour '{name}': {e}")
            return jsonify({"error": f"Failed to create feedback form: {e}"}), 502

        tour = _run(_tour_op(
            "create_tour",
            name=name,
            date=date,
            company=company,
            google_form_url=form_result["form_url"],
            google_sheet_id=form_result["sheet_id"],
        ))

        return jsonify({
            "id": tour.id,
            "name": tour.name,
            "company": tour.company,
            "date": str(tour.date) if tour.date else None,
            "google_form_url": tour.google_form_url,
            "google_sheet_id": tour.google_sheet_id,
        }), 201

    except Exception as e:
        logger.error(f"Error creating tour: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@tours_bp.route('/tours/<int:tour_id>', methods=['GET'])
def get_tour_detail(tour_id: int):
    try:
        tour = _run(_tour_op("get_tour", tour_id))
        if not tour:
            return jsonify({"error": "Tour not found"}), 404
        return jsonify({
            "id": tour.id,
            "name": tour.name,
            "company": tour.company,
            "date": str(tour.date) if tour.date else None,
            "google_form_url": tour.google_form_url,
            "google_sheet_id": tour.google_sheet_id,
        }), 200
    except Exception as e:
        logger.error(f"Error getting tour: {e}")
        return jsonify({"error": str(e)}), 500


@tours_bp.route('/tours/<int:tour_id>/send-to-discord', methods=['POST'])
def send_tour_to_discord(tour_id: int):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        channel_id = data.get('channel_id')
        if not channel_id:
            return jsonify({"error": "channel_id is required"}), 400

        try:
            channel_id = int(channel_id)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid channel_id"}), 400

        tour = _run(_tour_op("get_tour", tour_id))
        if not tour:
            return jsonify({"error": "Tour not found"}), 404
        if not tour.google_form_url:
            return jsonify({"error": "Tour has no feedback form linked"}), 400

        from bridge_bot.api import get_bot_adapter
        adapter = get_bot_adapter()
        success = _run(adapter.send_tour_feedback_link(
            tour_id=tour_id,
            tour_name=tour.name,
            form_url=tour.google_form_url,
            channel_id=channel_id,
        ))

        if not success:
            return jsonify({"error": "Failed to send message to Discord"}), 502

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error(f"Error sending tour to Discord: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@tours_bp.route('/tours/<int:tour_id>/feedback', methods=['GET'])
def get_tour_feedback_route(tour_id: int):
    try:
        feedback = _run(_tour_op("get_tour_feedback", tour_id))
        return jsonify({
            "tour_id": tour_id,
            "feedback": feedback,
            "count": len(feedback),
        }), 200
    except Exception as e:
        logger.error(f"Error getting tour feedback: {e}")
        return jsonify({"error": str(e)}), 500


@tours_bp.route('/feedback/submit', methods=['POST'])
def submit_feedback():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        tour_id = data.get('tour_id')
        student_id = data.get('student_id')
        student_name = data.get('student_name', '').strip()
        rating = data.get('rating')
        comments = data.get('comments', '').strip()

        if not tour_id or not student_id:
            return jsonify({"error": "tour_id and student_id are required"}), 400

        try:
            tour_id = int(tour_id)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid tour_id"}), 400

        if rating is not None:
            try:
                rating = int(rating)
                if rating < 1 or rating > 5:
                    return jsonify({"error": "Rating must be between 1 and 5"}), 400
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid rating"}), 400

        fb = _run(_tour_op(
            "submit_tour_feedback",
            tour_id=tour_id,
            student_id=int(student_id),
            student_name=student_name or "Anonymous",
            rating=rating,
            comments=comments or None,
        ))

        return jsonify({
            "success": True,
            "message": "Feedback submitted successfully",
            "feedback_id": fb.id,
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@tours_bp.route('/github/profile', methods=['GET'])
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
