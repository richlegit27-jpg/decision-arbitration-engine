from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
LEADS_PATH = DATA_DIR / "nova_leads.json"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: Any, limit: int = 4000) -> str:
    if value is None:
        return ""

    text = str(value).replace("\x00", "").strip()
    text = re.sub(r"\s+", " ", text)

    if len(text) > limit:
        text = text[:limit].rstrip()

    return text


def clean_payload(payload: dict[str, Any] | None) -> dict[str, str]:
    raw = payload or {}

    return {
        "name": clean_text(raw.get("name") or raw.get("full_name") or raw.get("fullname"), 180),
        "email": clean_text(raw.get("email"), 240).lower(),
        "company": clean_text(raw.get("company") or raw.get("organization"), 220),
        "interest": clean_text(raw.get("interest") or raw.get("reason") or raw.get("topic"), 500),
        "message": clean_text(raw.get("message") or raw.get("notes") or raw.get("note"), 4000),
        "source": clean_text(raw.get("source") or raw.get("page") or raw.get("form"), 180),
    }


def validate_lead(payload: dict[str, str]) -> None:
    email = payload.get("email", "")
    message = payload.get("message", "")
    interest = payload.get("interest", "")

    if email and not EMAIL_RE.match(email):
        raise ValueError("Please enter a valid email address.")

    if not email and not message and not interest:
        raise ValueError("Please add an email, message, or reason so Richard can follow up.")


def read_store() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not LEADS_PATH.exists():
        return {
            "version": 1,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "leads": [],
        }

    try:
        data = json.loads(LEADS_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    leads = data.get("leads")
    if not isinstance(leads, list):
        leads = []

    return {
        "version": int(data.get("version") or 1),
        "created_at": data.get("created_at") or utc_now_iso(),
        "updated_at": data.get("updated_at") or utc_now_iso(),
        "leads": leads,
    }


def write_store(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = utc_now_iso()

    tmp_path = LEADS_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    tmp_path.replace(LEADS_PATH)


def save_lead(kind: str, payload: dict[str, Any] | None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    clean = clean_payload(payload)
    validate_lead(clean)

    raw = payload or {}
    dry_run = bool(raw.get("dry_run") or raw.get("test") or raw.get("_test"))

    lead = {
        "id": "lead_" + uuid.uuid4().hex,
        "kind": clean_text(kind, 80) or "contact",
        "status": "new",
        "created_at": utc_now_iso(),
        "name": clean["name"],
        "email": clean["email"],
        "company": clean["company"],
        "interest": clean["interest"],
        "message": clean["message"],
        "source": clean["source"],
        "meta": meta or {},
    }

    if dry_run:
        lead["dry_run"] = True
        return lead

    data = read_store()
    data["leads"].insert(0, lead)
    data["leads"] = data["leads"][:1000]
    write_store(data)

    return lead


def list_leads(limit: int = 100) -> dict[str, Any]:
    data = read_store()
    leads = data.get("leads", [])

    try:
        limit = int(limit)
    except Exception:
        limit = 100

    limit = max(1, min(limit, 500))

    return {
        "ok": True,
        "count": len(leads),
        "leads": leads[:limit],
        "path": str(LEADS_PATH),
        "updated_at": data.get("updated_at"),
    }
