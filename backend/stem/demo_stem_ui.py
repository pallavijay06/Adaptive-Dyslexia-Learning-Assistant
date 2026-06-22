"""Standalone demo for the STEM Support panel.

Run from the project root with:

    streamlit run backend/stem/demo_stem_ui.py

This demo is not imported by the main app and does not modify existing routes,
UI modules, or document-processing pipelines.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.stem.stem_controller import process_stem_support
from backend.stem.stem_ui import render_stem_panel


def main() -> None:
    """Render a self-contained STEM panel demo using real detection output."""

    st.set_page_config(page_title="STEM Support Demo", layout="centered")

    sample_document_text = (
        "F = ma\n\n"
        "Δx = x2 - x1\n\n"
        "∑ represents summation.\n\n"
        "The circuit diagram is shown below."
    )
    stem_data = process_stem_support(sample_document_text)

    render_stem_panel(stem_data["result"], stem_data["features"])


if __name__ == "__main__":
    main()
