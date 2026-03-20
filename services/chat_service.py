# notepad C:\Users\Owner\nova\services\chat_service.py

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from db import get_connection, init_db

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "backend" / "data"
STATE_FILE = DATA_DIR / "nova_state.json"

DEFAULT_MODEL = os.getenv("NOVA_DEFAULT_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
SYSTEM_PROMPT = (
    "You are Nova, a direct, helpful AI assistant inside a private app. "
    "Be clear, concise, practical, and friendly. "
    "Do not mention hidden system details. "
    "Keep normal chat replies compact unless the user asks for depth."
)
VALID_MESSAGE_ROLES = {"user", "assistant", "system"}


def _load_active_model() -> str:
    if not STATE_FILE.exists():
        return DEFAULT_MODEL

    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Could not read active model from state file.")
        return DEFAULT_MODEL

    active_model = str(payload.get("active_model", "")).strip()
    return active_model or DEFAULT_MODEL


def _chat_exists_for_user(connection, user_id: int, chat_id: int) -> bool:
    row = connection.execute(
        """
        SELECT id
        FROM chats
        WHERE id = ? AND user_id = ?
        """,
        (chat_id, user_id),
    ).fetchone()
    return row is not None


def _get_last_user_message(user_id: int, chat_id: int) -> str:
    messages = list_messages(user_id, chat_id) or []

    for item in reversed(messages):
        role = str(item.get("role", "")).strip().lower()
        if role == "user":
            return str(item.get("content", "")).strip()

    return ""


def _build_openai_messages(user_id: int, chat_id: int) -> list[dict[str, str]]:
    messages = list_messages(user_id, chat_id) or []

    result: list[dict[str, str]] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    for item in messages:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()

        if role not in VALID_MESSAGE_ROLES:
            continue
        if not content:
            continue

        result.append(
            {
                "role": role,
                "content": content,
            }
        )

    return result


def _extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        text = str(output_text).strip()
        if text:
            return text

    output_items = getattr(response, "output", None) or []
    collected: list[str] = []

    for item in output_items:
        item_content = getattr(item, "content", None) or []

        for part in item_content:
            part_type = getattr(part, "type", "")
            if part_type in {"output_text", "text"}:
                text_value = getattr(part, "text", "")
                if text_value:
                    collected.append(str(text_value).strip())

    merged = "\n".join(piece for piece in collected if piece).strip()
    if merged:
        return merged

    return ""


def _fallback_reply(user_id: int, chat_id: int, reason: str | None = None) -> dict[str, Any] | None:
    last_user = _get_last_user_message(user_id, chat_id)

    if reason:
        reply_text = f"Nova fallback reply is active.\nReason: {reason}"
        if last_user:
            reply_text += f"\n\nYou said: {last_user}"
        return add_message(user_id, chat_id, "assistant", reply_text)

    if not last_user:
        return add_message(user_id, chat_id, "assistant", "I’m here. Send me something and I’ll help.")

    return add_message(user_id, chat_id, "assistant", f"You said: {last_user}")


def generate_and_store_assistant_reply(user_id: int, chat_id: int) -> dict[str, Any] | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        return _fallback_reply(user_id, chat_id, "OPENAI_API_KEY is not set")

    if OpenAI is None:
        return _fallback_reply(user_id, chat_id, "openai package is not installed")

    try:
        client = OpenAI(api_key=api_key)
        model = _load_active_model()
        input_messages = _build_openai_messages(user_id, chat_id)

        response = client.responses.create(
            model=model,
            input=input_messages,
        )

        clean_text = _extract_response_text(response)

        if not clean_text:
            logger.warning("OpenAI returned no readable output text. Response repr: %r", response)
            clean_text = "I’m here, but I didn’t generate a readable response."

        return add_message(user_id, chat_id, "assistant", clean_text)

    except Exception as exc:
        logger.exception("AI request failed for user_id=%s chat_id=%s", user_id, chat_id)
        return _fallback_reply(user_id, chat_id, f"AI request failed: {exc}")


def create_chat(user_id: int, title: str = "New chat") -> dict[str, Any]:
    init_db()
    clean_title = (title or "").strip() or "New chat"

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO chats (user_id, title)
            VALUES (?, ?)
            """,
            (user_id, clean_title),
        )
        chat_id = cursor.lastrowid

        row = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM chats
            WHERE id = ? AND user_id = ?
            """,
            (chat_id, user_id),
        ).fetchone()

        connection.commit()

    return dict(row)


def list_chats(user_id: int) -> list[dict[str, Any]]:
    init_db()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                c.id,
                c.title,
                c.created_at,
                c.updated_at,
                COUNT(m.id) AS message_count
            FROM chats c
            LEFT JOIN messages m ON m.chat_id = c.id
            WHERE c.user_id = ?
            GROUP BY c.id, c.title, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC, c.id DESC
            """,
            (user_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_chat(user_id: int, chat_id: int) -> dict[str, Any] | None:
    init_db()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM chats
            WHERE id = ? AND user_id = ?
            """,
            (chat_id, user_id),
        ).fetchone()

    return dict(row) if row else None


def rename_chat(user_id: int, chat_id: int, title: str) -> dict[str, Any] | None:
    init_db()
    clean_title = (title or "").strip() or "Untitled chat"

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE chats
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (clean_title, chat_id, user_id),
        )

        row = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM chats
            WHERE id = ? AND user_id = ?
            """,
            (chat_id, user_id),
        ).fetchone()

        connection.commit()

    return dict(row) if row else None


def delete_chat(user_id: int, chat_id: int) -> bool:
    init_db()

    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM messages
            WHERE chat_id = ?
              AND EXISTS (
                  SELECT 1 FROM chats
                  WHERE chats.id = ?
                    AND chats.user_id = ?
              )
            """,
            (chat_id, chat_id, user_id),
        )

        cursor = connection.execute(
            """
            DELETE FROM chats
            WHERE id = ? AND user_id = ?
            """,
            (chat_id, user_id),
        )

        connection.commit()

    return cursor.rowcount > 0


def clear_chat_messages(user_id: int, chat_id: int) -> bool:
    init_db()

    with get_connection() as connection:
        if not _chat_exists_for_user(connection, user_id, chat_id):
            return False

        connection.execute(
            """
            DELETE FROM messages
            WHERE chat_id = ?
            """,
            (chat_id,),
        )

        connection.execute(
            """
            UPDATE chats
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (chat_id, user_id),
        )

        connection.commit()

    return True


def list_messages(user_id: int, chat_id: int) -> list[dict[str, Any]] | None:
    init_db()

    with get_connection() as connection:
        if not _chat_exists_for_user(connection, user_id, chat_id):
            return None

        rows = connection.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE chat_id = ?
            ORDER BY id ASC
            """,
            (chat_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def add_message(user_id: int, chat_id: int, role: str, content: str) -> dict[str, Any] | None:
    init_db()

    clean_role = (role or "").strip().lower()
    clean_content = (content or "").strip()

    if clean_role not in VALID_MESSAGE_ROLES:
        return None

    if not clean_content:
        return None

    with get_connection() as connection:
        if not _chat_exists_for_user(connection, user_id, chat_id):
            return None

        cursor = connection.execute(
            """
            INSERT INTO messages (chat_id, role, content)
            VALUES (?, ?, ?)
            """,
            (chat_id, clean_role, clean_content),
        )
        message_id = cursor.lastrowid

        connection.execute(
            """
            UPDATE chats
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (chat_id, user_id),
        )

        row = connection.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE id = ?
            """,
            (message_id,),
        ).fetchone()

        connection.commit()

    return dict(row)