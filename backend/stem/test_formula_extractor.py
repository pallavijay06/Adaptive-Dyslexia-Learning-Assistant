"""Tests for the dedicated Formula Assistant extraction pipeline."""

from backend.stem.formula_extractor import extract_formulas


def test_extract_formulas_detects_simple_equations():
    text = "F = ma\n\nV = IR"

    assert extract_formulas(text) == ["F = ma", "V = IR"]


def test_extract_formulas_removes_duplicates():
    text = "F = ma\nF = ma\nf = ma"

    assert extract_formulas(text) == ["F = ma"]


def test_extract_formulas_empty_input_returns_empty_list():
    assert extract_formulas("") == []
    assert extract_formulas("   ") == []


def test_extract_formulas_detects_multiple_operator_styles():
    text = "x = y + 2\nA = b * h\nc^2 = a^2 + b^2\nr = \u221aA"

    assert extract_formulas(text) == [
        "x = y + 2",
        "A = b * h",
        "c^2 = a^2 + b^2",
        "r = \u221aA",
    ]


def test_extract_formulas_ignores_ordinary_sentences():
    text = "This sentence has words and no formula.\nThe circuit diagram is below."

    assert extract_formulas(text) == []
