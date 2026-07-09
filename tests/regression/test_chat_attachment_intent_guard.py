# NOVA_CHAT_ATTACHMENT_INTENT_GUARD_TESTS_20260705

import importlib

from nova_backend.services.chat_attachment_intent_guard import (
    attachment_guard_metadata,
    has_attachments,
    is_attachment_focused_message,
    should_suppress_web_for_attachment,
)


def test_guard_detects_attachments_from_aliases():
    assert has_attachments(
        {
            "files": [
                {
                    "name": "notes.txt",
                    "mime_type": "text/plain",
                }
            ]
        }
    )


def test_guard_marks_summarize_attachment_as_attachment_focused():
    payload = {
        "attachments": [
            {
                "filename": "notes.txt",
                "summary": "Notes.",
            }
        ]
    }

    assert is_attachment_focused_message("summarize this attached file", payload)
    assert should_suppress_web_for_attachment("summarize this attached file", payload)


def test_guard_marks_what_is_this_image_as_attachment_focused():
    payload = {
        "uploads": [
            {
                "name": "image.png",
                "mime_type": "image/png",
            }
        ]
    }

    assert is_attachment_focused_message("what is this image?", payload)
    assert should_suppress_web_for_attachment("what is this image?", payload)


def test_guard_does_not_suppress_explicit_web_request():
    payload = {
        "attachments": [
            {
                "filename": "company.txt",
                "summary": "Company name.",
            }
        ]
    }

    assert is_attachment_focused_message("look up latest news about this attached company", payload)
    assert not should_suppress_web_for_attachment("look up latest news about this attached company", payload)


def test_guard_does_not_trigger_without_attachments():
    payload = {
        "message": "summarize this attached file",
    }

    assert not is_attachment_focused_message("summarize this attached file", payload)
    assert not should_suppress_web_for_attachment("summarize this attached file", payload)


def test_guard_metadata_shape():
    payload = {
        "files": [
            {
                "name": "notes.txt",
                "description": "Notes.",
            }
        ]
    }

    data = attachment_guard_metadata("read this file", payload)

    assert data == {
        "attachments_present": True,
        "attachment_focused": True,
        "suppress_web": True,
    }


def test_attachment_intent_debug_route_disabled_without_env(monkeypatch):
    monkeypatch.delenv("NOVA_DEBUG_ROUTES", raising=False)

    app_module = importlib.import_module("app")
    client = app_module.app.test_client()

    response = client.post(
        "/api/debug/attachment-intent-guard",
        json={
            "message": "summarize this attached file",
            "attachments": [
                {
                    "filename": "notes.txt",
                    "summary": "Notes.",
                }
            ],
        },
    )

    assert response.status_code == 404
    data = response.get_json()
    assert data["ok"] is False


def test_attachment_intent_debug_route_enabled(monkeypatch):
    monkeypatch.setenv("NOVA_DEBUG_ROUTES", "1")

    app_module = importlib.import_module("app")
    client = app_module.app.test_client()

    response = client.post(
        "/api/debug/attachment-intent-guard",
        json={
            "message": "summarize this attached file",
            "attachments": [
                {
                    "filename": "notes.txt",
                    "summary": "Notes.",
                }
            ],
        },
    )

    assert response.status_code == 200
    data = response.get_json()

    assert data["ok"] is True
    assert data["guard"]["attachments_present"] is True
    assert data["guard"]["attachment_focused"] is True
    assert data["guard"]["suppress_web"] is True
