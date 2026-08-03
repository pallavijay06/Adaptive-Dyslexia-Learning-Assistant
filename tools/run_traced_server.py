"""Run the Flask API with runtime tracing attached.

This script must be used instead of running backend/flask_app.py directly
so that tracers are attached before the Flask app registers view functions.
"""
import logging
import sys
from pathlib import Path

# Ensure the `tools` package directory is importable when running this script directly
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import live_trace

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("live_trace_runner")

def main():
    logger.info("Attaching live tracers...")
    try:
        logs = live_trace.attach_tracers()
        logger.info("Attached tracers: %s", list(logs.keys()))
    except Exception:
        logger.exception("Failed to attach tracers")

    logger.info("Importing and starting Flask app...")
    # Import the app AFTER tracers are attached so the wrapped functions are used
    try:
        from backend.flask_app import app
    except Exception:
        logger.exception("Failed to import backend.flask_app")
        sys.exit(1)

    app.run(host="127.0.0.1", port=5000, debug=True)

if __name__ == "__main__":
    main()
