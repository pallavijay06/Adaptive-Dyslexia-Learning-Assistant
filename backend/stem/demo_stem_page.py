"""Standalone demo wrapper for the reusable STEM page component."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.stem.stem_page import render_stem_mode


def main() -> None:
    st.set_page_config(page_title="STEM Support Demo", layout="centered")

    sample_document_text = (
        "F = ma\n"
        "m = 5\n"
        "a = 2\n\n"
        "V = IR\n"
        "I = 2\n"
        "R = 4\n\n"
        "∑ represents summation in math.\n"
        "The circuit diagram shows a battery and resistor."
    )

    sample_diagrams: list[str] = []

    st.sidebar.header("STEM Demo Inputs")
    st.sidebar.markdown("Use the demo page to test the reusable STEM component.")
    st.sidebar.text_area("Document text", value=sample_document_text, height=260, key="demo_document_text")
    st.sidebar.info("This demo only shows how render_stem_mode works in isolation.")

    document_text = st.session_state.demo_document_text
    render_stem_mode(document_text, sample_diagrams)


if __name__ == "__main__":
    main()
