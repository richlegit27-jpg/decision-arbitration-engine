# NOVA_UPLOAD_ATTACHMENT_CONTEXT_COMPAT_TEST_20260705
"""
Upload-to-ChatTurn attachment context compatibility smoke.

This verifies:
1. /api/upload accepts a text file.
2. The upload response contains enough metadata for backend attachment hydration.
3. The resulting attachment context includes the uploaded file content.

No real model/API call is made.
"""

from __future__ import annotations

from io import BytesIO
import importlib


from nova_backend.services.chat_turn_attachment_context import (
    build_attachment_context_text,
    collect_attachments_from_scope,
)
from nova_backend.services.chat_turn_attachment_hydrator import (
    hydrate_attachments_for_context,
)


def test_upload_response_can_hydrate_attachment_context(monkeypatch, tmp_path):
    # Keep test-created uploads isolated when app code uses relative upload paths.
    monkeypatch.chdir(tmp_path)

    app_module = importlib.import_module("app")
    flask_app = getattr(app_module, "app")
    client = flask_app.test_client()

    upload_text = b"Upload endpoint compatibility marker: violet robot waterfall."

    response = client.post(
        "/api/upload",
        data={
            "file": (
                BytesIO(upload_text),
                "upload-context-compat.txt",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code in {200, 201}

    upload_json = response.get_json(silent=True) or {}

    assert upload_json

    attachments = collect_attachments_from_scope(
        {
            "attachments": [upload_json],
            "payload": upload_json,
            "request_json": upload_json,
        }
    )

    assert attachments, upload_json

    hydrated = hydrate_attachments_for_context(attachments)
    context = build_attachment_context_text(hydrated)

    assert "NOVA_ATTACHMENT_CONTEXT_20260705" in context
    assert "upload-context-compat.txt" in context or "upload_context_compat" in context
    assert "violet robot waterfall" in context
