from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, Response, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from services.chat_service import (
    generate_reply,
    generate_reply_stream,
    preview_chat_context,
)
from services.web_service import preview_web_text


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = BASE_DIR / "uploads"

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"

APP_HOST = os.getenv("NOVA_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("PORT", os.getenv("NOVA_PORT", "5001")))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    template_folder=str(TEMPLATES_DIR),
)
app.config["JSON_AS_ASCII"] = False
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_sessions() -> List[Dict[str, Any]]:
    data = read_json_file(SESSIONS_FILE, [])
    return data if isinstance(data, list) else []


def save_sessions(sessions: List[Dict[str, Any]]) -> None:
    write_json_file(SESSIONS_FILE, sessions)


def load_memory() -> List[Dict[str, Any]]:
    data = read_json_file(MEMORY_FILE, [])
    return data if isinstance(data, list) else []


def save_memory(memory_items: List[Dict[str, Any]]) -> None:
    write_json_file(MEMORY_FILE, memory_items)


def make_session(title: Optional[str] = None) -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    created_at = now_iso()
    return {
        "id": session_id,
        "title": (title or "New chat").strip() or "New chat",
        "created_at": created_at,
        "updated_at": created_at,
        "pinned": False,
        "messages": [],
    }


def find_session(session_id: str) -> Optional[Dict[str, Any]]:
    for session in load_sessions():
        if session.get("id") == session_id:
            return session
    return None


def upsert_session(updated_session: Dict[str, Any]) -> None:
    sessions = load_sessions()
    found = False
    for index, session in enumerate(sessions):
        if session.get("id") == updated_session.get("id"):
            sessions[index] = updated_session
            found = True
            break
    if not found:
        sessions.insert(0, updated_session)
    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    save_sessions(sessions)


def delete_session_by_id(session_id: str) -> bool:
    sessions = load_sessions()
    new_sessions = [s for s in sessions if s.get("id") != session_id]
    changed = len(new_sessions) != len(sessions)
    if changed:
        save_sessions(new_sessions)
    return changed


def rename_session_by_id(session_id: str, title: str) -> Optional[Dict[str, Any]]:
    sessions = load_sessions()
    for session in sessions:
        if session.get("id") == session_id:
            session["title"] = (title or "Untitled chat").strip() or "Untitled chat"
            session["updated_at"] = now_iso()
            save_sessions(sessions)
            return session
    return None


def toggle_session_pin(session_id: str) -> Optional[Dict[str, Any]]:
    sessions = load_sessions()
    for session in sessions:
        if session.get("id") == session_id:
            session["pinned"] = not bool(session.get("pinned"))
            session["updated_at"] = now_iso()
            save_sessions(sessions)
            return session
    return None


def message_public_view(message: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": message.get("id"),
        "role": message.get("role"),
        "content": message.get("content", ""),
        "created_at": message.get("created_at"),
        "meta": message.get("meta", {}),
    }


