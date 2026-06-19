"""Flask API entry point kept for backend/API use.

The Streamlit interface now lives in the project-level app.py so it can be run
with `streamlit run app.py`. This module preserves the existing Flask backend.
"""

from __future__ import annotations

from flask import Flask, jsonify

from backend.chat_routes import chat_bp
from backend.quiz_routes import quiz_bp
from backend.upload_routes import upload_bp
from backend.learning_routes import learning_bp
from database import init_db
from backend.quiz_routes import quiz_bp

from database import init_db


def create_app() -> Flask:
    """Create and configure the Flask app."""

    app = Flask(__name__)

    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

    # Initialize database on startup so tables exist before requests arrive.
    init_db()

    # Register blueprints
    app.register_blueprint(chat_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(learning_bp)
    app.register_blueprint(quiz_bp)

    @app.get("/health")
    def health() -> tuple[object, int]:
        """Simple health check used to confirm the backend is running."""
        return jsonify({"status": "ok"}), 200

    return app


app = create_app()


if __name__ == "__main__":
    print("[cHEAL] LLM provider order: OpenAI -> Gemini -> Ollama")
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )