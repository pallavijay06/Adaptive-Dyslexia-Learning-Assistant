"""Chat API routes for the cHEAL backend."""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from services.document_context import DocumentError, get_document_text
from services.llm_router import (
    LLMRouterError,
    extract_vocabulary,
    generate_quiz,
    simplify_document,
    summarize_document,
)
from backend.rag import ask_document
from database.db import save_chat, save_user, get_user

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__)


def _resolve_user_id() -> int:
    """Resolve a user id for chat storage using a fallback anonymous account."""
    user = get_user("anonymous@cheal.local")
    if user is not None:
        return user.id  # type: ignore[index]

    anonymous = save_user(
        name="Anonymous Learner",
        email="anonymous@cheal.local",
        password_hash="",
    )
    return anonymous.id  # type: ignore[index]


@chat_bp.post("/chat")
def chat() -> tuple[object, int]:
    """Handle a single chat turn and persist the conversation."""
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    document_id = payload.get("document_id")
    document_text = payload.get("document_text")
    document_id_for_db = None

    if document_id is not None:
        try:
            document_id_for_db = int(document_id)
        except (TypeError, ValueError):
            return jsonify({"error": "document_id must be an integer."}), 400

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    try:
        response = ask_document(
            message,
            document_id=document_id,
            document_text=document_text,
        )
        user_id = _resolve_user_id()
        saved_chat = save_chat(
            user_id=user_id,
            document_id=document_id_for_db,
            user_message=message,
            ai_response=response,
        )
        logger.info(
            "Chat saved to database: id=%s, user_id=%s, document_id=%s",
            saved_chat.id,
            saved_chat.user_id,
            saved_chat.document_id,
        )
        return jsonify({"response": response}), 200
    except DocumentError as exc:
        return jsonify({"error": str(exc)}), 400
    except LLMRouterError as exc:
        return jsonify({"error": str(exc)}), 502
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Unexpected server error."}), 500


@chat_bp.post("/document/summarize")
def summarize_active_document() -> tuple[object, int]:
    """Summarize the active or requested document."""
    return _run_document_action(summarize_document)


@chat_bp.post("/document/simplify")
def simplify_active_document() -> tuple[object, int]:
    """Simplify the active or requested document."""
    return _run_document_action(simplify_document)


@chat_bp.post("/document/quiz")
def quiz_active_document() -> tuple[object, int]:
    """Generate a quiz from the active or requested document."""
    return _run_document_action(generate_quiz)


@chat_bp.post("/document/vocabulary")
def vocabulary_active_document() -> tuple[object, int]:
    """Extract vocabulary from the active or requested document."""
    return _run_document_action(extract_vocabulary)


def _run_document_action(action) -> tuple[object, int]:
    payload = request.get_json(silent=True) or {}
    document_id = payload.get("document_id")

    try:
        document_text = get_document_text(document_id)
        if not document_text:
            return jsonify({"error": "Upload a document before using this action."}), 400
        return jsonify({"response": action(document_text)}), 200
    except DocumentError as exc:
        return jsonify({"error": str(exc)}), 400
    except LLMRouterError as exc:
        return jsonify({"error": str(exc)}), 502
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Unexpected server error."}), 500
