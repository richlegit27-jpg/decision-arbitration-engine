from __future__ import annotations

from app import app


def test_api_chats_endpoint_smoke() -> None:
    client = app.test_client()

    response = client.get("/api/chats")

    assert response.status_code == 200

    payload = response.get_json()

    assert isinstance(payload, dict)
    assert payload.get("ok") is True

    chats = payload.get("chats")

    assert isinstance(chats, list)
