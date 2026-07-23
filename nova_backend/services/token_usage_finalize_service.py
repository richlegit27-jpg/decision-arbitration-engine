# ============================================================
# NOVA_TOKEN_USAGE_FINALIZE_WRAPPER_20260705
# Backend-only token usage MVP.
#
# This records estimated usage for every response that passes through
# ChatService._finalize_response. Exact provider usage can be added later
# at the OpenAI gateway/client-call layer.
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
                from nova_backend.services.usage_ledger_service import (
                    record_model_usage,
                )

                username = ""

                try:
                    from flask import g

                    user = getattr(
                        g,
                        "nova_auth_user",
                        None,
                    ) or {}

                    username = str(
                        user.get("username") or ""
                    ).strip()

                except Exception:
                    pass


                if not username:
                    try:
                        from auth_utils import (
                            current_user,
                            normalize_username,
                        )

                        username = normalize_username(
                            str(
                                current_user().get("username", "")
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