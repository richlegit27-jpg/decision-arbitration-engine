import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

from flask import jsonify


class MobileSessionPersistService:

    def persist(
        self,
        payload,
        sessions_file,
    ):
        try:
            payload = payload if isinstance(payload, dict) else {}

            session_id = str(
                payload.get("session_id")
                or payload.get("client_session_id")
                or payload.get("active_session_id")
                or ""
            ).strip()

            user_text = str(
                payload.get("user_text")
                or payload.get("text")
                or payload.get("message")
                or ""
            ).strip()

            assistant_text = str(
                payload.get("assistant_text")
                or payload.get("assistant")
                or payload.get("response")
                or ""
            ).strip()

            if not session_id:
                session_id = "mobile_" + uuid.uuid4().hex[:16]

            if not user_text and not assistant_text:
                return jsonify({
                    "ok": False,
                    "error": "No message text supplied.",
                }), 400

            sessions_path = Path(sessions_file)
            sessions_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            if sessions_path.exists():
                raw = sessions_path.read_text(
                    encoding="utf-8-sig"
                ).strip()

                data = json.loads(raw) if raw else {
                    "sessions": []
                }

            else:
                data = {
                    "sessions": []
                }

            if isinstance(data, list):
                data = {
                    "sessions": data
                }

            sessions = data.setdefault(
                "sessions",
                [],
            )

            now = datetime.now(
                timezone.utc
            ).isoformat()

            session = None

            for item in sessions:
                if (
                    isinstance(item, dict)
                    and str(item.get("id") or "") == session_id
                ):
                    session = item
                    break

            if session is None:
                session = {
                    "id": session_id,
                    "title": user_text[:60] or "New Chat",
                    "created_at": now,
                    "updated_at": now,
                    "pinned": False,
                    "messages": [],
                    "working_state": {},
                    "active_execution": None,
                }

                sessions.append(session)

            messages = session.setdefault(
                "messages",
                [],
            )

            recent_pairs = [
                (
                    str(messages[i].get("text") or "").strip(),
                    str(messages[i + 1].get("text") or "").strip()
                    if i + 1 < len(messages)
                    and isinstance(messages[i + 1], dict)
                    else ""
                )
                for i in range(
                    max(0, len(messages) - 10),
                    len(messages),
                )
                if isinstance(messages[i], dict)
            ]

            if (
                user_text,
                assistant_text,
            ) not in recent_pairs:

                if user_text:
                    messages.append({
                        "id": "msg_" + uuid.uuid4().hex,
                        "role": "user",
                        "text": user_text,
                        "attachments": payload.get("attachments")
                        if isinstance(payload.get("attachments"), list)
                        else [],
                        "created_at": now,
                        "updated_at": now,
                        "meta": {
                            "route": "mobile_direct_session_persist",
                        },
                    })

                if assistant_text:
                    messages.append({
                        "id": "msg_" + uuid.uuid4().hex,
                        "role": "assistant",
                        "text": assistant_text,
                        "attachments": [],
                        "created_at": now,
                        "updated_at": now,
                        "meta": {
                            "route": "mobile_direct_session_persist",
                        },
                    })

            session["updated_at"] = now

            tmp = sessions_path.with_suffix(
                sessions_path.suffix + ".tmp"
            )

            tmp.write_text(
                json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            tmp.replace(
                sessions_path
            )

            return jsonify({
                "ok": True,
                "session_id": session_id,
                "messages": len(messages),
            })

        except Exception as exc:
            return jsonify({
                "ok": False,
                "error": str(exc),
            }), 500