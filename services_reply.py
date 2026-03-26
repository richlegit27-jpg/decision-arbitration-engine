from __future__ import annotations

from typing import Any, Callable


def generate_reply_impl(
    username: str,
    user_text: str,
    session_id: str,
    sessions: dict[str, dict[str, Any]],
    state_lock: Any,
    save_sessions_func: Callable[[], None],
    wants_web_search_func: Callable[[str], bool],
    search_web_for_query_func: Callable[[str, str], tuple[list[dict[str, Any]], str]],
    tavily_api_key: str,
    get_relevant_memory_func: Callable[[str, str], list[dict[str, Any]]],
    call_model_func: Callable[[str, str], str],
    clean_text_func: Callable[[Any], str],
) -> tuple[str, list[dict[str, Any]], str]:
    final_results: list[dict[str, Any]] = []
    provider = ""

    if wants_web_search_func(user_text):
        final_results, provider = search_web_for_query_func(user_text, tavily_api_key)

    with state_lock:
        if session_id in sessions:
            sessions[session_id]["last_web_results"] = final_results
            save_sessions_func()

    memory_items = get_relevant_memory_func(username, user_text)
    memory_context = "\n".join(
        f"- {item.get('value', '')}" for item in memory_items if item.get("value")
    ).strip()

    web_context = ""
    if final_results:
        parts: list[str] = []

        for idx, item in enumerate(final_results, start=1):
            title = clean_text_func(item.get("title"))
            url = clean_text_func(item.get("url"))
            snippet = clean_text_func(item.get("snippet"))

            parts.append(f"[{idx}] {title}")
            if url:
                parts.append(f"URL: {url}")
            if snippet:
                parts.append(f"Snippet: {snippet}")
            parts.append("")

        web_context = "\n".join(parts).strip()

    context_parts = [
        "You are Nova, a direct, no-BS AI assistant.",
        "You speak clearly, directly, and naturally.",
        "You do not write like a news article.",
        "You do not use citation numbering like [1] [2] in your final answer.",
        "When web results exist, use them to improve accuracy, but rewrite naturally.",
        "Keep answers tight, sharp, readable, and useful.",
    ]

    if memory_context:
        context_parts.append("Relevant user memory:\n" + memory_context)

    if web_context:
        context_parts.append(
            "Use these web results when relevant. Prefer them over guessing.\n\n" + web_context
        )

    context = "\n\n".join(context_parts).strip()

    try:
        reply_text = clean_text_func(call_model_func(user_text, context))
    except Exception as exc:
        if final_results:
            bullets: list[str] = []
            for item in final_results:
                title = clean_text_func(item.get("title"))
                snippet = clean_text_func(item.get("snippet"))
                if title and snippet:
                    bullets.append(f"- {title}: {snippet}")
                elif title:
                    bullets.append(f"- {title}")

            reply_text = "Here are the strongest results I found:\n\n" + "\n".join(bullets[:5]).strip()
        else:
            reply_text = f"Error generating reply: {exc}"

    if not reply_text:
        if final_results:
            bullets: list[str] = []
            for item in final_results:
                title = clean_text_func(item.get("title"))
                snippet = clean_text_func(item.get("snippet"))
                if title and snippet:
                    bullets.append(f"- {title}: {snippet}")
                elif title:
                    bullets.append(f"- {title}")

            reply_text = "Here are the strongest results I found:\n\n" + "\n".join(bullets[:5]).strip()
        else:
            reply_text = "I couldn't generate a response."

    return reply_text, final_results, provider