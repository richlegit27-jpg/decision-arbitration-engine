from __future__ import annotations

import os
import re
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from bs4 import BeautifulSoup
import uuid
from werkzeug.utils import secure_filename
from nova_backend.routes.memory_panel_routes import register_memory_panel_routes
from nova_backend.utils.api_response import ok_response, error_response
from nova_backend.utils.request_utils import get_json_body, get_str, get_list, normalize_attachments
from nova_backend.utils.route_guard import guarded_json_route
from nova_backend.config import (
    BASE_DIR,
    DATA_DIR,
    UPLOADS_DIR,
    SESSIONS_FILE,
    ARTIFACTS_FILE,
    MEMORY_FILE,
    WEB_TIMEOUT,
    RECON_TIMEOUT,
)

from nova_backend.services.session_service import SessionService
from nova_backend.services.artifact_service import ArtifactService
from nova_backend.services.memory_service import MemoryService
from nova_backend.services.web_service import WebService
from nova_backend.services.recon_service import ReconService
from nova_backend.services.intent_router_service import IntentRouterService
from nova_backend.utils.file_utils import ensure_dir
from nova_backend.services.chat_service import ChatService


# -----------------------
# APP SETUP
# -----------------------

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
CORS(app)

ensure_dir(DATA_DIR)
ensure_dir(UPLOADS_DIR)

app.config["UPLOAD_FOLDER"] = str(UPLOADS_DIR)

# -----------------------
# SERVICES
# -----------------------

session_service = SessionService(SESSIONS_FILE)
session_service = SessionService(str(SESSIONS_FILE))
artifact_service = ArtifactService(str(ARTIFACTS_FILE))
memory_service = MemoryService(str(MEMORY_FILE))
web_service = WebService(timeout=WEB_TIMEOUT)
recon_service = ReconService(timeout=RECON_TIMEOUT)
intent_router = IntentRouterService()

chat_service = ChatService(
    session_service=session_service,
    memory_service=memory_service,
    artifact_service=artifact_service,
    web_service=web_service,
    recon_service=recon_service,
)

print("CHAT SERVICE OBJ =", chat_service)
print("CHAT SERVICE TYPE =", type(chat_service))
print("CHAT SERVICE MODULE =", type(chat_service).__module__)
print("CHAT SERVICE HAS HANDLE =", hasattr(chat_service, "handle"))
print("CHAT SERVICE DIR HAS HANDLE =", "handle" in dir(chat_service))

# -----------------------
# HELPERS
# -----------------------

IDENTITY_QUESTION_PATTERNS = [
    re.compile(r"\bwhat(?:'s| is)\s+my\s+name\b", re.IGNORECASE),
    re.compile(r"\bdo\s+you\s+know\s+my\s+name\b", re.IGNORECASE),
    re.compile(r"\bwho\s+am\s+i\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+do\s+you\s+know\s+about\s+me\b", re.IGNORECASE),
]

NAME_MEMORY_PATTERNS = [
    re.compile(r"^\s*user\s+name\s+is\s+(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*name\s*:\s*(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*my\s+name\s+is\s+(.+?)\s*$", re.IGNORECASE),
]


def json_ok(**kwargs):
    payload = {"ok": True}
    payload.update(kwargs)
    return jsonify(payload)


def json_error(message: str, status: int = 400, **kwargs):
    payload = {"ok": False, "error": str(message)}
    payload.update(kwargs)
    return jsonify(payload), status

def request_json() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def build_common_state_payload(session_id: str = "") -> dict:
    session = None
    if session_id:
        session = session_service.get_session(session_id)
    if not session:
        session = session_service.get_active()

    return {
        "session": session,
        "sessions": session_service.get_all(),
        "active_session_id": session_service.active_session_id,
        "artifacts": artifact_service.build_list_payload(),
        "memory": memory_service.build_list_payload(),
    }


