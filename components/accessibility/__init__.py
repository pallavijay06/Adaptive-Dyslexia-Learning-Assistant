"""Accessibility components for Prototype 2.

Provides font, spacing, and theme management for dyslexia-friendly reading.
"""

from __future__ import annotations

from components.accessibility.font_settings import render_font_settings
from components.accessibility.spacing_settings import render_spacing_settings
from components.accessibility.theme_settings import (
    render_accessibility_sidebar,
    render_theme_settings,
)

__all__ = [
    "render_accessibility_sidebar",
    "render_font_settings",
    "render_spacing_settings",
    "render_theme_settings",
]
