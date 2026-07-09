# NOVA_ATTACHMENT_API_CONTRACT_TEST_20260705
"""
Attachment API contract regression.

This locks the backend contract we want mobile/client code to rely on:

1. /api/upload returns canonical attachment fields.
2. The exact upload JSON can be normalized as a chat attachment.
3. Text-like uploads carry or can produce backend-owned attachment context.
4. Attachment debug routes are disabled by default.
"""

from __future__ import annotations

from io import BytesIO
import importlib

from nova_backend.services.chat_attachment_payload_normalizer import (
    normalize_api_chat_attachments,
)
from nova_backend.services.chat_turn_attachment_context import (
    build_attachment_context_text,
)
from nova_backend.services.chat_turn_attachment_hydrator import (
    hydrate_attachments_for_context,
)


def _client():
    app_module = importlib.import_module("app")
    return app_module.app.test_client()


def test_attachment_api_contract_upload_json_is_chat_ready(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    client = _client()

    response = client.post(
        "/api/upload",
        data={
            "file": (
                BytesIO(b"Attachment API contract marker: client can reuse upload JSON."),
                "attachment-contract.txt",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code in {200, 201}

    upload_json = response.get_json(silent=True) or {}

    assert upload_json.get("ok") is not False

    # Canonical fields clients/mobile can safely carry into /api/chat.
    assert upload_json.get("filename") or upload_json.get("name")
    assert upload_json.get("url") or upload_json.get("download_url") or upload_json.get("path")

    attachments = normalize_api_chat_attachments(
        {
            "message": "summarize this attached file",
            "attachments": [
                upload_json,
            ],
        }
    )

    assert len(attachments) == 1

    hydrated = hydrate_attachments_for_context(attachments)
    context = build_attachment_context_text(hydrated)

    assert "NOVA_ATTACHMENT_CONTEXT_20260705" in context
    assert "attachment-contract.txt" in context
    assert "client can reuse upload JSON" in context


def test_attachment_api_contract_common_aliases_are_equivalent():
    payload = {
        "attachments": [
            {
                "filename": "a.txt",
                "summary": "A.",
            }
        ],
        "files": [
            {
                "name": "b.txt",
                "description": "B.",
            }
        ],
        "uploads": [
            {
                "url": "/api/uploads/c.txt",
                "mime_type": "text/plain",
            }
        ],
        "request_json": {
            "uploaded_files": [
                {
                    "name": "d.txt",
                    "summary": "D.",
                }
            ]
        },
    }

    attachments = normalize_api_chat_attachments(payload)
    text = str(attachments)

    assert len(attachments) == 4
    assert "a.txt" in text
    assert "b.txt" in text
    assert "c.txt" in text
    assert "d.txt" in text


def test_attachment_api_contract_debug_routes_disabled_by_default(monkeypatch):
    monkeypatch.delenv("NOVA_DEBUG_ROUTES", raising=False)

    client = _client()

    response = client.post(
        "/api/debug/attachment-readiness",
        json={
            "message": "summarize this attached file",
            "attachments": [
                {
                    "filename": "secret.txt",
                    "summary": "Should not be exposed by default.",
                }
            ],
        },
    )

    assert response.status_code == 404

    data = response.get_json(silent=True) or {}

    assert data.get("ok") is False
    assert "disabled" in data.get("error", "").lower()
