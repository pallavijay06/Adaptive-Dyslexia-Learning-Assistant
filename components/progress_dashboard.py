"""Streamlit UI rendering for the Progress Dashboard."""

from __future__ import annotations

import streamlit as st
from typing import Any

from services.progress_dashboard_service import get_dashboard_data


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _pct_bar(value: float, max_value: float = 100.0) -> None:
    """Render a labelled progress bar clamped to [0, 1]."""
    ratio = min(max(float(value) / float(max_value) if max_value else 0.0, 0.0), 1.0)
    st.progress(ratio)


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _status_color(status: str) -> str:
    if "Mastered" in status:
        return "#10b981"
    if "Needs Revision" in status:
        return "#f59e0b"
    return "#ef4444"


def _status_html(status: str) -> str:
    color = _status_color(status)
    return f"<span style='color:{color};font-weight:600'>{status}</span>"


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_learner_overview(overview: dict[str, Any]) -> None:
    with st.expander("👤 Learner Overview", expanded=True):
        c = st.columns(5)
        c[0].metric("Name", overview["student_name"])
        c[1].metric("Age", overview["age"])
        c[2].metric("Grade", overview["grade"])
        c[3].metric("Institution", overview["institution"])
        c[4].metric("Field of Study", overview["field_of_study"])


def _render_comprehension_profile(profile: Any, progress: dict[str, Any]) -> None:
    with st.expander("🧠 Comprehension Profile", expanded=True):
        if not profile or profile.comprehension_score is None:
            st.info("Complete at least one quiz to unlock your Comprehension Profile.")
            return

        c = st.columns(4)
        c[0].metric("Comprehension Score", f"{profile.comprehension_score:.1f}%")
        c[1].metric("Level", profile.comprehension_level or "N/A")
        c[2].metric("Quiz Accuracy", _fmt_pct(progress["quiz_accuracy"]))
        c[3].metric("First-Attempt Success", _fmt_pct(progress["first_attempt_success_rate"]))

        _pct_bar(profile.comprehension_score)
        st.caption("Comprehension score is calculated from quiz accuracy, concept mastery, hint usage, first-attempt success, and response speed.")

        metric_breakdown = profile.metric_breakdown or {}
        if metric_breakdown:
            with st.expander("View score breakdown", expanded=False):
                for metric_name, detail in metric_breakdown.items():
                    if not isinstance(detail, dict):
                        continue
                    raw_val = detail.get("value") or 0.0
                    label = metric_name.replace("_", " ").title()
                    col_a, col_b = st.columns([3, 1])
                    col_a.caption(label)
                    col_b.caption(f"{raw_val:.1f}%")
                    _pct_bar(float(raw_val))


def _render_learning_mode(profile: Any, mode_usage: list[dict], favorite_mode: str) -> None:
    with st.expander("📊 Learning Behaviour Analytics", expanded=True):
        extended: dict[str, Any] = {}
        if profile and profile.learner_model_metadata:
            metadata = profile.learner_model_metadata
            if isinstance(metadata, dict):
                extended = metadata.get("learning_behaviour_analytics") or {}
                if not isinstance(extended, dict):
                    extended = {}

        session_duration = extended.get("session_duration") or {}
        return_frequency = extended.get("return_frequency") or {}
        daily_study_time = extended.get("daily_study_time") or {}
        completion_rate = extended.get("completion_rate") or {}
        consecutive_days = extended.get("consecutive_learning_days") or {}

        st.markdown("**Behaviour Score**")
        score_cols = st.columns(2)
        if profile and profile.learning_behaviour_analytics_score is not None:
            score_cols[0].metric(
                "Behaviour Score",
                f"{profile.learning_behaviour_analytics_score:.1f}%",
            )
            score_cols[1].metric(
                "Behaviour Level",
                profile.learning_behaviour_analytics_level or "N/A",
            )
            _pct_bar(profile.learning_behaviour_analytics_score)
        else:
            score_cols[0].metric("Behaviour Score", "N/A")
            score_cols[1].metric("Behaviour Level", "N/A")
            st.info("Use learning modes and complete a quiz to unlock behaviour analytics.")

        st.divider()
        st.markdown("**Current Metrics**")
        st.caption(f"Favorite mode: **{favorite_mode}**")

        if profile and profile.learning_behaviour_analytics_score is not None:
            metric_cols = st.columns(5)
            metric_cols[0].metric("Feature Utilization", _fmt_pct(profile.feature_utilization_score))
            metric_cols[1].metric("Mode Engagement", _fmt_pct(profile.mode_engagement_score))
            metric_cols[2].metric("Mode Switching", _fmt_pct(profile.mode_switching_score))
            metric_cols[3].metric("Mode Retention", _fmt_pct(profile.mode_retention_score))
            metric_cols[4].metric("Post Mode Improvement", _fmt_pct(profile.post_mode_improvement_score))

            breakdown = profile.learning_behaviour_analytics_metric_breakdown or {}
            if breakdown:
                for metric_name, detail in breakdown.items():
                    if not isinstance(detail, dict):
                        continue
                    raw_val = float(detail.get("value") or 0.0)
                    label = metric_name.replace("_", " ").title()
                    col_a, col_b = st.columns([3, 1])
                    col_a.caption(label)
                    col_b.caption(f"{raw_val:.1f}%")
                    _pct_bar(raw_val)
        elif mode_usage:
            st.caption("How often you use each learning mode:")
            for item in mode_usage:
                col_l, col_r = st.columns([4, 1])
                col_l.markdown(f"**{item['mode']}**")
                col_r.markdown(f"{item['percentage']}%")
                _pct_bar(item["percentage"])
        else:
            st.info("No learning mode usage recorded yet. Select a mode in the Learning Hub to get started.")

        st.divider()
        st.markdown("**Session Analytics**")
        session_cols = st.columns(4)
        session_cols[0].metric(
            "Average Session Duration",
            f"{session_duration.get('average_session_duration_minutes', 0)} mins",
        )
        session_cols[1].metric(
            "Total Learning Time",
            f"{session_duration.get('total_learning_time_minutes', 0)} mins",
        )
        session_cols[2].metric(
            "Daily Study Time",
            f"{daily_study_time.get('today_minutes', 0)} mins today",
        )
        completion_pct = float(completion_rate.get("completion_rate") or 0.0)
        session_cols[3].metric("Completion Rate", _fmt_pct(completion_pct))
        _pct_bar(completion_pct)
        st.caption(
            f"Completed {completion_rate.get('completed_sessions', 0)} of "
            f"{completion_rate.get('started_sessions', 0)} started sessions."
        )

        freq_cols = st.columns(2)
        freq_cols[0].metric(
            "Sessions Per Week",
            return_frequency.get("average_sessions_per_week", 0),
        )
        avg_gap = return_frequency.get("average_days_between_sessions")
        freq_cols[1].metric(
            "Average Gap Between Sessions",
            f"{avg_gap} day(s)" if avg_gap is not None else "N/A",
        )

        st.divider()
        st.markdown("**Learning Consistency**")
        consistency_cols = st.columns(3)
        consistency_cols[0].metric(
            "Current Streak",
            f"{consecutive_days.get('current_streak', 0)} day(s)",
        )
        consistency_cols[1].metric(
            "Longest Streak",
            f"{consecutive_days.get('longest_streak', 0)} day(s)",
        )
        last_active = consecutive_days.get("last_active_date")
        consistency_cols[2].metric(
            "Last Active Date",
            last_active or "N/A",
        )

        if daily_study_time.get("daily"):
            with st.expander("Daily study time trend", expanded=False):
                st.line_chart({"Daily minutes": dict(daily_study_time["daily"])})


