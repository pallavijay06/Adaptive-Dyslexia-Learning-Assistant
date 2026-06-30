"""Learning mode effectiveness calculations for learner modelling.

This module mirrors the comprehension score service: it is pure calculation
logic over stored behaviour events and does not depend on UI, API, or LLM code.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from database.models import BehaviorEventRecord


LEARNING_MODE_EFFECTIVENESS_WEIGHTS: dict[str, float] = {
    "mode_engagement": 0.30,
    "mode_switching": 0.20,
    "feature_utilization": 0.20,
    "post_mode_improvement": 0.20,
    "mode_retention": 0.10,
}

MODE_ENTERED = "MODE_ENTERED"
MODE_EXITED = "MODE_EXITED"
MODE_SWITCHED = "MODE_SWITCHED"
QUIZ_COMPLETED = "QUIZ_COMPLETED"

FEATURE_EVENT_TYPES = {
    "VOCABULARY_CLICKED",
    "SIMPLIFY_CLICKED",
    "AI_TUTOR_OPENED",
    "AUDIO_PLAYED",
    "AUDIO_PAUSED",
    "AUDIO_REPLAYED",
    "AUDIO_STARTED",
    "AUDIO_COMPLETED",
    "DIAGRAM_OPENED",
    "IMAGE_EXPLANATION_VIEWED",
    "ANIMATION_VIEWED",
    "VISUAL_VIEWED",
    "QUIZ_STARTED",
    "QUIZ_RETRY",
    "FORMULA_ASSISTANT_USED",
    "SYMBOL_EXPLANATION_USED",
    "DIAGRAM_EXPLANATION_USED",
    "STEP_SOLVER_USED",
    "EXPLANATION_REQUESTED",
    "AI_TUTOR_USED",
}

SMOOTH_TRANSITIONS = {
    ("READ", "VISUAL"),
    ("READ", "LISTEN"),
    ("READ", "QUIZ"),
    ("READ", "STEM"),
    ("VISUAL", "LISTEN"),
    ("VISUAL", "QUIZ"),
    ("VISUAL", "READ"),
    ("LISTEN", "QUIZ"),
    ("LISTEN", "READ"),
    ("STEM", "QUIZ"),
    ("STEM", "READ"),
}


MetricValue = float | None


def calculate_learning_mode_effectiveness(
    behavior_events: list[BehaviorEventRecord],
) -> dict[str, Any]:
    """Calculate the learner's overall learning mode effectiveness score."""
    events = _sort_events(behavior_events)
    metric_scores: dict[str, MetricValue] = {
        "mode_engagement": calculate_mode_engagement_score(events),
        "mode_switching": calculate_mode_switching_score(events),
        "feature_utilization": calculate_feature_utilization_score(events),
        "post_mode_improvement": calculate_post_mode_improvement_score(events),
        "mode_retention": calculate_mode_retention_score(events),
    }
    active_weights = _normalize_active_weights(metric_scores)
    score = _weighted_score(metric_scores, active_weights)
    metric_breakdown = _metric_breakdown(metric_scores, active_weights)

    return {
        "learning_mode_effectiveness_score": score,
        "learning_mode_effectiveness_level": _effectiveness_level(score),
        "mode_engagement_score": metric_scores["mode_engagement"],
        "mode_switching_score": metric_scores["mode_switching"],
        "feature_utilization_score": metric_scores["feature_utilization"],
        "post_mode_improvement_score": metric_scores["post_mode_improvement"],
        "mode_retention_score": metric_scores["mode_retention"],
        "learning_mode_metric_breakdown": metric_breakdown,
    }


def calculate_mode_engagement_score(events: list[BehaviorEventRecord]) -> float | None:
    """Measure active learning mode usage from time, visits, and interactions."""
    durations = _mode_durations(events)
    visits = [event for event in events if event.event_type == MODE_ENTERED]
    features = _feature_events(events)
    if not visits and not features and not durations:
        return None

    total_minutes = sum(durations) / 60.0
    unique_modes = len({_event_mode(event) for event in visits if _event_mode(event)})
    repeated_visits = sum(
        max(count - 1, 0)
        for count in Counter(_event_mode(event) for event in visits if _event_mode(event)).values()
    )

    duration_points = min(total_minutes / 30.0, 1.0) * 40.0
    visit_points = min(len(visits) / 5.0, 1.0) * 20.0
    feature_points = min(len(features) / 8.0, 1.0) * 25.0
    diversity_points = min(unique_modes / 4.0, 1.0) * 10.0
    repeat_points = min(repeated_visits / 3.0, 1.0) * 5.0

    return round(_clamp(duration_points + visit_points + feature_points + diversity_points + repeat_points), 2)


