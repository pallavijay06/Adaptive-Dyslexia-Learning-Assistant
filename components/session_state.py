"""Session-state helpers for Prototype 2 accessibility preferences.

The functions in this module manage only reusable UI preferences for future
components. They intentionally avoid upload, RAG, OCR, audio, and rendering
state so Prototype 1 behavior remains isolated.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict

import streamlit as st

from components.ui_constants import (
    CHARACTER_SPACING,
    DEFAULT_CHARACTER_SPACING,
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DEFAULT_LEARNING_MODE,
    DEFAULT_THEME,
    FONTS,
    FONT_SIZES,
    LEARNING_MODES,
    THEMES,
)


class UIPreferences(TypedDict):
    """Complete accessibility preference values stored in session state."""

    font_size: str
    font_family: str
    character_spacing: str
    theme: str


class UIPreferenceUpdates(TypedDict):
    """Partial accessibility preference update payload."""

    font_size: NotRequired[str]
    font_family: NotRequired[str]
    character_spacing: NotRequired[str]
    theme: NotRequired[str]


_DEFAULT_UI_PREFERENCES: UIPreferences = {
    "font_size": DEFAULT_FONT_SIZE,
    "font_family": DEFAULT_FONT_FAMILY,
    "character_spacing": DEFAULT_CHARACTER_SPACING,
    "theme": DEFAULT_THEME,
}


def initialize_ui_preferences() -> None:
    """Create missing accessibility preference keys in Streamlit session state.

    Existing values are preserved when valid. Invalid or stale values are
    repaired to defaults so downstream components can rely on known options.
    """

    for key, default_value in _DEFAULT_UI_PREFERENCES.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

    _repair_invalid_preferences()


def get_ui_preferences() -> UIPreferences:
    """Return current accessibility preferences from Streamlit session state.

    Returns:
        A typed dictionary containing ``font_size``, ``font_family``,
        ``character_spacing``, and ``theme``.
    """

    initialize_ui_preferences()
    return {
        "font_size": str(st.session_state.font_size),
        "font_family": str(st.session_state.font_family),
        "character_spacing": str(st.session_state.character_spacing),
        "theme": str(st.session_state.theme),
    }


def update_ui_preferences(**updates: str) -> UIPreferences:
    """Update accessibility preferences and return the resulting values.

    Args:
        **updates: Any subset of ``font_size``, ``font_family``,
            ``character_spacing``, and ``theme``.

    Raises:
        KeyError: If an unknown preference key is provided.
        ValueError: If a preference value is not one of the configured options.
    """

    initialize_ui_preferences()
    _validate_update_keys(updates)
    _validate_update_values(updates)

    for key, value in updates.items():
        st.session_state[key] = value

    return get_ui_preferences()


def initialize_learning_mode() -> None:
    """Create or repair the selected learning mode in Streamlit session state."""

    if "learning_mode" not in st.session_state:
        st.session_state.learning_mode = DEFAULT_LEARNING_MODE

    if st.session_state.learning_mode not in LEARNING_MODES:
        st.session_state.learning_mode = DEFAULT_LEARNING_MODE


def get_learning_mode() -> str:
    """Return the currently selected learning mode."""

    initialize_learning_mode()
    return str(st.session_state.learning_mode)


def update_learning_mode(mode: str) -> str:
    """Persist a selected learning mode and return the repaired value.

    Args:
        mode: One of the configured learning mode labels.

    Raises:
        ValueError: If ``mode`` is not configured in ``LEARNING_MODES``.
    """

    if mode not in LEARNING_MODES:
        raise ValueError(f"Invalid learning mode: {mode}")

    st.session_state.learning_mode = mode
    return get_learning_mode()


def _repair_invalid_preferences() -> None:
    """Reset invalid session-state preference values to safe defaults."""

    validators = {
        "font_size": FONT_SIZES,
        "font_family": FONTS,
        "character_spacing": CHARACTER_SPACING,
        "theme": THEMES,
    }

    for key, valid_values in validators.items():
        if st.session_state[key] not in valid_values:
            st.session_state[key] = _DEFAULT_UI_PREFERENCES[key]  # type: ignore[literal-required]


def _validate_update_keys(updates: dict[str, str]) -> None:
    """Ensure only known preference keys are updated."""

    unknown_keys = set(updates) - set(_DEFAULT_UI_PREFERENCES)
    if unknown_keys:
        unknown = ", ".join(sorted(unknown_keys))
        raise KeyError(f"Unknown UI preference key(s): {unknown}")


def _validate_update_values(updates: dict[str, str]) -> None:
    """Ensure preference update values exist in centralized configuration."""

    valid_options: dict[str, object] = {
        "font_size": FONT_SIZES,
        "font_family": FONTS,
        "character_spacing": CHARACTER_SPACING,
        "theme": THEMES,
    }

    for key, value in updates.items():
        if value not in valid_options[key]:
            raise ValueError(f"Invalid value for {key}: {value}")
