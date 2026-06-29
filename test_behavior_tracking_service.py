import unittest
import uuid

from database import db
from services.behavior_tracking_service import (
    track_audio_played,
    track_document_opened,
    track_event,
    track_formula_assistant_used,
)


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


if __name__ == "__main__":
    unittest.main()
