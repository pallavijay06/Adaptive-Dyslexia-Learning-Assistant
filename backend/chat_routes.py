"""Chat API routes for the cHEAL backend with Adaptive AI Tutor integration."""

from __future__ import annotations

import json
import logging
from typing import Optional

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
from database.db import save_chat, save_user, get_user, get_user_by_id
from services.adaptive_tutor import AdaptiveAITutor
from services.learner_profile_service import LearnerProfileService

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__)


def _resolve_user_id(user_id_from_request: Optional[int] = None) -> int:
    """Resolve a user id for chat storage.
    
    Priority:
    1. Explicit user_id in request
    2. Fallback to anonymous account
    
    Args:
        user_id_from_request: Optional user ID from request.
        
    Returns:
        The user ID to use.
    """
    if user_id_from_request:
        user = get_user_by_id(user_id_from_request)
        if user:
            return user.id
    
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
    """Handle a single chat turn with adaptive tutor personalization.
    
    Now tracks learner behavior, maintains adaptive profiles, and provides
    personalized recommendations based on learning history.
    """
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    document_id = payload.get("document_id")
    document_text = payload.get("document_text")
    user_id_from_request = payload.get("user_id")
    topic = payload.get("topic")  # Optional topic context
    document_id_for_db = None

    if document_id is not None:
        try:
            document_id_for_db = int(document_id)
        except (TypeError, ValueError):
            return jsonify({"error": "document_id must be an integer."}), 400

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    try:
        # Resolve user ID with support for authenticated users
        user_id = _resolve_user_id(user_id_from_request)
        
        # Initialize adaptive tutor for this user
        tutor = AdaptiveAITutor(user_id, document_id=document_id_for_db)
        
        # Prepare adaptive context for the response
        adaptive_context = tutor.prepare_response_context(topic=topic)
        
        # Track the question interaction
        tutor.track_interaction(
            interaction_type="question",
            topic=topic,
            duration_seconds=0,
            session_id=None,
        )
        
        # Generate response using existing RAG system
        response = ask_document(
            message,
            document_id=document_id,
            document_text=document_text,
        )
        
        # Save chat to database
        saved_chat = save_chat(
            user_id=user_id,
            document_id=document_id_for_db,
            user_message=message,
            ai_response=response,
        )
        
        logger.info(
            "Chat saved with adaptive tutor: id=%s, user_id=%s, document_id=%s, topic=%s",
            saved_chat.id,
            saved_chat.user_id,
            saved_chat.document_id,
            topic,
        )
        
        # Get adaptive recommendations for this interaction
        recommendations = []
        
        # Check if we should recommend a learning mode
        mode_suggestion = tutor.should_recommend_mode()
        if mode_suggestion:
            recommendations.append({
                "type": "mode_suggestion",
                "message": f"Would you like a {mode_suggestion} explanation?",
                "mode": mode_suggestion,
            })
        
        # Check if we should recommend practice
        practice_suggestion = tutor.should_recommend_practice()
        if practice_suggestion:
            recommendations.append({
                "type": "practice_suggestion",
                "message": practice_suggestion.get("recommendation", ""),
            })
        
        # Get adjustment suggestion if needed
        adjustment = tutor.get_adjustment_suggestion()
        if adjustment:
            recommendations.append({
                "type": "adjustment_suggestion",
                "message": adjustment.get("reason", ""),
                "suggested": adjustment.get("suggested", ""),
            })
        
        # Return response with adaptive data
        return jsonify({
            "response": response,
            "adaptive": {
                "context": adaptive_context,
                "recommendations": recommendations,
                "learner_profile": {
                    "explanation_complexity": tutor.profile.explanation_complexity,
                    "preferred_mode": tutor.profile.preferred_learning_mode,
                    "confidence_level": round(tutor.profile.confidence_level, 2),
                },
            },
        }), 200
        
    except DocumentError as exc:
        return jsonify({"error": str(exc)}), 400
    except LLMRouterError as exc:
        return jsonify({"error": str(exc)}), 502
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as e:
        logger.exception("Unexpected error in chat endpoint: %s", str(e))
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


# ==================== Adaptive Tutor Endpoints ====================


