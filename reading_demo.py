"""Demo app for the dyslexia-friendly reading view."""

from __future__ import annotations

import streamlit as st

from components.accessibility.theme_settings import render_accessibility_sidebar
from components.reading.reading_view import render_reading_view
from components.session_state import initialize_ui_preferences


DEMO_CONTENT = """Photosynthesis

Plants use sunlight to make food.

The process occurs mainly in the leaves.

Oxygen is released as a byproduct.

Sunlight, water and carbon dioxide are required.
"""


def main() -> None:
    """Render the standalone reading-view demonstration."""

    st.set_page_config(
        page_title="Reading View Demo",
        layout="centered",
    )

    initialize_ui_preferences()
    render_accessibility_sidebar()

    st.title("Reading View Demo")
    render_reading_view(DEMO_CONTENT)


if __name__ == "__main__":
    main()
