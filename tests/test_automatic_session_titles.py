import tempfile
import unittest
from pathlib import Path

from nova_backend.services.session_service import (
    SessionService,
    _nova_session_title_from_message_20260624,
)


class AutomaticSessionTitleTests(unittest.TestCase):
    def test_greetings_and_non_user_messages_do_not_create_titles(self):
        self.assertEqual(_nova_session_title_from_message_20260624({"role": "user", "text": "hello"}), "")
        self.assertEqual(_nova_session_title_from_message_20260624({"role": "assistant", "text": "A response"}), "")

    def test_first_meaningful_message_titles_and_persists_session(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sessions.json"
            service = SessionService(path)
            session = service.create_session(user_id="user-a")
            self.assertEqual(session["title"], "New Chat")
            service.append_message(session["id"], {"role": "user", "text": "Create a project to build a calculator website."}, user_id="user-a")
            restored = SessionService(path).get_session(session["id"], user_id="user-a")
            self.assertEqual(restored["title"], "Calculator Website Project")

    def test_greeting_waits_for_meaningful_followup_and_manual_rename_wins(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SessionService(Path(directory) / "sessions.json")
            session = service.create_session(user_id="user-a")
            service.append_message(session["id"], {"role": "user", "text": "hello"}, user_id="user-a")
            self.assertEqual(service.get_session(session["id"], user_id="user-a")["title"], "New Chat")
            service.append_message(session["id"], {"role": "user", "text": "Why does the sky look blue?"}, user_id="user-a")
            self.assertEqual(service.get_session(session["id"], user_id="user-a")["title"], "Why does the sky look blue")
            service.rename(session["id"], "My chosen title", user_id="user-a")
            service.set_auto_title_if_untitled(session["id"], "Late automatic title", user_id="user-a")
            service.append_message(session["id"], {"role": "user", "text": "Tell me more about atmospheric scattering."}, user_id="user-a")
            self.assertEqual(service.get_session(session["id"], user_id="user-a")["title"], "My chosen title")

    def test_titles_are_scoped_to_the_session_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SessionService(Path(directory) / "sessions.json")
            session = service.create_session(user_id="user-a")
            service.append_message(session["id"], {"role": "user", "text": "Explain quantum computing simply."}, user_id="user-a")
            self.assertIsNone(service.get_session(session["id"], user_id="user-b"))


if __name__ == "__main__":
    unittest.main()
