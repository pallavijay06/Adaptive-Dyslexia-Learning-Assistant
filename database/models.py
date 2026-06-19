"""Database table definitions and query result helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UserRecord:
    id: int | None
    name: str
    email: str
    password_hash: str
    created_at: datetime


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


@dataclass(frozen=True)
class LearningSessionRecord:
    id: int | None
    user_id: int
    mode_used: str
    duration: int
    timestamp: datetime


@dataclass(frozen=True)
class UserPreferencesRecord:
    id: int | None
    user_id: int
    preferred_mode: str
    reading_level: str
