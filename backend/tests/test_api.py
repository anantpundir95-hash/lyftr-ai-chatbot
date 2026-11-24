import os

os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"

from fastapi.testclient import TestClient

from main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "ok"
        assert data["keys_configured"] >= 2
        assert data["cache_enabled"] is True


def test_unknown_session():
    with TestClient(app) as client:
        response = client.get(
            "/sessions/session-that-does-not-exist/messages"
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "session not found"


def test_empty_message_validation():
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "session_id": "validation-test",
                "message": "     "
            }
        )

        assert response.status_code == 422


def test_missing_session_id():
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "message": "Hello"
            }
        )

        assert response.status_code == 422


def test_message_too_long():
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "session_id": "long-message-test",
                "message": "a" * 4001
            }
        )

        assert response.status_code == 422


def test_all_keys_simulated_failure():
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={
                "X-Simulate-Failure": "*=429"
            },
            json={
                "session_id": "simulated-all-fail",
                "message": "This should not reach Gemini."
            }
        )

        assert response.status_code == 503
        assert response.json() == {
            "detail": "all providers unavailable"
        }


def test_failed_request_not_stored():
    with TestClient(app) as client:
        session_id = "failed-history-test"

        response = client.post(
            "/chat",
            headers={
                "X-Simulate-Failure": "*=429"
            },
            json={
                "session_id": session_id,
                "message": "This should fail."
            }
        )

        assert response.status_code == 503

        history_response = client.get(
            f"/sessions/{session_id}/messages"
        )

        assert history_response.status_code == 404
        