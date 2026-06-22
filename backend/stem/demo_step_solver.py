"""Standalone demo for the Step-by-Step Solver module.

Run from the project root with:

    streamlit run backend/stem/demo_step_solver.py

This demo is independent of app.py and the main STEM panel.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.stem.step_solver.solver_service import solve_problem
from backend.stem.step_solver.models import ProblemType


def _format_step_content(content: str) -> str:
    content = content.replace("*", " × ")
    content = content.replace("**", "^")
    content = content.replace("/", " / ")
    return content


def display_result(result) -> None:
    st.markdown("## Result")
    st.write("**Problem Type:**", result.problem_type.value if hasattr(result.problem_type, 'value') else str(result.problem_type))
    st.write("**Input Problem:**")
    st.code(result.input_expression)

    if result.success:
        st.markdown("### Step-by-Step Solution")
        if result.steps:
            for step in result.steps:
                if "\n" in step:
                    title, content = step.split("\n", 1)
                else:
                    title, content = step, ""

                st.markdown(f"**{title}**")
                if content:
                    st.write(_format_step_content(content))
                st.divider()
        else:
            st.info("No step-by-step details are available.")

        st.markdown("### Final Answer")
        st.success(result.final_answer or "No final answer available")
    else:
        st.error(result.final_answer or "An error occurred while solving the problem.")


def main() -> None:
    st.set_page_config(page_title="Step-by-Step Solver Demo", layout="centered")
    st.title("Step-by-Step Solver Demo")

    placeholder = (
        "10 + 5 * 2\n\n"
        "OR\n\n"
        "x + 5 = 12\n\n"
        "OR\n\n"
        "F = ma\n"
        "m = 5\n"
        "a = 2\n\n"
        "OR\n\n"
        "F = ma\n"
        "Find m\n"
        "F = 20\n"
        "a = 5"
    )

    problem_text = st.text_area("Enter a problem", value=placeholder, height=260)
    solve_button = st.button("Solve Problem")

    if solve_button:
        try:
            result = solve_problem(problem_text)
            display_result(result)
        except Exception as exc:
            st.error(f"An unexpected error occurred: {exc}")


if __name__ == "__main__":
    main()
