class PublicRouteService:

    def install_routes(self, app):
        from flask import (
            Response,
            jsonify,
            render_template,
            request,
        )

        @app.get("/")
        def nova_public_home_preview_20260709():
            return render_template(
                "nova_landing_home.html"
            )

        @app.get("/about")
        def nova_about_page_20260709():
            return render_template(
                "nova_about.html"
            )

        @app.get("/features")
        def nova_features_page_20260709():
            return render_template(
                "nova_features.html"
            )

        @app.get("/roadmap")
        def nova_roadmap_page_20260709():
            return render_template(
                "nova_roadmap.html"
            )

        @app.get("/faq")
        def nova_faq_page_20260709():
            return render_template(
                "nova_faq.html"
            )

        @app.get("/contact")
        @app.get("/early-access")
        def nova_contact_page_20260709():
            return render_template(
                "nova_contact.html"
            )

        @app.get("/sitemap.xml")
        def nova_public_sitemap_20260709():
            base_url = request.url_root.rstrip("/")

            xml = render_template(
                "nova_sitemap.xml",
                base_url=base_url,
            )

            return Response(
                xml,
                mimetype="application/xml",
            )

        @app.get("/robots.txt")
        def nova_public_robots_20260709():
            base_url = request.url_root.rstrip("/")

            text = render_template(
                "nova_robots.txt",
                base_url=base_url,
            )

            return Response(
                text,
                mimetype="text/plain",
            )

        @app.get("/privacy")
        def nova_privacy_page_20260709():
            return render_template(
                "nova_privacy.html"
            )

        @app.get("/terms")
        def nova_terms_page_20260709():
            return render_template(
                "nova_terms.html"
            )

        @app.errorhandler(404)
        def nova_public_not_found_20260709(error):
            if request.path.startswith("/api/"):
                return jsonify({
                    "ok": False,
                    "error": "Not found",
                }), 404

            return render_template(
                "nova_404.html",
                path=request.path,
            ), 404