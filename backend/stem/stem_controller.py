"""Controller layer for coordinating isolated STEM support processing.

This module provides a single UI-agnostic entry point for turning extracted
document text into detection results and available placeholder features.
"""

from __future__ import annotations

from typing import Any

from backend.stem.stem_service import (
    analyze_document_for_stem,
    get_available_stem_features,
)
from backend.stem.formula_extractor import extract_formulas
from backend.stem.symbol_extractor import extract_symbols


def process_stem_support(text: str, diagram_images: list[str] | None = None) -> dict[str, Any]:
    """Process extracted document text for STEM support.

    The controller performs no rendering and contains no Streamlit code. It
    coordinates existing STEM service functions and returns shared formula,
    symbol, and diagram image results.
    """

    result = analyze_document_for_stem(text, diagram_images=diagram_images)
    features = get_available_stem_features(result)
    formulas = extract_formulas(text)
    symbols = extract_symbols(text)

    return {
        "result": result,
        "features": features,
        "formulas": formulas,
        "symbols": symbols,
        "diagram_images": diagram_images or [],
    }
