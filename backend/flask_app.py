"""Flask API entry point — complete API-first backend for React migration.

The Streamlit interface lives in the project-level app.py and is unaffected.
This module registers every blueprint so all backend features are reachable
through HTTP APIs.
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory, abort

from backend.chat_routes import chat_bp
from backend.quiz_routes import quiz_bp
from backend.upload_routes import upload_bp
from backend.learning_routes import learning_bp
from backend.auth_routes import auth_bp
from backend.dashboard_routes import dashboard_bp
from backend.stem_routes import stem_bp
from backend.adaptive_routes import adaptive_bp
from backend.tracking_routes import tracking_bp
from backend.document_routes import document_bp
from database import init_db

# Absolute project root so static-file routes resolve correctly regardless
# of the working directory from which the server is started.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_AUDIO_DIR = _PROJECT_ROOT / "generated_audio"
_DIAGRAMS_DIR = _PROJECT_ROOT / "generated_diagrams"


def create_app() -> Flask:
    """Create and configure the Flask app."""

    app = Flask(__name__)

    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
    # A secret key is required for Flask session support (auth_routes).
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "cheal-dev-secret-change-in-prod")

    # Initialize database on startup so tables exist before requests arrive.
    init_db()

    # ── Existing blueprints (unchanged) ──────────────────────────────────────
    app.register_blueprint(chat_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(learning_bp)
    app.register_blueprint(quiz_bp)

    # ── New API-completion blueprints ─────────────────────────────────────────
    app.register_blueprint(auth_bp)        # /auth/*
    app.register_blueprint(dashboard_bp)   # /dashboard/*
    app.register_blueprint(stem_bp)        # /stem/*
    app.register_blueprint(adaptive_bp)    # /adaptive-plan/*
    app.register_blueprint(tracking_bp)    # /track/*
    app.register_blueprint(document_bp)    # /document/<id>/*  /quiz/hint  /vocabulary/explain

    # ── Static asset serving ──────────────────────────────────────────────────

    @app.get("/audio/<path:filename>")
    def serve_audio(filename: str):
        """Serve a generated MP3 audio file by name."""
        safe = Path(filename).name  # strip any directory traversal
        if not (_AUDIO_DIR / safe).is_file():
            abort(404)
        return send_from_directory(str(_AUDIO_DIR), safe, mimetype="audio/mpeg")

    @app.get("/diagrams/<path:filename>")
    def serve_diagram(filename: str):
        """Serve a generated diagram/image file by name."""
        safe = Path(filename).name
        if not (_DIAGRAMS_DIR / safe).is_file():
            abort(404)
        suffix = Path(safe).suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/jpeg"
        return send_from_directory(str(_DIAGRAMS_DIR), safe, mimetype=mime)

    # ── Health check ──────────────────────────────────────────────────────────

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
