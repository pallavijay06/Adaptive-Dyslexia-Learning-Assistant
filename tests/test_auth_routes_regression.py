from backend.flask_app import app


def test_auth_session_endpoint_returns_false_when_not_authenticated():
    client = app.test_client()
    response = client.get('/api/auth/session')

    assert response.status_code == 200
    assert response.get_json() == {'authenticated': False}
