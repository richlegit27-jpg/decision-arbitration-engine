from __future__ import annotations
import uuid
from pathlib import Path

import pytest
from nova_backend.config import UPLOADS_DIR
from nova_backend.services import attachment_memory_service as attachment_memory

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

def test_attachment_session_unique():
    unique = uuid.uuid4().hex
    session_id = f"pytest_session_{unique}"
    filename = f"pytest_file_{unique}.txt"
    content = f"Attachment content {unique}".encode("utf-8")

    Path(UPLOADS_DIR).mkdir(parents=True, exist_ok=True)
    temp_path = Path(UPLOADS_DIR) / filename
    temp_path.write_bytes(content)

    attachments = [{
        "filename": filename,
        "original_filename": filename,
        "size": len(content),
        "mime_type": "text/plain",
        "url": f"/api/uploads/{filename}",
        "file_url": f"/api/uploads/{filename}",
    }]

    try:
        added = attachment_memory.persist_attachments_for_session(
            attachments,
            session_id=session_id,
            client_session_id=session_id
        )
        assert int(added or 0) == 1

        summary = attachment_memory.summarize_attachments_for_session(
            session_id,
            limit=25,
            client_session_id=session_id
        )
        assert any(
            (item.get("filename") == filename or item.get("original_filename") == filename)
            for item in summary if isinstance(item, dict)
        )

    finally:
        temp_path.unlink(missing_ok=True)

        # Remove memory entry to avoid polluting test runs
        try:
            items = attachment_memory._safe_load()
            cleaned = [
                item for item in items
                if not (
                    isinstance(item, dict)
                    and item.get("session_id") == session_id
                    and item.get("filename") == filename
                )
            ]
            attachment_memory._safe_write(cleaned)
        except Exception:
            pass