def _clean_fact_value(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    raw = re.sub(r"\s+", " ", raw)
    return raw[:1].upper() + raw[1:]


def extract_memory_fact(user_text: str) -> dict | None:
    text = str(user_text or "").strip()
    if not text:
        return None

    patterns = [
        (
            re.compile(r"\bmy name is\s+([A-Za-z][A-Za-z0-9_\-']{0,40})\b", re.IGNORECASE),
            "profile",
            ["identity", "name"],
            5.0,
            lambda m: f"User name is {_clean_fact_value(m.group(1))}",
        ),
        (
            re.compile(r"\bi am\s+([A-Za-z][A-Za-z0-9_\-']{0,40})\b", re.IGNORECASE),
            "profile",
            ["identity"],
            3.5,
            lambda m: f"User says they are {_clean_fact_value(m.group(1))}",
        ),
        (
            re.compile(r"\bi prefer\s+(.+)$", re.IGNORECASE),
            "preference",
            ["preference"],
            2.5,
            lambda m: f"User preference: {m.group(1).strip()}",
        ),
        (
            re.compile(r"\bremember that\s+(.+)$", re.IGNORECASE),
            "note",
            ["memory"],
            2.0,
            lambda m: m.group(1).strip(),
        ),
    ]

    for pattern, kind, tags, weight, builder in patterns:
        match = pattern.search(text)
        if not match:
            continue

        fact_text = str(builder(match) or "").strip()
        if not fact_text:
            continue

        return {
            "text": fact_text,
            "kind": kind,
            "tags": tags,
            "weight": float(weight),
        }

    return None


def memory_exists_for_session(session_id: str, fact_text: str) -> bool:
    target_session = str(session_id or "").strip()
    target_text = str(fact_text or "").strip().lower()
    if not target_text:
        return False

    try:
        for item in memory_service.all():
            item_text = str(item.get("text") or "").strip().lower()
            item_session = str(item.get("session_id") or "").strip()
            if item_text == target_text and item_session == target_session:
                return True
    except Exception:
        return False

    return False

    if not decision.get("save_memory"):
        return None

    fact = extract_memory_fact(user_text)
    if not fact:
        return None

    fact_text = str(fact["text"] or "").strip()

    # phase 2 dominance:
    # if this is a name memory, wipe competing same-session name memories
    if extract_name_from_memory_text(fact_text):
        cleanup_competing_name_memories(session_id=session_id, winning_text=fact_text)

    if memory_exists_for_session(session_id, fact_text):
        return {
            "status": "duplicate_skipped",
            "fact": fact,
        }

    item = memory_service.add_memory(
        text=fact_text,
        kind=fact["kind"],
        source="router_auto",
        session_id=session_id,
    )

    try:
        if isinstance(item, dict):
            item["tags"] = fact.get("tags") or item.get("tags") or []
            item["weight"] = fact.get("weight", item.get("weight", 1.0))
    except Exception:
        pass

    return {
        "status": "saved",
        "fact": fact,
        "item": item,
    }

    text = str(user_text or "").strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in IDENTITY_QUESTION_PATTERNS)


