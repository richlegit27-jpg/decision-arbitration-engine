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
                    session_service.add_message(session_id, user_msg)
                    session_service.add_message(session_id, assistant_msg)
            except Exception:
                pass

            try:
                session_obj = session_service.get_session(session_id)
            except Exception:
                session_obj = None

            return jsonify({
                "ok": True,
                "active_session_id": session_id,
                "assistant_message": assistant_msg,
                "debug": {
                    "route": "before_request_explicit_memory_guard",
                    "route_taken": "memory_save",
                },
                "session": session_obj or {
                    "id": session_id,
                    "messages": [user_msg, assistant_msg],
                },
                "session_attachments": [],
            })

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
            raw_user_text = str(
                payload.get("user_text")
                or payload.get("text")
                or payload.get("message")
                or ""
            ).strip()

            clean_question = " ".join(
                raw_user_text.lower()
                .replace("?", " ")
                .split()
            )

            prefix = "what is my favorite "

            if not clean_question.startswith(prefix):
                return None

            favorite_key = clean_question[len(prefix):].strip()

            if not favorite_key:
                return None

            target_start = f"my favorite {favorite_key} is "

            best_item = None

            for item in memory_service.all() or []:
                if not isinstance(item, dict):
                    continue

                item_text = str(
                    item.get("text") or ""
                ).strip()

                if item_text.lower().startswith(target_start):
                    best_item = item
                    break

            if not best_item:
                return None

            item_text = str(
                best_item.get("text") or ""
            ).strip()

            answer_value = item_text[len(target_start):].strip()

            if not answer_value:
                return None

            session_id = str(
                payload.get("session_id")
                or payload.get("client_session_id")
                or ""
            ).strip()

            if not session_id:
                session_id = "session_" + uuid.uuid4().hex

            assistant_text = (
                f"Your favorite {favorite_key} is {answer_value}."
            )

            user_msg = {
                "role": "user",
                "text": raw_user_text,
                "attachments": [],
                "meta": {},
            }

            assistant_msg = {
                "role": "assistant",
                "text": assistant_text,
                "attachments": [],
                "memory_used": [best_item],
                "meta": {
                    "mode": "memory_recall",
                    "route": "favorite_memory_recall",
                    "before_request_guard": True,
                    "memory_used_count": 1,
                },
            }

            try:
                if hasattr(session_service, "add_message"):
                    session_service.add_message(session_id, user_msg)
                    session_service.add_message(session_id, assistant_msg)
            except Exception:
                pass

            try:
                session_obj = session_service.get_session(session_id)
            except Exception:
                session_obj = None

            return jsonify({
                "ok": True,
                "active_session_id": session_id,
                "assistant_message": assistant_msg,
                "debug": {
                    "route": "before_request_favorite_recall_guard",
                    "route_taken": "favorite_memory_recall",
                },
                "session": session_obj or {
                    "id": session_id,
                    "messages": [user_msg, assistant_msg],
                },
                "session_attachments": [],
            })

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
            raw_user_text = str(
                payload.get("user_text")
                or payload.get("text")
                or payload.get("message")
                or ""
            ).strip()

            clean_question = " ".join(
                raw_user_text.lower()
                .replace("?", " ")
                .split()
            )

            summary_questions = {
                "what do you remember about me",
                "what memory do you have",
                "what memories do you have",
                "show my memories",
                "show me my memories",
                "list my memories",
                "what do you know about me",
                "what have you remembered",
                "what have you saved about me",
            }

            if clean_question not in summary_questions:
                return None

            memories = memory_service.all() or []

            clean_memories = []
            seen = set()

            for item in memories:
                if not isinstance(item, dict):
                    continue

                text_value = str(
                    item.get("text") or ""
                ).strip()

                if not text_value:
                    continue

                key = text_value.lower()

                if key in seen:
                    continue

                seen.add(key)

                clean_memories.append(item)

            if clean_memories:
                lines = [
                    f"- [{x.get('kind') or 'memory'}] {x.get('text')}"
                    for x in clean_memories[:12]
                ]

                assistant_text = (
                    "Here is what I remember:\n\n"
                    + "\n".join(lines)
                )
            else:
                assistant_text = (
                    "I do not have any saved memories yet."
                )

            session_id = str(
                payload.get("session_id")
                or payload.get("client_session_id")
                or ""
            ).strip()

            if not session_id:
                session_id = "session_" + uuid.uuid4().hex

            user_msg = {
                "role": "user",
                "text": raw_user_text,
                "attachments": [],
                "meta": {},
            }

            assistant_msg = {
                "role": "assistant",
                "text": assistant_text,
                "attachments": [],
                "memory_used": clean_memories[:12],
                "meta": {
                    "mode": "memory_summary",
                    "route": "memory_summary_recall",
                    "before_request_guard": True,
                    "memory_used_count": len(clean_memories[:12]),
                },
            }

            try:
                if hasattr(session_service, "add_message"):
                    session_service.add_message(session_id, user_msg)
                    session_service.add_message(session_id, assistant_msg)
            except Exception:
                pass

            try:
                session_obj = session_service.get_session(session_id)
            except Exception:
                session_obj = None

            return jsonify({
                "ok": True,
                "active_session_id": session_id,
                "assistant_message": assistant_msg,
                "debug": {
                    "route": "before_request_memory_summary_guard",
                    "route_taken": "memory_summary_recall",
                },
                "session": session_obj or {
                    "id": session_id,
                    "messages": [user_msg, assistant_msg],
                },
                "session_attachments": [],
            })

        except Exception:
            return None