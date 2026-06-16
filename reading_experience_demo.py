"""Demo page for the dyslexia-friendly reading experience module."""

from __future__ import annotations

import streamlit as st

from components.accessibility.theme_settings import render_accessibility_sidebar
from components.reading.reading_view import (
    render_key_takeaways,
    render_learning_mode_switcher,
    render_listen_mode_placeholder,
    render_read_mode,
    render_visual_mode_placeholder,
)
from components.session_state import initialize_learning_mode, initialize_ui_preferences
from components.ui_constants import LEARNING_MODES


SAMPLE_EDUCATIONAL_CONTENT = """Photosynthesis

Plants use sunlight to make food. This process happens mainly inside the leaves. Leaves contain chlorophyll, a green material that captures energy from sunlight.

What Plants Need

- Sunlight provides energy.
- Water travels from the roots to the leaves.
- Carbon dioxide enters the leaves from the air.

During photosynthesis, plants use sunlight, water, and carbon dioxide to make glucose. Glucose is a simple sugar that stores energy for the plant. Oxygen is released as a byproduct, which helps many organisms breathe.

Why It Matters

Photosynthesis supports ecosystems because plants are food for many living things. The process also adds oxygen to the air. Without photosynthesis, many organisms would not have enough food or oxygen to survive.
"""


def main() -> None:
    """Render the standalone reading experience demo."""

    st.set_page_config(
        page_title="Reading Experience Demo",
        layout="centered",
    )

    initialize_ui_preferences()
    initialize_learning_mode()
    render_accessibility_sidebar()

    st.title("Broo test")
    selected_mode = render_learning_mode_switcher()

    if selected_mode == LEARNING_MODES[0]:
        render_read_mode(SAMPLE_EDUCATIONAL_CONTENT)
        render_key_takeaways(SAMPLE_EDUCATIONAL_CONTENT)
    elif selected_mode == LEARNING_MODES[1]:
        render_listen_mode_placeholder()
    else:
        render_visual_mode_placeholder()


if __name__ == "__main__":
    main()
