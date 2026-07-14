"""Adaptive Learning Plan and Recommended Learning Path API routes."""

from __future__ import annotations

import logging
from dataclasses import asdict

from flask import Blueprint, jsonify, request

from database.db import get_user_by_id
from services.master_decision_engine import get_adaptive_learning_plan
from services.recommendation_engine import RecommendationEngine
from services.revision_service import generate_revision_notes, RevisionServiceError

adaptive_bp = Blueprint("adaptive_plan", __name__, url_prefix="/adaptive-plan")
logger = logging.getLogger(__name__)

# In-memory journey state per user (keyed by user_id).
# Stores: { current_step: int, plan: dict, completed_steps: list[int] }
_journey_state: dict[int, dict] = {}


def _plan_to_dict(plan) -> dict:
    """Convert AdaptiveLearningPlan dataclass to a JSON-serialisable dict."""
    def _convert(obj):
        if hasattr(obj, "__dataclass_fields__"):
            return {k: _convert(getattr(obj, k)) for k in obj.__dataclass_fields__}
        if isinstance(obj, list):
            return [_convert(i) for i in obj]
        if isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        return obj
    return _convert(plan)


@adaptive_bp.post("/generate")
def generate_plan():
    """Generate an Adaptive Learning Plan for a learner.

    Request JSON:
        user_id (int, required)
        document_concepts (list[str], optional)
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "user_id is required."}), 400

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "user_id must be an integer."}), 400

    if get_user_by_id(user_id) is None:
        return jsonify({"success": False, "error": "User not found."}), 404

    document_concepts = data.get("document_concepts") or []
    if not isinstance(document_concepts, list):
        document_concepts = []

    try:
        plan = get_adaptive_learning_plan(user_id, document_concepts)
        plan_dict = _plan_to_dict(plan)

        # Initialise journey state for this user
        flow = plan_dict.get("adaptive_learning_flow", [])
        _journey_state[user_id] = {
            "current_step": 1,
            "plan": plan_dict,
            "completed_steps": [],
            "total_steps": len(flow),
        }

        return jsonify({"success": True, "plan": plan_dict}), 200
    except Exception:
        logger.exception("Adaptive plan generation failed for user %s", user_id)
        return jsonify({"success": False, "error": "Adaptive plan generation failed."}), 500


@adaptive_bp.get("/current/<int:user_id>")
def current_recommendation(user_id: int):
    """Return the current adaptive learning recommendation for a learner."""
    state = _journey_state.get(user_id)
    if state is None:
        return jsonify({"success": False, "error": "No active plan. Call /adaptive-plan/generate first."}), 404

    flow = state["plan"].get("adaptive_learning_flow", [])
    current_step = state["current_step"]
    current = next((s for s in flow if s.get("step") == current_step), None)

    return jsonify({
        "success": True,
        "current_step": current_step,
        "total_steps": state["total_steps"],
        "step": current,
        "completed_steps": state["completed_steps"],
        "summary": state["plan"].get("decision_summary"),
    }), 200


@adaptive_bp.get("/step/<int:user_id>")
def current_step(user_id: int):
    """Return only the current step details."""
    state = _journey_state.get(user_id)
    if state is None:
        return jsonify({"success": False, "error": "No active plan."}), 404

    flow = state["plan"].get("adaptive_learning_flow", [])
    current = next((s for s in flow if s.get("step") == state["current_step"]), None)
    return jsonify({"success": True, "step": current}), 200


@adaptive_bp.post("/next-step")
def next_step():
    """Advance to the next step in the learning journey."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "user_id is required."}), 400

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "user_id must be an integer."}), 400

    state = _journey_state.get(user_id)
    if state is None:
        return jsonify({"success": False, "error": "No active plan."}), 404

    current = state["current_step"]
    if current not in state["completed_steps"]:
        state["completed_steps"].append(current)

    if current >= state["total_steps"]:
        return jsonify({"success": True, "journey_complete": True, "message": "All steps completed."}), 200

    state["current_step"] = current + 1
    flow = state["plan"].get("adaptive_learning_flow", [])
    next_step_data = next((s for s in flow if s.get("step") == state["current_step"]), None)
    return jsonify({"success": True, "journey_complete": False, "step": next_step_data}), 200


