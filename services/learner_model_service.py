"""Learner modelling calculations for comprehension scoring.

This module is intentionally independent of UI, database, API, and LLM code.
Future dashboard and personalization modules can import these pure functions
without triggering side effects.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


COMPREHENSION_WEIGHTS: dict[str, float] = {
    "quiz_accuracy": 0.35,
    "conceptual_answer": 0.30,
    "learning_support": 0.15,
    "first_attempt": 0.10,
    "response_efficiency": 0.10,
}


MetricValue = int | float | None


def calculate_quiz_accuracy_score(
    quiz_evaluation: Mapping[str, Any] | None = None,
    *,
    correct_answers: int | float | None = None,
    total_questions: int | float | None = None,
    score: int | float | None = None,
    max_score: int | float | None = None,
) -> float | None:
    """Calculate quiz accuracy as a percentage from MCQ evaluation results.

    Args:
        quiz_evaluation: Optional quiz report, commonly containing
            ``correct_answers`` and ``total_questions`` or ``score`` and
            ``max_score``/``total_questions``.
        correct_answers: Explicit number of correct quiz answers.
        total_questions: Explicit number of attempted quiz questions.
        score: Explicit score fallback when ``correct_answers`` is unavailable.
        max_score: Explicit maximum score fallback.

    Returns:
        A score from 0 to 100, or ``None`` when no usable quiz data is supplied.
    """
    if quiz_evaluation:
        correct_answers = _first_number(
            correct_answers,
            quiz_evaluation.get("correct_answers"),
            quiz_evaluation.get("score"),
        )
        total_questions = _first_number(
            total_questions,
            quiz_evaluation.get("total_questions"),
            quiz_evaluation.get("total"),
            quiz_evaluation.get("questions_attempted"),
            quiz_evaluation.get("max_score"),
        )

    numerator = _first_number(correct_answers, score)
    denominator = _first_number(total_questions, max_score)

    return _percentage(numerator, denominator)


def calculate_conceptual_answer_score(
    short_answer_evaluations: Iterable[Mapping[str, Any]] | None = None,
) -> float | None:
    """Calculate average conceptual short-answer score as a percentage.

    Each evaluation should contain ``score`` and ``max_score``. Invalid or
    incomplete entries are skipped so partial evaluation batches can still be
    scored.

    Args:
        short_answer_evaluations: Short-answer evaluation dictionaries.

    Returns:
        The average percentage across valid short-answer evaluations, or
        ``None`` when no valid evaluations are supplied.
    """
    if short_answer_evaluations is None:
        return None

    percentages: list[float] = []
    for evaluation in short_answer_evaluations:
        if not isinstance(evaluation, Mapping):
            continue
        if isinstance(evaluation.get("evaluation"), Mapping):
            evaluation = evaluation["evaluation"]

        percentage = _percentage(
            _to_float(evaluation.get("score")),
            _to_float(evaluation.get("max_score")),
        )
        if percentage is not None:
            percentages.append(percentage)

    if not percentages:
        return None

    return round(sum(percentages) / len(percentages), 2)


def calculate_learning_support_score(
    behavior_events: Iterable[Mapping[str, Any]] | None = None,
) -> float | None:
    """Calculate learning support score from hint-request events."""
    hint_requests = _count_behavior_events(behavior_events, "HINT_REQUESTED")
    if hint_requests is None:
        return None
    if hint_requests <= 0:
        return 100.0
    if hint_requests == 1:
        return 80.0
    if hint_requests == 2:
        return 60.0
    return 40.0


def calculate_first_attempt_score(
    behavior_events: Iterable[Mapping[str, Any]] | None = None,
) -> float | None:
    """Estimate first-attempt success rate from retry behavior events."""
    if behavior_events is None:
        return None

    total_questions: set[str] = set()
    retry_questions: set[str] = set()
    for event in _normalize_behavior_events(behavior_events):
        metadata = event.get("metadata") or {}
        question_id = metadata.get("question_id")
        if not question_id:
            continue

        event_type = str(event.get("event_type") or "").strip().upper()
        if event_type == "RESPONSE_TIME":
            total_questions.add(str(question_id))
        elif event_type == "QUIZ_RETRY":
            retry_questions.add(str(question_id))

    if not total_questions:
        return None

    first_attempt_success_count = sum(1 for question_id in total_questions if str(question_id) not in retry_questions)
    return _percentage(first_attempt_success_count, len(total_questions))


def calculate_response_efficiency_score(
    behavior_events: Iterable[Mapping[str, Any]] | None = None,
) -> float | None:
    """Calculate response efficiency from recorded response-time events."""
    if behavior_events is None:
        return None

    response_times: list[float] = []
    for event in _normalize_behavior_events(behavior_events):
        metadata = event.get("metadata") or {}
        event_type = str(event.get("event_type") or "").strip().upper()
        if event_type != "RESPONSE_TIME":
            continue
        time_taken = _to_float(metadata.get("time_taken_seconds"))
        if time_taken is not None:
            response_times.append(time_taken)

    if not response_times:
        return None

    avg_response_time = sum(response_times) / len(response_times)
    if avg_response_time <= 30.0:
        return 100.0
    if avg_response_time >= 120.0:
        return 0.0
    return round(100.0 - ((avg_response_time - 30.0) / 90.0) * 100.0, 1)


def calculate_comprehension_score(
    quiz_evaluation: Mapping[str, Any] | None = None,
    short_answer_evaluations: Iterable[Mapping[str, Any]] | None = None,
    behavior_events: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Calculate the normalized overall comprehension score.

    All configured metrics are computed, unavailable metrics are ignored, and
    the weights for available metrics are normalized automatically. This keeps
    Version 1 compatible with the full metric framework.

    Args:
        quiz_evaluation: Optional MCQ quiz evaluation report.
        short_answer_evaluations: Optional short-answer evaluation results.

    Returns:
        A dictionary containing individual metric scores, active normalized
        weights, final comprehension score, and comprehension level.
    """
    metric_scores: dict[str, MetricValue] = {
        "quiz_accuracy": calculate_quiz_accuracy_score(quiz_evaluation),
        "conceptual_answer": calculate_conceptual_answer_score(short_answer_evaluations),
        "learning_support": calculate_learning_support_score(behavior_events),
        "first_attempt": calculate_first_attempt_score(behavior_events),
        "response_efficiency": calculate_response_efficiency_score(behavior_events),
    }

    active_weights = _normalize_active_weights(metric_scores)
    comprehension_score = _weighted_score(metric_scores, active_weights)

    return {
        "quiz_accuracy_score": metric_scores["quiz_accuracy"],
        "conceptual_answer_score": metric_scores["conceptual_answer"],
        "learning_support_score": metric_scores["learning_support"],
        "first_attempt_score": metric_scores["first_attempt"],
        "response_efficiency_score": metric_scores["response_efficiency"],
        "active_weights": active_weights,
        "metric_breakdown": _metric_breakdown(metric_scores, active_weights),
        "comprehension_score": comprehension_score,
        "comprehension_level": _comprehension_level(comprehension_score),
    }


