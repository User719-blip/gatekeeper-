from fastapi.testclient import TestClient

from app import app


def test_test_sentry_message_returns_200_and_sends_event(monkeypatch):
    captured = {}

    def fake_capture_message(message: str, level: str = "info"):
        captured["message"] = message
        captured["level"] = level

    monkeypatch.setattr("app.sentry_sdk.capture_message", fake_capture_message)

    with TestClient(app) as client:
        response = client.post("/test-sentry-message")

    assert response.status_code == 200
    assert response.json() == {"message": "Sentry test message sent"}
    assert captured["message"] == "Manual Sentry test message from /test-sentry-message"
    assert captured["level"] == "info"


def test_test_error_returns_500_when_server_exceptions_disabled():
    # Integration-style check for production behavior: endpoint returns 500.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-error")

    assert response.status_code == 500
