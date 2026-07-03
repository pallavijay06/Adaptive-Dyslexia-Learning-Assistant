"""Test concept mastery tracking during quiz submissions."""

import unittest
import uuid
from datetime import datetime

from database import db
from services.behavior_tracker import BehaviorTracker


class ConceptMasteryTrackingTests(unittest.TestCase):
    """Test that concept mastery is properly tracked after quiz submissions."""

    def setUp(self) -> None:
        """Initialize database and test user."""
        db.init_db()
        self.user = db.save_user(
            name="Concept Mastery Tester",
            email=f"concept+{uuid.uuid4().hex[:8]}@example.com",
            password_hash="hash",
            age=16,
            grade="10",
            institution="Test School",
            field_of_study="Science",
        )
        self.topic = "Physics"
        self.concept = "Gravity"

    def test_track_concept_question_creates_new_record(self) -> None:
        """Test that tracking a concept creates a new concept_mastery record."""
        BehaviorTracker.track_concept_question(
            user_id=self.user.id,
            topic=self.topic,
            concept=self.concept,
            is_correct=True,
        )

        records = db.get_concept_mastery(self.user.id, self.topic)
        self.assertGreater(len(records), 0)

        record = records[0]
        self.assertEqual(record.concept, self.concept)
        self.assertEqual(record.times_asked, 1)
        self.assertEqual(record.times_answered_correctly, 1)
        self.assertEqual(record.mastery_percentage, 100.0)

    def test_track_concept_question_updates_existing_record(self) -> None:
        """Test that tracking the same concept increments counters."""
        # First question: correct
        BehaviorTracker.track_concept_question(
            user_id=self.user.id,
            topic=self.topic,
            concept=self.concept,
            is_correct=True,
        )

        # Second question: incorrect
        BehaviorTracker.track_concept_question(
            user_id=self.user.id,
            topic=self.topic,
            concept=self.concept,
            is_correct=False,
        )

        records = db.get_concept_mastery(self.user.id, self.topic)
        self.assertEqual(len(records), 1)

        record = records[0]
        self.assertEqual(record.times_asked, 2)
        self.assertEqual(record.times_answered_correctly, 1)
        self.assertAlmostEqual(record.mastery_percentage, 50.0, places=1)

    def test_frequently_asked_flag(self) -> None:
        """Test that is_frequently_asked is set when concept is asked 3+ times."""
        for i in range(3):
            is_correct = i < 2  # First two correct, third incorrect
            BehaviorTracker.track_concept_question(
                user_id=self.user.id,
                topic=self.topic,
                concept=self.concept,
                is_correct=is_correct,
            )

        records = db.get_concept_mastery(self.user.id, self.topic)
        record = records[0]

        self.assertTrue(record.is_frequently_asked)
        self.assertAlmostEqual(record.mastery_percentage, 66.67, places=1)

    def test_frequently_missed_flag(self) -> None:
        """Test that is_frequently_missed is set when mastery is low with 3+ attempts."""
        for i in range(4):
            is_correct = False  # All incorrect
            BehaviorTracker.track_concept_question(
                user_id=self.user.id,
                topic=self.topic,
                concept=self.concept,
                is_correct=is_correct,
            )

        records = db.get_concept_mastery(self.user.id, self.topic)
        record = records[0]

        self.assertTrue(record.is_frequently_asked)
        self.assertTrue(record.is_frequently_missed)
        self.assertEqual(record.mastery_percentage, 0.0)

    def test_last_asked_timestamp_updated(self) -> None:
        """Test that last_asked is updated with current timestamp."""
        BehaviorTracker.track_concept_question(
            user_id=self.user.id,
            topic=self.topic,
            concept=self.concept,
            is_correct=True,
        )

        records = db.get_concept_mastery(self.user.id, self.topic)
        record = records[0]

        self.assertIsNotNone(record.last_asked)
        # Verify timestamp is recent (within last minute)
        now = datetime.utcnow()
        diff = (now - record.last_asked).total_seconds()
        self.assertLess(diff, 60)

    def test_multiple_concepts_per_topic(self) -> None:
        """Test tracking multiple concepts within a topic."""
        concepts = ["Gravity", "Velocity", "Acceleration"]

        for concept in concepts:
            BehaviorTracker.track_concept_question(
                user_id=self.user.id,
                topic=self.topic,
                concept=concept,
                is_correct=True,
            )

        records = db.get_concept_mastery(self.user.id, self.topic)
        self.assertEqual(len(records), 3)

        tracked_concepts = {record.concept for record in records}
        self.assertEqual(tracked_concepts, set(concepts))

    def test_get_concept_mastery_returns_all_concepts(self) -> None:
        """Test that get_concept_mastery returns all tracked concepts for a topic."""
        concepts_data = {
            "Photosynthesis": True,   # correct
            "Chlorophyll": False,     # incorrect
            "Mitochondria": True,     # correct
        }

        for concept, is_correct in concepts_data.items():
            BehaviorTracker.track_concept_question(
                user_id=self.user.id,
                topic="Biology",
                concept=concept,
                is_correct=is_correct,
            )

        records = db.get_concept_mastery(self.user.id, "Biology")

        self.assertEqual(len(records), 3)
        mastery_dict = {record.concept: record.mastery_percentage for record in records}

        self.assertEqual(mastery_dict["Photosynthesis"], 100.0)
        self.assertEqual(mastery_dict["Chlorophyll"], 0.0)
        self.assertEqual(mastery_dict["Mitochondria"], 100.0)


if __name__ == "__main__":
    unittest.main()
