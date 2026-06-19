"""Streamlit controls for accessibility character-spacing preferences."""

from __future__ import annotations

from typing import TypedDict

import streamlit as st

from components.ui_constants import CHARACTER_SPACING


class SpacingSettingsSelection(TypedDict):
    """Selected spacing setting returned by the spacing control."""

    character_spacing: str


def render_spacing_settings() -> SpacingSettingsSelection:
    """Render the character-spacing selector.

    The selected option is persisted in Streamlit session state for reuse by
    future content rendering components.

    Returns:
        A typed dictionary containing the selected ``character_spacing`` label.
    """

    spacing_options = list(CHARACTER_SPACING.keys())

    selected_character_spacing = st.selectbox(
        "Character Spacing",
        options=spacing_options,
        key="character_spacing",
    )

    return {"character_spacing": selected_character_spacing}
