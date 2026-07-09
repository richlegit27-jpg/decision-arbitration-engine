from nova_backend.services.chat_service import ChatService


def make_service():
    service = ChatService.__new__(ChatService)
    service.chat_model = "test-model"
    return service


def build_shadow(service):
    payload = {
        "session_id": "session_feature_flag_001",
        "message": "what is this image?",
        "attachments": [
            {
                "id": "upload_feature_001",
                "filename": "feature-image.png",
                "url": "/api/uploads/feature-image.png",
                "mime_type": "image/png",
            }
        ],
    }

    return service._nova_build_chat_turn_shadow(
        payload,
        metadata={"source": "test_chat_turn_feature_flag_adapter"},
    )


def test_chat_turn_messages_disabled_by_default(monkeypatch):
    service = make_service()
    build_shadow(service)

    fallback_messages = [
        {
            "role": "user",
            "content": "fallback message",
        }
    ]

    monkeypatch.delenv("NOVA_USE_CHAT_TURN_MESSAGES", raising=False)

    selected = service._nova_select_model_messages(fallback_messages)

    assert selected is fallback_messages
    assert selected[0]["content"] == "fallback message"


def test_chat_turn_messages_enabled_by_env_flag(monkeypatch):
    service = make_service()
    turn, shadow_messages = build_shadow(service)

    fallback_messages = [
        {
            "role": "user",
            "content": "fallback message",
        }
    ]

    monkeypatch.setenv("NOVA_USE_CHAT_TURN_MESSAGES", "1")

    selected = service._nova_select_model_messages(fallback_messages)

    assert selected is shadow_messages
    assert selected[-1]["role"] == "user"
    assert selected[-1]["content"] == "what is this image?"
    assert turn.intent == "image_attachment"


def test_chat_turn_messages_flag_accepts_true_values(monkeypatch):
    service = make_service()

    for value in ["1", "true", "yes", "on", "enabled"]:
        monkeypatch.setenv("NOVA_USE_CHAT_TURN_MESSAGES", value)
        assert service._nova_use_chat_turn_messages_enabled() is True


def test_chat_turn_messages_flag_rejects_false_values(monkeypatch):
    service = make_service()

    for value in ["", "0", "false", "no", "off", "disabled"]:
        monkeypatch.setenv("NOVA_USE_CHAT_TURN_MESSAGES", value)
        assert service._nova_use_chat_turn_messages_enabled() is False
