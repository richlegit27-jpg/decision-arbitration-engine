from pathlib import Path
from datetime import datetime

# Path to the test file to patch
TEST_FILE_PATH = Path(r"C:\Users\Owner\nova\tests\test_api_chat_smoke.py")

# Backup
backup = TEST_FILE_PATH.with_suffix(
    TEST_FILE_PATH.suffix + f".BAK_mock_openai_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
backup.write_text(TEST_FILE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
print(f"BACKUP: {backup}")

# Replacement code with monkeypatch mock
replacement = '''from __future__ import annotations

def test_api_chat_endpoint_smoke(monkeypatch):
    from app import app, chat_service

    def fake_handle(user_text, session_id="", attachments=None):
        return {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": "mock assistant response",
            },
            "active_session_id": session_id or "mock_session",
            "session_id": session_id or "mock_session",
            "session": {
                "id": session_id or "mock_session",
                "messages": [],
            },
            "debug": {
                "mocked": True,
            },
        }

    monkeypatch.setattr(chat_service, "handle", fake_handle)

    client = app.test_client()

    response = client.post(
        "/api/chat",
        json={
            "user_text": "hello",
            "session_id": "pytest_mock_session",
            "attachments": [],
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["assistant_message"]["text"] == "mock assistant response"
    assert payload["active_session_id"] == "pytest_mock_session"
'''

# Write replacement to test file
TEST_FILE_PATH.write_text(replacement, encoding="utf-8")
print("OK: test_api_chat_smoke.py now mocks chat_service.handle()")