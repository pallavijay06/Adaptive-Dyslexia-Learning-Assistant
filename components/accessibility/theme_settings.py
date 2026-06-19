"""Streamlit controls for accessibility theme preferences."""

from __future__ import annotations

from typing import TypedDict

import streamlit as st

from components.accessibility.font_settings import render_font_settings
from components.accessibility.spacing_settings import render_spacing_settings
from components.ui_constants import THEMES


class ThemeSettingsSelection(TypedDict):
    """Selected theme setting returned by the theme control."""

    theme: str


class AccessibilitySidebarSelection(TypedDict):
    """Aggregated accessibility settings returned by the sidebar."""

    font_size: str
    font_family: str
    character_spacing: str
    theme: str


def render_theme_settings() -> ThemeSettingsSelection:
    """Render the theme selector and persist the selected value.

    Returns:
        A typed dictionary containing the selected ``theme`` label.
    """

    theme_options = list(THEMES.keys())

    selected_theme = st.selectbox(
        "Theme",
        options=theme_options,
        key="theme",
    )

    return {"theme": selected_theme}


def render_accessibility_sidebar() -> AccessibilitySidebarSelection:
    """Render all Phase 1 accessibility settings in the Streamlit sidebar.

    Returns:
        A typed dictionary containing ``font_size``, ``font_family``,
        ``character_spacing``, and ``theme`` selections.
    """

    with st.sidebar:
        st.header("Accessibility Settings")
        font_settings = render_font_settings()
        spacing_settings = render_spacing_settings()
        theme_settings = render_theme_settings()

    return {
        "font_size": font_settings["font_size"],
        "font_family": font_settings["font_family"],
        "character_spacing": spacing_settings["character_spacing"],
        "theme": theme_settings["theme"],
    }
