from services.visual_service import generate_visual_content


def test_generate_visual_content_uses_new_pipeline_when_feature_flag_enabled(monkeypatch):
    monkeypatch.setenv("USE_MINDMAP_V2", "1")

    result = generate_visual_content(
        "Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to make glucose and oxygen.",
        visual_type="mind_map",
    )

    assert result["mindmap_path"]
    assert result["mindmap_layout_model"]["center_node"]["label"] == "Photosynthesis"
    assert result["mindmap_layout_model"]["branch_nodes"]
    assert result["mindmap_layout_model"]["child_nodes"]


def test_generate_visual_content_defaults_to_new_pipeline(monkeypatch):
    monkeypatch.delenv("USE_MINDMAP_V2", raising=False)

    result = generate_visual_content(
        "Ohm's Law relates voltage, current, and resistance in an electrical circuit.",
        visual_type="mind_map",
    )

    assert result["mindmap_path"]
    assert result["mindmap_layout_model"] is not None
    assert result["mindmap_layout_model"]["center_node"]["label"] == "Ohm's Law"
