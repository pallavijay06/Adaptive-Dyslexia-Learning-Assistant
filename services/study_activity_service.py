"""Shared study activity calculations used by Progress Dashboard and Learning Behaviour Analytics."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from database.models import LearningHistoryRecord, LearningSessionRecord


def normalize_datetime(value: Any) -> datetime | None:
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


def extract_date(value: Any) -> date | None:
    dt = normalize_datetime(value)
    if dt is None:
        return None
    return dt.date()


def calculate_current_streak(dates: list[date]) -> int:
    """Return consecutive calendar days ending on the most recent active day."""
    if not dates:
        return 0

    unique_days = sorted(set(dates), reverse=True)
    streak = 0
    current = unique_days[0]

    while streak < len(unique_days) and unique_days[streak] == current - timedelta(days=streak):
        streak += 1

    return streak


def calculate_longest_streak(dates: list[date]) -> int:
    """Return the longest run of consecutive calendar days with activity."""
    if not dates:
        return 0

    unique_days = sorted(set(dates))
    if len(unique_days) == 1:
        return 1

    longest = 1
    current = 1
    for index in range(1, len(unique_days)):
        if unique_days[index] == unique_days[index - 1] + timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def calculate_streak_metrics(dates: list[date]) -> dict[str, Any]:
    """Compute current streak, longest streak, and last active date."""
    if not dates:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "last_active_date": None,
        }

    unique_days = sorted(set(dates))
    last_active = unique_days[-1]
    return {
        "current_streak": calculate_current_streak(dates),
        "longest_streak": calculate_longest_streak(dates),
        "last_active_date": last_active.isoformat(),
    }


def collect_active_dates_from_sessions_and_history(
    sessions: list[LearningSessionRecord],
    history: list[LearningHistoryRecord] | None = None,
) -> list[date]:
    """Collect unique active calendar days from login sessions and learning history."""
    active_dates: list[date] = []
    for session in sessions:
        session_date = extract_date(session.timestamp)
        if session_date is not None:
            active_dates.append(session_date)

    for event in history or []:
        event_date = extract_date(event.timestamp)
        if event_date is not None:
            active_dates.append(event_date)

    return active_dates


def build_daily_study_time(
    sessions: list[LearningSessionRecord],
) -> dict[str, Any]:
    """Aggregate daily, weekly, and monthly study minutes from login sessions."""
    daily_study: dict[str, float] = defaultdict(float)
    weekly_study: dict[str, float] = defaultdict(float)
    monthly_study: dict[str, float] = defaultdict(float)

    for session in sessions:
        timestamp = normalize_datetime(session.timestamp)
        duration = float(session.session_duration_minutes or session.duration or 0)
        if not timestamp or duration <= 0:
            continue
        day_key = timestamp.strftime("%Y-%m-%d")
        week_key = f"{timestamp.isocalendar()[0]}-W{timestamp.isocalendar()[1]:02d}"
        month_key = timestamp.strftime("%Y-%m")
        daily_study[day_key] += duration
        weekly_study[week_key] += duration
        monthly_study[month_key] += duration

    today_key = datetime.utcnow().strftime("%Y-%m-%d")
    return {
        "daily": dict(sorted(daily_study.items())),
        "weekly": dict(sorted(weekly_study.items())),
        "monthly": dict(sorted(monthly_study.items())),
        "today_minutes": round(daily_study.get(today_key, 0.0), 1),
        "total_minutes": round(sum(daily_study.values()), 1),
    }
