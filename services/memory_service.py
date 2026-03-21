import json
import re
from datetime import UTC, datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MEMORY_FILE = DATA_DIR / "memory.json"


def _ensure_storage():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not MEMORY_FILE.exists():
        MEMORY_FILE.write_text("{}", encoding="utf-8")


def _load_memory_store():
    _ensure_storage()
    try:
        raw = MEMORY_FILE.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _save_memory_store(store: dict):
    _ensure_storage()
    MEMORY_FILE.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _user_key(user_id: int) -> str:
    return str(int(user_id))


def _normalize_text(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _looks_like_question(text: str) -> bool:
    clean = _normalize_text(text).lower()
    if not clean:
        return False

    question_starters = (
        "what ",
        "who ",
        "where ",
        "when ",
        "why ",
        "how ",
        "can ",
        "could ",
        "should ",
        "would ",
        "do ",
        "does ",
        "did ",
        "is ",
        "are ",
        "am ",
        "will ",
        "have ",
        "has ",
        "had ",
    )
    return clean.endswith("?") or clean.startswith(question_starters)


def _is_too_short(text: str) -> bool:
    clean = _normalize_text(text)
    if len(clean) < 12:
        return True
    if len(clean.split()) < 3:
        return True
    return False


def _contains_ephemeral_language(text: str) -> bool:
    clean = _normalize_text(text).lower()

    ephemeral_patterns = [
        r"\btoday\b",
        r"\btomorrow\b",
        r"\byesterday\b",
        r"\bright now\b",
        r"\bthis morning\b",
        r"\bthis afternoon\b",
        r"\btonight\b",
        r"\bsoon\b",
        r"\blater\b",
        r"\bnext week\b",
        r"\bremind me\b",
        r"\bi need to\b",
        r"\bi should\b",
        r"\bi am going to\b",
        r"\bi'm going to\b",
        r"\blet's\b",
        r"\bgo to the gym\b",
    ]
    return any(re.search(pattern, clean) for pattern in ephemeral_patterns)


def _extract_explicit_memory_candidate(message_text: str) -> str:
    clean = _normalize_text(message_text)
    if not clean:
        return ""

    patterns = [
        r"^(?:remember\s+that)\s+(.+)$",
        r"^(?:remember\s+hat)\s+(.+)$",
        r"^(?:remember)\s+(.+)$",
        r"^(?:note\s+that)\s+(.+)$",
        r"^(?:for\s+future\s+reference)\s+(.+)$",
        r"^(?:save\s+this)\s*[:\-]?\s*(.+)$",
        r"^(?:from\s+now\s+on)\s+(.+)$",
        r"^(?:my\s+preference\s+is)\s+(.+)$",
        r"^(?:i\s+always\s+want)\s+(.+)$",
        r"^(?:i\s+prefer)\s+(.+)$",
    ]

    for pattern in patterns:
        match = re.match(pattern, clean, flags=re.IGNORECASE)
        if match:
            return _normalize_text(match.group(1))

    return ""


def _is_durable_preference_statement(text: str) -> bool:
    clean = _normalize_text(text).lower()
    if not clean:
        return False

    durable_markers = [
        "always",
        "prefer",
        "preferred",
        "from now on",
        "my preference",
        "powershell commands",
        "notepad in front",
        "file path format",
        "uses ports",
        "use ports",
        "nova uses ports",
    ]
    return any(marker in clean for marker in durable_markers)


def _looks_like_durable_fact(text: str) -> bool:
    clean = _normalize_text(text).lower()
    if not clean:
        return False

    durable_patterns = [
        r"\buses?\s+ports?\s+\d+(?:\s+(?:and|&)\s+\d+)+\b",
        r"\bport\s+\d+\b",
        r"\bpreferred\b",
        r"\balways want\b",
        r"\bfile path\b",
        r"\bpowershell\b",
        r"\bnotepad in front\b",
        r"\bsetup uses\b",
    ]
    return any(re.search(pattern, clean) for pattern in durable_patterns)


def _should_auto_save_message(message_text: str) -> tuple[bool, str]:
    clean = _normalize_text(message_text)
    if not clean:
        return False, ""

    explicit_candidate = _extract_explicit_memory_candidate(clean)
    if explicit_candidate:
        if _is_too_short(explicit_candidate):
            return False, ""
        if _looks_like_question(explicit_candidate):
            return False, ""
        if _contains_ephemeral_language(explicit_candidate):
            return False, ""
        return True, explicit_candidate

    if _looks_like_question(clean):
        return False, ""

    if _is_too_short(clean):
        return False, ""

    if _contains_ephemeral_language(clean):
        return False, ""

    if _is_durable_preference_statement(clean):
        return True, clean

    if _looks_like_durable_fact(clean):
        return True, clean

    return False, ""


def list_memory_items(user_id: int) -> list[dict]:
    store = _load_memory_store()
    items = store.get(_user_key(user_id), [])
    if not isinstance(items, list):
        return []
    return items


def _next_memory_id(items: list[dict]) -> int:
    if not items:
        return 1
    return max(int(item.get("id", 0)) for item in items) + 1


def create_memory_item(user_id: int, content: str) -> dict | None:
    clean = _normalize_text(content)
    if not clean:
        return None

    store = _load_memory_store()
    key = _user_key(user_id)
    items = store.get(key, [])

    for existing in items:
        existing_content = _normalize_text(existing.get("content", ""))
        if existing_content.lower() == clean.lower():
            return existing

    item = {
        "id": _next_memory_id(items),
        "content": clean,
        "created_at": _utc_now_iso(),
    }

    items.insert(0, item)
    store[key] = items
    _save_memory_store(store)
    return item


def delete_memory_item(user_id: int, memory_id: int) -> bool:
    store = _load_memory_store()
    key = _user_key(user_id)
    items = store.get(key, [])

    original_count = len(items)
    filtered = [item for item in items if int(item.get("id", 0)) != int(memory_id)]

    if len(filtered) == original_count:
        return False

    store[key] = filtered
    _save_memory_store(store)
    return True


def delete_all_memory_items(user_id: int):
    store = _load_memory_store()
    key = _user_key(user_id)
    store[key] = []
    _save_memory_store(store)


def maybe_capture_memory_from_message(user_id: int, message_text: str) -> dict | None:
    should_save, memory_text = _should_auto_save_message(message_text)
    if not should_save:
        return None

    return create_memory_item(user_id, memory_text)