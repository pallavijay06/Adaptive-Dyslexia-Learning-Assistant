"""Tests for the STEM Symbol Explanation feature."""

import pytest

from backend.stem import symbol_assistant
from backend.stem.symbol_assistant import explain_symbol, get_symbol_explanations
from backend.stem.symbol_extractor import extract_symbols
from backend.stem.symbol_library import SYMBOL_LIBRARY, get_symbol_explanation


def test_symbol_library_contains_expanded_common_symbols():
    assert 40 <= len(SYMBOL_LIBRARY) <= 60
    assert "\u03a3" in SYMBOL_LIBRARY
    assert "\u0394" in SYMBOL_LIBRARY
    assert "\u03bb" in SYMBOL_LIBRARY
    assert "\u03a9" in SYMBOL_LIBRARY


def test_extract_symbols_preserves_order_and_removes_duplicates():
    text = "\u03a3 + \u0394 + \u03a3 + \u03c0 + \u03bb"

    assert extract_symbols(text) == ["\u03a3", "\u0394", "\u03c0", "\u03bb"]


def test_extract_symbols_empty_input_returns_empty_list():
    assert extract_symbols("") == []
    assert extract_symbols("   ") == []


def test_library_explanation_loads_correctly():
    explanation = get_symbol_explanation("\u03a3")

    assert explanation == {
        "symbol": "\u03a3",
        "meaning": "Summation",
        "simple_explanation": "Used to add many values together.",
        "similar_symbols": ["E"],
        "difference": "\u03a3 means add values, unlike the letter E.",
        "example": "\u03a3(1, 2, 3) = 6",
    }


def test_explain_symbol_uses_library_response():
    assert explain_symbol("\u0394") == {
        "symbol": "\u0394",
        "meaning": "Change",
        "simple_explanation": "Shows how much something changes.",
        "example": "\u0394x means change in position.",
    }


def test_unknown_symbol_returns_safe_fallback():
    assert explain_symbol("\u2234") == {
        "symbol": "\u2234",
        "meaning": "Unknown Symbol",
        "simple_explanation": "This symbol is not currently available in the STEM library.",
        "example": "No example available.",
    }


def test_unknown_symbol_does_not_call_ai_fallback(monkeypatch):
    def fail_if_called(symbol):
        raise AssertionError("AI fallback must not run in this version.")

    monkeypatch.setattr(symbol_assistant, "_get_ai_symbol_explanation", fail_if_called)

    assert explain_symbol("\u2234")["meaning"] == "Unknown Symbol"


def test_symbol_explanations_output_structure():
    explanations = get_symbol_explanations("\u03a3 \u2234")

    assert len(explanations) == 2
    for explanation in explanations:
        assert set(explanation.keys()) == {
            "symbol",
            "meaning",
            "simple_explanation",
            "example",
        }
    assert explanations[1]["meaning"] == "Unknown Symbol"


def test_future_ai_placeholder_is_not_implemented():
    with pytest.raises(NotImplementedError):
        symbol_assistant._get_ai_symbol_explanation("\u2234")
