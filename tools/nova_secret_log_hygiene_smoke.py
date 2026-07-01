from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


SCAN_SUFFIXES = {
    ".py",
    ".js",
    ".html",
    ".css",
}


IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "nova_backups",
    "uploads",
    "data",
}


SELF_ALLOWED_FILES = {
    "tools/nova_secret_log_hygiene_smoke.py",
    "tools/nova_openai_key_log_safety_smoke.py",
}


LOG_MARKERS = [
    "print(",
    "logger.",
    "logging.",
    "console.log(",
    "console.warn(",
    "console.error(",
    "Write-Host",
]


SENSITIVE_MARKERS = [
    "OPENAI_API_KEY",
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "bearer",
    "authorization",
    "sk-",
    "sk-proj",
]


SAFE_LOG_EXCEPTIONS = [
    '[Nova OpenAI Key] loaded',
    '[Nova OpenAI Key] not configured',
]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _iter_scan_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        rel = path.relative_to(ROOT).as_posix()

        if rel in SELF_ALLOWED_FILES:
            continue

        if path.suffix.lower() not in SCAN_SUFFIXES:
            continue

        if set(path.relative_to(ROOT).parts) & IGNORED_DIRS:
            continue

        yield path


def _line_has_log_marker(line: str) -> bool:
    lowered = line.lower()
    return any(marker.lower() in lowered for marker in LOG_MARKERS)


def _line_has_sensitive_marker(line: str) -> bool:
    lowered = line.lower()
    return any(marker.lower() in lowered for marker in SENSITIVE_MARKERS)


def _line_is_safe_exception(line: str) -> bool:
    return any(item in line for item in SAFE_LOG_EXCEPTIONS)


def main():
    failures = []

    for path in _iter_scan_files():
        text = _read(path)
        rel = path.relative_to(ROOT).as_posix()

        for number, line in enumerate(text.splitlines(), start=1):
            if not _line_has_sensitive_marker(line):
                continue

            if _line_is_safe_exception(line):
                continue

            if _line_has_log_marker(line):
                failures.append(f"{rel}:{number}: {line.strip()}")

            if "sk-proj" in line:
                failures.append(f"{rel}:{number}: {line.strip()}")

    if failures:
        raise AssertionError(
            "Potential secret/log hygiene issue found:\n"
            + "\n".join(sorted(set(failures)))
        )

    print("PASS repo secret log hygiene")
    print("NOVA SECRET LOG HYGIENE SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
