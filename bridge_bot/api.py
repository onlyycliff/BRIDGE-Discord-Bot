# Backend API for Bridge Dashboard
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from flask import Blueprint, jsonify, request
from .excel_manager import excel_manager
from .bot import send_poll

logger = logging.getLogger(__name__)

# Create API blueprint for separation of concerns
api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint - verify API and bot are responsive"""
    try:
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api.route('/polls/create', methods=['POST'])
def create_poll():
    """Create a new poll with multiple options
    
    Expected JSON:
    {
        "question": "Your question here",
        "options": ["Option 1", "Option 2", "Option 3"]
    }
    """
    try:
        data = request.get_json()
        
        # Validate input
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        question = data.get('question', '').strip()
        options = data.get('options', [])
        
        if not question:
            return jsonify({"error": "Question is required"}), 400
        
        if not isinstance(options, list) or len(options) < 2:
            return jsonify({"error": "At least 2 options are required"}), 400
        
        if len(options) > 5:
            return jsonify({"error": "Maximum 5 options allowed"}), 400
        
        # Remove duplicates and empty options
        options = [opt.strip() for opt in options if opt.strip()]
        options = list(dict.fromkeys(options))  # Remove duplicates while preserving order
        
        if len(options) < 2:
            return jsonify({"error": "Need at least 2 unique options"}), 400
        
        # Send poll to Discord - use thread-safe approach
        try:
            from .bot import bot
            
            # Check if bot is connected
            if not bot or not bot.is_ready():
                logger.warning("Bot not ready for poll creation")
                return jsonify({"error": "Bot not connected to Discord"}), 503
            
            # Get the running event loop from the bot
            loop = None
            try:
                # Try to get the bot's event loop
                loop = bot.loop
            except (AttributeError, RuntimeError):
                logger.warning("Could not get bot event loop, attempting fallback")
            
            # If no loop available, we have a connection issue
            if not loop or loop.is_closed():
                logger.error("Event loop not available or closed")
                return jsonify({"error": "Bot event loop unavailable"}), 503
            
            # Schedule coroutine safely
            logger.info(f"Scheduling poll: {question} with options: {options}")
            task = asyncio.run_coroutine_threadsafe(send_poll(question, options), loop)
            
            # Wait for result with timeout
            success = task.result(timeout=10)
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout scheduling poll: {question}")
            return jsonify({"error": "Poll creation timed out"}), 504
        except Exception as inner_e:
            logger.error(f"Error scheduling poll: {inner_e}", exc_info=True)
            return jsonify({"error": f"Failed to send poll: {str(inner_e)}"}), 500
        
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
    """List all polls with vote counts"""
    try:
        polls = excel_manager.get_all_polls()
        return jsonify(polls), 200
    except Exception as e:
        logger.error(f"Error listing polls: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api.route('/polls/<int:poll_id>', methods=['GET'])
def get_poll_detail(poll_id: int):
    """Get detailed data for a single poll"""
    try:
        stats = excel_manager.get_poll_stats(poll_id)
        if not stats:
            return jsonify({"error": "Poll not found"}), 404

        options_list = [
            {"name": choice, "votes": count}
            for choice, count in stats.get("choices", {}).items()
        ]

        return jsonify({
            "poll_id": poll_id,
            "question": stats.get("question", "Unknown"),
            "options": options_list,
            "total_votes": stats.get("total_votes", 0),
            "voters_by_choice": stats.get("voters_by_choice", {})
        }), 200
    except Exception as e:
        logger.error(f"Error getting poll detail: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api.route('/votes', methods=['GET'])
def get_votes_paginated():
    """Get votes with pagination
    Query params:
        page: Page number (default: 1)
        limit: Items per page (default: 25)
        question: Filter by question
        username: Filter by username
    """
    try:
        votes = excel_manager.get_all_votes()
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
    """Get bot status information"""
    try:
        from .bot import bot, poll_state, start_time

        online = bot is not None and bot.is_ready()

        uptime_str = "N/A"
        if online and start_time:
            elapsed = datetime.now() - start_time
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours}h {minutes}m {seconds}s"

        all_votes = excel_manager.get_all_votes()
        total_votes = len(all_votes)

        today = datetime.now().strftime("%Y-%m-%d")
        votes_today = sum(
            1 for v in all_votes
            if str(v.get("Timestamp", "")).startswith(today)
        )

        return jsonify({
            "online": online,
            "uptime": uptime_str,
            "votes_total": total_votes,
            "votes_today": votes_today,
            "last_command": "N/A",
            "latency_ms": round(bot.latency * 1000, 1) if online and hasattr(bot, "latency") else 0
        }), 200
    except Exception as e:
        logger.error(f"Error getting bot status: {e}", exc_info=True)
        return jsonify({
            "online": False,
            "uptime": "N/A",
            "votes_total": 0,
            "votes_today": 0,
            "last_command": "N/A",
            "latency_ms": 0
        }), 200


@api.route('/polls/stats', methods=['GET'])
def get_poll_stats():
    """Get statistics for a specific poll
    
    Query params:
        poll_id: ID of the poll
    """
    try:
        poll_id = request.args.get('poll_id', type=int)
        
        if not poll_id:
            return jsonify({"error": "poll_id parameter required"}), 400
        
        stats = excel_manager.get_poll_stats(poll_id)
        
        if not stats:
            return jsonify({"error": f"Poll {poll_id} not found"}), 404
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting poll stats: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@api.route('/votes/all', methods=['GET'])
def get_all_votes():
    """Get all votes from the system
    
    Optional query params:
        limit: Max number of records (default: all)
        question: Filter by question
        username: Filter by username
    """
    try:
        votes = excel_manager.get_all_votes()
        
        # Apply filters if provided
        question_filter = request.args.get('question')
        username_filter = request.args.get('username')
        limit = request.args.get('limit', type=int)
        
        if question_filter:
            votes = [v for v in votes if question_filter.lower() in str(v.get('Question', '')).lower()]
        
        if username_filter:
            votes = [v for v in votes if username_filter.lower() in str(v.get('Username', '')).lower()]
        
        if limit:
            votes = votes[-limit:]  # Get last N votes
        
        return jsonify({
            "total": len(votes),
            "votes": votes
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving votes: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@api.route('/votes/by-user/<int:user_id>', methods=['GET'])
def get_user_votes(user_id: int):
    """Get all votes by a specific user"""
    try:
        votes = excel_manager.get_all_votes()
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
    """Get summary statistics grouped by question"""
    try:
        summary = excel_manager.get_summary_by_question()
        
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
    """Export all poll data to CSV"""
    try:
        filepath = excel_manager.export_to_csv()
        
        if not filepath:
            return jsonify({"error": "No data to export"}), 404
        
        return jsonify({
            "success": True,
            "message": "Data exported to CSV",
            "file": filepath
        }), 200
        
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@api.route('/data/status', methods=['GET'])
def get_data_status():
    """Get storage statistics for data health indicator"""
    try:
        all_votes = excel_manager.get_all_votes()
        total_records = len(all_votes)

        last_timestamp = "N/A"
        if total_records > 0:
            timestamps = [v.get('Timestamp', '') for v in all_votes if v.get('Timestamp')]
            if timestamps:
                last_timestamp = max(timestamps)

        file_size = "N/A"
        try:
            fpath = Path(excel_manager.file_path)
            if fpath.exists():
                size_kb = fpath.stat().st_size / 1024
                file_size = f"{size_kb:.1f} KB"
        except Exception:
            pass

        return jsonify({
            "total_records": total_records,
            "last_timestamp": last_timestamp,
            "file_size": file_size,
            "cache_dirty": excel_manager._dirty,
            "status": "healthy"
        }), 200
    except Exception as e:
        logger.error(f"Error getting data status: {e}")
        return jsonify({"error": str(e)}), 500


@api.route('/dashboard/overview', methods=['GET'])
def get_dashboard_overview():
    """Get overview stats for dashboard"""
    try:
        all_votes = excel_manager.get_all_votes()
        summary = excel_manager.get_summary_by_question()
        
        # Calculate metrics with safe conversions
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
