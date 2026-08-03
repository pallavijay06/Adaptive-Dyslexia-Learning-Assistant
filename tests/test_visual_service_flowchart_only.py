import pytest

from services import visual_service


def test_generate_visual_content_ignores_mind_map_requests(monkeypatch, tmp_path):
    flowchart_calls = []

    def fake_create_process_flowchart(title, steps, theme):
        flowchart_calls.append((title, steps, theme))
        output = tmp_path / "flowchart.png"
        output.write_bytes(b"png")
        return str(output)

    monkeypatch.setattr(visual_service, "create_process_flowchart", fake_create_process_flowchart)
    monkeypatch.setattr(visual_service, "detect_topic", lambda text: "Test Topic")
    monkeypatch.setattr(
        visual_service,
        "_extract_visual_structure",
        lambda text: {
            "title": "Test Topic",
            "description": "A short description",
            "steps": ["First step", "Second step"],
            "inputs": [{"text": "Input", "emoji": "📥"}],
            "outputs": [{"text": "Output", "emoji": "📤"}],
        },
    )

    result = visual_service.generate_visual_content("Some educational content", visual_type="mind_map")

    assert result["flowchart_path"]
    assert "mindmap_path" not in result
    assert flowchart_calls == [("Test Topic", ["First step", "Second step"], "light")]
