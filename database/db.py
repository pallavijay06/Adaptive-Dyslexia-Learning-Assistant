"""SQLite database access layer for cHEAL learning assistant."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from sqlite3 import Connection, IntegrityError

from database.models import (
    ChatRecord,
    DocumentRecord,
    LearningSupportLogRecord,
    LearningSessionRecord,
    QuizAttemptRecord,
    QuizQuestionResponseRecord,
    UserPreferencesRecord,
    UserRecord,
    LearnerProfileRecord,
    LearningHistoryRecord,
    TopicProgressRecord,
    ConceptMasteryRecord,
    AdaptivePreferencesRecord,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data.sqlite"

# Module-level guard to ensure initialization runs only once per process
_initialized = False


def _get_connection() -> Connection:
    """Return a SQLite connection with foreign key enforcement enabled."""
    connection = sqlite3.connect(DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    """Create database tables if they do not exist."""
    global _initialized
    if _initialized:
        return
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                age INTEGER NOT NULL,
                grade TEXT NOT NULL,
                institution TEXT NOT NULL,
                field_of_study TEXT NOT NULL,
                preferred_language TEXT,
                learning_goal TEXT,
                dyslexia_status TEXT,
                registration_date TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                last_logout TIMESTAMP,
                total_sessions INTEGER NOT NULL DEFAULT 0,
                total_learning_minutes INTEGER NOT NULL DEFAULT 0
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
                comprehension_score REAL NOT NULL DEFAULT 0.0,
                feedback_strengths TEXT NOT NULL DEFAULT '',
                feedback_weaknesses TEXT NOT NULL DEFAULT '',
                feedback_recommended_concepts TEXT NOT NULL DEFAULT '',
                feedback_suggested_learning_mode TEXT NOT NULL DEFAULT '',
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS quiz_question_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                quiz_id INTEGER,
                question_id TEXT NOT NULL,
                question_type TEXT NOT NULL,
                topic TEXT,
                difficulty TEXT,
                question_start_time TIMESTAMP NOT NULL,
                question_submit_time TIMESTAMP NOT NULL,
                time_taken_seconds INTEGER NOT NULL,
                is_correct BOOLEAN NOT NULL,
                attempt_number INTEGER NOT NULL DEFAULT 1,
                first_attempt_success BOOLEAN NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(quiz_id) REFERENCES quiz_attempts(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS learning_support_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                quiz_id INTEGER,
                question_id TEXT NOT NULL,
                support_type TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(quiz_id) REFERENCES quiz_attempts(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS learning_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mode_used TEXT NOT NULL,
                duration INTEGER NOT NULL,
                login_time TIMESTAMP,
                logout_time TIMESTAMP,
                session_duration_minutes INTEGER NOT NULL DEFAULT 0,
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

            CREATE TABLE IF NOT EXISTS learner_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                total_study_time_minutes INTEGER NOT NULL DEFAULT 0,
                documents_uploaded INTEGER NOT NULL DEFAULT 0,
                unique_topics_studied INTEGER NOT NULL DEFAULT 0,
                total_questions_asked INTEGER NOT NULL DEFAULT 0,
                average_quiz_score REAL NOT NULL DEFAULT 0.0,
                preferred_learning_mode TEXT NOT NULL DEFAULT 'Simplified Notes',
                learning_frequency TEXT NOT NULL DEFAULT 'occasional',
                confidence_level REAL NOT NULL DEFAULT 0.5,
                explanation_complexity TEXT NOT NULL DEFAULT 'medium',
                prefers_examples BOOLEAN NOT NULL DEFAULT 1,
                prefers_analogies BOOLEAN NOT NULL DEFAULT 1,
                prefers_bullet_points BOOLEAN NOT NULL DEFAULT 1,
                avg_response_length_preference INTEGER NOT NULL DEFAULT 200,
                last_updated TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS learning_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id INTEGER,
                activity_type TEXT NOT NULL,
                topic TEXT,
                duration_seconds INTEGER NOT NULL DEFAULT 0,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(session_id) REFERENCES learning_sessions(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS topic_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                questions_asked INTEGER NOT NULL DEFAULT 0,
                quiz_attempts INTEGER NOT NULL DEFAULT 0,
                best_score REAL NOT NULL DEFAULT 0.0,
                last_studied TIMESTAMP,
                times_studied INTEGER NOT NULL DEFAULT 0,
                mastery_level REAL NOT NULL DEFAULT 0.0,
                is_weak_area BOOLEAN NOT NULL DEFAULT 0,
                is_strong_area BOOLEAN NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, topic)
            );

            CREATE TABLE IF NOT EXISTS concept_mastery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                concept TEXT NOT NULL,
                times_asked INTEGER NOT NULL DEFAULT 0,
                times_answered_correctly INTEGER NOT NULL DEFAULT 0,
                mastery_percentage REAL NOT NULL DEFAULT 0.0,
                last_asked TIMESTAMP,
                is_frequently_asked BOOLEAN NOT NULL DEFAULT 0,
                is_frequently_missed BOOLEAN NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, topic, concept)
            );

            CREATE TABLE IF NOT EXISTS adaptive_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                preferred_explanation_complexity TEXT NOT NULL DEFAULT 'medium',
                prefers_visual_aids BOOLEAN NOT NULL DEFAULT 1,
                prefers_audio BOOLEAN NOT NULL DEFAULT 0,
                prefers_bullet_points BOOLEAN NOT NULL DEFAULT 1,
                prefers_short_sentences BOOLEAN NOT NULL DEFAULT 0,
                prefers_analogies BOOLEAN NOT NULL DEFAULT 1,
                prefers_real_world_examples BOOLEAN NOT NULL DEFAULT 1,
                avg_successful_response_length INTEGER NOT NULL DEFAULT 200,
                response_time_patience INTEGER NOT NULL DEFAULT 60,
                quiz_difficulty_preference TEXT NOT NULL DEFAULT 'adaptive',
                last_updated TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        _migrate_database_schema(connection)
    # Mark as initialized so subsequent calls are no-ops
    _initialized = True


def _get_table_columns(connection: Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _get_row_value(row: sqlite3.Row, key: str, default: Any = "") -> Any:
    return row[key] if key in row.keys() else default


def _migrate_database_schema(connection: Connection) -> None:
    users_columns = _get_table_columns(connection, "users")

    if "full_name" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN full_name TEXT NOT NULL DEFAULT ''")
        if "name" in users_columns:
            connection.execute("UPDATE users SET full_name = name")

    if "age" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN age INTEGER NOT NULL DEFAULT 0")

    if "grade" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN grade TEXT NOT NULL DEFAULT ''")

    if "institution" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN institution TEXT NOT NULL DEFAULT ''")

    if "field_of_study" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN field_of_study TEXT NOT NULL DEFAULT ''")

    if "preferred_language" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN preferred_language TEXT")

    if "learning_goal" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN learning_goal TEXT")

    if "dyslexia_status" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN dyslexia_status TEXT")

    if "registration_date" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN registration_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
        if "created_at" in users_columns:
            connection.execute("UPDATE users SET registration_date = created_at")

    if "created_at" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")

    if "last_login" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")

    if "last_logout" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN last_logout TIMESTAMP")

    if "total_sessions" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN total_sessions INTEGER NOT NULL DEFAULT 0")

    if "total_learning_minutes" not in users_columns:
        connection.execute("ALTER TABLE users ADD COLUMN total_learning_minutes INTEGER NOT NULL DEFAULT 0")

    learning_columns = _get_table_columns(connection, "learning_sessions")
    if "login_time" not in learning_columns:
        connection.execute("ALTER TABLE learning_sessions ADD COLUMN login_time TIMESTAMP")
    if "logout_time" not in learning_columns:
        connection.execute("ALTER TABLE learning_sessions ADD COLUMN logout_time TIMESTAMP")
    if "session_duration_minutes" not in learning_columns:
        connection.execute("ALTER TABLE learning_sessions ADD COLUMN session_duration_minutes INTEGER NOT NULL DEFAULT 0")

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS quiz_question_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            quiz_id INTEGER,
            question_id TEXT NOT NULL,
            question_type TEXT NOT NULL,
            topic TEXT,
            difficulty TEXT,
            question_start_time TIMESTAMP NOT NULL,
            question_submit_time TIMESTAMP NOT NULL,
            time_taken_seconds INTEGER NOT NULL,
            is_correct BOOLEAN NOT NULL,
            attempt_number INTEGER NOT NULL DEFAULT 1,
            first_attempt_success BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(quiz_id) REFERENCES quiz_attempts(id) ON DELETE SET NULL
        )
        """
    )

    # Add new columns if they don't exist (migration for existing databases)
    try:
        connection.execute("ALTER TABLE quiz_question_responses ADD COLUMN attempt_number INTEGER NOT NULL DEFAULT 1")
    except Exception:
        pass  # Column already exists
    
    try:
        connection.execute("ALTER TABLE quiz_question_responses ADD COLUMN first_attempt_success BOOLEAN NOT NULL DEFAULT 0")
    except Exception:
        pass  # Column already exists

    try:
        connection.execute("ALTER TABLE quiz_attempts ADD COLUMN comprehension_score REAL NOT NULL DEFAULT 0.0")
    except Exception:
        pass  # Column already exists

    quiz_attempts_columns = _get_table_columns(connection, "quiz_attempts")
    if "feedback_strengths" not in quiz_attempts_columns:
        connection.execute("ALTER TABLE quiz_attempts ADD COLUMN feedback_strengths TEXT NOT NULL DEFAULT ''")
    if "feedback_weaknesses" not in quiz_attempts_columns:
        connection.execute("ALTER TABLE quiz_attempts ADD COLUMN feedback_weaknesses TEXT NOT NULL DEFAULT ''")
    if "feedback_recommended_concepts" not in quiz_attempts_columns:
        connection.execute("ALTER TABLE quiz_attempts ADD COLUMN feedback_recommended_concepts TEXT NOT NULL DEFAULT ''")
    if "feedback_suggested_learning_mode" not in quiz_attempts_columns:
        connection.execute("ALTER TABLE quiz_attempts ADD COLUMN feedback_suggested_learning_mode TEXT NOT NULL DEFAULT ''")

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS learning_support_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            quiz_id INTEGER,
            question_id TEXT NOT NULL,
            support_type TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(quiz_id) REFERENCES quiz_attempts(id) ON DELETE SET NULL
        )
        """
    )


def save_user(
    name: str,
    email: str,
    password_hash: str,
    age: int = 0,
    grade: str = "",
    institution: str = "",
    field_of_study: str = "",
    preferred_language: str | None = None,
    learning_goal: str | None = None,
    dyslexia_status: str | None = None,
    registration_date: datetime | None = None,
    created_at: datetime | None = None,
    total_sessions: int = 0,
    total_learning_minutes: int = 0,
) -> UserRecord:
    """Insert a new user and return the saved user record."""
    now = registration_date or datetime.utcnow()
    created_at = created_at or now
    dyslexia_status = dyslexia_status or "Prefer not to say"
    query = """
        INSERT INTO users (
            full_name, email, password_hash, age, grade, institution, field_of_study,
            preferred_language, learning_goal, dyslexia_status,
            registration_date, created_at, total_sessions, total_learning_minutes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        with _get_connection() as connection:
            cursor = connection.execute(
                query,
                (
                    name,
                    email,
                    password_hash,
                    age,
                    grade,
                    institution,
                    field_of_study,
                    preferred_language,
                    learning_goal,
                    dyslexia_status,
                    now,
                    created_at,
                    total_sessions,
                    total_learning_minutes,
                ),
            )
            user_id = cursor.lastrowid
    except IntegrityError as exc:
        raise ValueError("A user with that email already exists.") from exc

    return UserRecord(
        id=user_id,
        name=name,
        email=email,
        password_hash=password_hash,
        created_at=created_at,
        age=age,
        grade=grade,
        institution=institution,
        field_of_study=field_of_study,
        preferred_language=preferred_language,
        learning_goal=learning_goal,
        dyslexia_status=dyslexia_status,
        registration_date=now,
        last_login=None,
        last_logout=None,
        total_sessions=total_sessions,
        total_learning_minutes=total_learning_minutes,
    )


def get_user(email: str) -> UserRecord | None:
    """Return a user record by email, or None if no user exists."""
    query = "SELECT * FROM users WHERE email = ?"
    with _get_connection() as connection:
        row = connection.execute(query, (email,)).fetchone()
    if row is None:
        return None
    return UserRecord(
        id=row["id"],
        name=row["full_name"],
        email=row["email"],
        password_hash=row["password_hash"],
        created_at=row["created_at"],
        age=row["age"],
        grade=row["grade"],
        institution=row["institution"],
        field_of_study=row["field_of_study"],
        preferred_language=row["preferred_language"],
        learning_goal=row["learning_goal"],
        dyslexia_status=row["dyslexia_status"],
        registration_date=row["registration_date"],
        last_login=row["last_login"],
        last_logout=row["last_logout"],
        total_sessions=row["total_sessions"],
        total_learning_minutes=row["total_learning_minutes"],
    )


def get_user_by_id(user_id: int) -> UserRecord | None:
    """Return a user record by user id."""
    query = "SELECT * FROM users WHERE id = ?"
    with _get_connection() as connection:
        row = connection.execute(query, (user_id,)).fetchone()
    if row is None:
        return None
    return UserRecord(
        id=row["id"],
        name=row["full_name"],
        email=row["email"],
        password_hash=row["password_hash"],
        created_at=row["created_at"],
        age=row["age"],
        grade=row["grade"],
        institution=row["institution"],
        field_of_study=row["field_of_study"],
        preferred_language=row["preferred_language"],
        learning_goal=row["learning_goal"],
        dyslexia_status=row["dyslexia_status"],
        registration_date=row["registration_date"],
        last_login=row["last_login"],
        last_logout=row["last_logout"],
        total_sessions=row["total_sessions"],
        total_learning_minutes=row["total_learning_minutes"],
    )


def update_user_last_login(user_id: int, last_login: datetime) -> None:
    """Update the last login timestamp for a user."""
    query = "UPDATE users SET last_login = ? WHERE id = ?"
    with _get_connection() as connection:
        connection.execute(query, (last_login, user_id))


def update_user_logout(user_id: int, last_logout: int | datetime) -> None:
    """Update the last logout timestamp or duration for a user."""
    logout_time = last_logout if isinstance(last_logout, datetime) else datetime.utcnow()
    query = "UPDATE users SET last_logout = ? WHERE id = ?"
    with _get_connection() as connection:
        connection.execute(query, (logout_time, user_id))


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


def get_documents(user_id: int, limit: int = 100) -> list[DocumentRecord]:
    """Return recent documents uploaded by a specific user."""
    query = "SELECT * FROM documents WHERE user_id = ? ORDER BY upload_time DESC LIMIT ?"
    with _get_connection() as connection:
        rows = connection.execute(query, (user_id, limit)).fetchall()
    return [
        DocumentRecord(
            id=row["id"],
            user_id=row["user_id"],
            file_name=row["file_name"],
            file_type=row["file_type"],
            document_text=row["document_text"],
            upload_time=row["upload_time"],
        )
        for row in rows
    ]


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
    comprehension_score: float = 0.0,
    feedback_strengths: str = "",
    feedback_weaknesses: str = "",
    feedback_recommended_concepts: str = "",
    feedback_suggested_learning_mode: str = "",
) -> QuizAttemptRecord:
    """Save a completed quiz attempt."""
    query = """
        INSERT INTO quiz_attempts (
            user_id, topic, score, total_questions,
            comprehension_score, feedback_strengths, feedback_weaknesses,
            feedback_recommended_concepts, feedback_suggested_learning_mode,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    now = datetime.utcnow()
    with _get_connection() as connection:
        cursor = connection.execute(
            query,
            (
                user_id,
                topic,
                score,
                total_questions,
                float(comprehension_score),
                str(feedback_strengths),
                str(feedback_weaknesses),
                str(feedback_recommended_concepts),
                str(feedback_suggested_learning_mode),
                now,
            ),
        )
        attempt_id = cursor.lastrowid
    return QuizAttemptRecord(
        id=attempt_id,
        user_id=user_id,
        topic=topic,
        score=score,
        total_questions=total_questions,
        timestamp=now,
        comprehension_score=float(comprehension_score),
        feedback_strengths=str(feedback_strengths),
        feedback_weaknesses=str(feedback_weaknesses),
        feedback_recommended_concepts=str(feedback_recommended_concepts),
        feedback_suggested_learning_mode=str(feedback_suggested_learning_mode),
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
            comprehension_score=float(_get_row_value(row, "comprehension_score", 0.0) or 0.0),
            feedback_strengths=str(_get_row_value(row, "feedback_strengths", "") or ""),
            feedback_weaknesses=str(_get_row_value(row, "feedback_weaknesses", "") or ""),
            feedback_recommended_concepts=str(_get_row_value(row, "feedback_recommended_concepts", "") or ""),
            feedback_suggested_learning_mode=str(_get_row_value(row, "feedback_suggested_learning_mode", "") or ""),
        )
        for row in rows
    ]


def save_quiz_question_response(
    user_id: int,
    question_id: str,
    question_type: str,
    question_start_time: datetime,
    question_submit_time: datetime,
    time_taken_seconds: int,
    is_correct: bool,
    quiz_id: int | None = None,
    topic: str | None = None,
    difficulty: str | None = None,
    attempt_number: int = 1,
    first_attempt_success: bool = False,
) -> QuizQuestionResponseRecord:
    """Save one question-level quiz response timing record with attempt tracking."""
    query = """
        INSERT INTO quiz_question_responses (
            user_id, quiz_id, question_id, question_type, topic, difficulty,
            question_start_time, question_submit_time, time_taken_seconds, is_correct,
            attempt_number, first_attempt_success, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    created_at = datetime.utcnow()
    duration = max(0, int(time_taken_seconds))
    with _get_connection() as connection:
        cursor = connection.execute(
            query,
            (
                user_id,
                quiz_id,
                question_id,
                question_type,
                topic,
                difficulty,
                question_start_time,
                question_submit_time,
                duration,
                bool(is_correct),
                int(attempt_number),
                bool(first_attempt_success),
                created_at,
            ),
        )
        response_id = cursor.lastrowid
    return QuizQuestionResponseRecord(
        id=response_id,
        user_id=user_id,
        quiz_id=quiz_id,
        question_id=question_id,
        question_type=question_type,
        topic=topic,
        difficulty=difficulty,
        question_start_time=question_start_time,
        question_submit_time=question_submit_time,
        time_taken_seconds=duration,
        is_correct=bool(is_correct),
        created_at=created_at,
        attempt_number=int(attempt_number),
        first_attempt_success=bool(first_attempt_success),
    )


def save_quiz_question_responses(
    responses: list[dict],
) -> list[QuizQuestionResponseRecord]:
    """Save several question-level quiz response timing records."""
    saved_records: list[QuizQuestionResponseRecord] = []
    for response in responses:
        saved_records.append(save_quiz_question_response(**response))
    return saved_records


def get_quiz_question_responses(
    user_id: int,
    quiz_id: int | None = None,
    limit: int = 500,
) -> list[QuizQuestionResponseRecord]:
    """Return saved question-level quiz response timing records."""
    if quiz_id is None:
        query = """
            SELECT * FROM quiz_question_responses
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        params = (user_id, limit)
    else:
        query = """
            SELECT * FROM quiz_question_responses
            WHERE user_id = ? AND quiz_id = ?
            ORDER BY id ASC
            LIMIT ?
        """
        params = (user_id, quiz_id, limit)

    with _get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [
        QuizQuestionResponseRecord(
            id=row["id"],
            user_id=row["user_id"],
            quiz_id=row["quiz_id"],
            question_id=row["question_id"],
            question_type=row["question_type"],
            topic=row["topic"],
            difficulty=row["difficulty"],
            question_start_time=row["question_start_time"],
            question_submit_time=row["question_submit_time"],
            time_taken_seconds=row["time_taken_seconds"],
            is_correct=bool(row["is_correct"]),
            created_at=row["created_at"],
            attempt_number=int(row["attempt_number"]),
            first_attempt_success=bool(row["first_attempt_success"]),
        )
        for row in rows
    ]


def save_learning_support_log(
    user_id: int,
    question_id: str,
    support_type: str,
    quiz_id: int | None = None,
    timestamp: datetime | None = None,
) -> LearningSupportLogRecord:
    """Save one learning support request event."""
    query = """
        INSERT INTO learning_support_logs (
            user_id, quiz_id, question_id, support_type, timestamp, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """
    event_time = timestamp or datetime.utcnow()
    created_at = datetime.utcnow()
    normalized_support_type = str(support_type or "").strip().lower()
    with _get_connection() as connection:
        cursor = connection.execute(
            query,
            (
                user_id,
                quiz_id,
                str(question_id or "").strip(),
                normalized_support_type,
                event_time,
                created_at,
            ),
        )
        log_id = cursor.lastrowid
    return LearningSupportLogRecord(
        id=log_id,
        user_id=user_id,
        quiz_id=quiz_id,
        question_id=str(question_id or "").strip(),
        support_type=normalized_support_type,
        timestamp=event_time,
        created_at=created_at,
    )


def get_learning_support_logs(
    user_id: int,
    quiz_id: int | None = None,
    support_type: str | None = None,
    limit: int = 500,
) -> list[LearningSupportLogRecord]:
    """Return learning support request events for later dependency analysis."""
    filters = ["user_id = ?"]
    params: list[object] = [user_id]
    if quiz_id is not None:
        filters.append("quiz_id = ?")
        params.append(quiz_id)
    if support_type:
        filters.append("support_type = ?")
        params.append(str(support_type).strip().lower())
    params.append(limit)

    query = f"""
        SELECT * FROM learning_support_logs
        WHERE {' AND '.join(filters)}
        ORDER BY timestamp DESC
        LIMIT ?
    """
    with _get_connection() as connection:
        rows = connection.execute(query, tuple(params)).fetchall()

    return [
        LearningSupportLogRecord(
            id=row["id"],
            user_id=row["user_id"],
            quiz_id=row["quiz_id"],
            question_id=row["question_id"],
            support_type=row["support_type"],
            timestamp=row["timestamp"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def attach_learning_support_logs_to_quiz(
    user_id: int,
    quiz_id: int,
    question_ids: list[str],
    started_after: datetime | None = None,
) -> int:
    """Attach pending support events to the quiz attempt created at submit time."""
    clean_question_ids = [str(item).strip() for item in question_ids if str(item or "").strip()]
    if not clean_question_ids:
        return 0

    placeholders = ", ".join("?" for _ in clean_question_ids)
    params: list[object] = [quiz_id, user_id, *clean_question_ids]
    time_filter = ""
    if started_after is not None:
        time_filter = " AND timestamp >= ?"
        params.append(started_after)

    query = f"""
        UPDATE learning_support_logs
        SET quiz_id = ?
        WHERE user_id = ?
          AND quiz_id IS NULL
          AND question_id IN ({placeholders})
          {time_filter}
    """
    with _get_connection() as connection:
        cursor = connection.execute(query, tuple(params))
        return cursor.rowcount


def save_learning_session(
    user_id: int,
    mode_used: str,
    duration: int,
    login_time: datetime | None = None,
    logout_time: datetime | None = None,
    session_duration_minutes: int | None = None,
) -> LearningSessionRecord:
    """Save a learning session event for analytics and prototype tracking."""
    login_time = login_time or datetime.utcnow()
    logout_time = logout_time
    session_duration_minutes = session_duration_minutes if session_duration_minutes is not None else duration
    query = """
        INSERT INTO learning_sessions (
            user_id, mode_used, duration, login_time, logout_time,
            session_duration_minutes, timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    now = datetime.utcnow()
    with _get_connection() as connection:
        cursor = connection.execute(
            query,
            (
                user_id,
                mode_used,
                duration,
                login_time,
                logout_time,
                session_duration_minutes,
                now,
            ),
        )
        session_id = cursor.lastrowid
    return LearningSessionRecord(
        id=session_id,
        user_id=user_id,
        mode_used=mode_used,
        duration=duration,
        login_time=login_time,
        logout_time=logout_time,
        session_duration_minutes=session_duration_minutes,
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
            login_time=row["login_time"],
            logout_time=row["logout_time"],
            session_duration_minutes=row["session_duration_minutes"],
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


# ==================== Adaptive Tutor Database Functions ====================


def save_learner_profile(
    user_id: int,
    total_study_time_minutes: int = 0,
    documents_uploaded: int = 0,
    unique_topics_studied: int = 0,
    total_questions_asked: int = 0,
    average_quiz_score: float = 0.0,
    preferred_learning_mode: str = "Simplified Notes",
    learning_frequency: str = "occasional",
    confidence_level: float = 0.5,
    explanation_complexity: str = "medium",
    prefers_examples: bool = True,
    prefers_analogies: bool = True,
    prefers_bullet_points: bool = True,
    avg_response_length_preference: int = 200,
) -> LearnerProfileRecord:
    """Save or update a learner profile."""
    query = """
        INSERT INTO learner_profile (
            user_id, total_study_time_minutes, documents_uploaded, unique_topics_studied,
            total_questions_asked, average_quiz_score, preferred_learning_mode,
            learning_frequency, confidence_level, explanation_complexity,
            prefers_examples, prefers_analogies, prefers_bullet_points,
            avg_response_length_preference, last_updated
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            total_study_time_minutes = excluded.total_study_time_minutes,
            documents_uploaded = excluded.documents_uploaded,
            unique_topics_studied = excluded.unique_topics_studied,
            total_questions_asked = excluded.total_questions_asked,
            average_quiz_score = excluded.average_quiz_score,
            preferred_learning_mode = excluded.preferred_learning_mode,
            learning_frequency = excluded.learning_frequency,
            confidence_level = excluded.confidence_level,
            explanation_complexity = excluded.explanation_complexity,
            prefers_examples = excluded.prefers_examples,
            prefers_analogies = excluded.prefers_analogies,
            prefers_bullet_points = excluded.prefers_bullet_points,
            avg_response_length_preference = excluded.avg_response_length_preference,
            last_updated = excluded.last_updated
    """
    now = datetime.utcnow()
    with _get_connection() as connection:
        cursor = connection.execute(
            query,
            (
                user_id,
                total_study_time_minutes,
                documents_uploaded,
                unique_topics_studied,
                total_questions_asked,
                average_quiz_score,
                preferred_learning_mode,
                learning_frequency,
                confidence_level,
                explanation_complexity,
                prefers_examples,
                prefers_analogies,
                prefers_bullet_points,
                avg_response_length_preference,
                now,
            ),
        )
        profile_id = cursor.lastrowid
    return LearnerProfileRecord(
        id=profile_id,
        user_id=user_id,
        total_study_time_minutes=total_study_time_minutes,
        documents_uploaded=documents_uploaded,
        unique_topics_studied=unique_topics_studied,
        total_questions_asked=total_questions_asked,
        average_quiz_score=average_quiz_score,
        preferred_learning_mode=preferred_learning_mode,
        learning_frequency=learning_frequency,
        confidence_level=confidence_level,
        explanation_complexity=explanation_complexity,
        prefers_examples=prefers_examples,
        prefers_analogies=prefers_analogies,
        prefers_bullet_points=prefers_bullet_points,
        avg_response_length_preference=avg_response_length_preference,
        last_updated=now,
        created_at=now,
    )


def get_learner_profile(user_id: int) -> LearnerProfileRecord | None:
    """Get learner profile for a user."""
    query = "SELECT * FROM learner_profile WHERE user_id = ?"
    with _get_connection() as connection:
        row = connection.execute(query, (user_id,)).fetchone()
    if row is None:
        return None
    return LearnerProfileRecord(
        id=row["id"],
        user_id=row["user_id"],
        total_study_time_minutes=row["total_study_time_minutes"],
        documents_uploaded=row["documents_uploaded"],
        unique_topics_studied=row["unique_topics_studied"],
        total_questions_asked=row["total_questions_asked"],
        average_quiz_score=row["average_quiz_score"],
        preferred_learning_mode=row["preferred_learning_mode"],
        learning_frequency=row["learning_frequency"],
        confidence_level=row["confidence_level"],
        explanation_complexity=row["explanation_complexity"],
        prefers_examples=bool(row["prefers_examples"]),
        prefers_analogies=bool(row["prefers_analogies"]),
        prefers_bullet_points=bool(row["prefers_bullet_points"]),
        avg_response_length_preference=row["avg_response_length_preference"],
        last_updated=row["last_updated"],
        created_at=row["created_at"],
    )


def save_learning_history(
    user_id: int,
    activity_type: str,
    topic: str | None = None,
    session_id: int | None = None,
    duration_seconds: int = 0,
) -> LearningHistoryRecord:
    """Save a learning history event."""
    query = """
        INSERT INTO learning_history (user_id, session_id, activity_type, topic, duration_seconds)
        VALUES (?, ?, ?, ?, ?)
    """
    now = datetime.utcnow()
    with _get_connection() as connection:
        cursor = connection.execute(query, (user_id, session_id, activity_type, topic, duration_seconds))
        history_id = cursor.lastrowid
    return LearningHistoryRecord(
        id=history_id,
        user_id=user_id,
        session_id=session_id,
        activity_type=activity_type,
        topic=topic,
        duration_seconds=duration_seconds,
        timestamp=now,
    )


def get_learning_history(user_id: int, limit: int = 500) -> list[LearningHistoryRecord]:
    """Get learning history for a user."""
    query = """
        SELECT * FROM learning_history
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    with _get_connection() as connection:
        rows = connection.execute(query, (user_id, limit)).fetchall()
    return [
        LearningHistoryRecord(
            id=row["id"],
            user_id=row["user_id"],
            session_id=row["session_id"],
            activity_type=row["activity_type"],
            topic=row["topic"],
            duration_seconds=row["duration_seconds"],
            timestamp=row["timestamp"],
        )
        for row in rows
    ]


def save_topic_progress(
    user_id: int,
    topic: str,
    questions_asked: int = 0,
    quiz_attempts: int = 0,
    best_score: float = 0.0,
    times_studied: int = 0,
    mastery_level: float = 0.0,
    is_weak_area: bool = False,
    is_strong_area: bool = False,
) -> TopicProgressRecord:
    """Save or update topic progress."""
    query = """
        INSERT INTO topic_progress (
            user_id, topic, questions_asked, quiz_attempts, best_score,
            last_studied, times_studied, mastery_level, is_weak_area, is_strong_area
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, topic) DO UPDATE SET
            questions_asked = excluded.questions_asked,
            quiz_attempts = excluded.quiz_attempts,
            best_score = excluded.best_score,
            last_studied = excluded.last_studied,
            times_studied = excluded.times_studied,
            mastery_level = excluded.mastery_level,
            is_weak_area = excluded.is_weak_area,
            is_strong_area = excluded.is_strong_area
    """
    now = datetime.utcnow()
    with _get_connection() as connection:
        cursor = connection.execute(
            query,
            (
                user_id,
                topic,
                questions_asked,
                quiz_attempts,
                best_score,
                now,
                times_studied,
                mastery_level,
                is_weak_area,
                is_strong_area,
            ),
        )
        progress_id = cursor.lastrowid
    return TopicProgressRecord(
        id=progress_id,
        user_id=user_id,
        topic=topic,
        questions_asked=questions_asked,
        quiz_attempts=quiz_attempts,
        best_score=best_score,
        last_studied=now,
        times_studied=times_studied,
        mastery_level=mastery_level,
        is_weak_area=is_weak_area,
        is_strong_area=is_strong_area,
    )


def get_topic_progress(user_id: int, topic: str | None = None) -> list[TopicProgressRecord]:
    """Get topic progress for a user."""
    if topic:
        query = "SELECT * FROM topic_progress WHERE user_id = ? AND topic = ?"
        with _get_connection() as connection:
            rows = connection.execute(query, (user_id, topic)).fetchall()
    else:
        query = "SELECT * FROM topic_progress WHERE user_id = ? ORDER BY mastery_level DESC"
        with _get_connection() as connection:
            rows = connection.execute(query, (user_id,)).fetchall()
    return [
        TopicProgressRecord(
            id=row["id"],
            user_id=row["user_id"],
            topic=row["topic"],
            questions_asked=row["questions_asked"],
            quiz_attempts=row["quiz_attempts"],
            best_score=row["best_score"],
            last_studied=row["last_studied"],
            times_studied=row["times_studied"],
            mastery_level=row["mastery_level"],
            is_weak_area=bool(row["is_weak_area"]),
            is_strong_area=bool(row["is_strong_area"]),
        )
        for row in rows
    ]


def save_concept_mastery(
    user_id: int,
    topic: str,
    concept: str,
    times_asked: int = 0,
    times_answered_correctly: int = 0,
    mastery_percentage: float = 0.0,
    is_frequently_asked: bool = False,
    is_frequently_missed: bool = False,
) -> ConceptMasteryRecord:
    """Save or update concept mastery."""
    query = """
        INSERT INTO concept_mastery (
            user_id, topic, concept, times_asked, times_answered_correctly,
            mastery_percentage, last_asked, is_frequently_asked, is_frequently_missed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, topic, concept) DO UPDATE SET
            times_asked = excluded.times_asked,
            times_answered_correctly = excluded.times_answered_correctly,
            mastery_percentage = excluded.mastery_percentage,
            last_asked = excluded.last_asked,
            is_frequently_asked = excluded.is_frequently_asked,
            is_frequently_missed = excluded.is_frequently_missed
    """
    now = datetime.utcnow()
    with _get_connection() as connection:
        cursor = connection.execute(
            query,
            (
                user_id,
                topic,
                concept,
                times_asked,
                times_answered_correctly,
                mastery_percentage,
                now,
                is_frequently_asked,
                is_frequently_missed,
            ),
        )
        mastery_id = cursor.lastrowid
    return ConceptMasteryRecord(
        id=mastery_id,
        user_id=user_id,
        topic=topic,
        concept=concept,
        times_asked=times_asked,
        times_answered_correctly=times_answered_correctly,
        mastery_percentage=mastery_percentage,
        last_asked=now,
        is_frequently_asked=is_frequently_asked,
        is_frequently_missed=is_frequently_missed,
    )


def get_concept_mastery(user_id: int, topic: str | None = None) -> list[ConceptMasteryRecord]:
    """Get concept mastery for a user."""
    if topic:
        query = "SELECT * FROM concept_mastery WHERE user_id = ? AND topic = ? ORDER BY times_asked DESC"
        with _get_connection() as connection:
            rows = connection.execute(query, (user_id, topic)).fetchall()
    else:
        query = "SELECT * FROM concept_mastery WHERE user_id = ? ORDER BY times_asked DESC"
        with _get_connection() as connection:
            rows = connection.execute(query, (user_id,)).fetchall()
    return [
        ConceptMasteryRecord(
            id=row["id"],
            user_id=row["user_id"],
            topic=row["topic"],
            concept=row["concept"],
            times_asked=row["times_asked"],
            times_answered_correctly=row["times_answered_correctly"],
            mastery_percentage=row["mastery_percentage"],
            last_asked=row["last_asked"],
            is_frequently_asked=bool(row["is_frequently_asked"]),
            is_frequently_missed=bool(row["is_frequently_missed"]),
        )
        for row in rows
    ]


def save_adaptive_preferences(
    user_id: int,
    preferred_explanation_complexity: str = "medium",
    prefers_visual_aids: bool = True,
    prefers_audio: bool = False,
    prefers_bullet_points: bool = True,
    prefers_short_sentences: bool = False,
    prefers_analogies: bool = True,
    prefers_real_world_examples: bool = True,
    avg_successful_response_length: int = 200,
    response_time_patience: int = 60,
    quiz_difficulty_preference: str = "adaptive",
) -> AdaptivePreferencesRecord:
    """Save or update adaptive preferences for a user."""
    query = """
        INSERT INTO adaptive_preferences (
            user_id, preferred_explanation_complexity, prefers_visual_aids, prefers_audio,
            prefers_bullet_points, prefers_short_sentences, prefers_analogies,
            prefers_real_world_examples, avg_successful_response_length,
            response_time_patience, quiz_difficulty_preference, last_updated
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            preferred_explanation_complexity = excluded.preferred_explanation_complexity,
            prefers_visual_aids = excluded.prefers_visual_aids,
            prefers_audio = excluded.prefers_audio,
            prefers_bullet_points = excluded.prefers_bullet_points,
            prefers_short_sentences = excluded.prefers_short_sentences,
            prefers_analogies = excluded.prefers_analogies,
            prefers_real_world_examples = excluded.prefers_real_world_examples,
            avg_successful_response_length = excluded.avg_successful_response_length,
            response_time_patience = excluded.response_time_patience,
            quiz_difficulty_preference = excluded.quiz_difficulty_preference,
            last_updated = excluded.last_updated
    """
    now = datetime.utcnow()
    with _get_connection() as connection:
        cursor = connection.execute(
            query,
            (
                user_id,
                preferred_explanation_complexity,
                prefers_visual_aids,
                prefers_audio,
                prefers_bullet_points,
                prefers_short_sentences,
                prefers_analogies,
                prefers_real_world_examples,
                avg_successful_response_length,
                response_time_patience,
                quiz_difficulty_preference,
                now,
            ),
        )
        prefs_id = cursor.lastrowid
    return AdaptivePreferencesRecord(
        id=prefs_id,
        user_id=user_id,
        preferred_explanation_complexity=preferred_explanation_complexity,
        prefers_visual_aids=prefers_visual_aids,
        prefers_audio=prefers_audio,
        prefers_bullet_points=prefers_bullet_points,
        prefers_short_sentences=prefers_short_sentences,
        prefers_analogies=prefers_analogies,
        prefers_real_world_examples=prefers_real_world_examples,
        avg_successful_response_length=avg_successful_response_length,
        response_time_patience=response_time_patience,
        quiz_difficulty_preference=quiz_difficulty_preference,
        last_updated=now,
    )


def get_adaptive_preferences(user_id: int) -> AdaptivePreferencesRecord | None:
    """Get adaptive preferences for a user."""
    query = "SELECT * FROM adaptive_preferences WHERE user_id = ?"
    with _get_connection() as connection:
        row = connection.execute(query, (user_id,)).fetchone()
    if row is None:
        return None
    return AdaptivePreferencesRecord(
        id=row["id"],
        user_id=row["user_id"],
        preferred_explanation_complexity=row["preferred_explanation_complexity"],
        prefers_visual_aids=bool(row["prefers_visual_aids"]),
        prefers_audio=bool(row["prefers_audio"]),
        prefers_bullet_points=bool(row["prefers_bullet_points"]),
        prefers_short_sentences=bool(row["prefers_short_sentences"]),
        prefers_analogies=bool(row["prefers_analogies"]),
        prefers_real_world_examples=bool(row["prefers_real_world_examples"]),
        avg_successful_response_length=row["avg_successful_response_length"],
        response_time_patience=row["response_time_patience"],
        quiz_difficulty_preference=row["quiz_difficulty_preference"],
        last_updated=row["last_updated"],
    )


# Ensure the database is initialized when this module is imported so any
# consumer that performs queries immediately after importing will not fail
# if the sqlite file or tables are missing.
init_db()
