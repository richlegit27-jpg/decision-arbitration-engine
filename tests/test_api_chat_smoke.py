from __future__ import annotations

from app import app


def test_api_chat_endpoint_smoke() -> None:
    client = app.test_client()

    response = client.post(
        "/api/chat",
        json={
            "message": "Say pong only.",
            "session_id": "pytest_chat_smoke",
            "attachments": [],
        },
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert isinstance(payload, dict)
    assert payload.get("ok") is True
