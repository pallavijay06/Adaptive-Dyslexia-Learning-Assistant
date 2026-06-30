"""Reusable behaviour tracking engine for learner interactions."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Mapping

from database.db import save_behavior_event
from database.models import BehaviorEventRecord

logger = logging.getLogger(__name__)

STANDARD_SESSION_MODES = frozenset({"Simplified Notes", "Audio", "Visual", "AI Tutor"})

_TRACKED_MODE_LABELS = {
    "Read": "Simplified Notes",
    "READ": "Simplified Notes",
    "Listen": "Audio",
    "LISTEN": "Audio",
    "Visual": "Visual",
    "VISUAL": "Visual",
}

_EVENT_TO_SESSION_MODE = {
    "SIMPLIFY_CLICKED": "Simplified Notes",
    "VOCABULARY_CLICKED": "Simplified Notes",
    "AUDIO_STARTED": "Audio",
    "AUDIO_PLAYED": "Audio",
    "AUDIO_PAUSED": "Audio",
    "AUDIO_REPLAYED": "Audio",
    "AUDIO_COMPLETED": "Audio",
    "VISUAL_VIEWED": "Visual",
    "DIAGRAM_OPENED": "Visual",
    "IMAGE_EXPLANATION_VIEWED": "Visual",
    "ANIMATION_VIEWED": "Visual",
    "AI_TUTOR_USED": "AI Tutor",
    "AI_TUTOR_OPENED": "AI Tutor",
    "EXPLANATION_REQUESTED": "AI Tutor",
}

_active_learning_sessions: dict[int, dict[str, Any]] = {}


def begin_learning_session(
    user_id: int,
    *,
    document_id: int | None = None,
    document_name: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Start a document-to-quiz learning session and reset tracked modes."""
    context = {
        "session_id": session_id or str(uuid.uuid4()),
        "document_id": document_id,
        "document_name": document_name,
        "modes_used": set(),
    }
    _active_learning_sessions[user_id] = context
    return context


def get_active_learning_session(user_id: int) -> dict[str, Any] | None:
    """Return the in-progress learning session for a learner, if any."""
    return _active_learning_sessions.get(user_id)


def clear_active_learning_session(user_id: int) -> None:
    """Clear the active learning session after it has been persisted."""
    _active_learning_sessions.pop(user_id, None)


def record_session_mode(user_id: int, mode: str) -> None:
    """Record a learning mode used during the current session (deduplicated)."""
    if mode not in STANDARD_SESSION_MODES:
        return
    session = _active_learning_sessions.get(user_id)
    if session is None:
        return
    session["modes_used"].add(mode)


def collect_session_modes_from_events(behavior_events: list[Any]) -> list[str]:
    """Derive session modes from stored behaviour events as a fallback."""
    modes: set[str] = set()
    for event in behavior_events:
        event_type = str(getattr(event, "event_type", None) or (event.get("event_type") if isinstance(event, Mapping) else "")).strip().upper()
        metadata = getattr(event, "metadata", None)
        if metadata is None and isinstance(event, Mapping):
            metadata = event.get("metadata")
        if not isinstance(metadata, Mapping):
            metadata = {}
        mode = _resolve_session_mode(event_type, metadata)
        if mode:
            modes.add(mode)
    return sorted(modes)


def _resolve_session_mode(event_type: str, metadata: Mapping[str, Any]) -> str | None:
    if event_type == MODE_ENTERED:
        raw_mode = metadata.get("mode") or metadata.get("learning_mode")
        if raw_mode is None:
            return None
        return _TRACKED_MODE_LABELS.get(str(raw_mode))
    return _EVENT_TO_SESSION_MODE.get(event_type)


def _record_session_mode_from_event(
    user_id: int,
    event_type: str,
    metadata: Mapping[str, Any],
) -> None:
    mode = _resolve_session_mode(event_type, metadata)
    if mode:
        record_session_mode(user_id, mode)