def _difficulty_score_html(score: float, band: str, color: str) -> str:
    return (
        f"<span style='color:{color};font-weight:600'>"
        f"{score:.1f} — {band}</span>"
    )


def _render_difficulty_summary_card(label: str, item: dict[str, Any] | None, name_key: str) -> None:
    if not item:
        st.metric(label, "N/A")
        return
    name = item.get(name_key, "N/A")
    score = float(item.get("Difficulty Score") or 0.0)
    band = item.get("Band", "")
    color = item.get("Band Color", "#64748b")
    st.metric(label, name)
    st.markdown(
        _difficulty_score_html(score, band, color),
        unsafe_allow_html=True,
    )
    st.caption(
        f"Attempts: {item.get('Attempts', 0)} · "
        f"Accuracy: {float(item.get('Accuracy', 0.0)):.1f}%"
    )


def _render_difficulty_accuracy_table(rows: list[dict[str, Any]], name_key: str) -> None:
    if not rows:
        st.info("No data yet.")
        return

    header = st.columns([3, 1, 1, 2])
    header[0].markdown(f"**{name_key}**")
    header[1].markdown("**Attempts**")
    header[2].markdown("**Accuracy**")
    header[3].markdown("**Difficulty Score**")

    for row in rows:
        cols = st.columns([3, 1, 1, 2])
        cols[0].markdown(f"**{row[name_key]}**")
        cols[1].caption(str(row["Attempts"]))
        cols[2].caption(f"{float(row['Accuracy']):.1f}%")
        score = float(row["Difficulty Score"])
        cols[3].markdown(
            _difficulty_score_html(score, row["Band"], row["Band Color"]),
            unsafe_allow_html=True,
        )
        st.divider()


