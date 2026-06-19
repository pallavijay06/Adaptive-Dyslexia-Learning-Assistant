"""Centralized UI configuration for Prototype 2 accessibility settings.

This module is the single source of truth for user-facing accessibility
options. Components should import values from here instead of duplicating
labels, sizes, fonts, spacing values, or theme color definitions.
"""

from __future__ import annotations

from typing import Final, TypedDict


class ThemeColors(TypedDict):
    """Color palette used by an accessibility theme."""

    background_color: str
    text_color: str
    secondary_background: str
    border_color: str


FONT_SIZES: Final[dict[str, int]] = {
    "Small": 24,
    "Medium": 32,
    "Large": 38,
    "Extra Large": 44,
}
"""Available font-size labels mapped to CSS pixel values."""


CHARACTER_SPACING: Final[dict[str, str]] = {
    "Normal": "0px",
    "Relaxed": "2px",
    "Extra Relaxed": "4px",
}
"""Available character-spacing labels mapped to CSS letter-spacing values."""


FONTS: Final[list[str]] = [
    "Arial",
    "Verdana",
    "Courier"
]
"""Available font families for learner-facing content."""


THEMES: Final[dict[str, ThemeColors]] = {
    "Light": {
        "background_color": "#FFFFFF",
        "text_color": "#1F2933",
        "secondary_background": "#F5F7FA",
        "border_color": "#D9E2EC",
    },
    "Dark": {
        "background_color": "#121826",
        "text_color": "#F5F7FA",
        "secondary_background": "#1F2933",
        "border_color": "#52606D",
    },
    "Cream": {
        "background_color": "#FFF8E7",
        "text_color": "#2F2A1F",
        "secondary_background": "#F4E8C1",
        "border_color": "#D6C79B",
    },
    "Yellow": {
        "background_color": "#FFF9C4",
        "text_color": "#2B2B2B",
        "secondary_background": "#FFF59D",
        "border_color": "#E6D75A",
    },
}
"""Available accessibility themes mapped to their color palettes."""


DEFAULT_FONT_SIZE: Final[str] = "Medium"
DEFAULT_FONT_FAMILY: Final[str] = "Arial"
DEFAULT_CHARACTER_SPACING: Final[str] = "Normal"
DEFAULT_THEME: Final[str] = "Light"


# Compatibility aliases for existing Prototype 2 placeholder modules.
FONT_FAMILIES: Final[list[str]] = FONTS
CHARACTER_SPACINGS: Final[dict[str, str]] = CHARACTER_SPACING
READING_SPACINGS: Final[dict[str, float]] = {
    "Normal": 1.5,
    "Relaxed": 1.8,
    "Extra Relaxed": 2.0,
}
DEFAULT_READING_SPACING: Final[str] = "Normal"
DEFAULT_PLAYBACK_SPEED: Final[float] = 1.0
MIN_PLAYBACK_SPEED: Final[float] = 0.5
MAX_PLAYBACK_SPEED: Final[float] = 2.0
DEFAULT_CHUNK_SIZE: Final[int] = 500
DEFAULT_KEY_POINTS_COUNT: Final[int] = 5
DEFAULT_VISUALIZATION_WIDTH: Final[int] = 800
DEFAULT_VISUALIZATION_HEIGHT: Final[int] = 600


LEARNING_MODES: Final[list[str]] = [
    "📖 Read",
    "🔊 Listen",
    "🧠 Visual Learn",
]
"""Learning modes available in the Prototype 2 reading experience."""

DEFAULT_LEARNING_MODE: Final[str] = "📖 Read"


READING_CONTAINER_PADDING: Final[str] = "1.5rem"
READING_CONTAINER_RADIUS: Final[str] = "12px"
READING_SECTION_GAP: Final[str] = "1rem"
READING_COMPACT_GAP: Final[str] = "0.35rem"
READING_LIST_ITEM_PADDING: Final[str] = "0.75rem 0"
READING_LIST_INDENT: Final[str] = "1.25rem"
READING_LINE_HEIGHT: Final[float] = 1.8
READING_HEADING_LINE_HEIGHT: Final[float] = 1.35
READING_HEADING_SCALE: Final[str] = "1.2em"
READING_SECONDARY_HEADING_SCALE: Final[str] = "1.1em"
READING_CONTENT_MAX_WIDTH: Final[str] = "72ch"
READING_CARD_BORDER_WIDTH: Final[str] = "1px"
READING_HIGHLIGHT_RADIUS: Final[str] = "0.35rem"
READING_HIGHLIGHT_PADDING: Final[str] = "0.05rem 0.18rem"
READING_MAX_SENTENCES_PER_PARAGRAPH: Final[int] = 3
READING_LONG_PARAGRAPH_CHARACTER_LIMIT: Final[int] = 280
READING_TAKEAWAY_LIMIT: Final[int] = 4
READING_VOCABULARY_LIMIT: Final[int] = 8
