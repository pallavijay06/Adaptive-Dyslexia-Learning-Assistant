"""Symbol Explanation assistant for Prototype 3 STEM Support.

Current architecture:

Detected symbol -> curated library lookup -> AI fallback for unknown symbols.

The public API uses the library first and only calls the LLM when a symbol is
not available offline.
"""

from __future__ import annotations

import json
from typing import Any

from backend.llm import chat_with_gemini
from backend.stem.symbol_extractor import extract_symbols
from backend.stem.symbol_library import get_symbol_explanation


UNKNOWN_SYMBOL_RESPONSE = {
    "meaning": "Symbol explanation unavailable.",
    "simple_explanation": "No example available for this symbol.",
    "example": "No example available.",
}

SYMBOL_NORMALIZATION = {
    "∑": "Σ",
    "∴": "∴",
    "∞": "∞",
}

SYMBOL_EXPLANATION_CACHE: dict[str, dict[str, Any]] = {}


def explain_symbol(symbol: str) -> dict[str, Any]:
    """Return a concise library explanation or AI fallback response."""

    cleaned_symbol = (symbol or "").strip()
    if not cleaned_symbol:
        return _empty_symbol_response()

    normalized_symbol = _normalize_symbol(cleaned_symbol)
    cached_response = SYMBOL_EXPLANATION_CACHE.get(normalized_symbol)
    if cached_response is not None:
        return cached_response

    library_explanation = get_symbol_explanation(normalized_symbol)
    if library_explanation is not None:
        response = _simplify_explanation(library_explanation)
        SYMBOL_EXPLANATION_CACHE[normalized_symbol] = response
        return response

    explanation = _get_ai_symbol_explanation(normalized_symbol)
    SYMBOL_EXPLANATION_CACHE[normalized_symbol] = explanation
    return explanation


def _normalize_symbol(symbol: str) -> str:
    """Normalize extracted symbols before library lookup."""

    return SYMBOL_NORMALIZATION.get(symbol, symbol)


def _get_ai_symbol_explanation(symbol: str) -> dict[str, Any]:
    """Use AI to explain unknown STEM symbols while keeping responses short."""
    try:
        # Symbol explanations are short; ensure chat is constrained by router limits.
        response = chat_with_gemini(_build_symbol_prompt(symbol))
        return _parse_symbol_response(response, symbol)
    except Exception:
        return _unknown_symbol_response(symbol)


def _build_symbol_prompt(symbol: str) -> str:
    return (
        "You are a dyslexia-friendly STEM symbol helper.\n"
        "Return JSON only with these keys exactly: symbol, meaning, simple_explanation, example.\n"
        "Do not use markdown, bullet lists, or extra text outside the JSON.\n"
        "Keep each answer very short.\n"
        "Meaning must be one short sentence.\n"
        "simple_explanation must be one short phrase.\n"
        "example must be one short sentence.\n"
        f"Symbol to explain: {symbol}\n"
    )


def _parse_symbol_response(response: str, symbol: str) -> dict[str, Any]:
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        return _unknown_symbol_response(symbol)

    if not isinstance(parsed, dict):
        return _unknown_symbol_response(symbol)

    required_keys = {"symbol", "meaning", "simple_explanation", "example"}
    if set(parsed.keys()) != required_keys:
        return _unknown_symbol_response(symbol)

    if not all(isinstance(parsed.get(key), str) for key in required_keys):
        return _unknown_symbol_response(symbol)

    return {
        "symbol": str(parsed["symbol"]).strip() or symbol,
        "meaning": str(parsed["meaning"]).strip(),
        "simple_explanation": str(parsed["simple_explanation"]).strip(),
        "example": str(parsed["example"]).strip(),
    }


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
