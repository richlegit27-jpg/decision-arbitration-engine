import json


class WebFetchBridgeService:

    def __init__(
        self,
        session_service,
    ):
        self.session_service = session_service

    def handle(
        self,
        response,
        payload,
    ):
        try:
            if getattr(response, "status_code", 500) >= 400:
                return response

            if not isinstance(payload, dict):
                return response

            target_session_id = str(
                payload.get("session_id")
                or payload.get("client_session_id")
                or payload.get("active_session_id")
                or ""
            ).strip()

            if not target_session_id:
                return response

            user_text = str(
                payload.get("user_text")
                or payload.get("message")
                or payload.get("text")
                or ""
            ).strip()

            if not user_text:
                return response

            response_json = response.get_json(silent=True) or {}

            if not isinstance(response_json, dict):
                return response

            if not response_json.get("ok", False):
                return response

            debug = (
                response_json.get("debug")
                if isinstance(response_json.get("debug"), dict)
                else {}
            )

            assistant_message = response_json.get(
                "assistant_message"
            )

            assistant_meta = {}

            if (
                isinstance(assistant_message, dict)
                and isinstance(
                    assistant_message.get("meta"),
                    dict,
                )
            ):
                assistant_meta.update(
                    assistant_message.get("meta")
                    or {}
                )

            route_text = " ".join(
                [
                    str(debug.get("route") or ""),
                    str(debug.get("route_taken") or ""),
                    str(assistant_meta.get("route") or ""),
                    str(assistant_meta.get("strategy") or ""),
                ]
            ).lower()

            is_web_fetch = (
                "web_fetch" in route_text
                or assistant_meta.get("route") == "web"
                or assistant_meta.get("strategy") == "web_fetch"
                or isinstance(
                    assistant_meta.get("sources"),
                    list,
                )
                or isinstance(
                    assistant_meta.get("source_urls"),
                    list,
                )
            )

            if not is_web_fetch:
                return response

            assistant_text = ""
            assistant_attachments = []

            if isinstance(assistant_message, dict):

                assistant_text = str(
                    assistant_message.get("text")
                    or assistant_message.get("content")
                    or ""
                ).strip()

                if isinstance(
                    assistant_message.get("attachments"),
                    list,
                ):
                    assistant_attachments = (
                        assistant_message.get("attachments")
                        or []
                    )

            if not assistant_text:
                assistant_text = str(
                    response_json.get("text")
                    or response_json.get("response")
                    or response_json.get("answer")
                    or ""
                ).strip()

            if not assistant_text:
                return response

            bridge_meta = dict(assistant_meta)

            bridge_meta.update(
                {
                    "route": (
                        "web_fetch_requested_session_bridge_safe"
                    ),
                    "target_session_id": target_session_id,
                    "response_active_session_id": str(
                        response_json.get(
                            "active_session_id"
                        )
                        or ""
                    ),
                    "response_session_id": str(
                        response_json.get(
                            "session_id"
                        )
                        or ""
                    ),
                    "web_fetch_session_bridge": True,
                }
            )

            user_message = {
                "role": "user",
                "text": user_text,
                "content": user_text,
                "attachments": (
                    payload.get("attachments")
                    if isinstance(
                        payload.get("attachments"),
                        list,
                    )
                    else []
                ),
                "meta": {
                    "route": (
                        "web_fetch_requested_session_bridge_safe"
                    ),
                    "target_session_id": target_session_id,
                },
            }

            assistant_saved = {
                "role": "assistant",
                "text": assistant_text,
                "content": assistant_text,
                "attachments": assistant_attachments,
                "meta": bridge_meta,
            }

            try:
                final_session = (
                    self.session_service.get_session(
                        target_session_id
                    )
                )
            except Exception:
                final_session = None

            if not final_session:
                final_session = {
                    "id": target_session_id,
                    "messages": [
                        user_message,
                        assistant_saved,
                    ],
                    "session_attachments": [],
                    "meta": {},
                }

            response_json["session_id"] = target_session_id
            response_json["active_session_id"] = target_session_id
            response_json["target_session_append_bridge"] = True
            response_json["web_fetch_requested_session_bridge"] = True
            response_json["session"] = final_session

            if isinstance(
                response_json.get("assistant_message"),
                dict,
            ):
                response_json["assistant_message"][
                    "session_id"
                ] = target_session_id

                response_json["assistant_message"][
                    "active_session_id"
                ] = target_session_id

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

        except Exception:
            return response

        return response