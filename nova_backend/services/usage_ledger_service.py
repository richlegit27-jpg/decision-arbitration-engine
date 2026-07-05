"""
Nova usage ledger service.

Backend-only MVP:
- Estimate tokens when provider usage is missing.
- Record model usage events to data/nova_usage.json.
- Summarize usage globally and per session.
- Safe append/write with simple JSON file storage.
"""

from __future__ import annotations

import json
import math
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


_USAGE_LOCK = threading.Lock()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def usage_file_path() -> Path:
    return _project_root() / "data" / "nova_usage.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def estimate_tokens(value: Any) -> int:
    """
    Rough fallback estimate.

    This is not billing-perfect. It is only used when the model/provider
    response does not include official token usage.
    """
    if value is None:
        return 0

    if not isinstance(value, str):
        try:
            value = json.dumps(value, ensure_ascii=False)
        except Exception:
            value = str(value)

    text = value.strip()
    if not text:
        return 0

    # Common rough English/code estimate: about 4 chars per token.
    return max(1, math.ceil(len(text) / 4))


def _empty_ledger() -> Dict[str, Any]:
    return {
        "version": 1,
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "events": [],
        "totals": {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "calls": 0,
        },
        "by_session": {},
        "by_model": {},
    }


def load_usage_ledger() -> Dict[str, Any]:
    path = usage_file_path()

    if not path.exists():
        return _empty_ledger()

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return _empty_ledger()

    if not isinstance(data, dict):
        return _empty_ledger()

    data.setdefault("version", 1)
    data.setdefault("created_at", utc_now_iso())
    data.setdefault("updated_at", utc_now_iso())
    data.setdefault("events", [])
    data.setdefault("totals", {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "calls": 0,
    })
    data.setdefault("by_session", {})
    data.setdefault("by_model", {})

    return data


def save_usage_ledger(data: Dict[str, Any]) -> None:
    path = usage_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data["updated_at"] = utc_now_iso()

    tmp_path = path.with_suffix(".json.tmp")

    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    os.replace(tmp_path, path)


def _add_to_bucket(bucket: Dict[str, Any], key: str, input_tokens: int, output_tokens: int, total_tokens: int) -> None:
    safe_key = str(key or "unknown")

    item = bucket.setdefault(safe_key, {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "calls": 0,
    })

    item["input_tokens"] = int(item.get("input_tokens", 0)) + input_tokens
    item["output_tokens"] = int(item.get("output_tokens", 0)) + output_tokens
    item["total_tokens"] = int(item.get("total_tokens", 0)) + total_tokens
    item["calls"] = int(item.get("calls", 0)) + 1


def record_model_usage(
    *,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    model: Optional[str] = None,
    input_text: Any = None,
    output_text: Any = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    provider_usage: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Record one model usage event.

    If official provider usage is available, pass it as provider_usage.
    Otherwise this falls back to estimated tokens from input/output text.
    """
    provider_usage = provider_usage or {}
    meta = meta or {}

    official_input = (
        provider_usage.get("prompt_tokens")
        or provider_usage.get("input_tokens")
    )
    official_output = (
        provider_usage.get("completion_tokens")
        or provider_usage.get("output_tokens")
    )
    official_total = provider_usage.get("total_tokens")

    final_input = int(input_tokens if input_tokens is not None else (official_input or estimate_tokens(input_text)))
    final_output = int(output_tokens if output_tokens is not None else (official_output or estimate_tokens(output_text)))
    final_total = int(total_tokens if total_tokens is not None else (official_total or (final_input + final_output)))

    event = {
        "timestamp": utc_now_iso(),
        "session_id": session_id or "",
        "user_id": user_id or "",
        "username": username or "",
        "model": model or "unknown",
        "input_tokens": final_input,
        "output_tokens": final_output,
        "total_tokens": final_total,
        "estimated": not bool(official_total or official_input or official_output),
        "provider_usage": provider_usage,
        "meta": meta,
    }

    with _USAGE_LOCK:
        ledger = load_usage_ledger()

        ledger["events"].append(event)

        totals = ledger.setdefault("totals", {})
        totals["input_tokens"] = int(totals.get("input_tokens", 0)) + final_input
        totals["output_tokens"] = int(totals.get("output_tokens", 0)) + final_output
        totals["total_tokens"] = int(totals.get("total_tokens", 0)) + final_total
        totals["calls"] = int(totals.get("calls", 0)) + 1

        _add_to_bucket(ledger.setdefault("by_session", {}), session_id or "unknown", final_input, final_output, final_total)
        _add_to_bucket(ledger.setdefault("by_model", {}), model or "unknown", final_input, final_output, final_total)

        # Keep the file from growing forever during early dev.
        max_events = int(os.environ.get("NOVA_USAGE_MAX_EVENTS", "5000"))
        if len(ledger["events"]) > max_events:
            ledger["events"] = ledger["events"][-max_events:]

        save_usage_ledger(ledger)

    return event


def usage_summary(session_id: Optional[str] = None) -> Dict[str, Any]:
    ledger = load_usage_ledger()

    if session_id:
        session_totals = ledger.get("by_session", {}).get(session_id, {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "calls": 0,
        })

        recent_events = [
            event for event in ledger.get("events", [])
            if event.get("session_id") == session_id
        ][-50:]

        return {
            "ok": True,
            "session_id": session_id,
            "totals": session_totals,
            "recent_events": recent_events,
        }

    return {
        "ok": True,
        "totals": ledger.get("totals", {}),
        "by_session": ledger.get("by_session", {}),
        "by_model": ledger.get("by_model", {}),
        "recent_events": ledger.get("events", [])[-50:],
        "updated_at": ledger.get("updated_at"),
    }
