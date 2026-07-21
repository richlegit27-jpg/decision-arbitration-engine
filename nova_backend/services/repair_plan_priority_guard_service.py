from __future__ import annotations


class RepairPlanPriorityGuardService:

    def install(self, app):
        from flask import request as repair_request
        from flask import jsonify as repair_jsonify
        from nova_backend.services import repair_plan_adapter

        from nova_backend.services.chat_service import ChatService

        previous_handle = getattr(
            ChatService,
            "handle",
            None,
        )

        if previous_handle is None:
            return app

        def repair_plan_handle(self, *args, **kwargs):
            user_text = ""
            session_id = None
            attachments = []

            try:
                if args:
                    first = args[0]

                    if isinstance(first, dict):
                        user_text = str(
                            first.get("user_text")
                            or first.get("message")
                            or first.get("text")
                            or ""
                        )
                        session_id = first.get("session_id")
                        attachments = first.get("attachments") or []
                    else:
                        user_text = str(first or "")

                        if len(args) > 1:
                            session_id = args[1]

                        if len(args) > 2:
                            attachments = args[2] or []

                user_text = str(
                    kwargs.get("user_text")
                    or kwargs.get("message")
                    or kwargs.get("text")
                    or user_text
                    or ""
                )

                session_id = kwargs.get("session_id") or session_id
                attachments = kwargs.get("attachments") or attachments or []

                if repair_plan_adapter.extract_repair_plan_input(user_text) is not None:
                    payload = {
                        "user_text": user_text,
                        "session_id": (
                            session_id
                            or getattr(
                                getattr(self, "session_service", None),
                                "active_session_id",
                                None,
                            )
                            or "default"
                        ),
                        "attachments": attachments,
                    }

                    session_service = getattr(self, "session_service", None)

                    if session_service is None:
                        session_service = globals().get("session_service")

                    if session_service is not None:
                        return repair_plan_adapter.build_repair_plan_response(
                            payload,
                            session_service,
                        )

            except Exception as exc:
                print(
                    "[REPAIR_PLAN_COMMAND_PRIORITY_GUARD] failed:",
                    exc,
                )

            return previous_handle(self, *args, **kwargs)

        ChatService.handle = repair_plan_handle

        @app.before_request
        def repair_plan_api_before_request_priority():
            try:
                if repair_request.path != "/api/chat":
                    return None

                if repair_request.method != "POST":
                    return None

                data = repair_request.get_json(silent=True) or {}

                user_text = str(
                    data.get("user_text")
                    or data.get("message")
                    or data.get("text")
                    or ""
                )

                if repair_plan_adapter.extract_repair_plan_input(user_text) is None:
                    return None

                session_id = (
                    data.get("session_id")
                    or getattr(
                        globals().get("session_service"),
                        "active_session_id",
                        None,
                    )
                    or "default"
                )

                payload = {
                    "user_text": user_text,
                    "session_id": session_id,
                    "attachments": data.get("attachments") or [],
                }

                result = repair_plan_adapter.build_repair_plan_response(
                    payload,
                    globals().get("session_service"),
                )

                return repair_jsonify(result)

            except Exception as exc:
                print(
                    "[REPAIR_PLAN_API_BEFORE_REQUEST_PRIORITY] failed:",
                    exc,
                )

                return None


