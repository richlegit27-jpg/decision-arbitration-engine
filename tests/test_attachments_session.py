from __future__ import annotations

import uuid
from pathlib import Path

from nova_backend.config import UPLOADS_DIR
from nova_backend.services import attachment_memory_service as attachment_memory


def test_attachment_persistence_and_summarize_unique_item():
    unique = uuid.uuid4().hex
    session_id = f"pytest_attachment_session_{unique}"
    attachment_name = f"pytest_attachment_{unique}.txt"
    attachment_bytes = f"Attachment test content {unique}".encode("utf-8")

    uploads_dir = Path(UPLOADS_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    temp_path = uploads_dir / attachment_name
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
        added = attachment_memory.persist_attachments_for_session(
            attachments,
            session_id=session_id,
            client_session_id=session_id,
        )

        assert int(added or 0) == 1

        summary = attachment_memory.summarize_attachments_for_session(
            session_id,
            limit=25,
            client_session_id=session_id,
        )

        assert isinstance(summary, list)
        assert any(
            (
                item.get("filename") == attachment_name
                and item.get("session_id") == session_id
            )
            for item in summary
            if isinstance(item, dict)
        )

    finally:
        temp_path.unlink(missing_ok=True)

        # Keep the test from permanently polluting attachment memory.
        try:
            items = attachment_memory._safe_load()
            cleaned = [
                item
                for item in items
                if not (
                    isinstance(item, dict)
                    and item.get("session_id") == session_id
                    and item.get("filename") == attachment_name
                )
            ]
            attachment_memory._safe_write(cleaned)
        except Exception:
            pass
