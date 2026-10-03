import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

from nova_backend.services.blog_route_service import BlogRouteService
from nova_backend.services.blog_service import BlogService


class TemporaryBlogService(BlogService):
    def __init__(self, path):
        self.path = Path(path)

    def _posts_path(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return self.path


class BlogPublishAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / "templates"))
        app.secret_key = "test-secret"
        BlogRouteService(TemporaryBlogService(Path(self.temp.name) / "posts.json")).install_routes(app)
        self.client = app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def login(self):
        with self.client.session_transaction() as browser_session:
            browser_session["nova_user_id"] = "writer"

    def test_anonymous_cannot_open_writer_or_publish(self):
        self.assertEqual(self.client.get("/blog/write").status_code, 302)
        with patch.dict(os.environ, {"NOVA_ADMIN_KEY": "secret"}):
            self.assertEqual(self.client.post("/api/blog/posts", json={"title": "T", "body": "B"}).status_code, 403)

    def test_publishing_fails_closed_without_admin_key_and_accepts_authenticated_admin(self):
        self.login()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.client.post("/api/blog/posts", json={"title": "T", "body": "B"}).status_code, 403)
        with patch.dict(os.environ, {"NOVA_ADMIN_KEY": "secret"}):
            response = self.client.post("/api/blog/posts", json={"title": "A useful Nova guide", "body": "Helpful content."}, headers={"X-NOVA-ADMIN-KEY": "secret"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["post"]["slug"], "a-useful-nova-guide")


if __name__ == "__main__":
    unittest.main()
