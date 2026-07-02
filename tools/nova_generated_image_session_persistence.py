from pathlib import Path
import re

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="ignore")

marker = "NOVA_GENERATED_IMAGE_SESSION_PERSISTENCE_20260702"
if marker in text:
    print("already installed")
    raise SystemExit(0)

block = r'''

# NOVA_GENERATED_IMAGE_SESSION_PERSISTENCE_20260702
# Persist generated-image URL/attachment fields into saved session messages.
# Fixes mobile/session restore where generated image exists but restored assistant message has attachments=[].
try:
    from pathlib import Path as _nova_img_persist_Path_20260702
    from flask import request as _nova_img_persist_request_20260702

    def _nova_img_persist_filename_20260702(url):
        value = str(url or "").strip()
        return value.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1] if value else ""

    def _nova_img_persist_attachment_20260702(image_url):
        filename = _nova_img_persist_filename_20260702(image_url)
        return {
            "id": filename,
            "filename": filename,
            "stored_name": filename,
            "url": image_url,
            "file_url": image_url,
            "mime_type": "image/png",
            "type": "image/png",
        }

    def _nova_img_persist_patch_message_20260702(message, image_url):
        if not isinstance(message, dict) or not image_url:
            return message

        if str(message.get("role") or "").lower() != "assistant":
            return message

        message["image_url"] = image_url

        meta = message.get("meta")
        if not isinstance(meta, dict):
            meta = {}
        meta["image_url"] = image_url
        meta["source"] = "image_generation"
        message["meta"] = meta

        attachments = message.get("attachments")
        if not isinstance(attachments, list):
            attachments = []

        exists = False
        for item in attachments:
            if not isinstance(item, dict):
                continue
            item_url = str(item.get("url") or item.get("file_url") or "").strip()
            item_type = str(item.get("mime_type") or item.get("type") or "").lower()
            if item_url == image_url or item_type.startswith("image/"):
                item["url"] = item_url or image_url
                item["file_url"] = item.get("file_url") or image_url
                item["mime_type"] = item.get("mime_type") or "image/png"
                item["type"] = item.get("type") or "image/png"
                exists = True

        if not exists:
            attachments.append(_nova_img_persist_attachment_20260702(image_url))

        message["attachments"] = attachments
        return message

    def _nova_img_persist_find_sessions_20260702(data):
        found = []

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("messages") is not None:
                    found.append(item)
            return found

        if not isinstance(data, dict):
            return found

        if data.get("messages") is not None:
            found.append(data)

        sessions = data.get("sessions")
        if isinstance(sessions, list):
            for item in sessions:
                if isinstance(item, dict):
                    found.append(item)
        elif isinstance(sessions, dict):
            for item in sessions.values():
                if isinstance(item, dict):
                    found.append(item)

        for item in data.values():
            if isinstance(item, dict) and item.get("messages") is not None and item not in found:
                found.append(item)

        return found

    def _nova_img_persist_to_session_file_20260702(session_id, image_url, assistant_text):
        if not session_id or not image_url:
            return False

        sessions_path = _nova_img_persist_Path_20260702("data/nova_sessions.json")
        if not sessions_path.exists():
            return False

        data = json.loads(sessions_path.read_text(encoding="utf-8") or "{}")
        changed = False

        for session in _nova_img_persist_find_sessions_20260702(data):
            if str(session.get("id") or session.get("session_id") or "") != str(session_id):
                continue

            meta = session.get("meta")
            if not isinstance(meta, dict):
                meta = {}
            meta["last_image_url"] = image_url
            session["meta"] = meta

            messages = session.get("messages")
            if not isinstance(messages, list):
                continue

            target = None
            for message in reversed(messages):
                if not isinstance(message, dict):
                    continue
                if str(message.get("role") or "").lower() != "assistant":
                    continue
                msg_text = str(message.get("text") or message.get("content") or "")
                msg_meta = message.get("meta") if isinstance(message.get("meta"), dict) else {}
                if (
                    msg_meta.get("source") == "image_generation"
                    or "generated image" in msg_text.lower()
                    or (assistant_text and msg_text.strip() == str(assistant_text).strip())
                ):
                    target = message
                    break

            if target is None:
                target = {
                    "role": "assistant",
                    "text": assistant_text or "Generated image",
                    "content": assistant_text or "Generated image",
                    "attachments": [],
                    "meta": {"source": "image_generation"},
                }
                messages.append(target)

            _nova_img_persist_patch_message_20260702(target, image_url)
            changed = True

        if changed:
            sessions_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        return changed

    def _nova_img_persist_patch_payload_20260702(payload):
        if not isinstance(payload, dict):
            return payload

        assistant_message = payload.get("assistant_message") if isinstance(payload.get("assistant_message"), dict) else {}
        saved_artifact = payload.get("saved_artifact") if isinstance(payload.get("saved_artifact"), dict) else {}
        viewer = saved_artifact.get("viewer") if isinstance(saved_artifact.get("viewer"), dict) else {}

        image_url = (
            payload.get("image_url")
            or assistant_message.get("image_url")
            or saved_artifact.get("image_url")
            or saved_artifact.get("preview")
            or viewer.get("image_url")
            or ""
        )
        image_url = str(image_url or "").strip()

        if not image_url:
            return payload

        session_id = (
            payload.get("session_id")
            or payload.get("active_session_id")
            or assistant_message.get("session_id")
            or saved_artifact.get("session_id")
            or ""
        )

        assistant_text = (
            assistant_message.get("text")
            or assistant_message.get("content")
            or payload.get("text")
            or saved_artifact.get("summary")
            or "Generated image"
        )

        if isinstance(assistant_message, dict):
            payload["assistant_message"] = _nova_img_persist_patch_message_20260702(assistant_message, image_url)

        if isinstance(payload.get("session"), dict):
            messages = payload["session"].get("messages")
            if isinstance(messages, list):
                for message in reversed(messages):
                    if isinstance(message, dict) and str(message.get("role") or "").lower() == "assistant":
                        msg_text = str(message.get("text") or message.get("content") or "")
                        msg_meta = message.get("meta") if isinstance(message.get("meta"), dict) else {}
                        if msg_meta.get("source") == "image_generation" or "generated image" in msg_text.lower():
                            _nova_img_persist_patch_message_20260702(message, image_url)
                            break

        _nova_img_persist_to_session_file_20260702(session_id, image_url, assistant_text)
        return payload

    @app.after_request
    def _nova_generated_image_session_persistence_20260702(response):
        try:
            path = str(getattr(_nova_img_persist_request_20260702, "path", "") or "")
            if not path.endswith("/api/chat"):
                return response

            payload = response.get_json(silent=True)
            if not isinstance(payload, dict):
                return response

            patched = _nova_img_persist_patch_payload_20260702(payload)
            response.set_data(json.dumps(patched))
            response.mimetype = "application/json"
            return response
        except Exception as exc:
            try:
                print("[NOVA_GENERATED_IMAGE_SESSION_PERSISTENCE_20260702] failed:", exc)
            except Exception:
                pass
            return response

    print("[NOVA_GENERATED_IMAGE_SESSION_PERSISTENCE_20260702] installed")
except Exception as _nova_img_persist_install_error_20260702:
    print("[NOVA_GENERATED_IMAGE_SESSION_PERSISTENCE_20260702] install failed:", _nova_img_persist_install_error_20260702)
'''

main_match = re.search(r'(?m)^if\s+__name__\s*==\s*["\']__main__["\']\s*:\s*$', text)
if not main_match:
    raise SystemExit("could not find if __name__ == '__main__'")

new_text = text[:main_match.start()].rstrip() + "\n\n" + block + "\n" + text[main_match.start():]
path.write_text(new_text, encoding="utf-8")
print("installed generated image session persistence above app.run")
