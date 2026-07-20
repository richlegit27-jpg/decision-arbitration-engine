from __future__ import annotations


class RepairPlanPriorityGuardService:

    def install(self, app):
        return None













# NOVA_REPAIR_PLAN_COMMAND_PRIORITY_GUARD_20260701
# Explicit repair-plan / fix-plan commands must outrank project-context recall.
try:
    from nova_backend.services import repair_plan_adapter as _nova_repair_plan_adapter_20260701

    _NOVA_PRE_REPAIR_PLAN_COMMAND_PRIORITY_HANDLE_20260701 = ChatService.handle

    def _nova_repair_plan_command_priority_handle_20260701(self, *args, **kwargs):
        user_text = ""
        session_id = None
        attachments = []

        try:
            if args:
                first = args[0]

                if isinstance(first, dict):
                    user_text = str(first.get("user_text") or first.get("message") or first.get("text") or "")
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

            repair_input = _nova_repair_plan_adapter_20260701.extract_repair_plan_input(user_text)

            if repair_input is not None:
                payload = {
                    "user_text": user_text,
                    "session_id": session_id or getattr(getattr(self, "session_service", None), "active_session_id", None) or "default",
                    "attachments": attachments,
                }

                session_service = getattr(self, "session_service", None)

                if session_service is None:
                    session_service = globals().get("session_service")

                if session_service is not None:
                    return _nova_repair_plan_adapter_20260701.build_repair_plan_response(
                        payload,
                        session_service,
                    )

        except Exception as exc:
            try:
                print("[NOVA_REPAIR_PLAN_COMMAND_PRIORITY_GUARD_20260701] failed:", exc)
            except Exception:
                pass

        return _NOVA_PRE_REPAIR_PLAN_COMMAND_PRIORITY_HANDLE_20260701(self, *args, **kwargs)

    ChatService.handle = _nova_repair_plan_command_priority_handle_20260701
    print("[NOVA_REPAIR_PLAN_COMMAND_PRIORITY_GUARD_20260701] installed")
except Exception as _nova_repair_plan_command_priority_error_20260701:
    print("[NOVA_REPAIR_PLAN_COMMAND_PRIORITY_GUARD_20260701] failed:", _nova_repair_plan_command_priority_error_20260701)



# NOVA_REPAIR_PLAN_API_BEFORE_REQUEST_PRIORITY_20260701
# Explicit repair-plan / fix-plan commands must bypass project-context recall before /api/chat runs.
try:
    from flask import request as _nova_repair_plan_flask_request_20260701
    from flask import jsonify as _nova_repair_plan_flask_jsonify_20260701
    from nova_backend.services import repair_plan_adapter as _nova_repair_plan_api_adapter_20260701

    @app.before_request
    def _nova_repair_plan_api_before_request_priority_20260701():
        try:
            if _nova_repair_plan_flask_request_20260701.path != "/api/chat":
                return None

            if _nova_repair_plan_flask_request_20260701.method != "POST":
                return None

            data = _nova_repair_plan_flask_request_20260701.get_json(silent=True) or {}

            user_text = str(
                data.get("user_text")
                or data.get("message")
                or data.get("text")
                or ""
            )

            repair_input = _nova_repair_plan_api_adapter_20260701.extract_repair_plan_input(user_text)

            if repair_input is None:
                return None

            session_id = (
                data.get("session_id")
                or getattr(globals().get("session_service"), "active_session_id", None)
                or "default"
            )

            payload = {
                "user_text": user_text,
                "session_id": session_id,
                "attachments": data.get("attachments") or [],
            }

            result = _nova_repair_plan_api_adapter_20260701.build_repair_plan_response(
                payload,
                globals().get("session_service"),
            )

            return _nova_repair_plan_flask_jsonify_20260701(result)

        except Exception as exc:
            try:
                print("[NOVA_REPAIR_PLAN_API_BEFORE_REQUEST_PRIORITY_20260701] failed:", exc)
            except Exception:
                pass

            return None

    print("[NOVA_REPAIR_PLAN_API_BEFORE_REQUEST_PRIORITY_20260701] installed")
except Exception as _nova_repair_plan_api_before_request_error_20260701:
    print("[NOVA_REPAIR_PLAN_API_BEFORE_REQUEST_PRIORITY_20260701] failed:", _nova_repair_plan_api_before_request_error_20260701)