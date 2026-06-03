from __future__ import annotations

import uuid

from app import app


def test_chat_followup_reuses_prior_attachment_context(monkeypatch) -> None:
    session_id = f"pytest_chat_followup_{uuid.uuid4().hex}"
    upload_name = f"pytest_chat_followup_file_{uuid.uuid4().hex}.txt"
    file_url = f"/api/uploads/{upload_name}"

    client = app.test_client()

    first_payload = {
        "session_id": session_id,
        "user_text": "Use this uploaded file for the next step.",
        "attachments": [
            {
                "filename": upload_name,
                "original_filename": upload_name,
                "size": 555,
                "mime_type": "text/plain",
                "url": file_url,
                "file_url": file_url,
            }
        ],
    }

    first_response = client.post(
        "/api/chat",
        json=first_payload,
    )

    assert first_response.status_code == 200

    second_payload = {
        "session_id": session_id,
        "user_text": "Continue using that file.",
        "attachments": [],
    }

    second_response = client.post(
        "/api/chat",
        json=second_payload,
    )

    assert second_response.status_code == 200

    data = second_response.get_json() or {}

    assert data.get("ok") is True

    text = str(
        (data.get("assistant_message") or {}).get("text")
        or data.get("text")
        or ""
    )

    assert text
