"""Service for calculating learner progress metrics and recommendations."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from database.db import (
    get_user_by_id,
    get_documents,
    get_quiz_history,
    get_quiz_question_responses,
    get_learning_sessions,
    get_learning_history,
    get_learning_support_logs,
    get_topic_progress,
    get_concept_mastery,
    get_learner_profile,
    get_chat_history,
    get_behavior_events,
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


# Canonical mapping from MODE_ENTERED event metadata "mode" values to display labels.
_MODE_LABEL_MAP: dict[str, str] = {
    "Read": "Simplified Notes",
    "Listen": "Audio Learning",
    "Visual": "Visual Learning",
    "Quiz": "Quiz",
    "AI Tutor": "AI Tutor",
    "STEM": "STEM Support",
    "read": "Simplified Notes",
    "listen": "Audio Learning",
    "visual": "Visual Learning",
    "quiz": "Quiz",
    "ai tutor": "AI Tutor",
    "stem": "STEM Support",
}


def _count_mode_entries_from_behavior(behavior_events: list[Any]) -> Counter:
    """Count MODE_ENTERED behavior events by their canonical display label.

    Returns an empty Counter when no MODE_ENTERED events exist so the caller
    can distinguish "no data" from a non-zero count.
    """
    counts: Counter = Counter()
    for event in behavior_events:
        if (event.event_type or "").upper() != "MODE_ENTERED":
            continue
        metadata = event.metadata or {}
        raw_mode = str(
            metadata.get("learning_mode")
            or metadata.get("mode")
            or ""
        ).strip()
        if not raw_mode:
            continue
        label = _MODE_LABEL_MAP.get(raw_mode) or _MODE_LABEL_MAP.get(raw_mode.lower())
        if label:
            counts[label] += 1
    return counts


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


def _calculate_first_attempt_success_rate(responses: list[Any]) -> float:
    first_attempts = [record for record in responses if record.attempt_number == 1]
    if not first_attempts:
        return 0.0
    correct_first_attempts = sum(1 for record in first_attempts if record.first_attempt_success or record.is_correct)
    return round((correct_first_attempts / len(first_attempts)) * 100.0, 1)


def _calculate_average_attempts(responses: list[Any]) -> float:
    question_counts: dict[tuple[int | None, str], int] = {}
    for record in responses:
        key = (record.quiz_id, record.question_id)
        question_counts[key] = max(question_counts.get(key, 0), record.attempt_number)
    if not question_counts:
        return 0.0
    return round(sum(question_counts.values()) / len(question_counts), 1)


def _calculate_avg_time_per_question(responses: list[Any]) -> float:
    question_times: dict[tuple[int | None, str], int] = {}
    for record in responses:
        key = (record.quiz_id, record.question_id)
        question_times[key] = question_times.get(key, 0) + record.time_taken_seconds
    if not question_times:
        return 0.0
    return round(sum(question_times.values()) / len(question_times), 1)


def _calculate_conceptual_score(concepts: list[Any], fallback_score: float = 0.0) -> float:
    if not concepts:
        return fallback_score
    mastery_scores = [float(record.mastery_percentage or 0.0) for record in concepts]
    if not mastery_scores:
        return fallback_score
    return round(sum(mastery_scores) / len(mastery_scores), 1)


def _calculate_learning_support_dependency_score(support_count: int, total_questions: int) -> float:
    if total_questions <= 0:
        return 100.0
    dependency_ratio = min(1.0, support_count / float(total_questions))
    score = 100.0 - (dependency_ratio * 80.0)
    return round(max(min(score, 100.0), 0.0), 1)


def _calculate_response_efficiency_score(avg_time_per_question: float) -> float:
    if avg_time_per_question <= 30:
        return 100.0
    if avg_time_per_question >= 120:
        return 0.0
    return round(100.0 - ((avg_time_per_question - 30.0) / 90.0) * 100.0, 1)


def _calculate_comprehension_score(
    quiz_accuracy: float,
    conceptual_score: float,
    learning_support_dependency: float,
    first_attempt_success_rate: float,
    response_efficiency: float,
) -> float:
    if quiz_accuracy <= 0 and conceptual_score <= 0 and first_attempt_success_rate <= 0:
        return 0.0
    score = (
        (quiz_accuracy * 0.35)
        + (conceptual_score * 0.30)
        + (learning_support_dependency * 0.15)
        + (first_attempt_success_rate * 0.10)
        + (response_efficiency * 0.10)
    )
    return round(min(max(score, 0.0), 100.0), 1)


def calculate_quiz_comprehension_score(
    quiz_accuracy: float,
    conceptual_score: float,
    support_count: int,
    total_questions: int,
    first_attempt_success_rate: float,
    avg_time_per_question: float,
) -> float:
    support_dependency_score = _calculate_learning_support_dependency_score(support_count, total_questions)
    response_efficiency_score = _calculate_response_efficiency_score(avg_time_per_question)
    return _calculate_comprehension_score(
        quiz_accuracy,
        conceptual_score,
        support_dependency_score,
        first_attempt_success_rate,
        response_efficiency_score,
    )


def _create_badges(
    quiz_attempts: int,
    streak: int,
    quiz_accuracy: float,
    first_attempt_success_rate: float,
    average_attempts: float,
    avg_time_per_question: float,
    hint_usage: int,
    improvement_amount: float,
) -> list[str]:
    badges: list[str] = []
    if quiz_attempts >= 3 and first_attempt_success_rate >= 70:
        badges.append("First-Attempt Champion")
    if streak >= 3 and quiz_attempts >= 3:
        badges.append("Consistency Streak")
    if improvement_amount >= 10:
        badges.append("Growth Mindset")
    if avg_time_per_question > 0 and avg_time_per_question <= 90 and quiz_accuracy >= 65:
        badges.append("Quick Thinker")
    if hint_usage <= 1 and quiz_accuracy >= 75:
        badges.append("Independent Learner")
    if quiz_accuracy >= 85 and first_attempt_success_rate >= 75:
        badges.append("High Comprehension")
    return badges


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
    quiz_accuracy = 0.0
    quiz_percentages: list[float] = []
    if quiz_attempts:
        for attempt in quizzes:
            if attempt.total_questions:
                quiz_percentages.append(round((attempt.score / attempt.total_questions) * 100.0, 1))
        quiz_accuracy = round(sum(quiz_percentages) / len(quiz_percentages), 1) if quiz_percentages else 0.0

    all_responses = get_quiz_question_responses(user_id, limit=1000)
    support_logs = get_learning_support_logs(user_id, limit=1000)
    first_attempt_success_rate = _calculate_first_attempt_success_rate(all_responses)
    average_attempts = _calculate_average_attempts(all_responses)
    avg_time_per_question = _calculate_avg_time_per_question(all_responses)
    hint_usage = sum(1 for log in support_logs if log.support_type == "hint")

    if profile and profile.comprehension_score is not None:
        comprehension_score = float(profile.comprehension_score)
        concept_score = float(profile.conceptual_answer_score or 0.0)
        support_dependency_score = float(profile.learning_support_score or 0.0)
        response_efficiency_score = float(profile.response_efficiency_score or 0.0)
        if profile.first_attempt_score is not None:
            first_attempt_success_rate = float(profile.first_attempt_score)
        if profile.quiz_accuracy_score is not None:
            quiz_accuracy = float(profile.quiz_accuracy_score)
    else:
        concept_score = _calculate_conceptual_score(concepts, fallback_score=quiz_accuracy)
        support_dependency_score = _calculate_learning_support_dependency_score(
            len(support_logs),
            len(all_responses),
        )
        response_efficiency_score = _calculate_response_efficiency_score(avg_time_per_question)
        comprehension_score = _calculate_comprehension_score(
            quiz_accuracy,
            concept_score,
            support_dependency_score,
            first_attempt_success_rate,
            response_efficiency_score,
        )
    avg_session_duration = (sum(session_durations) / len(session_durations)) if session_durations else 0.0

    quiz_percentages_sorted = sorted(quiz_percentages)
    highest_score = max(quiz_percentages_sorted, default=0)
    lowest_score = min(quiz_percentages_sorted, default=0)
    quiz_line = [
        (quiz.timestamp.strftime("%Y-%m-%d"), round((quiz.score / quiz.total_questions) * 100.0, 1))
        for quiz in sorted(quizzes, key=lambda q: q.timestamp)
    ]

    improvement_amount = 0.0
    if len(quiz_percentages_sorted) >= 2:
        improvement_amount = quiz_percentages_sorted[-1] - quiz_percentages_sorted[0]

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

    # Learning mode preference — built exclusively from real MODE_ENTERED behavior events.
    behavior_events_all = get_behavior_events(user_id, limit=2000)
    mode_counts = _count_mode_entries_from_behavior(behavior_events_all)

    # Secondary signal: learning_history activity_type, used only when no
    # MODE_ENTERED events exist at all (e.g. very old data without tracking).
    if not mode_counts:
        for event in history:
            parsed = _parse_mode(event.activity_type)
            if parsed != "Other":
                mode_counts[parsed] += 1

    total_mode_events = sum(mode_counts.values()) or 0
    if total_mode_events > 0:
        mode_usage = [
            {
                "mode": mode,
                "count": count,
                "percentage": round((count / total_mode_events) * 100, 1),
            }
            for mode, count in mode_counts.most_common()
        ]
    else:
        mode_usage = []

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

    # --- Day-grouped summarized timeline ---
    _day_uploads: dict[str, list[str]] = defaultdict(list)
    _day_quizzes: dict[str, int] = defaultdict(int)
    _day_ai_questions: dict[str, int] = defaultdict(int)
    _day_modes: dict[str, set] = defaultdict(set)

    for doc in documents:
        day = _extract_date(doc.upload_time)
        if day:
            _day_uploads[str(day)].append(doc.file_name)

    for quiz in quizzes:
        day = _extract_date(quiz.timestamp)
        if day:
            _day_quizzes[str(day)] += 1

    for chat in chats:
        day = _extract_date(chat.timestamp)
        if day:
            _day_ai_questions[str(day)] += 1

    for event in behavior_events_all:
        if (event.event_type or "").upper() != "MODE_ENTERED":
            continue
        day = _extract_date(event.event_timestamp)
        if not day:
            continue
        metadata = event.metadata or {}
        raw_mode = str(
            metadata.get("learning_mode") or metadata.get("mode") or ""
        ).strip()
        label = _MODE_LABEL_MAP.get(raw_mode) or _MODE_LABEL_MAP.get(raw_mode.lower())
        if label:
            _day_modes[str(day)].add(label)

    all_days = sorted(
        set(_day_uploads) | set(_day_quizzes) | set(_day_ai_questions) | set(_day_modes),
        reverse=True,
    )

    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    last_week_start = today - timedelta(days=7)

    def _day_label(day_str: str) -> str:
        try:
            d = datetime.strptime(day_str, "%Y-%m-%d").date()
        except ValueError:
            return day_str
        if d == today:
            return "Today"
        if d == yesterday:
            return "Yesterday"
        return d.strftime("%A, %d %b %Y")

    timeline_days: list[dict[str, Any]] = []
    last_week_days: list[str] = []
    for day_str in all_days:
        try:
            day_date = datetime.strptime(day_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if day_date < last_week_start:
            last_week_days.append(day_str)
            continue
        bullets: list[str] = []
        uploads = _day_uploads.get(day_str, [])
        if uploads:
            for fname in uploads[:3]:
                bullets.append(f"Uploaded {fname}")
            if len(uploads) > 3:
                bullets.append(f"... and {len(uploads) - 3} more document(s)")
        qcount = _day_quizzes.get(day_str, 0)
        if qcount:
            bullets.append(f"Completed {qcount} quiz{'zes' if qcount > 1 else ''}")
        aiq = _day_ai_questions.get(day_str, 0)
        if aiq:
            bullets.append(f"Asked {aiq} AI Tutor question{'s' if aiq > 1 else ''}")
        modes = _day_modes.get(day_str, set())
        for m in sorted(modes):
            bullets.append(f"Used {m}")
        if bullets:
            timeline_days.append({"label": _day_label(day_str), "bullets": bullets})

    if last_week_days:
        lw_docs = sum(len(_day_uploads.get(d, [])) for d in last_week_days)
        lw_quizzes = sum(_day_quizzes.get(d, 0) for d in last_week_days)
        lw_modes: set = set()
        for d in last_week_days:
            lw_modes |= _day_modes.get(d, set())
        lw_bullets: list[str] = []
        if lw_docs:
            lw_bullets.append(f"Studied {lw_docs} document{'s' if lw_docs > 1 else ''}")
        if lw_quizzes:
            lw_bullets.append(f"Completed {lw_quizzes} quiz{'zes' if lw_quizzes > 1 else ''}")
        for m in sorted(lw_modes):
            lw_bullets.append(f"Used {m}")
        if lw_bullets:
            timeline_days.append({"label": "Last Week & Earlier", "bullets": lw_bullets})

    # Flat list kept for backward compatibility.
    timeline: list[dict[str, str]] = []
    for entry in timeline_days:
        for bullet in entry["bullets"]:
            timeline.append({"time": entry["label"], "event": bullet, "details": ""})

    # Insights
    insights: list[str] = []
    favorite_mode = mode_usage[0]["mode"] if mode_usage else "No preferred mode yet"
    if mode_usage:
        insights.append(f"You learn best using {favorite_mode}.")
    if topics:
        strongest_topic = max(topics, key=lambda t: t.mastery_level)
        insights.append(f"You usually study {strongest_topic.topic}.")
    evening_sessions = [
        _normalize_datetime(session.timestamp).hour for session in sessions
        if _normalize_datetime(session.timestamp) is not None
        and 17 <= _normalize_datetime(session.timestamp).hour <= 22
    ]
    if len(evening_sessions) >= max(1, len(sessions) // 2):
        insights.append("You perform better during evening sessions.")
    if quiz_attempts >= 2 and quiz_percentages:
        sorted_quiz_percentages = [
            round((quiz.score / quiz.total_questions) * 100.0, 1)
            for quiz in sorted(quizzes, key=lambda q: q.timestamp)
        ]
        first_score_pct = sorted_quiz_percentages[0]
        latest_score_pct = sorted_quiz_percentages[-1]
        if latest_score_pct > first_score_pct:
            insights.append(
                f"Your quiz accuracy improved from {first_score_pct:.0f}% to {latest_score_pct:.0f}%.")
    if weak_concepts:
        insights.append(f"Repeated mistakes detected on {weak_concepts[0]['Concept Name']}.")

    badges = _create_badges(
        quiz_attempts=quiz_attempts,
        streak=streak,
        quiz_accuracy=quiz_accuracy,
        first_attempt_success_rate=first_attempt_success_rate,
        average_attempts=average_attempts,
        avg_time_per_question=avg_time_per_question,
        hint_usage=hint_usage,
        improvement_amount=improvement_amount,
    )
    if comprehension_score >= 80 and "High Comprehension" not in badges:
        badges.append("High Comprehension")

    # --- Data-driven, reason-explained recommendations ---
    recommendations: list[dict[str, str]] = []

    truly_weak = [r for r in mastery_rows if r["Current Status"] == "\U0001f534 Weak Concept"]
    needs_revision = [r for r in mastery_rows if r["Current Status"] == "\U0001f7e1 Needs Revision"]
    revision_targets = truly_weak[:2] + needs_revision[:1]
    for r in revision_targets:
        recommendations.append(
            {
                "title": f"Revise: {r['Concept Name']}",
                "detail": (
                    f"Your mastery score for {r['Concept Name']} is {r['Mastery Score']}% "
                    f"with {r['Revisions']} revision(s) recorded. "
                    "Revisit this concept before attempting another quiz."
                ),
            }
        )

    if favorite_mode != "No preferred mode yet":
        mode_pct = mode_usage[0]["percentage"] if mode_usage else 0
        recommendations.append(
            {
                "title": f"Keep Using {favorite_mode}",
                "detail": (
                    f"{favorite_mode} accounts for {mode_pct}% of your learning activity "
                    "and is your most-used mode. Continue using it as your primary study method."
                ),
            }
        )
    else:
        recommendations.append(
            {
                "title": "Explore a Learning Mode",
                "detail": (
                    "You haven't used any learning mode yet. "
                    "Try Simplified Notes or Audio Learning to find the format that suits you best."
                ),
            }
        )

    if quiz_attempts > 0 and first_attempt_success_rate < 60:
        recommendations.append(
            {
                "title": "Improve First-Attempt Success",
                "detail": (
                    f"Your first-attempt success rate is {first_attempt_success_rate:.1f}%, "
                    "meaning you frequently revise answers. "
                    "Re-read simplified notes before each quiz to reduce this."
                ),
            }
        )
    elif quiz_attempts > 0 and first_attempt_success_rate >= 80:
        recommendations.append(
            {
                "title": "Strong First-Attempt Performance",
                "detail": (
                    f"You answered {first_attempt_success_rate:.1f}% of questions correctly on the first try. "
                    "This shows solid preparation. Keep using the same study routine."
                ),
            }
        )

    if quiz_attempts > 0 and avg_time_per_question > 90:
        recommendations.append(
            {
                "title": "Reduce Time Per Question",
                "detail": (
                    f"You average {avg_time_per_question:.0f} seconds per question "
                    "(recommended: under 90 seconds). "
                    "Practice reading questions quickly to improve response speed."
                ),
            }
        )
    elif quiz_attempts > 0 and 0 < avg_time_per_question <= 45:
        recommendations.append(
            {
                "title": "Efficient Response Time",
                "detail": (
                    f"Your average response time is {avg_time_per_question:.0f} seconds per question. "
                    "Excellent recall and preparation."
                ),
            }
        )

    if hint_usage > 3 and quiz_attempts > 0:
        hint_per_quiz = round(hint_usage / quiz_attempts, 1)
        recommendations.append(
            {
                "title": "Reduce Hint Dependency",
                "detail": (
                    f"You used hints {hint_usage} times across {quiz_attempts} quiz(zes) "
                    f"({hint_per_quiz} hints per quiz on average). "
                    "Try completing quizzes without hints to strengthen independent recall."
                ),
            }
        )

    if topics:
        weak_topics = [t for t in topics if t.mastery_level < 0.7]
        if weak_topics:
            nt = min(weak_topics, key=lambda t: t.mastery_level)
            recommendations.append(
                {
                    "title": f"Study Next: {nt.topic}",
                    "detail": (
                        f"{nt.topic} has the lowest mastery level "
                        f"({nt.mastery_level * 100:.0f}%) among your tracked topics. "
                        "Focus on this before moving to new material."
                    ),
                }
            )
        else:
            nt = topics[0]
            recommendations.append(
                {
                    "title": f"Continue: {nt.topic}",
                    "detail": (
                        "You have strong mastery across all studied topics. "
                        f"Continue deepening your knowledge of {nt.topic} with a new quiz."
                    ),
                }
            )

    if quiz_attempts == 0:
        recommendations.append(
            {
                "title": "Take Your First Quiz",
                "detail": (
                    "You haven't taken any quizzes yet. "
                    "Quizzes are the best way to measure retention. "
                    "Upload a document and generate a quiz to get started."
                ),
            }
        )
    elif quiz_attempts < 5:
        recommendations.append(
            {
                "title": "Build Quiz Consistency",
                "detail": (
                    f"You have completed {quiz_attempts} quiz(zes) so far. "
                    "Taking at least 5 quizzes gives the AI Tutor enough data "
                    "to personalise recommendations accurately."
                ),
            }
        )

    if truly_weak and favorite_mode != "Visual Learning":
        weak_names = ", ".join(r["Concept Name"] for r in truly_weak[:2])
        recommendations.append(
            {
                "title": "Try Visual Learning for Weak Concepts",
                "detail": (
                    f"Concepts like {weak_names} have low mastery scores. "
                    "Visual Learning (flowcharts and mind maps) can reinforce these "
                    "more effectively than text alone."
                ),
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
            "first_attempt_success_rate": first_attempt_success_rate,
            "comprehension_score": comprehension_score,
            "average_attempts": average_attempts,
            "avg_time_per_question": avg_time_per_question,
            "hint_usage": hint_usage,
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
            "highest_score": highest_score,
            "lowest_score": lowest_score,
            "improvement": quiz_line,
        },
        "badges": badges,
        "timeline": timeline,
        "timeline_days": timeline_days,
        "insights": insights,
        "recommendations": recommendations,
        "favorite_mode": favorite_mode,
    }