def _normalize_active_weights(metric_scores: Mapping[str, MetricValue]) -> dict[str, float]:
    """Return normalized weights for metrics that have available scores."""
    available_weight_total = sum(
        COMPREHENSION_WEIGHTS[metric_name]
        for metric_name, metric_score in metric_scores.items()
        if metric_score is not None
    )

    if available_weight_total <= 0:
        return {}

    return {
        metric_name: round(COMPREHENSION_WEIGHTS[metric_name] / available_weight_total, 4)
        for metric_name, metric_score in metric_scores.items()
        if metric_score is not None
    }


def _weighted_score(
    metric_scores: Mapping[str, MetricValue],
    active_weights: Mapping[str, float],
) -> float | None:
    """Return the weighted score using normalized active weights."""
    if not active_weights:
        return None

    total = sum(
        float(metric_scores[metric_name]) * weight
        for metric_name, weight in active_weights.items()
        if metric_scores[metric_name] is not None
    )
    return round(total, 2)


def _metric_breakdown(
    metric_scores: Mapping[str, MetricValue],
    active_weights: Mapping[str, float],
) -> dict[str, dict[str, float]]:
    """Build an explainable contribution map for available metrics."""
    return {
        metric_name: {
            "value": round(float(metric_score), 2),
            "weight": COMPREHENSION_WEIGHTS[metric_name],
            "normalized_weight": normalized_weight,
            "contribution": round(float(metric_score) * normalized_weight, 2),
        }
        for metric_name, metric_score in metric_scores.items()
        if metric_score is not None
        for normalized_weight in [active_weights.get(metric_name, 0.0)]
    }