def session_public_view(session: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": session.get("id"),
        "title": session.get("title", "Untitled chat"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "pinned": bool(session.get("pinned")),
        "messages": [message_public_view(m) for m in session.get("messages", [])],
    }


def session_summary_view(session: Dict[str, Any]) -> Dict[str, Any]:
    messages = session.get("messages", [])
    preview = ""
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            preview = str(msg.get("content", "")).strip()
            break
    if not preview and messages:
        preview = str(messages[-1].get("content", "")).strip()

    return {
        "id": session.get("id"),
        "title": session.get("title", "Untitled chat"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
        "pinned": bool(session.get("pinned")),
        "message_count": len(messages),
        "preview": preview[:240],
    }


def build_chat_history(session: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    history: List[Dict[str, str]] = []
    if not session:
        return history
    for msg in session.get("messages", []):
        role = str(msg.get("role") or "").strip().lower()
        content = str(msg.get("content") or "").strip()
        if role in {"user", "assistant", "system"} and content:
            history.append({"role": role, "content": content})
    return history


def guess_title_from_user_text(text: str) -> str:
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return "New chat"
    return cleaned[:60]


def parse_json_request() -> Dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def normalize_attachments(raw_items: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []
    normalized: List[Dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "name": item.get("name") or item.get("filename") or "attachment",
                "summary": item.get("summary") or item.get("preview") or item.get("text") or "",
                "mime_type": item.get("mime_type") or item.get("content_type") or "",
                "url": item.get("url") or "",
            }
        )
    return normalized


def ensure_session_for_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = str(payload.get("session_id") or "").strip()
    if session_id:
        session = find_session(session_id)
        if session:
            return session

    title = str(payload.get("title") or "").strip()
    session = make_session(title=title or None)
    upsert_session(session)
    return session


def build_route_inputs(payload: Dict[str, Any]) -> Dict[str, Any]:
    content = str(
        payload.get("content")
        or payload.get("text")
        or payload.get("message")
        or ""
    ).strip()

    session = ensure_session_for_request(payload)
    history = build_chat_history(session)
    memory = load_memory()
    attachments = normalize_attachments(payload.get("attachments"))

    return {
        "session": session,
        "user_text": content,
        "history": history,
        "memory": memory,
        "attachments": attachments,
        "model": str(payload.get("model") or OPENAI_MODEL).strip() or OPENAI_MODEL,
        "system_prompt": payload.get("system_prompt"),
        "web_enabled": bool(payload.get("web_enabled", True)),
    }


def append_message(
    session: Dict[str, Any],
    *,
    role: str,
    content: str,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    message = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "created_at": now_iso(),
        "meta": meta or {},
    }
    session.setdefault("messages", []).append(message)
    session["updated_at"] = now_iso()
    upsert_session(session)
    return message


def sse_event(event_type: str, data: Dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/")
def index() -> Any:
    return render_template("index.html")


@app.get("/uploads/<path:filename>")
def uploaded_file(filename: str) -> Any:
    return send_from_directory(str(UPLOADS_DIR), filename)


@app.get("/api/health")
def api_health() -> Any:
    sessions = load_sessions()
    memory_items = load_memory()
    return jsonify(
        {
            "ok": True,
            "app": "nova",
            "model": OPENAI_MODEL,
            "sessions": len(sessions),
            "memory_items": len(memory_items),
            "uploads_dir": str(UPLOADS_DIR),
        }
    )


@app.get("/api/models")
def api_models() -> Any:
    default_model = OPENAI_MODEL
    models = []
    for value in [default_model, "gpt-5.4", "gpt-4.1", "gpt-4.1-mini", "gpt-4o-mini"]:
        if value and value not in models:
            models.append(value)
    return jsonify(
        {
            "ok": True,
            "default": default_model,
            "models": models,
        }
    )


@app.get("/api/state")
def api_state() -> Any:
    sessions = load_sessions()
    return jsonify(
        {
            "ok": True,
            "model": OPENAI_MODEL,
            "sessions": [session_summary_view(s) for s in sessions],
            "memory": load_memory(),
        }
    )


@app.post("/api/session/new")
def api_session_new() -> Any:
    payload = parse_json_request()
    title = str(payload.get("title") or "").strip() or "New chat"
    session = make_session(title=title)
    upsert_session(session)
    return jsonify({"ok": True, "session": session_public_view(session)})


@app.get("/api/chat/<session_id>")
def api_chat_get(session_id: str) -> Any:
    session = find_session(session_id)
    if not session:
        return jsonify({"ok": False, "error": "Session not found"}), 404
    return jsonify({"ok": True, "session": session_public_view(session)})


@app.post("/api/session/delete")
def api_session_delete() -> Any:
    payload = parse_json_request()
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400
    deleted = delete_session_by_id(session_id)
    if not deleted:
        return jsonify({"ok": False, "error": "Session not found"}), 404
    return jsonify({"ok": True})


@app.post("/api/session/rename")
def api_session_rename() -> Any:
    payload = parse_json_request()
    session_id = str(payload.get("session_id") or "").strip()
    title = str(payload.get("title") or "").strip()
    if not session_id or not title:
        return jsonify({"ok": False, "error": "session_id and title are required"}), 400
    session = rename_session_by_id(session_id, title)
    if not session:
        return jsonify({"ok": False, "error": "Session not found"}), 404
    return jsonify({"ok": True, "session": session_public_view(session)})


@app.post("/api/session/toggle-pin")
def api_session_toggle_pin() -> Any:
    payload = parse_json_request()
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        return jsonify({"ok": False, "error": "session_id is required"}), 400
    session = toggle_session_pin(session_id)
    if not session:
        return jsonify({"ok": False, "error": "Session not found"}), 404
    return jsonify({"ok": True, "session": session_public_view(session)})


@app.get("/api/memory")
def api_memory_get() -> Any:
    return jsonify({"ok": True, "items": load_memory()})


@app.post("/api/memory/add")
def api_memory_add() -> Any:
    payload = parse_json_request()
    value = str(payload.get("value") or payload.get("text") or "").strip()
    kind = str(payload.get("kind") or "note").strip() or "note"
    if not value:
        return jsonify({"ok": False, "error": "value is required"}), 400

    memory_items = load_memory()
    item = {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "value": value,
        "created_at": now_iso(),
    }
    memory_items.insert(0, item)
    save_memory(memory_items[:200])
    return jsonify({"ok": True, "item": item, "items": load_memory()})


@app.post("/api/memory/delete")
def api_memory_delete() -> Any:
    payload = parse_json_request()
    memory_id = str(payload.get("id") or "").strip()
    if not memory_id:
        return jsonify({"ok": False, "error": "id is required"}), 400

    memory_items = load_memory()
    new_items = [m for m in memory_items if str(m.get("id")) != memory_id]
    if len(new_items) == len(memory_items):
        return jsonify({"ok": False, "error": "Memory item not found"}), 404

    save_memory(new_items)
    return jsonify({"ok": True, "items": new_items})


@app.post("/api/upload")
def api_upload() -> Any:
    files = request.files.getlist("files")
    if not files:
        return jsonify({"ok": False, "error": "No files uploaded"}), 400

    saved: List[Dict[str, Any]] = []
    for file in files:
        original_name = secure_filename(file.filename or "upload.bin")
        unique_name = f"{uuid.uuid4().hex[:12]}-{original_name}"
        target = UPLOADS_DIR / unique_name
        file.save(str(target))
        saved.append(
            {
                "name": original_name,
                "filename": unique_name,
                "url": f"/uploads/{unique_name}",
                "size": target.stat().st_size if target.exists() else 0,
            }
        )

    return jsonify({"ok": True, "files": saved})


@app.post("/api/chat")
def api_chat() -> Any:
    payload = parse_json_request()
    route_inputs = build_route_inputs(payload)

    session = route_inputs["session"]
    user_text = route_inputs["user_text"]

    if not user_text:
        return jsonify({"ok": False, "error": "content is required"}), 400

    if not session.get("messages"):
        session["title"] = guess_title_from_user_text(user_text)

    user_message = append_message(session, role="user", content=user_text)

    reply_text, debug = generate_reply(
        user_text=user_text,
        history=route_inputs["history"],
        memory=route_inputs["memory"],
        attachments=route_inputs["attachments"],
        model=route_inputs["model"],
        system_prompt=route_inputs["system_prompt"],
        web_enabled=route_inputs["web_enabled"],
    )

    assistant_message = append_message(
        session,
        role="assistant",
        content=reply_text,
        meta={"debug": debug},
    )

    return jsonify(
        {
            "ok": True,
            "session": session_public_view(session),
            "message": message_public_view(assistant_message),
            "user_message": message_public_view(user_message),
            "debug": debug,
        }
    )


@app.post("/api/chat/stream")
def api_chat_stream() -> Any:
    payload = parse_json_request()
    route_inputs = build_route_inputs(payload)

    session = route_inputs["session"]
    user_text = route_inputs["user_text"]

    if not user_text:
        return jsonify({"ok": False, "error": "content is required"}), 400

    if not session.get("messages"):
        session["title"] = guess_title_from_user_text(user_text)

    user_message = append_message(session, role="user", content=user_text)

    iterator, debug = generate_reply_stream(
        user_text=user_text,
        history=route_inputs["history"],
        memory=route_inputs["memory"],
        attachments=route_inputs["attachments"],
        model=route_inputs["model"],
        system_prompt=route_inputs["system_prompt"],
        web_enabled=route_inputs["web_enabled"],
    )

    def event_stream() -> Any:
        assistant_parts: List[str] = []
        assistant_message_id = str(uuid.uuid4())

        yield sse_event(
            "start",
            {
                "ok": True,
                "session_id": session["id"],
                "user_message_id": user_message["id"],
                "assistant_message_id": assistant_message_id,
                "debug": debug,
            },
        )

        for item in iterator:
            item_type = str(item.get("type") or "").strip().lower()

            if item_type == "delta":
                delta = str(item.get("delta") or "")
                if delta:
                    assistant_parts.append(delta)
                    yield sse_event(
                        "delta",
                        {
                            "delta": delta,
                            "assistant_message_id": assistant_message_id,
                            "session_id": session["id"],
                        },
                    )
                continue

            if item_type == "error":
                error_text = str(item.get("error") or "Streaming failed")
                yield sse_event(
                    "error",
                    {
                        "error": error_text,
                        "assistant_message_id": assistant_message_id,
                        "session_id": session["id"],
                    },
                )
                return

            if item_type == "done":
                final_text = str(item.get("text") or "".join(assistant_parts)).strip()
                assistant_message = {
                    "id": assistant_message_id,
                    "role": "assistant",
                    "content": final_text,
                    "created_at": now_iso(),
                    "meta": {"debug": debug},
                }
                session.setdefault("messages", []).append(assistant_message)
                session["updated_at"] = now_iso()
                upsert_session(session)

                yield sse_event(
                    "done",
                    {
                        "ok": True,
                        "text": final_text,
                        "message": message_public_view(assistant_message),
                        "session_id": session["id"],
                        "assistant_message_id": assistant_message_id,
                        "debug": debug,
                    },
                )
                return

        final_text = "".join(assistant_parts).strip()
        assistant_message = {
            "id": assistant_message_id,
            "role": "assistant",
            "content": final_text,
            "created_at": now_iso(),
            "meta": {"debug": debug},
        }
        session.setdefault("messages", []).append(assistant_message)
        session["updated_at"] = now_iso()
        upsert_session(session)

        yield sse_event(
            "done",
            {
                "ok": True,
                "text": final_text,
                "message": message_public_view(assistant_message),
                "session_id": session["id"],
                "assistant_message_id": assistant_message_id,
                "debug": debug,
            },
        )

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/debug/brain")
def api_debug_brain() -> Any:
    payload = parse_json_request()
    content = str(
        payload.get("content")
        or payload.get("text")
        or payload.get("message")
        or ""
    ).strip()

    preview = preview_chat_context(
        user_text=content,
        history=[],
        memory=load_memory(),
        attachments=normalize_attachments(payload.get("attachments")),
        system_prompt=payload.get("system_prompt"),
        web_enabled=bool(payload.get("web_enabled", True)),
    )

    return jsonify(
        {
            "ok": True,
            "message_count": len(preview.get("messages", [])),
            "messages_preview": preview.get("messages", [])[:6],
            "debug": preview.get("debug", {}),
        }
    )


@app.post("/api/debug/web_preview")
def api_debug_web_preview() -> Any:
    payload = parse_json_request()
    text = str(payload.get("text") or payload.get("content") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "text is required"}), 400

    result = preview_web_text(text)
    return jsonify(
        {
            "ok": True,
            "result": result,
            "summary": (
                f"Title: {result.get('title', '')}\n"
                f"URL: {result.get('final_url', '')}\n"
                f"Type: {result.get('content_type', '')}\n"
                f"Preview: {result.get('preview', '')}"
            ).strip(),
        }
    )


@app.get("/api/artifacts")
def api_artifacts_list() -> Any:
    return jsonify({"ok": True, "artifacts": []})


@app.get("/api/artifacts/<artifact_id>")
def api_artifacts_get(artifact_id: str) -> Any:
    return jsonify({"ok": False, "error": f"Artifact not found: {artifact_id}"}), 404


@app.post("/api/artifacts/create")
def api_artifacts_create() -> Any:
    return jsonify({"ok": False, "error": "Artifact create not wired yet"}), 501


@app.post("/api/artifacts/update")
def api_artifacts_update() -> Any:
    return jsonify({"ok": False, "error": "Artifact update not wired yet"}), 501


@app.post("/api/artifacts/save")
def api_artifacts_save() -> Any:
    return jsonify({"ok": False, "error": "Artifact save not wired yet"}), 501


@app.post("/api/artifacts/delete")
def api_artifacts_delete() -> Any:
    return jsonify({"ok": False, "error": "Artifact delete not wired yet"}), 501


@app.post("/api/artifacts/pin")
def api_artifacts_pin() -> Any:
    return jsonify({"ok": False, "error": "Artifact pin not wired yet"}), 501


@app.post("/api/artifacts/toggle-pin")
def api_artifacts_toggle_pin() -> Any:
    return jsonify({"ok": False, "error": "Artifact toggle pin not wired yet"}), 501


@app.post("/api/artifacts/export")
def api_artifacts_export() -> Any:
    return jsonify({"ok": False, "error": "Artifact export not wired yet"}), 501


if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT, debug=True)