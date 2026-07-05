# NOVA_ATTACHMENT_READINESS_DEBUG_ROUTE_TESTS_20260705

import importlib


def _client():
    app_module = importlib.import_module("app")
    return app_module.app.test_client()


def test_attachment_readiness_debug_route_disabled_without_env(monkeypatch):
    monkeypatch.delenv("NOVA_DEBUG_ROUTES", raising=False)

    client = _client()

    response = client.post(
        "/api/debug/attachment-readiness",
        json={
            "message": "summarize this attached file",
            "attachments": [
                {
                    "filename": "disabled.txt",
                    "summary": "Disabled route should hide this.",
                }
            ],
        },
    )

    assert response.status_code == 404
    data = response.get_json()
    assert data["ok"] is False
    assert "disabled" in data["error"].lower()


def test_attachment_readiness_debug_route_checks_full_chain(monkeypatch, tmp_path):
    monkeypatch.setenv("NOVA_DEBUG_ROUTES", "1")
    monkeypatch.chdir(tmp_path)

    uploads = tmp_path / "uploads"
    uploads.mkdir()

    target = uploads / "readiness.txt"
    target.write_text(
        "Attachment readiness marker: backend API chain works.",
        encoding="utf-8",
    )

    client = _client()

    response = client.post(
        "/api/debug/attachment-readiness",
        json={
            "message": "summarize this attached file",
            "files": [
                {
                    "name": "readiness.txt",
                    "mime_type": "text/plain",
                }
            ],
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["ok"] is True
    assert data["attachment_count"] == 1
    assert data["hydrated_attachment_count"] == 1
    assert data["attachment_context_present"] is True
    assert data["attachment_context_marker_present"] is True
    assert "readiness.txt" in data["attachment_context_preview"]
    assert "backend API chain works" in data["attachment_context_preview"]
    assert data["guard"]["attachments_present"] is True
    assert data["guard"]["attachment_focused"] is True
    assert data["guard"]["suppress_web"] is True
