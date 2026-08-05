from nova_backend.services.chat_response_contract_service import (
    normalize_assistant_message,
)

from nova_backend.services.chat_response_normalizer_service import (
    normalize_chat_result,
)


def build_assistant_message(
    result,
    user_text,
    session_id,
    response_quality_service,
):
    result = normalize_chat_result(
        result,
        session_id,
    )

    assistant_message = normalize_assistant_message(
        result,
        user_text,
        response_quality_service,
    )

    return result, assistant_message