DOCUMENT_OPENED = "DOCUMENT_OPENED"
MODE_ENTERED = "MODE_ENTERED"
MODE_EXITED = "MODE_EXITED"
MODE_SWITCHED = "MODE_SWITCHED"
VOCABULARY_CLICKED = "VOCABULARY_CLICKED"
SIMPLIFY_CLICKED = "SIMPLIFY_CLICKED"
AI_TUTOR_OPENED = "AI_TUTOR_OPENED"
AUDIO_STARTED = "AUDIO_STARTED"
AUDIO_COMPLETED = "AUDIO_COMPLETED"
AUDIO_PLAYED = "AUDIO_PLAYED"
AUDIO_PAUSED = "AUDIO_PAUSED"
AUDIO_REPLAYED = "AUDIO_REPLAYED"
VISUAL_VIEWED = "VISUAL_VIEWED"
DIAGRAM_OPENED = "DIAGRAM_OPENED"
IMAGE_EXPLANATION_VIEWED = "IMAGE_EXPLANATION_VIEWED"
ANIMATION_VIEWED = "ANIMATION_VIEWED"
AI_TUTOR_USED = "AI_TUTOR_USED"
QUIZ_STARTED = "QUIZ_STARTED"
QUIZ_COMPLETED = "QUIZ_COMPLETED"
FORMULA_ASSISTANT_USED = "FORMULA_ASSISTANT_USED"
SYMBOL_EXPLANATION_USED = "SYMBOL_EXPLANATION_USED"
DIAGRAM_EXPLANATION_USED = "DIAGRAM_EXPLANATION_USED"
STEP_SOLVER_USED = "STEP_SOLVER_USED"
EXPLANATION_REQUESTED = "EXPLANATION_REQUESTED"
HINT_REQUESTED = "HINT_REQUESTED"
QUIZ_RETRY = "QUIZ_RETRY"
RESPONSE_TIME = "RESPONSE_TIME"
SESSION_COMPLETED = "SESSION_COMPLETED"
LOGIN = "LOGIN"
LOGOUT = "LOGOUT"

SUPPORTED_EVENT_TYPES = {
    DOCUMENT_OPENED,
    MODE_ENTERED,
    MODE_EXITED,
    MODE_SWITCHED,
    VOCABULARY_CLICKED,
    SIMPLIFY_CLICKED,
    AI_TUTOR_OPENED,
    AUDIO_STARTED,
    AUDIO_COMPLETED,
    AUDIO_PLAYED,
    AUDIO_PAUSED,
    AUDIO_REPLAYED,
    VISUAL_VIEWED,
    DIAGRAM_OPENED,
    IMAGE_EXPLANATION_VIEWED,
    ANIMATION_VIEWED,
    AI_TUTOR_USED,
    QUIZ_STARTED,
    QUIZ_COMPLETED,
    FORMULA_ASSISTANT_USED,
    SYMBOL_EXPLANATION_USED,
    DIAGRAM_EXPLANATION_USED,
    STEP_SOLVER_USED,
    EXPLANATION_REQUESTED,
    HINT_REQUESTED,
    QUIZ_RETRY,
    RESPONSE_TIME,
    SESSION_COMPLETED,
    LOGIN,
    LOGOUT,
}


def _normalize_event_type(event_type: str) -> str:
    """Normalize event types to uppercase for consistent storage."""
    normalized = (event_type or "").strip().upper()
    if not normalized:
        raise ValueError("event_type must not be empty")
    return normalized


def _normalize_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Convert metadata to a JSON-serialisable dictionary."""
    if metadata is None:
        return {}
    if isinstance(metadata, Mapping):
        payload: dict[str, Any] = {}
        for key, value in metadata.items():
            if isinstance(value, (dict, list)):
                payload[str(key)] = value
            else:
                payload[str(key)] = value
        return payload
    raise TypeError("metadata must be a mapping")


def track_event(
    user_id: int | None,
    event_type: str,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
    event_timestamp: datetime | None = None,
) -> BehaviorEventRecord | None:
    """Record a generic behaviour event for a learner interaction."""
    if user_id is None:
        logger.debug("Skipping behavior event for missing user_id")
        return None

    normalized_type = _normalize_event_type(event_type)
    if normalized_type not in SUPPORTED_EVENT_TYPES:
        logger.debug("Tracking non-core event type %s", normalized_type)

    timestamp = event_timestamp or datetime.utcnow()
    payload = _normalize_metadata(metadata)
    record = save_behavior_event(
        user_id=user_id,
        session_id=session_id,
        event_type=normalized_type,
        event_timestamp=timestamp,
        metadata=payload,
    )
    _record_session_mode_from_event(user_id, normalized_type, payload)
    return record


def track_document_opened(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a document was opened or selected by a learner."""
    payload = _normalize_metadata(metadata)
    record = track_event(
        user_id=user_id,
        event_type=DOCUMENT_OPENED,
        session_id=session_id,
        metadata=payload,
    )
    begin_learning_session(
        user_id,
        document_id=payload.get("document_id"),
        document_name=str(payload.get("file_name") or payload.get("document_name") or ""),
    )
    return record


