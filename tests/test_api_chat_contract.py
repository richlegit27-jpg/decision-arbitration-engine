from __future__ import annotations

from app import app


def test_api_chat_response_contract_smoke() -> None:
    client = app.test_client()

    response = client.post(
        "/api/chat",
        json={
            "user_text": "Say pong only.",
            "session_id": "pytest_chat_contract",
            "attachments": [],
        },
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert isinstance(payload, dict)
    assert payload.get("ok") is True

    assistant_message = payload.get("assistant_message") or payload.get("assistant")

    assert isinstance(assistant_message, dict)

    text = (
        assistant_message.get("text")
        or assistant_message.get("content")
        or assistant_message.get("message")
        or ""
    )

    assert isinstance(text, str)
    assert text.strip()


