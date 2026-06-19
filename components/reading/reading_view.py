"""Dyslexia-friendly reading experience components for Streamlit."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from textwrap import dedent

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
    seen_word_set: set[str] = set()
    section_html = "\n".join(
        (
            _render_interactive_section(
                section,
                difficult_words,
                section_index,
                seen_word_set,
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
    seen_word_set: set[str],
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
            seen_word_set,
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
    seen_word_set: set[str],
) -> str:
    """Render a paragraph or list while preserving natural text flow."""

    group_name = f"reading_vocab_{section_index}_{block_index}"

    if block.kind == "bullet_list":
        item_html_blocks: list[str] = []
        hidden_html = ""
        definition_html = ""

        for item in block.items:
            item_html, item_hidden, item_definitions = _link_difficult_words(
                item,
                difficult_words,
                seen_word_set,
                group_name,
            )
            item_html_blocks.append(f'<li>{item_html}</li>')
            hidden_html += item_hidden
            definition_html += item_definitions

        return (
            f'<div class="reading-paragraph-block">'
            f'<ul class="reading-bullet-list">{"\n".join(item_html_blocks)}</ul>'
            f'{hidden_html}'
            "</div>"
        )

    paragraph_html, hidden_inputs_html, definition_html = _link_difficult_words(
        block.text,
        difficult_words,
        seen_word_set,
        group_name,
    )

    return (
        f'<div class="reading-paragraph-block">'
        f'<p class="reading-paragraph">{paragraph_html}</p>'
        f'{hidden_inputs_html}'
        "</div>"
    )


def _render_interactive_list_item(
    text: str,
    difficult_words: list[str],
    seen_word_set: set[str],
    group_name: str,
) -> tuple[str, str]:
    """Render one list item with inline vocabulary highlights."""

    item_html, _, _ = _link_difficult_words(
        text,
        difficult_words,
        seen_word_set,
        group_name,
    )

    return item_html, item_html


def _link_difficult_words(
    text: str,
    difficult_words: list[str],
    seen_word_set: set[str],
    group_name: str,
) -> tuple[str, str, str]:
    """Return inline HTML, hidden inputs, and definitions for first-use difficult words."""

    if not difficult_words:
        return html.escape(text), "", ""

    difficult_word_lookup = {word.lower() for word in difficult_words}
    hidden_blocks: list[str] = []
    word_index = 0

    def replace_word(match: re.Match[str]) -> str:
        nonlocal word_index

        word = match.group(0)
        normalized_word = word.lower()

        if normalized_word not in difficult_word_lookup:
            return html.escape(word)

        if normalized_word in seen_word_set:
            return html.escape(word)

        seen_word_set.add(normalized_word)
        input_id = f"{group_name}_{word_index}"
        word_index += 1

        hidden_blocks.append(
            dedent(
                f"""
                <input type="radio" name="{group_name}" id="{input_id}" class="reading-vocab-input">
                <div class="reading-vocabulary-definition reading-vocab-{input_id}">
                    <span class="reading-vocabulary-label">Meaning:</span>
                    {html.escape(_get_definition(normalized_word))}
                </div>
                """
            ).strip()
        )

        return (
            f'<span class="reading-vocabulary-word">'
            f'<label for="{input_id}">{html.escape(word)}</label>'
            '</span>'
        )

    paragraph_html = _WORD_PATTERN.sub(replace_word, text)
    return paragraph_html, "".join(hidden_blocks), ""


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
            background-color: {style.background_color};
            padding: {READING_CONTAINER_PADDING};
            border-radius: {READING_CONTAINER_RADIUS};
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

        .reading-vocabulary-word {{
            color: {vocabulary_color};
            font-weight: 700;
            text-decoration-color: {vocabulary_color};
            text-decoration-line: underline;
            text-decoration-thickness: 0.12em;
            text-underline-offset: 0.18em;
            cursor: pointer;
            display: inline;
        }}

        .reading-vocabulary-word:hover,
        .reading-vocabulary-word:focus {{
            color: {vocabulary_color};
            text-decoration-thickness: 0.18em;
        }}

        .reading-vocab-input {{
            display: none;
        }}

        .reading-vocab-input:checked + .reading-vocabulary-definition {{
            display: block;
        }}

        .reading-vocabulary-definition {{
            display: none;
            background-color: {style.background_color};
            border: 1px solid {style.border_color};
            border-radius: 0.5rem;
            color: {style.text_color};
            margin-top: 0.4rem;
            padding: 0.45rem 0.65rem;
            max-width: {READING_CONTENT_MAX_WIDTH};
            white-space: normal;
        }}

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
