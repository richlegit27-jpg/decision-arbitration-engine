class BlogRouteService:

    def __init__(self, blog_service):
        self.blog_service = blog_service

    def install_routes(self, app):
        from flask import render_template, jsonify, request

        @app.route("/help")
        def nova_help_page_20260611():
            return render_template("help.html")

        @app.route("/blog")
        def nova_blog_page_20260611():
            return render_template("blog.html")

        @app.route("/blog/write")
        def nova_blog_write_page_restored_20260711():
            return render_template("blog_write.html")

        @app.route("/blog/<slug>")
        def nova_blog_post_page_restored_20260711(slug):
            return render_template(
                "blog_post.html",
                slug=slug,
            )

        @app.route(
            "/api/blog/posts",
            methods=[
                "GET",
                "POST",
            ],
        )
        def nova_blog_posts_api_restored_20260711():

            posts = self.blog_service.read_posts()

            if request.method == "GET":
                posts = sorted(
                    posts,
                    key=lambda item: (
                        item.get("updated_at")
                        or item.get("created_at")
                        or ""
                    ),
                    reverse=True,
                )

                return jsonify(
                    {
                        "ok": True,
                        "posts": posts,
                    }
                )

            payload = request.get_json(
                silent=True
            ) or {}

            title = str(
                payload.get("title")
                or ""
            ).strip()

            body = str(
                payload.get("body")
                or ""
            ).strip()

            excerpt = str(
                payload.get("excerpt")
                or ""
            ).strip()

            tags = payload.get("tags")

            if isinstance(tags, str):
                tags = [
                    part.strip()
                    for part in tags.split(",")
                    if part.strip()
                ]

            elif isinstance(tags, list):
                tags = [
                    str(part).strip()
                    for part in tags
                    if str(part).strip()
                ]

            else:
                tags = []

            tags = list(dict.fromkeys(tags))

            if not title:
                return jsonify(
                    {
                        "ok": False,
                        "error": "Title is required.",
                    }
                ), 400

            if not body:
                return jsonify(
                    {
                        "ok": False,
                        "error": "Body is required.",
                    }
                ), 400

            post = self.blog_service.create_post(
                title=title,
                body=body,
                excerpt=excerpt,
                tags=tags,
                slug=payload.get("slug"),
            )

            return jsonify(
                {
                    "ok": True,
                    "post": post,
                }
            )

        @app.route(
            "/api/blog/posts/<slug>",
            methods=["GET"],
        )
        def nova_blog_single_post_api_restored_20260711(slug):

            post = self.blog_service.get_post(slug)

            if post:
                return jsonify(
                    {
                        "ok": True,
                        "post": post,
                    }
                )

            return jsonify(
                {
                    "ok": False,
                    "error": "Post not found.",
                }
            ), 404