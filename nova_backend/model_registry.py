"""
Central Nova model registry.

This file is intentionally outside nova_backend/services so tests can import it
without triggering nova_backend.services.__init__ or ChatService side effects.
"""

from __future__ import annotations

import os
from typing import Any


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _env(name: str, fallback: str) -> str:
    return _clean(os.getenv(name), fallback)


def _aliases() -> dict[str, dict[str, str]]:
    return {
        "nova-cheap": {
            "label": "Cheap",
            "billing_tier": "cheap",
            "model": _env("NOVA_MODEL_CHEAP", "gpt-4.1-mini"),
        },
        "nova-smart": {
            "label": "Smart",
            "billing_tier": "smart",
            "model": _env("NOVA_MODEL_SMART", "gpt-4.1-mini"),
        },
        "nova-pro": {
            "label": "Pro",
            "billing_tier": "pro",
            "model": _env("NOVA_MODEL_PRO", "gpt-4.1"),
        },
        "nova-max": {
            "label": "Max",
            "billing_tier": "max",
            "model": _env("NOVA_MODEL_MAX", _env("OPENAI_MODEL", "gpt-4.1-mini")),
        },
    }


def get_default_model_alias() -> str:
    alias = _clean(os.getenv("NOVA_DEFAULT_MODEL_ALIAS") or os.getenv("OPENAI_MODEL_ALIAS"), "nova-cheap")
    return alias if alias in _aliases() else "nova-cheap"


def get_public_models() -> list[str]:
    return list(_aliases().keys())


def get_model_details() -> list[dict[str, str]]:
    return [
        {
            "id": alias,
            "label": info["label"],
            "billing_tier": info["billing_tier"],
            "model": info["model"],
        }
        for alias, info in _aliases().items()
    ]


def get_vision_model() -> str:
    return _env("NOVA_VISION_MODEL", "gpt-4o-mini")


def get_image_model() -> str:
    return _env("NOVA_IMAGE_MODEL", "gpt-image-1")


def get_allowed_provider_models() -> set[str]:
    allowed = {
        "gpt-4.1-mini",
        "gpt-4.1",
        "gpt-4o-mini",
    }

    for info in _aliases().values():
        model = _clean(info.get("model"))
        if model:
            allowed.add(model)

    allowed.add(get_vision_model())
    allowed.add(get_image_model())

    return {item for item in allowed if item}


def _default_model_direct() -> str:
    aliases = _aliases()
    raw = _clean(os.getenv("OPENAI_MODEL"))

    if raw in aliases:
        return aliases[raw]["model"]

    if raw and raw in get_allowed_provider_models():
        return raw

    default_alias = get_default_model_alias()
    return aliases[default_alias]["model"]


def resolve_model(requested_model: Any = None, fallback: str | None = None) -> str:
    requested = _clean(requested_model)
    aliases = _aliases()

    if requested in aliases:
        return aliases[requested]["model"]

    if requested in get_allowed_provider_models():
        return requested

    fallback_text = _clean(fallback)

    if fallback_text in aliases:
        return aliases[fallback_text]["model"]

    if fallback_text in get_allowed_provider_models():
        return fallback_text

    return _default_model_direct()


def get_default_model() -> str:
    return _default_model_direct()


def get_model_billing_tier(requested_model: Any = None) -> str:
    requested = _clean(requested_model)
    aliases = _aliases()

    if requested in aliases:
        return aliases[requested]["billing_tier"]

    resolved = resolve_model(requested)

    for info in aliases.values():
        if info["model"] == resolved:
            return info["billing_tier"]

    return "custom"
