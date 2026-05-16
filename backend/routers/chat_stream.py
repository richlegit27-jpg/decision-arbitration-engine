from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from backend.memory_vectors import search_memory, store_memory
from backend.tools.python_runner import run_python

try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None


router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "backend" / "data"
STATE_FILE = DATA_DIR / "nova_state.json"
PROJECT_ROOT = Path(os.getenv("NOVA_PROJECT_ROOT", str(BASE_DIR))).resolve()

DATA_DIR.mkdir(parents=True, exist_ok=True)

AVAILABLE_MODELS = [
    {"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini"},
    {"id": "gpt-4.1", "name": "GPT-4.1"},
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
    {"id": "gpt-4o", "name": "GPT-4o"},
]

ALLOWED_MODEL_IDS = {m["id"] for m in AVAILABLE_MODELS}
DEFAULT_MODEL = "gpt-4.1-mini"

TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".json",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".env",
    ".sql",
    ".xml",
    ".csv",
}


# ------------------------------------------------
# helpers
# ------------------------------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sse(data: Dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def safe_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalize_model(model: Any) -> str:
    value = safe_text(model)
    return value if value in ALLOWED_MODEL_IDS else DEFAULT_MODEL


def normalize_role(value: Any) -> str:
    role = safe_text(value).lower()
    if role == "system":
        return "assistant"
    if role in {"assistant", "user"}:
        return role
    return "user"


def truncate_text(text: str, limit: int) -> str:
    text = "" if text is None else str(text)
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def rel_project_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except Exception:
        return str(path.resolve())


# ------------------------------------------------
# safe filesystem tools
# ------------------------------------------------


def resolve_project_path(user_path: str) -> Optional[Path]:
    raw = safe_text(user_path).strip('"').strip("'")
    if not raw:
        return None

    raw = raw.replace("\\", "/")
    candidate = Path(raw)

    if candidate.is_absolute():
        try:
            resolved = candidate.resolve()
        except Exception:
            return None
    else:
        try:
            resolved = (PROJECT_ROOT / candidate).resolve()
        except Exception:
            return None

    try:
        resolved.relative_to(PROJECT_ROOT)
        return resolved
    except Exception:
        return None


def list_project_files(target: str = ".", max_items: int = 200) -> str:
    path = resolve_project_path(target) or PROJECT_ROOT

    if not path.exists():
        return f"Path not found: {target}"

    if path.is_file():
        return f"That path is a file, not a directory: {rel_project_path(path)}"

    items: List[str] = []

    try:
        for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            marker = "DIR " if child.is_dir() else "FILE"
            items.append(f"{marker} {rel_project_path(child)}")
            if len(items) >= max_items:
                items.append("...[truncated]")
                break
    except Exception as exc:
        return f"Failed to list directory: {exc}"

    if not items:
        return f"Directory is empty: {rel_project_path(path)}"

    return "\n".join(items)


def read_project_file(target: str, max_chars: int = 20000) -> str:
    path = resolve_project_path(target)

    if path is None:
        return f"Invalid or out-of-project path: {target}"

    if not path.exists():
        return f"File not found: {target}"

    if path.is_dir():
        return f"That path is a directory, not a file: {rel_project_path(path)}"

    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return f"Unsupported file type for reading: {rel_project_path(path)}"

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return f"Failed to read file: {exc}"
    except Exception as exc:
        return f"Failed to read file: {exc}"

    header = f"FILE: {rel_project_path(path)}"
    return header + "\n" + truncate_text(text, max_chars)


