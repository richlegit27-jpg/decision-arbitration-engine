from flask import g, jsonify, session


def _nova_usage_current_user():
    auth_user = getattr(g, "nova_auth_user", None)

    if isinstance(auth_user, dict):
        user_id = str(
            auth_user.get("id")
            or auth_user.get("user_id")
            or ""
        ).strip()

        username = str(auth_user.get("username") or "").strip()

        if user_id:
            return user_id, username

    user_id = str(
        session.get("nova_user_id")
        or session.get("user_id")
        or ""
    ).strip()

    username = str(session.get("username") or "").strip()

    if user_id:
        return user_id, username

    from nova_backend.services.auth_context import get_current_user_id

    return str(get_current_user_id() or "").strip(), username


def install_usage_routes(app):

    @app.get("/api/usage")
    def nova_api_usage_summary_active_20260705():
        try:
            from nova_backend.services.usage_ledger_service import usage_summary

            user_id, username = _nova_usage_current_user()

            if not user_id and not username:
                return jsonify({
                    "ok": False,
                    "error": "Authentication is required to view usage.",
                }), 401

            return jsonify(
                usage_summary(user_id=user_id, username=username)
            )

        except Exception as exc:
            app.logger.exception("Failed to load usage summary")

            return jsonify({
                "ok": False,
                "error": str(exc),
                "route": "nova_api_usage_summary_active_20260705",
            }), 500

    @app.get("/api/usage/session/<session_id>")
    def nova_api_usage_session_summary_active_20260705(session_id):
        try:
            from nova_backend.services.usage_ledger_service import usage_summary

            user_id, username = _nova_usage_current_user()

            if not user_id and not username:
                return jsonify({
                    "ok": False,
                    "error": "Authentication is required to view usage.",
                }), 401

            return jsonify(
                usage_summary(
                    session_id=session_id,
                    user_id=user_id,
                    username=username,
                )
            )

        except Exception as exc:
            app.logger.exception("Failed to load session usage summary")

            return jsonify({
                "ok": False,
                "error": str(exc),
                "route": "nova_api_usage_session_summary_active_20260705",
                "session_id": session_id,
            }), 500

    print("[NOVA_USAGE_ROUTES_SERVICE] installed")