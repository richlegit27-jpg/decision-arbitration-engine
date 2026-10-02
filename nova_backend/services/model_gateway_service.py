# NOVA_MODEL_GATEWAY_SERVICE_COMPAT_20260705
"""
Central Nova model gateway.

All OpenAI calls pass Nova's API key explicitly instead of relying on
whatever OPENAI_API_KEY happens to exist in the running process environment.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Tuple

from dotenv import load_dotenv


NOVA_GATEWAY_MINIMUM_CREDIT_COST = 1


# ---------------------------------------------------------------------
# NOVA ENVIRONMENT / OPENAI CLIENT
# ---------------------------------------------------------------------

NOVA_ROOT = Path(__file__).resolve().parents[2]
NOVA_ENV_PATH = NOVA_ROOT / ".env"

load_dotenv(
    NOVA_ENV_PATH,
    override=True,
)


def _get_openai_api_key() -> str:
    """
    Always load Nova's project API key directly from Nova's environment.
    """

    load_dotenv(
        NOVA_ENV_PATH,
        override=True,
    )

    api_key = str(
        os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing from "
            + str(NOVA_ENV_PATH)
        )

    return api_key


def _get_openai_client():
    """
    Create an OpenAI client using Nova's explicitly loaded API key.
    """

    try:
        from openai import OpenAI
    except Exception as error:
        raise RuntimeError(
            f"OpenAI client is unavailable: {error}"
        ) from error

    api_key = _get_openai_api_key()

    return OpenAI(
        api_key=api_key,
    )


# ---------------------------------------------------------------------
# MODEL RESOLUTION
# ---------------------------------------------------------------------

def resolve_nova_model(model):
    from nova_backend.model_registry import resolve_model

    return resolve_model(model)


def resolve_nova_task_model(
    model=None,
    text="",
    intent="",
):
    from nova_backend.model_registry import (
        get_default_model_alias,
        get_model_provider,
        resolve_model,
    )

    # Explicit user-selected model always wins.
    if model:
        return resolve_model(model)

    intent = str(
        intent or ""
    ).lower().strip()

    if intent in {
        "coding",
        "debugging",
    }:
        return resolve_model("gpt-5.4-mini")

    if intent in {
        "planning",
        "working_state",
        "reasoning",
    }:
        return resolve_model("astra")

    if intent in {
        "image",
        "vision",
    }:
        from nova_backend.model_registry import (
            get_vision_model,
        )

        return get_vision_model()

    text = str(text or "").lower()

    if any(
        word in text
        for word in [
            "python",
            "code",
            "debug",
            "bug",
            "error",
            "function",
            "class",
            "backend",
            "frontend",
            "javascript",
        ]
    ):
        return resolve_model("gpt-5.4-mini")

    return resolve_model(
        get_default_model_alias()
    )


# ---------------------------------------------------------------------
# TEXT HELPERS
# ---------------------------------------------------------------------

def _nova_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts = []

        for item in value:
            if isinstance(item, str):
                parts.append(item)

            elif isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("content")
                    or item.get("input_text")
                    or ""
                )

                if text:
                    parts.append(str(text))

        return "\n".join(parts)

    if isinstance(value, dict):
        return str(
            value.get("text")
            or value.get("content")
            or ""
        )

    return str(value)


def _nova_messages_text(messages: Any) -> str:
    if not isinstance(messages, list):
        return _nova_text(messages)

    parts = []

    for message in messages:
        if isinstance(message, dict):
            content = message.get("content")

            if content:
                parts.append(
                    _nova_text(content)
                )

    return "\n".join(parts)


# ---------------------------------------------------------------------
# INTERNAL NOVA KWARGS
# ---------------------------------------------------------------------

def _nova_pop_internal_kwargs(
    kwargs: Dict[str, Any],
) -> Tuple[Any, Any, Any, bool]:

    user_id = kwargs.pop(
        "nova_user_id",
        None,
    )

    username = kwargs.pop(
        "nova_username",
        None,
    )

    session_id = kwargs.pop(
        "nova_session_id",
        None,
    )

    enforce = bool(
        kwargs.pop(
            "nova_enforce_credits",
            False,
        )
    )

    # Resolve the authenticated identity centrally when the
    # caller did not explicitly provide a user ID.
    if not str(user_id or "").strip():
        try:
            from flask import g, has_request_context, session

            if has_request_context():
                auth_user = getattr(
                    g,
                    "nova_auth_user",
                    None,
                )

                if isinstance(auth_user, dict):
                    user_id = auth_user.get("id")
                elif auth_user is not None:
                    user_id = getattr(
                        auth_user,
                        "id",
                        None,
                    )

                if not str(user_id or "").strip():
                    user_id = session.get("nova_user_id")

        except Exception:
            # Never infer authenticated identity from a username.
            user_id = None

    return (
        user_id,
        username,
        session_id,
        enforce,
    )
# ---------------------------------------------------------------------
# CREDIT PREFLIGHT
# ---------------------------------------------------------------------


def _nova_preflight_credits(
    user_id=None,
    username=None,
    model=None,
):
    if not str(user_id or "").strip():
        raise RuntimeError(
            "Nova credit enforcement requires an authenticated user ID."
        )

    from nova_backend.services import billing_service

    balance = billing_service.get_balance(
        user_id=user_id,
        username=username,
    )

    minimum_cost = billing_service.model_cost(
        model=model,
        input_tokens=1,
        output_tokens=0,
    )

    if balance < minimum_cost:
        raise RuntimeError(
            "Insufficient Nova credits. "
            f"Balance: {balance}; "
            f"minimum required: {minimum_cost}."
        )

    return {
        "ok": True,
        "balance": balance,
    }

# ---------------------------------------------------------------------
# USAGE / BILLING
# ---------------------------------------------------------------------

def _nova_consume_and_record_usage(
    user_id=None,
    username=None,
    session_id=None,
    model=None,
    messages=None,
    response=None,
    enforce=False,
):
    billing_result = None
    billing_error = None

    try:
        input_text = _nova_text(messages)

        output_text = ""

        if hasattr(response, "choices"):
            choices = getattr(
                response,
                "choices",
                None,
            ) or []

            if choices:
                choice = choices[0]

                message = getattr(
                    choice,
                    "message",
                    None,
                )

                output_text = str(
                    getattr(
                        message,
                        "content",
                        "",
                    )
                    or ""
                )

        elif hasattr(response, "output_text"):
            output_text = str(
                getattr(
                    response,
                    "output_text",
                    "",
                )
                or ""
            )

        usage = getattr(
            response,
            "usage",
            None,
        )

        input_tokens = 0
        output_tokens = 0
        provider_usage = None

        if usage:
            if hasattr(usage, "model_dump"):
                provider_usage = usage.model_dump()
            elif isinstance(usage, dict):
                provider_usage = usage
            else:
                provider_usage = {
                    key: value
                    for key in (
                        "prompt_tokens",
                        "completion_tokens",
                        "total_tokens",
                        "input_tokens",
                        "output_tokens",
                    )
                    if (value := getattr(usage, key, None)) is not None
                }

            if isinstance(usage, dict):
                input_tokens = int(
                    usage.get("prompt_tokens")
                    or usage.get("input_tokens")
                    or 0
                )

                output_tokens = int(
                    usage.get("completion_tokens")
                    or usage.get("output_tokens")
                    or 0
                )
            else:
                input_tokens = int(
                    getattr(usage, "prompt_tokens", 0)
                    or getattr(usage, "input_tokens", 0)
                    or 0
                )

                output_tokens = int(
                    getattr(usage, "completion_tokens", 0)
                    or getattr(usage, "output_tokens", 0)
                    or 0
                )

        if enforce and (input_tokens + output_tokens) <= 0:
            total_tokens = 0

            if isinstance(provider_usage, dict):
                total_tokens = int(
                    provider_usage.get("total_tokens") or 0
                )

            if total_tokens > 0:
                input_tokens = total_tokens
            else:
                raise RuntimeError(
                    "Provider token usage is missing or zero; "
                    "refusing to complete an enforced request."
                )

        if enforce:
            from nova_backend.services import billing_service

            provider_response_id = getattr(
                response,
                "id",
                None,
            )

            if isinstance(response, dict):
                provider_response_id = (
                    provider_response_id
                    or response.get("id")
                )

            idempotency_key = (
                f"provider_response:{str(provider_response_id).strip()}"
                if provider_response_id
                and str(provider_response_id).strip()
                else None
            )

            billing_result = billing_service.consume_usage(
                user_id=user_id,
                username=username,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                idempotency_key=idempotency_key,
            )

            if (
                not isinstance(billing_result, dict)
                or not billing_result.get("ok")
            ):
                reason = (
                    billing_result.get("reason", "Billing failed")
                    if isinstance(billing_result, dict)
                    else "Billing did not complete"
                )

                raise RuntimeError(
                    f"Nova billing enforcement failed: {reason}"
                )


        from nova_backend.services.usage_ledger_service import (
            record_model_usage,
        )

        usage_recorded = False

        try:
            record_model_usage(
                user_id=user_id,
                username=username,
                session_id=session_id,
                model=model,
                input_text=input_text,
                output_text=output_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                provider_usage=provider_usage,
                meta={"source": "model_gateway"},
            )
            usage_recorded = True

        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "Nova usage analytics write failed after "
                "model response; billing result is preserved."
            )

        if usage_recorded and provider_usage and any(
            provider_usage.get(key) is not None
            for key in (
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "input_tokens",
                "output_tokens",
            )
        ):
            try:
                from flask import g

                g._nova_provider_usage_recorded = True

            except Exception:
                pass

    except Exception as exc:
        billing_error = exc

    if enforce and billing_error is not None:
        raise RuntimeError(
            f"Nova billing enforcement failed: {billing_error}"
        ) from billing_error

    if enforce:

        if (
            not isinstance(billing_result, dict)
            or not billing_result.get("ok")
        ):
            reason = (
                billing_result.get("reason", "Billing failed")
                if isinstance(billing_result, dict)
                else "Billing did not complete"
            )

            raise RuntimeError(
                f"Nova billing enforcement failed: {reason}"
            )

    try:
        setattr(
            response,
            "_nova_billing",
            billing_result,
        )
        setattr(
            response,
            "_nova_usage_tokens",
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": (
                    input_tokens
                    + output_tokens
                ),
            },
        )

    except Exception:
        pass

    return billing_result


# ---------------------------------------------------------------------
# IMAGE GENERATION
# ---------------------------------------------------------------------


def images_generate_create(
    *args,
    **kwargs,
):
    from nova_backend.model_registry import (
        get_image_model,
        get_model_provider,
    )

    model = str(
        kwargs.get("model")
        or get_image_model()
    ).strip()

    if not model:
        raise RuntimeError(
            "Image generation model is not configured."
        )

    kwargs["model"] = model

    provider = get_model_provider(model)

    if provider != "openai":
        raise RuntimeError(
            f"Model provider '{provider}' is not yet connected "
            f"for image generation model '{model}'."
        )

    client = _get_openai_client()

    return client.images.generate(
        *args,
        **kwargs,
    )

# ---------------------------------------------------------------------
# CHAT COMPLETIONS
# ---------------------------------------------------------------------

def chat_completions_create(
    *args,
    **kwargs,
):
    kwargs["model"] = resolve_nova_task_model(
        model=kwargs.get("model"),
        text=_nova_messages_text(
            kwargs.get("messages")
        ),
    )

    (
        user_id,
        username,
        session_id,
        enforce,
    ) = _nova_pop_internal_kwargs(
        kwargs
    )

    model = str(
        kwargs.get("model")
        or os.environ.get("OPENAI_MODEL")
        or os.environ.get("NOVA_OPENAI_MODEL")
        or "unknown"
    )

    messages = kwargs.get("messages")

    if enforce:
        _nova_preflight_credits(
            user_id=user_id,
            username=username,
            model=model,
        )

    from nova_backend.model_registry import get_model_provider

    provider = get_model_provider(model)

    from nova_backend.services.provider_gateway_service import (
        create_provider_client,
    )

    client = create_provider_client(
        provider
    )

    if provider in {"anthropic", "google", "xai"}:
        from nova_backend.services.provider_execution_service import (
            execute_provider_chat,
        )

        response = execute_provider_chat(
            provider=provider,
            client=client,
            model=model,
            messages=messages,
            **kwargs,
        )
    else:

        try:
            response = client.chat.completions.create(
                *args,
                **kwargs,
            )

        except Exception as error:
            print(
                "MODEL GATEWAY EXECUTION ERROR =",
                repr(error),
                flush=True,
            )

            print(
                "MODEL GATEWAY FAILED MODEL =",
                model,
                flush=True,
            )

            raise

    _nova_consume_and_record_usage(
        user_id=user_id,
        username=username,
        session_id=session_id,
        model=model,
        messages=messages,
        response=response,
        enforce=enforce,
    )

    return response


# ---------------------------------------------------------------------
# RESPONSES API
# ---------------------------------------------------------------------

def responses_create(
    *args,
    **kwargs,
):
    kwargs["model"] = resolve_nova_task_model(
        model=kwargs.get("model"),
        text=_nova_text(
            kwargs.get("input")
        ),
    )

    (
        user_id,
        username,
        session_id,
        enforce,
    ) = _nova_pop_internal_kwargs(
        kwargs
    )

    model = str(
        kwargs.get("model")
        or os.environ.get("OPENAI_MODEL")
        or os.environ.get("NOVA_OPENAI_MODEL")
        or "unknown"
    )

    model_input = kwargs.get("input")

    if enforce:
        _nova_preflight_credits(
            user_id=user_id,
            username=username,
            model=model,
        )

    print(
        "MODEL GATEWAY DEBUG MODEL =",
        model,
        flush=True,
    )

    from nova_backend.model_registry import get_model_provider

    provider = get_model_provider(model)

    from nova_backend.services.provider_gateway_service import (
        create_provider_client,
    )

    client = create_provider_client(
        provider
    )

    try:
        response = client.responses.create(
            *args,
            **kwargs,
        )

    except Exception as error:
        print(
            "MODEL GATEWAY RESPONSES ERROR =",
            repr(error),
            flush=True,
        )

        raise

    _nova_consume_and_record_usage(
        user_id=user_id,
        username=username,
        session_id=session_id,
        model=model,
        messages=model_input,
        response=response,
        enforce=enforce,
    )

    return response