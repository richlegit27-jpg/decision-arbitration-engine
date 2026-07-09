# NOVA_UPLOAD_ATTACHMENT_SUMMARY_TESTS_20260705

from io import BytesIO
import importlib

from nova_backend.services.chat_turn_attachment_context import (
    build_attachment_context_text,
    collect_attachments_from_scope,
)


def test_upload_text_response_includes_backend_attachment_summary(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    app_module = importlib.import_module("app")
    client = app_module.app.test_client()

    response = client.post(
        "/api/upload",
        data={
            "file": (
                BytesIO(b"Upload summary marker: backend extracted this text."),
                "upload-summary.txt",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code in {200, 201}

    data = response.get_json(silent=True) or {}

    assert data.get("ok") is not False
    assert data.get("filename") or data.get("name")
    assert data.get("url") or data.get("download_url")
    assert "backend extracted this text" in (
        data.get("attachment_summary")
        or data.get("extracted_text")
        or data.get("summary")
        or ""
    )


def test_upload_summary_response_can_build_attachment_context(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    app_module = importlib.import_module("app")
    client = app_module.app.test_client()

    response = client.post(
        "/api/upload",
        data={
            "file": (
                BytesIO(b"Upload context marker: response already carries useful context."),
                "upload-context-ready.txt",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code in {200, 201}

    data = response.get_json(silent=True) or {}

    attachments = collect_attachments_from_scope(
        {
            "attachments": [data],
        }
    )

    context = build_attachment_context_text(attachments)

    assert "NOVA_ATTACHMENT_CONTEXT_20260705" in context
    assert "upload-context-ready.txt" in context
    assert "response already carries useful context" in context
