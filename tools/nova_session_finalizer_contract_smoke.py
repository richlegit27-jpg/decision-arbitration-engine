from nova_backend.services.session_response_finalizer_service import (
    finalize_session_response,
    assistant_message_already_saved,
)


def main():
    result = finalize_session_response(
        {"ok": True},
        "test_session",
    )

    assert result["finalizer_service"] is True
    assert result["finalizer_session_id"] == "test_session"

    messages = [
        {
            "role": "user",
            "text": "hello",
        },
        {
            "role": "assistant",
            "text": "already here",
        },
    ]

    assert assistant_message_already_saved(
        messages,
        assistant_text="already here",
    )

    assert not assistant_message_already_saved(
        messages,
        assistant_text="new answer",
    )

    print("NOVA SESSION FINALIZER CONTRACT SMOKE PASSED")


if __name__ == "__main__":
    main()