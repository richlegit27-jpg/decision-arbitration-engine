from collections import Counter
import re
import json
from pathlib import Path
from flask import request

def persist_title(session_id, clean_title):
    try:
        sid = str(session_id or "").strip()

        if not sid:
            return

        data_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "nova_sessions.json"
        )

        if not data_path.exists():
            return

        store = json.loads(
            data_path.read_text(encoding="utf-8")
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
                item.get("title") or ""
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

    except Exception as error:
        print(
            "[SESSION_TITLE_GUARD] persist skipped:",
            error,
        )

def apply_response_title_guard(response):
    try:
        request_path = str(getattr(request, "path", "") or "")
        request_method = str(getattr(request, "method", "") or "").upper()

        if request_method != "POST" or request_path != "/api/chat":
            return response

        data = response.get_json(silent=True) or {}

        if not isinstance(data, dict):
            return response

        user_text = str(
            data.get("user_text")
            or data.get("text")
            or data.get("message")
            or ""
        ).strip()

        session = data.get("session")

        if not isinstance(session, dict):
            return response

        old_title = str(
            session.get("title") or ""
        ).strip()

        route = str(
            data.get("route")
            or ""
        ).strip()

        source = str(
            data.get("source")
            or ""
        ).strip()
        
        cleaned = clean_title(
            old_title,
            user_text,
            route,
            source,
        )

        if cleaned != old_title:
            session["title"] = cleaned
            persist_title(
                session.get("id"),
                cleaned,
            )

            response.set_data(
                json.dumps(data, ensure_ascii=False)
            )

        return response

    except Exception as error:
        print(
            "[SESSION_TITLE_GUARD] skipped:",
            error,
        )

    return response

def is_garbage_title(value) -> bool:
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
    ratio = counts.most_common(1)[0][1] / max(len(compact), 1)

    if len(compact) >= 12 and ratio >= 0.75:
        return True

    if re.search(r"(.)\1{9,}", compact):
        return True

    return False


def clean_title(title, user_text, route, source):
    current = str(title or "").strip()

    if (
        str(route or "").lower() == "accidental_input_guard"
        or str(source or "").lower() == "accidental_input_guard"
        or is_garbage_title(current)
        or is_garbage_title(user_text)
    ):
        return "New Chat"

    if current.lower() in {
        "",
        "web fetch",
        "source preview",
        "generated image",
    }:
        candidate = str(user_text or "").replace("\n", " ").strip()

        if candidate and not is_garbage_title(candidate):
            return candidate[:60]

        return "New Chat"

    return current or "New Chat"

def install(app):
    @app.after_request
    def nova_final_title_guard_20260630(response):
        try:
            return apply_response_title_guard(response)
        except Exception as error:
            print(
                "[NOVA_FINAL_TITLE_GUARD_20260630] skipped:",
                error,
            )
        return response