# NOVA_API_CHAT_ATTACHMENT_CONTEXT_CAPTURE_TEST_20260705
"""
API-level attachment context smoke.

This test avoids real provider calls. It monkeypatches likely model-call entrypoints,
captures the messages passed to the model layer, and verifies uploaded file text was
hydrated into backend-owned attachment context.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any


def _fake_model_response(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Captured attachment context successfully.",
                }
            }
        ],
        "usage": {
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
        },
    }


def _install_model_call_captures(monkeypatch, captured: dict[str, Any]) -> None:
    def fake_chat_completions_create(*args: Any, **kwargs: Any) -> dict[str, Any]:
        captured["args"] = args
        captured["kwargs"] = kwargs
        captured["messages"] = kwargs.get("messages")

        if captured["messages"] is None and args:
            for value in args:
                if isinstance(value, list):
                    captured["messages"] = value
                    break

        return _fake_model_response(*args, **kwargs)

    candidates = [
        ("nova_backend.services.model_gateway_service", "chat_completions_create"),
        ("nova_backend.services.chat_turn_pipeline", "chat_completions_create"),
        ("nova_backend.services.chat_turn_pipeline", "_chat_completions_create"),
        ("nova_backend.services.chat_service", "chat_completions_create"),
        ("nova_backend.services.chat_service", "_chat_completions_create"),
    ]

    patched_any = False

    for module_name, attr_name in candidates:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue

        if hasattr(module, attr_name):
            monkeypatch.setattr(module, attr_name, fake_chat_completions_create, raising=False)
            patched_any = True

    # Patch common client/object-style call sites too, when present.
    object_candidates = [
        ("nova_backend.services.chat_turn_pipeline", "client"),
        ("nova_backend.services.chat_turn_pipeline", "openai_client"),
        ("nova_backend.services.chat_service", "client"),
        ("nova_backend.services.chat_service", "openai_client"),
    ]

    class _FakeCompletions:
        @staticmethod
        def create(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return fake_chat_completions_create(*args, **kwargs)

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeClient:
        chat = _FakeChat()

    for module_name, attr_name in object_candidates:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue

        if hasattr(module, attr_name):
            monkeypatch.setattr(module, attr_name, _FakeClient(), raising=False)
            patched_any = True

    assert patched_any, "No model-call entrypoint was available to patch."


def _extract_response_text(data: Any) -> str:
    if isinstance(data, dict):
        parts = []

        for key in (
            "response",
            "reply",
            "message",
            "content",
            "text",
            "assistant",
            "answer",
        ):
            value = data.get(key)

            if isinstance(value, str):
                parts.append(value)

        return "\n".join(parts)

    return ""


def _messages_text(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""

    parts = []

    for message in messages:
        if isinstance(message, dict):
            content = message.get("content")

            if isinstance(content, str):
                parts.append(content)
            else:
                parts.append(str(content))

    return "\n".join(parts)


def test_api_chat_injects_hydrated_upload_text_before_model_call(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    uploads = tmp_path / "uploads"
    uploads.mkdir()

    uploaded_file = uploads / "api-chat-context-smoke.txt"
    uploaded_file.write_text(
        "API chat attachment context marker: purple robot banana.",
        encoding="utf-8",
    )

    captured: dict[str, Any] = {}

    _install_model_call_captures(monkeypatch, captured)

    app_module = importlib.import_module("app")
    flask_app = getattr(app_module, "app")
    client = flask_app.test_client()

    payloads = [
        {
            "session_id": "session_api_chat_attachment_context_001",
            "message": "Summarize the attached file.",
            "attachments": [
                {
                    "filename": "api-chat-context-smoke.txt",
                    "mime_type": "text/plain",
                }
            ],
        },
        {
            "sessionId": "session_api_chat_attachment_context_002",
            "text": "Summarize the attached file.",
            "files": [
                {
                    "name": "api-chat-context-smoke.txt",
                    "type": "text/plain",
                }
            ],
        },
    ]

    final_response = None

    for payload in payloads:
        captured.clear()

        response = client.post("/api/chat", json=payload)
        final_response = response

        if captured.get("messages"):
            break

    assert final_response is not None
    assert final_response.status_code in {200, 201}

    data = final_response.get_json(silent=True) or {}
    response_text = _extract_response_text(data)

    assert "Captured attachment context successfully." in response_text or data.get("ok") is not False

    model_messages_text = _messages_text(captured.get("messages"))

    assert "NOVA_ATTACHMENT_CONTEXT_20260705" in model_messages_text
    assert "api-chat-context-smoke.txt" in model_messages_text
    assert "purple robot banana" in model_messages_text
