"""
Nova provider gateway.

Central provider dispatch layer for model execution.
"""

from __future__ import annotations

import os
import importlib.util
from typing import Any


def _get_provider_api_key(provider: str) -> str:
    env_names = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "xai": "XAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "ollama": "OLLAMA_API_KEY",
    }

    env_name = env_names.get(
        str(provider or "").strip().lower()
    )

    if not env_name:
        raise RuntimeError(
            f"Unsupported Nova model provider: {provider}"
        )

    value = str(
        os.getenv(env_name)
        or ""
    ).strip()

    if not value:
        raise RuntimeError(
            f"{env_name} is missing for provider '{provider}'."
        )

    return value


def get_provider_api_key(provider: str) -> str:
    return _get_provider_api_key(provider)


def provider_is_configured(provider: str) -> bool:
    try:
        _get_provider_api_key(provider)
        return True
    except Exception:
        return False


def _provider_client_available(provider: str) -> bool:
    module_by_provider = {
        "openai": "openai",
        "anthropic": "anthropic",
        "google": "google.genai",
        "xai": "openai",
        "deepseek": "openai",
    }
    module_name = module_by_provider.get(
        str(provider or "").strip().lower()
    )
    if not module_name:
        return False

    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def get_invocable_model_details() -> list[dict[str, str]]:
    """Return registry models whose gateway provider can be called here."""
    from nova_backend.model_registry import get_model_details

    return [
        item
        for item in get_model_details()
        if provider_is_configured(item.get("provider", ""))
        and _provider_client_available(item.get("provider", ""))
    ]


def select_invocable_model(requested: str, default: str) -> str:
    """Resolve a requested alias to one Nova can invoke in this process."""
    available = [
        item.get("id")
        for item in get_invocable_model_details()
        if item.get("id")
    ]
    requested = str(requested or "").strip()
    default = str(default or "").strip()
    if requested in available:
        return requested
    if default in available:
        return default
    return available[0] if available else ""


def create_openai_client():
    try:
        from openai import OpenAI
    except Exception as error:
        raise RuntimeError(
            f"OpenAI client is unavailable: {error}"
        ) from error

    return OpenAI(
        api_key=_get_provider_api_key("openai"),
    )

def create_xai_client():
    try:
        from openai import OpenAI
    except Exception as error:
        raise RuntimeError(
            f"xAI client is unavailable: {error}"
        ) from error

    return OpenAI(
        api_key=_get_provider_api_key("xai"),
        base_url="https://api.x.ai/v1",
    )

def create_deepseek_client():
    try:
        from openai import OpenAI
    except Exception as error:
        raise RuntimeError(
            f"DeepSeek client is unavailable: {error}"
        ) from error

    return OpenAI(
        api_key=_get_provider_api_key("deepseek"),
        base_url="https://api.deepseek.com",
    )

def create_anthropic_client():
    try:
        import anthropic
    except Exception as error:
        raise RuntimeError(
            "Anthropic client is unavailable. "
            "Install the anthropic package first."
        ) from error

    return anthropic.Anthropic(
        api_key=_get_provider_api_key("anthropic"),
    )

def create_google_client():
    try:
        from google import genai
    except Exception as error:
        raise RuntimeError(
            f"Google GenAI client is unavailable: {error}"
        ) from error

    return genai.Client(
        api_key=_get_provider_api_key("google"),
    )

def create_provider_client(provider: str):
    provider_name = str(
        provider or ""
    ).strip().lower()

    if provider_name == "openai":
        return create_openai_client()

    if provider_name == "anthropic":
        return create_anthropic_client()

    if provider_name == "google":
        return create_google_client()

    if provider_name == "xai":
        return create_xai_client()

    if provider_name == "deepseek":
        return create_deepseek_client()

    raise RuntimeError(
        f"Provider '{provider_name}' is not yet connected "
        "to Nova's execution gateway."
    )
