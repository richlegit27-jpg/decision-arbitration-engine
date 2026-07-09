# NOVA_ATTACHMENT_WEB_GUARD_DEBUG_ROUTE_TESTS_20260705

import importlib


def _client():
    app_module = importlib.import_module("app")
    return app_module.app.test_client()


def test_attachment_web_guard_debug_route_disabled_without_env(monkeypatch):
    monkeypatch.delenv("NOVA_DEBUG_ROUTES", raising=False)

    client = _client()

    response = client.post(
        "/api/debug/attachment-web-guard-dry-run",
        json={
            "message": "summarize this attached file",
            "attachments": [
                {
                    "filename": "disabled.txt",
                    "summary": "Hidden.",
                }
            ],
        },
    )

    assert response.status_code == 404
    data = response.get_json()
    assert data["ok"] is False


def test_attachment_web_guard_debug_route_suppresses_from_boundary_g(monkeypatch):
    monkeypatch.setenv("NOVA_DEBUG_ROUTES", "1")

    client = _client()

    response = client.post(
        "/api/debug/attachment-web-guard-dry-run",
        json={
            "message": "summarize this attached file",
            "files": [
                {
                    "name": "notes.txt",
                    "summary": "Backend attachment note.",
                }
            ],
        },
    )

    assert response.status_code == 200
    data = response.get_json()

    assert data["ok"] is True
    assert data["boundary_attachment_count"] == 1

    if data["available"]:
        assert data["suppressed"] is True
        assert data["reason"] == "attachment_focused_turn"