def _comprehension_level(score: float | None) -> str | None:
    """Map a comprehension score to its learning level label."""
    if score is None:
        return None
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "Weak"
    return "Needs Immediate Support"


def _percentage(numerator: float | None, denominator: float | None) -> float | None:
    """Convert a score ratio into a clamped 0-100 percentage."""
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return round(_clamp((numerator / denominator) * 100.0), 2)


def _count_behavior_events(
    behavior_events: Iterable[Mapping[str, Any]] | None,
    event_type: str,
) -> int | None:
    """Count matching behavior events from a supplied event stream."""
    if behavior_events is None:
        return None

    count = 0
    for event in _normalize_behavior_events(behavior_events):
        if str(event.get("event_type") or "").strip().upper() == str(event_type).strip().upper():
            count += 1
    return count


def _normalize_behavior_events(
    behavior_events: Iterable[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Normalize behavior-event objects and mappings into lightweight dictionaries."""
    if behavior_events is None:
        return []

    normalized: list[dict[str, Any]] = []
    for event in behavior_events:
        if isinstance(event, Mapping):
            metadata = event.get("metadata")
            normalized.append({
                "event_type": event.get("event_type"),
                "metadata": metadata if isinstance(metadata, Mapping) else None,
            })
            continue

        metadata = getattr(event, "metadata", None)
        normalized.append({
            "event_type": getattr(event, "event_type", None),
            "metadata": metadata if isinstance(metadata, Mapping) else None,
        })
    return normalized


def _first_number(*values: Any) -> float | None:
    """Return the first value that can be interpreted as a number."""
    for value in values:
        number = _to_float(value)
        if number is not None:
            return number
    return None


def _to_float(value: Any) -> float | None:
    """Convert numeric-like values to float while rejecting booleans."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """Clamp a numeric value to the scoring range."""
    return max(minimum, min(maximum, value))


def refresh_learner_profiles_from_quiz(
    user_id: int,
    *,
    quiz_evaluation: Mapping[str, Any] | None = None,
    short_answer_evaluations: Iterable[Mapping[str, Any]] | None = None,
    behavior_event_limit: int = 500,
) -> dict[str, Any]:
    """Recompute and persist comprehension and learning-mode profiles from stored events."""
    from database.db import (
        get_behavior_events,
        save_learner_comprehension_profile,
        save_learning_mode_effectiveness_profile,
    )
    from services.learning_mode_effectiveness_service import calculate_learning_mode_effectiveness

    behavior_events = get_behavior_events(user_id, limit=behavior_event_limit)
    learner_model_result = calculate_comprehension_score(
        quiz_evaluation=quiz_evaluation,
        short_answer_evaluations=short_answer_evaluations,
        behavior_events=behavior_events,
    )
    save_learner_comprehension_profile(user_id, learner_model_result)
    learning_mode_result = calculate_learning_mode_effectiveness(behavior_events)
    save_learning_mode_effectiveness_profile(user_id, learning_mode_result)
    return {
        "comprehension": learner_model_result,
        "learning_mode": learning_mode_result,
    }
