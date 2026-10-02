
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

    assert should_suppress_web_for_attachment(
        "summarize this attached file",
        payload,
    )


def test_chat_service_web_fetch_is_wrapped_when_available(monkeypatch):
    import nova_backend.services.chat_service as chat_service

    assert hasattr(
        chat_service,
        "_nova_install_attachment_guard_web_suppression",
    )

    installed = (
        chat_service
        ._nova_install_attachment_guard_web_suppression()
    )

    assert isinstance(installed, dict)
    assert installed.get("installed") is True
    assert installed.get("guard") == (
        "attachment_web_routing_suppression"
    )

    if hasattr(chat_service, "ChatService"):
        cls = chat_service.ChatService

        assert "_should_use_web" in installed.get(
            "wrapped_bool_methods", []
        )

        if hasattr(cls, "_execute_web_search"):
            assert "_execute_web_search" in installed.get(
                "wrapped_result_methods", []
            )


def test_chat_service_web_fetch_wrapper_suppresses_attachment_turn(
    monkeypatch,
):
    import nova_backend.services.chat_service as chat_service

    cls = getattr(chat_service, "ChatService", None)
    if cls is None or not hasattr(cls, "_execute_web_search"):
        return

    installed = (
        chat_service
        ._nova_install_attachment_guard_web_suppression()
    )
    assert installed.get("installed") is True

    # Exercise the wrapped search method without initializing ChatService
    # or invoking a real external web service.
    service = object.__new__(cls)

    result = service._execute_web_search(
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

    assert isinstance(result, dict)
    assert result.get("suppressed") is True
    assert result.get("reason") == "attachment_focused_turn"
    assert result.get("results") == []


def test_chat_service_web_fetch_wrapper_does_not_suppress_explicit_web(
    monkeypatch,
):
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