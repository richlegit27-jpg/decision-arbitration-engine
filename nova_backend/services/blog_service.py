from pathlib import Path
import json
import re
from datetime import datetime, timezone


class BlogService:

    def _posts_path(self):
        path = (
            Path(__file__).resolve().parents[2]
            /
            "data"
            /
            "blog_posts.json"
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        return path


    def read_posts(self):
        path = self._posts_path()

        if not path.exists():
            return []

        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            return []

        if isinstance(payload, list):
            return [
                item
                for item in payload
                if isinstance(item, dict)
            ]

        if isinstance(payload, dict):
            posts = payload.get("posts")

            if isinstance(posts, list):
                return [
                    item
                    for item in posts
                    if isinstance(item, dict)
                ]

        return []


    def write_posts(self, posts):
        self._posts_path().write_text(
            json.dumps(
                posts,
                ensure_ascii=False,
                indent=2,
            )
            +
            "\n",
            encoding="utf-8",
        )


    def slugify(self, value):
        value = str(
            value
            or
            ""
        ).strip().lower()

        value = re.sub(
            r"[^a-z0-9]+",
            "-",
            value,
        )

        return value.strip("-") or "post"


    def create_post(
        self,
        title,
        body,
        excerpt="",
        tags=None,
        slug=None,
    ):
        posts = self.read_posts()

        if isinstance(tags, str):
            tags = [
                x.strip()
                for x in tags.split(",")
                if x.strip()
            ]

        elif isinstance(tags, list):
            tags = [
                str(x).strip()
                for x in tags
                if str(x).strip()
            ]

        else:
            tags = []

        tags = list(dict.fromkeys(tags))

        base_slug = self.slugify(
            slug or title
        )

        final_slug = base_slug

        existing = {
            str(
                p.get("slug") or ""
            )
            for p in posts
        }

        suffix = 2

        while final_slug in existing:
            final_slug = (
                base_slug
                +
                "-"
                +
                str(suffix)
            )
            suffix += 1

        now = datetime.now(
            timezone.utc
        ).isoformat()

        if not excerpt:
            excerpt = body[:220].strip()

        post = {
            "slug": final_slug,
            "title": title,
            "excerpt": excerpt,
            "body": body,
            "tags": tags,
            "created_at": now,
            "updated_at": now,
        }

        posts.append(post)

        self.write_posts(posts)

        return post


    def get_post(self, slug):
        for post in self.read_posts():
            if str(post.get("slug") or "") == str(slug or ""):
                return post

        return None