"""Dyslexia-friendly reading experience components for Streamlit."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from textwrap import dedent
from urllib.parse import quote

import streamlit as st

from components.reading.content_formatter import (
    ReadingContentBlock,
    format_content_for_reading,
)
from components.reading.vocabulary_popup import (
    BUILT_IN_DICTIONARY,
    _get_definition,
    extract_difficult_words,
)
from components.session_state import (
    get_ui_preferences,
    initialize_learning_mode,
)
from components.ui_constants import (
    CHARACTER_SPACING,
    FONTS,
    FONT_SIZES,
    LEARNING_MODES,
    READING_CARD_BORDER_WIDTH,
    READING_COMPACT_GAP,
    READING_CONTAINER_PADDING,
    READING_CONTAINER_RADIUS,
    READING_CONTENT_MAX_WIDTH,
    READING_HEADING_LINE_HEIGHT,
    READING_LINE_HEIGHT,
    READING_LIST_INDENT,
    READING_SECTION_GAP,
    READING_HEADING_SCALE,
    READING_SECONDARY_HEADING_SCALE,
    READING_TAKEAWAY_LIMIT,
    THEMES,
)

_SENTENCE_PATTERN = re.compile(r"[^.!?]+[.!?]?")
_WORD_PATTERN = re.compile(r"\b[A-Za-z][A-Za-z'-]*\b")
_VOCABULARY_QUERY_PARAM = "reading_vocab"
_VOCABULARY_CLEAR_VALUE = "__clear__"
_VOCABULARY_SESSION_KEY = "reading_active_vocabulary_key"


@dataclass
class _ReadingSection:
    """A group of content blocks rendered as one reading card."""

    heading: str | None = None
    blocks: list[ReadingContentBlock] = field(default_factory=list)


@dataclass(frozen=True)
class _ReadingStyle:
    """Resolved CSS values for the current accessibility preferences."""

    background_color: str
    text_color: str
    secondary_background: str
    border_color: str
    font_family: str
    font_size: int
    character_spacing: str


def render_learning_mode_switcher() -> str:
    """Render the learning mode selector and persist the chosen mode."""

    initialize_learning_mode()
    selected_mode = st.radio(
        "Learning Mode",
        options=LEARNING_MODES,
        horizontal=True,
        key="learning_mode",
    )

    return selected_mode


def render_read_mode(content: str) -> None:
    """Render dyslexia-friendly read mode for educational content.

    Args:
        content: Plain text content to display in read mode.
    """

    style = _get_reading_style()
    blocks = format_content_for_reading(content)
    difficult_words = extract_difficult_words(content)
    st.session_state.reading_difficult_words = difficult_words

    sections = _group_blocks_into_sections(blocks)
    active_vocabulary_key = _get_active_vocabulary_key()
    seen_words: set[str] = set()
    section_html = "\n".join(
        (
            _render_interactive_section(
                section,
                difficult_words,
                section_index,
                active_vocabulary_key,
                seen_words,
            )
            for section_index, section in enumerate(sections)
        )
    )

    html_content = (
        '<div class="reading-experience" aria-label="Read mode">\n'
        f"{section_html}\n"
        "</div>\n"
        f"{_build_reading_styles(style)}"
    )
    _render_html(html_content)


def render_key_takeaways(content: str) -> None:
    """Extract and render rule-based key takeaways below reading content.

    Args:
        content: Plain text content to summarize with simple heuristics.
    """

    takeaways = _extract_key_takeaways(content)
    if not takeaways:
        return

    style = _get_reading_style()
    items = "\n".join(
        f'<li class="takeaway-item">{html.escape(takeaway)}</li>'
        for takeaway in takeaways
    )

    html_content = dedent(
        f"""
        <div class="takeaways-card" aria-label="Key takeaways">
        <h2 class="takeaways-heading">Key Takeaways</h2>
        <ul class="takeaways-list">
        {items}
        </ul>
        </div>
        {_build_shared_card_styles(style)}
        <style>
        .takeaways-list {{
            margin: 0;
            padding-left: {READING_LIST_INDENT};
        }}

        .takeaway-item {{
            margin-bottom: {READING_COMPACT_GAP};
        }}

        .takeaway-item:last-child {{
            margin-bottom: 0;
        }}
        </style>
        """
    ).strip()
    _render_html(html_content)


def render_listen_mode_placeholder() -> None:
    """Render the placeholder card for future audio mode."""

    _render_placeholder_card("Audio Mode Coming Soon")


def render_visual_mode_placeholder() -> None:
    """Render the placeholder card for future visual learning mode."""

    _render_placeholder_card("Visual Learning Mode Coming Soon")


def render_reading_view(content: str) -> None:
    """Backward-compatible wrapper for the Phase 1.5 reading view."""

    render_read_mode(content)


def _render_interactive_section(
    section: _ReadingSection,
    difficult_words: list[str],
    section_index: int,
    active_vocabulary_key: str,
    seen_words: set[str],
) -> str:
    """Render one section as continuous reading HTML."""

    heading_html = (
        f'<h2 class="reading-heading">{html.escape(section.heading)}</h2>'
        if section.heading
        else ""
    )
    block_html = "\n".join(
        _render_interactive_block(
            block,
            difficult_words,
            section_index,
            block_index,
            active_vocabulary_key,
            seen_words,
        )
        for block_index, block in enumerate(section.blocks)
    )

    return (
        '<div class="reading-section-card">\n'
        f"{heading_html}\n"
        f"{block_html}\n"
        "</div>"
    )


def _render_interactive_block(
    block: ReadingContentBlock,
    difficult_words: list[str],
    section_index: int,
    block_index: int,
    active_vocabulary_key: str,
    seen_words: set[str],
) -> str:
    """Render a paragraph or list while preserving natural text flow."""

    if block.kind == "bullet_list":
        items = "\n".join(
            _render_interactive_list_item(
                item,
                difficult_words,
                section_index,
                block_index,
                item_index,
                active_vocabulary_key,
                seen_words,
            )
            for item_index, item in enumerate(block.items)
        )
        return f'<ul class="reading-bullet-list">{items}</ul>'

    block_key = _build_block_key(section_index, block_index)
    vocabulary_words: list[str] = []
    paragraph_html = _link_difficult_words(
        block.text,
        difficult_words,
        block_key,
        seen_words,
        vocabulary_words,
        active_vocabulary_key,
    )
    definition_html = _render_vocabulary_definitions(
        block_key,
        vocabulary_words,
        active_vocabulary_key,
    )

    return (
        f'<div class="reading-paragraph-block" id="{html.escape(block_key)}">'
        f'<p class="reading-paragraph">{paragraph_html}</p>'
        f"{definition_html}"
        "</div>"
    )


def _render_interactive_list_item(
    text: str,
    difficult_words: list[str],
    section_index: int,
    block_index: int,
    item_index: int,
    active_vocabulary_key: str,
    seen_words: set[str],
) -> str:
    """Render one list item with inline vocabulary links."""

    block_key = _build_block_key(section_index, block_index, item_index)
    vocabulary_words: list[str] = []
    item_html = _link_difficult_words(
        text,
        difficult_words,
        block_key,
        seen_words,
        vocabulary_words,
        active_vocabulary_key,
    )
    definition_html = _render_vocabulary_definitions(
        block_key,
        vocabulary_words,
        active_vocabulary_key,
    )

    return f'<li id="{html.escape(block_key)}">{item_html}{definition_html}</li>'


def _link_difficult_words(
    text: str,
    difficult_words: list[str],
    block_key: str,
    seen_words: set[str],
    vocabulary_words: list[str],
    active_vocabulary_key: str,
) -> str:
    """Return escaped text with only first-use difficult words as links."""

    if not difficult_words:
        return html.escape(text)

    difficult_word_lookup = {word.lower() for word in difficult_words}

    def replace_word(match: re.Match[str]) -> str:
        word = match.group(0)
        normalized_word = word.lower()

        if normalized_word not in difficult_word_lookup:
            return html.escape(word)

        if normalized_word in seen_words:
            return html.escape(word)

        seen_words.add(normalized_word)
        vocabulary_words.append(normalized_word)
        target_id = _build_vocabulary_target_id(block_key, normalized_word)
        query_value = (
            _VOCABULARY_CLEAR_VALUE
            if active_vocabulary_key == target_id
            else target_id
        )
        return (
            '<a class="reading-vocabulary-link" '
            f'href="?{_VOCABULARY_QUERY_PARAM}={quote(query_value, safe="")}" '
            f'aria-describedby="{html.escape(target_id)}">'
            f"{html.escape(word)}</a>"
        )

    return _WORD_PATTERN.sub(replace_word, text)


def _render_vocabulary_definitions(
    block_key: str,
    vocabulary_words: list[str],
    active_vocabulary_key: str,
) -> str:
    """Render locally revealable vocabulary definitions for the current block."""

    if not vocabulary_words:
        return ""

    definitions: list[str] = []
    for word in vocabulary_words:
        target_id = _build_vocabulary_target_id(block_key, word)
        active_class = (
            " reading-vocabulary-definition-active"
            if active_vocabulary_key == target_id
            else ""
        )
        definitions.append(
            dedent(
                f"""
                <div id="{html.escape(target_id)}" class="reading-vocabulary-definition{active_class}" role="note">
                    <span class="reading-vocabulary-label">Meaning:</span>
                    <strong>{html.escape(word.capitalize())}</strong>
                    <span>{html.escape(_get_definition(word))}</span>
                </div>
                """
            ).strip()
        )

    return "\n".join(definitions)


def _get_active_vocabulary_key() -> str:
    """Store the selected vocabulary target and return session state."""

    selected_key = _get_requested_vocabulary_key()
    if selected_key:
        st.session_state[_VOCABULARY_SESSION_KEY] = (
            "" if selected_key == _VOCABULARY_CLEAR_VALUE else selected_key
        )

    return str(st.session_state.get(_VOCABULARY_SESSION_KEY, ""))


def _get_requested_vocabulary_key() -> str:
    """Read a vocabulary selection from Streamlit query parameters."""

    try:
        value = st.query_params.get(_VOCABULARY_QUERY_PARAM, "")
    except AttributeError:
        value = st.experimental_get_query_params().get(
            _VOCABULARY_QUERY_PARAM,
            [""],
        )

    if isinstance(value, list):
        return str(value[0]) if value else ""

    return str(value)


def _build_block_key(
    section_index: int,
    block_index: int,
    item_index: int | None = None,
) -> str:
    """Build a stable key for paragraph-level vocabulary state."""

    if item_index is None:
        return f"section-{section_index}-block-{block_index}"

    return f"section-{section_index}-block-{block_index}-item-{item_index}"


def _build_vocabulary_target_id(block_key: str, word: str) -> str:
    """Build a local HTML target id for a vocabulary definition."""

    return f"{block_key}-vocab-{word}"


def _get_vocabulary_link_color(style: _ReadingStyle) -> str:
    """Return a readable accent color for inline vocabulary links."""

    if style.background_color == "#121826":
        return "#93C5FD"

    return "#1D4ED8"


def _group_blocks_into_sections(
    blocks: list[ReadingContentBlock],
) -> list[_ReadingSection]:
    """Group structured content blocks into heading-led reading sections."""

    sections: list[_ReadingSection] = []
    current_section = _ReadingSection()

    for block in blocks:
        if block.kind == "heading":
            if current_section.heading or current_section.blocks:
                sections.append(current_section)
            current_section = _ReadingSection(heading=block.text)
            continue

        current_section.blocks.append(block)

    if current_section.heading or current_section.blocks:
        sections.append(current_section)

    return sections


def _extract_key_takeaways(content: str) -> list[str]:
    """Return major points using deterministic sentence scoring."""

    sentences = [
        sentence.strip()
        for sentence in _SENTENCE_PATTERN.findall(content.replace("\n", " "))
        if len(sentence.strip().split()) >= 4
    ]
    scored_sentences = sorted(
        enumerate(sentences),
        key=lambda item: _score_takeaway_sentence(item[1]),
        reverse=True,
    )

    selected_indexes = sorted(
        index
        for index, sentence in scored_sentences[:READING_TAKEAWAY_LIMIT]
        if _score_takeaway_sentence(sentence) > 0
    )

    if not selected_indexes:
        selected_indexes = list(range(min(len(sentences), READING_TAKEAWAY_LIMIT)))

    return [_clean_takeaway(sentences[index]) for index in selected_indexes]


def _score_takeaway_sentence(sentence: str) -> int:
    """Score a sentence for takeaway usefulness."""

    lower_sentence = sentence.lower()
    score = 0

    for keyword in ("use", "used", "make", "need", "required", "process", "occurs"):
        if keyword in lower_sentence:
            score += 2

    if 6 <= len(sentence.split()) <= 22:
        score += 1

    for word in extract_difficult_words(sentence):
        if word in BUILT_IN_DICTIONARY:
            score += 1

    return score


def _clean_takeaway(sentence: str) -> str:
    """Normalize a takeaway sentence for display."""

    return sentence.strip().rstrip(".") + "."


def _render_placeholder_card(message: str) -> None:
    """Render a theme-aware placeholder card for inactive modes."""

    style = _get_reading_style()
    html_content = dedent(
        f"""
        <div class="mode-placeholder-card" aria-label="{html.escape(message)}">
        <p>{html.escape(message)}</p>
        </div>
        {_build_shared_card_styles(style)}
        <style>
        .mode-placeholder-card p {{
            margin: 0;
        }}
        </style>
        """
    ).strip()
    _render_html(html_content)


def _render_html(html_content: str) -> None:
    """Render raw HTML/CSS without exposing CSS rules as Markdown text."""

    if hasattr(st, "html"):
        st.html(html_content)
        return

    st.markdown(html_content, unsafe_allow_html=True)


def _get_reading_style() -> _ReadingStyle:
    """Resolve the current accessibility preferences into CSS values."""

    preferences = get_ui_preferences()
    theme = THEMES[preferences["theme"]]

    return _ReadingStyle(
        background_color=theme["background_color"],
        text_color=theme["text_color"],
        secondary_background=theme["secondary_background"],
        border_color=theme["border_color"],
        font_family=_resolve_font_family(preferences["font_family"]),
        font_size=FONT_SIZES[preferences["font_size"]],
        character_spacing=CHARACTER_SPACING[preferences["character_spacing"]],
    )


def _resolve_font_family(font_family: str) -> str:
    """Return a CSS-safe font-family declaration from configured options."""

    if font_family not in FONTS:
        font_family = FONTS[0]

    return f'"{html.escape(font_family, quote=True)}", sans-serif'


def _build_reading_styles(style: _ReadingStyle) -> str:
    """Build CSS for read mode using centralized configuration values."""

    vocabulary_color = _get_vocabulary_link_color(style)

    return dedent(
        f"""
        <style>
        .reading-experience {{
            display: grid;
            gap: {READING_SECTION_GAP};
            font-family: {style.font_family};
            font-size: {style.font_size}px;
            line-height: {READING_LINE_HEIGHT};
            letter-spacing: {style.character_spacing};
            color: {style.text_color};
        }}

        .reading-section-card {{
            background-color: {style.secondary_background};
            border: {READING_CARD_BORDER_WIDTH} solid {style.border_color};
            border-radius: {READING_CONTAINER_RADIUS};
            padding: {READING_CONTAINER_PADDING};
        }}

        .reading-heading {{
            color: {style.text_color};
            font-size: {READING_HEADING_SCALE};
            line-height: {READING_HEADING_LINE_HEIGHT};
            margin: 0 0 {READING_SECTION_GAP};
        }}

        .reading-paragraph {{
            color: {style.text_color};
            font-size: {style.font_size}px;
            max-width: {READING_CONTENT_MAX_WIDTH};
            margin: 0 0 {READING_SECTION_GAP};
        }}

        .reading-paragraph-block:last-child .reading-paragraph {{
            margin-bottom: 0;
        }}

        .reading-vocabulary-link {{
            color: {vocabulary_color};
            font-weight: 700;
            text-decoration-color: {vocabulary_color};
            text-decoration-line: underline;
            text-decoration-thickness: 0.12em;
            text-underline-offset: 0.18em;
        }}

        .reading-vocabulary-link:hover,
        .reading-vocabulary-link:focus {{
            color: {vocabulary_color};
            text-decoration-thickness: 0.18em;
        }}

        .reading-vocabulary-link:focus {{
            outline: {READING_CARD_BORDER_WIDTH} solid {vocabulary_color};
            outline-offset: 0.16rem;
        }}

        .reading-vocabulary-definition {{
            background-color: {style.background_color};
            border-left: 0.22rem solid {vocabulary_color};
            color: {style.text_color};
            display: none;
            font-size: {style.font_size}px;
            gap: 0.1rem;
            line-height: {READING_LINE_HEIGHT};
            margin: -0.35rem 0 {READING_SECTION_GAP};
            max-width: {READING_CONTENT_MAX_WIDTH};
            padding: {READING_COMPACT_GAP} 0 {READING_COMPACT_GAP} {READING_COMPACT_GAP};
            scroll-margin-top: {READING_SECTION_GAP};
        }}

        .reading-vocabulary-definition-active {{
            display: grid;
        }}

        .reading-vocabulary-definition strong,
        .reading-vocabulary-label {{
            font-weight: 700;
        }}

        .reading-bullet-list {{
            color: {style.text_color};
            font-size: {style.font_size}px;
            max-width: {READING_CONTENT_MAX_WIDTH};
            margin: 0 0 {READING_SECTION_GAP};
            padding-left: {READING_LIST_INDENT};
        }}

        .reading-bullet-list:last-child {{
            margin-bottom: 0;
        }}

        .reading-bullet-list li {{
            margin-bottom: {READING_COMPACT_GAP};
        }}
        </style>
        """
    ).strip()


def _build_shared_card_styles(style: _ReadingStyle) -> str:
    """Build shared CSS for secondary reading-experience cards."""

    return dedent(
        f"""
        <style>
        .takeaways-card,
        .mode-placeholder-card {{
            background-color: {style.secondary_background};
            border: {READING_CARD_BORDER_WIDTH} solid {style.border_color};
            border-radius: {READING_CONTAINER_RADIUS};
            color: {style.text_color};
            font-family: {style.font_family};
            font-size: {style.font_size}px;
            letter-spacing: {style.character_spacing};
            line-height: {READING_LINE_HEIGHT};
            margin-top: {READING_SECTION_GAP};
            padding: {READING_CONTAINER_PADDING};
        }}

        .takeaways-heading {{
            color: {style.text_color};
            font-size: {READING_SECONDARY_HEADING_SCALE};
            margin: 0 0 {READING_SECTION_GAP};
        }}
        </style>
        """
    ).strip()


__all__ = [
    "render_key_takeaways",
    "render_learning_mode_switcher",
    "render_listen_mode_placeholder",
    "render_read_mode",
    "render_reading_view",
    "render_visual_mode_placeholder",
]
