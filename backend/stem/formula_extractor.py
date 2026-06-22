"""Formula extraction pipeline for STEM Formula Assistant.

This module is separate from the Phase 1 STEM detector. The detector counts
formula indicators for broad availability checks, while this extractor returns
clean formula strings that can be explained by the Formula Assistant.
"""

from __future__ import annotations

import re


FORMULA_OPERATOR_PATTERN = re.compile(r"(=|\+|-|\*|/|\^|\u221a)")
FORMULA_CANDIDATE_PATTERN = re.compile(
    r"(?m)^\s*(?:[-*]\s*)?"
    r"([A-Za-z0-9_\u0370-\u03ff\u221a][A-Za-z0-9_\u0370-\u03ff \t().,\u221a+\-*/^=]{0,120}"
    r"(?:=|\+|-|\*|/|\^|\u221a)"
    r"[A-Za-z0-9_\u0370-\u03ff \t().,\u221a+\-*/^=]{0,120})\s*$"
)


def extract_formulas(text: str) -> list[str]:
    """Extract clean formula candidates from document text.

    The extraction is intentionally conservative and line-oriented to avoid
    treating ordinary prose as formulas. It detects candidates containing common
    formula operators, removes duplicates, and preserves the original order.
    """

    if not text or not text.strip():
        return []

    formulas: list[str] = []
    seen: set[str] = set()

    for match in FORMULA_CANDIDATE_PATTERN.finditer(text):
        formula = _clean_formula(match.group(1))
        if not _is_formula_candidate(formula):
            continue

        formula_key = formula.casefold()
        if formula_key in seen:
            continue

        seen.add(formula_key)
        formulas.append(formula)

    return formulas


def _clean_formula(formula: str) -> str:
    """Normalize whitespace and remove surrounding prose punctuation."""

    cleaned = re.sub(r"\s+", " ", formula).strip()
    return cleaned.strip(" .,:;")


def _is_formula_candidate(formula: str) -> bool:
    """Return whether a cleaned string looks like a formula."""

    if not formula or not FORMULA_OPERATOR_PATTERN.search(formula):
        return False

    if len(formula) > 120:
        return False

    if re.search(r"[.!?]\s+[A-Z]", formula):
        return False

    tokens = formula.split()
    if len(tokens) > 12:
        return False

    return True
