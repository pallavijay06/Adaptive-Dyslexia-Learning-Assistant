"""Standalone demo for the STEM Symbol Explanation assistant.

Run from the project root with:

    streamlit run backend/stem/demo_symbol_assistant.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.stem.symbol_assistant import get_symbol_explanations


def main() -> None:
    """Render a self-contained Symbol Explanation demo."""

    st.set_page_config(page_title="Symbol Explanation Demo", layout="centered")
    st.subheader("Symbol Explanation")

    sample_text = "\u03a3 \u0394 \u03c0 \u03bb \u2234"
    explanations = get_symbol_explanations(sample_text)

    if not explanations:
        st.info("No STEM symbols detected.")
        return

    for explanation in explanations:
        st.markdown("### Detected Symbol")
        st.code(str(explanation["symbol"]))

        st.markdown("### Meaning")
        st.write(str(explanation["meaning"]))

        st.markdown("### Simple Explanation")
        st.write(str(explanation["simple_explanation"]))

        st.markdown("### Example")
        st.write(str(explanation["example"]))


if __name__ == "__main__":
    main()
