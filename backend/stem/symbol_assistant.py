"""Symbol Explanation assistant for Prototype 3 STEM Support.

Current architecture:

Detected symbol -> curated library lookup -> safe fallback for unknown symbols.

The public API remains ready for a future AI fallback, but this version does
not call OpenRouter, Gemini, Ollama, or any other AI provider.
"""

from __future__ import annotations

from typing import Any

from backend.stem.symbol_extractor import extract_symbols
from backend.stem.symbol_library import get_symbol_explanation


UNKNOWN_SYMBOL_RESPONSE = {
    "meaning": "Unknown Symbol",
    "simple_explanation": "This symbol is not currently available in the STEM library.",
    "example": "No example available.",
}


def explain_symbol(symbol: str) -> dict[str, Any]:
    """Return a concise library explanation or safe fallback response.
    
    Returns only the simplified fields: symbol, meaning, simple_explanation, example.
    Filters out similar_symbols and difference for simplified learning experience.
    """

    cleaned_symbol = (symbol or "").strip()
    if not cleaned_symbol:
        return _empty_symbol_response()

    library_explanation = get_symbol_explanation(cleaned_symbol)
    if library_explanation is not None:
        # Filter to keep only the simplified fields
        return _simplify_explanation(library_explanation)

    return _unknown_symbol_response(cleaned_symbol)


def get_symbol_explanations(text: str) -> list[dict[str, Any]]:
    """Extract symbols from text and return explanations for each one."""

    return [explain_symbol(symbol) for symbol in extract_symbols(text)]


def _unknown_symbol_response(symbol: str) -> dict[str, Any]:
    """Return the safe offline fallback for symbols missing from the library."""

    return {
        "symbol": symbol,
        "meaning": UNKNOWN_SYMBOL_RESPONSE["meaning"],
        "simple_explanation": UNKNOWN_SYMBOL_RESPONSE["simple_explanation"],
        "example": UNKNOWN_SYMBOL_RESPONSE["example"],
    }


def _simplify_explanation(explanation: dict[str, Any]) -> dict[str, Any]:
    """Filter library explanation to include only simplified fields.
    
    Removes similar_symbols and difference to reduce cognitive load for
    dyslexic learners. Keeps internal data intact for future features.
    """
    return {
        "symbol": explanation.get("symbol", ""),
        "meaning": explanation.get("meaning", ""),
        "simple_explanation": explanation.get("simple_explanation", ""),
        "example": explanation.get("example", ""),
    }


def _empty_symbol_response() -> dict[str, Any]:
    """Return a safe empty response for blank symbol input."""

    return {
        "symbol": "",
        "meaning": "",
        "simple_explanation": "",
        "example": "",
    }


def _get_ai_symbol_explanation(symbol: str) -> dict[str, Any]:
    """Placeholder interface for a future AI fallback.

    This function is intentionally not called in the current version. A future
    implementation can use this helper when a symbol is missing from the
    library without changing the public ``explain_symbol`` API.
    """

    raise NotImplementedError(
        "AI symbol explanation is reserved for a future version."
    )
