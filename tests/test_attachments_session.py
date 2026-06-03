from __future__ import annotations

from pathlib import Path

from nova_backend.config import UPLOADS_DIR
from nova_backend.services.attachment_memory_service import (
    persist_attachments_for_session,
    summarize_attachments_for_session,
)


def test_attachment_persistence_and_summarize():
    session_id = "pytest_attachment_session_001"

    attachment_name = "pytest_attachment.txt"
    attachment_bytes = b"Attachment test content"
    temp_path = Path(UPLOADS_DIR) / attachment_name
    temp_path.write_bytes(attachment_bytes)

    attachments = [
        {
            "filename": attachment_name,
            "original_filename": attachment_name,
            "size": len(attachment_bytes),
            "mime_type": "text/plain",
            "url": f"/api/uploads/{attachment_name}",
            "file_url": f"/api/uploads/{attachment_name}",
        }
    ]

    try:
        added = persist_attachments_for_session(
            attachments,
            session_id=session_id,
            client_session_id=session_id,
        )

        assert int(added or 0) >= 1

        summary = summarize_attachments_for_session(
            session_id,
            limit=25,
            client_session_id=session_id,
        )

        assert isinstance(summary, list)
        assert any(
            (
                item.get("filename") == attachment_name
                or item.get("original_filename") == attachment_name
            )
            for item in summary
            if isinstance(item, dict)
        )

    finally:
        temp_path.unlink(missing_ok=True)
