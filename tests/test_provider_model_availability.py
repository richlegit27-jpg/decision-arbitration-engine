from nova_backend.services import provider_gateway_service as gateway


def test_invocable_model_list_requires_provider_credentials_and_client(
    monkeypatch,
):
    def openai_only_key(provider):
        if provider != "openai":
            raise RuntimeError("provider key is not configured")
        return "test-key"

    monkeypatch.setattr(gateway, "_get_provider_api_key", openai_only_key)
    monkeypatch.setattr(
        gateway.importlib.util,
        "find_spec",
        lambda name: object() if name == "openai" else None,
    )

    details = gateway.get_invocable_model_details()

    assert details
    assert all(item["provider"] == "openai" for item in details)
    assert all("test-key" not in str(item) for item in details)


def test_invocable_model_list_is_empty_without_gateway_provider(
    monkeypatch,
):
    def missing_key(_provider):
        raise RuntimeError("provider key is not configured")

    monkeypatch.setattr(gateway, "_get_provider_api_key", missing_key)
    monkeypatch.setattr(
        gateway.importlib.util,
        "find_spec",
        lambda _name: object(),
    )

    assert gateway.get_invocable_model_details() == []
