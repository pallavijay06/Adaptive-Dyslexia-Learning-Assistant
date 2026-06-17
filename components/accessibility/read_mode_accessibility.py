"""Read Mode accessibility controls for dyslexia-friendly preferences."""

from __future__ import annotations

import streamlit as st

from components.accessibility.font_settings import render_font_settings
from components.accessibility.spacing_settings import render_spacing_settings
from components.accessibility.theme_settings import render_theme_settings
from components.session_state import initialize_ui_preferences


def render_read_mode_accessibility_panel() -> None:
    """Render accessibility controls inside Read Mode only."""

    initialize_ui_preferences()

    with st.expander("Accessibility Settings", expanded=False):
        render_font_settings()
        render_spacing_settings()
        render_theme_settings()
