from flask import jsonify, request


def register_tool_approval_routes(
    app,
    chat_service,
):

    @app.post("/api/tools/approve")
    def approve_tool():

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

        result = (
            chat_service.approve_pending_tool(
                session_id=session_id,
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

        result = (
            chat_service.deny_pending_tool(
                session_id=session_id,
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

        from nova_backend.tools.pending_tool_approval_service import (
            pending_tool_approval_service,
        )

        pending = (
            pending_tool_approval_service.get_pending(
                session_id
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