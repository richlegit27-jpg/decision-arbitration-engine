class LoginPageRouteService:

    def install_routes(self, app):
        import json
        from pathlib import Path
        from flask import render_template, redirect, request, session

        def route_exists(rule):
            return any(
                str(r.rule) == rule
                for r in app.url_map.iter_rules()
            )

        def login_page():
            return render_template(
                "login.html",
                active_tab="login",
                prefill_username=request.args.get(
                    "username",
                    "",
                ),
                prefill_register_username="",
            )

        def register_page():
            return render_template(
                "login.html",
                active_tab="register",
                prefill_username="",
                prefill_register_username=request.args.get(
                    "username",
                    "",
                ),
            )

        def forgot_password_page():
            return render_template(
                "forgot_password.html",
            )

        def reset_password_page():
            return render_template(
                "reset_password.html",
            )

        def verify_email_page():
            return render_template("verify_email.html")

        def account_page():
            user_id = str(session.get("nova_user_id") or "").strip()
            if not user_id:
                return redirect("/login")

            users_path = (
                Path(
                    app.config.get("NOVA_AUTH_USERS_PATH")
                    or (
                        Path(__file__).resolve().parents[2]
                        / "data"
                        / "nova_auth_users.json"
                    )
                )
            )
            try:
                users = json.loads(users_path.read_text(encoding="utf-8")).get(
                    "users", []
                )
            except (OSError, ValueError, AttributeError):
                users = []

            user = next(
                (item for item in users if str(item.get("id") or "") == user_id),
                None,
            )
            if not user:
                session.clear()
                return redirect("/login")

            return render_template(
                "account.html",
                username=str(user.get("username") or "User"),
                auth_provider=str(user.get("auth_provider") or "local"),
                mfa_enabled=bool(user.get("mfa_enabled", False)),
                google_linked=bool(user.get("google_sub")),
            )

        if not route_exists("/login"):
            app.add_url_rule(
                "/login",
                "nova_login_page_20260610",
                login_page,
                methods=["GET"],
            )

        if not route_exists("/register"):
            app.add_url_rule(
                "/register",
                "nova_register_page_20260610",
                register_page,
                methods=["GET"],
            )

        if not route_exists("/forgot-password"):
            app.add_url_rule(
                "/forgot-password",
                "nova_forgot_password_page_20260908",
                forgot_password_page,
                methods=["GET"],
            )

        if not route_exists("/reset-password"):
            app.add_url_rule(
                "/reset-password",
                "nova_reset_password_page_20260908",
                reset_password_page,
                methods=["GET"],
            )

        if not route_exists("/verify-email"):
            app.add_url_rule(
                "/verify-email",
                "nova_verify_email_page_20261002",
                verify_email_page,
                methods=["GET"],
            )

        if not route_exists("/account"):
            app.add_url_rule(
                "/account",
                "nova_account_security_page_20261002",
                account_page,
                methods=["GET"],
            )

        def logout_page():
            session.pop(
                "nova_user_id",
                None,
            )

            return redirect("/login")

        if not route_exists("/logout"):
            app.add_url_rule(
                "/logout",
                "nova_logout_page_20260610",
                logout_page,
                methods=["GET"],
            )
        else:
            app.view_functions[
                "nova_logout_page_20260610"
            ] = logout_page