def calculate_mode_switching_score(events: list[BehaviorEventRecord]) -> float | None:
    """Measure whether mode transitions follow a smooth learning sequence."""
    sequence = _mode_sequence(events)
    if len(sequence) <= 1:
        return 100.0 if sequence else None

    transitions = list(zip(sequence, sequence[1:]))
    smooth_count = sum(1 for transition in transitions if transition in SMOOTH_TRANSITIONS)
    backtracks = sum(
        1
        for index in range(2, len(sequence))
        if sequence[index] == sequence[index - 2] and sequence[index] != sequence[index - 1]
    )
    repeated_switches = sum(1 for left, right in transitions if left == right)
    excessive_switches = max(0, len(transitions) - (len(set(sequence)) + 2))

    smooth_ratio = smooth_count / len(transitions)
    score = 70.0 + (smooth_ratio * 30.0)
    score -= backtracks * 12.0
    score -= repeated_switches * 10.0
    score -= excessive_switches * 8.0
    return round(_clamp(score), 2)


def calculate_feature_utilization_score(events: list[BehaviorEventRecord]) -> float | None:
    """Measure meaningful use of available tools across learning modes."""
    features = _feature_events(events)
    if not features:
        return None

    feature_names = [_feature_name(event) for event in features]
    unique_features = len(set(feature_names))
    mode_coverage = len({_event_mode(event) for event in features if _event_mode(event)})
    capped_repetition = sum(min(count, 3) for count in Counter(feature_names).values())

    unique_points = min(unique_features / 6.0, 1.0) * 40.0
    usage_points = min(capped_repetition / 10.0, 1.0) * 35.0
    mode_points = min(mode_coverage / 4.0, 1.0) * 25.0
    return round(_clamp(unique_points + usage_points + mode_points), 2)


def calculate_post_mode_improvement_score(events: list[BehaviorEventRecord]) -> float | None:
    """Associate modes used before quizzes with final quiz performance."""
    quiz_events = [
        event for event in events
        if event.event_type == QUIZ_COMPLETED and _quiz_score(event) is not None
    ]
    if not quiz_events:
        return None

    mode_scores: dict[str, list[float]] = defaultdict(list)
    for quiz_event in quiz_events:
        prior_modes = _modes_before_event(events, quiz_event)
        quiz_score = _quiz_score(quiz_event)
        if quiz_score is None:
            continue
        for mode in prior_modes:
            if mode != "QUIZ":
                mode_scores[mode].append(quiz_score)

    if not mode_scores:
        return None

    mode_averages = [sum(scores) / len(scores) for scores in mode_scores.values()]
    return round(_clamp(sum(mode_averages) / len(mode_averages)), 2)


def calculate_mode_retention_score(events: list[BehaviorEventRecord]) -> float | None:
    """Measure productive attention span from recorded mode durations."""
    durations = _mode_durations(events)
    if not durations:
        return None

    visit_scores = [_duration_quality_score(duration) for duration in durations]
    return round(_clamp(sum(visit_scores) / len(visit_scores)), 2)


def _normalize_active_weights(metric_scores: dict[str, MetricValue]) -> dict[str, float]:
    available_weight_total = sum(
        LEARNING_MODE_EFFECTIVENESS_WEIGHTS[name]
        for name, score in metric_scores.items()
        if score is not None
    )
    if available_weight_total <= 0:
        return {}
    return {
        name: round(LEARNING_MODE_EFFECTIVENESS_WEIGHTS[name] / available_weight_total, 4)
        for name, score in metric_scores.items()
        if score is not None
    }


def _weighted_score(
    metric_scores: dict[str, MetricValue],
    active_weights: dict[str, float],
) -> float | None:
    if not active_weights:
        return None
    total = sum(
        float(metric_scores[name]) * weight
        for name, weight in active_weights.items()
        if metric_scores[name] is not None
    )
    return round(total, 2)


