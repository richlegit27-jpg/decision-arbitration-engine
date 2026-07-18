from pathlib import Path


def session_attachment_memory_path():
    try:
        base = Path(__file__).resolve().parents[2]
        data_dir = base / "data"
        data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        return data_dir / "nova_session_attachments.json"

    except Exception:
        return Path("data") / "nova_session_attachments.json"


from flask import jsonify



def handle_session_attachment_memory_gate(
    payload,
    attachment_memory_service,
):
    try:
        if not isinstance(payload, dict):
            return None

        session_id = str(
            payload.get("session_id")
            or payload.get("client_session_id")
            or payload.get("active_session_id")
            or ""
        ).strip()

        if not session_id:
            return None

        user_text = str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or ""
        ).strip()

        attachments = payload.get("attachments") or []

        if isinstance(attachments, dict):
            attachments = [attachments]

        if not isinstance(attachments, list):
            attachments = []

        saved = attachment_memory_service.get_or_create_session_attachments(
            session_id,
            attachments,
        )

        if attachments:
            return None

        clean = " ".join(
            user_text.lower().split()
        )

        wants_saved_attachment = (
            (
                "attachment" in clean
                or "file" in clean
                or ".txt" in clean
                or "secret phrase" in clean
            )
            and
            (
                "what" in clean
                or "summarize" in clean
                or "tell me" in clean
                or "secret phrase" in clean
                or "previous" in clean
                or "uploaded" in clean
            )
        )

        if not wants_saved_attachment or not saved:
            return None

        assistant_text = attachment_memory_service.build_saved_attachment_reply(
            user_text,
            saved,
        )

        if not assistant_text:
            return None

        return jsonify({
            "ok": True,
            "active_session_id": session_id,
            "session_id": session_id,
            "text": assistant_text,
            "session_attachments": saved,
            "debug": {
                "route": "api_chat",
                "route_taken": "session_attachment_memory_recall",
            },
        })

    except Exception:
        return None

def handle_stop_fake_attachment_chat_gate(payload):
    try:
        user_text = str(
            payload.get("user_text")
            or ""
        ).strip()

        attachments = payload.get("attachments") or []

        clean = " ".join(
            user_text.lower().split()
        )

        casual_messages = {
            "hi",
            "hey",
            "hello",
            "yo",
            "sup",
            "how are you",
            "how are you?",
            "how you doing",
            "how are u",
            "whats up",
            "what's up",
        }

        if attachments:
            return None

        if clean not in casual_messages:
            return None

        return jsonify({
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": "I'm good. Ready when you are.",
                "attachments": [],
                "meta": {
                    "route": "normal_chat_casual_gate"
                }
            },
            "attachments": [],
            "session_attachments": [],
            "debug": {
                "route": "normal_chat_casual_gate"
            }
        })

    except Exception:
        return None


def handle_attachment_followup_recall_gate(payload):
    try:
        user_text = str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or ""
        ).strip()

        session_id = str(
            payload.get("session_id")
            or ""
        ).strip()

        attachments = payload.get("attachments") or []

        lower = user_text.lower()

        wants_attachment = (
            "attachment" in lower
            and (
                "what was in" in lower
                or "what is in" in lower
                or "summarize" in lower
                or "tell me" in lower
            )
        )

        if not wants_attachment or attachments or not session_id:
            return None

        return None

    except Exception:
        return None