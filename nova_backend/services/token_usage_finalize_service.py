
# ============================================================
# NOVA_TOKEN_USAGE_FINALIZE_WRAPPER_20260705
# Backend-only token usage MVP.
#
# Records estimated usage for finalized responses when the model
# gateway has not already recorded provider-reported token usage.
# ============================================================


def _nova_token_usage_extract_assistant_text_20260705(value):
    try:
        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            for key in (
                "text",
                "content",
                "message",
                "response",
                "assistant_text",
            ):
                found = value.get(key)
                if isinstance(found, str) and found.strip():
                    return found

            nested = value.get("assistant_message")
            if isinstance(nested, dict):
                return _nova_token_usage_extract_assistant_text_20260705(
                    nested
                )

        return str(value or "")

    except Exception:
        return ""


def _nova_token_usage_extract_result_text_20260705(result):
    try:
        if isinstance(result, dict):
            for key in (
                "assistant_text",
                "response",
                "message",
                "content",
            ):
                found = result.get(key)
                if isinstance(found, str) and found.strip():
                    return found

            assistant = result.get("assistant_message")

            if isinstance(assistant, dict):
                text = _nova_token_usage_extract_assistant_text_20260705(
                    assistant
                )

                if text.strip():
                    return text

        return ""

    except Exception:
        return ""


def install_token_usage_finalize_wrapper(ChatService):
    try:
        cls = ChatService

        if getattr(
            cls,
            "_nova_token_usage_finalize_wrapped_20260705",
            False,
        ):
            return

        original = getattr(
            cls,
            "_finalize_response",
            None,
        )

        if not callable(original):
            return

        def wrapped(self, *args, **kwargs):
            result = original(
                self,
                *args,
                **kwargs,
            )

            try:
                from flask import g

                if getattr(
                    g,
                    "_nova_provider_usage_recorded",
                    False,
                ):
                    return result

            except Exception:
                pass

            try:
                from nova_backend.services.usage_ledger_service import (
                    record_model_usage,
                )

                user_id = kwargs.get("user_id")
                username = kwargs.get("username", "")

                try:
                    from auth_utils import (
                        current_user,
                        normalize_username,
                    )

                    current_user_data = current_user() or {}

                    if not isinstance(current_user_data, dict):
                        current_user_data = {}

                    if not user_id:
                        user_id = (
                            current_user_data.get("user_id")
                            or current_user_data.get("id")
                        )

                    if not username:
                        username = normalize_username(
                            str(
                                current_user_data.get("username", "")
                                or ""
                            )
                        )

                except Exception:
                    pass

                session_id = kwargs.get(
                    "session_id",
                    "",
                )

                user_text = kwargs.get(
                    "user_text",
                    "",
                )

                assistant_text = (
                    _nova_token_usage_extract_result_text_20260705(
                        result
                    )
                )

                model_name = kwargs.get(
                    "model_name",
                    getattr(
                        self,
                        "chat_model",
                        "unknown",
                    ),
                )

                record_model_usage(
                    user_id=user_id,
                    session_id=str(
                        session_id or ""
                    ),
                    username=username,
                    model=str(
                        model_name or "unknown"
                    ),
                    input_text=user_text or "",
                    output_text=assistant_text or "",
                    meta={
                        "source": "chat_service_finalize_response",
                        "estimated": True,
                    },
                )

            except Exception as exc:
                try:
                    print(
                        "[NOVA_TOKEN_USAGE_FINALIZE_WRAPPER] usage record failed:",
                        exc,
                    )
                except Exception:
                    pass

            return result

        cls._finalize_response = wrapped

        cls._nova_token_usage_finalize_wrapped_20260705 = True

    except Exception as exc:
        print(
            "[NOVA_TOKEN_USAGE_FINALIZE_WRAPPER] install failed:",
            exc,
        )