def search_project_text(query: str, max_matches: int = 40) -> str:
    pattern = safe_text(query)
    if not pattern:
        return "No search query provided."

    pattern_lower = pattern.lower()
    results: List[str] = []

    try:
        for path in PROJECT_ROOT.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in TEXT_EXTENSIONS:
                continue

            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            for line_no, line in enumerate(text.splitlines(), start=1):
                if pattern_lower in line.lower():
                    snippet = truncate_text(line.strip(), 300)
                    results.append(f"{rel_project_path(path)}:{line_no}: {snippet}")
                    if len(results) >= max_matches:
                        results.append("...[truncated]")
                        return "\n".join(results)

    except Exception as exc:
        return f"Search failed: {exc}"

    if not results:
        return f'No matches found for "{pattern}".'

    return "\n".join(results)


# ------------------------------------------------
# python tool helpers
# ------------------------------------------------


def extract_python_code_block(message: str) -> str:
    text = message or ""

    fenced_python = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced_python:
        return (fenced_python.group(1) or "").strip()

    fenced_any = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if fenced_any:
        return (fenced_any.group(1) or "").strip()

    return ""


def should_run_python(message: str) -> bool:
    lower = safe_text(message).lower()

    triggers = [
        "run python",
        "execute python",
        "run this python",
        "execute this python",
        "run code",
        "execute code",
        "test this python",
        "analyze with python",
        "use python",
    ]

    return any(trigger in lower for trigger in triggers)


def collect_debug_context(message: str) -> List[Dict[str, str]]:
    text = safe_text(message)
    lower = text.lower()
    tool_outputs: List[Dict[str, str]] = []

    windows_path_match = re.search(r"([A-Za-z]:\\[^\n\r\"']+)", text)
    unix_like_match = re.search(r"((?:backend|static|templates|app|src|data|logs|tests)[/\w\.\-]+)", text)

    extracted_path = ""
    if windows_path_match:
        extracted_path = windows_path_match.group(1)
    elif unix_like_match:
        extracted_path = unix_like_match.group(1)

    wants_read = any(
        phrase in lower
        for phrase in [
            "read file",
            "open file",
            "show file",
            "check file",
            "inspect file",
            "look at file",
            "debug file",
        ]
    )

    wants_list = any(
        phrase in lower
        for phrase in [
            "list files",
            "show files",
            "show folder",
            "list folder",
            "show directory",
            "list directory",
        ]
    )

    wants_search = any(
        phrase in lower
        for phrase in [
            "search for",
            "find in project",
            "grep",
            "search project",
            "find where",
            "find references",
        ]
    )

    if extracted_path and wants_read:
        tool_outputs.append(
            {
                "tool": "read_file",
                "input": extracted_path,
                "output": read_project_file(extracted_path),
            }
        )

    if extracted_path and wants_list:
        tool_outputs.append(
            {
                "tool": "list_files",
                "input": extracted_path,
                "output": list_project_files(extracted_path),
            }
        )

    if wants_list and not extracted_path:
        tool_outputs.append(
            {
                "tool": "list_files",
                "input": ".",
                "output": list_project_files("."),
            }
        )

    search_match = re.search(
        r'(?:search for|find in project|grep|search project|find where|find references)\s+["\']?([^"\']{2,120})',
        lower,
    )
    if wants_search:
        search_term = ""
        if search_match:
            search_term = safe_text(search_match.group(1)).strip(" .,:;!?")
        elif extracted_path:
            search_term = extracted_path

        if search_term:
            tool_outputs.append(
                {
                    "tool": "search_project",
                    "input": search_term,
                    "output": search_project_text(search_term),
                }
            )

    if should_run_python(text):
        code = extract_python_code_block(text)
        if code:
            tool_outputs.append(
                {
                    "tool": "run_python",
                    "input": "inline_python_code",
                    "output": run_python(code),
                }
            )
        else:
            tool_outputs.append(
                {
                    "tool": "run_python",
                    "input": "inline_python_code",
                    "output": "No Python code block found. Put code inside triple backticks.",
                }
            )

    return tool_outputs


# ------------------------------------------------
# state
# ------------------------------------------------


