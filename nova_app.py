from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, Response
from openai import OpenAI
from werkzeug.utils import secure_filename
import copy
import json
import os
import re
import time
import uuid

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_FILE = DATA_DIR / "nova_sessions.json"
MEMORY_FILE = DATA_DIR / "nova_memory.json"

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
DEFAULT_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip() or "gpt-4.1-mini"

MAX_UPLOAD_FILES = 10
MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB per file

SYSTEM_PROMPT = (
    "You are Nova, an elite AI assistant. "
    "Be clear, direct, intelligent, and efficient. "
    "Give strong structured answers without fluff. "
    "Do not invent facts. If you are unsure, say so plainly. "
    "Use saved memory only when it is relevant to the user's request. "
    "Treat saved memory as user-specific context, not as facts about the outside world."
)

MAX_CONTEXT_MESSAGES = 12
MAX_MEMORY_ITEMS = 50
MAX_MEMORY_PROMPT_ITEMS = 12

MEMORY_KIND_ORDER = ["name", "preference", "goal", "project", "skill", "workflow", "memory"]
MEMORY_KIND_LABELS = {
    "name": "Name",
    "preference": "Preference",
    "goal": "Goal",
    "project": "Project",
    "skill": "Skill",
    "workflow": "Workflow",
    "memory": "Memory",
}

LOW_VALUE_MEMORY_EXACT = {
    "yes",
    "no",
    "maybe",
    "okay",
    "ok",
    "cool",
    "nice",
    "thanks",
    "thank you",
    "hello",
    "hi",
    "hey",
    "test",
}

LOW_VALUE_MEMORY_PHRASES = [
    "right now",
    "today",
    "tomorrow",
    "yesterday",
    "this morning",
    "this afternoon",
    "this evening",
    "good question",
    "that makes sense",
    "i don't know",
    "not sure",
]

PREFERENCE_PREFIX_BLACKLIST = (
    "that ",
    "this ",
    "it ",
    "to ",
    "for now",
)

app = Flask(__name__, static_folder=str(STATIC_DIR), template_folder=str(TEMPLATES_DIR))
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_FILES * MAX_UPLOAD_SIZE_BYTES
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def now() -> int:
    return int(time.time())


def load_json_file(path: Path, default):
    if not path.exists():
        return default
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)
    except Exception:
        return default


def save_json_file(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_sessions():
    data = load_json_file(SESSIONS_FILE, [])
    return data if isinstance(data, list) else []


def save_sessions(sessions) -> None:
    save_json_file(SESSIONS_FILE, sessions)


def load_memory():
    data = load_json_file(MEMORY_FILE, {"items": []})
    if not isinstance(data, dict):
        return {"items": []}
    items = data.get("items", [])
    if not isinstance(items, list):
        items = []
    return {"items": items}


def save_memory(memory) -> None:
    save_json_file(MEMORY_FILE, memory)


def get_session(sessions, session_id: str):
    for session in sessions:
        if session.get("session_id") == session_id:
            return session
    return None


def create_session(title: str = "New Chat"):
    ts = now()
    return {
        "session_id": str(uuid.uuid4()),
        "title": title,
        "messages": [],
        "message_count": 0,
        "created_at": ts,
        "updated_at": ts,
    }


def summarize_sessions(sessions):
    items = []
    for session in sessions:
        messages = session.get("messages", [])
        items.append({
            "session_id": session.get("session_id"),
            "title": session.get("title") or "New Chat",
            "message_count": len(messages) if isinstance(messages, list) else 0,
            "updated_at": int(session.get("updated_at") or session.get("created_at") or now()),
        })
    items.sort(key=lambda x: x["updated_at"], reverse=True)
    return items


def normalize_text(value) -> str:
    return " ".join(str(value or "").split()).strip()


def generate_title(text: str) -> str:
    clean = normalize_text(text)
    if not clean:
        return "New Chat"
    if len(clean) <= 48:
        return clean
    return clean[:48].rstrip(" .,!?:;-") + "..."


def build_upload_context(uploaded_files) -> str:
    files = uploaded_files if isinstance(uploaded_files, list) else []
    if not files:
        return ""

    lines = []
    for item in files[:MAX_UPLOAD_FILES]:
        if not isinstance(item, dict):
            continue
        original_name = normalize_text(item.get("original_name")) or "unknown"
        content_type = normalize_text(item.get("content_type")) or "application/octet-stream"
        size = int(item.get("size") or 0)
        saved_name = normalize_text(item.get("saved_name")) or "unknown"
        lines.append(
            f"- name: {original_name} | type: {content_type} | size_bytes: {size} | stored_as: {saved_name}"
        )

    if not lines:
        return ""

    return "Attached files metadata:\n" + "\n".join(lines)


def make_message(role: str, content: str, model: str = DEFAULT_MODEL, uploaded_files=None):
    message = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "timestamp": now(),
        "model": model,
    }

    files = uploaded_files if isinstance(uploaded_files, list) else []
    if files:
        message["uploaded_files"] = files

    return message


