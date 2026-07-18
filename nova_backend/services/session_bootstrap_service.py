from datetime import datetime, timezone
from flask import g, session as flask_session


def _now_iso():
    try:
        return datetime.now(timezone.utc).isoformat()
    except Exception:
        return ""


class SessionBootstrapService:

    def __init__(self, session_service, logger=None):
        self.session_service = session_service
        self.logger = logger


    def ensure_requested_session(
        self,
        session_id,
        title="Mobile Chat",
    ):
        target_session_id = str(session_id or "").strip()

        if not target_session_id:
            return None

        try:
            existing = self.session_service.get_session(
                target_session_id,
            )

            if existing:
                try:
                    store = self.session_service._read_store()

                    if not isinstance(store, dict):
                        store = {
                            "active_session_id": "",
                            "sessions": [],
                        }

                    store["active_session_id"] = target_session_id

                    self.session_service._write_store(store)

                except Exception:
                    if self.logger:
                        self.logger.exception(
                            "[mobile-session-save] failed preserving existing session"
                        )

                return existing

        except Exception:
            if self.logger:
                self.logger.exception(
                    "[mobile-session-save] failed checking existing session"
                )

        owner_id = ""

        try:
            auth_user = getattr(g, "nova_auth_user", None) or {}

            owner_id = str(
                auth_user.get("id")
                or flask_session.get("nova_user_id")
                or ""
            ).strip()

        except Exception:
            owner_id = ""

        now = _now_iso()

        new_session = {
            "id": target_session_id,
            "title": str(title or "Mobile Chat").strip()[:80] or "Mobile Chat",
            "user_id": owner_id,
            "messages": [],
            "pinned": False,
            "created_at": now,
            "updated_at": now,
            "working_state": {
                "active_task": "",
                "current_file": "",
                "current_bug": "",
                "last_success": "",
                "next_move": "",
                "checkpoint": "",
                "updated_at": "",
            },
            "active_execution": None,
        }

        try:
            store = self.session_service._read_store()

            if not isinstance(store, dict):
                store = {
                    "active_session_id": "",
                    "sessions": [],
                }

            sessions = store.get("sessions")

            if not isinstance(sessions, list):
                sessions = []

            sessions = [
                item
                for item in sessions
                if isinstance(item, dict)
                and str(item.get("id") or "").strip()
                != target_session_id
            ]

            sessions.insert(0, new_session)

            store["sessions"] = sessions
            store["active_session_id"] = target_session_id

            self.session_service._write_store(store)

            return new_session

        except Exception:
            if self.logger:
                self.logger.exception(
                    "[mobile-session-save] failed creating requested session"
                )

            return new_session