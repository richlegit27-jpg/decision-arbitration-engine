class AuthCompatRouteService:

    def install_routes(self, app):
        try:
            from flask import jsonify, session

            def has_rule_method(rule_path, method):
                method = str(method or "").upper()

                for rule in app.url_map.iter_rules():
                    if (
                        getattr(rule, "rule", "") == rule_path
                        and method in getattr(rule, "methods", set())
                    ):
                        return True

                return False

            def forward_to_existing(endpoint_names):
                for endpoint in endpoint_names:
                    view = app.view_functions.get(endpoint)

                    if callable(view):
                        return view()

                return jsonify({
                    "ok": False,
                    "error": "Auth endpoint is not available.",
                }), 404

            def auth_status():
                user = None

                try:
                    uid = session.get("nova_user_id")

                    if uid:
                        from pathlib import Path
                        import json

                        users_path = (
                            Path(__file__)
                            .resolve()
                            .parents[2]
                            / "data"
                            / "nova_auth_users.json"
                        )

                        if users_path.exists():
                            users_data = json.loads(
                                users_path.read_text(
                                    encoding="utf-8"
                                )
                            )

                            users = (
                                users_data.get("users", [])
                                if isinstance(users_data, dict)
                                else []
                            )

                            for item in users:
                                if (
                                    isinstance(item, dict)
                                    and str(item.get("id") or "")
                                    == str(uid)
                                ):
                                    user = {
                                        "id": item.get("id"),
                                        "username": (
                                            item.get("username")
                                            or item.get("name")
                                            or item.get("email")
                                        ),
                                        "name": (
                                            item.get("name")
                                            or item.get("username")
                                            or item.get("email")
                                        ),
                                        "email": item.get("email") or "",
                                    }
                                    break

                except Exception:
                    user = None

                return jsonify({
                    "ok": True,
                    "authenticated": bool(user),
                    "user": user,
                    "mode": "local",
                })

            def auth_logout_alias():
                session.pop("nova_user_id", None)

                return jsonify({
                    "ok": True,
                    "authenticated": False,
                    "user": None,
                    "redirect_to": "/login",
                })

            def auth_login_alias():
                return forward_to_existing([
                    "nova_api_login_20260610",
                    "auth_login",
                ])

            def auth_register_alias():
                return forward_to_existing([
                    "nova_api_register_20260610",
                    "auth_register",
                ])

            routes = [
                (
                    "/api/auth/status",
                    "nova_api_auth_status_safe_20260611",
                    auth_status,
                    ["GET"],
                ),
                (
                    "/api/auth/me",
                    "nova_api_auth_me_safe_20260612",
                    auth_status,
                    ["GET"],
                ),
                (
                    "/api/me",
                    "nova_api_me_safe_20260612",
                    auth_status,
                    ["GET"],
                ),
                (
                    "/auth/status",
                    "nova_auth_status_page_safe_20260612",
                    auth_status,
                    ["GET"],
                ),
                (
                    "/api/auth/logout",
                    "nova_api_auth_logout_safe_20260611",
                    auth_logout_alias,
                    ["POST", "GET"],
                ),
                (
                    "/api/auth/login",
                    "nova_api_auth_login_safe_20260611",
                    auth_login_alias,
                    ["POST"],
                ),
                (
                    "/api/auth/register",
                    "nova_api_auth_register_safe_20260611",
                    auth_register_alias,
                    ["POST"],
                ),
                (
                    "/login",
                    "nova_login_post_safe_20260611",
                    auth_login_alias,
                    ["POST"],
                ),
                (
                    "/register",
                    "nova_register_post_safe_20260611",
                    auth_register_alias,
                    ["POST"],
                ),
            ]

            installed = 0

            for rule_path, endpoint, view, methods in routes:
                missing = [
                    method
                    for method in methods
                    if not has_rule_method(
                        rule_path,
                        method,
                    )
                ]

                if not missing:
                    continue

                app.add_url_rule(
                    rule_path,
                    endpoint,
                    view,
                    methods=missing,
                )

                installed += 1

            print(
                "[NOVA AUTH] safe compat alias routes installed:",
                installed,
            )

        except Exception as exc:
            print(
                "[NOVA AUTH] safe compat alias install failed:",
                exc,
            )