# NOVA_CHAT_TURN_ATTACHMENT_HYDRATOR_TESTS_20260705

from pathlib import Path

from nova_backend.services.chat_turn_attachment_context import (
    nova_chat_turn_inject_attachment_context_from_locals,
)
from nova_backend.services.chat_turn_attachment_hydrator import (
    hydrate_attachment_for_context,
    hydrate_attachments_for_context,
)


def test_hydrator_extracts_text_from_local_upload(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()

    target = uploads / "hello.txt"
    target.write_text("This is server-side extracted attachment text.", encoding="utf-8")

    hydrated = hydrate_attachment_for_context(
        {
            "filename": "hello.txt",
            "mime_type": "text/plain",
        },
        uploads_dir=uploads,
    )

    assert "attachment_summary" in hydrated
    assert "server-side extracted attachment text" in hydrated["attachment_summary"]


def test_hydrator_resolves_api_upload_url(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()

    target = uploads / "url-notes.md"
    target.write_text("# Notes\nHydrated from an upload URL.", encoding="utf-8")

    hydrated = hydrate_attachment_for_context(
        {
            "url": "/api/uploads/url-notes.md",
            "mime_type": "text/markdown",
        },
        uploads_dir=uploads,
    )

    assert "Hydrated from an upload URL" in hydrated["attachment_summary"]


def test_hydrator_does_not_override_existing_summary(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()

    target = uploads / "existing.txt"
    target.write_text("This should not replace the summary.", encoding="utf-8")

    hydrated = hydrate_attachment_for_context(
        {
            "filename": "existing.txt",
            "summary": "Already analyzed by upload pipeline.",
        },
        uploads_dir=uploads,
    )

    assert hydrated["summary"] == "Already analyzed by upload pipeline."
    assert "attachment_summary" not in hydrated


def test_hydrator_blocks_path_traversal(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()

    secret = tmp_path / "secret.txt"
    secret.write_text("do not read me", encoding="utf-8")

    hydrated = hydrate_attachment_for_context(
        {
            "filename": "../secret.txt",
            "mime_type": "text/plain",
        },
        uploads_dir=uploads,
    )

    assert "attachment_summary" not in hydrated


def test_hydrator_list_api_returns_list(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()

    target = uploads / "batch.txt"
    target.write_text("Batch extracted text.", encoding="utf-8")

    hydrated = hydrate_attachments_for_context(
        [
            {
                "filename": "batch.txt",
            }
        ],
        uploads_dir=uploads,
    )

    assert isinstance(hydrated, list)
    assert "Batch extracted text." in hydrated[0]["attachment_summary"]


def test_chat_turn_context_wiring_can_include_hydrated_upload(monkeypatch, tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()

    target = uploads / "chat-turn.txt"
    target.write_text("ChatTurn can see hydrated upload text.", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    messages = [
        {
            "role": "user",
            "content": "summarize this attached file",
        }
    ]

    output = nova_chat_turn_inject_attachment_context_from_locals(
        messages,
        {
            "attachments": [
                {
                    "filename": "chat-turn.txt",
                    "mime_type": "text/plain",
                }
            ]
        },
    )

    assert output[0]["role"] == "system"
    assert "NOVA_ATTACHMENT_CONTEXT_20260705" in output[0]["content"]
    assert "ChatTurn can see hydrated upload text." in output[0]["content"]
