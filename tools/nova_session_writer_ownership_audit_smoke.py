from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


APPROVED_WRITERS = {
    "nova_backend/services/session_response_finalizer_service.py",
    "nova_backend/services/session_service.py",
    "nova_backend/services/chat_service.py",
}

BLOCKED_PATTERNS = [
    "messages.append(assistant",
    "messages.append(assistant_msg",
    "messages.append(saved_assistant",
]


SAVE_PATTERNS = [
    "_save_sessions(",
    "save_sessions(",
    "persist_session",
]


IGNORED_FRAGMENTS = {
    ".before-",
    ".lock",
    "LOCK",
    "checkpoint",
    "working",
    "final-working",
    "route-voice",
    "response-override",
    "intent-lock",
    "memory-",
}


def scan_file(path: Path):
    text = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    has_message_write = any(
        pattern in text
        for pattern in BLOCKED_PATTERNS
    )

    has_session_save = any(
        pattern in text
        for pattern in SAVE_PATTERNS
    )

    return has_message_write and has_session_save


def main():
    print("NOVA SESSION WRITER OWNERSHIP AUDIT SMOKE")
    print("=" * 70)

    failures = []

    for path in ROOT.glob(
        "nova_backend/services/*.py"
    ):
        relative = str(
            path.relative_to(ROOT)
        ).replace("\\", "/")

        if relative in APPROVED_WRITERS:
            continue

        if any(
            fragment.lower()
            in path.name.lower()
            for fragment in IGNORED_FRAGMENTS
        ):
            continue

        if scan_file(path):
            failures.append(relative)

    if failures:
        print()
        print("FAIL: unauthorized session writers detected")
        for item in failures:
            print(item)
        raise SystemExit(1)

    print("PASS: no unauthorized session writers detected")
    print("=" * 70)


if __name__ == "__main__":
    main()