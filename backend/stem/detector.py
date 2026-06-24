"""Lightweight STEM content detector for Prototype 3 Phase 1.

The functions in this module analyze extracted document text and return simple
counts for formulas, STEM symbols, and diagram references. This is intentionally
placeholder logic: it gives the future UI and service layer a stable contract
without implementing Formula Assistant, Symbol Explanation, Diagram
Explanation, or Step-by-Step Solutions.
"""

from backend.stem.formula_extractor import extract_formulas
from backend.stem.models import STEMDetectionResult
from backend.stem.symbol_extractor import extract_symbols

import re


MATH_PLACEHOLDER_OPERATOR_PATTERN = re.compile(r"[=+*/]")
MATH_PLACEHOLDER_UNICODE_OPERATOR_PATTERN = re.compile(r"[×÷−]")
MATH_FUNCTION_PATTERN = re.compile(r"\b(?:sqrt|sin|cos|tan|log|ln|exp|abs|pow|root)\s*\(", re.IGNORECASE)
MATH_EXPONENT_PATTERN = re.compile(r"\b\w+\^[\w\d]+\b|[⁰¹²³⁴⁵⁶⁷⁸⁹]")


def _normalize_text(text: str | None) -> str:
    """Return safe text for placeholder detection."""

    return text or ""


def detect_formulas(text: str | None) -> int:
    """Detect STEM formula-like content without extracting exact formulas."""

    normalized_text = _normalize_text(text)
    if not normalized_text.strip():
        return 0

    actual_formulas = len(extract_formulas(normalized_text))
    placeholder_tokens = _count_placeholder_formula_tokens(normalized_text)

    return max(actual_formulas, placeholder_tokens)


def _count_placeholder_formula_tokens(text: str) -> int:
    """Count lightweight STEM math tokens and function patterns in prose."""

    operator_matches = len(MATH_PLACEHOLDER_OPERATOR_PATTERN.findall(text))
    unicode_operator_matches = len(MATH_PLACEHOLDER_UNICODE_OPERATOR_PATTERN.findall(text))
    function_matches = len(MATH_FUNCTION_PATTERN.findall(text))
    exponent_matches = len(MATH_EXPONENT_PATTERN.findall(text))

    return operator_matches + unicode_operator_matches + function_matches + exponent_matches


def detect_symbols(text: str | None) -> int:
    """Detect STEM symbols using the shared symbol extraction pipeline."""

    return len(extract_symbols(_normalize_text(text)))


def detect_diagrams(text: str | None, diagram_images: list[str] | None = None) -> int:
    """Detect diagrams based only on extracted image paths."""

    if not diagram_images:
        return 0
    return len([image for image in diagram_images if image])


def detect_stem_content(text: str | None, diagram_images: list[str] | None = None) -> STEMDetectionResult:
    """Analyze extracted document text and return STEM detection statistics."""

    formula_count = detect_formulas(text)
    symbol_count = detect_symbols(text)
    diagram_count = detect_diagrams(text, diagram_images)

    return STEMDetectionResult(
        has_formula=formula_count > 0,
        has_symbols=symbol_count > 0,
        has_diagrams=diagram_count > 0,
        formula_count=formula_count,
        symbol_count=symbol_count,
        diagram_count=diagram_count,
    )
