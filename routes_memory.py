from __future__ import annotations

import uuid

from flask import Blueprint, jsonify, request

from auth_utils import DEV_BYPASS_AUTH, current_user, normalize_username
from nova_context import (
    MEMORY_ITEMS,
    STATE_LOCK,
    extract_memory,
    get_user_memory_items,
    now_iso,
    save_memory,
)

memory_bp = Blueprint("memory", __name__, url_prefix="/api/memory")


def _username() -> str:
    if DEV_BYPASS_AUTH:
        return "dev"
    return normalize_username(str(current_user().get("username", "") or ""))


@memory_bp.get("")
def list_memory():
    return jsonify({"ok": True, "items": get_user_memory_items(_username())})


@memory_bp.post("")
def add_memory_root():
    data = request.get_json(silent=True) or {}
    username = _username()

    kind = str(data.get("kind", "memory") or "memory").strip() or "memory"
    value = str(data.get("value", "") or "").strip()

    if not value:
        return jsonify({"ok": False, "error": "value is required"}), 400

    item = {
        "id": str(uuid.uuid4()),
        "user": username,
        "kind": kind[:40],
        "value": value[:500],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }

    with STATE_LOCK:
        MEMORY_ITEMS.append(item)
        save_memory()

    return jsonify({"ok": True, "item": item})


@memory_bp.post("/add")
def add_memory_alias():
    return add_memory_root()


@memory_bp.post("/delete")
def delete_memory():
    data = request.get_json(silent=True) or {}
    item_id = str(data.get("id", "") or "").strip()
    username = _username()

    if not item_id:
        return jsonify({"ok": False, "error": "id is required"}), 400

    with STATE_LOCK:
        before = len(MEMORY_ITEMS)
        MEMORY_ITEMS[:] = [
            item
            for item in MEMORY_ITEMS
            if not (
                str(item.get("id", "")) == item_id
                and normalize_username(str(item.get("user", ""))) == username
            )
        ]
        deleted = len(MEMORY_ITEMS) != before
        if deleted:
            save_memory()

    return jsonify({"ok": True, "deleted": deleted})


@memory_bp.post("/extract")
def extract_memory_route():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "") or "").strip()
    username = _username()

    if not text:
        return jsonify({"ok": False, "error": "text is required"}), 400

    item = extract_memory(text)
    if not item:
        return jsonify({"ok": True, "item": None})

    item["user"] = username

    with STATE_LOCK:
        MEMORY_ITEMS.append(item)
        save_memory()

    return jsonify({"ok": True, "item": item})