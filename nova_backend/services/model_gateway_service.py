# NOVA_MODEL_GATEWAY_SERVICE_COMPAT_20260705
"""
Small compatibility module for model-call patching.

Regression tests monkeypatch chat_completions_create here so they can capture
the messages that /api/chat sends to the model without making a real OpenAI call.
"""

from __future__ import annotations


def chat_completions_create(*args, **kwargs):
    try:
        from openai import OpenAI
    except Exception as error:
        raise RuntimeError(f"OpenAI client is unavailable: {error}") from error

    client = OpenAI()
    return client.chat.completions.create(*args, **kwargs)
