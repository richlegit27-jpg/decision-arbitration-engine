import re

def should_save_memory_text(text, kind=None):

    cleaned = str(text or "").strip()

    if not cleaned:
        return False

    kind = str(kind or "").lower().strip()
    lowered = cleaned.lower()

    junk_patterns = (
        "traceback",
        "attributeerror",
        "nameerror",
        "syntaxerror",
        "indentationerror",
        "chat_service.py",
        "nova_backend",
        "copy regenerate",
    )

    if any(pattern in lowered for pattern in junk_patterns):
        return False

    if kind in {
        "profile",
        "project",
        "goal",
        "note",
        "style",
    }:
        return True

    if kind == "user_fact":
        strong_fact_signals = (
            "my name is",
            "call me",
            "i am ",
            "i'm ",
            "i work on",
            "i'm working on",
            "i live in",
        )

        return any(
            signal in lowered
            for signal in strong_fact_signals
        )

    if kind == "preference":
        return True

    weak_signals = (
        "i prefer",
        "i like ",
        "i love ",
        "i enjoy ",
        "i dislike ",
        "i hate ",
        "remember this",
        "remember that",
    )

    return any(
        signal in lowered
        for signal in weak_signals
    )


tests = [
    ("my name is Richard", "user_fact"),
    ("I prefer PowerShell commands", "preference"),
    ("I am building Nova", "user_fact"),
    ("hello", "user_fact"),
    ("bitcoin price right now", "user_fact"),
    ("what is my name", "user_fact"),
    ("fix this traceback", "user_fact"),
]

for text, kind in tests:
    print(
        should_save_memory_text(text, kind),
        "|",
        text,
    )