def move_session_to_top(sessions, session_id: str):
    idx = None
    for i, session in enumerate(sessions):
        if session.get("session_id") == session_id:
            idx = i
            break
    if idx is None or idx == 0:
        return
    session = sessions.pop(idx)
    sessions.insert(0, session)


def ensure_default_session():
    sessions = load_sessions()
    if not sessions:
        sessions = [create_session()]
        save_sessions(sessions)


def canonicalize_for_match(text: str) -> str:
    clean = normalize_text(text).lower()
    clean = re.sub(r"[^\w\s'-]+", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def normalize_memory_kind(kind: str) -> str:
    clean = canonicalize_for_match(kind)
    if clean in MEMORY_KIND_LABELS:
        return clean
    return "memory"


def is_low_value_memory(value: str, kind: str) -> bool:
    clean = normalize_text(value)
    lowered = canonicalize_for_match(clean)

    if not clean:
        return True

    if lowered in LOW_VALUE_MEMORY_EXACT:
        return True

    if len(clean) < 2 or len(clean) > 120:
        return True

    if kind == "name" and len(clean.split()) > 5:
        return True

    if kind == "preference" and lowered.startswith(PREFERENCE_PREFIX_BLACKLIST):
        return True

    for phrase in LOW_VALUE_MEMORY_PHRASES:
        if lowered == phrase or lowered.startswith(f"{phrase} "):
            return True

    return False


def upsert_memory_item(kind: str, value: str, source: str = "auto") -> None:
    normalized_kind = normalize_memory_kind(kind)
    clean_value = normalize_text(value)

    if is_low_value_memory(clean_value, normalized_kind):
        return

    memory = load_memory()
    items = memory.get("items", [])
    normalized_value = canonicalize_for_match(clean_value)

    existing = None
    for item in items:
        item_kind = normalize_memory_kind(str(item.get("kind") or "memory"))
        item_value = canonicalize_for_match(str(item.get("value") or ""))
        if item_kind == normalized_kind and item_value == normalized_value:
            existing = item
            break

    ts = now()

    if existing:
        existing["value"] = clean_value
        existing["kind"] = normalized_kind
        existing["updated_at"] = ts
        existing["source"] = source
    else:
        items.insert(0, {
            "id": str(uuid.uuid4()),
            "kind": normalized_kind,
            "value": clean_value,
            "source": source,
            "created_at": ts,
            "updated_at": ts,
        })

    seen = set()
    deduped = []
    for item in items:
        item_kind = normalize_memory_kind(str(item.get("kind") or "memory"))
        item_value = canonicalize_for_match(str(item.get("value") or ""))
        key = (item_kind, item_value)
        if not item_value or key in seen:
            continue
        seen.add(key)
        item["kind"] = item_kind
        deduped.append(item)

    deduped.sort(key=lambda x: int(x.get("updated_at") or x.get("created_at") or 0), reverse=True)
    memory["items"] = deduped[:MAX_MEMORY_ITEMS]
    save_memory(memory)


def extract_first_match(content: str, pattern: str):
    match = re.search(pattern, content, re.IGNORECASE)
    if not match:
        return None
    value = normalize_text(match.group(1))
    return value or None


def extract_memory_from_message(text: str) -> None:
    content = normalize_text(text)
    if not content:
        return

    content_lower = content.lower()

    memory_rules = [
        ("name", r"\bmy name is\s+([A-Za-z][A-Za-z0-9' -]{0,40})\b"),
        ("goal", r"\bi want to learn\s+(.+)$"),
        ("goal", r"\bi am learning\s+(.+)$"),
        ("goal", r"\bi'm learning\s+(.+)$"),
        ("goal", r"\bi want to build\s+(.+)$"),
        ("goal", r"\bmy goal is to\s+(.+)$"),
        ("project", r"\bi am working on\s+(.+)$"),
        ("project", r"\bi'm working on\s+(.+)$"),
        ("project", r"\bmy project is\s+(.+)$"),
        ("preference", r"\bi prefer\s+(.+)$"),
        ("preference", r"\bi like\s+(.+)$"),
        ("workflow", r"\bfrom now on\s+(.+)$"),
        ("workflow", r"\bgoing forward\s+(.+)$"),
        ("skill", r"\bi am good at\s+(.+)$"),
        ("skill", r"\bi'm good at\s+(.+)$"),
    ]

    if "?" in content and not any(
        trigger in content_lower for trigger in ["my name is", "i prefer", "from now on", "going forward"]
    ):
        return

    for kind, pattern in memory_rules:
        value = extract_first_match(content, pattern)
        if value:
            upsert_memory_item(kind, value, source="auto")


def score_memory_item_for_request(item, request_text: str) -> int:
    value = canonicalize_for_match(str(item.get("value") or ""))
    kind = normalize_memory_kind(str(item.get("kind") or "memory"))
    request = canonicalize_for_match(request_text)

    if not value:
        return 0

    score = 0

    if kind == "name":
        score += 5
    elif kind in {"preference", "workflow"}:
        score += 4
    elif kind in {"goal", "project"}:
        score += 3
    else:
        score += 2

    request_words = set(request.split())
    value_words = set(value.split())
    overlap = len(request_words.intersection(value_words))
    score += overlap * 4

    if any(word in request for word in value_words if len(word) >= 4):
        score += 2

    updated_at = int(item.get("updated_at") or item.get("created_at") or 0)
    age_bonus = max(0, 3 - min(3, (now() - updated_at) // 86400))
    score += int(age_bonus)

    return score


def build_memory_prompt(user_request: str = "") -> str:
    memory = load_memory()
    items = memory.get("items", [])
    if not items:
        return ""

    ranked = sorted(
        items,
        key=lambda item: (
            score_memory_item_for_request(item, user_request),
            int(item.get("updated_at") or item.get("created_at") or 0),
        ),
        reverse=True,
    )

    selected = ranked[:MAX_MEMORY_PROMPT_ITEMS]
    grouped = {}

    for item in selected:
        kind = normalize_memory_kind(str(item.get("kind") or "memory"))
        value = normalize_text(str(item.get("value") or ""))
        if not value:
            continue
        grouped.setdefault(kind, []).append(value)

    lines = []
    for kind in MEMORY_KIND_ORDER:
        values = grouped.get(kind, [])
        if not values:
            continue
        label = MEMORY_KIND_LABELS.get(kind, kind.title())
        for value in values:
            lines.append(f"- {label}: {value}")

    if not lines:
        return ""

    return (
        "Saved user memory:\n"
        + "\n".join(lines)
        + "\nUse this only when relevant to the current request."
    )


def get_context(messages, limit: int = MAX_CONTEXT_MESSAGES):
    usable = []
    for msg in messages[-limit:]:
        role = str(msg.get("role") or "").strip().lower()
        content = str(msg.get("content") or "").strip()
        if role in {"user", "assistant", "system"} and content:
            usable.append({"role": role, "content": content})
    return usable


def build_openai_messages(session_messages, user_request: str = "", uploaded_files=None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    memory_prompt = build_memory_prompt(user_request)
    if memory_prompt:
        messages.append({"role": "system", "content": memory_prompt})

    upload_context = build_upload_context(uploaded_files)
    if upload_context:
        messages.append({
            "role": "system",
            "content": upload_context + "\nThe files are uploaded locally. Use only this metadata unless the user provides file contents."
        })

    messages.extend(get_context(session_messages))
    return messages


def strip_copy_suffix(title: str) -> str:
    clean = normalize_text(title) or "New Chat"
    clean = re.sub(r"\s+\(copy(?:\s+\d+)?\)$", "", clean, flags=re.IGNORECASE).strip()
    return clean or "New Chat"


def make_duplicate_title(existing_titles, base_title: str) -> str:
    root_title = strip_copy_suffix(base_title)[:80].strip()
    normalized_titles = {normalize_text(title) for title in existing_titles}

    candidate = f"{root_title} (Copy)"
    if candidate not in normalized_titles:
        return candidate

    n = 2
    while True:
        candidate = f"{root_title} (Copy {n})"
        if candidate not in normalized_titles:
            return candidate
        n += 1


def duplicate_session_data(source_session, existing_titles):
    ts = now()
    cloned = copy.deepcopy(source_session)
    cloned["session_id"] = str(uuid.uuid4())
    cloned["created_at"] = ts
    cloned["updated_at"] = ts
    cloned["title"] = make_duplicate_title(existing_titles, source_session.get("title") or "New Chat")

    messages = cloned.get("messages", [])
    if not isinstance(messages, list):
        messages = []

    remapped_messages = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        msg_copy = dict(msg)
        msg_copy["id"] = str(uuid.uuid4())
        remapped_messages.append(msg_copy)

    cloned["messages"] = remapped_messages
    cloned["message_count"] = len(remapped_messages)
    return cloned


def make_safe_upload_name(original_name: str) -> str:
    safe_name = secure_filename(original_name or "")
    if not safe_name:
        safe_name = "file"
    prefix = uuid.uuid4().hex
    return f"{prefix}_{safe_name}"


def save_uploaded_file(file_storage):
    original_name = normalize_text(getattr(file_storage, "filename", ""))
    if not original_name:
        raise ValueError("One of the uploaded files is missing a filename.")

    saved_name = make_safe_upload_name(original_name)
    destination = UPLOADS_DIR / saved_name
    file_storage.save(destination)

    size = destination.stat().st_size if destination.exists() else 0
    if size > MAX_UPLOAD_SIZE_BYTES:
        try:
            destination.unlink(missing_ok=True)
        except Exception:
            pass
        raise ValueError(f"File '{original_name}' exceeds the {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB limit.")

    return {
        "id": str(uuid.uuid4()),
        "original_name": original_name,
        "saved_name": saved_name,
        "content_type": normalize_text(getattr(file_storage, "mimetype", "")) or "application/octet-stream",
        "size": size,
        "uploaded_at": now(),
        "url": f"/uploads/{saved_name}",
    }


ensure_default_session()


@app.route("/")
def index():
    return send_from_directory(TEMPLATES_DIR, "index.html")


@app.route("/uploads/<path:filename>", methods=["GET"])
def uploaded_file(filename):
    return send_from_directory(UPLOADS_DIR, filename, as_attachment=False)


@app.route("/api/models", methods=["GET"])
def api_models():
    return jsonify({
        "models": [
            DEFAULT_MODEL,
            "gpt-4.1-mini",
            "gpt-4.1",
            "gpt-4o-mini",
        ],
        "default": DEFAULT_MODEL,
    })


@app.route("/api/state", methods=["GET"])
def api_state():
    sessions = load_sessions()
    return jsonify({"sessions": summarize_sessions(sessions)})


@app.route("/api/chat/<session_id>", methods=["GET"])
def api_get_chat(session_id):
    sessions = load_sessions()
    session = get_session(sessions, session_id)
    if not session:
        return jsonify({"detail": "Session not found"}), 404

    session["message_count"] = len(session.get("messages", []))
    return jsonify(session)


@app.route("/api/memory", methods=["GET"])
def api_memory():
    return jsonify(load_memory())


@app.route("/api/memory/add", methods=["POST"])
def api_memory_add():
    data = request.get_json(silent=True) or {}
    kind = normalize_memory_kind(str(data.get("kind") or "memory"))
    value = normalize_text(data.get("value"))

    if not value:
        return jsonify({"detail": "Value is required"}), 400

    if is_low_value_memory(value, kind):
        return jsonify({"detail": "Memory value is too short, vague, or low quality"}), 400

    upsert_memory_item(kind[:40], value[:120], source="manual")
    return jsonify({"ok": True, "memory": load_memory()})


@app.route("/api/memory/delete", methods=["POST"])
def api_memory_delete():
    data = request.get_json(silent=True) or {}
    memory_id = normalize_text(data.get("id"))
    if not memory_id:
        return jsonify({"detail": "id is required"}), 400

    memory = load_memory()
    before = len(memory["items"])
    memory["items"] = [item for item in memory["items"] if str(item.get("id")) != memory_id]

    if len(memory["items"]) == before:
        return jsonify({"detail": "Memory item not found"}), 404

    save_memory(memory)
    return jsonify({"ok": True, "memory": memory})


@app.route("/api/session/new", methods=["POST"])
def api_session_new():
    sessions = load_sessions()
    session = create_session()
    sessions.insert(0, session)
    save_sessions(sessions)
    return jsonify({"session_id": session["session_id"]})


@app.route("/api/session/duplicate", methods=["POST"])
def api_session_duplicate():
    data = request.get_json(silent=True) or {}
    session_id = normalize_text(data.get("session_id"))

    if not session_id:
        return jsonify({"detail": "session_id is required"}), 400

    sessions = load_sessions()
    source_session = get_session(sessions, session_id)
    if not source_session:
        return jsonify({"detail": "Session not found"}), 404

    existing_titles = {
        normalize_text(str(session.get("title") or "New Chat"))
        for session in sessions
    }

    duplicated = duplicate_session_data(source_session, existing_titles)
    sessions.insert(0, duplicated)
    save_sessions(sessions)

    return jsonify({
        "ok": True,
        "session": {
            "session_id": duplicated["session_id"],
            "title": duplicated["title"],
            "message_count": duplicated["message_count"],
            "updated_at": duplicated["updated_at"],
        },
        "sessions": summarize_sessions(sessions),
    })


@app.route("/api/session/delete", methods=["POST"])
def api_session_delete():
    data = request.get_json(silent=True) or {}
    session_id = normalize_text(data.get("session_id"))
    if not session_id:
        return jsonify({"detail": "session_id is required"}), 400

    sessions = load_sessions()
    new_sessions = [s for s in sessions if s.get("session_id") != session_id]

    if len(new_sessions) == len(sessions):
        return jsonify({"detail": "Session not found"}), 404

    if not new_sessions:
        new_sessions = [create_session()]

    save_sessions(new_sessions)
    return jsonify({"ok": True})


@app.route("/api/session/rename", methods=["POST"])
def api_session_rename():
    data = request.get_json(silent=True) or {}
    session_id = normalize_text(data.get("session_id"))
    title = normalize_text(data.get("title"))

    if not session_id:
        return jsonify({"detail": "session_id is required"}), 400
    if not title:
        return jsonify({"detail": "Title cannot be empty"}), 400

    sessions = load_sessions()
    session = get_session(sessions, session_id)
    if not session:
        return jsonify({"detail": "Session not found"}), 404

    session["title"] = title[:80]
    session["updated_at"] = now()
    move_session_to_top(sessions, session_id)
    save_sessions(sessions)

    return jsonify({"ok": True})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"detail": "No files were uploaded"}), 400

    if len(files) > MAX_UPLOAD_FILES:
        return jsonify({"detail": f"Too many files. Max is {MAX_UPLOAD_FILES}"}), 400

    uploaded = []
    try:
        for file_storage in files:
            uploaded.append(save_uploaded_file(file_storage))
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": f"Upload failed: {e}"}), 500

    return jsonify({
        "ok": True,
        "files": uploaded,
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    session_id = normalize_text(data.get("session_id"))
    content = normalize_text(data.get("content"))
    model = normalize_text(data.get("model")) or DEFAULT_MODEL
    uploaded_files = data.get("uploaded_files") if isinstance(data.get("uploaded_files"), list) else []

    if not content:
        return jsonify({"detail": "Content cannot be empty"}), 400

    if not OPENAI_API_KEY or client is None:
        return jsonify({"detail": "Missing OPENAI_API_KEY"}), 500

    sessions = load_sessions()
    session = get_session(sessions, session_id) if session_id else None

    if not session:
        session = create_session()
        sessions.insert(0, session)

    user_msg = make_message("user", content, model, uploaded_files=uploaded_files)
    session["messages"].append(user_msg)
    session["message_count"] = len(session["messages"])
    session["updated_at"] = now()

    extract_memory_from_message(content)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=build_openai_messages(
                session["messages"],
                user_request=content,
                uploaded_files=uploaded_files,
            ),
            temperature=0.7,
        )
        assistant_text = str(response.choices[0].message.content or "").strip() or "No response returned."
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

    assistant_msg = make_message("assistant", assistant_text, model)

    session["messages"].append(assistant_msg)
    session["message_count"] = len(session["messages"])
    session["updated_at"] = now()

    if session["message_count"] == 2:
        session["title"] = generate_title(content)

    move_session_to_top(sessions, session["session_id"])
    save_sessions(sessions)

    return jsonify({
        "session_id": session["session_id"],
        "title": session["title"],
        "message_count": session["message_count"],
        "message": assistant_msg,
        "messages": session["messages"],
    })


@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    data = request.get_json(silent=True) or {}
    session_id = normalize_text(data.get("session_id"))
    content = normalize_text(data.get("content"))
    model = normalize_text(data.get("model")) or DEFAULT_MODEL
    uploaded_files = data.get("uploaded_files") if isinstance(data.get("uploaded_files"), list) else []

    if not content:
        return jsonify({"detail": "Content cannot be empty"}), 400

    if not OPENAI_API_KEY or client is None:
        return jsonify({"detail": "Missing OPENAI_API_KEY"}), 500

    sessions = load_sessions()
    session = get_session(sessions, session_id) if session_id else None

    if not session:
        session = create_session()
        sessions.insert(0, session)

    user_msg = make_message("user", content, model, uploaded_files=uploaded_files)
    session["messages"].append(user_msg)
    session["message_count"] = len(session["messages"])
    session["updated_at"] = now()

    extract_memory_from_message(content)

    openai_messages = build_openai_messages(
        session["messages"],
        user_request=content,
        uploaded_files=uploaded_files,
    )

    if session["message_count"] == 1:
        session["title"] = generate_title(content)

    def event_stream():
        assistant_text = ""

        try:
            start_payload = {
                "title": session["title"],
                "model_used": model,
                "session_id": session["session_id"],
            }
            yield f"event: start\ndata: {json.dumps(start_payload, ensure_ascii=False)}\n\n"

            stream = client.chat.completions.create(
                model=model,
                messages=openai_messages,
                stream=True,
                temperature=0.7,
            )

            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    assistant_text += delta
                    yield f"event: delta\ndata: {json.dumps({'text': delta, 'model_used': model}, ensure_ascii=False)}\n\n"

            assistant_msg = make_message(
                "assistant",
                assistant_text.strip() or "No response returned.",
                model,
            )

            session["messages"].append(assistant_msg)
            session["message_count"] = len(session["messages"])
            session["updated_at"] = now()

            if session["message_count"] == 2:
                session["title"] = generate_title(content)

            move_session_to_top(sessions, session["session_id"])
            save_sessions(sessions)

            done_payload = {
                "message": assistant_msg,
                "session_id": session["session_id"],
                "title": session["title"],
            }
            yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# ADD THIS NEAR YOUR OTHER ROUTES (BOTTOM OF FILE)

@app.route("/blog")
def blog_index():
    return send_from_directory(TEMPLATES_DIR, "blog.html")


@app.route("/blog/<slug>")
def blog_post(slug):
    filename = f"blog_{slug}.html"
    file_path = TEMPLATES_DIR / filename

    if not file_path.exists():
        return "Post not found", 404

    return send_from_directory(TEMPLATES_DIR, filename)

if __name__ == "__main__":
    host = (os.getenv("APP_HOST") or "127.0.0.1").strip()
    port = int((os.getenv("PORT") or os.getenv("APP_PORT") or "8743").strip())
    debug = (os.getenv("DEBUG") or "true").strip().lower() == "true"
    app.run(host=host, port=port, debug=debug)