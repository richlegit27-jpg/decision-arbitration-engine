"""
NOVA normal chat bleed guard service.

Extracted from:
NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701

Owns normal-chat safety decisions.
Does not own Flask hooks.
"""


def text(value):
    try:
        return str(value or "").strip()
    except Exception:
        return ""


def is_normal_chat(user_text):
    text_value = text(user_text).lower()

    if not text_value:
        return False

    project_context_tokens = (
        "nova",
        "project",
        "mission",
        "checkpoint",
        "progress",
        "status",
        "state",
        "working on",
        "where are we",
        "what are we doing",
        "what is left",
        "remaining work",
        "next move",
        "continue project",
        "continue nova",
    )

    if any(
        token in text_value
        for token in project_context_tokens
    ):
        return False

    command_exact = {
        "next",
        "continue",
        "run all",
        "run step",
        "run it",
        "execute",
        "stop",
        "cancel",
        "retry",
        "status",
    }

    if text_value in command_exact:
        return False

    command_prefixes = (
        "auto-plan",
        "autoplan",
        "build ",
        "create ",
        "make ",
        "implement ",
        "fix ",
        "repair ",
        "upgrade ",
        "run ",
    )

    if any(
        text_value.startswith(prefix)
        for prefix in command_prefixes
    ):
        return False

    normal_prefixes = (
        "what is ",
        "what's ",
        "whats ",
        "who is ",
        "where is ",
        "when is ",
        "why is ",
        "how do ",
        "how does ",
        "how many ",
        "how much ",
        "tell me ",
        "explain ",
        "define ",
        "ping",
        "hello",
        "hi",
        "hey",
    )

    return (
        text_value.endswith("?")
        or any(
            text_value.startswith(prefix)
            for prefix in normal_prefixes
        )
    )


def is_safe_probe(user_text):
    text_value = text(user_text).lower()

    compact = (
        text_value
        .replace(" ", "")
        .replace("?", "")
        .replace("plus", "+")
        .replace("add", "+")
    )

    if text_value.startswith("ping"):
        return True

    if "2+2" in compact or "twoplustwo" in compact:
        return True

    if (
        "short joke" in text_value
        or text_value.startswith("tell me a joke")
    ):
        return True

    return False


def is_bleed(content):
    text_value = text(content).lower()

    if not text_value:
        return False

    markers = (
        "next move:",
        "current focus:",
        "first remaining item:",
        "remaining work",
        "next command",
        "project state",
        "active nova mission",
        "active mission",
        "last mission",
        "autonomy task",
        "fallback guard cleanup",
        "autonomy-plan fallback",
        "patch-build fallback",
    )

    return any(
        marker in text_value
        for marker in markers
    )


def safe_answer(user_text):
    text_value = text(user_text).lower()

    compact = (
        text_value
        .replace(" ", "")
        .replace("?", "")
        .replace("plus", "+")
        .replace("add", "+")
    )

    if "2+2" in compact or "twoplustwo" in compact:
        return "2 plus 2 is 4."

    if text_value.startswith("ping"):
        return "pong"

    if (
        "short joke" in text_value
        or text_value.startswith("tell me a joke")
    ):
        return "Why did the computer get cold? It left its Windows open."

    return "I'm here. What would you like to talk about?"


def extract_response_text(data):
    if not isinstance(data, dict):
        return ""

    assistant = data.get("assistant_message")

    if isinstance(assistant, dict):
        for key in (
            "content",
            "text",
            "message",
            "response",
            "answer",
        ):
            value = assistant.get(key)
            if isinstance(value, str) and value.strip():
                return value

    for key in (
        "content",
        "response",
        "message",
        "text",
        "answer",
    ):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value

    return ""


def set_answer(data, answer):
    if not isinstance(data, dict):
        return data

    assistant = data.get("assistant_message")

    if not isinstance(assistant, dict):
        assistant = {
            "role": "assistant",
        }

    assistant["content"] = answer
    assistant["text"] = answer
    assistant["role"] = "assistant"

    meta = assistant.get("meta")

    if not isinstance(meta, dict):
        meta = {}

    meta["render_source"] = "normal_chat_bleed_guard"
    meta["normal_chat_priority"] = True

    assistant["meta"] = meta

    data["assistant_message"] = assistant

    data["content"] = answer
    data["text"] = answer
    data["response"] = answer
    data["message"] = answer
    data["answer"] = answer

    debug = data.get("debug")

    if not isinstance(debug, dict):
        debug = {}

    debug["route"] = "chat"
    debug["route_taken"] = "chat"
    debug["normal_chat_priority"] = True
    debug["suppressed_project_state_bleed"] = True
    debug["phase4f_prerun_final_guard"] = True

    data["debug"] = debug

    return data





  