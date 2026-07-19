from __future__ import annotations

from nova_backend.services.attachment_memory_service import (
    persist_attachments_for_session,
    get_attachments_for_session,
)


class ChatAttachmentMemoryService:

    def persist(
        self,
        attachments,
        session_id,
        requested_session_id,
        logger=None,
    ):
        if not attachments:
            return 0

        try:
            count = persist_attachments_for_session(
                attachments,
                session_id=session_id,
                client_session_id=requested_session_id,
            )

            if logger:
                logger.info(
                    "[api_chat] persisted attachment memory count=%s session_id=%s",
                    count,
                    session_id,
                )

            return count

        except Exception:
            if logger:
                logger.exception(
                    "[api_chat] failed to persist attachment memory"
                )

            return 0

    def summarize(
        self,
        session_id,
        requested_session_id,
        limit=25,
    ):
        try:
            return get_attachments_for_session(
                session_id,
                limit=limit,
                client_session_id=requested_session_id,
            )

        except Exception:
            return []