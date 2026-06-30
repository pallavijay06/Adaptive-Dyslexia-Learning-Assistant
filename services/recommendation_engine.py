"""Service for generating personalized learning recommendations."""

from __future__ import annotations

import logging
from typing import Any, Optional

from database.db import (
    get_learner_profile,
    get_topic_progress,
    get_concept_mastery,
    get_learning_history,
    get_adaptive_preferences,
    get_quiz_question_responses,
    get_learning_support_logs,
)
from services.behavior_tracker import BehaviorTracker

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Generates personalized learning recommendations based on learner profile."""

    @staticmethod
    def recommend_learning_mode(user_id: int) -> Optional[str]:
        """Recommend a learning mode based on user preferences and performance.
        
        Args:
            user_id: The user ID.
            
        Returns:
            Recommended learning mode or None.
        """
        profile = get_learner_profile(user_id)
        if not profile:
            return None
        
        prefs = get_adaptive_preferences(user_id)
        
        # Check recent activity to infer preferences
        history = get_learning_history(user_id, limit=10)
        
        # Count mode usage
        mode_usage = {}
        for activity in history:
            mode_type = activity.activity_type
            mode_usage[mode_type] = mode_usage.get(mode_type, 0) + 1
        
        # If user has strong preference for audio, recommend audio
        if prefs and prefs.prefers_audio and mode_usage.get("audio", 0) > 2:
            return "Audio"
        
        # If user has strong preference for visual, recommend visual
        if prefs and prefs.prefers_visual_aids and mode_usage.get("visual", 0) > 2:
            return "Visual"
        
        # If profile shows preference for simplification (common for dyslexic learners)
        if profile.prefers_bullet_points and profile.avg_response_length_preference < 200:
            return "Simplified Notes"
        
        return None

    @staticmethod
    def recommend_practice_quiz(user_id: int) -> Optional[dict]:
        """Recommend a practice quiz on weak areas.
        
        Args:
            user_id: The user ID.
            
        Returns:
            Dictionary with quiz recommendation or None.
        """
        # Get all topic progress
        topics = get_topic_progress(user_id)
        
        # Filter for weak areas (mastery < 60%)
        weak_topics = [t for t in topics if t.is_weak_area and t.mastery_level < 0.6]
        
        if not weak_topics:
            return None
        
        # Recommend the weakest topic
        weakest = min(weak_topics, key=lambda t: t.mastery_level)
        
        return {
            "recommendation": f"Let's practice {weakest.topic}! You're at {weakest.mastery_level * 100:.0f}% mastery.",
            "topic": weakest.topic,
            "current_mastery": round(weakest.mastery_level * 100, 1),
            "type": "weak_area",
        }

    @staticmethod
    def recommend_concept_review(user_id: int, topic: str) -> Optional[dict]:
        """Recommend reviewing frequently missed concepts.
        
        Args:
            user_id: The user ID.
            topic: The topic to focus on.
            
        Returns:
            Dictionary with concept review recommendation or None.
        """
        weak_concepts = BehaviorTracker.identify_weak_concepts(user_id, topic)
        
        if not weak_concepts:
            return None
        
        # Get concept details
        concepts = get_concept_mastery(user_id, topic)
        frequently_missed = [c for c in concepts if c.is_frequently_missed]
        
        if not frequently_missed:
            return None
        
        # Pick the most frequently asked yet frequently missed concept
        worst_concept = max(frequently_missed, key=lambda c: c.times_asked)
        
        return {
            "recommendation": f"You've asked about '{worst_concept.concept}' {worst_concept.times_asked} times with {worst_concept.mastery_percentage:.0f}% success. Let's review it!",
            "concept": worst_concept.concept,
            "times_asked": worst_concept.times_asked,
            "success_rate": round(worst_concept.mastery_percentage, 1),
            "type": "concept_review",
        }

    @staticmethod
    def recommend_explanation_complexity(user_id: int) -> Optional[str]:
        """Recommend explanation complexity level.
        
        Args:
            user_id: The user ID.
            
        Returns:
            Recommended complexity level or None.
        """
        profile = get_learner_profile(user_id)
        if not profile:
            return None
        
        # If confidence is low, recommend simpler explanations
        if profile.confidence_level < 0.4:
            return "simple"
        
        # If confidence is high, recommend more detailed explanations
        if profile.confidence_level > 0.8:
            return "advanced"
        
        # Default to medium
        return "medium"

    @staticmethod
    def get_session_summary_recommendations(user_id: int) -> list[dict]:
        """Generate recommendations for end of session.
        
        Args:
            user_id: The user ID.
            
        Returns:
            List of recommendations for the session.
        """
        recommendations = []
        profile = get_learner_profile(user_id)
        
        if not profile:
            return recommendations
        
        # Recommendation 1: Learning mode suggestion
        mode = RecommendationEngine.recommend_learning_mode(user_id)
        if mode:
            recommendations.append({
                "type": "mode_suggestion",
                "title": "Suggested Learning Mode",
                "text": f"Based on your preferences, try learning with {mode}!",
                "mode": mode,
            })
        
        # Recommendation 2: Practice quiz on weak area
        quiz_rec = RecommendationEngine.recommend_practice_quiz(user_id)
        if quiz_rec:
            recommendations.append({
                "type": "quiz_suggestion",
                "title": "Practice Opportunity",
                "text": quiz_rec["recommendation"],
                "topic": quiz_rec["topic"],
            })
        
        # Recommendation 3: Study more frequently
        if profile.learning_frequency == "occasional" and profile.total_study_time_minutes > 60:
            recommendations.append({
                "type": "frequency_suggestion",
                "title": "Learning Frequency",
                "text": "You've made great progress! Studying regularly will help you learn faster.",
            })
        
        # Recommendation 4: Mastery milestone
        topics = get_topic_progress(user_id)
        strong_topics = [t for t in topics if t.is_strong_area]
        if strong_topics:
            recommendations.append({
                "type": "milestone",
                "title": "Great Progress!",
                "text": f"You've mastered {len(strong_topics)} topic(s)! Keep it up!",
                "topics": [t.topic for t in strong_topics],
            })
        
        return recommendations

    @staticmethod
    def should_recommend_adjustment(user_id: int) -> Optional[dict]:
        """Determine if any learning style adjustments should be recommended.
        
        Args:
            user_id: The user ID.
            
        Returns:
            Adjustment recommendation or None.
        """
        profile = get_learner_profile(user_id)
        prefs = get_adaptive_preferences(user_id)
        
        if not profile or not prefs:
            return None
        
        # If user has low confidence, suggest simpler explanations
        if profile.confidence_level < 0.35 and profile.explanation_complexity != "simple":
            return {
                "type": "complexity_adjustment",
                "current": profile.explanation_complexity,
                "suggested": "simple",
                "reason": "Lower complexity might help you understand better.",
            }
        
        # If user has high confidence but using simple explanations, suggest more detail
        if profile.confidence_level > 0.85 and profile.explanation_complexity == "simple":
            return {
                "type": "complexity_adjustment",
                "current": profile.explanation_complexity,
                "suggested": "advanced",
                "reason": "You're ready for more detailed explanations!",
            }
        
        # If user is using bullet points and has low confidence, suggest keeping them
        if profile.prefers_bullet_points and profile.confidence_level < 0.6:
            return {
                "type": "format_preference",
                "current": "detailed paragraphs",
                "suggested": "bullet points",
                "reason": "Breaking content into bullet points helps comprehension.",
            }
        
        return None

    @staticmethod
    def get_personalized_greeting(user_id: int, user_name: str) -> str:
        """Generate a personalized greeting based on learner history.
        
        Args:
            user_id: The user ID.
            user_name: The user's name.
            
        Returns:
            Personalized greeting text.
        """
        profile = get_learner_profile(user_id)
        
        if not profile:
            return f"Hello {user_name}! Ready to learn?"
        
        # Reference past studies if available
        if profile.unique_topics_studied > 0:
            return (
                f"Welcome back, {user_name}! You've studied {profile.unique_topics_studied} "
                f"topics so far. Let's continue learning!"
            )
        
        # Reference performance
        if profile.average_quiz_score > 0:
            return (
                f"Hi {user_name}! Your quiz average is {profile.average_quiz_score:.0f}%. "
                f"Let's improve together!"
            )
        
        return f"Hello {user_name}! Let's start learning!"

    @staticmethod
    def should_suggest_revision_quiz(user_id: int, topic: str) -> Optional[dict]:
        """Suggest a revision quiz if the user hasn't reviewed a topic recently.
        
        Args:
            user_id: The user ID.
            topic: The topic.
            
        Returns:
            Quiz suggestion or None.
        """
        topics = get_topic_progress(user_id, topic=topic)
        
        if not topics:
            return None
        
        topic_progress = topics[0]
        
        # If topic was studied but accuracy is moderate, suggest revision
        if 50 <= topic_progress.mastery_level * 100 < 80 and topic_progress.times_studied > 1:
            return {
                "type": "revision_quiz",
                "topic": topic,
                "mastery": round(topic_progress.mastery_level * 100, 1),
                "suggestion": f"You're at {topic_progress.mastery_level * 100:.0f}% on {topic}. "
                             f"A quick quiz might help solidify your understanding.",
            }
        
        return None
