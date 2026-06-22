"""Standalone demo for the complete STEM Support page.

Run from the project root with:

    streamlit run backend/stem/demo_stem_complete.py

This page combines the existing STEM detection, formula assistant, symbol
explanation, diagram explanation, and step-by-step solver modules into a
single demo surface. It is intentionally built for future integration into
`app.py` or another larger UI surface.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.stem.diagram_explainer import explain_diagram
from backend.stem.formula_assistant import get_formula_explanations
from backend.stem.formula_extractor import extract_formulas
from backend.stem.symbol_assistant import get_symbol_explanations
from backend.stem.stem_controller import process_stem_support
from backend.stem.step_solver.solver_service import solve_problem


def _format_step_content(content: str) -> str:
    content = content.replace("**", "^")
    content = content.replace("*", " × ")
    content = content.replace("/", " / ")
    return content


def _display_metrics(result: Any) -> None:
    columns = st.columns(3)
    columns[0].metric("Formulas detected", result.formula_count)
    columns[1].metric("Symbols detected", result.symbol_count)
    columns[2].metric("Diagram references", result.diagram_count)


def _display_formula_explanations(document_text: str) -> None:
    formulas = extract_formulas(document_text)
    if not formulas:
        st.info("No extractable formulas found in the document text.")
        return

    st.subheader("Formula Assistant")
    st.write("The Formula Assistant explains formulas in simple language.")

    try:
        explanations = get_formula_explanations(document_text)
    except Exception as exc:  # pragma: no cover
        st.error("Formula Assistant is unavailable: " + str(exc))
        return

    if not explanations:
        st.info("No formula explanations were generated.")
        return

    for explanation in explanations:
        st.markdown("### Detected Formula")
        st.code(str(explanation["formula"]))

        st.markdown("**Meaning**")
        st.write(str(explanation["meaning"]))

        st.markdown("**Terms**")
        for term, description in explanation["terms"].items():
            st.write(f"{term} = {description}")

        st.markdown("**Real-world example**")
        st.write(str(explanation["example"]))
        st.divider()


def _display_symbol_explanations(document_text: str) -> None:
    symbols = get_symbol_explanations(document_text)
    if not symbols:
        st.info("No STEM symbols detected in the document text.")
        return

    st.subheader("Symbol Explanation")
    st.write("The Symbol Explanation feature gives short definitions for STEM symbols.")

    for symbol_data in symbols:
        st.markdown("### Detected Symbol")
        st.code(str(symbol_data.get("symbol", "")))

        st.markdown("**Meaning**")
        st.write(str(symbol_data.get("meaning", "")))

        st.markdown("**Simple explanation**")
        st.write(str(symbol_data.get("simple_explanation", "")))

        st.markdown("**Example**")
        st.write(str(symbol_data.get("example", "")))
        st.divider()


def _display_diagram_explanations(image_paths: list[str] | None) -> None:
    if not image_paths:
        st.info("Upload one or more diagram images to see Diagram Explanation results.")
        return

    st.subheader("Diagram Explanation")
    st.write("The Diagram Explanation feature analyzes uploaded images and explains them in simple terms.")

    for image_path in image_paths:
        st.markdown(f"### Uploaded Diagram: {Path(image_path).name}")
        st.image(str(image_path), use_column_width=True)

        try:
            explanation = explain_diagram(image_path)
        except Exception as exc:  # pragma: no cover
            st.error("Diagram Explanation failed: " + str(exc))
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


def _display_step_solver(document_text: str) -> None:
    st.subheader("Step-by-Step Solver")
    st.write("The Step-by-Step Solver uses the same STEM problem detection and solver service.")

    formulas = extract_formulas(document_text)
    problem_choices = formulas or [document_text.strip()] if document_text.strip() else []

    if not problem_choices:
        st.info("No solver input was detected in the document text.")
        return

    selected_problem = (
        st.selectbox("Choose the equation or problem to solve", problem_choices)
        if len(problem_choices) > 1
        else problem_choices[0]
    )

    if not selected_problem:
        st.info("Enter a problem or select a formula to solve.")
        return

    with st.spinner("Solving the selected STEM problem..."):
        result = solve_problem(selected_problem)

    st.markdown("**Problem Type**")
    st.write(result.problem_type.value if hasattr(result.problem_type, "value") else str(result.problem_type))

    st.markdown("**Input**")
    st.code(result.input_expression)

    if not result.success:
        st.error(result.final_answer or "Unable to solve the selected problem.")
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


def render_stem_support(document_text: str, diagram_paths: list[str] | None = None) -> None:
    """Render the complete STEM Support panel from extracted document content."""
    stem_data = process_stem_support(document_text)
    result = stem_data["result"]
    features = stem_data["features"]

    st.title("Complete STEM Support Demo")
    st.markdown(
        "This demo combines STEM detection, formula explanation, symbol explanation, "
        "diagram explanation, and step-by-step problem solving into one page."
    )

    st.subheader("Detected STEM Features")
    st.write(
        "Available features based on the document text: "
        + ", ".join(features) if features else "None"
    )

    _display_metrics(result)
    st.divider()

    st.subheader("Document Text")
    st.code(document_text or "(No document text provided)")
    st.divider()

    _display_formula_explanations(document_text)
    st.divider()

    _display_symbol_explanations(document_text)
    st.divider()

    _display_diagram_explanations(diagram_paths)
    st.divider()

    _display_step_solver(document_text)


def main() -> None:
    st.set_page_config(page_title="Complete STEM Support Demo", layout="centered")

    sample_document_text = (
        "F = ma\n"
        "m = 5\n"
        "a = 2\n\n"
        "V = IR\n"
        "I = 2\n"
        "R = 4\n\n"
        "∑ represents summation in math."
    )

    st.sidebar.header("STEM Support Inputs")
    document_text = st.sidebar.text_area(
        "Document text for STEM support",
        value=sample_document_text,
        height=260,
    )

    uploaded_files = st.sidebar.file_uploader(
        "Upload diagram images (PNG, JPG, JPEG)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )

    diagram_paths: list[str] = []
    if uploaded_files:
        import tempfile

        for uploaded_file in uploaded_files:
            suffix = Path(uploaded_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(uploaded_file.getvalue())
                diagram_paths.append(str(temp_file.name))

    if st.sidebar.button("Render STEM Support"):
        render_stem_support(document_text, diagram_paths)
    else:
        st.info("Edit the document text and upload diagrams, then click Render STEM Support.")


if __name__ == "__main__":
    main()
