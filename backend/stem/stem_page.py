"""Reusable STEM page component for app integration."""

from __future__ import annotations

from typing import Any
from pathlib import Path

import streamlit as st

from backend.stem.diagram_explainer import explain_diagram
from backend.stem.formula_assistant import explain_formula
from backend.stem.symbol_assistant import explain_symbol
from backend.stem.stem_controller import process_stem_support
from backend.stem.step_solver.solver_service import solve_problem


def _format_step_content(content: str) -> str:
    content = content.replace("**", "^")
    content = content.replace("*", " × ")
    content = content.replace("/", " / ")
    return content


def _render_formula_tab(formulas: list[str]) -> None:
    if not formulas:
        st.info("No formulas detected in the document text.")
        return

    for formula in formulas:
        title = str(formula).strip() or "Untitled Formula"
        with st.expander(title):
            try:
                explanation = explain_formula(formula)
            except Exception as exc:  # pragma: no cover
                st.error("Formula Assistant is unavailable: " + str(exc))
                continue

            st.markdown("**Meaning**")
            st.write(str(explanation.get("meaning", "")))

            st.markdown("**Terms**")
            for term, description in (explanation.get("terms") or {}).items():
                st.write(f"{term} = {description}")

            st.markdown("**Real-world example**")
            st.write(str(explanation.get("example", "")))
            st.divider()


def _render_symbol_tab(symbols: list[str] | None) -> None:
    if symbols is None:
        st.error("Symbol data is unavailable. Please refresh the STEM analysis.")
        return

    if not isinstance(symbols, list):
        st.error("Symbol data is malformed. Expected a list of symbol identifiers.")
        return

    if not symbols:
        st.info("No STEM symbols detected in the document text.")
        return

    for symbol in symbols:
        if not isinstance(symbol, str) or not symbol.strip():
            continue

        symbol_text = symbol.strip()
        explanation = explain_symbol(symbol_text)
        title = symbol_text or "Symbol"

        with st.expander(title):
            st.markdown("**Meaning**")
            st.write(str(explanation.get("meaning", "")))

            st.markdown("**Simple explanation**")
            st.write(str(explanation.get("simple_explanation", "")))

            st.markdown("**Example**")
            st.write(str(explanation.get("example", "")))
            st.divider()


def _render_diagram_tab(diagram_images: list[str] | None) -> None:
    if not diagram_images:
        st.info("No diagram images are available for explanation.")
        return
    for idx, image_path in enumerate(diagram_images, start=1):
        filename = Path(image_path).name
        # Attempt to get a descriptive title from the diagram analysis when possible
        try:
            explanation = explain_diagram(image_path)
            diagram_type = explanation.get("diagram_type") or f"Uploaded Diagram {idx}"
        except Exception:
            explanation = None
            diagram_type = f"Uploaded Diagram {idx}"

        title = diagram_type if diagram_type else f"Uploaded Diagram {idx}"
        with st.expander(title):
            st.markdown(f"### {title}: {filename}")
            st.image(str(image_path), use_column_width=True)

            if explanation is None:
                st.error("Diagram Explanation failed or is unavailable.")
                continue

            st.markdown("**Diagram Type**")
            st.write(explanation.get("diagram_type", "Unknown"))

            st.markdown("**Purpose**")
            st.write(explanation.get("purpose", ""))

            st.markdown("**How It Works**")
            steps = explanation.get("how_it_works") or []
            if steps:
                for step in steps:
                    st.write(f"• {step}")
            else:
                st.write("No process steps were identified.")

            st.markdown("**Component Roles**")
            component_roles = explanation.get("component_roles") or []
            if component_roles:
                for component_role in component_roles:
                    st.write(f"• {component_role.get('component', '')}: {component_role.get('role', '')}")
            else:
                st.write("No components were identified.")

            st.markdown("**Key Concept**")
            st.write(explanation.get("key_concept", ""))

            st.markdown("**Simplified Explanation**")
            st.write(explanation.get("simplified_explanation", ""))

            st.markdown("**Key Takeaway**")
            st.write(explanation.get("key_takeaway", ""))
            st.divider()


def _render_step_solver_tab(document_text: str) -> None:
    problem_input = st.text_area(
        "Enter your STEM problem",
        value="",
        height=180,
        placeholder=(
            "10 + 5 * 2\n\n"
            "OR\n\n"
            "x + 5 = 12\n\n"
            "F = ma\n"
            "m = 5\n"
            "a = 2\n\n"
            "V = IR\n"
            "find I\n"
            "V = 10\n"
            "R = 2"
        ),
        key="stem_solver_input",
    )

    solve_clicked = st.button("Solve Problem")
    if not solve_clicked:
        st.info("Type a STEM problem and click Solve Problem to begin.")
        return

    if not problem_input or not problem_input.strip():
        st.error("Please enter a STEM problem before solving.")
        return

    with st.spinner("Solving the entered STEM problem..."):
        result = solve_problem(problem_input.strip())

    st.markdown("**Problem Type**")
    st.write(result.problem_type.value if hasattr(result.problem_type, "value") else str(result.problem_type))

    st.markdown("**Input**")
    st.code(result.input_expression)

    if not result.success:
        st.error(result.final_answer or "Unable to solve the entered problem.")
        return

    if result.steps:
        for step in result.steps:
            if "\n" in step:
                title, content = step.split("\n", 1)
            else:
                title, content = step, ""

            st.markdown(f"**{title.strip()}**")
            if content:
                st.write(_format_step_content(content.strip()))
            st.divider()
    else:
        st.info("No step-by-step details are available.")

    st.markdown("**Final Answer**")
    st.success(result.final_answer or "No final answer available")


def render_stem_mode(document_text: str, diagram_images: list[str] | None = None) -> None:
    """Render the reusable STEM Support page from processed document content."""
    stem_data = process_stem_support(document_text, diagram_images=diagram_images)

    st.header("🧮 STEM Support")
    st.divider()

    tabs = st.tabs([
        "Formula Assistant",
        "Symbol Explanation",
        "Diagram Explanation",
        "Step Solver",
    ])

    with tabs[0]:
        _render_formula_tab(stem_data["formulas"])
    with tabs[1]:
        _render_symbol_tab(stem_data["symbols"])
    with tabs[2]:
        _render_diagram_tab(stem_data["diagram_images"])
    with tabs[3]:
        _render_step_solver_tab(document_text)
