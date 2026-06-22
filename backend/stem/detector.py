"""Lightweight STEM content detector for Prototype 3 Phase 1.

The functions in this module analyze extracted document text and return simple
counts for formulas, STEM symbols, and diagram references. This is intentionally
placeholder logic: it gives the future UI and service layer a stable contract
without implementing Formula Assistant, Symbol Explanation, Diagram
Explanation, or Step-by-Step Solutions.
"""

from backend.stem.constants import DIAGRAM_KEYWORDS, FORMULA_TOKENS, STEM_SYMBOLS
from backend.stem.models import STEMDetectionResult


def _normalize_text(text: str | None) -> str:
    """Return safe text for placeholder detection."""

    return text or ""


def detect_formulas(text: str | None) -> int:
    """Count placeholder formula tokens in extracted document text.

    Future Formula Assistant and Step-by-Step Solutions logic can replace this
    token counter with a math-aware parser while preserving the public detector
    contract.
    """

    content = _normalize_text(text)
    searchable_content = content.lower()
    return sum(searchable_content.count(token.lower()) for token in FORMULA_TOKENS)


def detect_symbols(text: str | None) -> int:
    """Count placeholder STEM symbols in extracted document text.

    Future Symbol Explanation logic can connect after this stage to explain
    detected symbols in context.
    """

    content = _normalize_text(text)
    return sum(content.count(symbol) for symbol in STEM_SYMBOLS)


def detect_diagrams(text: str | None) -> int:
    """Count diagram-related keywords in extracted document text.

    Future Diagram Explanation logic can connect after this stage to interpret
    referenced or extracted visual content.
    """

    searchable_content = _normalize_text(text).lower()
    return sum(searchable_content.count(keyword) for keyword in DIAGRAM_KEYWORDS)


def detect_stem_content(text: str | None) -> STEMDetectionResult:
    """Analyze extracted document text and return STEM detection statistics."""

    formula_count = detect_formulas(text)
    symbol_count = detect_symbols(text)
    diagram_count = detect_diagrams(text)

    return STEMDetectionResult(
        has_formula=formula_count > 0,
        has_symbols=symbol_count > 0,
        has_diagrams=diagram_count > 0,
        formula_count=formula_count,
        symbol_count=symbol_count,
        diagram_count=diagram_count,
    )
