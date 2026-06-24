"""Tests for diagram explanation caching in STEM support."""

import tempfile
from pathlib import Path
import time

from backend.stem.diagram_explainer import explain_diagram
from services.cache_service import clear_cache, get_cache_value, make_diagram_cache_key


def test_explain_diagram_uses_cache(monkeypatch, tmp_path: Path):
    image_file = tmp_path / "diagram.png"
    image_file.write_bytes(b"image-bytes-1")

    responses = {"count": 0}

    def fake_analyze(path):
        responses["count"] += 1
        return '{"diagram_type": "Flowchart", "purpose": "Shows steps.", "how_it_works": ["One", "Two"], "component_roles": [{"component": "A", "role": "B"}], "key_concept": "Steps.", "simplified_explanation": "It shows a flow.", "key_takeaway": "Follow the path."}'

    monkeypatch.setattr("backend.stem.diagram_explainer._analyze_image_with_gemini", fake_analyze)
    clear_cache()

    first = explain_diagram(str(image_file))
    second = explain_diagram(str(image_file))

    assert first == second
    assert responses["count"] == 1


def test_explain_diagram_different_image_creates_new_cache_entry(monkeypatch, tmp_path: Path):
    image_file_a = tmp_path / "diagram_a.png"
    image_file_b = tmp_path / "diagram_b.png"
    image_file_a.write_bytes(b"image-bytes-a")
    image_file_b.write_bytes(b"image-bytes-b")

    def fake_analyze(path):
        if str(path).endswith("diagram_a.png"):
            return '{"diagram_type": "Circuit", "purpose": "A.", "how_it_works": ["A"], "component_roles": [{"component": "X", "role": "Y"}], "key_concept": "A." , "simplified_explanation": "A.", "key_takeaway": "A."}'
        return '{"diagram_type": "Graph", "purpose": "B.", "how_it_works": ["B"], "component_roles": [{"component": "Y", "role": "Z"}], "key_concept": "B.", "simplified_explanation": "B.", "key_takeaway": "B."}'

    monkeypatch.setattr("backend.stem.diagram_explainer._analyze_image_with_gemini", fake_analyze)
    clear_cache()

    first = explain_diagram(str(image_file_a))
    second = explain_diagram(str(image_file_b))

    assert first["diagram_type"] == "Circuit"
    assert second["diagram_type"] == "Graph"
    assert first != second


def test_diagram_cache_values_are_stored_completely(tmp_path: Path):
    image_file = tmp_path / "diagram.png"
    image_file.write_bytes(b"image-bytes-1")
    cache_key = make_diagram_cache_key(image_file.read_bytes())

    cached_value = {
        "diagram_type": "Circuit",
        "purpose": "Shows current.",
        "how_it_works": ["Step1", "Step2"],
        "component_roles": [{"component": "Battery", "role": "Provides power"}],
        "key_concept": "Current flows.",
        "simplified_explanation": "Electricity moves.",
        "key_takeaway": "Use it wisely.",
    }

    from services.cache_service import set_cache_value
    clear_cache()
    set_cache_value(cache_key, cached_value, ttl_hours=1)

    assert get_cache_value(cache_key) == cached_value


def test_diagram_cache_ttl_expiry(tmp_path: Path):
    from services.cache_service import set_cache_value

    image_file = tmp_path / "diagram.png"
    image_file.write_bytes(b"image-bytes-ttl")
    cache_key = make_diagram_cache_key(image_file.read_bytes())

    clear_cache()
    set_cache_value(cache_key, {"diagram_type": "Expired"}, ttl_hours=0)
    assert get_cache_value(cache_key) is None
