"""
NOVA title guard service.

Extracted from:
NOVA_FINAL_TITLE_GUARD_20260630

Owns title validation, cleanup decisions, and persistence.
Does not own Flask request lifecycle.
"""

import json
import re
from collections import Counter
from pathlib import Path


def is_garbage_title(value):
    text = str(value or "")
    compact = "".join(text.split())

    if not compact:
        return False

    lower = compact.lower()

    if lower in {
        "k",
        "ok",
        "okay",
        "next",
        "continue",
        "run",
        "runit",
        "stop",
        "cancel",
        "yes",
        "no",
        "hello",
        "hi",
        "hey",
    }:
        return False

    if len(compact) < 8:
        return False

    counts = Counter(compact)
    most_common_ratio = counts.most_common(1)[0][1] / max(len(compact), 1)

    alpha_count = sum(
        1 for ch in compact if ch.isalpha()
    )

    digit_count = sum(
        1 for ch in compact if ch.isdigit()
    )

    symbol_count = sum(
        1 for ch in compact if not ch.isalnum()
    )

    symbol_digit_ratio = (
        digit_count + symbol_count
    ) / max(len(compact), 1)

    if len(compact) >= 12 and most_common_ratio >= 0.75:
        return True

    if len(compact) >= 20 and alpha_count == 0 and symbol_digit_ratio >= 0.90:
        return True

    if len(compact) >= 24 and alpha_count <= 2 and symbol_digit_ratio >= 0.80:
        return True

    if re.search(r"(.)\1{9,}", compact):
        return True

    if (
        re.search(r"([\[\]\(\)\{\}=\\\/\|'\-]){8,}", compact)
        and alpha_count <= 3
    ):
        return True

    return False


def clean_title(title, user_text, route, source):
    current = str(title or "").strip()
    lowered = current.lower().strip()

    web_like = lowered in {
        "",
        "web fetch",
        "source preview",
        "generated image",
    }

    guard_like = (
        str(route or "").strip().lower() == "accidental_input_guard"
        or str(source or "").strip().lower() == "accidental_input_guard"
        or is_garbage_title(current)
        or is_garbage_title(user_text)
    )

    if guard_like:
        return "New Chat"

    if web_like:
        candidate = str(user_text or "").replace("\n", " ").strip()

        if candidate and not is_garbage_title(candidate):
            return candidate[:60]

        return "New Chat"

    return current or "New Chat"


def persist_title(session_file, session_id, clean_title):
    try:
        sid = str(session_id or "").strip()

        if not sid:
            return

        data_path = Path(session_file)

        if not data_path.exists():
            return

        store = json.loads(
            data_path.read_text(
                encoding="utf-8"
            )
        )

        sessions = store.get("sessions")

        if not isinstance(sessions, list):
            return

        changed = False

        for item in sessions:
            if not isinstance(item, dict):
                continue

            item_id = str(
                item.get("id")
                or item.get("session_id")
                or ""
            ).strip()

            if item_id != sid:
                continue

            old_title = str(
                item.get("title")
                or ""
            ).strip()

            if (
                old_title.lower()
                in {
                    "",
                    "web fetch",
                    "source preview",
                    "generated image",
                }
                or is_garbage_title(old_title)
            ):
                item["title"] = clean_title
                changed = True

        if changed:
            tmp = data_path.with_suffix(
                data_path.suffix + ".tmp"
            )

            tmp.write_text(
                json.dumps(
                    store,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            tmp.replace(data_path)

    except Exception:
        pass