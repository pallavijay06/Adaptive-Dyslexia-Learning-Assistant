"""Standalone Streamlit UI components for STEM Support.

This module is intentionally isolated from the main application. It exposes a
single panel-rendering function that can later be plugged into `app.py` or
another approved UI surface with one function call.
"""

from __future__ import annotations

from collections.abc import Sequence

import streamlit as st

from backend.stem.models import STEMDetectionResult


STEM_FEATURES: tuple[str, ...] = (
    "Formula Assistant",
    "Symbol Explanation",
    "Diagram Explanation",
    "Step-by-Step Solutions",
)


def render_stem_panel(
    result: STEMDetectionResult,
    available_features: Sequence[str],
) -> None:
    """Render the standalone STEM Support panel.

    The buttons are placeholders only. Future implementations can connect:
    - Formula Assistant through the corresponding button callback.
    - Symbol Explanation through the corresponding button callback.
    - Diagram Explanation through the corresponding button callback.
    - Step-by-Step Solutions through the corresponding button callback.
    """

    available_feature_names = set(available_features)

    st.subheader("STEM Support Available")

    formula_column, symbol_column, diagram_column = st.columns(3)
    formula_column.metric("Formula count", result.formula_count)
    symbol_column.metric("Symbol count", result.symbol_count)
    diagram_column.metric("Diagram count", result.diagram_count)

    button_columns = st.columns(2)
    for index, feature_name in enumerate(STEM_FEATURES):
        column = button_columns[index % 2]
        column.button(
            feature_name,
            key=f"stem_feature_{feature_name.lower().replace(' ', '_').replace('-', '_')}",
            disabled=feature_name not in available_feature_names,
            use_container_width=True,
        )
