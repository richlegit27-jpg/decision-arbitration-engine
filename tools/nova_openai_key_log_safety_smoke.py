from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"


FORBIDDEN_PATTERNS = [
    "sk-proj",
    "sk-",
]


ALLOWED_KEY_LOGS = [
    'print("[Nova OpenAI Key] loaded")',
    'print("[Nova OpenAI Key] not configured")',
]


def main():
    text = APP_PATH.read_text(encoding="utf-8-sig")

    key_log_lines = [
        line.strip()
        for line in text.splitlines()
        if "[Nova OpenAI Key]" in line
    ]

    unsafe = []

    for line in key_log_lines:
        if line not in ALLOWED_KEY_LOGS:
            unsafe.append(line)

        for pattern in FORBIDDEN_PATTERNS:
            if pattern in line and line not in ALLOWED_KEY_LOGS:
                unsafe.append(line)

    if unsafe:
        raise AssertionError(
            "Unsafe OpenAI key boot log detected:\n"
            + "\n".join(sorted(set(unsafe)))
        )

    if key_log_lines:
        print("PASS safe OpenAI key boot log")
    else:
        print("PASS no OpenAI key boot log present")

    print("NOVA OPENAI KEY LOG SAFETY SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
