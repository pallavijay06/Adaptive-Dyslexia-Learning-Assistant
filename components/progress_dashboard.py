"""Streamlit UI rendering for the Progress Dashboard."""

from __future__ import annotations

import streamlit as st
from typing import Any

from services.progress_dashboard_service import get_dashboard_data


def _render_metrics_row(label: str, value: Any, delta: str | None = None, description: str | None = None) -> None:
    if delta:
        st.metric(label, value, delta=delta)
    else:
        st.metric(label, value)
    if description:
        st.caption(description)


def _render_status_badge(status: str) -> str:
    if "Mastered" in status:
        return f"<span style='color: #10b981;'>{status}</span>"
    if "Needs Revision" in status:
        return f"<span style='color: #f59e0b;'>{status}</span>"
    return f"<span style='color: #ef4444;'>{status}</span>"


def _format_timeline_item(event: dict[str, str]) -> str:
    return f"**{event['time']}** — {event['event']}: {event['details']}"


def render_dashboard(user_id: int) -> None:
    dashboard = get_dashboard_data(user_id)

    st.title("📈 Progress Dashboard")
    st.markdown(
        "A personalized snapshot of your learning journey, strengths, weaknesses, study habits, and AI Tutor recommendations."
    )

    overview = dashboard["overview"]
    progress = dashboard["progress"]
    mastery = dashboard["concept_mastery"]
    weak = dashboard["weak_concepts"]
    mode_usage = dashboard["learning_mode_usage"]
    study_activity = dashboard["study_activity"]
    quiz_performance = dashboard["quiz_performance"]
    timeline = dashboard["timeline"]
    insights = dashboard["insights"]
    recommendations = dashboard["recommendations"]
    favorite_mode = dashboard["favorite_mode"]

    with st.expander("Learner Overview", expanded=True):
        st.markdown("#### Student Profile")
        cols = st.columns(5)
        cols[0].metric("Name", overview["student_name"])
        cols[1].metric("Age", overview["age"])
        cols[2].metric("Grade", overview["grade"])
        cols[3].metric("Institution", overview["institution"])
        cols[4].metric("Field of Study", overview["field_of_study"])

        st.markdown("#### Learning Snapshot")
        cols = st.columns(4)
        cols[0].metric("Total Study Time", f"{overview['total_study_time']} mins")
        cols[1].metric("Learning Sessions", overview["total_learning_sessions"])
        cols[2].metric("Days Active", overview["days_active"])
        cols[3].metric("Current Streak", overview["current_streak"])

    with st.expander("Learning Progress", expanded=True):
        st.markdown("### Progress Metrics")
        cols = st.columns(3)
        cols[0].metric("Documents Studied", progress["documents_studied"])
        cols[1].metric("Topics Covered", progress["topics_covered"])
        cols[2].metric("Concepts Learned", progress["concepts_learned"])

        cols = st.columns(3)
        cols[0].metric("Questions Asked", progress["questions_asked"])
        cols[1].metric("Quiz Attempts", progress["quiz_attempts"])
        cols[2].metric("Quiz Accuracy", f"{progress['quiz_accuracy']:.1f}%")

        st.progress(min(max(progress["quiz_accuracy"] / 100.0, 0.0), 1.0))
        st.caption("Your quiz accuracy from all attempts so far.")

        cols = st.columns(2)
        cols[0].metric("Average Session Duration", f"{int(progress['avg_session_duration'])} mins")
        cols[1].metric("Favorite Mode", favorite_mode)

    with st.expander("Concept Mastery", expanded=False):
        st.markdown("### Mastery Table")
        if mastery:
            df = st.dataframe(
                [
                    {
                        "Concept": row["Concept Name"],
                        "Mastery": f"{row['Mastery Score']}%",
                        "Revisions": row["Revisions"],
                        "Quiz Accuracy": row["Quiz Accuracy"],
                        "Last Studied": row["Last Studied Date"],
                        "Status": row["Current Status"],
                    }
                    for row in mastery
                ],
                use_container_width=True,
            )
        else:
            st.info("No concept mastery data available yet.")

    with st.expander("Weak Concepts", expanded=False):
        if weak:
            for row in weak:
                st.markdown(
                    f"- **{row['Concept Name']}** — {row['Quiz Accuracy']}, {row['Revisions']} revision(s) — {_render_status_badge(row['Current Status'])}",
                    unsafe_allow_html=True,
                )
        else:
            st.success("No weak concepts found. Keep up the good work!")

    with st.expander("Learning Mode Preference", expanded=False):
        st.markdown("### Mode Usage")
        for item in mode_usage:
            st.markdown(f"**{item['mode']}** — {item['percentage']}%")
            st.progress(min(max(item['percentage'] / 100.0, 0.0), 1.0))

    with st.expander("Study Activity", expanded=False):
        cols = st.columns(3)
        cols[0].metric("Daily Study Points", len(study_activity["daily"]))
        cols[1].metric("Weekly Study Points", len(study_activity["weekly"]))
        cols[2].metric("Monthly Study Points", len(study_activity["monthly"]))

        if study_activity["daily"]:
            st.line_chart({"Daily Study Time": dict(study_activity["daily"])})
        if study_activity["weekly"]:
            st.line_chart({"Weekly Study Time": dict(study_activity["weekly"])})
        if study_activity["monthly"]:
            st.line_chart({"Monthly Study Time": dict(study_activity["monthly"])})

    with st.expander("Quiz Performance", expanded=False):
        cols = st.columns(4)
        cols[0].metric("Total Quizzes", quiz_performance["total_quizzes"])
        cols[1].metric("Average Score", f"{quiz_performance['average_score']}%")
        cols[2].metric("Highest Score", f"{quiz_performance['highest_score']}%")
        cols[3].metric("Lowest Score", f"{quiz_performance['lowest_score']}%")

        if quiz_performance["improvement"]:
            st.line_chart({"Quiz Score": dict(quiz_performance["improvement"])})

    with st.expander("Learning Timeline", expanded=False):
        if timeline:
            for event in timeline[:20]:
                st.markdown(_format_timeline_item(event))
        else:
            st.info("Your learning timeline will appear here as you interact with the platform.")

    with st.expander("AI Tutor Insights & Recommendations", expanded=True):
        st.markdown("### Insights")
        for insight in insights:
            st.write(f"• {insight}")

        st.markdown("### AI Recommendations")
        for item in recommendations:
            st.markdown(f"**{item['title']}**")
            st.write(item["detail"])

    with st.expander("Help & Next Steps", expanded=False):
        st.info(
            "Use this dashboard to track your learning habits, revisit weak concepts, and follow the AI Tutor's recommendations. Refresh the page anytime to use the latest learner data."
        )
