import importlib


def test_chat_turn_dry_run_route_accepts_attachment_payload(monkeypatch):
    monkeypatch.setenv("NOVA_DEBUG_ROUTES", "1")
    app_module = importlib.import_module("app")
    flask_app = getattr(app_module, "app")

    client = flask_app.test_client()

    payload = {
        "session_id": "session_dry_run_route_test_001",
        "message": "what is this image?",
        "attachments": [
            {
                "id": "upload_dry_route_001",
                "filename": "dry-route-test.png",
                "url": "/api/uploads/dry-route-test.png",
                "mime_type": "image/png",
            }
        ],
    }

    response = client.post(
        "/api/debug/chat-turn-dry-run",
        json=payload,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["ok"] is True
    assert data["turn"]["session_id"] == "session_dry_run_route_test_001"
    assert data["turn"]["intent"] == "image_attachment"
    assert data["turn"]["attachment_count"] == 1
    assert data["turn"]["attachments"][0]["kind"] == "image"
    assert data["messages"]["count"] >= 2

    roles = [item["role"] for item in data["messages"]["items"]]

    assert "system" in roles
    assert roles[-1] == "user"


def test_chat_turn_dry_run_route_coerces_alias_payload(monkeypatch):
    monkeypatch.setenv("NOVA_DEBUG_ROUTES", "1")
    app_module = importlib.import_module("app")
    flask_app = getattr(app_module, "app")

    client = flask_app.test_client()

    payload = {
        "sid": "session_dry_run_alias_test_001",
        "input": "analyze attached image",
        "uploaded_files": [
            {
                "id": "upload_alias_route_001",
                "filename": "alias-route-test.png",
                "url": "/api/uploads/alias-route-test.png",
                "mime_type": "image/png",
            }
        ],
    }

    response = client.post(
        "/api/debug/chat-turn-dry-run",
        json=payload,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["ok"] is True
    assert data["turn"]["session_id"] == "session_dry_run_alias_test_001"
    assert data["turn"]["user_text_preview"] == "analyze attached image"
    assert data["turn"]["attachment_count"] == 1

