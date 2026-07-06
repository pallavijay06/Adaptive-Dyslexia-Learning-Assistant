import types


def test_visual_personalization_helper_uses_prompt_builder(monkeypatch):
    from services import visual_service

    captured = {}

    class DummyPlan:
        decision_summary = types.SimpleNamespace(teaching_style="step_by_step")

    def fake_plan(user_id, document_concepts=None):
        return DummyPlan()

    def fake_build(context):
        captured["prompt_type"] = context.prompt_type
        return f"PERSONALIZED::{context.original_prompt}"

    monkeypatch.setattr(visual_service, "get_adaptive_learning_plan", fake_plan)
    monkeypatch.setattr(visual_service, "build_prompt", fake_build)

    prompt = visual_service._build_personalized_visual_prompt("ORIGINAL", 7)

    assert prompt == "PERSONALIZED::ORIGINAL"
    assert captured["prompt_type"] == visual_service.PromptType.VISUAL


def test_quiz_personalization_helper_uses_prompt_builder(monkeypatch):
    from services import quiz_service

    captured = {}

    class DummyPlan:
        decision_summary = types.SimpleNamespace(teaching_style="visual")

    def fake_plan(user_id, document_concepts=None):
        return DummyPlan()

    def fake_build(context):
        captured["prompt_type"] = context.prompt_type
        return f"PERSONALIZED::{context.original_prompt}"

    monkeypatch.setattr(quiz_service, "get_adaptive_learning_plan", fake_plan)
    monkeypatch.setattr(quiz_service, "build_prompt", fake_build)

    prompt = quiz_service._build_personalized_quiz_prompt("ORIGINAL", 7)

    assert prompt == "PERSONALIZED::ORIGINAL"
    assert captured["prompt_type"] == quiz_service.PromptType.QUIZ


def test_visual_personalization_falls_back_on_error(monkeypatch):
    from services import visual_service

    def fake_plan(user_id, document_concepts=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(visual_service, "get_adaptive_learning_plan", fake_plan)

    prompt = visual_service._build_personalized_visual_prompt("ORIGINAL", 7)

    assert prompt == "ORIGINAL"
