import types

import backend.chat_routes as chat_routes
from backend.flask_app import create_app


def test_chat_returns_answer_when_chat_persistence_fails(monkeypatch):
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
            return None

        def should_recommend_practice(self):
            return None

        def get_adjustment_suggestion(self):
            return None

    monkeypatch.setattr(chat_routes, "_resolve_user_id", lambda user_id_from_request=None: 1)
    monkeypatch.setattr(chat_routes, "AdaptiveAITutor", DummyTutor)
    monkeypatch.setattr(chat_routes, "get_db_document", lambda document_id: None)
    monkeypatch.setattr(chat_routes, "ask_document", lambda *args, **kwargs: "Generated answer")

    def failing_save_chat(**kwargs):
        raise RuntimeError("db locked")

    monkeypatch.setattr(chat_routes, "save_chat", failing_save_chat)

    response = client.post(
        "/chat",
        json={"message": "Explain this", "document_id": 7},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["response"] == "Generated answer"
    assert data["adaptive"]["context"]["topic"] is None