@adaptive_bp.post("/complete-step")
def complete_step():
    """Mark a specific step as completed."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    step_number = data.get("step")

    if not user_id or step_number is None:
        return jsonify({"success": False, "error": "user_id and step are required."}), 400

    try:
        user_id = int(user_id)
        step_number = int(step_number)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "user_id and step must be integers."}), 400

    state = _journey_state.get(user_id)
    if state is None:
        return jsonify({"success": False, "error": "No active plan."}), 404

    if step_number not in state["completed_steps"]:
        state["completed_steps"].append(step_number)

    return jsonify({
        "success": True,
        "completed_steps": state["completed_steps"],
        "total_steps": state["total_steps"],
    }), 200


@adaptive_bp.post("/resume")
def resume_journey():
    """Resume an existing learning journey or start a new one."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "user_id is required."}), 400

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "user_id must be an integer."}), 400

    state = _journey_state.get(user_id)
    if state is None:
        return jsonify({"success": False, "error": "No active plan. Call /adaptive-plan/generate first."}), 404

    flow = state["plan"].get("adaptive_learning_flow", [])
    current = next((s for s in flow if s.get("step") == state["current_step"]), None)
    return jsonify({
        "success": True,
        "current_step": state["current_step"],
        "total_steps": state["total_steps"],
        "step": current,
        "completed_steps": state["completed_steps"],
    }), 200


@adaptive_bp.get("/journey-complete/<int:user_id>")
def journey_complete(user_id: int):
    """Check whether the learner has completed all journey steps."""
    state = _journey_state.get(user_id)
    if state is None:
        return jsonify({"success": True, "complete": False, "reason": "No active plan."}), 200

    complete = len(state["completed_steps"]) >= state["total_steps"]
    return jsonify({"success": True, "complete": complete, "completed_steps": state["completed_steps"]}), 200


@adaptive_bp.post("/revision-notes")
def revision_notes():
    """Generate dyslexia-friendly revision notes for a list of topics.

    Request JSON:
        revision_topics (list[str], required)  — topics to revise

    The topics are supplied by the frontend from the revision step's
    ``revision_topics`` field, which was populated by the Understanding
    Decision Engine and carried forward by the Master Decision Engine.
    All adaptive decisions are made in the backend; this endpoint only
    generates the LLM output.
    """
    data = request.get_json(silent=True) or {}
    topics = data.get("revision_topics")

    if not topics or not isinstance(topics, list):
        return jsonify({"success": False, "error": "revision_topics must be a non-empty list."}), 400

    topics = [str(t).strip() for t in topics if str(t).strip()]
    if not topics:
        return jsonify({"success": False, "error": "revision_topics contains no valid topic names."}), 400

    try:
        notes = generate_revision_notes(topics)
        return jsonify({"success": True, "revision_notes": notes, "topics": topics}), 200
    except RevisionServiceError as exc:
        logger.error("Revision note generation failed: %s", exc)
        return jsonify({"success": False, "error": "Revision note generation failed. Please try again."}), 500
    except Exception:
        logger.exception("Unexpected error in revision_notes endpoint")
        return jsonify({"success": False, "error": "An unexpected error occurred."}), 500


@adaptive_bp.get("/learning-path/<int:user_id>")
def learning_path(user_id: int):
    """Return the full recommended learning path for a learner."""
    state = _journey_state.get(user_id)
    if state is None:
        return jsonify({"success": False, "error": "No active plan. Call /adaptive-plan/generate first."}), 404

    return jsonify({
        "success": True,
        "learning_path": state["plan"].get("adaptive_learning_flow", []),
        "summary": state["plan"].get("decision_summary"),
        "current_step": state["current_step"],
        "completed_steps": state["completed_steps"],
    }), 200
