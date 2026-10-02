"""
Central Nova model registry.

Models are ordered from cheapest to most expensive so the user naturally
understands that moving down the list increases capability and cost.
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
        "gpt-5-nano": {
            "label": "GPT-5 Nano",
            "description": "Fastest and cheapest for simple tasks.",
            "billing_tier": "cheapest",
            "provider": "openai",
            "model": "gpt-5-nano",
        },
        "gpt-5.4-nano": {
            "label": "GPT-5.4 Nano",
            "description": "Cheap high-volume tasks, extraction, and classification.",
            "billing_tier": "cheap",
            "provider": "openai",
            "model": "gpt-5.4-nano",
        },
        "gpt-5.6-luna": {
            "label": "GPT-5.6 Luna",
            "description": "Modern model optimized for cost-sensitive workloads.",
            "billing_tier": "cheap",
            "provider": "openai",
            "model": "gpt-5.6-luna",
        },
        "gpt-4o-mini": {
            "label": "GPT-4o Mini",
            "description": "Fast and affordable for focused everyday tasks.",
            "billing_tier": "cheap",
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
        "gpt-4.1-mini": {
            "label": "GPT-4.1 Mini",
            "description": "Reliable and fast everyday messaging.",
            "billing_tier": "standard",
            "provider": "openai",
            "model": "gpt-4.1-mini",
        },
        "gpt-5-mini": {
            "label": "GPT-5 Mini",
            "description": "Strong intelligence for high-volume work.",
            "billing_tier": "standard",
            "provider": "openai",
            "model": "gpt-5-mini",
        },
        "gpt-5.4-mini": {
            "label": "GPT-5.4 Mini",
            "description": "Strong coding, reasoning, and agent work at lower cost.",
            "billing_tier": "standard",
            "provider": "openai",
            "model": "gpt-5.4-mini",
        },
        "gpt-5.6-terra": {
            "label": "GPT-5.6 Terra",
            "description": "Balanced intelligence and cost.",
            "billing_tier": "balanced",
            "provider": "openai",
            "model": "gpt-5.6-terra",
        },
        "gpt-4.1": {
            "label": "GPT-4.1",
            "description": "Smart general-purpose model for serious work.",
            "billing_tier": "advanced",
            "provider": "openai",
            "model": "gpt-4.1",
        },
        "gpt-4o": {
            "label": "GPT-4o",
            "description": "Fast and flexible multimodal model.",
            "billing_tier": "advanced",
            "provider": "openai",
            "model": "gpt-4o",
        },
        "gpt-5.4": {
            "label": "GPT-5.4",
            "description": "Flagship model for complex professional work.",
            "billing_tier": "premium",
            "provider": "openai",
            "model": "gpt-5.4",
        },
        "gpt-5.5": {
            "label": "GPT-5.5",
            "description": "Advanced coding and professional intelligence.",
            "billing_tier": "premium",
            "provider": "openai",
            "model": "gpt-5.5",
        },
        "gpt-5.6": {
            "label": "GPT-5.6",
            "description": "High-end reasoning and professional work.",
            "billing_tier": "premium",
            "provider": "openai",
            "model": "gpt-5.6",
        },
        "astra": {
            "label": "Astra",
            "description": "Nova's premium reasoning mode for difficult thinking and complex work.",
            "billing_tier": "premium",
            "provider": "openai",
            "model": _env(
                "NOVA_MODEL_ASTRA",
                "gpt-5.6",
            ),
        },
        "gpt-5-pro": {
            "label": "GPT-5 Pro",
            "description": "Maximum GPT-5 quality for difficult tasks.",
            "billing_tier": "pro",
            "provider": "openai",
            "model": "gpt-5-pro",
        },
        "gpt-5.4-pro": {
            "label": "GPT-5.4 Pro",
            "description": "Smarter and more precise for extremely difficult work.",
            "billing_tier": "pro",
            "provider": "openai",
            "model": "gpt-5.4-pro",
        },
        "gpt-5.5-pro": {
            "label": "GPT-5.5 Pro",
            "description": "Maximum professional reasoning and precision.",
            "billing_tier": "maximum",
            "provider": "openai",
            "model": "gpt-5.5-pro",
        },
        "claude-haiku-4-5": {
            "label": "Claude Haiku 4.5",
            "description": "Fast Anthropic model for efficient everyday work.",
            "billing_tier": "standard",
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
        },
        "claude-sonnet-5": {
            "label": "Claude Sonnet 5",
            "description": "Advanced Anthropic model for demanding general-purpose work.",
            "billing_tier": "premium",
            "provider": "anthropic",
            "model": "claude-sonnet-5",
        },
        "claude-opus-5": {
            "label": "Claude Opus 5",
            "description": "High-end Anthropic model for complex reasoning and professional work.",
            "billing_tier": "maximum",
            "provider": "anthropic",
            "model": "claude-opus-5",
        },
        "gemini-3.8-flash": {
            "label": "Gemini 3.8 Flash",
            "description": "Google's latest stable Flash model for advanced general-purpose and agentic work.",
            "billing_tier": "standard",
            "provider": "google",
            "model": "gemini-3.8-flash",
        },
        "gemini-3.7-flash": {
            "label": "Gemini 3.7 Flash",
            "description": "Google stable Flash model for coding, agentic workflows, and multi-step execution.",
            "billing_tier": "standard",
            "provider": "google",
            "model": "gemini-3.7-flash",
        },
        "gemini-3.6-flash": {
            "label": "Gemini 3.6 Flash",
            "description": "Google stable multimodal Flash model for general-purpose work.",
            "billing_tier": "standard",
            "provider": "google",
            "model": "gemini-3.6-flash",
        },
        "gemini-3.5-flash": {
            "label": "Gemini 3.5 Flash",
            "description": "Google stable Flash model for routine and high-throughput workloads.",
            "billing_tier": "standard",
            "provider": "google",
            "model": "gemini-3.5-flash",
        },
        "gemini-3.5-flash-lite": {
            "label": "Gemini 3.5 Flash-Lite",
            "description": "Google's cost-efficient stable model for high-throughput execution.",
            "billing_tier": "standard",
            "provider": "google",
            "model": "gemini-3.5-flash-lite",
        },
        "gemini-3.1-flash-lite": {
            "label": "Gemini 3.1 Flash-Lite",
            "description": "Google's efficient stable model for speed, scale, and cost-sensitive workloads.",
            "billing_tier": "standard",
            "provider": "google",
            "model": "gemini-3.1-flash-lite",
        },
        "gemini-3.1-pro": {
            "label": "Gemini 3.1 Pro",
            "description": "Google preview model for advanced reasoning, complex problem solving, and agentic work.",
            "billing_tier": "premium",
            "provider": "google",
            "model": "gemini-3.1-pro-preview",
        },
        "grok-4.7": {
            "label": "Grok 4.7",
            "description": "xAI's latest Grok model for advanced general-purpose work.",
            "billing_tier": "premium",
            "provider": "xai",
            "model": "grok-4.7",
        },
        "grok-4.6": {
            "label": "Grok 4.6",
            "description": "xAI Grok model for advanced reasoning and general-purpose work.",
            "billing_tier": "premium",
            "provider": "xai",
            "model": "grok-4.6",
        },
        "grok-4.5": {
            "label": "Grok 4.5",
            "description": "xAI Grok model for general-purpose and agentic workloads.",
            "billing_tier": "premium",
            "provider": "xai",
            "model": "grok-4.5",
        },
        "grok-4.3": {
            "label": "Grok 4.3",
            "description": "xAI Grok model for general-purpose workloads.",
            "billing_tier": "standard",
            "provider": "xai",
            "model": "grok-4.3",
        },
        "deepseek-flash": {
            "label": "DeepSeek V4.1 Flash",
            "description": "DeepSeek's current Flash model for fast general-purpose and agentic work.",
            "billing_tier": "standard",
            "provider": "deepseek",
            "model": "deepseek-flash",
        },
        "deepseek-v4-flash": {
            "label": "DeepSeek V4 Flash",
            "description": "DeepSeek's V4 Flash API model.",
            "billing_tier": "standard",
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
        },
        "deepseek-v4-pro": {
            "label": "DeepSeek V4 Pro",
            "description": "DeepSeek's V4 Pro model for demanding reasoning and agent workflows.",
            "billing_tier": "premium",
            "provider": "deepseek",
            "model": "deepseek-v4-pro",
        },
    }



def get_default_model_alias() -> str:
    alias = _clean(
        os.getenv("NOVA_DEFAULT_MODEL_ALIAS")
        or os.getenv("OPENAI_MODEL_ALIAS"),
        "gpt-4.1-mini",
    )

    return (
        alias
        if alias in _aliases()
        else "gpt-4.1-mini"
    )


def get_public_models() -> list[str]:
    return list(_aliases().keys())


def get_model_details() -> list[dict[str, str]]:
    return [
        {
            "id": alias,
            "label": info["label"],
            "description": info["description"],
            "billing_tier": info["billing_tier"],
            "provider": info["provider"],
            "model": info["model"],
        }
        for alias, info in _aliases().items()
    ]


def get_vision_model() -> str:
    return _env(
        "NOVA_VISION_MODEL",
        "gpt-4o",
    )


def get_image_model() -> str:
    return _env(
        "NOVA_IMAGE_MODEL",
        "gpt-image-1",
    )


def get_allowed_provider_models() -> set[str]:
    allowed = set()

    for info in _aliases().values():
        model = _clean(info.get("model"))

        if model:
            allowed.add(model)

    allowed.add(get_vision_model())
    allowed.add(get_image_model())

    return {
        item
        for item in allowed
        if item
    }


def _default_model_direct() -> str:
    aliases = _aliases()

    raw = _clean(os.getenv("OPENAI_MODEL"))

    if raw in aliases:
        return aliases[raw]["model"]

    if raw and raw in get_allowed_provider_models():
        return raw

    default_alias = get_default_model_alias()

    return aliases[default_alias]["model"]


def resolve_model(
    requested_model: Any = None,
    fallback: str | None = None,
) -> str:
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


def get_model_billing_tier(
    requested_model: Any = None,
) -> str:
    requested = _clean(requested_model)
    aliases = _aliases()

    if requested in aliases:
        return aliases[requested]["billing_tier"]

    resolved = resolve_model(requested)

    for info in aliases.values():
        if info["model"] == resolved:
            return info["billing_tier"]

    return "custom"


def get_model_provider(
    requested_model: Any = None,
) -> str:
    requested = _clean(requested_model)
    aliases = _aliases()

    if requested in aliases:
        return aliases[requested]["provider"]

    resolved = resolve_model(requested)

    for info in aliases.values():
        if info["model"] == resolved:
            return info["provider"]

    return "openai"