def _metric_breakdown(
    metric_scores: dict[str, MetricValue],
    active_weights: dict[str, float],
) -> dict[str, dict[str, float]]:
    return {
        name: {
            "value": round(float(score), 2),
            "weight": LEARNING_MODE_EFFECTIVENESS_WEIGHTS[name],
            "normalized_weight": active_weights.get(name, 0.0),
            "contribution": round(float(score) * active_weights.get(name, 0.0), 2),
        }
        for name, score in metric_scores.items()
        if score is not None
    }


def _sort_events(events: list[BehaviorEventRecord]) -> list[BehaviorEventRecord]:
    return sorted(events, key=lambda event: (_event_timestamp(event), event.id or 0))


def _event_timestamp(event: BehaviorEventRecord) -> datetime:
    timestamp = event.event_timestamp
    if isinstance(timestamp, datetime):
        return timestamp
    return datetime.fromisoformat(str(timestamp))


def _mode_durations(events: list[BehaviorEventRecord]) -> list[float]:
    return [
        duration
        for event in events
        if event.event_type == MODE_EXITED
        for duration in [_metadata_number(event, "duration_seconds")]
        if duration is not None and duration > 0
    ]


def _mode_sequence(events: list[BehaviorEventRecord]) -> list[str]:
    sequence: list[str] = []
    for event in events:
        if event.event_type != MODE_ENTERED:
            continue
        mode = _event_mode(event)
        if mode and (not sequence or sequence[-1] != mode):
            sequence.append(mode)
    return sequence


def _modes_before_event(
    events: list[BehaviorEventRecord],
    target_event: BehaviorEventRecord,
) -> set[str]:
    target_time = _event_timestamp(target_event)
    target_session = target_event.session_id
    modes: set[str] = set()
    for event in events:
        if _event_timestamp(event) >= target_time:
            break
        if target_session is not None and event.session_id != target_session:
            continue
        if event.event_type == MODE_ENTERED:
            mode = _event_mode(event)
            if mode:
                modes.add(mode)
    return modes


def _feature_events(events: list[BehaviorEventRecord]) -> list[BehaviorEventRecord]:
    return [
        event for event in events
        if event.event_type in FEATURE_EVENT_TYPES
    ]


def _event_mode(event: BehaviorEventRecord) -> str | None:
    metadata = event.metadata or {}
    raw_mode = metadata.get("mode")
    if raw_mode is None:
        raw_mode = metadata.get("learning_mode")
    if raw_mode is None:
        return None
    return _normalize_mode(str(raw_mode))


def _feature_name(event: BehaviorEventRecord) -> str:
    metadata = event.metadata or {}
    return str(metadata.get("feature") or event.event_type).upper()


def _quiz_score(event: BehaviorEventRecord) -> float | None:
    score = _metadata_number(event, "quiz_accuracy")
    if score is None:
        score = _metadata_number(event, "score")
    return _clamp(score) if score is not None else None


def _metadata_number(event: BehaviorEventRecord, key: str) -> float | None:
    metadata = event.metadata or {}
    value = metadata.get(key)
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _duration_quality_score(duration_seconds: float) -> float:
    if duration_seconds < 10:
        return 10.0
    if duration_seconds < 60:
        return 40.0 + (duration_seconds - 10.0) * 0.6
    if duration_seconds <= 1200:
        return 70.0 + min((duration_seconds - 60.0) / 1140.0, 1.0) * 30.0
    if duration_seconds <= 2700:
        return 100.0
    return max(60.0, 100.0 - ((duration_seconds - 2700.0) / 60.0))


def _effectiveness_level(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 90:
        return "Highly Effective Learning Pattern"
    if score >= 75:
        return "Effective Learning Pattern"
    if score >= 60:
        return "Moderately Effective"
    if score >= 40:
        return "Needs Better Mode Usage"
    return "Learning Modes Underutilized"


def _normalize_mode(mode: str) -> str:
    cleaned = mode.strip().upper()
    if "SIMPLIFIED" in cleaned or "NOTES" in cleaned or "READ" in cleaned:
        return "READ"
    if "LISTEN" in cleaned or "AUDIO" in cleaned:
        return "LISTEN"
    if "VISUAL" in cleaned or "DIAGRAM" in cleaned:
        return "VISUAL"
    if "QUIZ" in cleaned:
        return "QUIZ"
    if "STEM" in cleaned or "FORMULA" in cleaned or "ASSISTANT" in cleaned:
        return "STEM"
    return cleaned


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))
