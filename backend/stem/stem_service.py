"""Service layer for the isolated Phase 1 STEM support framework.

This module provides the high-level entry points future routes or UI workflows
can call when STEM integration is approved. It does not import Streamlit, app
entry points, quiz modules, or existing document-processing pipelines.
"""

from backend.stem.detector import detect_stem_content
from backend.stem.models import STEMDetectionResult


def analyze_document_for_stem(text: str | None, diagram_images: list[str] | None = None) -> STEMDetectionResult:
    """Analyze extracted document text and return STEM detection statistics."""

    return detect_stem_content(text, diagram_images=diagram_images)


def get_available_stem_features(result: STEMDetectionResult) -> list[str]:
    """Return placeholder STEM feature names based on detected content.

    Future connection points:
    - Formula Assistant will connect when ``result.has_formula`` is true.
    - Step-by-Step Solutions will connect when formulas are available.
    - Symbol Explanation will connect when ``result.has_symbols`` is true.
    - Diagram Explanation will connect when ``result.has_diagrams`` is true.
    """

    features = []

    if result.has_formula:
        features.append("Formula Assistant")
        features.append("Step-by-Step Solutions")

    if result.has_symbols:
        features.append("Symbol Explanation")

    if result.has_diagrams:
        features.append("Diagram Explanation")

    return features
