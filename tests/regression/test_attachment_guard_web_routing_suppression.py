# NOVA_ATTACHMENT_GUARD_WEB_ROUTING_SUPPRESSION_TESTS_20260705


def test_web_routing_suppression_installer_runs():
    import nova_backend.services.chat_service as chat_service

    assert hasattr(chat_service, "_nova_attachment_guard_install_web_routing_suppression")

    result = chat_service._nova_attachment_guard_install_web_routing_suppression()

    assert result["installed"] is True
    assert "wrapped_result_methods" in result
    assert "wrapped_bool_methods" in result


def test_web_routing_suppression_predicate_with_attachment_payload():
    import nova_backend.services.chat_service as chat_service

    assert chat_service._nova_attachment_guard_should_suppress_current_web_call(
        args=(
            "summarize this attached file",
            {
                "attachments": [
                    {
                        "filename": "notes.txt",
                        "summary": "Notes.",
                    }
                ]
            },
        ),
        kwargs={},
    ) is True


def test_web_routing_suppression_predicate_allows_explicit_web():
    import nova_backend.services.chat_service as chat_service

    assert chat_service._nova_attachment_guard_should_suppress_current_web_call(
        args=(
            "look up latest news about this attached company",
            {
                "attachments": [
                    {
                        "filename": "company.txt",
                        "summary": "Company.",
                    }
                ]
            },
        ),
        kwargs={},
    ) is False


def test_web_routing_bool_wrapper_blocks_attachment_turn(monkeypatch):
    import nova_backend.services.chat_service as chat_service

    class FakeService:
        def _should_use_web(self, user_text, payload=None):
            return True

    chat_service.ChatService = FakeService

    result = chat_service._nova_attachment_guard_install_web_routing_suppression()

    service = chat_service.ChatService()

    assert result["installed"] is True
    assert service._should_use_web(
        "summarize this attached file",
        {
            "attachments": [
                {
                    "filename": "notes.txt",
                    "summary": "Notes.",
                }
            ]
        },
    ) is False

    assert service._should_use_web(
        "look up latest news about this attached company",
        {
            "attachments": [
                {
                    "filename": "company.txt",
                    "summary": "Company.",
                }
            ]
        },
    ) is True


def test_web_routing_result_wrapper_returns_suppressed_result(monkeypatch):
    import nova_backend.services.chat_service as chat_service

    class FakeService:
        def _execute_web_search(self, user_text, payload=None):
            return {
                "ok": True,
                "results": ["should not be returned"],
            }

    chat_service.ChatService = FakeService

    result = chat_service._nova_attachment_guard_install_web_routing_suppression()

    service = chat_service.ChatService()

    output = service._execute_web_search(
        "summarize this attached file",
        {
            "attachments": [
                {
                    "filename": "notes.txt",
                    "summary": "Notes.",
                }
            ]
        },
    )

    assert result["installed"] is True
    assert output["suppressed"] is True
    assert output["reason"] == "attachment_focused_turn"
    assert output["results"] == []
