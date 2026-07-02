"""
Bridge 2026 Flask Dashboard
Main entry point for the web interface and API
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import logging
from flask import Flask, render_template
import os
import threading
from bridge_bot.bot import start_bot, bot
from bridge_bot.api import api

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_bot_thread():
    """Run Discord bot in background thread"""
    try:
        logger.info("Starting Discord bot...")
        start_bot()
    except Exception as e:
        logger.error(f"Bot error: {e}")

# Initialize Flask application
app = Flask(__name__, template_folder='templates', static_folder='static')
dashboard = app

# Auto-start bot thread on import (for gunicorn/Railway)
_bot_started = False
def _ensure_bot_started():
    global _bot_started
    if not _bot_started:
        _bot_started = True
        thread = threading.Thread(target=run_bot_thread, daemon=True)
        thread.start()
        logger.info("Bot thread auto-started")

_ensure_bot_started()

# Register API blueprint
dashboard.register_blueprint(api)

@dashboard.route('/')
def home():
    """Serve main dashboard page"""
    try:
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return f"Error loading dashboard: {e}", 500

@dashboard.route('/create-poll')
def create_poll_page():
    """Serve poll creation page"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error loading poll creation page: {e}")
        return f"Error loading page: {e}", 500

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
    
