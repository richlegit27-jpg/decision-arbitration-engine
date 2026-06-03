from __future__ import annotations
import uuid
from pathlib import Path

import pytest
from app import app, UPLOADS_DIR

@pytest.fixture(autouse=True)
def mock_openai(monkeypatch):
    """Prevent real OpenAI calls during pytest"""
    from nova_backend.services.chat_service import ChatService
    monkeypatch.setattr(
        ChatService,
        "handle",
        lambda self, *args, **kwargs: {
            "ok": True,
            "assistant_message": {"role": "assistant", "text": "mocked response"},
        },
    )

def test_frontend_mobile_attachment_integration():
    # Unique session and file
    session_id = f"pytest_mobile_frontend_{uuid.uuid4().hex}"
    upload_name = f"pytest_frontend_file_{uuid.uuid4().hex}.txt"
    upload_content = b"Frontend mobile integration content"

    # Prepare upload directory
    Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
    temp_path = Path(UPLOADS_DIR) / upload_name
    temp_path.write_bytes(upload_content)

    client = app.test_client()

    # Step 1: upload file
    response = client.post(
        "/api/upload",
        data={"file": (__import__("io").BytesIO(upload_content), upload_name)},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["filename"]
    assert payload["file_url"].startswith("/api/uploads/")
    assert payload["url"].startswith("/api/uploads/")

    saved_path = Path(UPLOADS_DIR) / payload["filename"]

    try:
        # Step 2: simulate mobile chat with attachment injection
        chat_response = client.post(
            "/api/chat",
            json={
                "user_text": "Verify attachments in mobile session",
                "session_id": session_id,
                "attachments": [payload],
            },
        )

        assert chat_response.status_code == 200
        chat_payload = chat_response.get_json()
        assert chat_payload["ok"] is True
        assert isinstance(chat_payload.get("assistant_message"), dict)
        assert chat_payload["assistant_message"].get("text")

        # Step 3: check attachment injection
        assert "session_attachments" in chat_payload
        assert "attachment_debug" in chat_payload
        debug = chat_payload["attachment_debug"]
        assert debug.get("requested_session_id") == session_id
        assert int(debug.get("session_attachments_count") or 0) >= 1

        session_attachments = chat_payload["session_attachments"]
        assert any(
            (item.get("filename") == payload["filename"] or item.get("original_filename") == upload_name)
            for item in session_attachments if isinstance(item, dict)
        )

    finally:
        # Cleanup files
        temp_path.unlink(missing_ok=True)
        saved_path.unlink(missing_ok=True)
