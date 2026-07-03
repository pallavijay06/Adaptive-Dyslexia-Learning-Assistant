"""Tests for Learning Progress analytics calculations."""

from __future__ import annotations

from datetime import datetime

import pytest

from database.models import QuizAttemptRecord, QuizQuestionResponseRecord
from services.learning_progress_analytics_service import (
    compute_comprehension_trend,
    compute_learning_improvement_trend,
    compute_retention_score,
    compute_weekly_goal,
)


def _quiz(
    quiz_id: int,
    score: int,
    total: int,
    ts: datetime,
    comprehension: float,
) -> QuizAttemptRecord:
    return QuizAttemptRecord(
        id=quiz_id,
        user_id=1,
        topic="Physics",
        score=score,
        total_questions=total,
        timestamp=ts,
        comprehension_score=comprehension,
    )


def _response(
    quiz_id: int,
    concept: str,
    is_correct: bool,
    ts: datetime,
) -> QuizQuestionResponseRecord:
    return QuizQuestionResponseRecord(
        id=None,
        user_id=1,
        quiz_id=quiz_id,
        question_id="q1",
        question_type="MCQ",
        topic=concept,
        difficulty="medium",
        question_start_time=ts,
        question_submit_time=ts,
        time_taken_seconds=30,
        is_correct=is_correct,
        created_at=ts,
    )


def test_learning_improvement_trend_improving():
    quizzes = [
        _quiz(1, 5, 10, datetime(2026, 1, 1), 52.0),
        _quiz(2, 6, 10, datetime(2026, 1, 8), 63.0),
        _quiz(3, 7, 10, datetime(2026, 1, 15), 74.0),
        _quiz(4, 8, 10, datetime(2026, 1, 22), 82.0),
    ]
    result = compute_learning_improvement_trend(quizzes)
    assert result["status"] == "Improving"
    assert result["overall_improvement_pct"] == 30.0
    assert len(result["history"]) == 4


def test_comprehension_trend_mini_history():
    quizzes = [
        _quiz(1, 5, 10, datetime(2026, 1, 1), 68.0),
        _quiz(2, 6, 10, datetime(2026, 1, 8), 74.0),
        _quiz(3, 7, 10, datetime(2026, 1, 15), 79.0),
        _quiz(4, 8, 10, datetime(2026, 1, 22), 86.0),
    ]
    result = compute_comprehension_trend(quizzes)
    assert result["mini_history"] == [68.0, 74.0, 79.0, 86.0]
    assert result["current_trend"] == "Improving"


def test_retention_score_with_improving_concept():
    quizzes = [
        _quiz(1, 3, 5, datetime(2026, 1, 1), 50.0),
        _quiz(2, 4, 5, datetime(2026, 1, 8), 60.0),
    ]
    responses = [
        _response(1, "Voltage", False, datetime(2026, 1, 1)),
        _response(1, "Voltage", False, datetime(2026, 1, 1)),
        _response(2, "Voltage", True, datetime(2026, 1, 8)),
        _response(2, "Voltage", True, datetime(2026, 1, 8)),
    ]
    result = compute_retention_score(responses, quizzes)
    assert result["has_data"] is True
    assert result["score"] > 70.0


def test_weekly_goal_default():
    class Session:
        timestamp = datetime.utcnow()

    result = compute_weekly_goal([Session()], [], goal=5)
    assert result["goal"] == 5
    assert result["completed_sessions"] == 1
    assert result["progress_pct"] == 20.0
