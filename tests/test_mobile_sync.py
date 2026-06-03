from __future__ import annotations
from pathlib import Path
import uuid
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

def test_mobile_sync_upload_and_session():
    # Unique identifiers to avoid collisions
    session_id = f"pytest_mobile_{uuid.uuid4().hex}"
    upload_name = f"pytest_file_{uuid.uuid4().hex}.txt"
    upload_content = b"Mobile sync test content"

    # Ensure upload directory exists
    Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
    temp_file = Path(UPLOADS_DIR) / upload_name
    temp_file.write_bytes(upload_content)

    client = app.test_client()

    # Simulate file upload
    response = client.post(
        "/api/upload",
        data={"file": (__import__("io").BytesIO(upload_content), upload_name)},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    saved_filename = payload["filename"]
    saved_path = Path(UPLOADS_DIR) / saved_filename
    assert saved_path.exists()
    assert saved_path.read_bytes() == upload_content

    # Simulate session switch and chat with attachment injection
    response2 = client.post(
        "/api/chat",
        json={
            "user_text": "Check attachments",
            "session_id": session_id,
            "attachments": [payload],
        },
    )

    assert response2.status_code == 200
    chat_payload = response2.get_json()
    assert chat_payload["ok"] is True
    assert "mocked response" in chat_payload["assistant_message"]["text"]

    # Cleanup
    saved_path.unlink(missing_ok=True)
    temp_file.unlink(missing_ok=True)
