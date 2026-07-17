import json
import os
from datetime import datetime


class SessionHistoryService:

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.cache = {}


    def session_store_path(self):
        return os.path.join(
            self.base_dir,
            "data",
            "nova_sessions.json",
        )


    def load_sessions_store(self):
        try:
            path_value = self.session_store_path()

            if os.path.exists(path_value):
                with open(
                    path_value,
                    "r",
                    encoding="utf-8",
                ) as handle:
                    data = json.load(handle) or {}

                    if isinstance(data, dict):
                        return data

        except Exception:
            pass

        return {}


    def save_sessions_store(self, store):
        try:
            path_value = self.session_store_path()

            os.makedirs(
                os.path.dirname(path_value),
                exist_ok=True,
            )

            with open(
                path_value,
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    store,
                    handle,
                    ensure_ascii=False,
                    indent=2,
                )

            return True

        except Exception:
            return False

    def find_session_in_store(
        self,
        store,
        session_id,
    ):
        sessions = store.get("sessions")

        if isinstance(sessions, dict):
            item = sessions.get(session_id)

            if isinstance(item, dict):
                return item

        if isinstance(sessions, list):
            for item in sessions:
                if (
                    isinstance(item, dict)
                    and str(item.get("id") or "") == session_id
                ):
                    return item

        return None


    def upsert_session_in_store(
        self,
        session_id,
        session_obj,
    ):
        if not session_id:
            return None

        if not isinstance(session_obj, dict):
            return None

        store = self.load_sessions_store()

        sessions = store.get("sessions")

        if not isinstance(sessions, list):
            sessions = []

        existing = None

        for item in sessions:
            if (
                isinstance(item, dict)
                and str(item.get("id") or "") == session_id
            ):
                existing = item
                break

        if existing is None:
            existing = {
                "id": session_id,
                "title": str(
                    session_obj.get("title")
                    or "Web Fetch"
                )[:80],
                "messages": [],
                "session_attachments": [],
                "meta": {},
            }

            sessions.insert(
                0,
                existing,
            )

        for key, value in session_obj.items():

            if key == "messages":
                continue

            existing[key] = value

        messages = session_obj.get("messages")

        if not isinstance(messages, list):
            messages = (
                existing.get("messages")
                if isinstance(
                    existing.get("messages"),
                    list,
                )
                else []
            )

        existing["messages"] = messages
        existing["message_count"] = len(messages)
        existing["active_session_id"] = session_id

        try:
            existing["updated_at"] = (
                datetime.utcnow().isoformat()
                + "Z"
            )
        except Exception:
            pass

        meta = existing.get("meta")

        if not isinstance(meta, dict):
            meta = {}
            existing["meta"] = meta

        meta[
            "final_session_detail_response_cache"
        ] = True

        store["sessions"] = sessions
        store["active_session_id"] = session_id

        self.save_sessions_store(store)

        self.cache[session_id] = existing

        return existing

    def history_sid(
        self,
        session,
    ):
        if not isinstance(session, dict):
            return ""

        return str(
            session.get("id")
            or ""
        ).strip()


    def history_title(
        self,
        session,
    ):
        if not isinstance(session, dict):
            return "Untitled Session"

        return str(
            session.get("title")
            or "Untitled Session"
        ).strip()


    def history_messages(
        self,
        session,
    ):
        if not isinstance(session, dict):
            return []

        messages = session.get("messages")

        if isinstance(messages, list):
            return messages

        return []


    def history_msg_text(
        self,
        message,
    ):
        if not isinstance(message, dict):
            return ""

        return str(
            message.get("text")
            or message.get("content")
            or ""
        ).strip()


    def history_msg_role(
        self,
        message,
    ):
        if not isinstance(message, dict):
            return ""

        return str(
            message.get("role")
            or message.get("sender")
            or ""
        ).strip()