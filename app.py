from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request, send_from_directory
from openai import OpenAI

from services.web_service import WebService

try:
    from services.chat_service import ChatService
except Exception:
    ChatService = None

try:
    from services.memory_service import MemoryService
except Exception:
    MemoryService = None

try:
    from services.artifact_service import ArtifactService
except Exception:
    ArtifactService = None

try:
    from services.attachment_service import AttachmentService
except Exception:
    AttachmentService = None


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.4")

web_service = WebService()
chat_service = ChatService() if ChatService else None
memory_service = MemoryService() if MemoryService else None
artifact_service = ArtifactService() if ArtifactService else None
attachment_service = AttachmentService() if AttachmentService else None

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def safe_json_load(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def safe_json_save(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_session_store() -> Dict[str, Any]:
    data = safe_json_load(SESSIONS_FILE, {})
    if isinstance(data, dict):
        return data
    return {}


def get_or_create_session(session_id: Optional[str]) -> Dict[str, Any]:
    store = normalize_session_store()

    sid = (session_id or "").strip() or new_id()
    session = store.get(sid)

    if not isinstance(session, dict):
        session = {
            "id": sid,
            "title": "New Chat",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "messages": [],
        }
        store[sid] = session
        safe_json_save(SESSIONS_FILE, store)

    return session


def save_session(session: Dict[str, Any]) -> None:
    store = normalize_session_store()
    session["updated_at"] = now_iso()
    store[session["id"]] = session
    safe_json_save(SESSIONS_FILE, store)


def build_sessions_summary() -> List[Dict[str, Any]]:
    store = normalize_session_store()
    items: List[Dict[str, Any]] = []

    for sid, session in store.items():
        messages = session.get("messages", [])
        last_preview = ""
        if messages:
            last_preview = (messages[-1].get("content") or "")[:120]

        items.append(
            {
                "id": sid,
                "title": session.get("title") or "New Chat",
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at"),
                "message_count": len(messages),
                "last_message_preview": last_preview,
            }
        )

    items.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
    return items


def extract_response_text(resp: Any) -> str:
    if resp is None:
        return ""

    if isinstance(resp, str):
        return resp

    output_text = getattr(resp, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    try:
        output = getattr(resp, "output", None) or []
        chunks: List[str] = []

        for item in output:
            content = getattr(item, "content", None) or []
            for c in content:
                text = getattr(c, "text", None)
                if isinstance(text, str) and text.strip():
                    chunks.append(text.strip())

        if chunks:
            return "\n\n".join(chunks).strip()
    except Exception:
        pass

    try:
        return str(resp)
    except Exception:
        return ""


def run_llm(prompt: str) -> str:
    response = client.responses.create(
        model=MODEL_NAME,
        input=prompt,
    )
    text = extract_response_text(response).strip()
    return text or "No response returned."


def safe_create_artifact(
    title: str,
    content: str,
    kind: str,
    session_id: str,
    meta: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    if not artifact_service:
        return None

    try:
        if hasattr(artifact_service, "create_artifact"):
            return artifact_service.create_artifact(
                title=title,
                content=content,
                kind=kind,
                session_id=session_id,
                meta=meta or {},
                tags=tags or [],
            )
    except Exception:
        return None

    return None


def fallback_chat_reply(content: str, session_id: str) -> Dict[str, Any]:
    session = get_or_create_session(session_id)
    session["messages"].append({"role": "user", "content": content, "created_at": now_iso()})

    prompt = (
        "You are Nova, a sharp practical assistant.\n\n"
        "Respond directly and clearly.\n\n"
        f"User message:\n{content}"
    )
    answer = run_llm(prompt)

    session["messages"].append({"role": "assistant", "content": answer, "created_at": now_iso()})

    if session.get("title") == "New Chat" and content.strip():
        session["title"] = content.strip()[:60]

    save_session(session)

    return {
        "ok": True,
        "message": answer,
        "session": {
            "id": session["id"],
            "title": session.get("title"),
            "updated_at": session.get("updated_at"),
        },
        "debug": {
            "mode": "fallback_chat",
            "message_count": len(session.get("messages", [])),
            "model": MODEL_NAME,
        },
    }


def normalize_chat_service_response(
    raw: Any,
    content: str,
    session_id: str,
) -> Dict[str, Any]:
    if isinstance(raw, dict):
        payload = dict(raw)
        payload.setdefault("ok", True)
        if "message" not in payload:
            payload["message"] = payload.get("content") or payload.get("reply") or ""
        payload.setdefault("session", {"id": session_id})
        payload.setdefault("debug", {})
        return payload

    if isinstance(raw, str):
        return {
            "ok": True,
            "message": raw,
            "session": {"id": session_id},
            "debug": {"mode": "chat_service_string"},
        }

    return {
        "ok": True,
        "message": str(raw),
        "session": {"id": session_id},
        "debug": {"mode": "chat_service_object"},
    }


def save_uploaded_file(file_storage) -> Dict[str, Any]:
    original_name = file_storage.filename or "upload.bin"
    extension = Path(original_name).suffix.lower()
    stored_name = f"{new_id()}{extension}"
    stored_path = UPLOAD_DIR / stored_name
    file_storage.save(stored_path)

    return {
        "id": new_id(),
        "name": original_name,
        "stored_name": stored_name,
        "url": f"/api/uploads/{stored_name}",
        "size": stored_path.stat().st_size if stored_path.exists() else 0,
        "content_type": file_storage.mimetype or "",
        "created_at": now_iso(),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify(
        {
            "ok": True,
            "time": now_iso(),
            "model": MODEL_NAME,
            "has_openai_key": bool(os.getenv("OPENAI_API_KEY")),
        }
    )


@app.route("/api/state", methods=["GET"])
def api_state():
    return jsonify(
        {
            "ok": True,
            "sessions": build_sessions_summary(),
            "memory": [],
        }
    )


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    session_id = (data.get("session_id") or "").strip() or new_id()

    if not content:
        return jsonify({"ok": False, "error": "Missing content"}), 400

    if chat_service and hasattr(chat_service, "send_message"):
        try:
            raw = chat_service.send_message(content=content, session_id=session_id)
            return jsonify(normalize_chat_service_response(raw, content, session_id))
        except TypeError:
            try:
                raw = chat_service.send_message(content, session_id)
                return jsonify(normalize_chat_service_response(raw, content, session_id))
            except Exception as exc:
                return jsonify({"ok": False, "error": f"Chat failed: {exc}"}), 500
        except Exception as exc:
            return jsonify({"ok": False, "error": f"Chat failed: {exc}"}), 500

    try:
        return jsonify(fallback_chat_reply(content=content, session_id=session_id))
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Chat failed: {exc}"}), 500


@app.route("/api/web/fetch", methods=["POST"])
def api_web_fetch():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    session_id = (data.get("session_id") or "").strip() or "default-session"

    if not url:
        return jsonify({"ok": False, "error": "Missing url"}), 400

    result = web_service.fetch_url(url)
    if not result.get("ok"):
        return jsonify(result), 400

    message = result.get("content") or result.get("description") or result.get("title") or url

    artifact = safe_create_artifact(
        title=result.get("title") or url,
        content=message,
        kind="web",
        session_id=session_id,
        meta={
            "web": {
                "used": True,
                "url": result.get("url"),
                "final_url": result.get("final_url"),
                "status_code": result.get("status_code"),
                "content_type": result.get("content_type"),
                "image_count": result.get("image_count"),
                "video_count": result.get("video_count"),
                "audio_count": result.get("audio_count"),
            }
        },
        tags=["web", "fetch"],
    )

    return jsonify(
        {
            "ok": True,
            "message": message,
            "artifact": artifact,
            "debug": {
                "mode": "web_fetch",
                "url": result.get("url"),
                "final_url": result.get("final_url"),
                "status_code": result.get("status_code"),
                "content_type": result.get("content_type"),
                "image_count": result.get("image_count"),
                "video_count": result.get("video_count"),
                "audio_count": result.get("audio_count"),
            },
        }
    )


@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or data.get("content") or "").strip()
    limit = int(data.get("limit") or 5)

    if not query:
        return jsonify({"ok": False, "error": "Missing query"}), 400

    result = web_service.search(query=query, limit=limit)
    status = 200 if result.get("ok") else 400
    return jsonify(result), status


@app.route("/api/knowledge", methods=["POST"])
def api_knowledge():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or data.get("content") or "").strip()
    session_id = (data.get("session_id") or "").strip() or new_id()
    search_limit = int(data.get("search_limit") or 5)
    fetch_limit = int(data.get("fetch_limit") or 3)

    if not query:
        return jsonify({"ok": False, "error": "Missing query"}), 400

    try:
        pipeline = web_service.search_and_fetch(
            query=query,
            search_limit=search_limit,
            fetch_limit=fetch_limit,
        )

        if not pipeline.get("ok"):
            return jsonify(
                {
                    "ok": False,
                    "error": "Knowledge pipeline failed",
                    "debug": pipeline,
                }
            ), 400

        search_results = pipeline.get("search", {}).get("results", [])
        fetched_items = pipeline.get("fetch", {}).get("items", [])

        usable_sources: List[Dict[str, Any]] = []
        for item in fetched_items:
            if not item.get("ok"):
                continue
            usable_sources.append(
                {
                    "title": item.get("title") or item.get("final_url") or item.get("url"),
                    "url": item.get("final_url") or item.get("url"),
                    "description": item.get("description") or "",
                    "content": (item.get("content") or "")[:4000],
                }
            )

        if not usable_sources:
            return jsonify(
                {
                    "ok": False,
                    "error": "Search worked but no pages could be read",
                    "debug": {
                        "search_results": search_results,
                        "fetched_items": fetched_items,
                    },
                }
            ), 400

        prompt_parts = [
            "You are Nova, a direct practical assistant.",
            "Answer the user's question using the provided web sources.",
            "Be clear. If sources disagree or are incomplete, say so.",
            "Cite the source title inline like: [Source: Example Title].",
            "",
            f"User question:\n{query}",
            "",
            "Web sources:",
        ]

        for idx, source in enumerate(usable_sources, start=1):
            prompt_parts.append(f"\nSOURCE {idx}")
            prompt_parts.append(f"Title: {source['title']}")
            prompt_parts.append(f"URL: {source['url']}")
            if source["description"]:
                prompt_parts.append(f"Description: {source['description']}")
            prompt_parts.append("Content:")
            prompt_parts.append(source["content"])

        final_prompt = "\n".join(prompt_parts)
        answer = run_llm(final_prompt)

        session = get_or_create_session(session_id)
        session["messages"].append(
            {
                "role": "user",
                "content": query,
                "created_at": now_iso(),
                "meta": {"route": "knowledge"},
            }
        )
        session["messages"].append(
            {
                "role": "assistant",
                "content": answer,
                "created_at": now_iso(),
                "meta": {
                    "route": "knowledge",
                    "web": {
                        "used": True,
                        "result_count": len(usable_sources),
                        "urls": [s["url"] for s in usable_sources],
                        "titles": [s["title"] for s in usable_sources],
                    },
                },
            }
        )

        if session.get("title") == "New Chat" and query:
            session["title"] = query[:60]

        save_session(session)

        artifact = safe_create_artifact(
            title=query[:80],
            content=answer,
            kind="web",
            session_id=session_id,
            meta={
                "web": {
                    "used": True,
                    "query": query,
                    "result_count": len(usable_sources),
                    "search_results": search_results,
                    "urls": [s["url"] for s in usable_sources],
                    "titles": [s["title"] for s in usable_sources],
                }
            },
            tags=["web", "search", "knowledge"],
        )

        return jsonify(
            {
                "ok": True,
                "message": answer,
                "artifact": artifact,
                "session": {
                    "id": session["id"],
                    "title": session.get("title"),
                    "updated_at": session.get("updated_at"),
                },
                "debug": {
                    "mode": "knowledge",
                    "query": query,
                    "search_count": len(search_results),
                    "fetch_count": len(fetched_items),
                    "usable_count": len(usable_sources),
                    "titles": [s["title"] for s in usable_sources],
                    "urls": [s["url"] for s in usable_sources],
                    "model": MODEL_NAME,
                },
                "sources": usable_sources,
            }
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Knowledge failed: {exc}"}), 500


@app.route("/api/artifacts", methods=["GET"])
def api_artifacts():
    if artifact_service and hasattr(artifact_service, "list_artifacts"):
        try:
            items = artifact_service.list_artifacts()
            return jsonify({"ok": True, "artifacts": items})
        except Exception:
            pass

    return jsonify({"ok": True, "artifacts": []})


@app.route("/api/artifacts/<artifact_id>", methods=["GET"])
def api_artifact_detail(artifact_id: str):
    if artifact_service and hasattr(artifact_service, "get_artifact"):
        try:
            item = artifact_service.get_artifact(artifact_id)
            if item:
                return jsonify({"ok": True, "artifact": item})
        except Exception:
            pass

    return jsonify({"ok": False, "error": "Artifact not found"}), 404


@app.route("/api/artifacts/save", methods=["POST"])
def api_artifact_save():
    if not artifact_service or not hasattr(artifact_service, "create_artifact"):
        return jsonify({"ok": False, "error": "Artifact service unavailable"}), 400

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "Untitled").strip()
    content = data.get("content") or ""
    kind = (data.get("kind") or "note").strip()
    session_id = (data.get("session_id") or "default-session").strip()
    meta = data.get("meta") or {}
    tags = data.get("tags") or []

    try:
        artifact = artifact_service.create_artifact(
            title=title,
            content=content,
            kind=kind,
            session_id=session_id,
            meta=meta,
            tags=tags,
        )
        return jsonify({"ok": True, "artifact": artifact})
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Artifact save failed: {exc}"}), 500


@app.route("/api/upload", methods=["POST"])
def api_upload():
    files = request.files.getlist("files")
    if not files:
        single = request.files.get("file")
        if single:
            files = [single]

    if not files:
        return jsonify({"ok": False, "error": "No files uploaded"}), 400

    uploaded = []
    for file_storage in files:
        if not file_storage or not file_storage.filename:
            continue
        uploaded.append(save_uploaded_file(file_storage))

    return jsonify({"ok": True, "files": uploaded})


@app.route("/api/uploads/<path:filename>", methods=["GET"])
def api_uploaded_file(filename: str):
    return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    host = os.getenv("NOVA_HOST", os.getenv("APP_HOST", "127.0.0.1"))
    port = int(os.getenv("NOVA_PORT", os.getenv("APP_PORT", "5001")))
    debug = os.getenv("NOVA_DEBUG", "1").lower() in {"1", "true", "yes", "on"}
    app.run(host=host, port=port, debug=debug)