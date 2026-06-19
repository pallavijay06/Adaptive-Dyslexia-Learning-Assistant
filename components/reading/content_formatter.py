"""Structured formatting helpers for dyslexia-friendly reading content."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from components.ui_constants import (
    READING_LONG_PARAGRAPH_CHARACTER_LIMIT,
    READING_MAX_SENTENCES_PER_PARAGRAPH,
)

ReadingBlockKind = Literal["heading", "paragraph", "bullet_list"]

_BULLET_PATTERN = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+)$")
_SENTENCE_END_PATTERN = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class ReadingContentBlock:
    """A structured content block for the reading experience."""

    kind: ReadingBlockKind
    text: str = ""
    items: list[str] = field(default_factory=list)


def format_content_for_reading(content: str) -> list[ReadingContentBlock]:
    """Format plain text into structured reading blocks.

    The formatter detects headings, preserves bullet lists, and splits long
    paragraphs into smaller chunks for more comfortable reading. It performs no
    AI simplification and does not call external services.

    Args:
        content: Plain text educational content.

    Returns:
        A list of structured content blocks.
    """

    normalized_content = content.strip()
    if not normalized_content:
        return [ReadingContentBlock(kind="paragraph", text="No reading content available.")]

    blocks: list[ReadingContentBlock] = []
    paragraph_lines: list[str] = []
    bullet_items: list[str] = []

    for line_index, raw_line in enumerate(normalized_content.splitlines()):
        line = raw_line.strip()

        if not line:
            _flush_bullets(blocks, bullet_items)
            _flush_paragraph(blocks, paragraph_lines)
            continue

        bullet_match = _BULLET_PATTERN.match(line)
        if bullet_match:
            _flush_paragraph(blocks, paragraph_lines)
            bullet_items.append(bullet_match.group(1).strip())
            continue

        _flush_bullets(blocks, bullet_items)

        if _is_heading(line, line_index, bool(blocks), bool(paragraph_lines)):
            _flush_paragraph(blocks, paragraph_lines)
            blocks.append(ReadingContentBlock(kind="heading", text=_clean_heading(line)))
            continue

        paragraph_lines.append(line)

    _flush_bullets(blocks, bullet_items)
    _flush_paragraph(blocks, paragraph_lines)

    return blocks


def _is_heading(
    line: str,
    line_index: int,
    has_blocks: bool,
    has_pending_paragraph: bool,
) -> bool:
    """Return whether a line should be treated as a heading."""

    if line.startswith("#"):
        return True

    if has_pending_paragraph:
        return False

    if line.endswith((".", "!", "?", ";", ",")):
        return False

    if len(line) > 90:
        return False

    return line_index == 0 or has_blocks or line.istitle()


def _clean_heading(line: str) -> str:
    """Remove lightweight heading markers from a heading line."""

    return line.lstrip("#").strip()


def _flush_paragraph(
    blocks: list[ReadingContentBlock],
    paragraph_lines: list[str],
) -> None:
    """Append pending paragraph chunks to ``blocks``."""

    if not paragraph_lines:
        return

    paragraph = " ".join(paragraph_lines)
    for chunk in _chunk_paragraph(paragraph):
        blocks.append(ReadingContentBlock(kind="paragraph", text=chunk))

    paragraph_lines.clear()


def _flush_bullets(
    blocks: list[ReadingContentBlock],
    bullet_items: list[str],
) -> None:
    """Append pending bullet items as a single structured list."""

    if not bullet_items:
        return

    blocks.append(ReadingContentBlock(kind="bullet_list", items=list(bullet_items)))
    bullet_items.clear()


def _chunk_paragraph(paragraph: str) -> list[str]:
    """Split a long paragraph into smaller sentence-aware chunks."""

    if len(paragraph) <= READING_LONG_PARAGRAPH_CHARACTER_LIMIT:
        return [paragraph]

    sentences = [
        sentence.strip()
        for sentence in _SENTENCE_END_PATTERN.split(paragraph)
        if sentence.strip()
    ]
    if len(sentences) <= 1:
        return _chunk_by_words(paragraph)

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_length = 0

    for sentence in sentences:
        next_length = current_length + len(sentence)
        should_flush = (
            current_sentences
            and (
                len(current_sentences) >= READING_MAX_SENTENCES_PER_PARAGRAPH
                or next_length > READING_LONG_PARAGRAPH_CHARACTER_LIMIT
            )
        )

        if should_flush:
            chunks.append(" ".join(current_sentences))
            current_sentences = []
            current_length = 0

        current_sentences.append(sentence)
        current_length += len(sentence)

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return chunks


def _chunk_by_words(paragraph: str) -> list[str]:
    """Split text without sentence boundaries into readable word chunks."""

    chunks: list[str] = []
    words = paragraph.split()
    current_words: list[str] = []
    current_length = 0

    for word in words:
        next_length = current_length + len(word) + 1
        if current_words and next_length > READING_LONG_PARAGRAPH_CHARACTER_LIMIT:
            chunks.append(" ".join(current_words))
            current_words = []
            current_length = 0

        current_words.append(word)
        current_length += len(word) + 1

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


__all__ = ["ReadingContentBlock", "ReadingBlockKind", "format_content_for_reading"]
