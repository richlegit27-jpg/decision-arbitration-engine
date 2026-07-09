from __future__ import annotations


def test_api_chat_endpoint_smoke(monkeypatch):
    from app import app, chat_service

    def fake_handle(user_text, session_id="", attachments=None):
        return {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": "mock assistant response",
            },
            "active_session_id": session_id or "mock_session",
            "session_id": session_id or "mock_session",
            "session": {
                "id": session_id or "mock_session",
                "messages": [],
            },
            "debug": {
                "mocked": True,
            },
        }

    monkeypatch.setattr(chat_service, "handle", fake_handle)

    client = app.test_client()

    response = client.post(
        "/api/chat",
        json={
            "user_text": "hello",
            "session_id": "pytest_mock_session",
            "attachments": [],
        },
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload["ok"] is True
    assert payload["assistant_message"]["text"] == "mock assistant response"
    assert payload["active_session_id"] == "pytest_mock_session"


