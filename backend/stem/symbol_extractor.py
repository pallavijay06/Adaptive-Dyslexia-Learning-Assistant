"""Symbol extraction for the STEM Symbol Explanation feature."""

from __future__ import annotations

import re


STEM_SYMBOL_PATTERN = re.compile(
    r"[\u0370-\u03ff\u2200-\u22ff\u00b0\u00b1\u00d7\u00f7]"
)


def extract_symbols(text: str) -> list[str]:
    """Extract STEM symbols from text while preserving first-seen order."""

    if not text or not text.strip():
        return []

    symbols: list[str] = []
    seen: set[str] = set()

    for match in STEM_SYMBOL_PATTERN.finditer(text):
        symbol = match.group(0)
        if symbol in seen:
            continue

        seen.add(symbol)
        symbols.append(symbol)

    return symbols
