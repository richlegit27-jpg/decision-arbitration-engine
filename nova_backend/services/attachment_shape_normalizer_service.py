import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

data_dir = BASE_DIR / "data"
sessions_path = data_dir / "nova_sessions.json"


def load_store():
    try:
        if not sessions_path.exists():
            return {
                "active_session_id": "",
                "sessions": [],
            }

        data = json.loads(
            sessions_path.read_text(
                encoding="utf-8-sig"
            )
        )

        if not isinstance(data, dict):
            return {
                "active_session_id": "",
                "sessions": [],
            }

        if not isinstance(data.get("sessions"), list):
            data["sessions"] = []

        data.setdefault(
            "active_session_id",
            "",
        )

        return data

    except Exception:
        return {
            "active_session_id": "",
            "sessions": [],
        }


def save_store(store):
    try:
        data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        tmp = sessions_path.with_suffix(
            sessions_path.suffix + ".tmp"
        )

        tmp.write_text(
            json.dumps(
                store,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        tmp.replace(
            sessions_path
        )

        return True

    except Exception:
        return False


def parse_powershell_object_string(value):
    text = str(value or "").strip()

    if not text:
        return []

    if not (
        text.startswith("@{")
        and text.endswith("}")
    ):
        return []

    inner = text[2:-1].strip()

    if not inner:
        return []

    item = {}

    parts = re.split(
        r";\s*",
        inner,
    )

    for part in parts:
        if "=" not in part:
            continue

        key, raw = part.split(
            "=",
            1,
        )

        key = str(key or "").strip()
        raw = str(raw or "").strip()

        if not key:
            continue

        if key in (
            "size",
            "size_bytes",
        ):
            try:
                item[key] = int(raw)
            except Exception:
                item[key] = raw
        else:
            item[key] = raw

    if not item:
        return []

    if "url" in item and "file_url" not in item:
        item["file_url"] = item.get("url") or ""

    if "filename" in item and "name" not in item:
        item["name"] = item.get("filename") or ""

    return [item]


def normalize_attachments(value):
    changed = False

    if value is None:
        return [], True

    if isinstance(value, list):
        out = []

        for item in value:
            if isinstance(item, dict):
                clean = dict(item)

                if "url" in clean and "file_url" not in clean:
                    clean["file_url"] = clean.get("url") or ""
                    changed = True

                if "filename" in clean and "name" not in clean:
                    clean["name"] = clean.get("filename") or ""
                    changed = True

                out.append(clean)
                continue

            if isinstance(item, str):
                parsed = parse_powershell_object_string(item)

                if parsed:
                    out.extend(parsed)

                changed = True
                continue

            changed = True

        return out, changed

    if isinstance(value, dict):
        clean = dict(value)

        if "url" in clean and "file_url" not in clean:
            clean["file_url"] = clean.get("url") or ""

        if "filename" in clean and "name" not in clean:
            clean["name"] = clean.get("filename") or ""

        return [clean], True

    if isinstance(value, str):
        return parse_powershell_object_string(value), True

    return [], True


def normalize_message_attachment_shapes():
    store = load_store()

    sessions = store.get(
        "sessions",
        [],
    )

    if not isinstance(sessions, list):
        return 0

    changed_count = 0

    for sess in sessions:
        if not isinstance(sess, dict):
            continue

        messages = sess.get(
            "messages"
        )

        if not isinstance(messages, list):
            continue

        for msg in messages:
            if not isinstance(msg, dict):
                continue

            attachments, changed = normalize_attachments(
                msg.get("attachments")
            )

            if changed:
                msg["attachments"] = attachments
                changed_count += 1

            meta = msg.get("meta")

            if (
                isinstance(meta, str)
                and meta.strip().startswith("@{")
                and meta.strip().endswith("}")
            ):
                parsed_meta = parse_powershell_object_string(meta)

                msg["meta"] = (
                    parsed_meta[0]
                    if parsed_meta
                    else {}
                )

                changed_count += 1

            elif meta is None:
                msg["meta"] = {}
                changed_count += 1

    if changed_count:
        store["sessions"] = sessions
        save_store(store)

    return changed_count


class AttachmentShapeNormalizerService:

    def install(self, app):
        from flask import request

        @app.after_request
        def nova_attachment_shape_normalizer_after_request_20260610(response):
            path = str(request.path or "")

            if (
                path.startswith("/api/sessions")
                or path.startswith("/api/chat")
                or path.startswith("/api/chat/stream")
                or path == "/mobile"
            ):
                changed = normalize_message_attachment_shapes()

                if changed:
                    try:
                        app.logger.info(
                            "[Nova Attachment Shape Normalizer] repaired %s message attachment/meta fields",
                            changed,
                        )
                    except Exception:
                        pass

            return response