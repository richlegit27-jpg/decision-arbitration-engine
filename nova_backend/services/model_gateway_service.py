# NOVA_MODEL_GATEWAY_SERVICE_COMPAT_20260705
"""
Small compatibility module for model-call patching.

Regression tests monkeypatch chat_completions_create here so they can capture
the messages that /api/chat sends to the model without making a real OpenAI call.

NOVA_MODEL_GATEWAY_CREDIT_ENFORCEMENT_20260709:
- Keeps the same public wrapper function.
- Adds local billing credit enforcement at the OpenAI gateway boundary.
- Records usage after a successful provider response when the usage ledger exists.
- Removes Nova-only kwargs before sending the request to OpenAI.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Tuple


NOVA_GATEWAY_MINIMUM_CREDIT_COST = 1


def _nova_text(value: Any) -> str:
    try:
        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, list):
            return " ".join(_nova_text(item) for item in value)

        if isinstance(value, dict):
            parts = []

            for key in ("text", "content", "input_text", "output_text"):
                if key in value:
                    parts.append(_nova_text(value.get(key)))

            if not parts:
                parts = [_nova_text(item) for item in value.values()]

            return " ".join(part for part in parts if part)

        return str(value)
    except Exception:
        return ""


def _nova_messages_text(messages: Any) -> str:
    if not isinstance(messages, list):
        return _nova_text(messages)

    chunks = []

    for message in messages:
        if isinstance(message, dict):
            role = _nova_text(message.get("role"))
            content = _nova_text(message.get("content"))
            chunks.append((role + " " + content).strip())
        else:
            chunks.append(_nova_text(message))

    return "\n".join(chunk for chunk in chunks if chunk)


def _nova_estimate_tokens(value: Any) -> int:
    try:
        from nova_backend.services.usage_ledger_service import estimate_tokens

        return max(0, int(estimate_tokens(value)))
    except Exception:
        text = _nova_text(value)
        return max(1, int((len(text) + 3) / 4)) if text else 0


def _nova_extract_provider_usage(response: Any) -> Dict[str, int]:
    usage = getattr(response, "usage", None)

    if usage is None and isinstance(response, dict):
        usage = response.get("usage")

    if usage is None:
        return {}

    def get_value(name: str) -> int:
        try:
            if isinstance(usage, dict):
                return int(usage.get(name) or 0)

            return int(getattr(usage, name, 0) or 0)
        except Exception:
            return 0

    prompt_tokens = get_value("prompt_tokens") or get_value("input_tokens")
    completion_tokens = get_value("completion_tokens") or get_value("output_tokens")
    total_tokens = get_value("total_tokens") or prompt_tokens + completion_tokens

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "input_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def _nova_extract_response_text(response: Any) -> str:
    try:
        choices = getattr(response, "choices", None)

        if choices is None and isinstance(response, dict):
            choices = response.get("choices")

        if choices:
            first = choices[0]

            message = getattr(first, "message", None)

            if message is None and isinstance(first, dict):
                message = first.get("message")

            content = getattr(message, "content", None)

            if content is None and isinstance(message, dict):
                content = message.get("content")

            return _nova_text(content)
    except Exception:
        pass

    return ""


def _nova_pop_internal_kwargs(kwargs: Dict[str, Any]) -> Tuple[str, str, bool]:
    username = (
        kwargs.pop("nova_username", None)
        or kwargs.pop("_nova_username", None)
        or kwargs.pop("billing_username", None)
        or os.environ.get("NOVA_DEFAULT_USERNAME")
        or "richard"
    )

    session_id = (
        kwargs.pop("nova_session_id", None)
        or kwargs.pop("_nova_session_id", None)
        or kwargs.pop("billing_session_id", None)
        or kwargs.pop("session_id", None)
        or ""
    )

    enforce = kwargs.pop("nova_enforce_billing", None)

    if enforce is None:
        raw = os.environ.get("NOVA_MODEL_GATEWAY_BILLING_ENFORCED", "1")
        enforce = str(raw).strip().lower() not in {"0", "false", "no", "off"}

    username = str(username or "richard").strip().lower() or "richard"
    session_id = str(session_id or "").strip()

    return username, session_id, bool(enforce)


def _nova_preflight_credits(username: str, model: str) -> None:
    try:
        from nova_backend.services.billing_service import get_account

        account = get_account(username)
        plan = str(account.get("plan") or "").strip().lower()

        if plan == "developer":
            return

        credits = int(account.get("credits", 0) or 0)

        if credits < NOVA_GATEWAY_MINIMUM_CREDIT_COST:
            raise RuntimeError(
                "Nova billing blocked model call: insufficient credits "
                f"for {username}. Balance={credits}."
            )
    except RuntimeError:
        raise
    except Exception:
        # Billing should protect usage when available, but the gateway should not
        # hard-crash if local development billing state cannot be read.
        return


def _nova_consume_and_record_usage(
    username: str,
    session_id: str,
    model: str,
    messages: Any,
    response: Any,
    enforce: bool,
) -> Dict[str, Any]:
    input_text = _nova_messages_text(messages)
    output_text = _nova_extract_response_text(response)
    provider_usage = _nova_extract_provider_usage(response)

    input_tokens = int(
        provider_usage.get("input_tokens")
        or provider_usage.get("prompt_tokens")
        or _nova_estimate_tokens(input_text)
        or 0
    )

    output_tokens = int(
        provider_usage.get("output_tokens")
        or provider_usage.get("completion_tokens")
        or _nova_estimate_tokens(output_text)
        or 0
    )

    billing_result = {
        "ok": True,
        "cost": 0,
        "balance": None,
        "skipped": True,
    }

    if enforce:
        try:
            from nova_backend.services.billing_service import consume_usage

            billing_result = consume_usage(
                username=username,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            if not billing_result.get("ok"):
                raise RuntimeError(
                    "Nova billing usage consume failed after model call: "
                    + str(billing_result)
                )
        except RuntimeError:
            raise
        except Exception as exc:
            billing_result = {
                "ok": False,
                "error": str(exc),
                "skipped": False,
            }

    try:
        from nova_backend.services.usage_ledger_service import record_model_usage

        record_model_usage(
            session_id=session_id,
            route="model_gateway",
            model=model,
            input_text=input_text,
            output_text=output_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_usage=provider_usage,
        )
    except Exception:
        pass

    try:
        setattr(response, "_nova_billing", billing_result)
        setattr(response, "_nova_usage_tokens", {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        })
    except Exception:
        pass

    return billing_result


def chat_completions_create(*args, **kwargs):
    username, session_id, enforce = _nova_pop_internal_kwargs(kwargs)

    model = str(
        kwargs.get("model")
        or os.environ.get("OPENAI_MODEL")
        or os.environ.get("NOVA_OPENAI_MODEL")
        or "unknown"
    )

    messages = kwargs.get("messages")

    if enforce:
        _nova_preflight_credits(username=username, model=model)

    try:
        from openai import OpenAI
    except Exception as error:
        raise RuntimeError(f"OpenAI client is unavailable: {error}") from error

    client = OpenAI()
    response = client.chat.completions.create(*args, **kwargs)

    _nova_consume_and_record_usage(
        username=username,
        session_id=session_id,
        model=model,
        messages=messages,
        response=response,
        enforce=enforce,
    )

    return response
