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
    from services.vocabulary_service import explain_word

    words = extract_difficult_words(content) if content is not None else _get_stored_words()
    if not words:
        return

    preferences = get_ui_preferences()
    theme = THEMES[preferences["theme"]]
    font_size = FONT_SIZES[preferences["font_size"]]
    character_spacing = CHARACTER_SPACING[preferences["character_spacing"]]

    # Present a simple list of words only. Selecting a word shows details below.
    st.markdown(f"""
    <div class="vocabulary-card" aria-label="Vocabulary support">
      <h2 class="vocabulary-heading">Vocabulary</h2>
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
                        .vocab-highlight {{
                                background-color: {theme["secondary_background"]};
                color: {theme['text_color']};
                padding: 0.5rem 0.75rem;
                border-radius: 6px;
                font-weight: 700;
            }}
    </style>
    """ , unsafe_allow_html=True)

    display_options = [_display_word(w) for w in words]
    selected_display = st.selectbox("Select a word to explore:", options=display_options, key="reading_vocab_select")

    if selected_display:
        # Map back to original lowercase word
        sel_word = None
        for w in words:
            if _display_word(w) == selected_display:
                sel_word = w
                break
        sel_word = sel_word or selected_display.lower()

        # Simple accent color for highlight to increase contrast
        def _vocab_accent_color(theme_dict: dict[str, str]) -> str:
            if theme_dict.get("background_color") == "#121826":
                return "#93C5FD"
            return "#1D4ED8"

        accent = _vocab_accent_color(theme)

        # Determine whether accent is light/dark to pick readable text color
        def _is_light_hex(hex_color: str) -> bool:
            c = hex_color.lstrip("#")
            if len(c) == 3:
                c = ''.join([ch*2 for ch in c])
            try:
                r = int(c[0:2], 16)
                g = int(c[2:4], 16)
                b = int(c[4:6], 16)
            except Exception:
                return False
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return brightness > 160

        highlight_text_color = "#000" if _is_light_hex(accent) else "#fff"

        # Use session cache to avoid repeated LLM calls across reruns
        cache = st.session_state.setdefault("vocab_explain_cache", {})
        key = str(sel_word).strip().lower()
        if key in cache:
            explanation = cache[key]
        else:
            with st.spinner("Looking up the word..."):
                try:
                    explanation = explain_word(sel_word)
                except Exception:
                    explanation = {
                        "word": _display_word(sel_word),
                        "meaning": _get_definition(sel_word),
                        "explanation": "",
                        "example": "",
                    }
            cache[key] = explanation
            st.session_state["vocab_explain_cache"] = cache

        html = dedent(
            f"""
            <div class="vocab-details" role="region" aria-live="polite">
              <div class="vocab-highlight">{explanation.get('word', selected_display)}</div>
              <div style="margin-top:0.9rem">
                <div><strong>📖 Meaning:</strong> {explanation.get('meaning','')}</div>
                <div style="margin-top:0.6rem"><strong>📝 Explanation:</strong> {explanation.get('explanation','')}</div>
                <div style="margin-top:0.6rem"><strong>💡 Example:</strong> "{explanation.get('example','')}"</div>
              </div>
            </div>
            <style>
                            .vocab-details {{
                                margin-top: {READING_SECTION_GAP};
                                font-size: {font_size}px;
                                line-height: {READING_LINE_HEIGHT};
                                letter-spacing: {character_spacing};
                                background-color: {theme['background_color']};
                                color: {theme['text_color']};
                                padding: 0.75rem;
                                border-radius: 8px;
                                border: 1px solid {theme['border_color']};
                            }}
                            .vocab-highlight {{
                                display: inline-block;
                                background-color: {accent};
                                color: {highlight_text_color};
                                padding: 0.5rem 0.75rem;
                                border-radius: 6px;
                                font-weight: 800;
                                box-shadow: 0 2px 6px rgba(0,0,0,0.08);
                            }}
            </style>
            """
        ).strip()

        _render_html(st, html)


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
