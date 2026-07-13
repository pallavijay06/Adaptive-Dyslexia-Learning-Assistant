"""Interactive one-question-at-a-time quiz UI component."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import streamlit as st

logger = logging.getLogger(__name__)


def initialize_quiz_session_state(
    mcqs: list[dict[str, Any]],
    short_questions: list[dict[str, Any]],
) -> None:
    """Initialize session state for the new interactive quiz experience."""
    if "quiz_state" not in st.session_state:
        # Merge MCQs and short questions into a single quiz list
        all_questions = []
        
        for i, mcq in enumerate(mcqs):
            all_questions.append({
                **mcq,
                "quiz_index": i,
                "original_type": "MCQ",
                "question_id": f"mcq_{i}",
            })
        
        for i, short_q in enumerate(short_questions):
            all_questions.append({
                **short_q,
                "quiz_index": len(mcqs) + i,
                "original_type": "Short Answer",
                "question_id": f"short_{i}",
            })
        
        st.session_state.quiz_state = {
            "questions": all_questions,
            "current_question_index": 0,
            "answers": [""] * len(all_questions),  # Store answers
            "completed_questions": set(),  # Track which questions have been answered and moved on from
            "question_timers": {},  # { question_index: { "view_start_time": ts_or_none, "accumulated_time": sec, "timer_started": bool } }
            "hints": {},  # { question_index: hint_text } - cached hints
            "hint_used": {},  # { question_index: count } - track hint usage
            "quiz_started": True,
            "quiz_submitted": False,
        }
        
        # Initialize timers for ALL questions
        for idx in range(len(all_questions)):
            _initialize_question_timer(idx)


def _initialize_question_timer(question_index: int) -> None:
    """Initialize timer for a question.
    
    Fields:
    - view_start_time: When user navigated to this question (None until first view)
    - accumulated_time: Total time spent across all visits
    - timer_started: Whether first interaction has occurred
    """
    if question_index not in st.session_state.quiz_state["question_timers"]:
        st.session_state.quiz_state["question_timers"][question_index] = {
            "view_start_time": None,  # Set when user enters the question (every visit)
            "accumulated_time": 0,  # Total time from all visits
            "timer_started": False,  # Whether first interaction occurred
        }


def mark_question_completed(question_index: int) -> None:
    """Mark a question as completed when moving away from it.
    
    A question is only marked as completed if it has an answer.
    """
    quiz_state = st.session_state.quiz_state
    answer = quiz_state["answers"][question_index]
    
    # Only mark as completed if there's an answer
    if answer and str(answer).strip():
        quiz_state["completed_questions"].add(question_index)


def _start_question_viewing(question_index: int) -> None:
    """Mark the start of viewing a question (called when navigating to it).
    
    This sets view_start_time to NOW, so time is counted from the moment
    the user navigates to the question, not just when they interact.
    """
    timers = st.session_state.quiz_state["question_timers"]
    
    # Lazy initialize if not already done
    if question_index not in timers:
        _initialize_question_timer(question_index)
    
    timer_data = timers.get(question_index)
    if timer_data and timer_data.get("view_start_time") is None:
        # First time viewing this question this session
        timer_data["view_start_time"] = time.time()


def _start_question_timer(question_index: int) -> None:
    """Mark first interaction with a question.
    
    Sets timer_started=True so we know the user has interacted.
    Time counting already started in _start_question_viewing().
    """
    timers = st.session_state.quiz_state["question_timers"]
    
    if question_index not in timers:
        _initialize_question_timer(question_index)
    
    timer_data = timers.get(question_index)
    if timer_data and not timer_data.get("timer_started", False):
        timer_data["timer_started"] = True


def _pause_question_timer(question_index: int) -> None:
    """Pause the question and accumulate the viewing time.
    
    Calculates time from when user navigated to the question (view_start_time)
    and adds it to accumulated_time. Resets view_start_time for next visit.
    """
    timer_data = st.session_state.quiz_state["question_timers"].get(question_index)
    if timer_data and timer_data.get("view_start_time") is not None:
        # Accumulate time from when user entered this question
        elapsed = time.time() - timer_data["view_start_time"]
        timer_data["accumulated_time"] += elapsed
        timer_data["view_start_time"] = None  # Clear for next visit


def get_current_question_time_seconds(question_index: int) -> int:
    """Get the current total time spent on a question.
    
    Includes accumulated time from previous visits PLUS current viewing session.
    """
    timer_data = st.session_state.quiz_state["question_timers"].get(question_index, {})
    accumulated = timer_data.get("accumulated_time", 0)
    view_start_time = timer_data.get("view_start_time")
    
    # If currently viewing, add time since entering this question
    if view_start_time is not None:
        elapsed = time.time() - view_start_time
        return int(accumulated + elapsed)
    else:
        # Not currently viewing (already paused)
        return int(accumulated)


def format_time_seconds(seconds: int) -> str:
    """Format seconds to MM:SS format."""
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins:02d}:{secs:02d}"


def get_quiz_submission_attempt_metadata(quiz_attempt_number: int, is_correct: bool) -> tuple[int, bool]:
    """Return attempt metadata for a whole-quiz submission."""
    attempt_number = max(1, int(quiz_attempt_number or 1))
    first_attempt_success = bool(is_correct and attempt_number == 1)
    return attempt_number, first_attempt_success


def render_quiz_progress_indicator(current_index: int, total: int) -> None:
    """Render the progress indicator based on COMPLETED questions, not current question."""
    quiz_state = st.session_state.quiz_state
    completed = len(quiz_state.get("completed_questions", set()))
    progress = (completed / total) if total > 0 else 0
    progress_pct = int(progress * 100)

    st.markdown(
        f"""
        <style>
        .quiz-progress-wrap {{
            display: flex; align-items: center; gap: 1rem;
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid #334155; border-radius: 14px;
            padding: 1rem 1.4rem; margin-bottom: 0.5rem;
        }}
        .quiz-q-label {{
            font-size: 1rem; font-weight: 700; color: #f8fafc;
            white-space: nowrap; min-width: 130px;
        }}
        .quiz-bar-wrap {{ flex: 1; }}
        .quiz-bar-bg {{
            background: #1e293b; border-radius: 999px; height: 10px;
            border: 1px solid #334155; overflow: hidden;
        }}
        .quiz-bar-fill {{
            height: 100%; border-radius: 999px;
            background: linear-gradient(90deg, #6366f1, #8b5cf6);
            transition: width 0.4s ease;
        }}
        .quiz-pct {{
            font-size: 0.82rem; color: #94a3b8; margin-top: 4px;
            text-align: right;
        }}
        </style>
        <div class="quiz-progress-wrap">
            <div class="quiz-q-label">Question {current_index + 1} / {total}</div>
            <div class="quiz-bar-wrap">
                <div class="quiz-bar-bg">
                    <div class="quiz-bar-fill" style="width:{progress_pct}%"></div>
                </div>
                <div class="quiz-pct">{completed} answered &nbsp;·&nbsp; {progress_pct}% complete</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_quiz_question(
    question: dict[str, Any],
    question_index: int,
    stored_answer: str,
) -> str:
    """
    Render a single quiz question with appropriate input based on type.

    Returns:
        The selected/entered answer
    """
    question_text = question.get("question", "")
    options = question.get("options", [])
    original_type = question.get("original_type", "MCQ")
    badge_color = "#6366f1" if original_type == "MCQ" else "#0ea5e9"
    badge_label = "Multiple Choice" if original_type == "MCQ" else "Short Answer"

    st.markdown(
        f"""
        <style>
        .quiz-card {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid #334155; border-radius: 16px;
            padding: 1.6rem 1.8rem; margin: 0.8rem 0 1rem;
        }}
        .quiz-type-badge {{
            display: inline-block;
            background: {badge_color}22; color: {badge_color};
            border: 1px solid {badge_color}55;
            border-radius: 999px; padding: 2px 12px;
            font-size: 0.75rem; font-weight: 700;
            letter-spacing: 0.05em; text-transform: uppercase;
            margin-bottom: 0.75rem;
        }}
        .quiz-question-text {{
            font-size: 1.08rem; font-weight: 600;
            color: #f1f5f9; line-height: 1.7;
        }}
        </style>
        <div class="quiz-card">
            <div class="quiz-type-badge">{badge_label}</div>
            <div class="quiz-question-text">{question_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if original_type == "MCQ" and options:
        options_with_placeholder = ["-- Select Answer --"] + options
        selected_index = (
            options_with_placeholder.index(stored_answer)
            if stored_answer and stored_answer in options
            else 0
        )
        st.markdown(
            "<p style='color:#94a3b8;font-size:0.9rem;margin:0 0 6px;'>Choose the best answer:</p>",
            unsafe_allow_html=True,
        )
        selected = st.radio(
            "Options:",
            options=options_with_placeholder,
            index=selected_index,
            key=f"question_{question_index}_answer",
            label_visibility="collapsed",
        )
        if selected != "-- Select Answer --" and (selected != stored_answer or not stored_answer):
            _start_question_timer(question_index)
        return selected if selected != "-- Select Answer --" else (stored_answer or "")
    else:
        st.markdown(
            "<p style='color:#94a3b8;font-size:0.9rem;margin:0 0 6px;'>Write your answer below:</p>",
            unsafe_allow_html=True,
        )
        answer = st.text_area(
            "Enter your answer:",
            value=stored_answer,
            key=f"question_{question_index}_answer",
            height=130,
            label_visibility="collapsed",
            placeholder="Type your answer here…",
        )
        if answer and not stored_answer:
            _start_question_timer(question_index)
        elif answer and answer != stored_answer:
            timer_data = st.session_state.quiz_state["question_timers"].get(question_index)
            if timer_data and not timer_data.get("timer_started", False):
                _start_question_timer(question_index)
        return answer or ""


def render_question_timer(question_index: int) -> None:
    """Render a styled timer for the current question."""
    seconds = get_current_question_time_seconds(question_index)
    formatted = format_time_seconds(seconds)
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg,#1e293b,#0f172a);
            border:1px solid #334155; border-radius:12px;
            padding:0.7rem 1rem; text-align:center;
        ">
            <div style="font-size:0.72rem;color:#64748b;letter-spacing:0.08em;
                        text-transform:uppercase;margin-bottom:2px;">⏱ Time</div>
            <div style="font-size:1.5rem;font-weight:800;color:#a5b4fc;
                        font-variant-numeric:tabular-nums;">{formatted}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hint_button(question_index: int, question: dict[str, Any]) -> str | None:
    """
    Render hint button with non-blocking hint generation.
    
    - Generates hint only once (cached)
    - Shows spinner only during generation
    - Never navigates away from quiz page
    - Remains on same quiz interface throughout
    """
    from services.quiz_hint_service import generate_quiz_hint
    
    quiz_state = st.session_state.quiz_state
    hints = quiz_state["hints"]
    hint_used = quiz_state["hint_used"]
    
    # Session state flag to track if user clicked hint button
    want_hint_flag = f"want_hint_{question_index}"
    generating_flag = f"generating_hint_{question_index}"
    
    # Initialize flags if not present
    if want_hint_flag not in st.session_state:
        st.session_state[want_hint_flag] = False
    if generating_flag not in st.session_state:
        st.session_state[generating_flag] = False
    
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "💡 Show Hint",
            key=f"hint_btn_{question_index}",
            help="Get a helpful hint for this question",
            use_container_width=True,
        ):
            st.session_state[want_hint_flag] = True
    
    # Generate hint if requested and not cached
    if st.session_state[want_hint_flag]:
        if question_index not in hints:
            # Not cached - generate it
            st.session_state[generating_flag] = True
            try:
                with st.spinner("Generating Hint..."):
                    question_text = question.get("question", "")
                    correct_answer = question.get("answer", "")
                    concept = question.get("concept", None)
                    
                    hint = generate_quiz_hint(
                        question=question_text,
                        correct_answer=correct_answer,
                        concept=concept,
                    )
                    
                    if hint:
                        hints[question_index] = hint
                        # Track hint usage
                        if question_index not in hint_used:
                            hint_used[question_index] = 0
                        hint_used[question_index] += 1
                    
                    st.session_state[generating_flag] = False
            except Exception:
                logger.exception("Failed to generate hint")
                st.error("Could not generate hint. Please try again.")
                st.session_state[generating_flag] = False
                st.session_state[want_hint_flag] = False
                return None
        else:
            # Cached - just track usage
            if question_index not in hint_used:
                hint_used[question_index] = 0
            if hint_used[question_index] == 0:  # Only increment if first time showing cached hint
                hint_used[question_index] += 1
    
    if question_index in hints:
        st.markdown(
            f"""
            <div style="
                background:#1e3a5f22; border:1px solid #3b82f655;
                border-left:4px solid #3b82f6; border-radius:10px;
                padding:0.9rem 1.1rem; margin-top:0.5rem;
                color:#93c5fd; font-size:0.95rem; line-height:1.6;
            ">
                💡 <strong>Hint:</strong> {hints[question_index]}
            </div>
            """,
            unsafe_allow_html=True,
        )
        return hints[question_index]
    
    return None


def render_quiz_navigation(
    current_index: int,
    total_questions: int,
    answers: list[str],
) -> tuple[str, int | None]:
    """
    Render navigation buttons (Previous, Next, Submit).
    
    Returns:
        Tuple of (action, next_index) where action is "previous", "next", "submit", or None
    """
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if current_index > 0:
            if st.button("◀ Previous", key="nav_prev", use_container_width=True):
                return "previous", current_index - 1
        else:
            st.button("◀ Previous", key="nav_prev", disabled=True, use_container_width=True)
    
    with col3:
        if current_index < total_questions - 1:
            if st.button("Next ▶", key="nav_next", use_container_width=True):
                return "next", current_index + 1
        else:
            # Last question - show Submit button
            if st.button("Submit Quiz", key="nav_submit", use_container_width=True):
                # Validate all questions are answered
                unanswered = [i for i, ans in enumerate(answers) if not ans or not str(ans).strip()]
                if unanswered:
                    st.warning(f"⚠️ Please answer all questions. Unanswered: {[i+1 for i in unanswered]}")
                    return None, None
                return "submit", None
    
    return None, None


def persist_question_timing(
    question_index: int,
    user_id: int | None = None,
    quiz_id: int | None = None,
) -> int:
    """
    Pause the current question's timer and return accumulated time.
    
    Args:
        question_index: Index of the question
        user_id: User ID (for database tracking)
        quiz_id: Quiz attempt ID (for database tracking)
    
    Returns:
        Time spent on question in seconds
    """
    _pause_question_timer(question_index)
    accumulated_time = get_current_question_time_seconds(question_index)
    
    # Optionally save to database if user_id is provided
    if user_id is not None:
        question = st.session_state.quiz_state["questions"][question_index]
        question_id = question.get("question_id", f"q_{question_index}")
        
        # This would be handled during quiz submission
        # For now, just track in session state
        pass
    
    return accumulated_time


def get_quiz_summary() -> dict[str, Any]:
    """
    Generate a quiz summary with per-question timing and basic stats.
    
    Returns:
        A dict with summary statistics
    """
    questions = st.session_state.quiz_state.get("questions", [])
    question_timers = st.session_state.quiz_state.get("question_timers", {})
    
    total_time = 0
    question_times = []
    
    for i, question in enumerate(questions):
        time_seconds = get_current_question_time_seconds(i)
        total_time += time_seconds
        question_times.append({
            "question_number": i + 1,
            "question": question.get("question", ""),
            "time_seconds": time_seconds,
            "time_formatted": format_time_seconds(time_seconds),
        })
    
    return {
        "total_time_seconds": total_time,
        "total_time_formatted": format_time_seconds(total_time),
        "question_times": question_times,
        "total_questions": len(questions),
    }
