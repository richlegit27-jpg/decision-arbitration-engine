def build_project_next_response(fixed_text, session_id):
    meta = {
        "route": "api_chat_project_next_endpoint_wrapper_fixed",
        "strategy": "api_chat_project_next_endpoint_wrapper_fixed",
        "session_id": session_id,
        "source_urls": [],
        "sources": [],
    }

    assistant_message = {
        "role": "assistant",
        "content": fixed_text,
        "text": fixed_text,
        "attachments": [],
        "meta": meta,
    }

    data = {
        "ok": True,
        "success": True,
        "assistant_message": assistant_message,
        "assistant_text": fixed_text,
        "text": fixed_text,
        "saved_artifact": None,
        "session": {
            "id": session_id,
            "session_id": session_id,
            "messages": [assistant_message],
            "attachments": [],
            "meta": meta,
        },
        "route": "api_chat_project_next_endpoint_wrapper_fixed",
        "route_taken": "api_chat_project_next_endpoint_wrapper_fixed",
        "debug": {
            "route": "api_chat_project_next_endpoint_wrapper_fixed",
            "route_taken": "api_chat_project_next_endpoint_wrapper_fixed",
        },
        "meta": meta,
        "session_id": session_id,
        "active_session_id": session_id,
    }

    return data