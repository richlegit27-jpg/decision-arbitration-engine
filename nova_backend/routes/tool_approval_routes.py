from flask import jsonify, request
from nova_backend.services.auth_context import get_current_user_id


def _owned_session(chat_service, session_id, owner_id):
    sessions = getattr(chat_service, "session_service", None)
    if sessions is None or not session_id or not owner_id:
        return False
    try:
        return bool(sessions.get_session(session_id, user_id=owner_id))
    except Exception:
        return False


def register_tool_approval_routes(
    app,
    chat_service,
):

    @app.get("/api/tools")
    def list_tools():
        if not get_current_user_id():
            return jsonify({"ok": False, "error": "authentication_required"}), 401

        try:
            registry = getattr(chat_service, "tool_registry", None)
            tools = registry.get_model_tool_definitions("chat") if registry else []
            return jsonify({"ok": True, "count": len(tools), "tools": tools})

        except Exception as exc:
            app.logger.error("tool catalog request failed", extra={"error_type": type(exc).__name__})

            return jsonify(
                {
                    "ok": False,
                    "error": "tool_catalog_unavailable",
                }
            ), 500


    @app.get("/api/tools/<tool_name>")
    def get_tool(tool_name):
        if not get_current_user_id():
            return jsonify({"ok": False, "error": "authentication_required"}), 401

        try:
            registry = getattr(chat_service, "tool_registry", None)
            tool = next(
                (item for item in registry.get_model_tool_definitions("chat") if item.get("name") == tool_name),
                None,
            ) if registry else None
            result = {"ok": bool(tool), "tool": tool} if tool else {"ok": False, "error": "tool_not_found", "tool": tool_name}

            status_code = (
                200
                if result.get("ok")
                else 404
            )

            return jsonify(
                result
            ), status_code

        except Exception as exc:
            app.logger.error("tool metadata request failed", extra={"error_type": type(exc).__name__})

            return jsonify(
                {
                    "ok": False,
                    "tool": tool_name,
                    "error": "tool_metadata_unavailable",
                }
            ), 500


    @app.post("/api/tools/approve")
    def approve_tool():

        owner_id = get_current_user_id()
        if not owner_id:
            return jsonify({"ok": False, "error": "authentication_required"}), 401

        data = request.get_json(
            silent=True
        ) or {}

        session_id = str(
            data.get("session_id") or ""
        ).strip()

        if not session_id:

            return jsonify(
                {
                    "ok": False,
                    "error": "Missing session_id.",
                }
            ), 400

        if not _owned_session(chat_service, session_id, owner_id):
            return jsonify({"ok": False, "error": "session_not_found"}), 404

        result = (
            chat_service.approve_pending_tool(
                session_id=session_id,
                owner_id=owner_id,
            )
        )

        status_code = (
            200
            if result.get("ok")
            else 400
        )

        return jsonify(
            result
        ), status_code


    @app.post("/api/tools/deny")
    def deny_tool():

        owner_id = get_current_user_id()
        if not owner_id:
            return jsonify({"ok": False, "error": "authentication_required"}), 401

        data = request.get_json(
            silent=True
        ) or {}

        session_id = str(
            data.get("session_id") or ""
        ).strip()

        if not session_id:

            return jsonify(
                {
                    "ok": False,
                    "error": "Missing session_id.",
                }
            ), 400

        if not _owned_session(chat_service, session_id, owner_id):
            return jsonify({"ok": False, "error": "session_not_found"}), 404

        result = (
            chat_service.deny_pending_tool(
                session_id=session_id,
                owner_id=owner_id,
            )
        )

        status_code = (
            200
            if result.get("ok")
            else 400
        )

        return jsonify(
            result
        ), status_code


    @app.get("/api/tools/pending")
    def get_pending_tool():

        owner_id = get_current_user_id()
        if not owner_id:
            return jsonify({"ok": False, "error": "authentication_required"}), 401

        session_id = str(
            request.args.get(
                "session_id",
                "",
            )
        ).strip()

        if not session_id:

            return jsonify(
                {
                    "ok": False,
                    "error": "Missing session_id.",
                }
            ), 400

        if not _owned_session(chat_service, session_id, owner_id):
            return jsonify({"ok": False, "error": "session_not_found"}), 404

        from nova_backend.tools.pending_tool_approval_service import (
            pending_tool_approval_service,
        )

        pending = (
            pending_tool_approval_service.get_pending(
                session_id, owner_id=owner_id
            )
        )

        return jsonify(
            {
                "ok": True,
                "pending": pending,
            }
        )


    print(
        "[NOVA TOOL APPROVAL ROUTES] installed",
        flush=True,
    )
