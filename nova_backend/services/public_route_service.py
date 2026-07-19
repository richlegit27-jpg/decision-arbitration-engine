class PublicRouteService:

    def install_routes(self, app):
        from flask import render_template, jsonify, request

        @app.route("/")
        def nova_public_home_preview_20260709():
            ...

        @app.route("/about")
        def nova_about_page_20260709():
            ...

        # remaining public routes