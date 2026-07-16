"""Adaptive Learning Plan and Recommended Learning Path API routes."""

from __future__ import annotations

import logging
import re
from dataclasses import asdict

from flask import Blueprint, jsonify, request

from database.db import get_user_by_id, get_document as get_db_document
from services.document_context import get_document as get_active_document
from services.master_decision_engine import get_adaptive_learning_plan
from services.recommendation_engine import RecommendationEngine
from services.revision_service import generate_revision_notes, RevisionServiceError
from backend.stem.stem_service import analyze_document_for_stem

adaptive_bp = Blueprint("adaptive_plan", __name__, url_prefix="/adaptive-plan")
logger = logging.getLogger(__name__)

# In-memory journey state per user (keyed by user_id).
# Stores: { current_step: int, plan: dict, completed_steps: list[int] }
_journey_state: dict[int, dict] = {}

_STOPWORDS = {
    "about", "after", "again", "against", "all", "also", "an", "and", "any", "are", "as",
    "at", "be", "because", "been", "before", "being", "between", "both", "but", "by", "can",
    "could", "did", "do", "does", "doing", "during", "each", "few", "for", "from", "further",
    "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him", "himself",
    "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more",
    "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or",
    "other", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so",
    "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
    "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "with", "would", "you", "your", "yours", "yourself", "yourselves", "will", "this",
    "these", "those", "their", "there", "here", "when", "where", "while", "though",
}


def _plan_to_dict(plan) -> dict:
    """Convert adaptive-plan objects to JSON-serialisable data."""
    def _convert(obj):
        if hasattr(obj, "__dataclass_fields__"):
            return {k: _convert(getattr(obj, k)) for k in obj.__dataclass_fields__}
        if hasattr(obj, "__dict__") and not isinstance(obj, (str, bytes, int, float, bool)):
            return {k: _convert(v) for k, v in vars(obj).items() if not k.startswith("_")}
        if isinstance(obj, list):
            return [_convert(i) for i in obj]
        if isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        return obj
    return _convert(plan)


def _extract_document_concepts(text: str, limit: int = 8) -> list[str]:
    """Extract a compact set of concepts from document text for adaptive planning."""
    if not text or not text.strip():
        return []

    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []

    candidates: list[str] = []
    for line in cleaned.splitlines():
        line = line.strip()
        if not line:
            continue
        if 1 <= len(line.split()) <= 6 and not line.endswith((".", "!", "?")):
            candidates.extend(re.findall(r"[A-Za-z][A-Za-z0-9'’\-]{2,}", line))
            break

    token_counts: dict[str, int] = {}
    for token in re.findall(r"[A-Za-z][A-Za-z0-9'’\-]{2,}", cleaned):
        lowered = token.lower()
        if lowered in _STOPWORDS or len(token) <= 3:
            continue
        token_counts[lowered] = token_counts.get(lowered, 0) + 1

    ranked_tokens = [token for token, _ in sorted(token_counts.items(), key=lambda item: (-item[1], item[0]))]
    for token in ranked_tokens[:limit]:
        if token not in {c.lower() for c in candidates}:
            candidates.append(token)

    concepts: list[str] = []
    seen: set[str] = set()
    for concept in candidates:
        normalized = " ".join(str(concept).split())
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        concepts.append(normalized.title())

    return concepts[:limit]


def _resolve_document_text(data: dict) -> str | None:
    """Resolve raw document text from the request payload or the current document context."""
    document_id = data.get("document_id")
    record = None

    if document_id is not None:
        try:
            if isinstance(document_id, (int, float)) and not isinstance(document_id, bool):
                record = get_db_document(int(document_id))
            else:
                record = get_active_document(str(document_id))
        except (TypeError, ValueError):
            record = None

    if record is None:
        record = get_active_document()

    if record is None:
        return None

    document_text = getattr(record, "document_text", None)
    if isinstance(document_text, str) and document_text.strip():
        return document_text

    extracted_path = getattr(record, "extracted_path", None)
    if extracted_path:
        try:
            with open(extracted_path, encoding="utf-8") as handle:
                return handle.read()
        except (OSError, UnicodeError):
            return None

    return None


def _resolve_document_concepts(data: dict) -> list[str]:
    """Resolve document concepts from the request payload or the current document context."""
    explicit = data.get("document_concepts") or []
    if isinstance(explicit, list):
        concepts = [str(c).strip() for c in explicit if str(c).strip()]
        if concepts:
            return concepts

    document_id = data.get("document_id")
    record = None

    if document_id is not None:
        try:
            if isinstance(document_id, (int, float)) and not isinstance(document_id, bool):
                record = get_db_document(int(document_id))
            else:
                record = get_active_document(str(document_id))
        except (TypeError, ValueError):
            record = None

    if record is None:
        record = get_active_document()

    if record is None:
        return []

    document_text = getattr(record, "document_text", None)
    if isinstance(document_text, str) and document_text.strip():
        return _extract_document_concepts(document_text)

    extracted_path = getattr(record, "extracted_path", None)
    if extracted_path:
        try:
            with open(extracted_path, encoding="utf-8") as handle:
                return _extract_document_concepts(handle.read())
        except (OSError, UnicodeError):
            return []

    return []


@adaptive_bp.post("/generate")
def generate_plan():
    """Generate an Adaptive Learning Plan for a learner.

    Request JSON:
        user_id (int, required)
        document_concepts (list[str], optional)
        document_id (int | str, optional)
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

    document_concepts = _resolve_document_concepts(data)

    # Detect STEM content using the existing backend STEM service.
    # The frontend never decides whether a document is STEM — the backend does.
    is_stem_document = False
    try:
        doc_text = _resolve_document_text(data)
        if doc_text:
            stem_result = analyze_document_for_stem(doc_text)
            is_stem_document = stem_result.has_formula or stem_result.has_symbols
    except Exception:
        logger.exception("STEM detection failed for user %s — defaulting to non-STEM", user_id)

    try:
        plan = get_adaptive_learning_plan(user_id, document_concepts, is_stem_document=is_stem_document)
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
    user_id = data.get("user_id")
    document_id = data.get("document_id")
    revision_reason = data.get("revision_reason")

    print("[backend] revision-notes endpoint reached")
    print("[backend] request payload", data)
    print("[backend] topics", topics)
    print("[backend] document_id", document_id)
    print("[backend] user_id", user_id)
    print("[backend] revision_reason", revision_reason)

    logger.info(
        "Revision notes request received: user_id=%s document_id=%s topics=%s revision_reason=%s",
        user_id,
        document_id,
        topics,
        revision_reason,
    )

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