def default_state() -> Dict[str, Any]:
    return {
        "selectedModel": DEFAULT_MODEL,
        "activeChatId": None,
        "chats": [],
        "messagesByChatId": {},
        "memory": [],
        "conversationSummaries": {},
    }


def load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return default_state()

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return default_state()

    state = default_state()
    if isinstance(data, dict):
        state.update(data)

    if not isinstance(state.get("messagesByChatId"), dict):
        state["messagesByChatId"] = {}

    if not isinstance(state.get("memory"), list):
        state["memory"] = []

    if not isinstance(state.get("conversationSummaries"), dict):
        state["conversationSummaries"] = {}

    if not isinstance(state.get("chats"), list):
        state["chats"] = []

    return state


def save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ------------------------------------------------
# chat helpers
# ------------------------------------------------


def get_chat_messages(state: Dict[str, Any], chat_id: str) -> List[Dict[str, Any]]:
    raw = state.get("messagesByChatId", {}).get(chat_id, [])

    if not isinstance(raw, list):
        return []

    messages: List[Dict[str, Any]] = []

    for item in raw:
        if not isinstance(item, dict):
            continue

        messages.append(
            {
                "id": item.get("id") or f"msg_{uuid4().hex}",
                "role": normalize_role(item.get("role")),
                "content": safe_text(item.get("content")),
                "created_at": item.get("created_at") or now_iso(),
            }
        )

    return messages


def append_message(
    state: Dict[str, Any],
    chat_id: str,
    role: str,
    content: str,
) -> Dict[str, Any]:
    messages = get_chat_messages(state, chat_id)

    msg = {
        "id": f"msg_{uuid4().hex}",
        "role": normalize_role(role),
        "content": safe_text(content),
        "created_at": now_iso(),
    }

    messages.append(msg)
    state["messagesByChatId"][chat_id] = messages
    return msg


# ------------------------------------------------
# memory helpers
# ------------------------------------------------


def add_memory_item(state: Dict[str, Any], text: str) -> None:
    text = safe_text(text)
    if not text:
        return

    memory = state.get("memory", [])
    if not isinstance(memory, list):
        memory = []

    existing = {safe_text(item).lower() for item in memory}
    if text.lower() not in existing:
        memory.append(text)

    state["memory"] = memory


def auto_extract_memory(user_text: str, assistant_text: str) -> List[str]:
    combined = f"{safe_text(user_text)} {safe_text(assistant_text)}".lower()

    patterns = [
        r"\bmy name is ([a-z][a-z ]{0,40})\b",
        r"\bi live in ([a-z][a-z ]{0,60})\b",
        r"\bi use ([a-z0-9_\-\. ]{1,60})\b",
        r"\bmy project is ([a-z0-9_\-\. ]{1,80})\b",
        r"\bi am working on ([a-z0-9_\-\. ]{1,80})\b",
        r"\bmy backend uses ([a-z0-9_\-\. ]{1,80})\b",
    ]

    facts: List[str] = []

    for pattern in patterns:
        match = re.search(pattern, combined)
        if not match:
            continue

        fact = safe_text(match.group(0)).strip(" .,!?:;")
        if fact and len(fact) <= 120 and fact not in facts:
            facts.append(fact)

    return facts


# ------------------------------------------------
# summary
# ------------------------------------------------


def summarize_older(messages: List[Dict[str, Any]]) -> str:
    if len(messages) < 12:
        return ""

    older = messages[:-12]
    lines: List[str] = []

    for message in older:
        content = safe_text(message.get("content"))
        if not content:
            continue

        role = "User" if normalize_role(message.get("role")) == "user" else "Nova"

        if len(content) > 200:
            content = content[:200] + "..."

        lines.append(f"{role}: {content}")

    return "\n".join(lines)


# ------------------------------------------------
# prompt builder
# ------------------------------------------------


SYSTEM_PROMPT = """
You are Nova.

Be concise, practical, and intelligent.
Avoid filler words.

When solving problems:
1. explain briefly
2. give concrete steps
3. produce working code if applicable

Use provided tool results when they are available.
Do not pretend you inspected files or ran code if no tool output was given.
If uncertain, say so clearly.
""".strip()