def _render_difficulty_profile(difficulty_data: dict[str, Any]) -> None:
    with st.expander("🎯 Difficulty Profile", expanded=True):
        if not difficulty_data.get("has_data"):
            st.info("Complete at least one quiz to unlock your Difficulty Profile.")
            return

        st.markdown("**Overall Difficulty Summary**")
        summary = difficulty_data.get("summary") or {}

        summary_cols = st.columns(5)
        with summary_cols[0]:
            _render_difficulty_summary_card(
                "Most Difficult Concept",
                summary.get("most_difficult_concept"),
                "Concept",
            )
        with summary_cols[1]:
            _render_difficulty_summary_card(
                "Most Difficult Question Type",
                summary.get("most_difficult_question_type"),
                "Question Type",
            )
        with summary_cols[2]:
            _render_difficulty_summary_card(
                "Most Difficult Skill",
                summary.get("most_difficult_skill"),
                "Skill",
            )
        with summary_cols[3]:
            _render_difficulty_summary_card(
                "Most Difficult Level",
                summary.get("most_difficult_level"),
                "Level",
            )
        with summary_cols[4]:
            top_error = summary.get("highest_error_frequency")
            if top_error:
                st.metric("Highest Error Frequency", top_error["Category"])
                st.markdown(
                    f"<span style='color:#ef4444;font-weight:600'>"
                    f"{float(top_error['Error Frequency']):.1f}%</span>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"Type: {top_error['Type']} · "
                    f"Attempts: {top_error['Attempts']} · "
                    f"Incorrect: {top_error['Incorrect']}"
                )
            else:
                st.metric("Highest Error Frequency", "N/A")

        st.caption(
            "Difficulty score = 100 − accuracy. "
            "Green (0–25) Low · Yellow (26–50) Moderate · "
            "Orange (51–75) High · Red (76–100) Very High"
        )

        st.divider()

        st.markdown("**Concept Difficulty**")
        _render_difficulty_accuracy_table(
            difficulty_data.get("concept_difficulty") or [],
            "Concept",
        )

        st.markdown("**Question Type Difficulty**")
        _render_difficulty_accuracy_table(
            difficulty_data.get("question_type_difficulty") or [],
            "Question Type",
        )

        st.markdown("**Skill Difficulty**")
        _render_difficulty_accuracy_table(
            difficulty_data.get("skill_difficulty") or [],
            "Skill",
        )

        st.markdown("**Difficulty Level Analysis**")
        _render_difficulty_accuracy_table(
            difficulty_data.get("difficulty_level_analysis") or [],
            "Level",
        )

        st.markdown("**Error Frequency**")
        error_rows = difficulty_data.get("error_frequency") or []
        if not error_rows:
            st.info("No error frequency data yet.")
        else:
            header = st.columns([3, 2, 1, 1, 2])
            header[0].markdown("**Category**")
            header[1].markdown("**Type**")
            header[2].markdown("**Attempts**")
            header[3].markdown("**Incorrect**")
            header[4].markdown("**Error Frequency**")
            for row in error_rows:
                cols = st.columns([3, 2, 1, 1, 2])
                cols[0].markdown(f"**{row['Category']}**")
                cols[1].caption(row["Type"])
                cols[2].caption(str(row["Attempts"]))
                cols[3].caption(str(row["Incorrect"]))
                freq = float(row["Error Frequency"])
                freq_color = "#ef4444" if freq > 50 else "#f97316" if freq > 25 else "#64748b"
                cols[4].markdown(
                    f"<span style='color:{freq_color};font-weight:600'>{freq:.1f}%</span>",
                    unsafe_allow_html=True,
                )
                st.divider()


def _trend_color(status: str) -> str:
    if status == "Improving":
        return "#10b981"
    if status == "Declining":
        return "#ef4444"
    return "#64748b"


def _render_mini_history(values: list[float], arrow: str = "→") -> None:
    if not values:
        st.caption("No history yet.")
        return
    parts = [f"**{value:.0f}**" for value in values]
    st.markdown(f" {arrow} ".join(parts))


def _compact_line_chart(data: list[tuple[str, float]], y_label: str) -> None:
    """Render a compact ~200px Vega-Lite line chart with tight axis scaling."""
    if not data:
        return
    values = [v for _, v in data]
    y_min = max(0.0, min(values) - 10)
    y_max = min(100.0, max(values) + 10) if max(values) <= 100 else max(values) * 1.1
    records = [{"x": label, "y": val} for label, val in data]
    st.vega_lite_chart(
        {"values": records},
        {
            "height": 200,
            "mark": {"type": "line", "point": True, "interpolate": "monotone"},
            "encoding": {
                "x": {"field": "x", "type": "ordinal", "axis": {"labelAngle": -30, "title": None}},
                "y": {
                    "field": "y",
                    "type": "quantitative",
                    "scale": {"domain": [y_min, y_max]},
                    "axis": {"title": y_label},
                },
            },
            "config": {"view": {"stroke": "transparent"}},
        },
        use_container_width=True,
    )


