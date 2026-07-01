from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


SCAN_SUFFIXES = {
    ".py",
    ".js",
    ".html",
}


IGNORED_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "nova_backups",
    "uploads",
    "data",
    "runtime",
}


IGNORED_PATH_PART_PREFIXES = (
    "static/js_BACKUP",
    "static/js_BAK",
    "static/js_backup",
)


SELF_ALLOWED_FILES = {
    "tools/nova_secret_log_hygiene_smoke.py",
    "tools/nova_openai_key_log_safety_smoke.py",
    "tools/nova_phase_3h_cleanup_lock_smoke.py",
}


SAFE_LOG_EXCEPTIONS = [
    '[Nova OpenAI Key] loaded',
    '[Nova OpenAI Key] not configured',
    'OPENAI_API_KEY missing',
    'NOVA_API_KEY len=',
    'apiHeaders bearer len=',
]


LOG_CALL_RE = re.compile(
    r"\b(print|console\.log|console\.warn|console\.error|logger\.\w+|logging\.\w+)\s*\(",
    re.IGNORECASE,
)


LITERAL_SECRET_RE = re.compile(
    r"sk-(?:proj-)?[A-Za-z0-9_\-]{12,}"
)


UNSAFE_LOG_VALUE_RE = re.compile(
    r"""
    (print|console\.log|console\.warn|console\.error|logger\.\w+|logging\.\w+)
    \s*\(
    [^\n)]*
    (?:
        OPENAI_API_KEY\s*\[
        |
        NOVA_API_KEY\s*\[
        |
        api[_-]?key\s*\[
        |
        token\s*\[
        |
        secret\s*\[
        |
        password\s*\[
        |
        bearer\s*\[
        |
        :\s*(OPENAI_API_KEY|NOVA_API_KEY|apiKey|api_key|token|secret|password|bearer)\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _is_ignored(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()

    if rel in SELF_ALLOWED_FILES:
        return True

    if any(rel.startswith(prefix) for prefix in IGNORED_PATH_PART_PREFIXES):
        return True

    if set(path.relative_to(ROOT).parts) & IGNORED_DIR_NAMES:
        return True

    return False


def _iter_scan_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in SCAN_SUFFIXES:
            continue

        if _is_ignored(path):
            continue

        yield path


def _line_is_safe(line: str) -> bool:
    return any(item in line for item in SAFE_LOG_EXCEPTIONS)


def main():
    failures = []

    for path in _iter_scan_files():
        text = _read(path)
        rel = path.relative_to(ROOT).as_posix()

        for number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()

            if not stripped or _line_is_safe(stripped):
                continue

            if LITERAL_SECRET_RE.search(stripped):
                failures.append(f"{rel}:{number}: literal secret-like value: {stripped}")
                continue

            if LOG_CALL_RE.search(stripped) and UNSAFE_LOG_VALUE_RE.search(stripped):
                failures.append(f"{rel}:{number}: unsafe sensitive value log: {stripped}")

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
