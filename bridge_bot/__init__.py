# Bridge Bot Package Initialization
# Exports main components for dashboard integration

from bridge_bot.bot import bot, send_poll, start_bot, poll_state
from bridge_bot.excel_manager import excel_manager, ExcelDataManager
from bridge_bot.colab_integration import colab_integration, ColabIntegration
from bridge_bot.api import api

__all__ = [
    'bot',
    'send_poll',
    'start_bot',
    'poll_state',
    'excel_manager',
    'ExcelDataManager',
    'colab_integration',
    'ColabIntegration',
    'api'
]
