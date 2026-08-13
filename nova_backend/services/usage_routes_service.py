from flask import current_app


def install_usage_routes(app):

    @app.get("/api/usage")
    def nova_api_usage_summary_active_20260705():
        try:
            from nova_backend.services.usage_ledger_service import usage_summary
            return current_app.json_ok(
                **usage_summary()
            )
        except Exception as exc:
            return current_app.json_error(
                str(exc),
                route="nova_api_usage_summary_active_20260705",
            )

    @app.get("/api/usage/session/<session_id>")
    def nova_api_usage_session_summary_active_20260705(session_id):
        try:
            from nova_backend.services.usage_ledger_service import usage_summary
            return current_app.json_ok(
                **usage_summary(session_id=session_id)
            )
        except Exception as exc:
            return current_app.json_error(
                str(exc),
                route="nova_api_usage_session_summary_active_20260705",
                session_id=session_id,
            )

    print(
        "[NOVA_USAGE_ROUTES_SERVICE] installed"
    )