import pytest
from pathlib import Path
from app import app, UPLOADS_DIR, persist_attachments_for_session, summarize_attachments_for_session

@pytest.fixture(autouse=True)
def mock_openai(monkeypatch):
    """Prevent real OpenAI calls during pytest"""
    from nova_backend.services.chat_service import ChatService

    def fake_handle(self, *args, **kwargs):
        return {
            "ok": True,
            "assistant_message": {"role": "assistant", "text": "mocked response"},
        }

    monkeypatch.setattr(ChatService, "handle", fake_handle)

def test_attachment_persistence_and_summarize():
    session_id = "pytest_session_001"

    # Create a temp attachment
    attachment_name = "pytest_attachment.txt"
    attachment_bytes = b"Attachment test content"
    temp_path = UPLOADS_DIR / attachment_name
    temp_path.write_bytes(attachment_bytes)

    attachments = [{
        "filename": attachment_name,
        "original_filename": attachment_name,
        "size": len(attachment_bytes),
        "mime_type": "text/plain",
        "url": f"/api/uploads/{attachment_name}",
    }]

    # Persist attachments into session memory
    persist_attachments_for_session(session_id, attachments)

    # Summarize for project-aware context
    summary = summarize_attachments_for_session(session_id)
    assert attachment_name in summary
    assert "Attachment test content" in summary

    # Cleanup
    saved_path = UPLOADS_DIR / attachment_name
    if saved_path.exists():
        saved_path.unlink()