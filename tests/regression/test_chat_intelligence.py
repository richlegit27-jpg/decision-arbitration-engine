from __future__ import annotations

from types import MethodType, SimpleNamespace

import pytest

import nova_backend.services.chat.handle as chat_handle_module
import nova_backend.services.chat_service as chat_service_module
from nova_backend.services.chat_service import ChatService
from nova_backend.services.planner.decision_service import DecisionService


class _RoutingChatService:
    ROUTE_ATTACHMENT_ANALYSIS = "attachment_analysis"

    def _load_execution_state(self, _session_id):
        return {}

    def _nova_has_image_attachment_20260607(self, _attachments):
        return False


@pytest.fixture
def decision_service():
    return DecisionService(_RoutingChatService())


@pytest.mark.parametrize(
    "request",
    [
        "Build me a simple website for my landscaping business.",
        "Create a project to research and plan a YouTube channel.",
        "Could you make a website for my bakery?",
    ],
)
def test_explicit_conversational_build_requests_use_project_builder_route(
    decision_service, request
):
    decision = decision_service._decide_route(request)

    assert decision["intent"] == "project_creation"
    assert decision["route"] == "project_builder"


def test_project_creation_does_not_authorize_project_execution(decision_service):
    decision = decision_service._decide_route(
        "Create a project to research and plan a YouTube channel."
    )

    assert decision["intent"] == "project_creation"

    explicit_run = decision_service._decide_route(
        "Create a project to build a website, then run the project."
    )
    assert explicit_run["intent"] == "project_execution"


@pytest.mark.parametrize(
    "request",
    [
        "How would I build a shed?",
        "How do I create a project for a YouTube channel?",
        "Create a project plan for a website launch.",
    ],
)
def test_how_to_questions_and_project_plan_documents_stay_conversational(
    decision_service, request
):
    decision = decision_service._decide_route(request)

    assert decision["intent"] != "project_execution"


@pytest.mark.parametrize(
    "question",
    [
        "What's left?",
        "What did we finish?",
        "What's blocking us?",
        "Continue planning it.",
        "Explain the current task.",
    ],
)
def test_active_project_questions_route_to_project_state(
    decision_service, question
):
    decision = decision_service._decide_route(question)

    assert decision["route"] == "project_brain"
    assert decision["intent"] == "mission_control"


def test_legacy_project_request_check_uses_same_conservative_intent(
    decision_service,
):
    service = ChatService.__new__(ChatService)
    service.decision_service = decision_service

    assert service._looks_like_project_request(
        "Build me a simple website."
    ) is True
    assert service._looks_like_project_request(
        "Create a project plan for a website launch."
    ) is False


def test_project_creation_uses_authenticated_owner_sets_active_and_persists_chat(
    monkeypatch,
):
    calls = {}

    class ProjectBuilder:
        def build_project_from_request(self, **kwargs):
            calls["build"] = kwargs
            return {
                "project_id": "project-123",
                "project": {"id": "project-123", "title": "Landscaping site"},
                "tasks": [{"id": "task-1", "title": "Create homepage"}],
            }

    class ProjectWorkspace:
        def set_active_project(self, project_id):
            calls["active_project_id"] = project_id
            return {"id": project_id, "title": "Landscaping site", "active": True}

    class ChatStub:
        project_builder_service = ProjectBuilder()
        project_workspace_service = ProjectWorkspace()

        def safe_str(self, value):
            return str(value or "")

        def _create_session(self):
            return "session-123"

        def _build_user_message(self, text, attachments=None):
            return {"role": "user", "text": text, "attachments": attachments or []}

        def _build_assistant_message(self, text, meta=None, attachments=None):
            return {
                "role": "assistant",
                "text": text,
                "meta": meta or {},
                "attachments": attachments or [],
            }

        def _finalize_response(self, **kwargs):
            calls["finalize"] = kwargs
            return {
                "ok": True,
                "assistant_message": kwargs["assistant_msg"],
                "session_id": kwargs["session_id"],
            }

    monkeypatch.setattr(chat_handle_module, "get_current_user_id", lambda: "owner-a")
    response = chat_handle_module.chat_handle(
        ChatStub(),
        user_text="Build me a simple website for my landscaping business.",
        session_id="session-123",
        decision={
            "route": "project_builder",
            "mode": "project_creation",
            "intent": "project_creation",
        },
    )

    assert calls["build"]["owner_id"] == "owner-a"
    assert calls["active_project_id"] == "project-123"
    assert calls["finalize"]["project_id"] == "project-123"
    assert response["route"] == "project_builder"
    assert response["project_id"] == "project-123"
    assert response["ok"] is True