@chat_bp.post("/adaptive/record-quiz")
def record_quiz_attempt() -> tuple[object, int]:
    """Record a quiz attempt and update learner profile."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    topic = payload.get("topic")
    score = payload.get("score")  # 0-100
    total_questions = payload.get("total_questions", 10)
    session_id = payload.get("session_id")

    if not user_id or not topic or score is None:
        return jsonify({"error": "Missing required fields: user_id, topic, score."}), 400

    try:
        tutor = AdaptiveAITutor(user_id)
        tutor.record_quiz_attempt(
            topic=topic,
            score=float(score),
            total_questions=int(total_questions),
            session_id=session_id,
        )
        
        logger.info("Recorded quiz attempt for user %s on topic %s with score %.1f", user_id, topic, score)
        
        return jsonify({
            "success": True,
            "message": f"Quiz recorded. Your score: {score}%",
            "profile_update": LearnerProfileService.get_profile_summary(user_id),
        }), 200
    except Exception as e:
        logger.exception("Error recording quiz: %s", str(e))
        return jsonify({"error": str(e)}), 500


@chat_bp.post("/adaptive/track-mode")
def track_learning_mode() -> tuple[object, int]:
    """Track usage of a specific learning mode."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    mode = payload.get("mode")  # e.g., 'Audio', 'Visual', 'Simplified Notes', 'Quiz'
    session_id = payload.get("session_id")

    if not user_id or not mode:
        return jsonify({"error": "Missing required fields: user_id, mode."}), 400

    try:
        tutor = AdaptiveAITutor(user_id)
        tutor.track_interaction(
            interaction_type=mode,
            session_id=session_id,
        )
        
        logger.info("Tracked %s mode usage for user %s", mode, user_id)
        
        return jsonify({"success": True, "message": f"Tracked {mode} usage."}), 200
    except Exception as e:
        logger.exception("Error tracking mode: %s", str(e))
        return jsonify({"error": str(e)}), 500


@chat_bp.post("/adaptive/record-concept")
def record_concept_question() -> tuple[object, int]:
    """Record a question about a specific concept."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    topic = payload.get("topic")
    concept = payload.get("concept")
    is_correct = payload.get("is_correct", False)

    if not user_id or not topic or not concept:
        return jsonify({"error": "Missing required fields: user_id, topic, concept."}), 400

    try:
        tutor = AdaptiveAITutor(user_id)
        tutor.record_concept_question(
            topic=topic,
            concept=concept,
            is_correct=bool(is_correct),
        )
        
        logger.info("Recorded concept question for user %s: %s/%s", user_id, topic, concept)
        
        return jsonify({"success": True, "message": "Concept recorded."}), 200
    except Exception as e:
        logger.exception("Error recording concept: %s", str(e))
        return jsonify({"error": str(e)}), 500


@chat_bp.post("/adaptive/track-document")
def track_document_upload() -> tuple[object, int]:
    """Track document upload."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    session_id = payload.get("session_id")

    if not user_id:
        return jsonify({"error": "Missing required field: user_id."}), 400

    try:
        tutor = AdaptiveAITutor(user_id)
        tutor.track_interaction(
            interaction_type="upload",
            session_id=session_id,
        )
        
        logger.info("Tracked document upload for user %s", user_id)
        
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.exception("Error tracking document upload: %s", str(e))
        return jsonify({"error": str(e)}), 500


@chat_bp.get("/adaptive/profile/<int:user_id>")
def get_learner_profile(user_id: int) -> tuple[object, int]:
    """Get the learner profile summary for a user."""
    try:
        tutor = AdaptiveAITutor(user_id)
        summary = tutor.get_learner_summary()
        
        return jsonify(summary), 200
    except Exception as e:
        logger.exception("Error getting learner profile: %s", str(e))
        return jsonify({"error": str(e)}), 500


@chat_bp.get("/adaptive/recommendations/<int:user_id>")
def get_recommendations(user_id: int) -> tuple[object, int]:
    """Get personalized recommendations for a user."""
    try:
        tutor = AdaptiveAITutor(user_id)
        recommendations = tutor.get_adaptive_recommendations()
        
        return jsonify({
            "recommendations": recommendations,
            "greeting": tutor.get_session_greeting(),
        }), 200
    except Exception as e:
        logger.exception("Error getting recommendations: %s", str(e))
        return jsonify({"error": str(e)}), 500


@chat_bp.post("/adaptive/initialize-profile")
def initialize_learner_profile() -> tuple[object, int]:
    """Initialize a learner profile for a new or existing user."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")

    if not user_id:
        return jsonify({"error": "Missing required field: user_id."}), 400

    try:
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found."}), 404
        
        profile = LearnerProfileService.initialize_profile(user)
        
        logger.info("Initialized learner profile for user %s", user_id)
        
        return jsonify({
            "success": True,
            "profile": LearnerProfileService.get_profile_summary(user_id),
        }), 200
    except Exception as e:
        logger.exception("Error initializing profile: %s", str(e))
        return jsonify({"error": str(e)}), 500
