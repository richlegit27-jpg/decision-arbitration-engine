import json


class SessionDetailResponseCacheService:

    def __init__(
        self,
        session_service,
        session_detail_cache_service,
        session_response_cache_service,
        attachment_text_service,
        user_message_already_saved,
        assistant_message_already_saved,
        assistant_same_text_already_saved,
    ):
        self.session_service = session_service
        self.session_detail_cache_service = session_detail_cache_service
        self.session_response_cache_service = session_response_cache_service
        self.attachment_text_service = attachment_text_service
 
    def _user_message_already_saved(
        self,
        messages,
        user_text,
    ):
        for msg in messages:
            if not isinstance(msg, dict):
                continue

            if msg.get("role") != "user":
                continue

            text = str(
                msg.get("text")
                or msg.get("content")
                or ""
            ).strip()

            if text == user_text:
                return True

        return False


    def _assistant_message_already_saved(
        self,
        messages,
        assistant_text,
        assistant_id="",
    ):
        for msg in messages:
            if not isinstance(msg, dict):
                continue

            if msg.get("role") != "assistant":
                continue

            text = str(
                msg.get("text")
                or msg.get("content")
                or ""
            ).strip()

            if text == assistant_text:
                return True

        return False


    def _assistant_same_text_already_saved(
        self,
        messages,
        assistant_text,
    ):
        return self._assistant_message_already_saved(
            messages,
            assistant_text,
        )

    def handle(
        self,
        response,
        request,
        app,
    ):
        try:
            request_path = str(
                getattr(request, "path", "")
                or ""
            )

            request_method = str(
                getattr(request, "method", "")
                or ""
            ).upper()

            if request_method == "POST" and request_path == "/api/chat":

                response_json = response.get_json(silent=True) or {}

                if not isinstance(response_json, dict):
                    return response

                session_id = str(
                    response_json.get("session_id")
                    or response_json.get("active_session_id")
                    or ""
                ).strip()

                if not session_id:
                    return response

                session_obj = response_json.get("session")

                if not isinstance(session_obj, dict):
                    session_obj = {
                        "id": session_id,
                        "title": "Web Fetch",
                        "messages": [],
                        "session_attachments": [],
                        "meta": {},
                    }

                session_obj["id"] = session_id

                messages = session_obj.get("messages")

                if not isinstance(messages, list):
                    messages = []

                payload = request.get_json(silent=True) or {}

                user_text = ""

                if isinstance(payload, dict):
                    user_text = str(
                        payload.get("user_text")
                        or payload.get("message")
                        or payload.get("text")
                        or ""
                    ).strip()

                assistant_message = response_json.get(
                    "assistant_message"
                )

                assistant_text = ""

                if isinstance(assistant_message, dict):
                    assistant_text = str(
                        assistant_message.get("text")
                        or assistant_message.get("content")
                        or ""
                    ).strip()

                (
                    assistant_text,
                    assistant_message,
                    session_obj,
                ) = self.session_response_cache_service.repair_working_recall(
                    session_obj,
                    messages,
                    user_text,
                    assistant_text,
                    assistant_message,
                    session_id,
                )

                if user_text and not self._user_message_already_saved(
                    messages,
                    user_text,
                ):
                    messages.append(
                        {
                            "role": "user",
                            "text": user_text,
                            "content": user_text,
                            "attachments": [],
                            "meta": {
                                "route": "final_session_detail_response_cache",
                                "session_id": session_id,
                            },
                        }
                    )

                assistant_id = ""

                if isinstance(assistant_message, dict):
                    assistant_id = str(
                        assistant_message.get("id")
                        or ""
                    ).strip()

                assistant_already_saved = (
                    self._assistant_message_already_saved(
                        messages,
                        assistant_text=assistant_text,
                        assistant_id=assistant_id,
                    )
                )

                if assistant_text and not assistant_already_saved:
                    assistant_already_saved = (
                        self._assistant_same_text_already_saved(
                            messages,
                            assistant_text=assistant_text,
                        )
                    )

                if assistant_text and not assistant_already_saved:
                    saved_assistant = (
                        assistant_message
                        if isinstance(assistant_message, dict)
                        else {}
                    )

                    saved_assistant = dict(saved_assistant)
                    saved_assistant["role"] = "assistant"
                    saved_assistant["text"] = assistant_text
                    saved_assistant["content"] = assistant_text

                    messages.append(saved_assistant)

                session_obj["messages"] = messages
                session_obj["message_count"] = len(messages)
                session_obj["active_session_id"] = session_id

                session_obj = (
                    self.session_response_cache_service
                    .persist_working_state(
                        session_obj,
                        session_id,
                    )
                )

                cached = (
                    self.session_detail_cache_service
                    .upsert_session_in_store(
                        session_id,
                        session_obj,
                    )
                )

                if isinstance(cached, dict):
                    response_json["session"] = cached

                response_json["session_id"] = session_id
                response_json["active_session_id"] = session_id
                response_json[
                    "final_session_detail_response_cache"
                ] = True

                response.set_data(
                    json.dumps(
                        response_json,
                        ensure_ascii=False,
                    )
                )

                response.headers["Content-Length"] = str(
                    len(response.get_data())
                )

                response.headers["Content-Type"] = (
                    "application/json"
                )

            return response

        except Exception:
            return response