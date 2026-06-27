"""Main Adaptive AI Tutor service that orchestrates personalized learning."""

from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime

from database.db import (
    get_learner_profile,
    get_user_by_id,
    get_adaptive_preferences,
    save_adaptive_preferences,
)
from services.learner_profile_service import LearnerProfileService
from services.behavior_tracker import BehaviorTracker
from services.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)


class AdaptiveAITutor:
    """Main adaptive AI tutor service that personalizes responses and tracks learning."""

    def __init__(self, user_id: int, document_id: Optional[int] = None):
        """Initialize the adaptive tutor for a user.
        
        Args:
            user_id: The user ID.
            document_id: Optional ID of the document being studied.
        """
        self.user_id = user_id
        self.document_id = document_id
        self.user = get_user_by_id(user_id)
        self.profile = LearnerProfileService.get_or_create_profile(user_id)
        self.preferences = get_adaptive_preferences(user_id) or self._initialize_preferences()

    def _initialize_preferences(self):
        """Initialize adaptive preferences if they don't exist."""
        user = self.user
        if not user:
            return None
        
        # Determine preferences based on user profile
        is_dyslexic = user.dyslexia_status == "Yes" or user.dyslexia_status == "Dyslexic"
        
        prefs = save_adaptive_preferences(
            user_id=self.user_id,
            preferred_explanation_complexity=self.profile.explanation_complexity,
            prefers_visual_aids=True,
            prefers_audio=False,
            prefers_bullet_points=is_dyslexic,
            prefers_short_sentences=is_dyslexic,
            prefers_analogies=True,
            prefers_real_world_examples=True,
            avg_successful_response_length=150 if is_dyslexic else 250,
            response_time_patience=60,
            quiz_difficulty_preference="adaptive",
        )
        return prefs

    def prepare_response_context(self, topic: Optional[str] = None) -> dict:
        """Prepare context for adapting AI responses.
        
        Args:
            topic: Optional topic being discussed.
            
        Returns:
            Dictionary with adaptation context.
        """
        context = {
            "user_name": self.user.name if self.user else "Student",
            "user_age": self.user.age if self.user else None,
            "user_grade": self.user.grade if self.user else None,
            "is_dyslexic": self.user.dyslexia_status == "Yes" if self.user else False,
            "explanation_complexity": self.profile.explanation_complexity,
            "prefers_examples": self.profile.prefers_examples,
            "prefers_analogies": self.profile.prefers_analogies,
            "prefers_bullet_points": self.profile.prefers_bullet_points,
            "avg_response_length": self.profile.avg_response_length_preference,
            "confidence_level": self.profile.confidence_level,
            "learning_frequency": self.profile.learning_frequency,
            "preferred_mode": self.profile.preferred_learning_mode,
            "topic": topic,
        }
        
        # Add weak concept information if available
        if topic:
            weak_concepts = BehaviorTracker.identify_weak_concepts(self.user_id, topic)
            strong_concepts = BehaviorTracker.identify_strong_concepts(self.user_id, topic)
            context["weak_concepts"] = weak_concepts
            context["strong_concepts"] = strong_concepts
        
        return context

    def track_interaction(
        self,
        interaction_type: str,
        topic: Optional[str] = None,
        success: Optional[bool] = None,
        duration_seconds: int = 0,
        session_id: Optional[int] = None,
    ) -> None:
        """Track a learning interaction.
        
        Args:
            interaction_type: Type of interaction (e.g., 'question', 'quiz', 'upload').
            topic: The topic being studied.
            success: Whether the interaction was successful (for quizzes).
            duration_seconds: Duration of the interaction.
            session_id: Optional session ID.
        """
        if interaction_type == "question":
            BehaviorTracker.track_question(
                self.user_id,
                topic=topic,
                session_id=session_id,
                duration_seconds=duration_seconds,
            )
        elif interaction_type == "quiz":
            # This will be called separately with score
            pass
        elif interaction_type == "upload":
            BehaviorTracker.track_document_upload(self.user_id, session_id)
        else:
            BehaviorTracker.track_mode_usage(self.user_id, interaction_type, session_id)

    def record_quiz_attempt(
        self,
        topic: str,
        score: float,
        total_questions: int,
        session_id: Optional[int] = None,
    ) -> None:
        """Record a quiz attempt and update learner profile.
        
        Args:
            topic: The quiz topic.
            score: Score achieved (0-100).
            total_questions: Total questions in quiz.
            session_id: Optional session ID.
        """
        BehaviorTracker.track_quiz_attempt(
            self.user_id,
            topic=topic,
            score=score,
            total_questions=total_questions,
            session_id=session_id,
        )

    def record_concept_question(
        self,
        topic: str,
        concept: str,
        is_correct: bool = False,
    ) -> None:
        """Record a question about a specific concept.
        
        Args:
            topic: The topic.
            concept: The specific concept.
            is_correct: Whether the answer was correct.
        """
        BehaviorTracker.track_concept_question(
            self.user_id,
            topic=topic,
            concept=concept,
            is_correct=is_correct,
        )

    def get_session_greeting(self) -> str:
        """Get a personalized greeting for the session.
        
        Returns:
            Personalized greeting text.
        """
        user_name = self.user.name if self.user else "Student"
        return RecommendationEngine.get_personalized_greeting(self.user_id, user_name)

    def get_adaptive_recommendations(self) -> list[dict]:
        """Get adaptive recommendations for the learner.
        
        Returns:
            List of recommendation dictionaries.
        """
        return RecommendationEngine.get_session_summary_recommendations(self.user_id)

    def should_recommend_mode(self) -> Optional[str]:
        """Check if a learning mode should be recommended.
        
        Returns:
            Recommended mode or None.
        """
        return RecommendationEngine.recommend_learning_mode(self.user_id)

    def should_recommend_practice(self) -> Optional[dict]:
        """Check if practice quiz should be recommended.
        
        Returns:
            Practice recommendation or None.
        """
        return RecommendationEngine.recommend_practice_quiz(self.user_id)

    def get_adjustment_suggestion(self) -> Optional[dict]:
        """Check if learning style adjustment should be recommended.
        
        Returns:
            Adjustment suggestion or None.
        """
        return RecommendationEngine.should_recommend_adjustment(self.user_id)

    def generate_adaptive_system_prompt(self) -> str:
        """Generate a system prompt for the LLM adapted to the learner.
        
        Returns:
            System prompt text adapted to learner preferences.
        """
        prompt = f"""You are an Adaptive AI Tutor personalized for {self.user.name if self.user else 'a student'}.

## Learner Profile
- Age: {self.user.age if self.user else 'unknown'}
- Grade: {self.user.grade if self.user else 'unknown'}
- Dyslexia Status: {'Yes' if self.user and self.user.dyslexia_status == 'Yes' else 'No'}
- Current Confidence Level: {self.profile.confidence_level * 100:.0f}%
- Topics Studied: {self.profile.unique_topics_studied}

## Adaptive Guidelines
1. **Explanation Complexity**: Use "{self.profile.explanation_complexity}" level explanations
   - Simple: Use basic vocabulary, short sentences, concrete examples
   - Medium: Use standard terminology, balanced depth
   - Advanced: Use technical terms, detailed analysis

2. **Format Preferences**:
   - Use bullet points: {'Yes' if self.profile.prefers_bullet_points else 'No'}
   - Include examples: {'Yes' if self.profile.prefers_examples else 'No'}
   - Use analogies: {'Yes' if self.profile.prefers_analogies else 'No'}

3. **Response Length**: Aim for approximately {self.profile.avg_response_length_preference} words

4. **Dyslexia Accommodations**: {'Enable' if self.user and self.user.dyslexia_status == 'Yes' else 'Standard'}
   - Shorter sentences and paragraphs
   - Clear spacing
   - Simpler vocabulary
   - Visual breaks with subheadings

5. **Learning Mode Preference**: {self.profile.preferred_learning_mode}
   - Suggest this mode when appropriate
   - Offer alternatives if effectiveness decreases

6. **Personalization**:
   - Remember previous topics studied
   - Reference past learning
   - Build on existing knowledge
   - Celebrate progress

## Previous Learning Context
- Topics Recently Studied: {self._get_recent_topics()}
- Average Quiz Score: {self.profile.average_quiz_score:.1f}%
- Preferred Learning Frequency: {self.profile.learning_frequency}

## Adaptive Behavior
- If confidence is low (< 0.4): Use simpler explanations, more examples, ask for understanding
- If confidence is high (> 0.8): Provide deeper analysis, challenge with advanced concepts
- If learner struggles with a concept: Offer multiple explanation angles
- If learner asks repeatedly about same topic: Flag as weak area, suggest targeted practice

## Important
- Be encouraging and supportive
- Provide specific feedback, not generic praise
- Track what topics are mentioned - the system will record this for profile updates
- Suggest follow-up questions to deepen understanding
- Offer mode-specific suggestions based on learner preferences
"""
        return prompt

    def _get_recent_topics(self) -> str:
        """Get recently studied topics for context.
        
        Returns:
            Comma-separated list of recent topics.
        """
        activity_summary = BehaviorTracker.get_recent_activity_summary(self.user_id)
        topics = activity_summary.get("topics_studied", [])
        if topics:
            return ", ".join(topics[:5])  # Limit to 5 recent topics
        return "None yet"

    def get_learner_summary(self) -> dict:
        """Get a complete summary of learner progress and profile.
        
        Returns:
            Dictionary with learner summary data.
        """
        return {
            "user_info": {
                "name": self.user.name if self.user else "Unknown",
                "age": self.user.age if self.user else None,
                "grade": self.user.grade if self.user else None,
                "institution": self.user.institution if self.user else None,
                "dyslexia_status": self.user.dyslexia_status if self.user else None,
            },
            "profile": LearnerProfileService.get_profile_summary(self.user_id),
            "activity_summary": BehaviorTracker.get_recent_activity_summary(self.user_id),
            "recommendations": self.get_adaptive_recommendations(),
        }

    def should_store_conversation(self) -> bool:
        """Determine if conversation should be stored and analyzed.
        
        Returns:
            True if conversation should be stored.
        """
        # Always store for later analysis and personalization
        return True
