from datetime import datetime, timezone


def _now_iso():
    try:
        return datetime.now(timezone.utc).isoformat()
    except Exception:
        return ""


class MobileExchangeService:

    def __init__(self, session_service):
        self.session_service = session_service


    def direct_save_mobile_exchange(
        self,
        session_id,
        user_text,
        assistant_text,
        attachments=None,
        route="mobile_attachment",
        clean_text=None,
        logger=None,
    ):
        target_session_id = str(session_id or "").strip()

        if not target_session_id:
            return False

        now = _now_iso()

        try:
            session = self.session_service.get_session(
                target_session_id
            )

            if not isinstance(session, dict):
                session = self.session_service.create_session(
                    title=user_text or "Mobile Chat",
                )

                target_session_id = session.get("id")

            visible_text = (
                clean_text(user_text)
                if callable(clean_text)
                else str(user_text or "")
            )

            self.session_service.append_message(
                target_session_id,
                {
                    "role": "user",
                    "text": visible_text,
                    "attachments": attachments or [],
                    "created_at": now,
                    "meta": {
                        "route": route,
                    },
                },
            )

            self.session_service.append_message(
                target_session_id,
                {
                    "role": "assistant",
                    "text": str(assistant_text or "").strip(),
                    "attachments": attachments or [],
                    "created_at": now,
                    "meta": {
                        "route": route,
                    },
                },
            )

            self.session_service.set_active(
                target_session_id
            )

            return True

        except Exception:
            if logger:
                logger.exception(
                    "[direct-mobile-session-save] failed"
                )

            return False


    def save_mobile_exchange(
        self,
        session_id,
        user_text,
        assistant_text,
        attachments=None,
        route="mobile_attachment",
        ensure_session=None,
        clean_text=None,
        logger=None,
    ):
        target_session_id = str(session_id or "").strip()

        if not target_session_id:
            return False

        if callable(ensure_session):
            ensure_session(
                target_session_id,
                title=user_text or "Mobile Chat",
            )

        try:
            visible_text = (
                clean_text(user_text)
                if callable(clean_text)
                else str(user_text or "")
            )

            self.session_service.append_message(
                target_session_id,
                {
                    "role": "user",
                    "text": visible_text,
                    "attachments": attachments or [],
                    "meta": {
                        "route": route,
                    },
                },
            )

            self.session_service.append_message(
                target_session_id,
                {
                    "role": "assistant",
                    "text": str(assistant_text or "").strip(),
                    "attachments": attachments or [],
                    "meta": {
                        "route": route,
                    },
                },
            )

            sessions = self.session_service.get_all()

            self.session_service.save(
                sessions,
                active=target_session_id,
            )

            return True

        except Exception:
            if logger:
                logger.exception(
                    "[mobile-session-save] failed appending mobile exchange"
                )

            return False