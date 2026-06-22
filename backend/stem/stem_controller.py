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


def process_stem_support(text: str) -> dict[str, Any]:
    """Process extracted document text for STEM support.

    The controller performs no rendering and contains no Streamlit code. It
    only coordinates existing STEM service functions so future UI integration
    can call one stable entry point.
    """

    result = analyze_document_for_stem(text)
    features = get_available_stem_features(result)

    return {
        "result": result,
        "features": features,
    }
