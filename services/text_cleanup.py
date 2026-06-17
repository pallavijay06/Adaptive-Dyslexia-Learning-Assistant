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


def remove_markdown_and_html(text: str) -> str:
    """Remove markdown and HTML formatting artifacts from AI-generated text."""
    if not text:
        return ""

    cleaned = text
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"(?m)^\s*>{1,}\s?", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*#{1,6}\s*", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*([-*+]\s+|\d+\.\s+)", "", cleaned)
    cleaned = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).replace('```', ''), cleaned)
    cleaned = re.sub(r"`{1,3}([^`]*)`{1,3}", r"\1", cleaned)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)
    cleaned = re.sub(r"_(.*?)_", r"\1", cleaned)
    cleaned = re.sub(r"~~(.*?)~~", r"\1", cleaned)
    cleaned = re.sub(r"\*{1,3}", "", cleaned)
    cleaned = re.sub(r"_{1,3}", "", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"(?m)^[ \t]+|[ \t]+$", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