@pytest.mark.parametrize(
    "follow_up",
    [
        "why?",
        "use the second one",
        "fix it",
        "make that simpler",
        "what about the other one?",
        "finish it",
    ],
)
def test_follow_up_prompt_includes_recent_user_and_assistant_context(follow_up):
    transcript = [
        {"role": "system", "content": "internal instruction that must not leak"},
        {"role": "user", "text": "Option one is a blog. Option two is a portfolio."},
        {"role": "assistant", "text": "I recommend the portfolio because it highlights your work."},
        {"role": "assistant", "text": "Here is code:\n\ndef total(items):\n    return sum(items)\n"},
        {"role": "user", "text": "Now fix it."},
    ]
    service = SimpleNamespace(
        safe_str=lambda value: str(value or ""),
        memory_limit=6,
        _rank_memory_context=lambda **_kwargs: [],
        _format_memory_context=lambda _items: "",
        _get_session_payload=lambda _session_id: {"messages": transcript},
    )
    service._build_continuity_context = MethodType(
        ChatService._build_continuity_context,
        service,
    )

    prompt = ChatService._build_chat_input(
        service,
        user_text=follow_up,
        decision={},
        session_id="test-session",
    )

    assert "Option one is a blog" in prompt
    assert "I recommend the portfolio" in prompt
    assert "def total(items):\n    return sum(items)" in prompt
    assert "internal instruction that must not leak" not in prompt


def test_unrelated_question_does_not_dump_old_conversation():
    transcript = [
        {"role": "user", "text": "An old, unrelated private discussion."},
    ]
    context = ChatService._build_continuity_context(
        ChatService.__new__(ChatService),
        session={"messages": transcript},
        user_text="What is the boiling point of water?",
    )

    assert context == ""


@pytest.mark.parametrize(
    ("history", "follow_up", "expected"),
    [
        (
            [
                {"role": "user", "text": "Explain why leaves change color."},
                {"role": "assistant", "text": "Chlorophyll breaks down in autumn."},
                {"role": "user", "text": "Why?"},
                {"role": "assistant", "text": "Shorter days and cooler weather slow chlorophyll production."},
                {"role": "user", "text": "Give me an example."},
            ],
            "Make that simpler.",
            "Shorter days and cooler weather",
        ),
        (
            [
                {"role": "user", "text": "Here is my function:\n\ndef average(values):\n    return sum(values) / len(values)"},
                {"role": "assistant", "text": "It fails for an empty list."},
            ],
            "Fix it, then explain the change.",
            "return sum(values) / len(values)",
        ),
        (
            [
                {"role": "user", "text": "Uploaded notes.txt"},
                {"role": "assistant", "text": "The second issue is that the backup path is never checked."},
            ],
            "What was the second issue?",
            "backup path is never checked",
        ),
    ],
)
def test_realistic_follow_up_sequences_keep_the_referent(
    history, follow_up, expected
):
    context = ChatService._build_continuity_context(
        ChatService.__new__(ChatService),
        session={"messages": history},
        user_text=follow_up,
    )

    assert expected in context


def test_provider_failure_raises_instead_of_becoming_a_successful_answer(monkeypatch):
    def fail_provider(**_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        chat_service_module.model_gateway_service,
        "responses_create",
        fail_provider,
    )
    service = SimpleNamespace(
        _build_chat_input=lambda **_kwargs: "prompt",
        chat_model="test-model",
        username=None,
    )

    with pytest.raises(RuntimeError, match="could not complete this chat request"):
        ChatService._run_chat_model(
            service,
            user_text="hello",
            decision={},
        )


def test_generated_placeholders_and_code_whitespace_are_preserved(monkeypatch):
    generated = "Subject: Update for [name]\n\n```python\ndef add(a, b):\n    return a + b\n```"
    monkeypatch.setattr(
        chat_service_module.model_gateway_service,
        "responses_create",
        lambda **_kwargs: object(),
    )
    service = SimpleNamespace(
        _build_chat_input=lambda **_kwargs: "prompt",
        _safe_str=lambda value: str(value or ""),
        chat_model="test-model",
        username=None,
        response_handler=SimpleNamespace(
            extract_response_text=lambda _response: generated,
        ),
    )

    answer = ChatService._run_chat_model(
        service,
        user_text="Write an update email and a code example.",
        decision={},
    )

    assert answer == generated
    assert "    return a + b" in answer
