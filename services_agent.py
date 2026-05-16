from __future__ import annotations

import threading
import time
from typing import Any, Callable


def agent_brain_prompt_impl(
    session_obj: dict[str, Any],
    username: str,
    get_relevant_memory_func: Callable[[str, str], list[dict[str, Any]]],
) -> str:
    goal = str(session_obj.get("agent_goal") or "").strip()
    if not goal:
        return ""

    messages = session_obj.get("messages", [])[-8:]
    transcript_lines: list[str] = []

    for msg in messages:
        role = msg.get("role", "unknown")
        content = str(msg.get("content", "") or "")
        transcript_lines.append(f"{role.upper()}: {content}")

    transcript = "\n".join(transcript_lines).strip()
    memory_items = get_relevant_memory_func(username, goal)
    memory_context = "\n".join(
        f"- {item.get('value', '')}" for item in memory_items if item.get("value")
    )

    return f"""
You are Nova running in autonomous background agent mode for this one session.

Your job:
- Continue working on the user's goal without asking follow-up questions
- Make one useful incremental step only
- Be concise
- If there is nothing useful to add right now, return exactly: NO_UPDATE

Current goal:
{goal}

Relevant memory:
{memory_context}

Recent session context:
{transcript}
""".strip()


def run_agent_step_for_session_impl(
    session_id: str,
    sessions: dict[str, dict[str, Any]],
    agent_state: dict[str, Any],
    state_lock: Any,
    save_sessions_func: Callable[[], None],
    normalize_username_func: Callable[[str], str],
    get_relevant_memory_func: Callable[[str, str], list[dict[str, Any]]],
    call_model_func: Callable[[str, str], str],
    autonomous_loop_refine_func: Callable[[str, str, str], str],
    add_message_func: Callable[..., dict[str, Any]],
    now_iso_func: Callable[[], str],
) -> str:
    with state_lock:
        session_obj = sessions.get(session_id)
        if not session_obj:
            return ""
        if not session_obj.get("agent_enabled"):
            return ""

        goal = str(session_obj.get("agent_goal") or "").strip()
        if not goal:
            session_obj["agent_status"] = "idle"
            save_sessions_func()
            return ""

        username = normalize_username_func(str(session_obj.get("user", "")))
        session_obj["agent_status"] = "running"
        save_sessions_func()

    prompt = agent_brain_prompt_impl(
        session_obj=session_obj,
        username=username,
        get_relevant_memory_func=get_relevant_memory_func,
    )
    if not prompt:
        with state_lock:
            if session_id in sessions:
                sessions[session_id]["agent_status"] = "idle"
                save_sessions_func()
        return ""

    try:
        draft = call_model_func(prompt, "")
        if not draft or draft.strip() == "NO_UPDATE":
            with state_lock:
                if session_id in sessions:
                    sessions[session_id]["agent_status"] = "idle"
                    sessions[session_id]["agent_last_run_at"] = now_iso_func()
                    sessions[session_id]["agent_last_output"] = ""
                    save_sessions_func()
            return ""

        improved = autonomous_loop_refine_func(goal, draft, "")
        add_message_func(session_id, "assistant", improved)

        with state_lock:
            if session_id in sessions:
                sessions[session_id]["agent_status"] = "idle"
                sessions[session_id]["agent_last_run_at"] = now_iso_func()
                sessions[session_id]["agent_last_output"] = improved
                save_sessions_func()

        return improved

    except Exception as exc:
        with state_lock:
            agent_state["last_error"] = str(exc)
            agent_state["last_tick_at"] = now_iso_func()
            if session_id in sessions:
                sessions[session_id]["agent_status"] = "error"
                sessions[session_id]["agent_last_run_at"] = now_iso_func()
                sessions[session_id]["agent_last_output"] = f"Agent error: {exc}"
                save_sessions_func()
        return ""


def background_agent_worker_impl(
    sessions: dict[str, dict[str, Any]],
    agent_state: dict[str, Any],
    state_lock: Any,
    run_agent_step_for_session_func: Callable[[str], str],
    now_iso_func: Callable[[], str],
) -> None:
    while True:
        try:
            if agent_state.get("enabled"):
                agent_state["last_tick_at"] = now_iso_func()

                with state_lock:
                    session_ids = [
                        session_id
                        for session_id, session_obj in sessions.items()
                        if session_obj.get("agent_enabled")
                    ]

                outputs: list[str] = []
                for session_id in session_ids:
                    output = run_agent_step_for_session_func(session_id)
                    if output:
                        outputs.append(f"{session_id}: updated")

                agent_state["last_summary"] = ", ".join(outputs) if outputs else "no updates"
        except Exception as exc:
            agent_state["last_error"] = str(exc)

        interval = int(agent_state.get("interval_seconds", 20) or 20)
        time.sleep(max(3, interval))


def ensure_agent_thread_impl(
    agent_state: dict[str, Any],
    worker_target: Callable[[], None],
) -> None:
    if agent_state.get("thread_started"):
        return

    thread = threading.Thread(
        target=worker_target,
        daemon=True,
        name="nova-background-agent",
    )
    thread.start()
    agent_state["thread_started"] = True