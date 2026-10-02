"""
Nova provider execution service.

Normalizes provider-specific text execution behind one interface.
"""

from __future__ import annotations

from typing import Any


def execute_anthropic(
    client: Any,
    model: str,
    messages: list,
    max_tokens: int = 4096,
    **kwargs,
):
    system = None
    anthropic_messages = []

    for message in messages or []:
        if not isinstance(message, dict):
            continue

        role = str(
            message.get("role") or "user"
        ).strip().lower()

        content = message.get("content") or ""

        if role == "system":
            system = str(content)
            continue

        if role not in {"user", "assistant"}:
            role = "user"

        anthropic_messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    request = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": anthropic_messages,
    }

    if system:
        request["system"] = system

    for key in (
        "temperature",
        "top_p",
        "top_k",
        "stop_sequences",
    ):
        if key in kwargs and kwargs[key] is not None:
            request[key] = kwargs[key]

    return client.messages.create(
        **request
    )


def execute_provider_chat(
    provider: str,
    client: Any,
    model: str,
    messages: list,
    **kwargs,
):
    provider_name = str(
        provider or ""
    ).strip().lower()

    if provider_name == "anthropic":
        return execute_anthropic(
            client=client,
            model=model,
            messages=messages,
            **kwargs,
        )

    if provider_name == "google":
        return execute_google(
            client=client,
            model=model,
            messages=messages,
            **kwargs,
        )

    if provider_name == "xai":
        return client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )

    raise RuntimeError(
        f"Provider '{provider_name}' does not have "
        "a chat execution adapter."
    )

def execute_google(
    client: Any,
    model: str,
    messages: list,
    **kwargs,
):
    system = None
    contents = []

    for message in messages or []:
        if not isinstance(message, dict):
            continue

        role = str(
            message.get("role") or "user"
        ).strip().lower()

        content = message.get("content") or ""

        if role == "system":
            system = str(content)
            continue

        contents.append(
            str(content)
        )

    request = {
        "model": model,
        "contents": contents,
    }

    config_kwargs = {}

    if system:
        config_kwargs["system_instruction"] = system

    if "max_tokens" in kwargs and kwargs["max_tokens"] is not None:
        config_kwargs["max_output_tokens"] = kwargs["max_tokens"]

    for key in (
        "temperature",
        "top_p",
        "top_k",
        "stop_sequences",
    ):
        if key in kwargs and kwargs[key] is not None:
            config_kwargs[key] = kwargs[key]

    if config_kwargs:
        from google.genai import types

        request["config"] = types.GenerateContentConfig(
            **config_kwargs
        )

    return client.models.generate_content(
        **request
    )