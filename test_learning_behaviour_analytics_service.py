import unittest
from datetime import datetime, timedelta

from database.models import BehaviorEventRecord, LearningSessionRecord
from services.learning_behaviour_analytics_service import (
    calculate_completion_rate_metrics,
    calculate_learning_behaviour_analytics,
    calculate_return_frequency_metrics,
    calculate_session_duration_metrics,
    extract_document_learning_sessions,
)


def _event(event_type: str, timestamp: datetime, metadata: dict | None = None) -> BehaviorEventRecord:
    return BehaviorEventRecord(
        id=1,
        user_id=1,
        session_id=None,
        event_type=event_type,
        event_timestamp=timestamp,
        metadata=metadata or {},
    )


class LearningBehaviourAnalyticsServiceTests(unittest.TestCase):
    def test_extract_document_learning_sessions_completed_and_abandoned(self) -> None:
        start = datetime(2026, 1, 1, 10, 0, 0)
        mid = datetime(2026, 1, 1, 10, 30, 0)
        end = datetime(2026, 1, 1, 11, 0, 0)
        second_start = datetime(2026, 1, 2, 9, 0, 0)

        events = [
            _event("DOCUMENT_OPENED", start, {"document_id": 1, "file_name": "notes.pdf"}),
            _event("QUIZ_COMPLETED", end, {"quiz_accuracy": 80.0}),
            _event("DOCUMENT_OPENED", second_start, {"document_id": 2, "file_name": "chapter2.pdf"}),
            _event("SESSION_COMPLETED", second_start + timedelta(minutes=20), {"completed": False}),
        ]

        sessions = extract_document_learning_sessions(events)
        self.assertEqual(len(sessions), 2)
        self.assertTrue(sessions[0]["completed"])
        self.assertEqual(sessions[0]["duration_minutes"], 60.0)
        self.assertFalse(sessions[1]["completed"])
        self.assertEqual(sessions[1]["duration_minutes"], 20.0)

    def test_session_duration_metrics(self) -> None:
        sessions = [
            {"duration_minutes": 30.0},
            {"duration_minutes": 90.0},
        ]
        metrics = calculate_session_duration_metrics(sessions)
        self.assertEqual(metrics["average_session_duration_minutes"], 60.0)
        self.assertEqual(metrics["longest_session_minutes"], 90.0)
        self.assertEqual(metrics["total_learning_time_minutes"], 120.0)

    def test_completion_rate_metrics(self) -> None:
        sessions = [
            {"completed": True},
            {"completed": True},
            {"completed": False},
        ]
        metrics = calculate_completion_rate_metrics(sessions)
        self.assertEqual(metrics["started_sessions"], 3)
        self.assertEqual(metrics["completed_sessions"], 2)
        self.assertAlmostEqual(metrics["completion_rate"], 66.7, places=1)

    def test_return_frequency_average_gap(self) -> None:
        sessions = [
            {"session_start": "2026-01-01T10:00:00"},
            {"session_start": "2026-01-02T10:00:00"},
            {"session_start": "2026-01-05T10:00:00"},
        ]
        metrics = calculate_return_frequency_metrics(sessions)
        self.assertEqual(metrics["average_days_between_sessions"], 2.0)

    def test_calculate_learning_behaviour_analytics_includes_extended_metrics(self) -> None:
        now = datetime.utcnow()
        events = [
            _event("DOCUMENT_OPENED", now - timedelta(minutes=45), {"document_id": 1}),
            _event("MODE_ENTERED", now - timedelta(minutes=40), {"mode": "Read"}),
            _event("QUIZ_COMPLETED", now, {"quiz_accuracy": 75.0}),
        ]
        login_sessions = [
            LearningSessionRecord(
                id=1,
                user_id=1,
                mode_used="authentication",
                duration=30,
                timestamp=now,
                session_duration_minutes=30,
            )
        ]
        result = calculate_learning_behaviour_analytics(
            events,
            learning_sessions=login_sessions,
            learning_history=[],
        )
        self.assertIn("session_duration", result)
        self.assertIn("daily_study_time", result)
        self.assertIn("consecutive_learning_days", result)
        self.assertEqual(result["daily_study_time"]["today_minutes"], 30.0)


if __name__ == "__main__":
    unittest.main()
