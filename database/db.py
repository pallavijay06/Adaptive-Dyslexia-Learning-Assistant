"""SQLite database access layer for cHEAL learning assistant."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from sqlite3 import Connection, IntegrityError

from database.models import (
    ChatRecord,
    DocumentRecord,
    LearningSessionRecord,
    QuizAttemptRecord,
    UserPreferencesRecord,
    UserRecord,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data.sqlite"


def _get_connection() -> Connection:
    """Return a SQLite connection with foreign key enforcement enabled."""
    connection = sqlite3.connect(DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    """Create database tables if they do not exist."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                document_text TEXT NOT NULL,
                upload_time TIMESTAMP NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                document_id INTEGER,
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS learning_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mode_used TEXT NOT NULL,
                duration INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                preferred_mode TEXT NOT NULL,
                reading_level TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


def save_user(name: str, email: str, password_hash: str) -> UserRecord:
    """Insert a new user and return the saved user record."""
    query = """
        INSERT INTO users (name, email, password_hash, created_at)
        VALUES (?, ?, ?, ?)
    """
    now = datetime.utcnow()
    try:
        with _get_connection() as connection:
            cursor = connection.execute(query, (name, email, password_hash, now))
            user_id = cursor.lastrowid
    except IntegrityError as exc:
        raise ValueError("A user with that email already exists.") from exc

    return UserRecord(id=user_id, name=name, email=email, password_hash=password_hash, created_at=now)


def get_user(email: str) -> UserRecord | None:
    """Return a user record by email, or None if no user exists."""
    query = "SELECT * FROM users WHERE email = ?"
    with _get_connection() as connection:
        row = connection.execute(query, (email,)).fetchone()
    if row is None:
        return None
    return UserRecord(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        password_hash=row["password_hash"],
        created_at=row["created_at"],
    )


def save_document(
    user_id: int,
    file_name: str,
    file_type: str,
    document_text: str,
) -> DocumentRecord:
    """Save uploaded document metadata and extracted text."""
    query = """
        INSERT INTO documents (user_id, file_name, file_type, document_text, upload_time)
        VALUES (?, ?, ?, ?, ?)
    """
    now = datetime.utcnow()
    with _get_connection() as connection:
        cursor = connection.execute(query, (user_id, file_name, file_type, document_text, now))
        document_id = cursor.lastrowid
    return DocumentRecord(
        id=document_id,
        user_id=user_id,
        file_name=file_name,
        file_type=file_type,
        document_text=document_text,
        upload_time=now,
    )


def get_document(document_id: int) -> DocumentRecord | None:
    """Return a document record by id."""
    query = "SELECT * FROM documents WHERE id = ?"
    with _get_connection() as connection:
        row = connection.execute(query, (document_id,)).fetchone()
    if row is None:
        return None
    return DocumentRecord(
        id=row["id"],
        user_id=row["user_id"],
        file_name=row["file_name"],
        file_type=row["file_type"],
        document_text=row["document_text"],
        upload_time=row["upload_time"],
    )


def save_chat(
    user_id: int,
    document_id: int | None,
    user_message: str,
    ai_response: str,
) -> ChatRecord:
    """Save a single chat turn for a user and optional document."""
    query = """
        INSERT INTO chat_history (user_id, document_id, user_message, ai_response, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """
    now = datetime.utcnow()
    with _get_connection() as connection:
        cursor = connection.execute(query, (user_id, document_id, user_message, ai_response, now))
        chat_id = cursor.lastrowid
    return ChatRecord(
        id=chat_id,
        user_id=user_id,
        document_id=document_id,
        user_message=user_message,
        ai_response=ai_response,
        timestamp=now,
    )


