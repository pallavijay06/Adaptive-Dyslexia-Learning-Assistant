from unittest.mock import patch

from backend.document_routes import document_bp
from services import quiz_hint_service
from services.llm_router import LLMRouterError


def test_quiz_hint_uses_bounded_question_only_request() -> None:
    captured = {}

    def fake_generate_content(prompt, max_tokens=None):
        captured["prompt"] = prompt
        captured["max_tokens"] = max_tokens
        return "Think about the process that turns light into stored energy."

    with patch.object(quiz_hint_service, "generate_content", side_effect=fake_generate_content):
        hint = quiz_hint_service.generate_quiz_hint(
            question="What process lets plants make food?",
            correct_answer="Photosynthesis",
            concept="Plant energy",
            question_type="MCQ",
        )

    assert hint.startswith("Think about")
    assert captured["max_tokens"] == quiz_hint_service.QUIZ_HINT_MAX_TOKENS
    assert captured["max_tokens"] != 65535
    assert "What process lets plants make food?" in captured["prompt"]
    assert "Photosynthesis" in captured["prompt"]
    assert "Plant energy" in captured["prompt"]
    assert "DOCUMENT CONTENT:" not in captured["prompt"]
    assert "ALL QUESTIONS" not in captured["prompt"]
    assert "ANSWER OPTIONS" not in captured["prompt"]


def test_quiz_hint_route_returns_generated_hint() -> None:
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(document_bp)

    with patch.object(
        quiz_hint_service,
        "generate_content",
        return_value="Focus on the starting condition in the question.",
    ):
        response = app.test_client().post(
            "/quiz/hint",
            json={
                "question": "What happens first?",
                "correct_answer": "Evaporation",
                "concept": "Water cycle",
                "question_type": "MCQ",
            },
        )

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "hint": "Focus on the starting condition in the question.",
    }


def test_quiz_hint_route_does_not_replace_provider_failure_with_hint() -> None:
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(document_bp)

    with patch.object(
        quiz_hint_service,
        "generate_content",
        side_effect=LLMRouterError("provider unavailable"),
    ):
        response = app.test_client().post(
            "/quiz/hint",
            json={"question": "What happens first?", "correct_answer": "Evaporation"},
        )

    assert response.status_code == 503
    assert response.get_json() == {"success": False, "error": "provider unavailable"}