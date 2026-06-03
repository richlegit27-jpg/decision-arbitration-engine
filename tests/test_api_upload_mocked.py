# notepad C:\Users\Owner\nova\tests\test_api_upload_mocked.py

import pytest
from pathlib import Path
from app import app, UPLOADS_DIR

@pytest.fixture(autouse=True)
def mock_openai(monkeypatch):
    """
    Auto-mock the chat_service.handle() to prevent real OpenAI calls during pytest.
    """
    from nova_backend.services.chat_service import ChatService

    def fake_handle(self, *args, **kwargs):
        return {
            "ok": True,
            "assistant_message": {"role": "assistant", "text": "mocked response"},
        }

    monkeypatch.setattr(ChatService, "handle", fake_handle)

def test_file_upload_flask():
    # Prepare a small in-memory file
    upload_name = "pytest_mock_upload.txt"
    upload_bytes = b"hello world"

    client = app.test_client()

    response = client.post(
        "/api/upload",
        data={
            "file": (__import__("io").BytesIO(upload_bytes), upload_name),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["original_filename"] == upload_name
    assert "filename" in payload
    assert payload["url"].startswith("/api/uploads/")
    assert payload["file_url"].startswith("/api/uploads/")
    assert payload["mime_type"]
    assert int(payload["size"]) == len(upload_bytes)

    # Verify file saved correctly
    saved_path = Path(UPLOADS_DIR) / payload["filename"]
    assert saved_path.exists()
    assert saved_path.read_bytes() == upload_bytes

    # Cleanup
    saved_path.unlink(missing_ok=True)