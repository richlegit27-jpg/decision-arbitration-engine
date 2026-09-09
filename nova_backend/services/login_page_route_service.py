class LoginPageRouteService:

    def install_routes(self, app):
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