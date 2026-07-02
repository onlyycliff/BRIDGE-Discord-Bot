"""
Bridge 2026 Flask Dashboard
Main entry point for the web interface and API
"""

import logging
from flask import Flask, render_template
import threading
from bridge_bot.bot import start_bot, bot
from bridge_bot.api import api

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask application
dashboard = Flask(__name__, template_folder='templates', static_folder='static')

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

def run_bot_thread():
    """Run Discord bot in background thread"""
    try:
        logger.info("Starting Discord bot...")
        start_bot()
    except Exception as e:
        logger.error(f"Bot error: {e}")

def main():
    """Main entry point"""
    try:
        # Start bot in background daemon thread
        bot_thread = threading.Thread(target=run_bot_thread, daemon=True)
        bot_thread.start()
        logger.info("Bot thread started")
        
        # Start Flask dashboard
        logger.info("Starting Flask dashboard on http://localhost:5000")
        dashboard.run(debug=False, host='localhost', port=5000)
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise













if __name__ == '__main__':
    main()
    