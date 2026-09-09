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
    username=None,
    model=None,
):
    try:
        from nova_backend.services.usage_ledger_service import (
            ensure_user_can_use_model,
        )

        return ensure_user_can_use_model(
            username=username,
            model=model,
        )

    except ImportError:
        return None

    except Exception as error:
        raise RuntimeError(
            f"Nova credit preflight failed: {error}"
        ) from error


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
    if not enforce:
        return None

    billing_result = None

    try:
        from nova_backend.services.usage_ledger_service import (
            consume_model_usage,
        )

        billing_result = consume_model_usage(
            username=username,
            model=model,
            response=response,
        )

    except ImportError:
        pass

    except Exception:
        pass

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
            provider_usage = usage

            input_tokens = int(
                getattr(
                    usage,
                    "prompt_tokens",
                    0,
                )
                or getattr(
                    usage,
                    "input_tokens",
                    0,
                )
                or 0
            )

            output_tokens = int(
                getattr(
                    usage,
                    "completion_tokens",
                    0,
                )
                or getattr(
                    usage,
                    "output_tokens",
                    0,
                )
                or 0
            )

        from nova_backend.services.usage_ledger_service import (
            record_model_usage,
        )

        record_model_usage(
            user_id=user_id,
            username=username,
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
            username=username,
            model=model,
        )

    client = _get_openai_client()

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
            username=username,
            model=model,
        )

    print(
        "MODEL GATEWAY DEBUG MODEL =",
        model,
        flush=True,
    )

    client = _get_openai_client()

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
