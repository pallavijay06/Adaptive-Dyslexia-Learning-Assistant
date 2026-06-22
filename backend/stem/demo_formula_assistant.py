"""Standalone demo for the STEM Formula Assistant.

Run from the project root with:

    streamlit run backend/stem/demo_formula_assistant.py

This demo is isolated from the main app and uses the existing project LLM
configuration through the STEM Formula Assistant service.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.stem.formula_assistant import get_formula_explanations


def main() -> None:
    """Render the standalone Formula Assistant demo."""

    st.set_page_config(page_title="Formula Assistant Demo", layout="centered")
    st.subheader("Formula Assistant")

    sample_text = "F = ma\n\nV = IR"
    explanations = get_formula_explanations(sample_text)

    if not explanations:
        st.info("No formulas detected.")
        return

    for explanation in explanations:
        st.markdown("### Detected Formula")
        st.code(str(explanation["formula"]))

        st.markdown("### Terms")
        for term, description in explanation["terms"].items():
            st.write(f"{term} = {description}")

        st.markdown("### Meaning")
        st.write(str(explanation["meaning"]))

        st.markdown("### Real World Example")
        st.write(str(explanation["example"]))


if __name__ == "__main__":
    main()
