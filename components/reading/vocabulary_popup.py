"""Vocabulary extraction and display for dyslexia-friendly reading."""

from __future__ import annotations

import re
from collections.abc import Iterable
from textwrap import dedent

from components.ui_constants import (
    CHARACTER_SPACING,
    FONT_SIZES,
    READING_CARD_BORDER_WIDTH,
    READING_COMPACT_GAP,
    READING_CONTAINER_PADDING,
    READING_CONTAINER_RADIUS,
    READING_LINE_HEIGHT,
    READING_LIST_ITEM_PADDING,
    READING_SECTION_GAP,
    READING_SECONDARY_HEADING_SCALE,
    READING_VOCABULARY_LIMIT,
    THEMES,
)

BUILT_IN_DICTIONARY: dict[str, str] = {
    "adaptation": "A change that helps a living thing survive.",
    "byproduct": "Something extra made during a process.",
    "carbon": "A basic element found in living things and air.",
    "chlorophyll": "The green material in leaves that captures sunlight.",
    "chloroplast": "The part of a plant cell where food is made.",
    "condensation": "When water vapor cools and becomes liquid water.",
    "ecosystem": "Living and nonliving things interacting in one place.",
    "evaporation": "When liquid water changes into water vapor.",
    "glucose": "A simple sugar that living things use for energy.",
    "mitochondria": "Part of a cell that creates energy.",
    "nutrients": "Substances living things need to grow and stay healthy.",
    "organism": "A living thing.",
    "oxygen": "A gas many living things need to breathe.",
    "photosynthesis": "Process plants use to make food.",
    "precipitation": "Water that falls from clouds as rain, snow, sleet, or hail.",
    "required": "Needed for something to happen.",
    "respiration": "The process living things use to release energy from food.",
    "sunlight": "Light energy from the sun.",
    "transpiration": "Water leaving plant leaves as vapor.",
}

_STOP_WORDS: set[str] = {
    "about",
    "above",
    "after",
    "again",
    "because",
    "before",
    "between",
    "could",
    "during",
    "every",
    "from",
    "have",
    "into",
    "mainly",
    "other",
    "should",
    "their",
    "there",
    "these",
    "thing",
    "things",
    "through",
    "water",
    "where",
    "which",
    "while",
    "with",
    "would",
}

_WORD_PATTERN = re.compile(r"\b[A-Za-z][A-Za-z'-]*\b")


def extract_difficult_words(content: str) -> list[str]:
    """Extract long or uncommon words from content without external services.

    Args:
        content: Plain text to inspect.

    Returns:
        Unique difficult words, preserving first appearance order.
    """

    seen_words: set[str] = set()
    difficult_words: list[str] = []

    for match in _WORD_PATTERN.finditer(content):
        word = match.group(0).strip("'").lower()
        if not _is_difficult_word(word) or word in seen_words:
            continue

        seen_words.add(word)
        difficult_words.append(word)

    return difficult_words[:READING_VOCABULARY_LIMIT]


def render_vocabulary_panel(content: str | None = None) -> None:
    """Render a vocabulary card for difficult words in the current reading.

    Args:
        content: Optional content to extract words from. When omitted, the panel
            uses words stored by ``render_read_mode`` in Streamlit session state.
    """

    import streamlit as st
    from components.session_state import get_ui_preferences

    words = extract_difficult_words(content) if content is not None else _get_stored_words()
    if not words:
        return

    preferences = get_ui_preferences()
    theme = THEMES[preferences["theme"]]
    font_size = FONT_SIZES[preferences["font_size"]]
    character_spacing = CHARACTER_SPACING[preferences["character_spacing"]]

    items = "\n".join(
        (
            '<li class="vocabulary-item">'
            f'<span class="vocabulary-word">{_display_word(word)}</span>'
            f'<span class="vocabulary-definition">{_get_definition(word)}</span>'
            "</li>"
        )
        for word in words
    )

    html_content = dedent(
        f"""
        <div class="vocabulary-card" aria-label="Vocabulary support">
        <h2 class="vocabulary-heading">Vocabulary</h2>
        <ul class="vocabulary-list">
        {items}
        </ul>
        </div>
        <style>
        .vocabulary-card {{
            background-color: {theme["secondary_background"]};
            color: {theme["text_color"]};
            border: {READING_CARD_BORDER_WIDTH} solid {theme["border_color"]};
            border-radius: {READING_CONTAINER_RADIUS};
            padding: {READING_CONTAINER_PADDING};
            margin-top: {READING_SECTION_GAP};
            font-size: {font_size}px;
            line-height: {READING_LINE_HEIGHT};
            letter-spacing: {character_spacing};
        }}

        .vocabulary-heading {{
            color: {theme["text_color"]};
            font-size: {READING_SECONDARY_HEADING_SCALE};
            margin: 0 0 {READING_SECTION_GAP};
        }}

        .vocabulary-list {{
            list-style: none;
            margin: 0;
            padding: 0;
        }}

        .vocabulary-item {{
            border-top: {READING_CARD_BORDER_WIDTH} solid {theme["border_color"]};
            display: grid;
            gap: {READING_COMPACT_GAP};
            padding: {READING_LIST_ITEM_PADDING};
        }}

        .vocabulary-item:first-child {{
            border-top: 0;
            padding-top: 0;
        }}

        .vocabulary-word {{
            font-weight: 700;
        }}

        .vocabulary-definition {{
            opacity: 0.92;
        }}
        </style>
        """
    ).strip()
    _render_html(st, html_content)


def _render_html(streamlit_module: object, html_content: str) -> None:
    """Render raw HTML/CSS without exposing CSS rules as page text."""

    html_renderer = getattr(streamlit_module, "html", None)
    if callable(html_renderer):
        html_renderer(html_content)
        return

    markdown_renderer = getattr(streamlit_module, "markdown")
    markdown_renderer(html_content, unsafe_allow_html=True)


def _is_difficult_word(word: str) -> bool:
    """Return whether a word should be included in vocabulary support."""

    return (
        len(word) >= 9
        or word in BUILT_IN_DICTIONARY
    ) and word not in _STOP_WORDS


def _get_stored_words() -> list[str]:
    """Read difficult words stored by read mode from Streamlit session state."""

    import streamlit as st

    stored_words = st.session_state.get("reading_difficult_words", [])
    if not isinstance(stored_words, list):
        return []

    return [str(word) for word in stored_words]


def _get_definition(word: str) -> str:
    """Return a simple definition for a vocabulary word."""

    return BUILT_IN_DICTIONARY.get(word, "An important topic word from the reading.")


def _display_word(word: str) -> str:
    """Return a readable display form for a vocabulary word."""

    return word.capitalize()


def known_vocabulary_words(words: Iterable[str]) -> set[str]:
    """Return words that have built-in meanings."""

    return {word.lower() for word in words if word.lower() in BUILT_IN_DICTIONARY}


__all__ = [
    "BUILT_IN_DICTIONARY",
    "extract_difficult_words",
    "known_vocabulary_words",
    "render_vocabulary_panel",
]
