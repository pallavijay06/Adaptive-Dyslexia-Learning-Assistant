"""Tests for the isolated Phase 1 STEM detection framework."""

from backend.stem.detector import (
    detect_diagrams,
    detect_formulas,
    detect_stem_content,
    detect_symbols,
)
from backend.stem.models import STEMDetectionResult
from backend.stem.stem_service import (
    analyze_document_for_stem,
    get_available_stem_features,
)


def test_detect_formulas_counts_placeholder_tokens():
    text = "Area = length * width. Use sqrt(16) / 2 and x^2."

    assert detect_formulas(text) == 5


def test_detect_symbols_counts_supported_symbols():
    text = "Use ∑ for summation, Δ for change, and π with θ."

    assert detect_symbols(text) == 4


def test_detect_diagrams_counts_keywords_case_insensitively():
    text = "Figure 1 shows a circuit diagram and a Graph."

    assert detect_diagrams(text) == 4


def test_detect_stem_content_returns_detection_result():
    text = "Figure: ∑ values where x = sqrt(9)."

    result = detect_stem_content(text)

    assert result == STEMDetectionResult(
        has_formula=True,
        has_symbols=True,
        has_diagrams=True,
        formula_count=2,
        symbol_count=1,
        diagram_count=1,
    )


def test_analyze_document_for_stem_uses_detector_contract():
    result = analyze_document_for_stem("Plain reading passage without markers.")

    assert result == STEMDetectionResult(
        has_formula=False,
        has_symbols=False,
        has_diagrams=False,
        formula_count=0,
        symbol_count=0,
        diagram_count=0,
    )


def test_get_available_stem_features_for_detected_content():
    result = STEMDetectionResult(
        has_formula=True,
        has_symbols=True,
        has_diagrams=True,
        formula_count=2,
        symbol_count=3,
        diagram_count=1,
    )

    assert get_available_stem_features(result) == [
        "Formula Assistant",
        "Step-by-Step Solutions",
        "Symbol Explanation",
        "Diagram Explanation",
    ]


def test_get_available_stem_features_for_empty_result():
    result = STEMDetectionResult(
        has_formula=False,
        has_symbols=False,
        has_diagrams=False,
        formula_count=0,
        symbol_count=0,
        diagram_count=0,
    )

    assert get_available_stem_features(result) == []
