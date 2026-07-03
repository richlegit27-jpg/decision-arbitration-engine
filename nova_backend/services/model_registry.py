"""
Central Nova model registry.

Frontend/public aliases:
- nova-cheap
- nova-smart
- nova-pro
- nova-max

Provider model IDs can be changed with env vars without rewriting routes.
"""

from __future__ import annotations

import os
from typing import Any


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _env(name: str, fallback: str) -> str:
    return _clean(os.getenv(name), fallback)


def _public_aliases() -> dict[str, dict[str, str]]:
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
    return alias if alias in _public_aliases() else "nova-cheap"


def get_default_model() -> str:
    raw = _clean(os.getenv("OPENAI_MODEL"))

    if raw:
        return resolve_model(raw)

    aliases = _public_aliases()
    return aliases[get_default_model_alias()]["model"]


def get_public_models() -> list[str]:
    return list(_public_aliases().keys())


def get_model_details() -> list[dict[str, str]]:
    details = []

    for alias, info in _public_aliases().items():
        details.append(
            {
                "id": alias,
                "label": info["label"],
                "billing_tier": info["billing_tier"],
                "model": info["model"],
            }
        )

    return details


def get_allowed_provider_models() -> set[str]:
    allowed = {
        "gpt-4.1-mini",
        "gpt-4.1",
        "gpt-4o-mini",
    }

    for info in _public_aliases().values():
        model = _clean(info.get("model"))
        if model:
            allowed.add(model)

    vision_model = get_vision_model()
    if vision_model:
        allowed.add(vision_model)

    image_model = get_image_model()
    if image_model:
        allowed.add(image_model)

    return allowed


def resolve_model(requested_model: Any = None, fallback: str | None = None) -> str:
    requested = _clean(requested_model)
    aliases = _public_aliases()

    if requested in aliases:
        return aliases[requested]["model"]

    if requested in get_allowed_provider_models():
        return requested

    if fallback:
        fallback_text = _clean(fallback)

        if fallback_text in aliases:
            return aliases[fallback_text]["model"]

        if fallback_text in get_allowed_provider_models():
            return fallback_text

    return aliases[get_default_model_alias()]["model"]


def get_model_billing_tier(requested_model: Any = None) -> str:
    requested = _clean(requested_model)
    aliases = _public_aliases()

    if requested in aliases:
        return aliases[requested]["billing_tier"]

    resolved = resolve_model(requested)

    for info in aliases.values():
        if info["model"] == resolved:
            return info["billing_tier"]

    return "custom"


def get_vision_model() -> str:
    return _env("NOVA_VISION_MODEL", "gpt-4o-mini")


def get_image_model() -> str:
    return _env("NOVA_IMAGE_MODEL", "gpt-image-1")
