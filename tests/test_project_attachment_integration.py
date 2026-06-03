from __future__ import annotations

import io
import uuid
from pathlib import Path

from app import app
from nova_backend.services.attachment_memory_service import persist_attachments_for_session
from nova_backend.services.project_search_attachment_patch import (
    build_uploaded_file_context_with_attachments,
)

UPLOADS_DIR = Path(r"C:\Users\Owner\nova\runtime\uploads")


def test_project_aware_attachment_flow_from_mobile_upload() -> None:
    session_id = f"pytest_mobile_project_attach_{uuid.uuid4().hex}"
    upload_name = f"pytest_mobile_project_file_{uuid.uuid4().hex}.txt"
    upload_content = b"Mobile project-aware attachment content for memory injection."

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    client = app.test_client()

    # Step 1: Upload the file
    response = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(upload_content), upload_name)},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200

    uploaded_payload = response.get_json() or {}
    file_url = uploaded_payload.get("file_url") or uploaded_payload.get("url")
    assert file_url, "Upload did not return a file URL"

    # Step 2: Persist attachment in session memory
    added = persist_attachments_for_session(
        [
            {
                "filename": upload_name,
                "original_filename": upload_name,
                "size": len(upload_content),
                "mime_type": "text/plain",
                "url": file_url,
                "file_url": file_url,
            }
        ],
        session_id=session_id,
        client_session_id=session_id,
    )
    assert added >= 1

    # Step 3: Retrieve attachments using project-aware context
    attachments = build_uploaded_file_context_with_attachments(session_id)

    # Step 4: Match attachment using actual file_url returned from upload
    matched = [item for item in attachments if item.get("file_url") == file_url]
    assert len(matched) == 1
    attachment = matched[0]

    # Step 5: Validate attachment fields
    assert attachment["filename"] == upload_name
    assert attachment["original_filename"] == upload_name
    assert attachment["size"] == len(upload_content)
    assert attachment["mime_type"] == "text/plain"
    assert attachment["url"] == file_url
    assert attachment["file_url"] == file_url
    assert attachment["session_id"] == session_id
