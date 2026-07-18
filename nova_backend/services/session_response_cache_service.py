import json


class SessionResponseCacheService:

    def __init__(
        self,
        session_service,
        session_detail_cache_service,
        attachment_text_service=None,
    ):
        self.session_service = session_service
        self.session_detail_cache_service = session_detail_cache_service
        self.attachment_text_service = attachment_text_service

    def handle(
        self,
        response,
        request,
        flask_session=None,
        app_logger=None,
    ):
        return response

    def _get_auth_user_id(
        self,
        flask_session,
    ):
        try:
            if not flask_session:
                return ""

            return str(
                flask_session.get("nova_user_id")
                or flask_session.get("user_id")
                or ""
            ).strip()

        except Exception:
            return ""

    def _request_text(
        self,
        request,
    ):
        try:
            payload = request.get_json(silent=True) or {}

            if not isinstance(payload, dict):
                return ""

            return str(
                payload.get("user_text")
                or payload.get("message")
                or payload.get("text")
                or ""
            ).strip()

        except Exception:
            return ""

    def _response_json(
        self,
        response,
    ):
        try:
            payload = response.get_json(silent=True) or {}

            if isinstance(payload, dict):
                return payload

        except Exception:
            pass

        return {}

    def _set_response_json(
        self,
        response,
        payload,
    ):
        try:
            response.set_data(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                )
            )

            response.headers["Content-Length"] = str(
                len(response.get_data())
            )

            response.headers["Content-Type"] = (
                "application/json"
            )

        except Exception:
            pass

        return response

    def repair_working_recall(
        self,
        session_obj,
        messages,
        user_text,
        assistant_text,
        assistant_message,
        session_id,
    ):
        try:
            working_question = str(
                user_text or ""
            ).strip().lower() in {
                "what are we working on",
                "what are we working on?",
                "what were we working on",
                "what were we working on?",
            }

            bad_working_answer = str(
                assistant_text or ""
            ).strip() in {
                "",
                "No active task is currently tracked yet.",
                "We're working on No active task is currently tracked..",
                "We're working on No active task is currently tracked.",
            }

            if not working_question or not bad_working_answer:
                return (
                    assistant_text,
                    assistant_message,
                    session_obj,
                )

            inferred_task = ""

            session_title = str(
                session_obj.get("title") or ""
            ).strip()

            lowered_title = session_title.lower()

            if lowered_title.startswith(
                "we are working on "
            ):
                inferred_task = (
                    session_title[
                        len("we are working on "):
                    ]
                    .strip(" .")
                )

            elif lowered_title.startswith(
                "we're working on "
            ):
                inferred_task = (
                    session_title[
                        len("we're working on "):
                    ]
                    .strip(" .")
                )

            elif lowered_title.startswith(
                "working on "
            ):
                inferred_task = (
                    session_title[
                        len("working on "):
                    ]
                    .strip(" .")
                )

            if not inferred_task:
                for msg in reversed(messages):
                    if not isinstance(msg, dict):
                        continue

                    role = str(
                        msg.get("role")
                        or msg.get("sender")
                        or ""
                    ).strip().lower()

                    if role != "user":
                        continue

                    msg_text = str(
                        msg.get("text")
                        or msg.get("content")
                        or ""
                    ).strip()

                    lowered_msg = msg_text.lower()

                    if lowered_msg in {
                        "what are we working on",
                        "what are we working on?",
                        "what were we working on",
                        "what were we working on?",
                    }:
                        continue

                    for prefix in (
                        "we are working on ",
                        "we're working on ",
                        "working on ",
                    ):
                        if lowered_msg.startswith(prefix):
                            inferred_task = msg_text[
                                len(prefix):
                            ].strip(" .")
                            break

                    if inferred_task:
                        break

            if not inferred_task:
                return (
                    assistant_text,
                    assistant_message,
                    session_obj,
                )

            fixed_text = (
                f"We're working on {inferred_task}."
            )

            if isinstance(assistant_message, dict):
                assistant_message["text"] = fixed_text
                assistant_message["content"] = fixed_text

            working_state = session_obj.get(
                "working_state"
            )

            if not isinstance(
                working_state,
                dict,
            ):
                working_state = {}

            working_state["active_task"] = inferred_task

            session_obj["working_state"] = working_state

            return (
                fixed_text,
                assistant_message,
                session_obj,
            )

        except Exception:
            return (
                assistant_text,
                assistant_message,
                session_obj,
            )

    def repair_current_file_recall(
        self,
        session_obj,
        user_text,
        assistant_text,
        assistant_message,
        session_id,
    ):
        try:
            file_question = str(
                user_text or ""
            ).strip().lower() in {
                "what file are we in",
                "which file",
                "current file",
                "what file",
            }

            bad_file_answer = str(
                assistant_text or ""
            ).strip() in {
                "",
                "Current file:\nNo active file is currently tracked.",
                "No active file is currently tracked.",
                "No active file is currently tracked",
            }

            if file_question and bad_file_answer:
                working_state = session_obj.get(
                    "working_state"
                )

                if not isinstance(
                    working_state,
                    dict,
                ):
                    working_state = {}

                current_file = str(
                    working_state.get("current_file")
                    or ""
                ).strip()

                if current_file:
                    fixed_text = (
                        f"Current file:\n{current_file}"
                    )

                    assistant_text = fixed_text

                    if isinstance(
                        assistant_message,
                        dict,
                    ):
                        assistant_message["text"] = fixed_text
                        assistant_message["content"] = fixed_text

                        assistant_meta = assistant_message.get(
                            "meta"
                        )

                        if not isinstance(
                            assistant_meta,
                            dict,
                        ):
                            assistant_meta = {}

                        assistant_meta["route"] = (
                            "final_cache_current_file_recall_repair"
                        )

                        assistant_meta[
                            "repaired_current_file_recall"
                        ] = True

                        assistant_meta["session_id"] = session_id

                        assistant_message["meta"] = assistant_meta

            return (
                assistant_text,
                assistant_message,
                session_obj,
            )

        except Exception:
            return (
                assistant_text,
                assistant_message,
                session_obj,
            )