def build_prompt(
    state: Dict[str, Any],
    chat_id: str,
    user_message: str,
    semantic_memory: List[str],
    tool_context: List[Dict[str, str]],
) -> str:
    messages = get_chat_messages(state, chat_id)
    recent = messages[-12:]
    summary = summarize_older(messages)

    parts: List[str] = [SYSTEM_PROMPT]

    if semantic_memory:
        parts.append("\nRelevant memory:")
        for item in semantic_memory:
            text = safe_text(item)
            if text:
                parts.append(f"- {text}")

    if tool_context:
        parts.append("\nTool results:")
        for item in tool_context:
            parts.append(f"\n[{item['tool']}] input={item['input']}")
            parts.append(item["output"])

    if summary:
        parts.append("\nEarlier conversation:")
        parts.append(summary)

    if recent:
        parts.append("\nRecent conversation:")
        for message in recent:
            role = "User" if normalize_role(message.get("role")) == "user" else "Nova"
            parts.append(f"{role}: {safe_text(message.get('content'))}")

    parts.append(f"\nUser: {safe_text(user_message)}")
    parts.append("Nova:")

    return "\n".join(parts)


# ------------------------------------------------
# API
# ------------------------------------------------


@router.post("/api/chat/stream")
async def chat_stream(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    chat_id = safe_text(body.get("chat_id") or body.get("chatId"))
    message = safe_text(body.get("message") or body.get("content"))
    model = normalize_model(body.get("model"))

    if not chat_id:
        return JSONResponse({"error": "chat_id required"}, status_code=400)

    if not message:
        return JSONResponse({"error": "message required"}, status_code=400)

    state = load_state()
    append_message(state, chat_id, "user", message)
    save_state(state)

    async def event_stream():
        if AsyncOpenAI is None:
            yield sse({"type": "error", "error": "OpenAI not installed"})
            return

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            yield sse({"type": "error", "error": "OPENAI_API_KEY missing"})
            return

        client = AsyncOpenAI(api_key=api_key)

        try:
            embedding_response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=message,
            )
            query_vector = embedding_response.data[0].embedding
            semantic_memory = search_memory(query_vector) or []
        except Exception:
            semantic_memory = []

        tool_context = collect_debug_context(message)

        prompt = build_prompt(
            state=state,
            chat_id=chat_id,
            user_message=message,
            semantic_memory=semantic_memory,
            tool_context=tool_context,
        )

        final_chunks: List[str] = []

        try:
            response_stream = await client.responses.create(
                model=model,
                input=prompt,
                stream=True,
            )

            if tool_context:
                yield sse(
                    {
                        "type": "tools",
                        "content": [
                            {
                                "tool": item["tool"],
                                "input": item["input"],
                            }
                            for item in tool_context
                        ],
                    }
                )

            async for event in response_stream:
                if await request.is_disconnected():
                    return

                if event.type == "response.output_text.delta":
                    delta = getattr(event, "delta", "")
                    if delta:
                        final_chunks.append(delta)
                        yield sse({"type": "token", "content": delta})

            final_text = "".join(final_chunks).strip()

            if not final_text:
                final_text = "I did not generate a response."

            state_after = load_state()
            append_message(state_after, chat_id, "assistant", final_text)

            facts = auto_extract_memory(message, final_text)

            for fact in facts:
                try:
                    fact_embedding = await client.embeddings.create(
                        model="text-embedding-3-small",
                        input=fact,
                    )
                    store_memory(fact, fact_embedding.data[0].embedding)
                    add_memory_item(state_after, fact)
                except Exception:
                    continue

            save_state(state_after)

            yield sse({"type": "done", "content": final_text})

        except Exception as exc:
            yield sse({"type": "error", "error": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )