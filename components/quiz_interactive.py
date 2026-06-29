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
    """Render the progress indicator based on COMPLETED questions, not current question.
    
    A question is completed when the learner has:
    1. Provided an answer (MCQ selection OR short answer text)
    2. Clicked Next or Submit Quiz (moved away from the question)
    """
    quiz_state = st.session_state.quiz_state
    completed = len(quiz_state.get("completed_questions", set()))
    progress = (completed / total) if total > 0 else 0
    progress_pct = int(progress * 100)
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown(f"### Question {current_index + 1} of {total}")
    
    with col2:
        st.progress(progress)
        st.markdown(f"**{completed} / {total} Questions - {progress_pct}%**")


def render_quiz_question(
    question: dict[str, Any],
    question_index: int,
    stored_answer: str,
) -> str:
    """
    Render a single quiz question with appropriate input based on type.
    
    Detects first interaction and starts the timer.
    
    Args:
        question: Question data dict
        question_index: Index in the quiz
        stored_answer: The previously stored answer for this question
    
    Returns:
        The selected/entered answer
    """
    question_text = question.get("question", "")
    options = question.get("options", [])
    original_type = question.get("original_type", "MCQ")
    
    st.markdown("---")
    st.markdown(f"**Question:**\n\n{question_text}")
    st.markdown("---")
    
    if original_type == "MCQ" and options:
        # Multiple choice question
        st.markdown("**Choose the best answer:**")
        options_with_placeholder = ["-- Select Answer --"] + options
        
        if stored_answer and stored_answer in options:
            selected_index = options_with_placeholder.index(stored_answer)
        else:
            selected_index = 0
        
        selected = st.radio(
            "Options:",
            options=options_with_placeholder,
            index=selected_index,
            key=f"question_{question_index}_answer",
            label_visibility="collapsed",
        )
        
        # Start timer ONLY on first selection of this visit (when changing from placeholder)
        if selected != "-- Select Answer --" and selected != stored_answer:
            # User made a new selection (not just displaying stored answer)
            _start_question_timer(question_index)
        elif selected != "-- Select Answer --" and not stored_answer:
            # First time selecting an answer on fresh load of this question
            _start_question_timer(question_index)
        
        return selected if selected != "-- Select Answer --" else (stored_answer or "")
    else:
        # Short answer question
        st.markdown("**Your answer:**")
        answer = st.text_area(
            "Enter your answer:",
            value=stored_answer,
            key=f"question_{question_index}_answer",
            height=120,
            label_visibility="collapsed",
        )
        
        # Start timer on first interaction (when user types)
        if answer and not stored_answer:
            # First time user has typed something (was empty, now has text)
            _start_question_timer(question_index)
        elif answer and answer != stored_answer:
            # User has changed the answer (was answered, now changed)
            timer_data = st.session_state.quiz_state["question_timers"].get(question_index)
            if timer_data and not timer_data.get("timer_started", False):
                # Timer not started yet for this visit, start it now
                _start_question_timer(question_index)
        
        return answer or ""


def render_question_timer(question_index: int) -> None:
    """Render a live updating timer for the current question.
    
    Timer only shows time after first interaction.
    Timer updates on each rerun (which happens on user interaction).
    """
    seconds = get_current_question_time_seconds(question_index)
    st.metric(
        label="⏱ Time on this question",
        value=format_time_seconds(seconds),
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
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Button to request hint
        if st.button(
            "💡 Show Hint",
            key=f"hint_btn_{question_index}",
            help="Get a helpful hint for this question",
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
    
    # Display cached hint if available
    if question_index in hints:
        st.info(f"💡 **Hint:** {hints[question_index]}")
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
