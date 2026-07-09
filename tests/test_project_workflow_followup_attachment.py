from __future__ import annotations

import uuid

from nova_backend.services.attachment_memory_service import persist_attachments_for_session
from nova_backend.services.project_search_attachment_patch import (
    build_uploaded_file_context_with_attachments,
)


def test_project_workflow_followup_can_reuse_prior_attachment_context() -> None:
    session_id = f"pytest_project_followup_{uuid.uuid4().hex}"

    upload_name = f"pytest_followup_context_{uuid.uuid4().hex}.txt"
    file_url = f"/api/uploads/{upload_name}"

    added = persist_attachments_for_session(
        [
            {
                "filename": upload_name,
                "original_filename": upload_name,
                "size": 444,
                "mime_type": "text/plain",
                "url": file_url,
                "file_url": file_url,
            }
        ],
        session_id=session_id,
        client_session_id=session_id,
    )

    assert added >= 1

    first_context = build_uploaded_file_context_with_attachments(session_id)

    assert any(
        item.get("filename") == upload_name
        for item in first_context
    )

    # Simulates a later follow-up turn like:
    # "continue", "next", "use that file", or "summarize the attachment again"
    followup_context = build_uploaded_file_context_with_attachments(session_id)

    matched = [
        item
        for item in followup_context
        if item.get("file_url") == file_url
    ]

    assert len(matched) == 1

    attachment = matched[0]

    assert attachment["filename"] == upload_name
    assert attachment["original_filename"] == upload_name
    assert attachment["file_url"] == file_url
    assert attachment["url"] == file_url
    assert attachment["session_id"] == session_id
    assert attachment["client_session_id"] == session_id
    assert attachment["size"] == 444
    assert attachment["mime_type"] == "text/plain"


