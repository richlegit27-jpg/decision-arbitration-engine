# NOVA_ATTACHMENT_CONTEXT_DEBUG_ROUTE_TESTS_20260705

import importlib


def _client():
    app_module = importlib.import_module("app")
    flask_app = getattr(app_module, "app")
    return flask_app.test_client()


def test_attachment_context_debug_route_disabled_without_env(monkeypatch):
    monkeypatch.delenv("NOVA_DEBUG_ROUTES", raising=False)

    client = _client()

    response = client.post(
        "/api/debug/attachment-context-dry-run",
        json={
            "attachments": [
                {
                    "filename": "disabled.txt",
                    "summary": "This should not be visible while disabled.",
                }
            ]
        },
    )

    assert response.status_code == 404
    data = response.get_json()
    assert data["ok"] is False
    assert "disabled" in data["error"].lower()


def test_attachment_context_debug_route_returns_context_when_enabled(monkeypatch):
    monkeypatch.setenv("NOVA_DEBUG_ROUTES", "1")

    client = _client()

    response = client.post(
        "/api/debug/attachment-context-dry-run",
        json={
            "attachments": [
                {
                    "filename": "notes.txt",
                    "mime_type": "text/plain",
                    "size_bytes": 123,
                    "summary": "Backend attachment context is visible.",
                }
            ]
        },
    )

    assert response.status_code == 200
    data = response.get_json()

    assert data["ok"] is True
    assert data["attachment_count"] == 1
    assert data["attachment_context_present"] is True
    assert "NOVA_ATTACHMENT_CONTEXT_20260705" in data["attachment_context"]
    assert "notes.txt" in data["attachment_context"]
    assert "Backend attachment context is visible." in data["attachment_context"]


def test_attachment_context_debug_route_accepts_nested_upload_alias(monkeypatch):
    monkeypatch.setenv("NOVA_DEBUG_ROUTES", "1")

    client = _client()

    response = client.post(
        "/api/debug/attachment-context-dry-run",
        json={
            "request_json": {
                "uploads": [
                    {
                        "name": "nested-image.png",
                        "description": "Nested uploaded image description.",
                    }
                ]
            }
        },
    )

    assert response.status_code == 200
    data = response.get_json()

    assert data["ok"] is True
    assert data["attachment_count"] == 1
    assert data["attachment_context_present"] is True
    assert "nested-image.png" in data["attachment_context"]
    assert "Nested uploaded image description." in data["attachment_context"]
