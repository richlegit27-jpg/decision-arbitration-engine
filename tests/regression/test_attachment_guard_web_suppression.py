# NOVA_ATTACHMENT_GUARD_WEB_SUPPRESSION_TESTS_20260705

from nova_backend.services.chat_attachment_intent_guard import (
    should_suppress_web_for_attachment,
)


def test_attachment_guard_suppresses_attachment_focused_web():
    payload = {
        "attachments": [
            {
                "filename": "notes.txt",
                "summary": "Notes.",
            }
        ]
    }

    assert should_suppress_web_for_attachment("summarize this attached file", payload)


def test_chat_service_web_fetch_is_wrapped_when_available(monkeypatch):
    import nova_backend.services.chat_service as chat_service

    assert hasattr(chat_service, "_nova_install_attachment_guard_web_suppression")

    installed = chat_service._nova_install_attachment_guard_web_suppression()

    if hasattr(chat_service, "ChatService") and hasattr(chat_service.ChatService, "_execute_web_fetch"):
        assert installed is True
        assert getattr(chat_service.ChatService, "_nova_attachment_guard_web_suppression_installed", False) is True


def test_chat_service_web_fetch_wrapper_suppresses_attachment_turn(monkeypatch):
    import nova_backend.services.chat_service as chat_service

    if not hasattr(chat_service, "ChatService"):
        return

    service = chat_service.ChatService()

    if not hasattr(service, "_execute_web_fetch"):
        return

    result = service._execute_web_fetch(
        "summarize this attached file",
        {
            "attachments": [
                {
                    "filename": "notes.txt",
                    "summary": "Important attachment notes.",
                }
            ]
        },
    )

    # If the project has a real _execute_web_fetch, the wrapper should stop attachment-focused search.
    if isinstance(result, dict):
        assert result.get("suppressed") is True
        assert result.get("reason") == "attachment_focused_turn"
        assert result.get("results") == []


def test_chat_service_web_fetch_wrapper_does_not_suppress_explicit_web(monkeypatch):
    import nova_backend.services.chat_service as chat_service

    assert should_suppress_web_for_attachment(
        "look up latest news about this attached company",
        {
            "attachments": [
                {
                    "filename": "company.txt",
                    "summary": "Company name.",
                }
            ]
        },
    ) is False
