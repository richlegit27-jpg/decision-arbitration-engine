from __future__ import annotations

from nova_backend.services.chat_service import ChatService


def require(condition, label, detail=""):
    if not condition:
        raise AssertionError(label + (" DETAIL: " + repr(detail) if detail else ""))

    print("PASS", label)


def main():
    print("NOVA PHASE 7B HIDDEN THREAD CONTINUITY REDACTION SMOKE")
    print("=" * 72)

    service = ChatService.__new__(ChatService)

    service._build_system_prompt = lambda decision=None: "SYSTEM"

    service._build_continuity_context = lambda session=None: (
        "Recent conversation:\\n"
        "User: after this let's fix attachments\\n"
        "Assistant: I can see you asked about an attachment, "
        "but no attachment reached /api/chat."
    )

    service._find_latest_execution_artifact = lambda session_id="": None

    session = {
        "id": "phase_7b_redaction_smoke",
        "messages": [
            {
                "role": "user",
                "text": "we are testing quiet unresolved threads",
            },
            {
                "role": "assistant",
                "text": "Okay.",
            },
            {
                "role": "user",
                "text": "after this let's fix attachments",
            },
            {
                "role": "assistant",
                "text": "Okay, later.",
            },
        ],
    }

    messages = service._compose_model_messages(
        "why did the conversation state brain matter",
        session=session,
        decision={"route": "chat"},
        memory_context="",
    )

    system_text = "\\n".join(
        str(message.get("content") or "")
        for message in messages
        if isinstance(message, dict)
        and message.get("role") == "system"
    ).lower()

    require(
        "there are explicitly deferred conversation threads" in system_text,
        "hidden-thread warning reaches model path",
    )

    require(
        "attachment" not in system_text,
        "deferred thread term is redacted from system context",
        system_text,
    )

    require(
        "[deferred thread hidden]" in system_text,
        "redaction marker appears in continuity",
        system_text,
    )

    print()
    print("=" * 72)
    print("NOVA PHASE 7B HIDDEN THREAD CONTINUITY REDACTION: REAL PASS")
    print("=" * 72)


if __name__ == "__main__":
    main()
