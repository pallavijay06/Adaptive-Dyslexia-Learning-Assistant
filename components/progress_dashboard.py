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

        st.divider()

        c2 = st.columns(4)
        c2[0].metric("⏱ Total Study Time", f"{overview['total_study_time']} mins")
        c2[1].metric("📅 Learning Sessions", overview["total_learning_sessions"])
        c2[2].metric("🗓 Days Active", overview["days_active"])
        c2[3].metric("🔥 Current Streak", f"{overview['current_streak']} day(s)")


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
    with st.expander("🎯 Learning Mode", expanded=True):
        c = st.columns(2)
        c[0].metric("Favorite Mode", favorite_mode)

        if profile and profile.learning_mode_effectiveness_score is not None:
            c[1].metric(
                "Mode Effectiveness",
                f"{profile.learning_mode_effectiveness_score:.1f}%",
            )
        else:
            c[1].metric("Mode Effectiveness", "N/A")

        if mode_usage:
            st.caption("How often you use each learning mode:")
            for item in mode_usage:
                col_l, col_r = st.columns([4, 1])
                col_l.markdown(f"**{item['mode']}**")
                col_r.markdown(f"{item['percentage']}%")
                _pct_bar(item["percentage"])
        else:
            st.info("No learning mode usage recorded yet. Select a mode in the Learning Hub to get started.")

        if profile and profile.learning_mode_effectiveness_score is not None:
            with st.expander("View mode effectiveness details", expanded=False):
                eff_cols = st.columns(4)
                eff_cols[0].metric("Engagement", _fmt_pct(profile.mode_engagement_score))
                eff_cols[1].metric("Feature Utilisation", _fmt_pct(profile.feature_utilization_score))
                eff_cols[2].metric("Post-Mode Improvement", _fmt_pct(profile.post_mode_improvement_score))
                eff_cols[3].metric("Mode Retention", _fmt_pct(profile.mode_retention_score))

                breakdown = profile.learning_mode_metric_breakdown or {}
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


def _render_learning_progress(progress: dict[str, Any], quiz_performance: dict[str, Any], study_activity: dict[str, Any], favorite_mode: str) -> None:
    with st.expander("📊 Learning Progress", expanded=True):
        # --- Row 1: content engagement ---
        c = st.columns(4)
        c[0].metric("📄 Documents Studied", progress["documents_studied"])
        c[1].metric("📚 Topics Covered", progress["topics_covered"])
        c[2].metric("💡 Concepts Learned", progress["concepts_learned"])
        c[3].metric("🤖 AI Tutor Questions", progress["questions_asked"])

        st.divider()

        # --- Row 2: quiz performance ---
        c2 = st.columns(4)
        c2[0].metric("📝 Quiz Attempts", progress["quiz_attempts"])
        c2[1].metric("🎯 Quiz Accuracy", _fmt_pct(progress["quiz_accuracy"]))
        c2[2].metric("🏆 Highest Score", f"{quiz_performance['highest_score']}%")
        c2[3].metric("⬇ Lowest Score", f"{quiz_performance['lowest_score']}%")

        _pct_bar(progress["quiz_accuracy"])
        st.caption("Quiz accuracy across all attempts.")

        st.divider()

        # --- Row 3: session metrics ---
        c3 = st.columns(3)
        c3[0].metric("⏱ Avg Session Duration", f"{int(progress['avg_session_duration'])} mins")
        c3[1].metric("⚡ Avg Time / Question", f"{int(progress['avg_time_per_question'])}s")
        c3[2].metric("💬 Hints Used", progress["hint_usage"])

        # --- Quiz score trend ---
        if quiz_performance["improvement"]:
            with st.expander("Quiz score trend", expanded=False):
                st.line_chart({"Score": dict(quiz_performance["improvement"])})

        # --- Study time charts ---
        if study_activity["daily"] or study_activity["weekly"]:
            with st.expander("Study time over time", expanded=False):
                if study_activity["daily"]:
                    st.caption("Daily study time (minutes)")
                    st.line_chart({"Daily": dict(study_activity["daily"])})
                if study_activity["weekly"]:
                    st.caption("Weekly study time (minutes)")
                    st.line_chart({"Weekly": dict(study_activity["weekly"])})


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

    _render_learner_overview(overview)
    _render_comprehension_profile(profile, progress)
    _render_learning_mode(profile, mode_usage, favorite_mode)
    _render_learning_progress(progress, quiz_performance, study_activity, favorite_mode)
    _render_concept_mastery(mastery)
    _render_weak_concepts(weak)
    _render_timeline(timeline_days)
    _render_insights_and_recommendations(insights, recommendations, badges)
    _render_next_actions(
        progress, weak, mastery, mode_usage,
        favorite_mode, profile, quiz_performance, overview,
    )
