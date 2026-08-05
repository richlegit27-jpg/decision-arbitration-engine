def clear_pending_execution_actions(result):
    if not isinstance(result, dict):
        return result

    session = result.get("session") or {}
    session_meta = session.get("meta") or {}

    if session_meta.get("pending_execution_action"):
        session_meta["pending_execution_action"] = ""

    assistant_message = result.get("assistant_message") or {}
    assistant_meta = assistant_message.get("meta") or {}

    if assistant_meta.get("pending_execution_action"):
        assistant_meta["pending_execution_action"] = ""

    return result
