from flask import jsonify, request


def register_payments_routes(app):

    try:

        def _nova_payments_route_exists_20260709(rule_text):
            try:
                return any(
                    str(rule) == rule_text
                    for rule in app.url_map.iter_rules()
                )
            except Exception:
                return False
                return False


        def _nova_payments_current_username_20260709():
            try:
                from flask import session

                username = (
                    session.get("username")
                    or session.get("nova_username")
                    or "richard"
                )

            except Exception:
                username = "richard"

            return str(username or "richard").strip()


        def _nova_payments_json_20260709(payload, status_code=200):
            response = jsonify(payload)
            response.status_code = status_code
            return response


        if not _nova_payments_route_exists_20260709(
            "/api/billing/readiness"
        ):

            @app.get("/api/billing/readiness")
            def nova_billing_readiness_api_20260709():

                from nova_backend.services.payments_readiness_service import (
                    build_payments_readiness,
                )

                username = (
                    _nova_payments_current_username_20260709()
                )

                data = build_payments_readiness(
                    username=username
                )

                return _nova_payments_json_20260709(
                    {
                        "ok": True,
                        **data,
                    }
                )


        if not _nova_payments_route_exists_20260709(
            "/api/billing/plans"
        ):

            @app.get("/api/billing/plans")
            def nova_billing_plans_api_20260709():

                from nova_backend.services.payments_readiness_service import (
                    build_payments_readiness,
                )

                username = (
                    _nova_payments_current_username_20260709()
                )

                data = build_payments_readiness(
                    username=username
                )

                return _nova_payments_json_20260709(
                    {
                        "ok": True,
                        "plans": data.get("plans", []),
                        "payments": data.get(
                            "payments",
                            {},
                        ),
                    }
                )


        if not _nova_payments_route_exists_20260709(
            "/admin/billing-readiness"
        ):

            @app.get("/admin/billing-readiness")
            def nova_admin_billing_readiness_20260709():

                from nova_backend.services.payments_readiness_service import (
                    build_payments_readiness,
                )

                username = (
                    _nova_payments_current_username_20260709()
                )

                data = build_payments_readiness(
                    username=username
                )

                return (
                    "<h1>Nova Billing Readiness</h1>"
                    f"<pre>{data}</pre>"
                )


        print(
            "[NOVA_PAYMENTS_READINESS_ROUTES_20260709] installed"
        )


    except Exception as exc:

        print(
            "[NOVA_PAYMENTS_READINESS_ROUTES_20260709] failed:",
            exc,
        )