def extract_name_from_memory_text(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""

    for pattern in NAME_MEMORY_PATTERNS:
        match = pattern.search(raw)
        if match:
            name = str(match.group(1) or "").strip()
            name = re.sub(r"[^\w\s'\-]", "", name).strip()
            if name:
                return _clean_fact_value(name)

    return ""


def find_best_name_memory(session_id: str) -> dict | None:
    target_session = str(session_id or "").strip()
    all_memory = memory_service.all() or []
    candidates = []

    for item in all_memory:
        if not isinstance(item, dict):
            continue

        item_text = str(item.get("text") or "").strip()
        if not item_text:
            continue

        name = extract_name_from_memory_text(item_text)
        if not name:
            continue

        item_session = str(item.get("session_id") or "").strip()
        item_kind = str(item.get("kind") or "").strip().lower()
        item_source = str(item.get("source") or "").strip().lower()
        item_updated = str(item.get("updated_at") or item.get("created_at") or "")
        weight = float(item.get("weight", 1.0) or 1.0)

        score = 0.0
        if item_session and item_session == target_session:
            score += 100.0
        elif not item_session:
            score += 20.0

        if item_kind == "profile":
            score += 25.0

        if item_source in {"router_auto", "manual", "assistant"}:
            score += 5.0

        if item_text.lower().startswith("user name is"):
            score += 15.0
        elif item_text.lower().startswith("name:"):
            score += 10.0
        elif item_text.lower().startswith("my name is"):
            score += 5.0

        score += weight

        candidates.append(
            {
                "score": score,
                "updated_at": item_updated,
                "name": name,
                "item": item,
            }
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda c: (
            float(c.get("score", 0.0)),
            str(c.get("updated_at") or ""),
        ),
        reverse=True,
    )
    return candidates[0]


    match = find_best_name_memory(session_id=session_id)

    payload = build_common_state_payload(session_id=session_id)

    if match:
        name = match["name"]
        item = match["item"]

        payload.update(
            {
                "assistant_message": {
                    "role": "assistant",
                },
                "debug": {
                    "decision": decision,
                },
            }
        )
        return json_ok(**payload)

    payload.update(
        {
            "assistant_message": {
                "role": "assistant",
                "text": "I don’t know your name yet. Tell me with “my name is …” and I’ll remember it.",
            },
            "debug": {
                "decision": decision,
            },
        },
    )
    return json_ok(**payload)

# ==============================
# ==============================

IDENTITY_QUESTION_PATTERNS = [
    re.compile(r"\bwhat(?:'s| is)\s+my\s+name\b", re.IGNORECASE),
    re.compile(r"\bdo\s+you\s+know\s+my\s+name\b", re.IGNORECASE),
    re.compile(r"\bwho\s+am\s+i\b", re.IGNORECASE),
]

NAME_VALUE_PATTERNS = [
    re.compile(r"^\s*user\s+name\s+is\s+(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*name\s*:\s*(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*my\s+name\s+is\s+(.+?)\s*$", re.IGNORECASE),
]


def _clean_memory_value(value: str) -> str:
    value = str(value or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _normalize_name(value: str) -> str:
    value = _clean_memory_value(value)
    value = re.sub(r"[^\w\s'\-]", "", value).strip()
    if not value:
        return ""
    return value[:1].upper() + value[1:]


    raw = str(text or "").strip()
    if not raw:
        return False
    return any(p.search(raw) for p in IDENTITY_QUESTION_PATTERNS)


def extract_name_from_memory_text(text: str) -> str:
    raw = _clean_memory_value(text)
    if not raw:
        return ""

    for pattern in NAME_VALUE_PATTERNS:
        match = pattern.search(raw)
        if match:
            return _normalize_name(match.group(1))

    return ""


def is_name_memory_item(item: dict) -> bool:
    if not isinstance(item, dict):
        return False
    return bool(extract_name_from_memory_text(item.get("text", "")))


def get_memory_items():
    try:
        items = memory_service.all()
        return items if isinstance(items, list) else []
    except Exception:
        return []


def delete_memory_item(memory_id: str) -> bool:
    if not memory_id:
        return False

    for method_name in ("delete_memory", "delete", "remove"):
        method = getattr(memory_service, method_name, None)
        if callable(method):
            try:
                return bool(method(memory_id))
            except Exception:
                return False
    return False


def score_name_memory(item: dict, session_id: str) -> float:
    if not isinstance(item, dict):
        return -9999.0

    score = 0.0
    item_text = str(item.get("text") or "").strip()
    item_session = str(item.get("session_id") or "").strip()
    item_kind = str(item.get("kind") or "").strip().lower()
    item_source = str(item.get("source") or "").strip().lower()
    item_updated = str(item.get("updated_at") or item.get("created_at") or "")

    if not extract_name_from_memory_text(item_text):
        return -9999.0

    if item_session and item_session == str(session_id or "").strip():
        score += 100.0
    elif not item_session:
        score += 15.0

    if item_kind == "profile":
        score += 20.0

    if item_source in {"router_auto", "assistant", "manual", "user"}:
        score += 5.0

    lowered = item_text.lower()
    if lowered.startswith("user name is"):
        score += 15.0
    elif lowered.startswith("name:"):
        score += 10.0
    elif lowered.startswith("my name is"):
        score += 5.0

    if item_updated:
        score += 1.0

    return score


def find_best_name_memory(session_id: str) -> dict | None:
    items = get_memory_items()
    candidates = []

    for item in items:
        score = score_name_memory(item, session_id)
        if score <= -9999.0:
            continue

        candidates.append({
            "item": item,
            "score": score,
            "updated_at": str(item.get("updated_at") or item.get("created_at") or ""),
            "name": extract_name_from_memory_text(item.get("text", "")),
        })

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (x["score"], x["updated_at"]),
        reverse=True,
    )
    return candidates[0]


def cleanup_competing_name_memories(session_id: str, winning_text: str):
    target_session = str(session_id or "").strip()
    winning_text = str(winning_text or "").strip().lower()
    if not winning_text:
        return

    for item in get_memory_items():
        if not isinstance(item, dict):
            continue

        item_id = str(item.get("id") or "").strip()
        item_session = str(item.get("session_id") or "").strip()
        item_text = str(item.get("text") or "").strip().lower()

        if not item_id:
            continue
        if item_session != target_session:
            continue
        if not is_name_memory_item(item):
            continue
        if item_text == winning_text:
            continue

        delete_memory_item(item_id)
# -----------------------
# PAGE ROUTES
# -----------------------

@app.get("/")
def index():
    return render_template("index.html")


# -----------------------
# HEALTH
# -----------------------

@app.get("/api/health")
def api_health():
    return json_ok(
        status="ready",
        app="nova",
        cwd=os.getcwd(),
        base_dir=str(BASE_DIR),
        uploads_dir=str(UPLOADS_DIR),
        sessions_file=str(SESSIONS_FILE),
        artifacts_file=str(ARTIFACTS_FILE),
        memory_file=str(MEMORY_FILE),
        route_build="backend-memory-recall-fix-phase-1-001",
    )


# -----------------------
# STATE
# -----------------------

@app.get("/api/state")
def api_state():
    return json_ok(
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
        session=session_service.get_active(),
        artifacts=artifact_service.build_list_payload(),
        memory=memory_service.build_list_payload(),
    )


# -----------------------
# CHAT
# -----------------------
@app.post("/api/chat")
def api_chat():
    data = request_json()

    user_text = str(data.get("user_text") or "").strip()
    session_id = str(data.get("session_id") or "").strip()
    attachments = normalize_attachments(data.get("attachments"))

    if not session_id:
        active = session_service.get_active()
        if active:
            session_id = str(active.get("id") or "").strip()

    if not session_id:
        created = session_service.create("New Chat")
        session_id = created["id"]

    if not user_text and not attachments:
        return json_error("Missing user_text or attachments", 400)

    decision = intent_router.decide(
        user_text=user_text,
        attachments=attachments,
    )

    lowered = user_text.lower()

    # 🔒 HARD ROUTE LOCK (stability first)
    if any(x in lowered for x in [
        "weather", "forecast", "temperature", "rain", "snow", "wind", "humidity"
    ]):
        decision["route"] = "web_search"

    elif any(x in lowered for x in [
        "hours", "open now", "closing time", "address",
        "phone number", "location", "directions", "near me"
    ]):
        decision["route"] = "web_search"

    elif any(x in lowered for x in [
        "price", "btc", "bitcoin", "crypto", "market cap"
    ]):
        decision["route"] = "web_search"

    elif any(x in lowered for x in [
        "latest", "news", "current", "update", "who is", "what is", "tell me about"
    ]):
        decision["route"] = "web_search"

    # FORCE WEB SEARCH FOR COMMON QUERIES
    if any(x in lowered for x in [
        "news",
        "latest",
        "price",
        "who is",
        "what is",
        "tell me about",
        "current",
        "update",
        "weather",
        "forecast",
        "temperature",
        "rain",
        "snow",
        "wind",
        "humidity",
        "hours",
        "open now",
        "closing time",
        "address",
        "phone number",
        "location",
        "directions",
        "near me",
    ]):
        decision["route"] = "web_search"

    has_url = (
        "http://" in lowered
        or "https://" in lowered
        or bool(re.search(r"\bwww\.[^\s]+\.[^\s]+\b", lowered))
    )

    looks_like_web_search = (
        lowered.startswith("search ")
        or lowered.startswith("look up ")
        or lowered.startswith("lookup ")
        or lowered.startswith("find ")
        or lowered.startswith("latest ")
        or lowered.startswith("news ")
        or lowered.startswith("current ")
        or lowered.startswith("today ")
        or " latest " in lowered
        or " news " in lowered
        or " current " in lowered
        or " today " in lowered
    )

    if has_url:
        if "url" not in decision or not str(decision.get("url") or "").strip():
            m = re.search(r"(https?://[^\s]+)", user_text, re.IGNORECASE)
            if m:
                decision["url"] = m.group(1).strip()
            else:
                m = re.search(r"\b(www\.[^\s]+\.[^\s]+)\b", user_text, re.IGNORECASE)
                if m:
                    decision["url"] = "https://" + m.group(1).strip()

        decision["route"] = "web"

    elif looks_like_web_search:
        decision["route"] = "web_search"

    try:
        # identity recall
        if any(p.search(user_text) for p in IDENTITY_QUESTION_PATTERNS):
            best = find_best_name_memory(session_id)
            payload = build_common_state_payload(session_id=session_id)

            if best:
                payload["assistant_message"] = {
                    "role": "assistant",
                    "text": f"Your name is {best['name']}.",
                }
            else:
                payload["assistant_message"] = {
                    "role": "assistant",
                    "text": "I don’t know your name yet.",
                }

            payload["debug"] = {
                "decision": decision,
                "route_taken": "identity",
            }
            return json_ok(**payload)

        # web route
        # web search route
        if decision.get("route") == "web_search":
            query = user_text.strip()
            result = web_service.search(query)

            if not isinstance(result, dict):
                return json_error("Invalid web result", 500)
            if not result.get("ok"):
                payload = build_common_state_payload(session_id=session_id)
                payload.update(
                    {
                        "assistant_message": {
                            "role": "assistant",
                            "text": str(
                                result.get("summary")
                                or f'Web search failed for "{query}".'
                            ),
                        },
                        "web_result": result,
                        "debug": {
                            "decision": decision,
                            "route_taken": "web_search_soft_fail",
                        },
                    }
                )
                return json_ok(**payload)
            artifact_payload = web_service.build_search_artifact_payload(result)
            payload = build_common_state_payload(session_id=session_id)
            payload.update(
                {
                    "assistant_message": {
                        "role": "assistant",
                        "text": str(
                            result.get("summary")
                            or f'Web search completed for "{query}".'
                        ).strip(),
                    },
                    "saved_artifact": artifact_payload,
                    "web_result": result,
                    "debug": {
                        "decision": decision,
                        "route_taken": "web_search",
                    },
                }
            )
            return json_ok(**payload)
        # web route
        if decision.get("route") == "web":
            url = str(decision.get("url") or "").strip()
            if not url:
                return json_error("URL could not be determined", 400)

            result = web_service.fetch(url)

        # recon route
        if decision.get("route") == "recon":
            url = str(decision.get("url") or "").strip()
            if not url:
                return json_error("Recon route selected but no URL was found", 400)

            result = recon_service.analyze_target(url)

            if not result.get("ok"):
                return json_error(result.get("error") or "Recon failed", 500)

            artifact_payload = recon_service.build_artifact_payload(result)

            payload = build_common_state_payload(session_id=session_id)
            payload.update(
                {
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            result.get("summary")
                            or result.get("preview")
                            or f"Recon complete for {url}"
                        ),
                    },
                    "saved_artifact": artifact_payload,
                    "recon_result": result,
                    "debug": {
                        "decision": decision,
                        "route_taken": "recon",
                    },
                }
            )
            return json_ok(**payload)

        # default chat
        result = chat_service.handle(
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
        )

        if not isinstance(result, dict):
            result = {
                "assistant_message": {
                    "role": "assistant",
                    "text": str(result),
                }
            }

        # persist artifact with readable text for UI
        saved_artifact = result.get("saved_artifact")
        if isinstance(saved_artifact, dict):
            try:
                artifact_payload = dict(saved_artifact)

                text = (
                    artifact_payload.get("text")
                    or artifact_payload.get("body")
                    or artifact_payload.get("analysis_text")
                    or ((artifact_payload.get("viewer") or {}).get("body"))
                    or ((result.get("assistant_message") or {}).get("text"))
                    or "Generated artifact"
                )

                artifact_payload["body"] = text
                artifact_payload["preview"] = text[:140]

                viewer = artifact_payload.get("viewer")
                if not isinstance(viewer, dict):
                    viewer = {}
                viewer["body"] = text
                artifact_payload["viewer"] = viewer

                artifact_payload["kind"] = artifact_payload.get("kind", "chat")
                artifact_payload["title"] = artifact_payload.get("title", "Generated Artifact")
                artifact_payload["session_id"] = session_id

                artifact_service.save_artifact(artifact_payload)

            except Exception as e:
                result.setdefault("debug", {})
                result["debug"]["artifact_persist_error"] = str(e)

        existing_debug = result.get("debug") if isinstance(result.get("debug"), dict) else {}
        saved_artifact = result.get("saved_artifact")

        session_payload = result.get("session")
        if not isinstance(session_payload, dict):
            session_payload = session_service.get_session(session_id) or {}

        session_messages = session_payload.get("messages") if isinstance(session_payload.get("messages"), list) else []

        final_text = ""
        for msg in reversed(session_messages):
            if not isinstance(msg, dict):
                continue
            if str(msg.get("role") or "").strip().lower() != "assistant":
                continue

            candidate = str(msg.get("text") or "").strip()
            if candidate and candidate.lower() != "none":
                final_text = candidate
                break

        if not final_text:
            final_text = "I'm here. Tell me what you need."

        assistant_message = {
            "role": "assistant",
            "text": final_text,
        }

        # ATTACH IMAGE TO CHAT MESSAGE
        if isinstance(assistant_message, dict) and isinstance(saved_artifact, dict):
            image_url = (
                saved_artifact.get("image_url")
                or ((saved_artifact.get("viewer") or {}).get("image_url"))
                or ((saved_artifact.get("meta") or {}).get("image_url"))
                or ""
            )

            if image_url:
                assistant_message = dict(assistant_message)
                assistant_message["image_url"] = image_url

                meta = assistant_message.get("meta")
                if not isinstance(meta, dict):
                    meta = {}
                meta["image_url"] = image_url
                assistant_message["meta"] = meta

        payload = {
            "assistant_message": assistant_message,
            "session": result.get("session") or session_service.get_session(session_id),
            "sessions": result.get("sessions") or session_service.get_all(),
            "active_session_id": result.get("active_session_id") or session_service.active_session_id,
            "artifacts": result.get("artifacts") or artifact_service.build_list_payload(),
            "memory": result.get("memory") or memory_service.build_list_payload(),
            "saved_artifact": saved_artifact,
            "debug": {
                **existing_debug,
                "decision": decision,
                "route_taken": "chat",
            },
        }

        payload = {k: v for k, v in payload.items() if v is not None}
        return json_ok(**payload)

    except Exception as exc:
        return json_error(
            str(exc),
            500,
            debug={"decision": decision},
        )

