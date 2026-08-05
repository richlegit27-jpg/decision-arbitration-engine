_nova_exec_payload2 = request.get_json(silent=True) or {}
_nova_exec_text2 = ...
_nova_exec_session_id2 = ...

execution_action_result = execution_guard_service.handle_execution_action(...)

if execution_action_result:
    return jsonify(...)