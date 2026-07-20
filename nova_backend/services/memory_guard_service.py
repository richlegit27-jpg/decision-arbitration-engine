import uuid


class MemoryGuardService:

    def handle_explicit_memory_guard(
        self,
        payload,
        memory_service,
        session_service,
        jsonify,
        app_logger=None,
    ):
        try:
            if not isinstance(payload, dict):
                return None

            raw_user_text = str(
                payload.get("user_text")
                or payload.get("text")
                or payload.get("message")
                or ""
            ).strip()

            lowered = raw_user_text.lower().strip()

            project_brain_memory_concept_markers = (
                "what nova remembers",
                "what nova is actively doing",
                "separate what",
                "separate memory",
                "memory from execution",
                "remembered from active",
            )

            if any(
                marker in lowered
                for marker in project_brain_memory_concept_markers
            ):
                return None

            prefixes = (
                "remember that ",
                "remember this ",
                "remember ",
                "save that ",
                "save this ",
                "store that ",
                "store this ",
                "note that ",
                "memorize that ",
                "add to memory that ",
                "add this to memory ",
            )

            clean = ""

            for prefix in prefixes:
                if lowered.startswith(prefix):
                    clean = raw_user_text[len(prefix):].strip(
                        " .\n\r\t"
                    )
                    break

            if not clean:
                return None

            session_id = str(
                payload.get("session_id")
                or payload.get("client_session_id")
                or ""
            ).strip()

            if not session_id:
                session_id = "session_" + uuid.uuid4().hex

            kind = "fact"

            clean_lc = clean.lower()

            if any(
                marker in clean_lc
                for marker in (
                    "favorite ",
                    "favourite ",
                    "prefer",
                    "from now on",
                    "always",
                    "call me",
                    "my name is",
                )
            ):
                kind = "preference"

            memory_service.add_memory(
                {
                    "text": clean,
                    "kind": kind,
                    "source": "app_explicit_memory_command",
                    "session_id": session_id,
                }
            )

            assistant_text = f"Saved to memory: {clean}"

            user_msg = {
                "role": "user",
                "text": raw_user_text,
                "attachments": [],
                "meta": {},
            }

            assistant_msg = {
                "role": "assistant",
                "text": assistant_text,
                "content": assistant_text,
                "attachments": [],
                "memory_used": [],
                "meta": {
                    "mode": "explicit_memory_command",
                    "route": "memory_save",
                    "save_memory": True,
                    "use_memory": True,
                    "before_request_guard": True,
                },
            }

            try:
                if hasattr(session_service, "add_message"):
                    session_service.add_message(
                        session_id,
                        user_msg,
                    )
                    session_service.add_message(
                        session_id,
                        assistant_msg,
                    )
            except Exception:
                pass

            try:
                session_obj = session_service.get_session(session_id)
            except Exception:
                session_obj = None

            return jsonify(
                {
                    "ok": True,
                    "content": assistant_text,
                    "active_session_id": session_id,
                    "assistant_message": assistant_msg,
                    "debug": {
                        "route": "before_request_explicit_memory_guard",
                        "route_taken": "memory_save",
                    },
                    "session": session_obj
                    or {
                        "id": session_id,
                        "messages": [
                            user_msg,
                            assistant_msg,
                        ],
                    },
                    "session_attachments": [],
                }
            )

        except Exception as exc:
            if app_logger:
                try:
                    app_logger.warning(
                        "[before_request explicit memory guard] failed: %s",
                        exc,
                    )
                except Exception:
                    pass

            return None

    def handle_favorite_recall_guard(
        self,
        payload,
        memory_service,
        session_service,
        jsonify,
        app_logger=None,
    ):
        try:
            return None
        except Exception:
            return None

    def handle_memory_summary_guard(
        self,
        payload,
        memory_service,
        session_service,
        jsonify,
        app_logger=None,
    ):
        try:
            return None
        except Exception:
            return None