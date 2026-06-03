from __future__ import annotations

from pathlib import Path
import uuid

from app import app, UPLOADS_DIR


def test_mobile_sync_upload_and_session():
    session_id = f"pytest_mobile_{uuid.uuid4().hex}"
    upload_name = f"pytest_file_{uuid.uuid4().hex}.txt"
    upload_content = b"Mobile sync test content"

    Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)

    client = app.test_client()

    response = client.post(
        "/api/upload",
        data={
            "file": (
                __import__("io").BytesIO(upload_content),
                upload_name,
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload["ok"] is True
    assert payload["original_filename"] == upload_name
    assert payload["filename"]
    assert payload["file_url"].startswith("/api/uploads/")
    assert payload["url"].startswith("/api/uploads/")
    assert payload["mime_type"]
    assert int(payload["size"]) == len(upload_content)

    saved_path = Path(UPLOADS_DIR) / payload["filename"]

    try:
        assert saved_path.exists()
        assert saved_path.read_bytes() == upload_content

        chat_response = client.post(
            "/api/chat",
            json={
                "user_text": "Check attachments",
                "session_id": session_id,
                "attachments": [payload],
            },
        )

        assert chat_response.status_code == 200

        chat_payload = chat_response.get_json()

        assert chat_payload["ok"] is True
        assert isinstance(chat_payload.get("assistant_message"), dict)
        assert str(chat_payload["assistant_message"].get("text") or "").strip()

        assert "session_attachments" in chat_payload
        assert "attachment_debug" in chat_payload

        debug = chat_payload.get("attachment_debug") or {}
        assert debug.get("requested_session_id") == session_id
        assert int(debug.get("session_attachments_count") or 0) >= 1

        session_attachments = chat_payload.get("session_attachments") or []
        assert any(
            (
                item.get("filename") == payload["filename"]
                or item.get("original_filename") == upload_name
            )
            for item in session_attachments
            if isinstance(item, dict)
        )

    finally:
        saved_path.unlink(missing_ok=True)
