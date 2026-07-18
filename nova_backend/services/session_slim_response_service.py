import json


class SessionSlimResponseService:

    def __init__(self):
        pass

    def handle(
        self,
        response,
        request,
        app,
    ):
        try:
            path = str(
                request.path or ""
            )

            # NOVA_HEADER_SKIP_SLIM_SESSIONS_RESPONSE_20260611
            if response.headers.get(
                "X-Nova-Slim-Sessions"
            ) == "1":
                return response

            if path != "/api/sessions":
                return response

            try:
                payload = response.get_json(
                    silent=True
                )
            except Exception:
                payload = None

            if not isinstance(payload, dict):
                return response

            # NOVA_SKIP_AFTER_REQUEST_FOR_SLIM_SESSIONS_20260611
            if (
                payload.get("slim_sessions_payload") is True
                and isinstance(
                    payload.get("debug"),
                    dict,
                )
                and payload.get("debug", {}).get(
                    "route_taken"
                )
                == "slim_sessions_payload"
            ):
                return response

            if "artifacts" in payload:
                payload["artifacts"] = []

            if "artifact" in payload:
                payload.pop(
                    "artifact",
                    None,
                )

            sessions = payload.get(
                "sessions"
            )

            if isinstance(
                sessions,
                list,
            ):
                slim_sessions = []

                for item in sessions:
                    if not isinstance(
                        item,
                        dict,
                    ):
                        continue

                    messages = item.get(
                        "messages"
                    )

                    message_count = (
                        len(messages)
                        if isinstance(messages, list)
                        else 0
                    )

                    slim_sessions.append(
                        {
                            "id": item.get("id"),
                            "title": item.get("title")
                            or "New Chat",
                            "created_at": item.get(
                                "created_at"
                            ),
                            "updated_at": item.get(
                                "updated_at"
                            ),
                            "pinned": bool(
                                item.get("pinned")
                            ),
                            "message_count": message_count,
                            "user_id": item.get(
                                "user_id"
                            ),
                            "username": item.get(
                                "username"
                            ),
                            "meta": item.get("meta")
                            if isinstance(
                                item.get("meta"),
                                dict,
                            )
                            else {},
                            "working_state": item.get(
                                "working_state"
                            )
                            if isinstance(
                                item.get(
                                    "working_state"
                                ),
                                dict,
                            )
                            else {},
                            "active_execution": item.get(
                                "active_execution"
                            )
                            if isinstance(
                                item.get(
                                    "active_execution"
                                ),
                                dict,
                            )
                            else {},
                        }
                    )

                payload["sessions"] = slim_sessions

            session_obj = payload.get(
                "session"
            )

            if isinstance(
                session_obj,
                dict,
            ):
                messages = session_obj.get(
                    "messages"
                )

                message_count = (
                    len(messages)
                    if isinstance(messages, list)
                    else 0
                )

                payload["session"] = {
                    "id": session_obj.get("id"),
                    "title": session_obj.get("title")
                    or "New Chat",
                    "created_at": session_obj.get(
                        "created_at"
                    ),
                    "updated_at": session_obj.get(
                        "updated_at"
                    ),
                    "pinned": bool(
                        session_obj.get("pinned")
                    ),
                    "message_count": message_count,
                    "user_id": session_obj.get(
                        "user_id"
                    ),
                    "username": session_obj.get(
                        "username"
                    ),
                    "meta": session_obj.get(
                        "meta"
                    )
                    if isinstance(
                        session_obj.get("meta"),
                        dict,
                    )
                    else {},
                    "working_state": session_obj.get(
                        "working_state"
                    )
                    if isinstance(
                        session_obj.get(
                            "working_state"
                        ),
                        dict,
                    )
                    else {},
                    "active_execution": session_obj.get(
                        "active_execution"
                    )
                    if isinstance(
                        session_obj.get(
                            "active_execution"
                        ),
                        dict,
                    )
                    else {},
                }

            payload.setdefault(
                "ok",
                True,
            )

            payload["slim_sessions_payload"] = True

            body = json.dumps(
                payload,
                ensure_ascii=False,
            )

            response.set_data(
                body
            )

            response.headers[
                "Content-Type"
            ] = "application/json; charset=utf-8"

            response.headers[
                "Content-Length"
            ] = str(
                len(
                    body.encode("utf-8")
                )
            )

            return response

        except Exception as exc:
            try:
                app.logger.warning(
                    "[Nova Slim Sessions Payload] failed: %s",
                    exc,
                )
            except Exception:
                pass

            return response