"""Streamlit controls for accessibility font preferences."""

from __future__ import annotations

from typing import TypedDict

import streamlit as st

from components.ui_constants import FONTS, FONT_SIZES


class FontSettingsSelection(TypedDict):
    """Selected font settings returned by the font controls."""

    font_size: str
    font_family: str


def render_font_settings() -> FontSettingsSelection:
    """Render font size and font family selectors.

    Defaults are read from Streamlit session state. Any changed selection is
    persisted immediately for reuse by future reading, audio, or visual
    components.

    Returns:
        A typed dictionary containing the selected ``font_size`` and
        ``font_family`` labels.
    """

    font_size_options = list(FONT_SIZES.keys())

    selected_font_size = st.selectbox(
        "Font Size",
        options=font_size_options,
        key="font_size",
    )
    selected_font_family = st.selectbox(
        "Font Family",
        options=FONTS,
        key="font_family",
    )

    return {
        "font_size": selected_font_size,
        "font_family": selected_font_family,
    }
