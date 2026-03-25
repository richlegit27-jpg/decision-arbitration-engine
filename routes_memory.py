# C:\Users\Owner\nova\routes_memory.py

from __future__ import annotations

from flask import Blueprint, jsonify, request


memory_bp = Blueprint("memory_bp", __name__)


def _get_ctx():
    from app import (
        DEV_BYPASS_AUTH,
        MEMORY_ITEMS,
        STATE_LOCK,
        current_user,
        get_user_memory_items,
        normalize_username,
        now_iso,
        save_memory,
    )

    return {
        "DEV_BYPASS_AUTH": DEV_BYPASS_AUTH,
        "MEMORY_ITEMS": MEMORY_ITEMS,
        "STATE_LOCK": STATE_LOCK,
        "current_user": current_user,
        "get_user_memory_items": get_user_memory_items,
        "normalize_username": normalize_username,
        "now_iso": now_iso,
        "save_memory": save_memory,
    }


@memory_bp.route("/api/memory", methods=["GET"])
def memory():
    ctx = _get_ctx()
    username = ctx["current_user"]() or "dev"

    if ctx["DEV_BYPASS_AUTH"] and ctx["normalize_username"](username) == "dev":
        return jsonify({"ok": True, "memory": ctx["MEMORY_ITEMS"]})

    return jsonify({"ok": True, "memory": ctx["get_user_memory_items"](username)})


@memory_bp.route("/api/memory", methods=["POST"])
def memory_add():
    import uuid

    ctx = _get_ctx()
    data = request.get_json(silent=True) or {}
    username = ctx["current_user"]() or "dev"
    value = str(data.get("value") or "").strip()
    kind = str(data.get("kind") or "memory").strip()

    if not value:
        return jsonify({"ok": False, "error": "Missing memory value"}), 400

    item = {
        "id": str(uuid.uuid4()),
        "user": ctx["normalize_username"](username),
        "kind": kind or "memory",
        "value": value[:300],
        "created_at": ctx["now_iso"](),
        "updated_at": ctx["now_iso"](),
    }

    with ctx["STATE_LOCK"]:
        ctx["MEMORY_ITEMS"].insert(0, item)
        ctx["save_memory"]()

    if ctx["DEV_BYPASS_AUTH"] and ctx["normalize_username"](username) == "dev":
        memory_payload = ctx["MEMORY_ITEMS"]
    else:
        memory_payload = ctx["get_user_memory_items"](username)

    return jsonify({"ok": True, "item": item, "memory": memory_payload})


@memory_bp.route("/api/memory/delete", methods=["POST"])
def memory_delete():
    ctx = _get_ctx()
    data = request.get_json(silent=True) or {}
    username = ctx["current_user"]() or "dev"
    memory_id = str(data.get("id") or "").strip()

    if not memory_id:
        return jsonify({"ok": False, "error": "Missing memory id"}), 400

    with ctx["STATE_LOCK"]:
        before = len(ctx["MEMORY_ITEMS"])

        if ctx["DEV_BYPASS_AUTH"] and ctx["normalize_username"](username) == "dev":
            ctx["MEMORY_ITEMS"][:] = [
                item
                for item in ctx["MEMORY_ITEMS"]
                if str(item.get("id", "")).strip() != memory_id
            ]
        else:
            ctx["MEMORY_ITEMS"][:] = [
                item
                for item in ctx["MEMORY_ITEMS"]
                if not (
                    str(item.get("id", "")).strip() == memory_id
                    and ctx["normalize_username"](str(item.get("user", ""))) == ctx["normalize_username"](username)
                )
            ]

        changed = len(ctx["MEMORY_ITEMS"]) != before
        if changed:
            ctx["save_memory"]()

    return jsonify({"ok": True, "deleted": changed})