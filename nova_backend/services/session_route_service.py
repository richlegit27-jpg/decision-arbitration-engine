from flask import jsonify


class SessionRouteService:

    def handle_slim_sessions(
        self,
        request,
        session,
        session_service,
        app,
        jsonify,
    ):
        try:
            
            if request.path != "/api/sessions" or request.method != "GET":
                return None

            if not session.get("nova_user_id"):
                return None

            raw_sessions = []

            for method_name in (
                "list_sessions",
                "get_sessions",
                "all_sessions",
                "load_sessions",
                "all",
            ):
                try:
                    method = getattr(session_service, method_name, None)

                    if callable(method):
                        candidate = method(
                            user_id=str(
                                session.get("nova_user_id") or ""
                            ).strip()
                        )

                        if isinstance(candidate, list):
                            raw_sessions = candidate
                            break

                        if isinstance(candidate, dict):
                            if isinstance(candidate.get("sessions"), list):
                                raw_sessions = candidate.get("sessions") or []
                                break

                            if (
                                isinstance(candidate.get("data"), dict)
                                and isinstance(candidate["data"].get("sessions"), list)
                            ):
                                raw_sessions = candidate["data"]["sessions"] or []
                                break

                except Exception:
                    pass

            current_user_id = str(
                session.get("nova_user_id") or ""
            ).strip()

            raw_sessions = [
                item
                for item in raw_sessions
                if (
                    isinstance(item, dict)
                    and str(item.get("user_id") or "").strip()
                    == current_user_id
                )
            ]

            slim_sessions = []

            for item in raw_sessions:
                if not isinstance(item, dict):
                    continue

                messages = item.get("messages")

                message_count = (
                    len(messages)
                    if isinstance(messages, list)
                    else int(item.get("message_count") or 0)
                )

                slim_sessions.append({
                    "id": item.get("id") or item.get("session_id") or "",
                    "title": item.get("title") or "New Chat",
                    "created_at": item.get("created_at") or "",
                    "updated_at": item.get("updated_at") or "",
                    "pinned": bool(item.get("pinned")),
                    "message_count": message_count,
                    "user_id": item.get("user_id") or "",
                    "username": item.get("username") or "",
                    "meta": item.get("meta")
                    if isinstance(item.get("meta"), dict)
                    else {},
                    "working_state": item.get("working_state")
                    if isinstance(item.get("working_state"), dict)
                    else {},
                    "active_execution": item.get("active_execution")
                    if isinstance(item.get("active_execution"), dict)
                    else {},
                })

            slim_sessions.sort(
                key=lambda item: str(
                    item.get("updated_at")
                    or item.get("created_at")
                    or ""
                ),
                reverse=True,
            )

            active_session_id = ""

            try:
                active_session_id = str(
                    request.cookies.get("nova_active_session_id")
                    or request.cookies.get("active_session_id")
                    or request.cookies.get("session_id")
                    or ""
                ).strip()

            except Exception:
                active_session_id = ""

            if not active_session_id and slim_sessions:
                for candidate in slim_sessions:
                    if int(candidate.get("message_count") or 0) > 0:
                        active_session_id = str(candidate.get("id") or "")
                        break

                if not active_session_id:
                    active_session_id = str(
                        slim_sessions[0].get("id") or ""
                    )

            returned_sessions = slim_sessions[:50]

            response = jsonify({
                "ok": True,
                "active_session_id": active_session_id,
                "sessions": returned_sessions,
                "items": returned_sessions,
                "artifacts": [],
                "slim_sessions_payload": True,
                "debug": {
                    "route": "before_request_slim_api_sessions",
                    "route_taken": "slim_sessions_payload",
                    "raw_session_count": len(raw_sessions),
                    "returned_session_count": len(returned_sessions),
                },
            })

            response.headers["X-Nova-Slim-Sessions"] = "1"

            return response

        except Exception as exc:
            print("[SESSION_ROUTE_SERVICE_ERROR]", repr(exc))
            try:
                app.logger.warning(
                    "[Nova Before Request Slim Sessions] failed: %s",
                    exc,
                )
            except Exception:
                pass

            raise