from nova_backend.services.chat_turn_pipeline import (
    build_chat_turn_from_request,
    build_model_messages,
    coerce_chat_payload,
)


def test_chat_turn_pipeline_clean_attachment_payload():
    payload = {
        "session_id": "session_test_clean_001",
        "message": "what is this image?",
        "attachments": [
            {
                "id": "upload_test_001",
                "filename": "test-image.png",
                "url": "/api/uploads/test-image.png",
                "mime_type": "image/png",
            }
        ],
    }

    turn = build_chat_turn_from_request(
        payload,
        history=[
            {
                "role": "user",
                "content": "we are debugging mobile attachments",
            }
        ],
        memory=[
            {
                "text": "User prefers exact paths and no blind patching.",
            }
        ],
        attachment_context=[
            {
                "filename": "test-image.png",
                "summary": "Uploaded image is available for model context.",
            }
        ],
        model="test-model",
    )

    messages = build_model_messages(turn)

    assert turn.session_id == "session_test_clean_001"
    assert turn.user_text == "what is this image?"
    assert turn.intent == "image_attachment"
    assert len(turn.attachments) == 1
    assert turn.attachments[0].kind == "image"
    assert messages[-1]["role"] == "user"
    assert "what is this image?" in messages[-1]["content"]


def test_chat_turn_pipeline_coerces_nested_payload_shapes():
    attachment = {
        "id": "upload_nested_001",
        "filename": "nested-image.png",
        "url": "/api/uploads/nested-image.png",
        "mime_type": "image/png",
    }

    payload = {
        "request_json": {
            "sessionId": "session_nested_001",
            "text": "summarize this attached file",
            "files": [attachment],
        }
    }

    coerced = coerce_chat_payload(payload)
    turn = build_chat_turn_from_request(payload)

    assert coerced["sessionId"] == "session_nested_001"
    assert coerced["text"] == "summarize this attached file"
    assert turn.session_id == "session_nested_001"
    assert turn.user_text == "summarize this attached file"
    assert len(turn.attachments) == 1
    assert turn.attachments[0].kind == "image"


def test_chat_turn_pipeline_coerces_args_and_alias_shapes():
    attachment = {
        "id": "upload_args_001",
        "filename": "args-image.png",
        "url": "/api/uploads/args-image.png",
        "mime_type": "image/png",
    }

    args_payload = {
        "arg_0": "session_args_001",
        "arg_1": "what is this image?",
        "kwargs": {
            "uploads": [attachment],
        },
    }

    alias_payload = {
        "sid": "session_alias_001",
        "input": "analyze attached image",
        "uploaded_files": [attachment],
    }

    args_turn = build_chat_turn_from_request(args_payload)
    alias_turn = build_chat_turn_from_request(alias_payload)

    assert args_turn.session_id == "session_args_001"
    assert args_turn.user_text == "what is this image?"
    assert len(args_turn.attachments) == 1

    assert alias_turn.session_id == "session_alias_001"
    assert alias_turn.user_text == "analyze attached image"
    assert len(alias_turn.attachments) == 1
