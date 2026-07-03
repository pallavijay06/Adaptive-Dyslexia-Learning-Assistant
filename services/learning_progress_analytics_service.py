"""Learning Progress analytics — improvement-focused metrics aggregated from existing data.

Reuses quiz history, comprehension scores, difficulty profile, and session records
without duplicating comprehension/difficulty engines.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from database.models import QuizAttemptRecord, QuizQuestionResponseRecord

DEFAULT_WEEKLY_SESSION_GOAL = 5
IMPROVEMENT_STABLE_THRESHOLD = 3.0


def _quiz_accuracy_pct(attempt: QuizAttemptRecord) -> float:
    if not attempt.total_questions:
        return 0.0
    return round((attempt.score / attempt.total_questions) * 100.0, 1)


def _question_difficulty_score(is_correct: bool) -> float:
    """Mirror difficulty profile formula at question level: 100 − accuracy."""
    return 0.0 if is_correct else 100.0


def _trend_status(change: float, *, improving_label: str = "Improving") -> str:
    if change > IMPROVEMENT_STABLE_THRESHOLD:
        return improving_label
    if change < -IMPROVEMENT_STABLE_THRESHOLD:
        return "Declining"
    return "Stable"


def compute_learning_improvement_trend(
    quizzes: list[QuizAttemptRecord],
) -> dict[str, Any]:
    """Track quiz accuracy trend using half-split averages when >= 4 attempts exist.

    With >= 4 attempts: split into two halves, compare average of each half.
    With 2-3 attempts: fall back to first-vs-last comparison.
    """
    ordered = sorted(quizzes, key=lambda q: q.timestamp)
    history = [
        (f"Attempt {index + 1}", _quiz_accuracy_pct(attempt))
        for index, attempt in enumerate(ordered)
    ]

    if len(history) < 2:
        return {
            "status": "Stable",
            "overall_improvement_pct": 0.0,
            "history": history,
            "has_data": len(history) > 0,
        }

    scores = [pct for _, pct in history]
    if len(scores) >= 4:
        midpoint = len(scores) // 2
        first_half_avg = sum(scores[:midpoint]) / midpoint
        second_half_avg = sum(scores[midpoint:]) / len(scores[midpoint:])
        overall_improvement = round(second_half_avg - first_half_avg, 1)
    else:
        overall_improvement = round(scores[-1] - scores[0], 1)

    return {
        "status": _trend_status(overall_improvement),
        "overall_improvement_pct": overall_improvement,
        "history": history,
        "has_data": True,
    }


def compute_comprehension_trend(
    quizzes: list[QuizAttemptRecord],
) -> dict[str, Any]:
    """Progression of per-quiz comprehension scores over time."""
    ordered = sorted(quizzes, key=lambda q: q.timestamp)
    scores = [
        round(float(attempt.comprehension_score or 0.0), 1)
        for attempt in ordered
        if attempt.comprehension_score is not None
    ]

    if not scores:
        return {
            "current_trend": "Stable",
            "mini_history": [],
            "chart_data": [],
            "has_data": False,
        }

    mini_history = scores[-4:]
    chart_data = [
        (attempt.timestamp.strftime("%Y-%m-%d"), round(float(attempt.comprehension_score or 0.0), 1))
        for attempt in ordered
        if attempt.comprehension_score is not None
    ]

    current_trend = "Stable"
    if len(scores) >= 2:
        change = scores[-1] - scores[-2]
        current_trend = _trend_status(change)

    return {
        "current_trend": current_trend,
        "mini_history": mini_history,
        "chart_data": chart_data,
        "has_data": True,
    }


def compute_difficulty_reduction(
    responses: list[QuizQuestionResponseRecord],
    quizzes: list[QuizAttemptRecord],
    difficulty_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    """Measure whether average difficulty score is reducing across weekly sessions.

    Uses the difficulty profile formula (100 − accuracy) on historical quiz responses
    grouped by ISO week — does not re-run the difficulty profile engine.
    """
    if not responses or not quizzes:
        return {
            "reduction_pct": 0.0,
            "status": "Needs More Practice",
            "weekly_history": [],
            "has_data": False,
        }

    quiz_timestamps = {
        attempt.id: attempt.timestamp
        for attempt in quizzes
        if attempt.id is not None
    }

    weekly_scores: dict[str, list[float]] = defaultdict(list)
    for response in responses:
        quiz_id = response.quiz_id
        if quiz_id is None or quiz_id not in quiz_timestamps:
            continue
        timestamp = quiz_timestamps[quiz_id]
        week_key = f"Week {timestamp.isocalendar()[1]:02d} ({timestamp.isocalendar()[0]})"
        weekly_scores[week_key].append(_question_difficulty_score(response.is_correct))

    if not weekly_scores:
        return {
            "reduction_pct": 0.0,
            "status": "Needs More Practice",
            "weekly_history": [],
            "has_data": False,
        }

    weekly_averages = sorted(
        (week, round(sum(scores) / len(scores), 1))
        for week, scores in weekly_scores.items()
    )

    first_avg = weekly_averages[0][1]
    last_avg = weekly_averages[-1][1]
    reduction_pct = round(first_avg - last_avg, 1)
    status = "Improving" if reduction_pct > 0 else "Needs More Practice"

    return {
        "reduction_pct": reduction_pct,
        "status": status,
        "weekly_history": weekly_averages,
        "has_data": True,
    }


def _group_responses_by_concept_and_quiz(
    responses: list[QuizQuestionResponseRecord],
    quizzes: list[QuizAttemptRecord],
) -> dict[str, dict[int, list[bool]]]:
    """Map concept (stored in topic field) → quiz_id → correctness flags."""
    valid_quiz_ids = {attempt.id for attempt in quizzes if attempt.id is not None}
    grouped: dict[str, dict[int, list[bool]]] = defaultdict(lambda: defaultdict(list))

    for response in responses:
        concept = str(response.topic or "").strip()
        quiz_id = response.quiz_id
        if not concept or quiz_id is None or quiz_id not in valid_quiz_ids:
            continue
        grouped[concept][quiz_id].append(response.is_correct)

    return grouped


def _quiz_order_index(quizzes: list[QuizAttemptRecord]) -> dict[int, int]:
    ordered = sorted(quizzes, key=lambda q: q.timestamp)
    return {
        attempt.id: index
        for index, attempt in enumerate(ordered)
        if attempt.id is not None
    }


def _accuracy_from_flags(flags: list[bool]) -> float:
    if not flags:
        return 0.0
    return round((sum(1 for flag in flags if flag) / len(flags)) * 100.0, 1)


def compute_retention_score(
    responses: list[QuizQuestionResponseRecord],
    quizzes: list[QuizAttemptRecord],
) -> dict[str, Any]:
    """Evidence-based retention from historical quiz performance per concept."""
    grouped = _group_responses_by_concept_and_quiz(responses, quizzes)
    quiz_order = _quiz_order_index(quizzes)

    concept_retentions: list[float] = []
    for concept, quiz_map in grouped.items():
        quiz_entries = [
            (quiz_order.get(quiz_id, 0), flags)
            for quiz_id, flags in quiz_map.items()
            if quiz_id in quiz_order
        ]
        if len(quiz_entries) < 2:
            continue

        quiz_entries.sort(key=lambda item: item[0])
        midpoint = len(quiz_entries) // 2
        early_flags = [flag for _, flags in quiz_entries[:midpoint] for flag in flags]
        late_flags = [flag for _, flags in quiz_entries[midpoint:] for flag in flags]

        early_accuracy = _accuracy_from_flags(early_flags)
        late_accuracy = _accuracy_from_flags(late_flags)
        change = late_accuracy - early_accuracy

        if change >= 0:
            concept_retentions.append(min(100.0, 70.0 + change))
        else:
            concept_retentions.append(max(0.0, 70.0 + change))

    if not concept_retentions:
        return {"score": 0.0, "repeated_concepts": 0, "avg_retained_accuracy": 0.0, "has_data": False}

    # Compute average retained accuracy across all repeated concepts
    retained_accuracies: list[float] = []
    for concept, quiz_map in grouped.items():
        quiz_entries = [
            (quiz_order.get(quiz_id, 0), flags)
            for quiz_id, flags in quiz_map.items()
            if quiz_id in quiz_order
        ]
        if len(quiz_entries) < 2:
            continue
        quiz_entries.sort(key=lambda item: item[0])
        late_flags = [flag for _, flags in quiz_entries[len(quiz_entries) // 2:] for flag in flags]
        retained_accuracies.append(_accuracy_from_flags(late_flags))

    avg_retained = round(sum(retained_accuracies) / len(retained_accuracies), 1) if retained_accuracies else 0.0

    return {
        "score": round(sum(concept_retentions) / len(concept_retentions), 1),
        "repeated_concepts": len(concept_retentions),
        "avg_retained_accuracy": avg_retained,
        "has_data": True,
    }


def compute_most_improved_concept(
    responses: list[QuizQuestionResponseRecord],
    quizzes: list[QuizAttemptRecord],
    difficulty_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    """Find the concept with the largest difficulty-score reduction across quiz history."""
    grouped = _group_responses_by_concept_and_quiz(responses, quizzes)
    quiz_order = _quiz_order_index(quizzes)

    best_concept = ""
    best_improvement = 0.0
    earliest_difficulty = 0.0
    latest_difficulty = 0.0

    for concept, quiz_map in grouped.items():
        quiz_entries = [
            (quiz_order.get(quiz_id, 0), flags)
            for quiz_id, flags in quiz_map.items()
            if quiz_id in quiz_order
        ]
        if len(quiz_entries) < 2:
            continue

        quiz_entries.sort(key=lambda item: item[0])
        early_accuracy = _accuracy_from_flags(quiz_entries[0][1])
        late_accuracy = _accuracy_from_flags(quiz_entries[-1][1])
        early_difficulty = round(100.0 - early_accuracy, 1)
        late_difficulty = round(100.0 - late_accuracy, 1)
        improvement = round(early_difficulty - late_difficulty, 1)

        if improvement > best_improvement:
            best_improvement = improvement
            best_concept = concept
            earliest_difficulty = early_difficulty
            latest_difficulty = late_difficulty

    if not best_concept:
        profile_concepts = (difficulty_profile or {}).get("concept_difficulty") or {}
        if isinstance(profile_concepts, dict) and profile_concepts:
            name = next(iter(profile_concepts))
            entry = profile_concepts[name]
            score = float(entry.get("difficulty_score") or 0.0)
            return {
                "concept": name,
                "improvement_pct": 0.0,
                "earliest_difficulty": score,
                "latest_difficulty": score,
                "has_data": True,
            }
        return {
            "concept": "",
            "improvement_pct": 0.0,
            "earliest_difficulty": 0.0,
            "latest_difficulty": 0.0,
            "has_data": False,
        }

    return {
        "concept": best_concept,
        "improvement_pct": best_improvement,
        "earliest_difficulty": earliest_difficulty,
        "latest_difficulty": latest_difficulty,
        "has_data": True,
    }


def compute_needs_more_practice(
    difficulty_data: dict[str, Any],
) -> dict[str, Any]:
    """Identify the concept needing the most practice from the difficulty profile."""
    if not difficulty_data.get("has_data"):
        return {"concept": "", "reason": "", "has_data": False}

    summary = difficulty_data.get("summary") or {}
    concept_rows = difficulty_data.get("concept_difficulty") or []

    candidates: list[tuple[str, float, str]] = []

    top_concept = summary.get("most_difficult_concept")
    if top_concept:
        candidates.append((
            str(top_concept.get("Concept", "")),
            float(top_concept.get("Difficulty Score") or 0.0),
            "Highest Difficulty",
        ))

    top_error = summary.get("highest_error_frequency")
    if top_error and top_error.get("Type") == "Concept":
        candidates.append((
            str(top_error.get("Category", "")),
            float(top_error.get("Error Frequency") or 0.0),
            "Highest Error Frequency",
        ))

    if concept_rows:
        lowest_accuracy = min(concept_rows, key=lambda row: float(row.get("Accuracy") or 0.0))
        candidates.append((
            str(lowest_accuracy.get("Concept", "")),
            100.0 - float(lowest_accuracy.get("Accuracy") or 0.0),
            "Lowest Accuracy",
        ))

    if not candidates:
        return {"concept": "", "reason": "", "has_data": False}

    best = max(candidates, key=lambda item: item[1])
    return {
        "concept": best[0],
        "reason": best[2],
        "has_data": bool(best[0]),
    }


def compute_weekly_goal(
    mode_sessions: list[Any],
    login_sessions: list[Any],
    *,
    goal: int = DEFAULT_WEEKLY_SESSION_GOAL,
    user_goal: int | None = None,
) -> dict[str, Any]:
    """Track weekly learning session progress against a configurable goal.

    Pass user_goal to override the default when user-configurable goals are added.
    Falls back to DEFAULT_WEEKLY_SESSION_GOAL when user_goal is None.
    """
    goal = user_goal if user_goal is not None else goal
    today = datetime.utcnow().date()
    week_start = today - timedelta(days=today.weekday())

    def _session_in_current_week(timestamp: Any) -> bool:
        if timestamp is None:
            return False
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                return False
        if hasattr(timestamp, "date"):
            session_date = timestamp.date()
        else:
            return False
        return session_date >= week_start

    completed = sum(
        1 for session in mode_sessions
        if _session_in_current_week(getattr(session, "timestamp", None))
    )

    if completed == 0 and login_sessions:
        completed = sum(
            1 for session in login_sessions
            if _session_in_current_week(getattr(session, "timestamp", None))
        )

    progress_pct = round(min(100.0, (completed / goal) * 100.0), 1) if goal else 0.0

    return {
        "completed_sessions": completed,
        "goal": goal,
        "progress_pct": progress_pct,
        "has_data": completed > 0,
    }


def build_learning_progress_analytics(
    *,
    quizzes: list[QuizAttemptRecord],
    responses: list[QuizQuestionResponseRecord],
    difficulty_data: dict[str, Any],
    mode_sessions: list[Any],
    login_sessions: list[Any],
) -> dict[str, Any]:
    """Aggregate all Learning Progress improvement metrics."""
    raw_profile = difficulty_data.get("raw_profile") if difficulty_data else None

    return {
        "learning_improvement_trend": compute_learning_improvement_trend(quizzes),
        "comprehension_trend": compute_comprehension_trend(quizzes),
        "difficulty_reduction": compute_difficulty_reduction(
            responses, quizzes, raw_profile,
        ),
        "retention_score": compute_retention_score(responses, quizzes),
        "most_improved_concept": compute_most_improved_concept(
            responses, quizzes, raw_profile,
        ),
        "needs_more_practice": compute_needs_more_practice(difficulty_data),
        "weekly_goal": compute_weekly_goal(mode_sessions, login_sessions),
        # Pass concept rows through so the UI can display difficulty/attempts/accuracy
        # for the Needs More Practice card without re-querying.
        "_difficulty_concept_rows": difficulty_data.get("concept_difficulty") or [],
    }
