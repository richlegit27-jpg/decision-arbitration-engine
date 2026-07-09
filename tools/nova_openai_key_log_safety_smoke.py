from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SCAN_PATHS = [
    ROOT / "app.py",
    *sorted((ROOT / "nova_backend" / "services").glob("*.py")),
]

FORBIDDEN_PATTERNS = [
    "sk-proj",
    "sk-",
    "env_key[:",
    "env_key[-",
    "OPENAI_API_KEY missing",
]


ALLOWED_KEY_LOGS = [
    'print("[Nova OpenAI Key] loaded")',
    'print("[Nova OpenAI Key] not configured")',
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main():
    unsafe = []
    key_log_count = 0

    for path in SCAN_PATHS:
        if not path.exists():
            continue

        text = read_text(path)

        lines = text.splitlines()

        for index, line in enumerate(lines, start=1):
            stripped = line.strip()

            if "[Nova OpenAI Key]" not in stripped:
                continue

            key_log_count += 1

            if stripped not in ALLOWED_KEY_LOGS:
                unsafe.append(f"{path.relative_to(ROOT)}:{index}: {stripped}")

            window = "\n".join(lines[index - 1:index + 4])

            for pattern in FORBIDDEN_PATTERNS:
                if pattern in window and stripped not in ALLOWED_KEY_LOGS:
                    unsafe.append(f"{path.relative_to(ROOT)}:{index}: forbidden {pattern}: {stripped}")

    if unsafe:
        raise AssertionError(
            "Unsafe OpenAI key boot log detected:\n"
            + "\n".join(sorted(set(unsafe)))
        )

    if key_log_count:
        print("PASS safe OpenAI key boot log")
    else:
        print("PASS no OpenAI key boot log present")

    print("NOVA OPENAI KEY LOG SAFETY SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
