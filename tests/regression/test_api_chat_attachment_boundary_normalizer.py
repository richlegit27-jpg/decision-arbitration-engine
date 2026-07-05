# NOVA_API_CHAT_ATTACHMENT_BOUNDARY_NORMALIZER_TESTS_20260705

from nova_backend.services.chat_attachment_payload_normalizer import (
    normalize_api_chat_attachments,
)
from nova_backend.services.chat_turn_attachment_context import (
    nova_chat_turn_inject_attachment_context_from_locals,
)


def test_boundary_normalizer_accepts_top_level_aliases():
    payload = {
        "session_id": "s1",
        "message": "summarize",
        "attachments": [
            {
                "filename": "a.txt",
                "summary": "A attachment.",
            }
        ],
        "files": [
            {
                "name": "b.txt",
                "description": "B attachment.",
            }
        ],
        "uploads": [
            {
                "url": "/api/uploads/c.txt",
                "mime_type": "text/plain",
            }
        ],
    }

    attachments = normalize_api_chat_attachments(payload)

    names = str(attachments)

    assert len(attachments) == 3
    assert "a.txt" in names
    assert "b.txt" in names
    assert "c.txt" in names


def test_boundary_normalizer_accepts_nested_aliases():
    payload = {
        "request_json": {
            "payload": {
                "uploaded_files": [
                    {
                        "name": "nested.txt",
                        "summary": "Nested attachment.",
                    }
                ]
            }
        }
    }

    attachments = normalize_api_chat_attachments(payload)

    assert len(attachments) == 1
    assert attachments[0]["name"] == "nested.txt"


def test_boundary_normalizer_dedupes_same_upload():
    payload = {
        "attachments": [
            {
                "filename": "same.txt",
                "summary": "One.",
            }
        ],
        "files": [
            {
                "filename": "same.txt",
                "summary": "One again.",
            }
        ],
    }

    attachments = normalize_api_chat_attachments(payload)

    assert len(attachments) == 1
    assert attachments[0]["filename"] == "same.txt"


def test_boundary_normalizer_does_not_treat_chat_payload_as_attachment():
    payload = {
        "session_id": "s1",
        "message": "hello",
        "text": "this is the user text, not file text",
    }

    attachments = normalize_api_chat_attachments(payload)

    assert attachments == []


def test_chat_turn_injector_reads_flask_g_boundary_attachments(monkeypatch, tmp_path):
    import importlib

    monkeypatch.chdir(tmp_path)

    uploads = tmp_path / "uploads"
    uploads.mkdir()

    target = uploads / "g-boundary.txt"
    target.write_text("Flask g boundary attachment text.", encoding="utf-8")

    app_module = importlib.import_module("app")
    flask_app = getattr(app_module, "app")

    with flask_app.test_request_context(
        "/api/chat",
        method="POST",
        json={
            "files": [
                {
                    "name": "g-boundary.txt",
                    "mime_type": "text/plain",
                }
            ]
        },
    ):
        flask_app.preprocess_request()

        output = nova_chat_turn_inject_attachment_context_from_locals(
            [
                {
                    "role": "user",
                    "content": "summarize this attached file",
                }
            ],
            {},
        )

    text = output[0]["content"]

    assert "NOVA_ATTACHMENT_CONTEXT_20260705" in text
    assert "g-boundary.txt" in text
    assert "Flask g boundary attachment text." in text
