"""Local text chunking for document retrieval."""

from __future__ import annotations

import re
from typing import Any


DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 200


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    """Split extracted document text into overlapping chunks."""
    cleaned_text = _normalize_whitespace(text)
    if not cleaned_text:
        return []

    chunks: list[dict[str, Any]] = []
    start = 0
    total_length = len(cleaned_text)
    chunk_id = 0

    while start < total_length:
        end = min(start + chunk_size, total_length)
        chunk_text = cleaned_text[start:end]

        if end < total_length:
            last_space = chunk_text.rfind(" ")
            if last_space > 0:
                chunk_text = chunk_text[:last_space]
                end = start + last_space

        chunk_text = chunk_text.strip()
        if chunk_text:
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "start_index": start,
                    "end_index": end,
                }
            )
            chunk_id += 1

        if end >= total_length:
            break

        start = max(0, end - overlap)

    return chunks


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
