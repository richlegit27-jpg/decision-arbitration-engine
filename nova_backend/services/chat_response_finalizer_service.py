from __future__ import annotations

from typing import Any, Dict


from nova_backend.services.weak_response_guard_service import (
    apply_weak_response_guard,
)


def build_answer_quality_95_payload(
    answer: str,
    session_id: str,
    route: str,
    slim_payload_builder=None,
) -> Dict[str, Any]:
    """
    Response payload builder for answer-quality direct policy responses.

    Keeps response shape ownership out of app.py.
    """

    try:
        if slim_payload_builder:
            return slim_payload_builder(
                answer,
                session_id=session_id,
                route=route,
                route_taken=route,
                answer_quality_95_policy=True,
            )
    except Exception:
        pass

    return {
        "ok": True,
        "session_id": session_id,
        "active_session_id": session_id,
        "text": answer,
        "assistant_message": {
            "role": "assistant",
            "text": answer,
            "content": answer,
        },
        "debug": {
            "route": route,
            "route_taken": route,
        },
        "route": route,
        "route_taken": route,
    }


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