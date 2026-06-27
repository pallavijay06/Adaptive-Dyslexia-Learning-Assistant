"""Service for tracking learner behavior and updating profiles."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from database.db import (
    save_learning_history,
    save_topic_progress,
    save_concept_mastery,
    get_topic_progress,
    get_concept_mastery,
    get_learning_history,
)
from services.learner_profile_service import LearnerProfileService

logger = logging.getLogger(__name__)


class BehaviorTracker:
    """Tracks learner behavior and updates learner profile accordingly."""

    @staticmethod
    def track_question(
        user_id: int,
        topic: Optional[str] = None,
        session_id: Optional[int] = None,
        duration_seconds: int = 0,
    ) -> None:
        """Track that a user asked a question.
        
        Args:
            user_id: The user ID.
            topic: The topic being asked about.
            session_id: Optional session ID.
            duration_seconds: Time spent on this activity.
        """
        # Record in learning history
        save_learning_history(
            user_id=user_id,
            activity_type="question",
            topic=topic,
            session_id=session_id,
            duration_seconds=duration_seconds,
        )
        
        # Update learner profile
        LearnerProfileService.update_question_asked(user_id)
        
        # Update topic progress if topic provided
        if topic:
            BehaviorTracker._update_topic_question_count(user_id, topic)
        
        logger.debug("Tracked question for user %s on topic %s", user_id, topic)

    @staticmethod
    def track_quiz_attempt(
        user_id: int,
        topic: str,
        score: float,
        total_questions: int,
        session_id: Optional[int] = None,
    ) -> None:
        """Track a quiz attempt and update related data.
        
        Args:
            user_id: The user ID.
            topic: The topic of the quiz.
            score: The score achieved (0-100).
            total_questions: Total questions in the quiz.
            session_id: Optional session ID.
        """
        # Record in learning history
        save_learning_history(
            user_id=user_id,
            activity_type="quiz",
            topic=topic,
            session_id=session_id,
            duration_seconds=0,
        )
        
        # Update topic progress
        progress = get_topic_progress(user_id, topic)
        if progress:
            progress_record = progress[0]
            updated_attempts = progress_record.quiz_attempts + 1
            best_score = max(progress_record.best_score, score)
        else:
            updated_attempts = 1
            best_score = score
        
        times_studied = 1 if not progress else progress[0].times_studied + 1
        
        save_topic_progress(
            user_id=user_id,
            topic=topic,
            questions_asked=progress[0].questions_asked if progress else 0,
            quiz_attempts=updated_attempts,
            best_score=best_score,
            times_studied=times_studied,
            mastery_level=_calculate_mastery(best_score),
            is_weak_area=best_score < 60,
            is_strong_area=best_score > 85,
        )
        
        # Update learner profile with new quiz score
        LearnerProfileService.update_quiz_score(user_id, score)
        
        logger.debug(
            "Tracked quiz for user %s on topic %s with score %.1f",
            user_id,
            topic,
            score,
        )

    @staticmethod
    def track_document_upload(user_id: int, session_id: Optional[int] = None) -> None:
        """Track that a user uploaded a document.
        
        Args:
            user_id: The user ID.
            session_id: Optional session ID.
        """
        save_learning_history(
            user_id=user_id,
            activity_type="upload",
            session_id=session_id,
        )
        
        # Update learner profile
        LearnerProfileService.update_document_upload(user_id)
        
        logger.debug("Tracked document upload for user %s", user_id)

    @staticmethod
    def track_mode_usage(
        user_id: int,
        mode: str,
        session_id: Optional[int] = None,
    ) -> None:
        """Track usage of a specific learning mode.
        
        Args:
            user_id: The user ID.
            mode: The mode (e.g., 'Audio', 'Visual', 'Simplified Notes', 'Quiz').
            session_id: Optional session ID.
        """
        save_learning_history(
            user_id=user_id,
            activity_type=mode.lower().replace(" ", "_"),
            session_id=session_id,
        )
        
        # Update preferred mode if this appears to be a strong preference
        _update_mode_preference(user_id, mode)
        
        logger.debug("Tracked %s mode usage for user %s", mode, user_id)

    @staticmethod
    def track_concept_question(
        user_id: int,
        topic: str,
        concept: str,
        is_correct: bool = False,
    ) -> None:
        """Track a question about a specific concept.
        
        Args:
            user_id: The user ID.
            topic: The topic.
            concept: The specific concept.
            is_correct: Whether the answer was correct.
        """
        existing = get_concept_mastery(user_id, topic)
        
        # Find if this concept exists
        concept_record = None
        for record in existing:
            if record.concept == concept:
                concept_record = record
                break
        
        if concept_record:
            times_asked = concept_record.times_asked + 1
            times_correct = concept_record.times_answered_correctly + (1 if is_correct else 0)
        else:
            times_asked = 1
            times_correct = 1 if is_correct else 0
        
        mastery_percentage = (times_correct / times_asked * 100) if times_asked > 0 else 0
        
        # Mark as frequently asked if asked 3+ times
        is_frequently_asked = times_asked >= 3
        
        # Mark as frequently missed if accuracy is low despite multiple attempts
        is_frequently_missed = times_asked >= 3 and mastery_percentage < 50
        
        save_concept_mastery(
            user_id=user_id,
            topic=topic,
            concept=concept,
            times_asked=times_asked,
            times_answered_correctly=times_correct,
            mastery_percentage=mastery_percentage,
            is_frequently_asked=is_frequently_asked,
            is_frequently_missed=is_frequently_missed,
        )
        
        logger.debug(
            "Tracked concept %s for user %s: mastery=%.1f%%",
            concept,
            user_id,
            mastery_percentage,
        )

    @staticmethod
    def track_study_session(
        user_id: int,
        duration_minutes: int,
        session_id: Optional[int] = None,
    ) -> None:
        """Track total study session duration.
        
        Args:
            user_id: The user ID.
            duration_minutes: Duration of the study session.
            session_id: Optional session ID.
        """
        LearnerProfileService.update_study_time(user_id, duration_minutes)
        logger.debug("Tracked study session for user %s: %d minutes", user_id, duration_minutes)

    @staticmethod
    def identify_weak_concepts(user_id: int, topic: str) -> list[str]:
        """Identify concepts that the user struggles with.
        
        Args:
            user_id: The user ID.
            topic: The topic to analyze.
            
        Returns:
            List of weak concepts.
        """
        concepts = get_concept_mastery(user_id, topic)
        weak_concepts = [
            c.concept for c in concepts
            if c.is_frequently_missed or c.mastery_percentage < 50
        ]
        return weak_concepts

    @staticmethod
    def identify_strong_concepts(user_id: int, topic: str) -> list[str]:
        """Identify concepts that the user has mastered.
        
        Args:
            user_id: The user ID.
            topic: The topic to analyze.
            
        Returns:
            List of strong concepts.
        """
        concepts = get_concept_mastery(user_id, topic)
        strong_concepts = [
            c.concept for c in concepts
            if c.mastery_percentage >= 80 and c.times_asked >= 2
        ]
        return strong_concepts

    @staticmethod
    def get_frequently_asked_concepts(user_id: int, topic: str, limit: int = 5) -> list[str]:
        """Get the most frequently asked concepts for a topic.
        
        Args:
            user_id: The user ID.
            topic: The topic.
            limit: Maximum number of concepts to return.
            
        Returns:
            List of frequently asked concepts.
        """
        concepts = get_concept_mastery(user_id, topic)
        sorted_concepts = sorted(concepts, key=lambda x: x.times_asked, reverse=True)
        return [c.concept for c in sorted_concepts[:limit]]

    @staticmethod
    def get_recent_activity_summary(user_id: int, limit: int = 20) -> dict:
        """Get a summary of recent learning activities.
        
        Args:
            user_id: The user ID.
            limit: Number of recent activities to summarize.
            
        Returns:
            Dictionary with activity summary.
        """
        history = get_learning_history(user_id, limit)
        
        activity_counts = {}
        topics_count = {}
        
        for activity in history:
            # Count activities
            activity_type = activity.activity_type
            activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1
            
            # Count topics
            if activity.topic:
                topics_count[activity.topic] = topics_count.get(activity.topic, 0) + 1
        
        return {
            "activity_counts": activity_counts,
            "topics_studied": list(topics_count.keys()),
            "most_studied_topic": max(topics_count, key=topics_count.get) if topics_count else None,
            "total_activities": len(history),
        }


def _calculate_mastery(score: float) -> float:
    """Convert a score to a mastery level (0-1).
    
    Args:
        score: Score from 0-100.
        
    Returns:
        Mastery level from 0-1.
    """
    return min(1.0, max(0.0, score / 100.0))


def _update_mode_preference(user_id: int, mode: str) -> None:
    """Update mode preference if there's a clear pattern.
    
    Args:
        user_id: The user ID.
        mode: The mode being used.
    """
    history = get_learning_history(user_id, limit=20)
    
    mode_key = mode.lower().replace(" ", "_")
    mode_count = sum(1 for h in history if mode_key in h.activity_type)
    
    # If used in last 20 activities more than 5 times, consider it a preference
    if mode_count > 5:
        LearnerProfileService.update_preferred_learning_mode(user_id, mode)
