"""
WSGI entry point for Railway/gunicorn.
Ensures the project root is on sys.path before importing the app.
"""
import sys
from pathlib import Path
_root = str(Path(__file__).parent.resolve())
if _root not in sys.path:
    sys.path.insert(0, _root)

# Now import the Flask app (this triggers bridge_bot imports with the path set)
from dashboard import app