@app.get("/api/sessions")
def api_sessions():
    return json_ok(
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
        session=session_service.get_active(),
    )


@app.get("/api/sessions/<session_id>")
def api_session_by_id(session_id: str):
    session = session_service.get_session(session_id)
    if not session:
        return json_error("Session not found", 404)

    return json_ok(
        session=session,
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/new")
def api_sessions_new():
    data = request_json()
    title = str(data.get("title") or "New Chat").strip() or "New Chat"

    session = session_service.create_session(title)
    if not session:
        return json_error("Failed to create session", 500)

    return json_ok(
        session=session_service.get_session(session["id"]),
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/switch")
def api_sessions_switch():
    data = request_json()
    session_id = str(data.get("session_id") or "").strip()

    if not session_id:
        return json_error("Missing session_id", 400)

    session = session_service.set_active(session_id)
    if not session:
        return json_error("Session not found", 404)

    return json_ok(
        session=session_service.get_session(session_id),
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/rename")
def api_sessions_rename():
    data = request_json()
    session_id = str(data.get("session_id") or "").strip()
    title = str(data.get("title") or "").strip()

    if not session_id:
        return json_error("Missing session_id", 400)

    session = session_service.rename(session_id, title or "New Chat")
    if not session:
        return json_error("Session not found", 404)

    return json_ok(
        session=session_service.get_session(session_id),
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/pin")
def api_sessions_pin():
    data = request_json()
    session_id = str(data.get("session_id") or "").strip()
    pinned = bool(data.get("pinned"))

    if not session_id:
        return json_error("Missing session_id", 400)

    session = session_service.pin(session_id, pinned)
    if not session:
        return json_error("Session not found", 404)

    return json_ok(
        session=session_service.get_session(session_id),
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/delete")
def api_sessions_delete():
    data = request_json()
    session_id = str(data.get("session_id") or "").strip()

    if not session_id:
        return json_error("Missing session_id", 400)

    if not session_service.delete(session_id):
        return json_error("Session not found", 404)

    active_id = session_service.active_session_id
    active_session = session_service.get_active()

    return json_ok(
        session=active_session,
        sessions=session_service.get_all(),
        active_session_id=active_id,
    )

# -----------------------
# ARTIFACTS
# -----------------------

@app.get("/api/artifacts")
def api_artifacts():
    return json_ok(
        artifacts=artifact_service.build_list_payload(),
    )


@app.get("/api/artifacts/<artifact_id>")
def api_artifact_view(artifact_id: str):
    payload = artifact_service.build_view_payload(artifact_id)
    if not payload:
        return json_error("Artifact not found", 404)

    return json_ok(
        artifact=payload,
    )


# -----------------------
# MEMORY
# -----------------------

@app.get("/api/memory")
@guarded_json_route
def api_memory():
    memory = memory_service.all()
    return ok_response(
        data={
            "memory": memory,
            "count": len(memory),
        },
        message="Memory loaded.",
    )


@app.post("/api/memory/add")
@guarded_json_route
def api_memory_add():
    data = get_json_body(request)

    text = get_str(data, "text")
    kind = get_str(data, "kind", "note") or "note"
    source = get_str(data, "source", "manual") or "manual"
    session_id = get_str(data, "session_id")

    if not text:
        return error_response(
            error="text is required.",
            code="missing_text",
        ), 400

    item = memory_service.add_memory(
        text=text,
        kind=kind,
        source=source,
        session_id=session_id,
    )

    memory = memory_service.all()

    return ok_response(
        data={
            "item": item,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory added.",
    )


@app.post("/api/memory/delete")
@guarded_json_route
def api_memory_delete():
    data = get_json_body(request)
    memory_id = get_str(data, "id") or get_str(data, "memory_id")

    if not memory_id:
        return error_response(
            error="id is required.",
            code="missing_id",
        ), 400

    deleted = memory_service.delete_memory(memory_id)
    memory = memory_service.all()

    return ok_response(
        data={
            "deleted": deleted,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory deleted." if deleted else "Memory not found.",
    )


@app.post("/api/memory/cleanup")
@guarded_json_route
def api_memory_cleanup():
    result = memory_service.cleanup_memories()
    memory = memory_service.all()

    return ok_response(
        data={
            "result": result,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory cleanup complete.",
    )


@app.post("/api/memory/promote")
@guarded_json_route
def api_memory_promote():
    result = memory_service.promote_memories()
    memory = memory_service.all()

    return ok_response(
        data={
            "result": result,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory promotion complete.",
    )


@app.post("/api/memory/cleanup-promote")
@guarded_json_route
def api_memory_cleanup_promote():
    result = memory_service.cleanup_and_promote_memories()
    memory = memory_service.all()

    return ok_response(
        data={
            "result": result,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory cleanup and promotion complete.",
    )


# -----------------------
# WEB
# -----------------------

@app.post("/api/web/fetch")
def api_web_fetch():
    data = request_json()
    url = str(data.get("url") or "").strip()

    if not url:
        return json_error("Missing url", 400)

    result = web_service.fetch(url)
    if not result.get("ok"):
        return json_error(result.get("error") or "Fetch failed", 500, result=result)

    return json_ok(
        result=result,
        artifact=web_service.build_artifact_payload(result),
    )


# -----------------------
# RECON
# -----------------------

@app.post("/api/recon/analyze")
def api_recon_analyze():
    data = request_json()
    url = str(data.get("url") or "").strip()

    if not url:
        return json_error("Missing url", 400)

    result = recon_service.analyze_target(url)
    if not result.get("ok"):
        return json_error(result.get("error") or "Recon failed", 500, result=result)

    return json_ok(
        result=result,
        artifact=recon_service.build_artifact_payload(result),
    )

@app.post("/api/upload")
def api_upload():
    try:
        if "file" not in request.files:
            return jsonify({
                "ok": False,
                "error": "No file provided.",
            }), 400

        file = request.files["file"]
        if not file or not getattr(file, "filename", ""):
            return jsonify({
                "ok": False,
                "error": "Empty file.",
            }), 400

        original_name = os.path.basename(str(file.filename or "upload"))
        safe_name = secure_filename(original_name) or "upload.bin"

        base, ext = os.path.splitext(safe_name)
        ext = ext or ""
        final_name = f"{base}_{uuid.uuid4().hex}{ext}"

        save_path = UPLOADS_DIR / final_name
        file.save(str(save_path))

        mime_type = getattr(file, "mimetype", None) or "application/octet-stream"
        size = save_path.stat().st_size if save_path.exists() else 0

        return jsonify({
            "ok": True,
            "filename": final_name,
            "original_filename": original_name,
            "file_url": f"/api/uploads/{final_name}",
            "url": f"/api/uploads/{final_name}",
            "mime_type": mime_type,
            "size": size,
        })
    except Exception as e:
        app.logger.exception("api_upload failed")
        return jsonify({
            "ok": False,
            "error": str(e),
        }), 500

# -----------------------
# UPLOADS
# -----------------------
@app.get("/api/uploads/<path:filename>")
def api_uploads(filename: str):
    try:
        raw_name = str(filename or "").strip().lstrip("/\\")
        full_path = (UPLOADS_DIR / raw_name).resolve()
        uploads_root = UPLOADS_DIR.resolve()

        try:
            full_path.relative_to(uploads_root)
        except ValueError:
            app.logger.warning(f"UPLOAD BLOCKED OUTSIDE ROOT: {full_path}")
            return jsonify({
                "ok": False,
                "error": "Invalid upload path",
                "filename": raw_name,
            }), 400

        if not full_path.exists() or not full_path.is_file():
            app.logger.warning(f"UPLOAD MISS: {full_path}")
            return jsonify({
                "ok": False,
                "error": "File not found",
                "filename": raw_name,
                "full_path": str(full_path),
                "uploads_dir": str(uploads_root),
            }), 404

        app.logger.info(f"UPLOAD HIT: {full_path}")
        return send_from_directory(
            directory=str(uploads_root),
            path=raw_name,
            as_attachment=False,
        )

    except TypeError:
        # Older Flask / Werkzeug compatibility
        try:
            raw_name = str(filename or "").strip().lstrip("/\\")
            full_path = (UPLOADS_DIR / raw_name).resolve()
            uploads_root = UPLOADS_DIR.resolve()

            try:
                full_path.relative_to(uploads_root)
            except ValueError:
                app.logger.warning(f"UPLOAD BLOCKED OUTSIDE ROOT: {full_path}")
                return jsonify({
                    "ok": False,
                    "error": "Invalid upload path",
                    "filename": raw_name,
                }), 400

            if not full_path.exists() or not full_path.is_file():
                app.logger.warning(f"UPLOAD MISS: {full_path}")
                return jsonify({
                    "ok": False,
                    "error": "File not found",
                    "filename": raw_name,
                    "full_path": str(full_path),
                    "uploads_dir": str(uploads_root),
                }), 404

            app.logger.info(f"UPLOAD HIT: {full_path}")
            return send_from_directory(
                str(uploads_root),
                raw_name,
                as_attachment=False,
            )
        except Exception as e:
            app.logger.exception("api_uploads failed (compat path)")
            return jsonify({
                "ok": False,
                "error": str(e),
                "filename": str(filename or ""),
            }), 500

    except Exception as e:
        app.logger.exception("api_uploads failed")
        return jsonify({
            "ok": False,

            "error": str(e),
            "filename": str(filename or ""),
        }), 500
# -----------------------
# MAIN
# -----------------------
if __name__ == "__main__":
    app.run(debug=False, port=5001)