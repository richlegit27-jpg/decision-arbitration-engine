import os
import tempfile
import unittest
from pathlib import Path

from flask import Flask

from nova_backend.services.preferences_route_service import PreferencesRouteService


class PreferencesRouteServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Flask(__name__)
        self.app.secret_key = "test-secret"
        PreferencesRouteService(Path(self.temp.name)).install_routes(self.app)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def login_as(self, user_id):
        with self.client.session_transaction() as browser_session:
            browser_session["nova_user_id"] = user_id

    def test_anonymous_preferences_are_rejected(self):
        self.assertEqual(self.client.get("/api/settings").status_code, 401)
        self.assertEqual(self.client.patch("/api/settings", json={"theme": "light"}).status_code, 401)

    def test_settings_persist_per_authenticated_user_and_ignore_supplied_user_id(self):
        self.login_as("user-a")
        self.assertEqual(self.client.patch("/api/settings", json={"theme": "light", "user_id": "user-b"}).status_code, 400)
        saved = self.client.patch("/api/settings", json={"theme": "light"})
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json["preferences"]["theme"], "light")
        self.login_as("user-b")
        other = self.client.get("/api/settings").json["preferences"]
        self.assertEqual(other["theme"], "dark")
        self.login_as("user-a")
        self.assertEqual(self.client.get("/api/settings").json["preferences"]["theme"], "light")

    def test_invalid_values_are_rejected_without_changing_stored_preference(self):
        self.login_as("user-a")
        self.assertEqual(self.client.patch("/api/settings", json={"theme": "neon"}).status_code, 400)
        self.assertEqual(self.client.patch("/api/settings", json={"enter_to_send": "false"}).status_code, 400)
        self.assertEqual(self.client.get("/api/settings").json["preferences"]["theme"], "dark")


if __name__ == "__main__":
    unittest.main()