def _render_learning_progress(
    progress: dict[str, Any],
    quiz_performance: dict[str, Any],
    study_activity: dict[str, Any],
    learning_analytics: dict[str, Any],
) -> None:
    with st.expander("📊 Learning Progress", expanded=True):
        st.caption("Evidence of learner improvement over time.")

        # --- Core metrics ---
        c = st.columns(4)
        c[0].metric("📄 Documents Studied", progress["documents_studied"])
        c[1].metric("📝 Quiz Attempts", progress["quiz_attempts"])
        c[2].metric("🎯 Quiz Accuracy", _fmt_pct(progress["quiz_accuracy"]))
        c[3].metric("🏆 Highest Score", f"{quiz_performance['highest_score']}%")

        c2 = st.columns(3)
        c2[0].metric("⬇ Lowest Score", f"{quiz_performance['lowest_score']}%")
        c2[1].metric("⏱ Avg Session Duration", f"{int(progress['avg_session_duration'])} mins")
        c2[2].metric("⚡ Avg Time / Question", f"{int(progress['avg_time_per_question'])}s")

        st.divider()

        improvement = learning_analytics.get("learning_improvement_trend") or {}
        comprehension = learning_analytics.get("comprehension_trend") or {}
        difficulty = learning_analytics.get("difficulty_reduction") or {}
        retention = learning_analytics.get("retention_score") or {}
        most_improved = learning_analytics.get("most_improved_concept") or {}
        needs_practice = learning_analytics.get("needs_more_practice") or {}
        weekly_goal = learning_analytics.get("weekly_goal") or {}

        # --- Learning Trend ---
        st.markdown("**Learning Trend**")
        trend_cols = st.columns(2)
        trend_status = improvement.get("status", "Stable")
        trend_color = _trend_color(trend_status)
        trend_cols[0].markdown(
            f"<span style='color:{trend_color};font-size:1.4rem;font-weight:700'>"
            f"{trend_status}</span>",
            unsafe_allow_html=True,
        )
        trend_cols[1].metric(
            "Overall Improvement",
            f"{improvement.get('overall_improvement_pct', 0.0):+.1f}%",
        )
        if improvement.get("history"):
            history_labels = [f"{label}: {pct:.0f}%" for label, pct in improvement["history"]]
            st.caption(" · ".join(history_labels))

        st.divider()

        # --- Comprehension Trend ---
        st.markdown("**Comprehension Trend**")
        comp_trend = comprehension.get("current_trend", "Stable")
        comp_color = _trend_color(comp_trend)
        st.markdown(
            f"<span style='color:{comp_color};font-weight:600'>"
            f"Current Trend: {comp_trend}</span>",
            unsafe_allow_html=True,
        )
        st.caption("See the Comprehension Trend chart below for historical values.")

        st.divider()

        # --- Difficulty Reduction ---
        st.markdown("**Difficulty Reduction**")
        diff_cols = st.columns(2)
        diff_status = difficulty.get("status", "Needs More Practice")
        diff_color = _trend_color(diff_status if diff_status == "Improving" else "Declining")
        diff_cols[0].markdown(
            f"<span style='color:{diff_color};font-weight:600'>{diff_status}</span>",
            unsafe_allow_html=True,
        )
        diff_cols[1].metric(
            "Difficulty Reduction",
            f"{difficulty.get('reduction_pct', 0.0):.1f}%",
        )
        if difficulty.get("weekly_history"):
            weekly_labels = [f"{week}: {score:.0f}" for week, score in difficulty["weekly_history"]]
            st.caption(" → ".join(weekly_labels))

        st.divider()

        # --- Retention, Most Improved, Needs Practice ---
        insight_cols = st.columns(3)

        with insight_cols[0]:
            st.markdown("**Retention Score**")
            if retention.get("has_data"):
                st.metric("", f"{retention.get('score', 0.0):.1f}%")
                _pct_bar(retention.get("score", 0.0))
                repeated = retention.get("repeated_concepts", 0)
                avg_acc = retention.get("avg_retained_accuracy", 0.0)
                st.caption(f"Based on {repeated} repeated concept{'s' if repeated != 1 else ''}")
                st.caption(f"Average retained accuracy: {avg_acc:.1f}%")
            else:
                st.info("Complete more quizzes to measure retention.")

        with insight_cols[1]:
            st.markdown("**Most Improved Concept**")
            if most_improved.get("has_data") and most_improved.get("concept"):
                st.markdown(f"**{most_improved['concept']}**")
                prev = most_improved.get('earliest_difficulty', 0)
                curr = most_improved.get('latest_difficulty', 0)
                imp = most_improved.get('improvement_pct', 0.0)
                st.markdown(
                    f"<div style='line-height:1.9;font-size:0.95rem;'>"
                    f"<span style='font-weight:600'>{prev:.0f}</span><br>"
                    f"<span style='color:#64748b'>↓</span><br>"
                    f"<span style='font-weight:600'>{curr:.0f}</span><br>"
                    f"<span style='color:#64748b'>↓</span><br>"
                    f"<span style='color:#10b981;font-weight:700'>{imp:.1f}% Improvement</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.info("Needs 2+ quizzes on the same concept.")

        with insight_cols[2]:
            st.markdown("**Needs More Practice**")
            if needs_practice.get("has_data") and needs_practice.get("concept"):
                concept_name = needs_practice["concept"]
                st.markdown(f"**{concept_name}**")
                # Pull detail from difficulty profile concept rows
                concept_rows = (learning_analytics.get("_difficulty_concept_rows") or [])
                matched = next(
                    (r for r in concept_rows if r.get("Concept") == concept_name),
                    None,
                )
                if matched:
                    st.caption(f"Difficulty: {float(matched.get('Difficulty Score', 0)):.0f}")
                    st.caption(f"Attempts: {matched.get('Attempts', 0)}")
                    st.caption(f"Accuracy: {float(matched.get('Accuracy', 0)):.1f}%")
                else:
                    st.caption(needs_practice.get("reason", ""))
            else:
                st.info("Complete a quiz to identify weak areas.")

        st.divider()

        # --- Weekly Goal ---
        st.markdown("**Weekly Learning Goal**")
        goal_cols = st.columns(3)
        completed = weekly_goal.get("completed_sessions", 0)
        goal = weekly_goal.get("goal", 5)
        goal_cols[0].metric("Completed Sessions", completed)
        goal_cols[1].metric("Goal", goal)
        goal_cols[2].metric("Progress", f"{weekly_goal.get('progress_pct', 0.0):.0f}%")
        st.caption(f"{completed} / {goal} Sessions")
        _pct_bar(weekly_goal.get("progress_pct", 0.0))

        st.divider()

        # --- Charts ---
        if quiz_performance.get("improvement"):
            st.markdown("**Quiz Trend**")
            _compact_line_chart(quiz_performance["improvement"], "Quiz Accuracy (%)")

        if study_activity.get("daily") or study_activity.get("weekly"):
            st.markdown("**Study Time**")
            if study_activity.get("daily"):
                st.caption("Daily study time (minutes)")
                _compact_line_chart(study_activity["daily"], "Minutes")
            if study_activity.get("weekly"):
                st.caption("Weekly study time (minutes)")
                _compact_line_chart(study_activity["weekly"], "Minutes")

        if comprehension.get("chart_data"):
            st.markdown("**Comprehension Trend**")
            _compact_line_chart(comprehension["chart_data"], "Comprehension Score")


def _render_concept_mastery(mastery: list[dict]) -> None:
    with st.expander("🟢 Concept Mastery", expanded=False):
        if not mastery:
            st.info("No concept mastery data yet. Complete quizzes to see your concept-level performance.")
            return

        # Render each concept as a compact card row instead of a wide table.
        for row in mastery:
            col_name, col_score, col_bar, col_status = st.columns([3, 1, 3, 2])
            col_name.markdown(f"**{row['Concept Name']}**")
            col_name.caption(f"Last studied: {row['Last Studied Date']}")
            col_score.metric("", f"{row['Mastery Score']}%")
            with col_bar:
                _pct_bar(row["Mastery Score"])
                st.caption(f"{row['Revisions']} revision(s)")
            col_status.markdown(
                _status_html(row["Current Status"]),
                unsafe_allow_html=True,
            )
            st.divider()


def _render_weak_concepts(weak: list[dict]) -> None:
    with st.expander("🔴 Weak Concepts", expanded=False):
        if not weak:
            st.success("✅ No weak concepts found. Keep up the great work!")
            return

        st.caption(f"{len(weak)} concept(s) need attention:")
        for row in weak:
            col_a, col_b, col_c = st.columns([3, 2, 2])
            col_a.markdown(f"**{row['Concept Name']}**")
            col_b.markdown(
                _status_html(row["Current Status"]),
                unsafe_allow_html=True,
            )
            col_c.caption(f"Mastery: {row['Mastery Score']}% · {row['Revisions']} revision(s)")
            _pct_bar(row["Mastery Score"])
            st.divider()


def _render_learning_mode_effectiveness(mode_effectiveness: dict[str, Any]) -> None:
    with st.expander("🏆 Learning Mode Effectiveness", expanded=True):
        rankings = mode_effectiveness.get("mode_rankings", [])
        recommended_mode = mode_effectiveness.get("recommended_mode")

        if recommended_mode:
            st.markdown("**Overall Recommended Learning Mode**")
            st.markdown(
                f"<div style='"
                f"display:inline-block;"
                f"background:#1d4ed8;color:#fff;"
                f"padding:6px 18px;border-radius:8px;"
                f"font-size:1rem;font-weight:700;"
                f"margin-bottom:1rem;"
                f"'>{recommended_mode}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info(
                "Complete at least one quiz after a learning session to see "
                "your mode effectiveness rankings."
            )
            return

        if not rankings:
            return

        st.divider()

        header_cols = st.columns([3, 2, 3, 3, 2])
        header_cols[0].markdown("**Learning Mode**")
        header_cols[1].markdown("**Sessions Used**")
        header_cols[2].markdown("**Avg Quiz Accuracy**")
        header_cols[3].markdown("**Avg Comprehension Score**")
        header_cols[4].markdown("**Effectiveness Score**")

        for rank in rankings:
            row_cols = st.columns([3, 2, 3, 3, 2])
            row_cols[0].markdown(rank["mode"])
            row_cols[1].markdown(str(rank["sessions"]))
            row_cols[2].markdown(f"{rank['average_quiz']}%")
            row_cols[3].markdown(f"{rank['average_comprehension']}%")
            row_cols[4].markdown(f"{rank['effectiveness']}%")


def _render_timeline(timeline_days: list[dict]) -> None:
    with st.expander("📅 Learning Timeline", expanded=False):
        if not timeline_days:
            st.info("Your learning timeline will appear here as you interact with the platform.")
            return

        for entry in timeline_days:
            st.markdown(f"**{entry['label']}**")
            for bullet in entry["bullets"]:
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;✓ {bullet}")
            st.divider()


def _render_badges(badges: list[str]) -> None:
    if not badges:
        return
    st.markdown("**🏅 Achievements**")
    badge_html = " ".join(
        f"<span style='display:inline-block;background:#1d4ed8;color:#fff;"
        f"padding:4px 10px;border-radius:999px;font-size:0.8rem;"
        f"margin:2px;'>{b}</span>"
        for b in badges
    )
    st.markdown(badge_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Next Learning Actions builder and renderer
# ---------------------------------------------------------------------------

_PRIORITY_STYLES: dict[str, dict[str, str]] = {
    "High":   {"dot": "🔴", "badge_bg": "#fee2e2", "badge_fg": "#b91c1c", "border": "#fca5a5"},
    "Medium": {"dot": "🟡", "badge_bg": "#fef9c3", "badge_fg": "#92400e", "border": "#fde68a"},
    "Low":    {"dot": "🟢", "badge_bg": "#dcfce7", "badge_fg": "#166534", "border": "#86efac"},
}


def _build_next_actions(
    progress: dict[str, Any],
    weak: list[dict],
    mastery: list[dict],
    mode_usage: list[dict],
    favorite_mode: str,
    profile: Any,
    quiz_performance: dict[str, Any],
    overview: dict[str, Any],
) -> list[dict[str, str]]:
    """Derive 3-5 prioritised next-action cards from actual learner data.

    Each card is a dict with keys: icon, title, action, reason, priority.
    Cards are ordered High -> Medium -> Low.
    """
    cards: list[dict[str, str]] = []

    quiz_attempts   = progress["quiz_attempts"]
    quiz_accuracy   = progress["quiz_accuracy"]
    first_attempt   = progress["first_attempt_success_rate"]
    avg_time        = progress["avg_time_per_question"]
    hint_usage      = progress["hint_usage"]
    docs_studied    = progress["documents_studied"]
    streak          = overview["current_streak"]
    comprehension   = progress["comprehension_score"]

    truly_weak   = [r for r in mastery if r["Current Status"] == "\U0001f534 Weak Concept"]
    needs_rev    = [r for r in mastery if r["Current Status"] == "\U0001f7e1 Needs Revision"]
    mastered     = [r for r in mastery if r["Current Status"] == "\U0001f7e2 Mastered"]

    # --- HIGH priority actions ---

    # 1. Weak concept to revise before next quiz.
    if truly_weak:
        worst = min(truly_weak, key=lambda r: r["Mastery Score"])
        cards.append({
            "icon": "🎯",
            "title": "Revise Before Your Next Quiz",
            "action": f"Revisit '{worst['Concept Name']}' in the Learning Hub before attempting another quiz.",
            "reason": f"Your mastery score is only {worst['Mastery Score']}% and {worst['Revisions']} revision(s) are on record.",
            "priority": "High",
        })

    # 2. Low first-attempt success — read before quizzing.
    if quiz_attempts > 0 and first_attempt < 50:
        cards.append({
            "icon": "📖",
            "title": "Read Simplified Notes Before Quizzing",
            "action": "Open the simplified version of your uploaded document and re-read it fully before starting a new quiz.",
            "reason": f"You answer only {first_attempt:.0f}% of questions correctly on the first attempt, indicating gaps in preparation.",
            "priority": "High",
        })

    # 3. Very low quiz accuracy.
    if quiz_attempts > 0 and quiz_accuracy < 50:
        cards.append({
            "icon": "📝",
            "title": "Focus on Core Concepts",
            "action": f"Spend extra time on the concepts with the lowest mastery scores before taking another quiz.",
            "reason": f"Your overall quiz accuracy is {quiz_accuracy:.0f}%, which suggests several core concepts need reinforcement.",
            "priority": "High",
        })

    # --- MEDIUM priority actions ---

    # 4. Concepts needing revision (not yet fully weak).
    if needs_rev and len(cards) < 5:
        target = needs_rev[0]
        cards.append({
            "icon": "🔁",
            "title": f"Revise '{target['Concept Name']}'",
            "action": f"Review '{target['Concept Name']}' using Simplified Notes or the AI Tutor before your next quiz.",
            "reason": f"Mastery is {target['Mastery Score']}% — one more revision session should bring it above the threshold.",
            "priority": "Medium",
        })

    # 5. No quizzes yet — take the first one.
    if quiz_attempts == 0 and docs_studied > 0 and len(cards) < 5:
        cards.append({
            "icon": "📝",
            "title": "Take Your First Quiz",
            "action": "Go to the Learning Hub, select your uploaded document, and generate a quiz.",
            "reason": "You have studied documents but haven't tested your retention yet. Quizzes are the fastest way to identify gaps.",
            "priority": "Medium",
        })

    # 6. High hint usage — try without hints.
    if hint_usage > 3 and quiz_attempts > 0 and len(cards) < 5:
        per_quiz = round(hint_usage / quiz_attempts, 1)
        cards.append({
            "icon": "🧠",
            "title": "Practice Independent Recall",
            "action": "Attempt the next quiz without using any hints to strengthen your independent recall.",
            "reason": f"You have used {hint_usage} hints across {quiz_attempts} quiz(zes) ({per_quiz} per quiz on average).",
            "priority": "Medium",
        })

    # 7. Slow response time — targeted reading.
    if quiz_attempts > 0 and avg_time > 90 and len(cards) < 5:
        cards.append({
            "icon": "⚡",
            "title": "Improve Your Response Speed",
            "action": "Re-read the simplified notes for the topic you quiz next to improve familiarity with key terms.",
            "reason": f"You average {avg_time:.0f}s per question. Faster recall comes from repeated exposure to the material.",
            "priority": "Medium",
        })

    # 8. No documents uploaded yet.
    if docs_studied == 0 and len(cards) < 5:
        cards.append({
            "icon": "📄",
            "title": "Upload Your First Document",
            "action": "Go to the Learning Hub and upload a PDF, PPTX, or DOCX file to get started.",
            "reason": "No documents have been studied yet. Uploading a document unlocks all learning modes and quizzes.",
            "priority": "Medium",
        })

    # --- LOW priority actions ---

    # 9. Try a different mode for weak concepts.
    if truly_weak and favorite_mode not in ("Visual Learning", "No preferred mode yet") and len(cards) < 5:
        weak_name = truly_weak[0]["Concept Name"]
        cards.append({
            "icon": "🎧",
            "title": "Try Visual Learning for Weak Concepts",
            "action": f"Switch to Visual Learning mode and generate a mind map or flowchart for '{weak_name}'.",
            "reason": f"Visual representations often help consolidate concepts with low mastery scores like '{weak_name}'.",
            "priority": "Low",
        })

    # 10. AI Tutor for weak concepts.
    if truly_weak and progress["questions_asked"] == 0 and len(cards) < 5:
        weak_name = truly_weak[0]["Concept Name"]
        cards.append({
            "icon": "🤖",
            "title": "Ask the AI Tutor",
            "action": f"Open the AI Tutor and ask: 'Can you explain {weak_name} in simple terms?'",
            "reason": f"You haven't used the AI Tutor yet and '{weak_name}' has a low mastery score.",
            "priority": "Low",
        })

    # 11. Streak encouragement.
    if streak >= 3 and len(cards) < 5:
        cards.append({
            "icon": "🔥",
            "title": "Keep Your Streak Going",
            "action": "Log in tomorrow and complete at least one quiz or reading session to maintain your streak.",
            "reason": f"You have been active for {streak} consecutive day(s). Consistent daily practice improves long-term retention.",
            "priority": "Low",
        })

    # 12. Accuracy improving — reward with harder content.
    if quiz_attempts >= 3 and quiz_accuracy >= 75 and len(mastered) >= 2 and len(cards) < 5:
        cards.append({
            "icon": "📚",
            "title": "Explore Advanced Content",
            "action": "Upload a new or more advanced document on the same topic to continue progressing.",
            "reason": f"Your quiz accuracy is {quiz_accuracy:.0f}% and you have mastered {len(mastered)} concept(s). You are ready for new material.",
            "priority": "Low",
        })

    # Sort High -> Medium -> Low and cap at 5.
    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    cards.sort(key=lambda c: priority_order.get(c["priority"], 9))
    return cards[:5]


def _render_next_actions(
    progress: dict[str, Any],
    weak: list[dict],
    mastery: list[dict],
    mode_usage: list[dict],
    favorite_mode: str,
    profile: Any,
    quiz_performance: dict[str, Any],
    overview: dict[str, Any],
) -> None:
    """Render the Next Learning Actions panel."""
    with st.expander("🚀 Next Learning Actions", expanded=True):
        cards = _build_next_actions(
            progress, weak, mastery, mode_usage,
            favorite_mode, profile, quiz_performance, overview,
        )

        if not cards:
            # No learner data yet — friendly onboarding prompt.
            st.markdown(
                """
                <div style='padding:1.2rem 1.4rem;border-radius:10px;
                            background:#f0f9ff;border:1px solid #bae6fd;
                            color:#0c4a6e;line-height:1.7;'>
                    <strong>👋 Welcome!</strong><br>
                    Complete your first learning session to receive personalised
                    recommendations here.<br><br>
                    <strong>To get started:</strong><br>
                    1. Upload a document in the <em>Learning Hub</em>.<br>
                    2. Choose a learning mode (Read, Listen, or Visual).<br>
                    3. Take a quiz to measure your understanding.
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        for card in cards:
            style   = _PRIORITY_STYLES.get(card["priority"], _PRIORITY_STYLES["Low"])
            dot     = style["dot"]
            bg      = style["badge_bg"]
            fg      = style["badge_fg"]
            border  = style["border"]
            icon    = card["icon"]
            title   = card["title"]
            action  = card["action"]
            reason  = card["reason"]
            priority = card["priority"]

            st.markdown(
                f"""
                <div style='
                    border:1px solid {border};
                    border-left:4px solid {fg};
                    border-radius:8px;
                    padding:1rem 1.2rem;
                    margin-bottom:0.8rem;
                    line-height:1.7;
                '>
                    <div style='display:flex;align-items:center;
                                justify-content:space-between;margin-bottom:0.35rem;'>
                        <span style='font-size:1.05rem;font-weight:700;'>
                            {icon}&nbsp;{title}
                        </span>
                        <span style='
                            background:{bg};color:{fg};
                            font-size:0.72rem;font-weight:700;
                            padding:2px 9px;border-radius:999px;
                            white-space:nowrap;
                        '>{dot} {priority} Priority</span>
                    </div>
                    <div style='margin-bottom:0.3rem;'>{action}</div>
                    <div style='font-size:0.85rem;color:#6b7280;'>
                        <em>Why: {reason}</em>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_insights_and_recommendations(
    insights: list[str],
    recommendations: list[dict],
    badges: list[str],
) -> None:
    with st.expander("💡 AI Tutor Insights & Recommendations", expanded=True):
        # Badges
        _render_badges(badges)

        if badges:
            st.divider()

        # Insights
        if insights:
            st.markdown("**What the data says about you:**")
            for insight in insights:
                st.markdown(f"&nbsp;&nbsp;• {insight}")
            st.divider()

        # Recommendations
        if recommendations:
            st.markdown("**Personalised recommendations:**")
            for item in recommendations:
                with st.container():
                    st.markdown(f"**{item['title']}**")
                    st.markdown(item["detail"])
                    st.divider()
        else:
            st.info("Start learning to receive personalised recommendations.")


def _generate_learning_summary(
    learning_analytics: dict[str, Any],
    progress: dict[str, Any],
) -> str:
    """Generate a rule-based learning summary from existing learner metrics. No LLM."""
    sentences: list[str] = []

    # Quiz trend
    improvement = learning_analytics.get("learning_improvement_trend") or {}
    trend_status = improvement.get("status", "Stable")
    improvement_pct = improvement.get("overall_improvement_pct", 0.0)
    if trend_status == "Improving":
        sentences.append(
            f"Quiz performance has improved by {improvement_pct:.1f}% over recent sessions."
        )
    elif trend_status == "Declining":
        sentences.append(
            f"Quiz performance has slightly declined by {abs(improvement_pct):.1f}% over recent sessions."
        )
    else:
        sentences.append("Quiz performance has remained stable across recent sessions.")

    # Comprehension trend
    comp = learning_analytics.get("comprehension_trend") or {}
    comp_trend = comp.get("current_trend", "Stable")
    if comp_trend == "Improving":
        sentences.append("Comprehension is trending upward.")
    elif comp_trend == "Declining":
        sentences.append("Comprehension has shown a recent decline — revisiting core material is recommended.")
    else:
        sentences.append("Comprehension remains consistent.")

    # Retention
    retention = learning_analytics.get("retention_score") or {}
    if retention.get("has_data"):
        score = retention.get("score", 0.0)
        repeated = retention.get("repeated_concepts", 0)
        if score >= 75:
            sentences.append(
                f"Retention remains strong at {score:.1f}% across {repeated} repeated concept{'s' if repeated != 1 else ''}."
            )
        elif score >= 50:
            sentences.append(
                f"Retention is moderate at {score:.1f}% — continued practice on repeated concepts is advised."
            )
        else:
            sentences.append(
                f"Retention is low at {score:.1f}% — revisiting previously studied concepts is strongly recommended."
            )

    # Needs more practice
    needs_practice = learning_analytics.get("needs_more_practice") or {}
    if needs_practice.get("has_data") and needs_practice.get("concept"):
        sentences.append(
            f"{needs_practice['concept']} still requires additional practice."
        )

    # Most improved concept
    most_improved = learning_analytics.get("most_improved_concept") or {}
    if most_improved.get("has_data") and most_improved.get("concept") and most_improved.get("improvement_pct", 0) > 0:
        sentences.append(
            f"{most_improved['concept']} has shown the highest improvement "
            f"({most_improved['improvement_pct']:.1f}%)."
        )

    # Difficulty reduction
    difficulty = learning_analytics.get("difficulty_reduction") or {}
    diff_status = difficulty.get("status", "")
    if diff_status == "Improving":
        sentences.append(
            f"Overall difficulty is reducing — keep practising to consolidate this progress."
        )
    elif diff_status == "Needs More Practice":
        sentences.append(
            "Overall difficulty has not yet reduced — focus on weaker concepts before attempting new material."
        )

    return " ".join(sentences) if sentences else ""


def _render_learning_summary(
    learning_analytics: dict[str, Any],
    progress: dict[str, Any],
) -> None:
    with st.expander("📝 Learning Summary", expanded=True):
        if not progress.get("quiz_attempts"):
            st.info("Complete at least one quiz to generate your Learning Summary.")
            return

        summary = _generate_learning_summary(learning_analytics, progress)
        if not summary:
            st.info("Not enough data yet to generate a summary.")
            return

        st.markdown(
            f"<div style='"
            f"background:#f8fafc;border-left:4px solid #1d4ed8;"
            f"border-radius:6px;padding:1rem 1.2rem;"
            f"line-height:1.8;color:#1e293b;font-size:0.95rem;"
            f"'>{summary}</div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Main render entry point
# ---------------------------------------------------------------------------

def render_dashboard(user_id: int) -> None:
    dashboard = get_dashboard_data(user_id)

    st.title("📈 Progress Dashboard")
    st.caption(
        "A personalised snapshot of your learning journey — "
        "comprehension, concept mastery, study habits, and AI Tutor recommendations."
    )

    overview        = dashboard["overview"]
    profile         = dashboard["profile"]
    progress        = dashboard["progress"]
    mastery         = dashboard["concept_mastery"]
    weak            = dashboard["weak_concepts"]
    mode_usage      = dashboard["learning_mode_usage"]
    study_activity  = dashboard["study_activity"]
    quiz_performance = dashboard["quiz_performance"]
    timeline_days   = dashboard.get("timeline_days", [])
    insights        = dashboard["insights"]
    recommendations = dashboard["recommendations"]
    favorite_mode   = dashboard["favorite_mode"]
    badges          = dashboard.get("badges", [])

    mode_effectiveness      = dashboard.get("learning_mode_effectiveness", {})
    difficulty_profile_data = dashboard.get("difficulty_profile", {})
    learning_analytics      = dashboard.get("learning_progress_analytics", {})

    _render_learner_overview(overview)
    _render_comprehension_profile(profile, progress)
    _render_learning_mode(profile, mode_usage, favorite_mode)
    _render_learning_mode_effectiveness(mode_effectiveness)
    _render_difficulty_profile(difficulty_profile_data)
    _render_learning_progress(progress, quiz_performance, study_activity, learning_analytics)
    _render_concept_mastery(mastery)
    _render_weak_concepts(weak)
    _render_timeline(timeline_days)
    _render_insights_and_recommendations(insights, recommendations, badges)
    _render_next_actions(
        progress, weak, mastery, mode_usage,
        favorite_mode, profile, quiz_performance, overview,
    )
    _render_learning_summary(learning_analytics, progress)
