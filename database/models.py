"""Database table definitions and query result helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class UserRecord:
    id: int | None
    name: str
    email: str
    password_hash: str
    created_at: datetime
    age: int | None = None
    grade: str | None = None
    institution: str | None = None
    field_of_study: str | None = None
    preferred_language: str | None = None
    learning_goal: str | None = None
    dyslexia_status: str | None = None
    registration_date: datetime | None = None
    last_login: datetime | None = None
    last_logout: datetime | None = None
    total_sessions: int = 0
    total_learning_minutes: int = 0


@dataclass(frozen=True)
class DocumentRecord:
    id: int | None
    user_id: int
    file_name: str
    file_type: str
    document_text: str
    upload_time: datetime


@dataclass(frozen=True)
class ChatRecord:
    id: int | None
    user_id: int
    document_id: int | None
    user_message: str
    ai_response: str
    timestamp: datetime


@dataclass(frozen=True)
class QuizAttemptRecord:
    id: int | None
    user_id: int
    topic: str
    score: int
    total_questions: int
    timestamp: datetime
    comprehension_score: float = 0.0
    feedback_strengths: str = ""
    feedback_weaknesses: str = ""
    feedback_recommended_concepts: str = ""
    feedback_suggested_learning_mode: str = ""


@dataclass(frozen=True)
class QuizQuestionResponseRecord:
    id: int | None
    user_id: int
    quiz_id: int | None
    question_id: str
    question_type: str
    topic: str | None
    difficulty: str | None
    question_start_time: datetime
    question_submit_time: datetime
    time_taken_seconds: int
    is_correct: bool
    created_at: datetime
    attempt_number: int = 1  # NEW: Track which attempt this was (1, 2, 3, ...)
    first_attempt_success: bool = False  # NEW: True if correct on first attempt


@dataclass(frozen=True)
class LearningSupportLogRecord:
    id: int | None
    user_id: int
    quiz_id: int | None
    question_id: str
    support_type: str
    timestamp: datetime
    created_at: datetime


@dataclass(frozen=True)
class LearningSessionRecord:
    id: int | None
    user_id: int
    mode_used: str
    duration: int
    timestamp: datetime
    login_time: datetime | None = None
    logout_time: datetime | None = None
    session_duration_minutes: int = 0


@dataclass(frozen=True)
class UserPreferencesRecord:
    id: int | None
    user_id: int
    preferred_mode: str
    reading_level: str


@dataclass(frozen=True)
class LearnerProfileRecord:
    """Stores comprehensive learner profile for adaptive tutoring."""
    id: int | None
    user_id: int
    total_study_time_minutes: int = 0
    documents_uploaded: int = 0
    unique_topics_studied: int = 0
    total_questions_asked: int = 0
    average_quiz_score: float = 0.0
    preferred_learning_mode: str | None = None
    learning_frequency: str = "occasional"  # daily, weekly, occasional
    confidence_level: float = 0.5  # 0-1 scale
    explanation_complexity: str = "medium"  # simple, medium, advanced
    prefers_examples: bool = True
    prefers_analogies: bool = True
    prefers_bullet_points: bool = True
    avg_response_length_preference: int = 200  # words
    comprehension_score: float | None = None
    comprehension_level: str | None = None
    quiz_accuracy_score: float | None = None
    conceptual_answer_score: float | None = None
    learning_support_score: float | None = None
    first_attempt_score: float | None = None
    response_efficiency_score: float | None = None
    metric_breakdown: dict[str, Any] | None = None
    learner_model_metadata: dict[str, Any] | None = None
    learning_behaviour_analytics_score: float | None = None
    learning_behaviour_analytics_level: str | None = None
    mode_engagement_score: float | None = None
    mode_switching_score: float | None = None
    feature_utilization_score: float | None = None
    post_mode_improvement_score: float | None = None
    mode_retention_score: float | None = None
    learning_behaviour_analytics_metric_breakdown: dict[str, Any] | None = None
    last_updated: datetime | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class LearningHistoryRecord:
    """Tracks individual learning activities and interactions."""
    id: int | None
    user_id: int
    session_id: int | None
    activity_type: str  # 'question', 'quiz', 'upload', 'read', 'listen', 'visual'
    topic: str | None
    duration_seconds: int = 0
    timestamp: datetime | None = None


@dataclass(frozen=True)
class BehaviorEventRecord:
    """Stores generic learner behaviour events for future analytics."""
    id: int | None
    user_id: int
    session_id: int | None
    event_type: str
    event_timestamp: datetime
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class LearningModeSessionRecord:
    """Stores a completed document-to-quiz learning session for effectiveness analysis."""
    id: int | None
    session_id: str
    user_id: int
    document_id: int | None
    document_name: str | None
    timestamp: datetime | None
    modes_used: list[str]
    quiz_accuracy: float
    comprehension_score: float


@dataclass(frozen=True)
class TopicProgressRecord:
    """Tracks progress on specific topics."""
    id: int | None
    user_id: int
    topic: str
    questions_asked: int = 0
    quiz_attempts: int = 0
    best_score: float = 0.0
    last_studied: datetime | None = None
    times_studied: int = 0
    mastery_level: float = 0.0  # 0-1 scale
    is_weak_area: bool = False
    is_strong_area: bool = False


@dataclass(frozen=True)
class ConceptMasteryRecord:
    """Tracks mastery level of individual concepts."""
    id: int | None
    user_id: int
    topic: str
    concept: str
    times_asked: int = 0
    times_answered_correctly: int = 0
    mastery_percentage: float = 0.0
    last_asked: datetime | None = None
    is_frequently_asked: bool = False
    is_frequently_missed: bool = False


@dataclass(frozen=True)
class AdaptivePreferencesRecord:
    """Stores adaptive conversation preferences learned from user behavior."""
    id: int | None
    user_id: int
    preferred_explanation_complexity: str = "medium"  # simple, medium, advanced
    prefers_visual_aids: bool = True
    prefers_audio: bool = False
    prefers_bullet_points: bool = True
    prefers_short_sentences: bool = False
    prefers_analogies: bool = True
    prefers_real_world_examples: bool = True
    avg_successful_response_length: int = 200
    response_time_patience: int = 60  # seconds
    quiz_difficulty_preference: str = "adaptive"  # easy, medium, hard, adaptive
    last_updated: datetime | None = None
