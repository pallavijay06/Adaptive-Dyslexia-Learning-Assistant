"""Shared UI constants for Prototype 2 components.

Defines theme colors, font families, spacing values, and other constants
used across accessibility and visual components.
"""

from __future__ import annotations

from typing import Final

# ============================================================================
# Theme Definitions
# ============================================================================

THEMES: Final[dict[str, dict[str, str]]] = {
    "light": {
        "primary_bg": "#FFFFFF",
        "primary_text": "#000000",
        "secondary_bg": "#F5F5F5",
        "secondary_text": "#404040",
        "accent": "#2E7D32",
        "warning": "#F57C00",
    },
    "dark": {
        "primary_bg": "#1E1E1E",
        "primary_text": "#FFFFFF",
        "secondary_bg": "#2D2D2D",
        "secondary_text": "#E0E0E0",
        "accent": "#66BB6A",
        "warning": "#FFB74D",
    },
    "cream": {
        "primary_bg": "#FFFDD0",
        "primary_text": "#3E2723",
        "secondary_bg": "#FFF9E6",
        "secondary_text": "#5D4037",
        "accent": "#558B2F",
        "warning": "#FF6F00",
    },
    "yellow": {
        "primary_bg": "#FFFACD",
        "primary_text": "#333333",
        "secondary_bg": "#FFFEF0",
        "secondary_text": "#555555",
        "accent": "#FFA500",
        "warning": "#FF8C00",
    },
}

# ============================================================================
# Font Families
# ============================================================================

FONT_FAMILIES: Final[list[str]] = [
    "sans-serif",
    "monospace",
    "Georgia",
    "Calibri",
    "Arial",
]

# ============================================================================
# Font Sizes (in pixels)
# ============================================================================

FONT_SIZES: Final[dict[str, int]] = {
    "small": 12,
    "normal": 16,
    "medium": 18,
    "large": 20,
    "extra_large": 24,
}

# ============================================================================
# Character Spacing (em units)
# ============================================================================

CHARACTER_SPACINGS: Final[dict[str, float]] = {
    "normal": 0.0,
    "tight": -0.02,
    "loose": 0.05,
    "extra_loose": 0.1,
}

# ============================================================================
# Reading Spacing (line height multipliers)
# ============================================================================

READING_SPACINGS: Final[dict[str, float]] = {
    "compact": 1.2,
    "normal": 1.5,
    "relaxed": 1.8,
    "extra_relaxed": 2.0,
}

# ============================================================================
# Default Settings
# ============================================================================

DEFAULT_THEME: Final[str] = "light"
DEFAULT_FONT_FAMILY: Final[str] = "sans-serif"
DEFAULT_FONT_SIZE: Final[str] = "normal"
DEFAULT_CHARACTER_SPACING: Final[str] = "normal"
DEFAULT_READING_SPACING: Final[str] = "normal"

# ============================================================================
# Content Chunking Defaults
# ============================================================================

DEFAULT_CHUNK_SIZE: Final[int] = 500  # characters per chunk for display
DEFAULT_KEY_POINTS_COUNT: Final[int] = 5  # max key points to extract

# ============================================================================
# Audio Defaults
# ============================================================================

DEFAULT_PLAYBACK_SPEED: Final[float] = 1.0
MIN_PLAYBACK_SPEED: Final[float] = 0.5
MAX_PLAYBACK_SPEED: Final[float] = 2.0

# ============================================================================
# Visual Defaults
# ============================================================================

DEFAULT_VISUALIZATION_WIDTH: Final[int] = 800  # pixels
DEFAULT_VISUALIZATION_HEIGHT: Final[int] = 600  # pixels
