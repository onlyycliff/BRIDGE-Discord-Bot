# Bridge Bot Package Initialization
# Exports main components for dashboard integration

from .excel_manager import excel_manager, ExcelDataManager
from .colab_integration import colab_integration, ColabIntegration

__all__ = [
    'excel_manager',
    'ExcelDataManager',
    'colab_integration',
    'ColabIntegration'
]
