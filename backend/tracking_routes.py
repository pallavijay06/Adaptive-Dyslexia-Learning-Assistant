"""Tracking API routes — exposes all behaviour and progress tracking services."""

from __future__ import annotations

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from services.behavior_tracking_service import (
    track_event,
    track_document_opened,
    track_mode_entered,
    track_mode_exited,
    track_mode_switched,
    track_audio_started,
    track_audio_completed,
    track_audio_played,
    track_audio_paused,
    track_audio_replayed,
    track_visual_viewed,
    track_ai_tutor_used,
    track_ai_tutor_opened,
    track_quiz_started,
    track_quiz_completed,
    track_formula_assistant_used,
    track_symbol_explanation_used,
    track_diagram_explanation_used,
    track_step_solver_used,
    track_explanation_requested,
    track_hint_requested,
    track_quiz_retry,
    track_response_time,
    track_simplify_clicked,
    track_vocabulary_clicked,
    track_session_completed,
    SUPPORTED_EVENT_TYPES,
)
from database.db import save_learning_session, save_learning_history

tracking_bp = Blueprint("tracking", __name__, url_prefix="/track")
logger = logging.getLogger(__name__)


def _require_user_id(data: dict):
    uid = data.get("user_id")
    if uid is None:
        return None, (jsonify({"success": False, "error": "user_id is required."}), 400)
    try:
        return int(uid), None
    except (TypeError, ValueError):
        return None, (jsonify({"success": False, "error": "user_id must be an integer."}), 400)


