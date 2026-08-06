import types

import backend.chat_routes as chat_routes
from backend.flask_app import create_app


def test_chat_returns_answer_when_recommendations_fail(monkeypatch):
    app = create_app()
    client = app.test_client()

    class DummyTutor:
        def __init__(self, user_id, document_id=None):
            self.user_id = user_id
            self.document_id = document_id
            self.profile = types.SimpleNamespace(
                explanation_complexity="simple",
                preferred_learning_mode="Simplified Notes",
                confidence_level=0.8,
            )

        def prepare_response_context(self, topic=None):
            return {"topic": topic}

        def track_interaction(self, interaction_type, topic=None, duration_seconds=0, session_id=None):
            return None

        def should_recommend_mode(self):
            raise RuntimeError("recommendation DB down")

        def should_recommend_practice(self):
            raise RuntimeError("recommendation DB down")

        def get_adjustment_suggestion(self):
            raise RuntimeError("recommendation DB down")

    monkeypatch.setattr(chat_routes, "_resolve_user_id", lambda user_id_from_request=None: 1)
    monkeypatch.setattr(chat_routes, "AdaptiveAITutor", DummyTutor)
    monkeypatch.setattr(chat_routes, "get_db_document", lambda document_id: None)
    monkeypatch.setattr(chat_routes, "ask_document", lambda *args, **kwargs: "Generated answer")
    monkeypatch.setattr(chat_routes, "save_chat", lambda **kwargs: types.SimpleNamespace(id=1, user_id=1, document_id=None))

    response = client.post(
        "/chat",
        json={"message": "Explain this", "document_id": 7},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["response"] == "Generated answer"
    # recommendations may be empty but endpoint must succeed
    assert isinstance(data.get("adaptive", {}).get("recommendations", []), list)
