def handle_execution_command_guard(
    execution_guard_service,
    request,
):
    _nova_exec_payload2 = request.get_json(
        silent=True
    ) or {}

    _nova_exec_text2 = str(
        _nova_exec_payload2.get("user_text")
        or _nova_exec_payload2.get("text")
        or _nova_exec_payload2.get("message")
        or ""
    ).strip().lower()

    _nova_exec_session_id2 = str(
        _nova_exec_payload2.get("session_id")
        or _nova_exec_payload2.get("client_session_id")
        or "default"
    ).strip()

    execution_action_result = None

    if not (
        hasattr(
            execution_guard_service,
            "chat_service",
        )
        and execution_guard_service.chat_service
        and hasattr(
            execution_guard_service.chat_service,
            "execution_orchestrator_service",
        )
    ):
        execution_action_result = (
            execution_guard_service.handle_execution_action(
                _nova_exec_text2,
                _nova_exec_session_id2,
            )
        )

    if execution_action_result:
        return execution_action_result

    return None