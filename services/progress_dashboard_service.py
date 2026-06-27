"""Service for calculating learner progress metrics and recommendations."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from database.db import (
    get_user_by_id,
    get_documents,
    get_quiz_history,
    get_learning_sessions,
    get_learning_history,
    get_topic_progress,
    get_concept_mastery,
    get_learner_profile,
    get_chat_history,
)


def _normalize_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            try:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
    return None


def _extract_date(value: Any) -> datetime.date | None:
    dt = _normalize_datetime(value)
    if dt is None:
        return None
    return dt.date()


def _calculate_streak(dates: list[datetime.date]) -> int:
    if not dates:
        return 0

    unique_days = sorted(set(dates), reverse=True)
    streak = 0
    current = unique_days[0]

    while streak < len(unique_days) and unique_days[streak] == current - timedelta(days=streak):
        streak += 1

    return streak


def _parse_mode(activity_type: str) -> str:
    lower = (activity_type or "").lower()
    if "audio" in lower:
        return "Audio Learning"
    if "visual" in lower:
        return "Visual Learning"
    if "quiz" in lower:
        return "Quiz"
    if "simplified" in lower or "read" in lower or "notes" in lower:
        return "Simplified Notes"
    if "question" in lower or "chat" in lower:
        return "AI Tutor"
    if "stem" in lower:
        return "STEM Support"
    return "Other"


def _build_chart_series(data: dict[str, float], max_points: int = 30) -> list[tuple[str, float]]:
    items = list(data.items())
    if len(items) > max_points:
        items = items[-max_points:]
    return items


def _format_minutes(minutes: int | float) -> str:
    hours = int(minutes) // 60
    remainder = int(minutes) % 60
    if hours > 0:
        return f"{hours}h {remainder}m"
    return f"{remainder}m"


def get_dashboard_data(user_id: int) -> dict[str, Any]:
    user = get_user_by_id(user_id)
    profile = get_learner_profile(user_id)
    documents = get_documents(user_id, limit=200)
    quizzes = get_quiz_history(user_id, limit=200)
    sessions = get_learning_sessions(user_id, limit=200)
    history = get_learning_history(user_id, limit=500)
    topics = get_topic_progress(user_id)
    concepts = get_concept_mastery(user_id)
    chats = get_chat_history(user_id, limit=200)

    # Overview totals
    total_study_time = profile.total_study_time_minutes if profile else 0
    session_durations = [
        (session.session_duration_minutes or session.duration) for session in sessions if session is not None
    ]
    if not total_study_time:
        total_study_time = int(sum(session_durations))

    total_sessions = len(sessions)
    days_active = len({_extract_date(session.timestamp) for session in sessions if _extract_date(session.timestamp)})
    if days_active == 0:
        days_active = len({
            _extract_date(event.timestamp) for event in history if _extract_date(event.timestamp)
        })

    active_dates = [
        _extract_date(session.timestamp)
        for session in sessions
        if _extract_date(session.timestamp) is not None
    ]
    active_dates += [
        _extract_date(event.timestamp)
        for event in history
        if _extract_date(event.timestamp) is not None
    ]
    active_dates = [d for d in active_dates if d is not None]
    streak = _calculate_streak(active_dates)

    # Progress metrics
    documents_studied = len(documents)
    topics_covered = len(topics)
    concepts_learned = len(concepts)
    questions_asked = profile.total_questions_asked if profile else sum(
        1 for event in history if _parse_mode(event.activity_type) == "AI Tutor"
    )
    quiz_attempts = len(quizzes)
    quiz_accuracy = (sum(attempt.score for attempt in quizzes) / quiz_attempts) if quiz_attempts else 0.0
    avg_session_duration = (sum(session_durations) / len(session_durations)) if session_durations else 0.0

    # Concept mastery details
    mastery_rows: list[dict[str, Any]] = []
    for record in concepts:
        mastery_value = float(record.mastery_percentage or 0.0)
        if mastery_value >= 80:
            status = "🟢 Mastered"
        elif mastery_value >= 60:
            status = "🟡 Needs Revision"
        else:
            status = "🔴 Weak Concept"

        mastery_rows.append(
            {
                "Concept Name": record.concept,
                "Mastery Score": round(mastery_value, 1),
                "Revisions": record.times_asked,
                "Quiz Accuracy": f"{round(mastery_value, 1)}%",
                "Last Studied Date": _normalize_datetime(record.last_asked).strftime("%Y-%m-%d") if record.last_asked else "N/A",
                "Current Status": status,
            }
        )

    weak_concepts = [
        row for row in mastery_rows
        if row["Mastery Score"] < 70 or row["Revisions"] >= 2 or (
            row["Current Status"] == "🔴 Weak Concept"
        )
    ]

    # Learning mode preference
    mode_counts = Counter(_parse_mode(event.activity_type) for event in history)
    if not mode_counts:
        mode_counts["Simplified Notes"] = 1
    total_mode_events = sum(mode_counts.values()) or 1
    mode_usage = [
        {
            "mode": mode,
            "count": count,
            "percentage": round((count / total_mode_events) * 100, 1),
        }
        for mode, count in mode_counts.most_common()
    ]

    # Study activity trends
    daily_study: dict[str, float] = defaultdict(float)
    weekly_study: dict[str, float] = defaultdict(float)
    monthly_study: dict[str, float] = defaultdict(float)
    for session in sessions:
        timestamp = _normalize_datetime(session.timestamp)
        duration = float(session.session_duration_minutes or session.duration or 0)
        if not timestamp or duration <= 0:
            continue
        day_key = timestamp.strftime("%Y-%m-%d")
        week_key = f"{timestamp.isocalendar()[0]}-W{timestamp.isocalendar()[1]:02d}"
        month_key = timestamp.strftime("%Y-%m")
        daily_study[day_key] += duration
        weekly_study[week_key] += duration
        monthly_study[month_key] += duration

    # Timeline events
    timeline: list[dict[str, str]] = []
    for document in documents:
        timeline.append(
            {
                "time": document.upload_time.strftime("%Y-%m-%d %H:%M"),
                "event": "Document Uploaded",
                "details": document.file_name,
            }
        )
    for quiz in quizzes:
        timeline.append(
            {
                "time": quiz.timestamp.strftime("%Y-%m-%d %H:%M"),
                "event": "Quiz Taken",
                "details": f"{quiz.topic} — {quiz.score}/{quiz.total_questions}",
            }
        )
    for topic in topics:
        if topic.last_studied:
            timeline.append(
                {
                    "time": topic.last_studied.strftime("%Y-%m-%d %H:%M"),
                    "event": "Topic Learned",
                    "details": topic.topic,
                }
            )
    for activity in history:
        activity_type = activity.activity_type or ""
        timestamp = _normalize_datetime(activity.timestamp)
        if not timestamp:
            continue
        if "audio" in activity_type:
            timeline.append(
                {
                    "time": timestamp.strftime("%Y-%m-%d %H:%M"),
                    "event": "Audio Generated",
                    "details": activity.topic or "Audio learning session",
                }
            )
        elif "visual" in activity_type:
            timeline.append(
                {
                    "time": timestamp.strftime("%Y-%m-%d %H:%M"),
                    "event": "Visual Generated",
                    "details": activity.topic or "Visual learning session",
                }
            )
        elif "question" in activity_type or "chat" in activity_type:
            timeline.append(
                {
                    "time": timestamp.strftime("%Y-%m-%d %H:%M"),
                    "event": "AI Tutor Session",
                    "details": activity.topic or "Question answered",
                }
            )
    timeline.sort(key=lambda item: item["time"], reverse=True)

    # Insights
    insights: list[str] = []
    favorite_mode = mode_usage[0]["mode"] if mode_usage else "Simplified Notes"
    insights.append(f"You learn best using {favorite_mode}.")

    if topics:
        strongest_topic = max(topics, key=lambda t: t.mastery_level)
        insights.append(f"You usually study {strongest_topic.topic}.")

    evening_sessions = [
        _normalize_datetime(session.timestamp).hour for session in sessions
        if _normalize_datetime(session.timestamp) is not None and 17 <= _normalize_datetime(session.timestamp).hour <= 22
    ]
    if len(evening_sessions) >= max(1, len(sessions) // 2):
        insights.append("You perform better during evening sessions.")

    if quiz_attempts >= 2:
        sorted_quizzes = sorted(quizzes, key=lambda q: q.timestamp)
        first_score = sorted_quizzes[0].score
        latest_score = sorted_quizzes[-1].score
        if latest_score > first_score:
            insights.append(
                f"You have improved your quiz accuracy from {first_score:.0f}% to {latest_score:.0f}%.")
    if weak_concepts:
        insights.append(f"You should revise {weak_concepts[0]['Concept Name']}.")

    # Recommendations
    recommendations: list[dict[str, str]] = []
    if weak_concepts:
        recommendations.append(
            {
                "title": "Concepts to Revise",
                "detail": ", ".join(
                    row["Concept Name"] for row in weak_concepts[:3]
                ),
            }
        )
    next_topic = None
    if topics:
        weak_topics = [t for t in topics if t.mastery_level < 0.7]
        if weak_topics:
            next_topic = min(weak_topics, key=lambda t: t.mastery_level).topic
        else:
            next_topic = topics[0].topic
    if next_topic:
        recommendations.append(
            {
                "title": "Next Topic to Study",
                "detail": next_topic,
            }
        )
    recommendations.append(
        {
            "title": "Suggested Learning Mode",
            "detail": favorite_mode,
        }
    )
    target_minutes = 30 if total_study_time < 60 else 45
    recommendations.append(
        {
            "title": "Daily Learning Goal",
            "detail": f"Aim for {target_minutes} minutes today.",
        }
    )
    if quiz_attempts < 5:
        recommendations.append(
            {
                "title": "Quiz Practice",
                "detail": "Try a short quiz to reinforce your learning.",
            }
        )
    if any("🔴 Weak Concept" in row["Current Status"] for row in mastery_rows):
        recommendations.append(
            {
                "title": "Visual Revision",
                "detail": "Review weak concepts with a visual learning exercise.",
            }
        )

    # Chart-ready data sets
    study_line = _build_chart_series(dict(sorted(daily_study.items())))
    weekly_line = _build_chart_series(dict(sorted(weekly_study.items())))
    monthly_line = _build_chart_series(dict(sorted(monthly_study.items())))
    quiz_line = [
        (quiz.timestamp.strftime("%Y-%m-%d"), quiz.score)
        for quiz in sorted(quizzes, key=lambda q: q.timestamp)
    ]

    return {
        "user": user,
        "profile": profile,
        "overview": {
            "student_name": user.name if user else "Learner",
            "age": user.age if user and user.age is not None else "N/A",
            "grade": user.grade if user else "N/A",
            "institution": user.institution if user else "N/A",
            "field_of_study": user.field_of_study if user else "N/A",
            "total_study_time": total_study_time,
            "total_learning_sessions": total_sessions,
            "days_active": days_active,
            "current_streak": streak,
        },
        "progress": {
            "documents_studied": documents_studied,
            "topics_covered": topics_covered,
            "concepts_learned": concepts_learned,
            "questions_asked": questions_asked,
            "quiz_attempts": quiz_attempts,
            "quiz_accuracy": quiz_accuracy,
            "avg_session_duration": avg_session_duration,
        },
        "concept_mastery": mastery_rows,
        "weak_concepts": weak_concepts,
        "learning_mode_usage": mode_usage,
        "study_activity": {
            "daily": study_line,
            "weekly": weekly_line,
            "monthly": monthly_line,
        },
        "quiz_performance": {
            "total_quizzes": quiz_attempts,
            "average_score": round(quiz_accuracy, 1),
            "highest_score": max((quiz.score for quiz in quizzes), default=0),
            "lowest_score": min((quiz.score for quiz in quizzes), default=0),
            "improvement": quiz_line,
        },
        "timeline": timeline,
        "insights": insights,
        "recommendations": recommendations,
        "favorite_mode": favorite_mode,
    }
