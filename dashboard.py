"""
Bridge 2026 Flask Dashboard
Main entry point for the web interface and API
"""

import os
import sys
import logging
import threading
from pathlib import Path

_BRIDGE_BOT_DIR = str(Path(__file__).resolve().parent / 'bridge_bot')
if _BRIDGE_BOT_DIR not in sys.path:
    sys.path.insert(0, _BRIDGE_BOT_DIR)

from flask import Flask, jsonify
from flask_cors import CORS
from bot import start_bot, bot
from api import api

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
dashboard = app

cors_origin = os.getenv("CORS_ORIGIN", "http://localhost:5173")
CORS(dashboard, resources={r"/api/*": {"origins": cors_origin}})
logger.info(f"CORS configured for origin: {cors_origin}")

_bot_started = False
_bot_thread_lock = threading.Lock()

def run_bot_thread():
    try:
        logger.info("Starting Discord bot...")
        start_bot()
    except Exception as e:
        logger.error(f"Bot error: {e}")

def _ensure_bot_started():
    global _bot_started
    if _bot_started:
        return
    with _bot_thread_lock:
        if _bot_started:
            return
        _bot_started = True
        thread = threading.Thread(target=run_bot_thread, daemon=True)
        thread.start()
        logger.info("Bot thread auto-started")

_ensure_bot_started()

dashboard.register_blueprint(api)

@dashboard.route('/')
def home():
    """API root — returns service info"""
    return jsonify({
        "service": "Bridge 2026 Dashboard API",
        "version": "2.0.0",
        "docs": "/api/health",
        "frontend": os.getenv("FRONTEND_URL", "http://localhost:5173")
    })

@dashboard.route('/create-poll')
def create_poll_redirect():
    """Informational — poll creation is at POST /api/polls/create"""
    return jsonify({
        "message": "Use POST /api/polls/create to create a poll",
        "docs": "/api/health"
    })

@dashboard.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 error: {error}")
    return {"error": "Endpoint not found"}, 404

@dashboard.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    logger.error(f"500 error: {error}")
    return {"error": "Internal server error"}, 500

def main():
    """Main entry point"""
    try:
        _ensure_bot_started()
        port = int(os.getenv('PORT', 5000))
        logger.info(f"Starting Flask dashboard on http://0.0.0.0:{port}")
        app.run(debug=False, host='0.0.0.0', port=port)
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

if __name__ == '__main__':
    main()
    
