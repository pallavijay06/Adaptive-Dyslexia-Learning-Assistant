"""Shared text cleanup helpers for AI-generated responses."""

from __future__ import annotations

import re


ANSI_ESCAPE_PATTERN = re.compile(
    r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
)

ORPHANED_TERMINAL_CONTROL_PATTERN = re.compile(
    r"\[[0-9;?]*[A-Za-z]"
)


def remove_ansi_escape_codes(text: str) -> str:
    """Remove ANSI escape sequences and orphaned terminal control fragments."""
    if not text:
        return ""

    cleaned = ANSI_ESCAPE_PATTERN.sub("", text)
    cleaned = ORPHANED_TERMINAL_CONTROL_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    return cleaned.strip()
