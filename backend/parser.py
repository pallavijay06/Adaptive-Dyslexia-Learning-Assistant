"""Parser facade for the Streamlit app.

This file keeps the requested backend/parser.py shape while delegating to the
existing document processing service.
"""

from __future__ import annotations

from pathlib import Path

from services.document_context import (
    DocumentRecord,
    extract_text_from_file,
    process_uploaded_bytes,
)


def process_uploaded_file(filename: str, file_bytes: bytes) -> DocumentRecord:
    """Save and parse an uploaded file using the existing document pipeline."""
    return process_uploaded_bytes(filename, file_bytes)


def parse_file(path: str | Path) -> str:
    """Extract text from a file path using the existing parser dispatch."""
    return extract_text_from_file(path)