def get_chat_history(user_id: int, limit: int = 100) -> list[ChatRecord]:
    """Return recent chat history for a user."""
    query = """
        SELECT * FROM chat_history
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    with _get_connection() as connection:
        rows = connection.execute(query, (user_id, limit)).fetchall()
    return [
        ChatRecord(
            id=row["id"],
            user_id=row["user_id"],
            document_id=row["document_id"],
            user_message=row["user_message"],
            ai_response=row["ai_response"],
            timestamp=row["timestamp"],
        )
        for row in rows
    ]


def save_quiz_score(
    user_id: int,
    topic: str,
    score: int,
    total_questions: int,
) -> QuizAttemptRecord:
    """Save a completed quiz attempt."""
    query = """
        INSERT INTO quiz_attempts (user_id, topic, score, total_questions, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """
    now = datetime.utcnow()
    with _get_connection() as connection:
        cursor = connection.execute(query, (user_id, topic, score, total_questions, now))
        attempt_id = cursor.lastrowid
    return QuizAttemptRecord(
        id=attempt_id,
        user_id=user_id,
        topic=topic,
        score=score,
        total_questions=total_questions,
        timestamp=now,
    )


def get_quiz_history(user_id: int, limit: int = 100) -> list[QuizAttemptRecord]:
    """Return recent quiz attempts for a user."""
    query = """
        SELECT * FROM quiz_attempts
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    with _get_connection() as connection:
        rows = connection.execute(query, (user_id, limit)).fetchall()
    return [
        QuizAttemptRecord(
            id=row["id"],
            user_id=row["user_id"],
            topic=row["topic"],
            score=row["score"],
            total_questions=row["total_questions"],
            timestamp=row["timestamp"],
        )
        for row in rows
    ]


def save_learning_session(user_id: int, mode_used: str, duration: int) -> LearningSessionRecord:
    """Save a learning session event for analytics and prototype tracking."""
    query = """
        INSERT INTO learning_sessions (user_id, mode_used, duration, timestamp)
        VALUES (?, ?, ?, ?)
    """
    now = datetime.utcnow()
    with _get_connection() as connection:
        cursor = connection.execute(query, (user_id, mode_used, duration, now))
        session_id = cursor.lastrowid
    return LearningSessionRecord(
        id=session_id,
        user_id=user_id,
        mode_used=mode_used,
        duration=duration,
        timestamp=now,
    )


def get_learning_sessions(user_id: int, limit: int = 100) -> list[LearningSessionRecord]:
    """Return recent learning sessions for a user."""
    query = """
        SELECT * FROM learning_sessions
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    with _get_connection() as connection:
        rows = connection.execute(query, (user_id, limit)).fetchall()
    return [
        LearningSessionRecord(
            id=row["id"],
            user_id=row["user_id"],
            mode_used=row["mode_used"],
            duration=row["duration"],
            timestamp=row["timestamp"],
        )
        for row in rows
    ]


def save_user_preferences(
    user_id: int,
    preferred_mode: str,
    reading_level: str,
) -> UserPreferencesRecord:
    """Save or update user reading preferences."""
    query = """
        INSERT INTO user_preferences (user_id, preferred_mode, reading_level)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            preferred_mode = excluded.preferred_mode,
            reading_level = excluded.reading_level
    """
    with _get_connection() as connection:
        cursor = connection.execute(query, (user_id, preferred_mode, reading_level))
        pref_id = cursor.lastrowid
    return UserPreferencesRecord(
        id=pref_id,
        user_id=user_id,
        preferred_mode=preferred_mode,
        reading_level=reading_level,
    )


def get_user_preferences(user_id: int) -> UserPreferencesRecord | None:
    """Return stored preferences for a user."""
    query = "SELECT * FROM user_preferences WHERE user_id = ?"
    with _get_connection() as connection:
        row = connection.execute(query, (user_id,)).fetchone()
    if row is None:
        return None
    return UserPreferencesRecord(
        id=row["id"],
        user_id=row["user_id"],
        preferred_mode=row["preferred_mode"],
        reading_level=row["reading_level"],
    )
