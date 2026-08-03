from services.visual_service import generate_visual_content


def test_generate_visual_content_keeps_flowchart_output_for_legacy_mind_map_requests(monkeypatch):
    monkeypatch.delenv("USE_MINDMAP_V2", raising=False)

    result = generate_visual_content(
        "Ohm's Law relates voltage, current, and resistance in an electrical circuit.",
        visual_type="mind_map",
    )

    assert result["flowchart_path"]
    assert "mindmap_path" not in result
