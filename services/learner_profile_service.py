"""Service for managing learner profiles for adaptive tutoring."""

from __future__ import annotations

import logging
from datetime import datetime

from database.db import (
    get_learner_profile,
    save_learner_profile,
    get_user_by_id,
)
from database.models import LearnerProfileRecord, UserRecord

logger = logging.getLogger(__name__)


class LearnerProfileService:
    """Manages learner profiles and initializes them from user data."""

    @staticmethod
    def initialize_profile(user: UserRecord) -> LearnerProfileRecord:
        """Initialize a learner profile from user registration data.
        
        Args:
            user: The user record with demographic information.
            
        Returns:
            The initialized learner profile.
        """
        # Determine initial explanation complexity based on age/grade
        explanation_complexity = _determine_initial_complexity(user)
        
        # Determine if bullet points are preferred (helpful for dyslexic learners)
        prefers_bullet_points = user.dyslexia_status == "Yes" or user.dyslexia_status == "Dyslexic"
        
        # Initialize profile with defaults from user info
        profile = save_learner_profile(
            user_id=user.id,
            total_study_time_minutes=0,
            documents_uploaded=0,
            unique_topics_studied=0,
            total_questions_asked=0,
            average_quiz_score=0.0,
            preferred_learning_mode="Simplified Notes",
            learning_frequency="occasional",
            confidence_level=0.5,
            explanation_complexity=explanation_complexity,
            prefers_examples=True,
            prefers_analogies=True,
            prefers_bullet_points=prefers_bullet_points,
            avg_response_length_preference=150 if prefers_bullet_points else 250,
        )
        
        logger.info(
            "Initialized learner profile for user %s with complexity=%s",
            user.id,
            explanation_complexity,
        )
        return profile

    @staticmethod
    def get_or_create_profile(user_id: int) -> LearnerProfileRecord:
        """Get existing profile or create a new one if it doesn't exist.
        
        Args:
            user_id: The user ID.
            
        Returns:
            The learner profile.
        """
        profile = get_learner_profile(user_id)
        if profile:
            return profile
        
        # If no profile exists, create a default one
        user = get_user_by_id(user_id)
        if not user:
            logger.warning("User %s not found", user_id)
            # Create a minimal default profile
            return save_learner_profile(user_id=user_id)
        
        return LearnerProfileService.initialize_profile(user)

    @staticmethod
    def update_study_time(
        user_id: int,
        additional_minutes: int,
    ) -> LearnerProfileRecord:
        """Update total study time for a user.
        
        Args:
            user_id: The user ID.
            additional_minutes: Minutes to add to total study time.
            
        Returns:
            Updated learner profile.
        """
        profile = get_learner_profile(user_id)
        if not profile:
            profile = LearnerProfileService.get_or_create_profile(user_id)
        
        new_total = profile.total_study_time_minutes + additional_minutes
        
        # Update learning frequency based on study time
        learning_frequency = _infer_learning_frequency(new_total)
        
        updated = save_learner_profile(
            user_id=user_id,
            total_study_time_minutes=new_total,
            documents_uploaded=profile.documents_uploaded,
            unique_topics_studied=profile.unique_topics_studied,
            total_questions_asked=profile.total_questions_asked,
            average_quiz_score=profile.average_quiz_score,
            preferred_learning_mode=profile.preferred_learning_mode,
            learning_frequency=learning_frequency,
            confidence_level=profile.confidence_level,
            explanation_complexity=profile.explanation_complexity,
            prefers_examples=profile.prefers_examples,
            prefers_analogies=profile.prefers_analogies,
            prefers_bullet_points=profile.prefers_bullet_points,
            avg_response_length_preference=profile.avg_response_length_preference,
        )
        return updated

    @staticmethod
    def update_document_upload(user_id: int) -> LearnerProfileRecord:
        """Increment document upload count.
        
        Args:
            user_id: The user ID.
            
        Returns:
            Updated learner profile.
        """
        profile = get_learner_profile(user_id)
        if not profile:
            profile = LearnerProfileService.get_or_create_profile(user_id)
        
        updated = save_learner_profile(
            user_id=user_id,
            total_study_time_minutes=profile.total_study_time_minutes,
            documents_uploaded=profile.documents_uploaded + 1,
            unique_topics_studied=profile.unique_topics_studied,
            total_questions_asked=profile.total_questions_asked,
            average_quiz_score=profile.average_quiz_score,
            preferred_learning_mode=profile.preferred_learning_mode,
            learning_frequency=profile.learning_frequency,
            confidence_level=profile.confidence_level,
            explanation_complexity=profile.explanation_complexity,
            prefers_examples=profile.prefers_examples,
            prefers_analogies=profile.prefers_analogies,
            prefers_bullet_points=profile.prefers_bullet_points,
            avg_response_length_preference=profile.avg_response_length_preference,
        )
        return updated

    @staticmethod
    def update_topic_studied(user_id: int) -> LearnerProfileRecord:
        """Increment unique topics studied count.
        
        Args:
            user_id: The user ID.
            
        Returns:
            Updated learner profile.
        """
        profile = get_learner_profile(user_id)
        if not profile:
            profile = LearnerProfileService.get_or_create_profile(user_id)
        
        updated = save_learner_profile(
            user_id=user_id,
            total_study_time_minutes=profile.total_study_time_minutes,
            documents_uploaded=profile.documents_uploaded,
            unique_topics_studied=profile.unique_topics_studied + 1,
            total_questions_asked=profile.total_questions_asked,
            average_quiz_score=profile.average_quiz_score,
            preferred_learning_mode=profile.preferred_learning_mode,
            learning_frequency=profile.learning_frequency,
            confidence_level=profile.confidence_level,
            explanation_complexity=profile.explanation_complexity,
            prefers_examples=profile.prefers_examples,
            prefers_analogies=profile.prefers_analogies,
            prefers_bullet_points=profile.prefers_bullet_points,
            avg_response_length_preference=profile.avg_response_length_preference,
        )
        return updated

    @staticmethod
    def update_question_asked(user_id: int) -> LearnerProfileRecord:
        """Increment total questions asked count.
        
        Args:
            user_id: The user ID.
            
        Returns:
            Updated learner profile.
        """
        profile = get_learner_profile(user_id)
        if not profile:
            profile = LearnerProfileService.get_or_create_profile(user_id)
        
        # Infer confidence level from question frequency
        new_question_count = profile.total_questions_asked + 1
        
        updated = save_learner_profile(
            user_id=user_id,
            total_study_time_minutes=profile.total_study_time_minutes,
            documents_uploaded=profile.documents_uploaded,
            unique_topics_studied=profile.unique_topics_studied,
            total_questions_asked=new_question_count,
            average_quiz_score=profile.average_quiz_score,
            preferred_learning_mode=profile.preferred_learning_mode,
            learning_frequency=profile.learning_frequency,
            confidence_level=profile.confidence_level,
            explanation_complexity=profile.explanation_complexity,
            prefers_examples=profile.prefers_examples,
            prefers_analogies=profile.prefers_analogies,
            prefers_bullet_points=profile.prefers_bullet_points,
            avg_response_length_preference=profile.avg_response_length_preference,
        )
        return updated

    @staticmethod
    def update_quiz_score(user_id: int, new_score: float) -> LearnerProfileRecord:
        """Update average quiz score.
        
        Args:
            user_id: The user ID.
            new_score: The new quiz score (0-100).
            
        Returns:
            Updated learner profile.
        """
        profile = get_learner_profile(user_id)
        if not profile:
            profile = LearnerProfileService.get_or_create_profile(user_id)
        
        # Calculate new average
        total_attempts = profile.total_questions_asked or 1
        old_total = (profile.average_quiz_score * total_attempts)
        new_average = (old_total + new_score) / (total_attempts + 1)
        
        # Infer confidence level based on quiz performance
        confidence_level = min(1.0, max(0.0, new_average / 100.0))
        
        updated = save_learner_profile(
            user_id=user_id,
            total_study_time_minutes=profile.total_study_time_minutes,
            documents_uploaded=profile.documents_uploaded,
            unique_topics_studied=profile.unique_topics_studied,
            total_questions_asked=profile.total_questions_asked,
            average_quiz_score=new_average,
            preferred_learning_mode=profile.preferred_learning_mode,
            learning_frequency=profile.learning_frequency,
            confidence_level=confidence_level,
            explanation_complexity=profile.explanation_complexity,
            prefers_examples=profile.prefers_examples,
            prefers_analogies=profile.prefers_analogies,
            prefers_bullet_points=profile.prefers_bullet_points,
            avg_response_length_preference=profile.avg_response_length_preference,
        )
        return updated

    @staticmethod
    def update_preferred_learning_mode(user_id: int, mode: str) -> LearnerProfileRecord:
        """Update the preferred learning mode.
        
        Args:
            user_id: The user ID.
            mode: The learning mode (e.g., 'Audio', 'Visual', 'Quiz', 'Simplified Notes').
            
        Returns:
            Updated learner profile.
        """
        profile = get_learner_profile(user_id)
        if not profile:
            profile = LearnerProfileService.get_or_create_profile(user_id)
        
        updated = save_learner_profile(
            user_id=user_id,
            total_study_time_minutes=profile.total_study_time_minutes,
            documents_uploaded=profile.documents_uploaded,
            unique_topics_studied=profile.unique_topics_studied,
            total_questions_asked=profile.total_questions_asked,
            average_quiz_score=profile.average_quiz_score,
            preferred_learning_mode=mode,
            learning_frequency=profile.learning_frequency,
            confidence_level=profile.confidence_level,
            explanation_complexity=profile.explanation_complexity,
            prefers_examples=profile.prefers_examples,
            prefers_analogies=profile.prefers_analogies,
            prefers_bullet_points=profile.prefers_bullet_points,
            avg_response_length_preference=profile.avg_response_length_preference,
        )
        return updated

    @staticmethod
    def get_profile_summary(user_id: int) -> dict:
        """Get a summary of the learner profile.
        
        Args:
            user_id: The user ID.
            
        Returns:
            Dictionary with profile summary data.
        """
        profile = get_learner_profile(user_id)
        if not profile:
            return {}
        
        return {
            "total_study_time_minutes": profile.total_study_time_minutes,
            "documents_uploaded": profile.documents_uploaded,
            "unique_topics_studied": profile.unique_topics_studied,
            "total_questions_asked": profile.total_questions_asked,
            "average_quiz_score": round(profile.average_quiz_score, 2),
            "preferred_learning_mode": profile.preferred_learning_mode,
            "learning_frequency": profile.learning_frequency,
            "confidence_level": round(profile.confidence_level, 2),
            "explanation_complexity": profile.explanation_complexity,
            "prefers_examples": profile.prefers_examples,
            "prefers_analogies": profile.prefers_analogies,
            "prefers_bullet_points": profile.prefers_bullet_points,
            "avg_response_length_preference": profile.avg_response_length_preference,
        }


def _determine_initial_complexity(user: UserRecord) -> str:
    """Determine initial explanation complexity based on user age/grade.
    
    Args:
        user: The user record.
        
    Returns:
        One of: 'simple', 'medium', 'advanced'.
    """
    try:
        age = user.age or 0
        grade_str = user.grade or ""
        
        # Try to extract numeric grade
        grade_num = 0
        for word in grade_str.split():
            try:
                grade_num = int(word)
                break
            except (ValueError, AttributeError):
                pass
        
        # Determine complexity
        if age < 10 or grade_num < 5:
            return "simple"
        elif age < 15 or grade_num < 10:
            return "medium"
        else:
            return "advanced"
    except (TypeError, AttributeError):
        return "medium"


def _infer_learning_frequency(total_minutes: int) -> str:
    """Infer learning frequency from total study time.
    
    Args:
        total_minutes: Total study time in minutes.
        
    Returns:
        One of: 'daily', 'weekly', 'occasional'.
    """
    if total_minutes < 60:  # Less than 1 hour
        return "occasional"
    elif total_minutes < 300:  # Less than 5 hours
        return "weekly"
    else:
        return "daily"
