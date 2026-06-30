"""Evidence-based learning mode effectiveness from completed session history.

Determines which learning mode helps the learner perform best using actual
quiz and comprehension outcomes per session — not weighted interaction scores.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from database.db import get_learning_mode_sessions as _get_mode_sessions_from_db
from database.db import save_learning_mode_session as _save_mode_session_to_db
from database.models import LearningModeSessionRecord
from services.behavior_tracking_service import (
    clear_active_learning_session,
    collect_session_modes_from_events,
    get_active_learning_session,
)

STANDARD_LEARNING_MODES = (
    "Simplified Notes",
    "Audio",
    "Visual",
    "AI Tutor",
)


def save_learning_session(
    user_id: int,
    *,
    session_id: str | None = None,
    document_id: int | None = None,
    document_name: str | None = None,
    modes_used: list[str] | None = None,
    quiz_accuracy: float,
    comprehension_score: float,
    timestamp: datetime | None = None,
) -> LearningModeSessionRecord:
    """Persist one completed learning session after quiz evaluation."""
    active = get_active_learning_session(user_id)
    resolved_session_id = session_id or (active or {}).get("session_id") or str(uuid.uuid4())
    resolved_document_id = document_id if document_id is not None else (active or {}).get("document_id")
    resolved_document_name = document_name or (active or {}).get("document_name")
    resolved_modes = _dedupe_modes(modes_used if modes_used is not None else list((active or {}).get("modes_used", [])))

    record = _save_mode_session_to_db(
        session_id=resolved_session_id,
        user_id=user_id,
        document_id=resolved_document_id,
        document_name=resolved_document_name,
        modes_used=resolved_modes,
        quiz_accuracy=quiz_accuracy,
        comprehension_score=comprehension_score,
        timestamp=timestamp,
    )
    clear_active_learning_session(user_id)
    return record


def finalize_learning_session_on_quiz(
    user_id: int,
    *,
    quiz_accuracy: float,
    comprehension_score: float,
    document_id: int | None = None,
    document_name: str | None = None,
    behavior_events: list[Any] | None = None,
) -> LearningModeSessionRecord | None:
    """Save the active session after quiz completion, with event fallback for modes."""
    active = get_active_learning_session(user_id)
    modes_used: list[str] = list((active or {}).get("modes_used", []))
    if not modes_used and behavior_events:
        modes_used = collect_session_modes_from_events(behavior_events)

    if active is None and not modes_used and document_id is None and document_name is None:
        modes_used = modes_used or []

    return save_learning_session(
        user_id,
        document_id=document_id or (active or {}).get("document_id"),
        document_name=document_name or (active or {}).get("document_name"),
        modes_used=modes_used,
        quiz_accuracy=quiz_accuracy,
        comprehension_score=comprehension_score,
    )


def get_learning_sessions(user_id: int, limit: int = 500) -> list[LearningModeSessionRecord]:
    """Return all stored learning mode sessions for a learner."""
    return _get_mode_sessions_from_db(user_id, limit=limit)


def compute_mode_effectiveness(user_id: int) -> dict[str, Any]:
    """Compute per-mode effectiveness rankings from session history."""
    sessions = get_learning_sessions(user_id)
    mode_stats: dict[str, dict[str, list[float]]] = {
        mode: {"quiz": [], "comprehension": []} for mode in STANDARD_LEARNING_MODES
    }

    for session in sessions:
        for mode in session.modes_used or []:
            if mode not in mode_stats:
                continue
            mode_stats[mode]["quiz"].append(float(session.quiz_accuracy))
            mode_stats[mode]["comprehension"].append(float(session.comprehension_score))

    rankings: list[dict[str, Any]] = []
    for mode in STANDARD_LEARNING_MODES:
        quiz_scores = mode_stats[mode]["quiz"]
        comp_scores = mode_stats[mode]["comprehension"]
        if not quiz_scores:
            continue
        average_quiz = round(sum(quiz_scores) / len(quiz_scores), 1)
        average_comprehension = round(sum(comp_scores) / len(comp_scores), 1)
        effectiveness = round((average_quiz + average_comprehension) / 2.0, 1)
        rankings.append({
            "mode": mode,
            "sessions": len(quiz_scores),
            "average_quiz": average_quiz,
            "average_comprehension": average_comprehension,
            "effectiveness": effectiveness,
        })

    rankings.sort(key=lambda item: item["effectiveness"], reverse=True)
    recommended_mode = rankings[0]["mode"] if rankings else None
    return {
        "mode_rankings": rankings,
        "recommended_mode": recommended_mode,
    }


def _dedupe_modes(modes: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for mode in modes:
        if mode in STANDARD_LEARNING_MODES and mode not in seen:
            seen.add(mode)
            ordered.append(mode)
    return ordered
