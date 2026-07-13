from __future__ import annotations

from typing import Any, Dict

from nova_backend.services.weak_response_guard_service import (
    apply_weak_response_guard,
)


def finalize_chat_response(
    user_text: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Final response boundary.

    Keeps app.py from owning individual response repair rules.
    """

    try:
        return apply_weak_response_guard(
            user_text,
            result,
        )
    except Exception as error:
        print(
            "[chat_response_finalizer_service] weak guard skipped:",
            error,
        )
        return result