def track_mode_entered(
    user_id: int,
    mode: str,
    session_id: int | None = None,
    document_id: int | None = None,
    previous_mode: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    event_timestamp: datetime | None = None,
) -> BehaviorEventRecord:
    """Record that a learner entered a learning mode."""
    payload = _normalize_metadata(metadata)
    payload.update({
        "mode": mode,
        "learning_mode": mode,
        "document_id": document_id,
        "previous_mode": previous_mode,
    })
    return track_event(
        user_id=user_id,
        event_type=MODE_ENTERED,
        session_id=session_id,
        metadata=payload,
        event_timestamp=event_timestamp,
    )


def track_mode_exited(
    user_id: int,
    mode: str,
    entered_at: datetime,
    exited_at: datetime | None = None,
    session_id: int | None = None,
    document_id: int | None = None,
    next_mode: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner exited a mode using timestamp-derived duration."""
    exit_time = exited_at or datetime.utcnow()
    duration_seconds = max(0.0, (exit_time - entered_at).total_seconds())
    payload = _normalize_metadata(metadata)
    payload.update({
        "mode": mode,
        "learning_mode": mode,
        "document_id": document_id,
        "next_mode": next_mode,
        "entered_at": entered_at.isoformat(),
        "exited_at": exit_time.isoformat(),
        "duration_seconds": round(duration_seconds, 2),
    })
    return track_event(
        user_id=user_id,
        event_type=MODE_EXITED,
        session_id=session_id,
        metadata=payload,
        event_timestamp=exit_time,
    )


def track_mode_switched(
    user_id: int,
    previous_mode: str,
    mode: str,
    session_id: int | None = None,
    document_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
    event_timestamp: datetime | None = None,
) -> BehaviorEventRecord:
    """Record an explicit mode transition sequence event."""
    payload = _normalize_metadata(metadata)
    payload.update({
        "previous_mode": previous_mode,
        "mode": mode,
        "learning_mode": mode,
        "document_id": document_id,
    })
    return track_event(
        user_id=user_id,
        event_type=MODE_SWITCHED,
        session_id=session_id,
        metadata=payload,
        event_timestamp=event_timestamp,
    )


def track_feature_used(
    user_id: int,
    feature: str,
    mode: str,
    event_type: str,
    session_id: int | None = None,
    document_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record a meaningful feature interaction within a learning mode."""
    payload = _normalize_metadata(metadata)
    payload.update({
        "feature": feature,
        "mode": mode,
        "document_id": document_id,
    })
    return track_event(
        user_id=user_id,
        event_type=event_type,
        session_id=session_id,
        metadata=payload,
    )


def track_vocabulary_clicked(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record vocabulary support usage in Read mode."""
    return track_feature_used(user_id, "vocabulary", "Read", VOCABULARY_CLICKED, session_id, metadata=metadata)


def track_simplify_clicked(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record simplification usage in Read mode."""
    return track_feature_used(user_id, "simplify", "Read", SIMPLIFY_CLICKED, session_id, metadata=metadata)


def track_ai_tutor_opened(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that the AI Tutor was opened from a learning mode."""
    return track_feature_used(user_id, "ai_tutor", "Read", AI_TUTOR_OPENED, session_id, metadata=metadata)


def track_audio_started(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner started audio playback."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("mode", "Listen")
    payload.setdefault("feature", "audio")
    return track_event(
        user_id=user_id,
        event_type=AUDIO_STARTED,
        session_id=session_id,
        metadata=payload,
    )


def track_audio_completed(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner completed audio playback."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("mode", "Listen")
    payload.setdefault("feature", "audio")
    return track_event(
        user_id=user_id,
        event_type=AUDIO_COMPLETED,
        session_id=session_id,
        metadata=payload,
    )


def track_audio_played(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner played audio."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("mode", "Listen")
    payload.setdefault("feature", "audio")
    return track_event(
        user_id=user_id,
        event_type=AUDIO_PLAYED,
        session_id=session_id,
        metadata=payload,
    )


def track_audio_paused(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner paused audio."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("mode", "Listen")
    payload.setdefault("feature", "audio")
    return track_event(
        user_id=user_id,
        event_type=AUDIO_PAUSED,
        session_id=session_id,
        metadata=payload,
    )


def track_audio_replayed(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner replayed audio."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("mode", "Listen")
    payload.setdefault("feature", "audio")
    return track_event(
        user_id=user_id,
        event_type=AUDIO_REPLAYED,
        session_id=session_id,
        metadata=payload,
    )


def track_visual_viewed(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner viewed a visual aid."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("mode", "Visual")
    payload.setdefault("feature", "diagram")
    return track_event(
        user_id=user_id,
        event_type=VISUAL_VIEWED,
        session_id=session_id,
        metadata=payload,
    )


def track_ai_tutor_used(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner used the AI tutor."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("mode", "Read")
    payload.setdefault("feature", "ai_tutor")
    return track_event(
        user_id=user_id,
        event_type=AI_TUTOR_USED,
        session_id=session_id,
        metadata=payload,
    )


def track_quiz_started(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner started a quiz."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("mode", "Quiz")
    payload.setdefault("feature", "quiz_started")
    return track_event(
        user_id=user_id,
        event_type=QUIZ_STARTED,
        session_id=session_id,
        metadata=payload,
    )


def track_quiz_completed(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner completed a quiz."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("mode", "Quiz")
    payload.setdefault("feature", "quiz_completed")
    return track_event(
        user_id=user_id,
        event_type=QUIZ_COMPLETED,
        session_id=session_id,
        metadata=payload,
    )


def track_formula_assistant_used(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner used the formula assistant."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("mode", "STEM")
    payload.setdefault("feature", "formula_assistant")
    return track_event(
        user_id=user_id,
        event_type=FORMULA_ASSISTANT_USED,
        session_id=session_id,
        metadata=payload,
    )


def track_symbol_explanation_used(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner used the symbol explanation feature."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("mode", "STEM")
    payload.setdefault("feature", "symbol_explanation")
    return track_event(
        user_id=user_id,
        event_type=SYMBOL_EXPLANATION_USED,
        session_id=session_id,
        metadata=payload,
    )


def track_diagram_explanation_used(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner used the diagram explanation feature."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("mode", "STEM")
    payload.setdefault("feature", "diagram_explanation")
    return track_event(
        user_id=user_id,
        event_type=DIAGRAM_EXPLANATION_USED,
        session_id=session_id,
        metadata=payload,
    )


def track_step_solver_used(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner used the step solver."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("mode", "STEM")
    payload.setdefault("feature", "step_solver")
    return track_event(
        user_id=user_id,
        event_type=STEP_SOLVER_USED,
        session_id=session_id,
        metadata=payload,
    )


def track_explanation_requested(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Record that a learner requested an explanation."""
    payload = _normalize_metadata(metadata)
    payload.setdefault("feature", "explanation")
    return track_event(
        user_id=user_id,
        event_type=EXPLANATION_REQUESTED,
        session_id=session_id,
        metadata=payload,
    )


def track_hint_requested(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Placeholder for future hint-tracking support."""
    return track_event(
        user_id=user_id,
        event_type=HINT_REQUESTED,
        session_id=session_id,
        metadata=metadata,
    )


def track_quiz_retry(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Placeholder for future retry-tracking support."""
    return track_event(
        user_id=user_id,
        event_type=QUIZ_RETRY,
        session_id=session_id,
        metadata=metadata,
    )


def track_response_time(
    user_id: int,
    session_id: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> BehaviorEventRecord:
    """Placeholder for future response-time tracking support."""
    return track_event(
        user_id=user_id,
        event_type=RESPONSE_TIME,
        session_id=session_id,
        metadata=metadata,
    )
