from __future__ import annotations

from nova_backend.services.attachment_memory_service import get_attachments_for_session


def build_uploaded_file_context_with_attachments(session_id: str):
    """
    Returns attachment dicts for the given session,
    formatted for project-aware memory injection.
    """
    session_id = str(session_id or "").strip()

    if not session_id:
        return []

    memory = get_attachments_for_session(session_id)

    attachments = []

    for item in memory:
        if not isinstance(item, dict):
            continue

        attachments.append(
            {
                "filename": item.get("filename") or "<unknown>",
                "original_filename": item.get("original_filename") or item.get("filename") or "<unknown>",
                "size": item.get("size") or 0,
                "mime_type": item.get("mime_type") or "",
                "url": item.get("url") or item.get("file_url") or "",
                "file_url": item.get("file_url") or item.get("url") or "",
                "session_id": item.get("session_id") or "",
                "client_session_id": item.get("client_session_id") or "",
                "created_at": item.get("created_at") or "",
            }
        )

    return attachments
