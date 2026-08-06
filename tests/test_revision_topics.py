from types import SimpleNamespace

from flask import Flask

from backend import adaptive_routes as adaptive_routes_module
from backend.adaptive_routes import adaptive_bp


def test_generate_plan_uses_document_concepts_from_document_id(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(adaptive_bp)

    captured = {}

    def fake_get_user_by_id(user_id):
        return SimpleNamespace(id=user_id)

    def fake_get_adaptive_learning_plan(user_id, document_concepts, is_stem_document=False):
        captured["user_id"] = user_id
        captured["document_concepts"] = document_concepts
        captured["is_stem_document"] = is_stem_document
        return SimpleNamespace(
            adaptive_learning_flow=[],
            content_instruction=SimpleNamespace(),
            concept_instruction=SimpleNamespace(),
            learning_strategy=SimpleNamespace(),
            overall_confidence=0.0,
            decision_summary=SimpleNamespace(),
            prompt_instruction_set=SimpleNamespace(),
        )

    def fake_get_active_document(document_id=None):
        assert document_id in {None, "42"}
        return SimpleNamespace(document_text="Ohm's law explains voltage, current, and resistance in a circuit.")

    def fake_get_db_document(document_id):
        assert document_id == 42
        return SimpleNamespace(document_text="Ohm's law explains voltage, current, and resistance in a circuit.")

    monkeypatch.setattr(adaptive_routes_module, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(adaptive_routes_module, "get_adaptive_learning_plan", fake_get_adaptive_learning_plan)
    monkeypatch.setattr(adaptive_routes_module, "get_active_document", fake_get_active_document)
    monkeypatch.setattr(adaptive_routes_module, "get_db_document", fake_get_db_document)

    with app.test_client() as client:
        response = client.post(
            "/adaptive-plan/generate",
            json={"user_id": 7, "document_id": 42},
        )

    assert response.status_code == 200
    assert captured["user_id"] == 7
    assert any(c.lower() == "voltage" for c in captured["document_concepts"])
    assert any(c.lower() == "current" for c in captured["document_concepts"])
    assert any(c.lower() == "resistance" for c in captured["document_concepts"])


def test_current_recommendation_exposes_summary_fields(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(adaptive_bp)

    from backend import adaptive_routes as adaptive_routes_module

    adaptive_routes_module._journey_state[7] = {
        "current_step": 1,
        "plan": {
            "adaptive_learning_flow": [{"step": 1, "action": "learning_mode"}],
            "decision_summary": {
                "teaching_style": "Simple, Step-by-Step",
                "focus_concepts": ["Reading"],
                "learning_strategy": "Visual",
                "revision_required": False,
                "session_duration": "20 minutes",
                "overall_confidence": 0.95,
                "comprehension_level": "Good",
                "recommended_learning_mode": "Visual",
            },
        },
        "completed_steps": [],
        "total_steps": 1,
    }

    with app.test_client() as client:
        response = client.get("/adaptive-plan/current/7")

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["summary"]["comprehension_level"] == "Good"
    assert body["summary"]["recommended_learning_mode"] == "Visual"
