from nova_backend.services import provider_gateway_service as gateway


def test_model_selection_rejects_models_without_an_invocable_provider(
    monkeypatch,
):
    monkeypatch.setattr(
        gateway,
        "get_invocable_model_details",
        lambda: [
            {"id": "gpt-4.1-mini", "provider": "openai"},
            {"id": "gpt-5-mini", "provider": "openai"},
        ],
    )

    assert gateway.select_invocable_model(
        "claude-opus-5", "gpt-4.1-mini"
    ) == "gpt-4.1-mini"
    assert gateway.select_invocable_model(
        "gpt-5-mini", "gpt-4.1-mini"
    ) == "gpt-5-mini"


def test_model_selection_has_no_unavailable_fallback(monkeypatch):
    monkeypatch.setattr(gateway, "get_invocable_model_details", lambda: [])

    assert gateway.select_invocable_model(
        "claude-opus-5", "gpt-4.1-mini"
    ) == ""
