"""Tests for the STEM Diagram Explanation feature."""

import tempfile
from pathlib import Path

from backend.stem.diagram_explainer import explain_diagram


def test_explain_diagram_missing_image_returns_fallback():
    result = explain_diagram("nonexistent_image.png")
    assert result == {
        "diagram_type": "Unknown",
        "purpose": "Unable to determine diagram purpose.",
        "how_it_works": [],
        "component_roles": [],
        "key_concept": "",
        "simplified_explanation": "The diagram could not be analyzed.",
        "key_takeaway": "Try another image.",
    }


def test_explain_diagram_invalid_extension_returns_fallback(tmp_path: Path):
    invalid_file = tmp_path / "diagram.txt"
    invalid_file.write_text("not an image")

    result = explain_diagram(str(invalid_file))

    assert result["diagram_type"] == "Unknown"
    assert result["component_roles"] == []


def test_explain_diagram_valid_image_path_uses_stubbed_analysis(monkeypatch, tmp_path: Path):
    image_file = tmp_path / "diagram.png"
    image_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    def fake_analyze(path):
        return '{"diagram_type": "Flowchart", "purpose": "Shows the steps of a process.", "how_it_works": ["Start", "Do step 1", "Make a decision", "End"], "component_roles": [{"component": "Start", "role": "Beginning"}, {"component": "End", "role": "Finish"}], "key_concept": "Order of steps matters.", "simplified_explanation": "This shows steps in order. Arrows show what happens next.", "key_takeaway": "Follow the arrows to understand the order."}'

    monkeypatch.setattr("backend.stem.diagram_explainer._analyze_image_with_gemini", fake_analyze)

    result = explain_diagram(str(image_file))

    assert result == {
        "diagram_type": "Flowchart",
        "purpose": "Shows the steps of a process.",
        "how_it_works": ["Start", "Do step 1", "Make a decision", "End"],
        "component_roles": [{"component": "Start", "role": "Beginning"}, {"component": "End", "role": "Finish"}],
        "key_concept": "Order of steps matters.",
        "simplified_explanation": "This shows steps in order. Arrows show what happens next.",
        "key_takeaway": "Follow the arrows to understand the order.",
    }


def test_explain_diagram_analysis_error_returns_fallback(monkeypatch, tmp_path: Path):
    image_file = tmp_path / "diagram.jpg"
    image_file.write_bytes(b"\xff\xd8\xff\xdb")

    def bad_analyze(path):
        raise RuntimeError("Vision provider failed")

    monkeypatch.setattr("backend.stem.diagram_explainer._analyze_image_with_gemini", bad_analyze)

    result = explain_diagram(str(image_file))

    assert result["diagram_type"] == "Unknown"
    assert result["key_takeaway"] == "Try another image."
