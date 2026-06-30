import unittest
import uuid
from datetime import datetime

from database import db
from services.behavior_tracking_service import (
    track_audio_played,
    track_document_opened,
    track_event,
    track_formula_assistant_used,
)
from services.learner_model_service import calculate_comprehension_score, calculate_conceptual_answer_score


class BehaviorTrackingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        db.init_db()
        self.user = db.save_user(
            name="Behavior Tester",
            email=f"behavior+{uuid.uuid4().hex[:8]}@example.com",
            password_hash="hash",
            age=16,
            grade="10",
            institution="Test School",
            field_of_study="Science",
        )

    def test_track_document_opened_persists_event(self) -> None:
        event = track_document_opened(self.user.id, metadata={"document_id": 42})

        self.assertEqual(event.event_type, "DOCUMENT_OPENED")
        self.assertEqual(event.user_id, self.user.id)

        stored_events = db.get_behavior_events(self.user.id, limit=10)
        self.assertEqual(len(stored_events), 1)
        self.assertEqual(stored_events[0].event_type, "DOCUMENT_OPENED")
        self.assertEqual(stored_events[0].metadata["document_id"], 42)

    def test_track_event_supports_flexible_metadata(self) -> None:
        event = track_event(
            user_id=self.user.id,
            event_type="CUSTOM_EVENT",
            metadata={"custom_flag": True, "count": 3},
        )

        self.assertEqual(event.event_type, "CUSTOM_EVENT")
        self.assertTrue(event.metadata["custom_flag"])
        self.assertEqual(event.metadata["count"], 3)

    def test_feature_tracking_wrappers_persist_events(self) -> None:
        audio_event = track_audio_played(self.user.id, metadata={"mode": "Listen"})
        formula_event = track_formula_assistant_used(self.user.id, metadata={"formula": "V = IR"})

        self.assertEqual(audio_event.event_type, "AUDIO_PLAYED")
        self.assertEqual(formula_event.event_type, "FORMULA_ASSISTANT_USED")

        stored_events = db.get_behavior_events(self.user.id, limit=10)
        self.assertEqual(len(stored_events), 2)
        self.assertIn("AUDIO_PLAYED", {event.event_type for event in stored_events})
        self.assertIn("FORMULA_ASSISTANT_USED", {event.event_type for event in stored_events})

    def test_calculate_comprehension_score_uses_behavior_events(self) -> None:
        behavior_events = [
            {"event_type": "HINT_REQUESTED", "metadata": {"question_id": "q1", "hint_number": 1}},
            {"event_type": "HINT_REQUESTED", "metadata": {"question_id": "q2", "hint_number": 2}},
            {"event_type": "QUIZ_RETRY", "metadata": {"question_id": "q1", "attempt_number": 2}},
            {"event_type": "RESPONSE_TIME", "metadata": {"question_id": "q1", "attempt_number": 1, "time_taken_seconds": 20}},
            {"event_type": "RESPONSE_TIME", "metadata": {"question_id": "q2", "attempt_number": 2, "time_taken_seconds": 90}},
        ]

        result = calculate_comprehension_score(behavior_events=behavior_events)

        self.assertEqual(result["learning_support_score"], 60.0)
        self.assertEqual(result["first_attempt_score"], 50.0)
        self.assertAlmostEqual(result["response_efficiency_score"], 72.2, places=1)

    def test_conceptual_answer_score_from_short_answer_evaluations(self) -> None:
        short_answers = [
            {"evaluation": {"score": 4, "max_score": 5}},
            {"evaluation": {"score": 3, "max_score": 5}},
        ]
        score = calculate_conceptual_answer_score(short_answers)
        self.assertEqual(score, 70.0)

        result = calculate_comprehension_score(
            quiz_evaluation={"correct_answers": 3, "total_questions": 4},
            short_answer_evaluations=short_answers,
        )
        self.assertEqual(result["conceptual_answer_score"], 70.0)
        self.assertIn("conceptual_answer", result["metric_breakdown"])

    def test_mode_tracking_events_persist(self) -> None:
        from services.behavior_tracking_service import (
            track_mode_entered,
            track_mode_exited,
            track_mode_switched,
        )

        entered_at = datetime.utcnow()
        track_mode_entered(self.user.id, mode="Read", document_id=1)
        track_mode_switched(self.user.id, previous_mode="Read", mode="Listen", document_id=1)
        track_mode_exited(self.user.id, mode="Listen", entered_at=entered_at, document_id=1)

        stored = db.get_behavior_events(self.user.id, limit=10)
        event_types = {event.event_type for event in stored}
        self.assertIn("MODE_ENTERED", event_types)
        self.assertIn("MODE_SWITCHED", event_types)
        self.assertIn("MODE_EXITED", event_types)


if __name__ == "__main__":
    unittest.main()