def _parse_ts(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Generic event endpoint
# ---------------------------------------------------------------------------

@tracking_bp.post("/event")
def track_generic_event():
    """Record any supported behaviour event.

    Request JSON:
        user_id (int, required)
        event_type (str, required) — must be in SUPPORTED_EVENT_TYPES
        session_id (int, optional)
        metadata (dict, optional)
        event_timestamp (str ISO-8601, optional)
    """
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err

    event_type = (data.get("event_type") or "").strip().upper()
    if not event_type:
        return jsonify({"success": False, "error": "event_type is required."}), 400

    session_id = data.get("session_id")
    metadata = data.get("metadata") or {}
    ts = _parse_ts(data.get("event_timestamp"))

    try:
        record = track_event(
            user_id=user_id,
            event_type=event_type,
            session_id=int(session_id) if session_id is not None else None,
            metadata=metadata,
            event_timestamp=ts,
        )
        return jsonify({"success": True, "event_id": record.id if record else None}), 200
    except Exception:
        logger.exception("Generic event tracking failed")
        return jsonify({"success": False, "error": "Event tracking failed."}), 500


# ---------------------------------------------------------------------------
# Document tracking
# ---------------------------------------------------------------------------

@tracking_bp.post("/document-opened")
def track_doc_opened():
    """Record that a learner opened a document and start a learning session."""
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err

    metadata = data.get("metadata") or {}
    if data.get("document_id"):
        metadata.setdefault("document_id", data["document_id"])
    if data.get("file_name"):
        metadata.setdefault("file_name", data["file_name"])

    try:
        record = track_document_opened(user_id=user_id, metadata=metadata)
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        logger.exception("Document opened tracking failed")
        return jsonify({"success": False, "error": "Tracking failed."}), 500


# ---------------------------------------------------------------------------
# Learning mode tracking
# ---------------------------------------------------------------------------

@tracking_bp.post("/mode-entered")
def track_mode_enter():
    """Record that a learner entered a learning mode.

    Request JSON:
        user_id (int, required)
        mode (str, required) — e.g. "Read", "Listen", "Visual", "Quiz", "AI Tutor"
        document_id (int, optional)
        previous_mode (str, optional)
        session_id (int, optional)
        event_timestamp (str, optional)
    """
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err

    mode = (data.get("mode") or "").strip()
    if not mode:
        return jsonify({"success": False, "error": "mode is required."}), 400

    try:
        record = track_mode_entered(
            user_id=user_id,
            mode=mode,
            session_id=data.get("session_id"),
            document_id=data.get("document_id"),
            previous_mode=data.get("previous_mode"),
            event_timestamp=_parse_ts(data.get("event_timestamp")),
        )
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        logger.exception("Mode entered tracking failed")
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/mode-exited")
def track_mode_exit():
    """Record that a learner exited a learning mode.

    Request JSON:
        user_id (int, required)
        mode (str, required)
        entered_at (str ISO-8601, required)
        exited_at (str ISO-8601, optional — defaults to now)
        document_id (int, optional)
        next_mode (str, optional)
        session_id (int, optional)
    """
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err

    mode = (data.get("mode") or "").strip()
    entered_at = _parse_ts(data.get("entered_at"))
    if not mode or not entered_at:
        return jsonify({"success": False, "error": "mode and entered_at are required."}), 400

    try:
        record = track_mode_exited(
            user_id=user_id,
            mode=mode,
            entered_at=entered_at,
            exited_at=_parse_ts(data.get("exited_at")),
            session_id=data.get("session_id"),
            document_id=data.get("document_id"),
            next_mode=data.get("next_mode"),
        )
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        logger.exception("Mode exited tracking failed")
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/mode-switched")
def track_mode_switch():
    """Record an explicit mode transition."""
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err

    previous_mode = (data.get("previous_mode") or "").strip()
    mode = (data.get("mode") or "").strip()
    if not previous_mode or not mode:
        return jsonify({"success": False, "error": "previous_mode and mode are required."}), 400

    try:
        record = track_mode_switched(
            user_id=user_id,
            previous_mode=previous_mode,
            mode=mode,
            session_id=data.get("session_id"),
            document_id=data.get("document_id"),
            event_timestamp=_parse_ts(data.get("event_timestamp")),
        )
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        logger.exception("Mode switched tracking failed")
        return jsonify({"success": False, "error": "Tracking failed."}), 500


# ---------------------------------------------------------------------------
# Audio tracking
# ---------------------------------------------------------------------------

@tracking_bp.post("/audio-started")
def audio_started():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_audio_started(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/audio-completed")
def audio_completed():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_audio_completed(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/audio-played")
def audio_played():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_audio_played(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/audio-paused")
def audio_paused():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_audio_paused(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/audio-replayed")
def audio_replayed():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_audio_replayed(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


# ---------------------------------------------------------------------------
# Visual / AI Tutor tracking
# ---------------------------------------------------------------------------

@tracking_bp.post("/visual-viewed")
def visual_viewed():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_visual_viewed(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/ai-tutor-used")
def ai_tutor_used():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_ai_tutor_used(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/ai-tutor-opened")
def ai_tutor_opened():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_ai_tutor_opened(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


# ---------------------------------------------------------------------------
# Quiz tracking
# ---------------------------------------------------------------------------

@tracking_bp.post("/quiz-started")
def quiz_started():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_quiz_started(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/quiz-completed")
def quiz_completed():
    """Record quiz completion with optional score metadata."""
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err

    metadata = data.get("metadata") or {}
    for key in ("score", "quiz_accuracy", "topic", "document_id"):
        if data.get(key) is not None:
            metadata.setdefault(key, data[key])

    try:
        record = track_quiz_completed(user_id=user_id, metadata=metadata)
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/quiz-retry")
def quiz_retry():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_quiz_retry(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


# ---------------------------------------------------------------------------
# STEM feature tracking
# ---------------------------------------------------------------------------

@tracking_bp.post("/formula-used")
def formula_used():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_formula_assistant_used(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/symbol-used")
def symbol_used():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_symbol_explanation_used(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/diagram-used")
def diagram_used():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_diagram_explanation_used(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/step-solver-used")
def step_solver_used():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_step_solver_used(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


# ---------------------------------------------------------------------------
# Read-mode feature tracking
# ---------------------------------------------------------------------------

@tracking_bp.post("/simplify-clicked")
def simplify_clicked():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_simplify_clicked(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/vocabulary-clicked")
def vocabulary_clicked():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_vocabulary_clicked(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/explanation-requested")
def explanation_requested():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_explanation_requested(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/hint-requested")
def hint_requested():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_hint_requested(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/response-time")
def response_time():
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err
    try:
        record = track_response_time(user_id=user_id, metadata=data.get("metadata"))
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        return jsonify({"success": False, "error": "Tracking failed."}), 500


# ---------------------------------------------------------------------------
# Learning session tracking
# ---------------------------------------------------------------------------

@tracking_bp.post("/session-completed")
def session_completed():
    """Record that a document learning session ended.

    Request JSON:
        user_id (int, required)
        session_start (str ISO-8601, optional)
        session_end (str ISO-8601, optional)
        duration_minutes (float, optional)
        document_id (int, optional)
        document_name (str, optional)
        completed (bool, optional)
        session_uuid (str, optional)
    """
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err

    try:
        record = track_session_completed(
            user_id=user_id,
            session_start=_parse_ts(data.get("session_start")),
            session_end=_parse_ts(data.get("session_end")),
            duration_minutes=data.get("duration_minutes"),
            document_id=data.get("document_id"),
            document_name=data.get("document_name"),
            completed=bool(data.get("completed", False)),
            session_uuid=data.get("session_uuid"),
        )
        return jsonify({"success": True, "event_id": record.id}), 200
    except Exception:
        logger.exception("Session completed tracking failed")
        return jsonify({"success": False, "error": "Tracking failed."}), 500


@tracking_bp.post("/learning-session")
def save_learning_session_route():
    """Persist a learning session record (mode + duration).

    Request JSON:
        user_id (int, required)
        mode_used (str, required)
        duration (int, required) — minutes
        login_time (str ISO-8601, optional)
        logout_time (str ISO-8601, optional)
    """
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err

    mode_used = (data.get("mode_used") or "").strip()
    duration = data.get("duration")
    if not mode_used or duration is None:
        return jsonify({"success": False, "error": "mode_used and duration are required."}), 400

    try:
        record = save_learning_session(
            user_id=user_id,
            mode_used=mode_used,
            duration=int(duration),
            login_time=_parse_ts(data.get("login_time")),
            logout_time=_parse_ts(data.get("logout_time")),
        )
        return jsonify({"success": True, "session_id": record.id}), 200
    except Exception:
        logger.exception("Learning session save failed")
        return jsonify({"success": False, "error": "Session save failed."}), 500


@tracking_bp.post("/learning-history")
def save_learning_history_route():
    """Persist a learning history activity record.

    Request JSON:
        user_id (int, required)
        activity_type (str, required)
        topic (str, optional)
        session_id (int, optional)
        duration_seconds (int, optional)
    """
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err

    activity_type = (data.get("activity_type") or "").strip()
    if not activity_type:
        return jsonify({"success": False, "error": "activity_type is required."}), 400

    try:
        record = save_learning_history(
            user_id=user_id,
            activity_type=activity_type,
            topic=data.get("topic"),
            session_id=data.get("session_id"),
            duration_seconds=int(data.get("duration_seconds") or 0),
        )
        return jsonify({"success": True, "history_id": record.id}), 200
    except Exception:
        logger.exception("Learning history save failed")
        return jsonify({"success": False, "error": "History save failed."}), 500


# ---------------------------------------------------------------------------
# Journey step completion
# ---------------------------------------------------------------------------

@tracking_bp.post("/journey-step")
def journey_step_completed():
    """Record that a learner completed a journey step.

    Delegates to the generic event tracker with QUIZ_COMPLETED or MODE_ENTERED
    depending on the step action, and also fires a behaviour event.

    Request JSON:
        user_id (int, required)
        step (int, required)
        action (str, required) — e.g. "learning_mode", "quiz", "revision"
        mode (str, optional)
        document_id (int, optional)
    """
    data = request.get_json(silent=True) or {}
    user_id, err = _require_user_id(data)
    if err:
        return err

    step = data.get("step")
    action = (data.get("action") or "").strip()
    if step is None or not action:
        return jsonify({"success": False, "error": "step and action are required."}), 400

    metadata = {
        "step": step,
        "action": action,
        "mode": data.get("mode"),
        "document_id": data.get("document_id"),
    }

    event_type = "QUIZ_COMPLETED" if action == "quiz" else "MODE_ENTERED"
    try:
        record = track_event(user_id=user_id, event_type=event_type, metadata=metadata)
        return jsonify({"success": True, "event_id": record.id if record else None}), 200
    except Exception:
        logger.exception("Journey step tracking failed")
        return jsonify({"success": False, "error": "Tracking failed."}), 500


# ---------------------------------------------------------------------------
# Supported event types reference
# ---------------------------------------------------------------------------

@tracking_bp.get("/event-types")
def list_event_types():
    """Return all supported behaviour event type names."""
    return jsonify({"success": True, "event_types": sorted(SUPPORTED_EVENT_TYPES)}), 200
