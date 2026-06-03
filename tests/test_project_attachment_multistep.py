from __future__ import annotations

import uuid

from nova_backend.services.attachment_memory_service import persist_attachments_for_session
from nova_backend.services.project_search_attachment_patch import (
    build_uploaded_file_context_with_attachments,
)


def test_project_aware_attachment_multi_step_session_memory() -> None:
    session_id = f"pytest_project_multi_attach_{uuid.uuid4().hex}"
    other_session_id = f"pytest_project_multi_attach_other_{uuid.uuid4().hex}"

    first_name = f"pytest_project_step_one_{uuid.uuid4().hex}.txt"
    second_name = f"pytest_project_step_two_{uuid.uuid4().hex}.txt"
    isolated_name = f"pytest_project_isolated_{uuid.uuid4().hex}.txt"

    first_url = f"/api/uploads/{first_name}"
    second_url = f"/api/uploads/{second_name}"
    isolated_url = f"/api/uploads/{isolated_name}"

    added_first = persist_attachments_for_session(
        [
            {
                "filename": first_name,
                "original_filename": first_name,
                "size": 111,
                "mime_type": "text/plain",
                "url": first_url,
                "file_url": first_url,
            }
        ],
        session_id=session_id,
        client_session_id=session_id,
    )

    added_second = persist_attachments_for_session(
        [
            {
                "filename": second_name,
                "original_filename": second_name,
                "size": 222,
                "mime_type": "text/plain",
                "url": second_url,
                "file_url": second_url,
            }
        ],
        session_id=session_id,
        client_session_id=session_id,
    )

    added_isolated = persist_attachments_for_session(
        [
            {
                "filename": isolated_name,
                "original_filename": isolated_name,
                "size": 333,
                "mime_type": "text/plain",
                "url": isolated_url,
                "file_url": isolated_url,
            }
        ],
        session_id=other_session_id,
        client_session_id=other_session_id,
    )

    assert added_first >= 1
    assert added_second >= 1
    assert added_isolated >= 1

    attachments = build_uploaded_file_context_with_attachments(session_id)

    filenames = {item.get("filename") for item in attachments}
    file_urls = {item.get("file_url") for item in attachments}

    assert first_name in filenames
    assert second_name in filenames
    assert isolated_name not in filenames

    assert first_url in file_urls
    assert second_url in file_urls
    assert isolated_url not in file_urls

    first_match = [
        item
        for item in attachments
        if item.get("filename") == first_name
    ][0]

    second_match = [
        item
        for item in attachments
        if item.get("filename") == second_name
    ][0]

    assert first_match["session_id"] == session_id
    assert second_match["session_id"] == session_id
    assert first_match["size"] == 111
    assert second_match["size"] == 222
