# NOVA_ATTACHMENT_DEBUG_ROUTES_DISABLED_TEST_20260705
"""
Security regression:
All attachment debug endpoints must stay disabled unless NOVA_DEBUG_ROUTES=1.
"""

import importlib


ATTACHMENT_DEBUG_ROUTES = [
    "/api/debug/attachment-context-dry-run",
    "/api/debug/attachment-intent-guard",
    "/api/debug/attachment-readiness",
    "/api/debug/attachment-web-guard-dry-run",
]


def _client():
    app_module = importlib.import_module("app")
    return app_module.app.test_client()


def test_attachment_debug_routes_are_disabled_by_default(monkeypatch):
    monkeypatch.delenv("NOVA_DEBUG_ROUTES", raising=False)

    client = _client()

    for route in ATTACHMENT_DEBUG_ROUTES:
        response = client.post(
            route,
            json={
                "message": "summarize this attached file",
                "attachments": [
                    {
                        "filename": "debug-lock.txt",
                        "summary": "This should not be exposed.",
                    }
                ],
            },
        )

        assert response.status_code == 404, route

        data = response.get_json(silent=True) or {}

        assert data.get("ok") is False, route
        assert "disabled" in data.get("error", "").lower(), route


def test_attachment_debug_routes_enable_with_env(monkeypatch):
    monkeypatch.setenv("NOVA_DEBUG_ROUTES", "1")

    client = _client()

    for route in ATTACHMENT_DEBUG_ROUTES:
        response = client.post(
            route,
            json={
                "message": "summarize this attached file",
                "attachments": [
                    {
                        "filename": "debug-enabled.txt",
                        "summary": "Debug route enabled test.",
                    }
                ],
            },
        )

        assert response.status_code != 404, route

        data = response.get_json(silent=True) or {}

        assert data.get("ok") is True, route
