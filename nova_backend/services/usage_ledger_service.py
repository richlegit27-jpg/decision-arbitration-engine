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

# ============================================================
# NOVA_PROVIDER_COST_ESTIMATOR
# Provider costs are USD per million tokens.
# Configure verified rates using NOVA_MODEL_PRICING_USD_PER_MILLION.
# Unknown models deliberately return no cost estimate.
# ============================================================

def _nova_provider_cost_estimate(
    model,
    input_tokens,
    output_tokens,
    estimated_tokens,
):
    import json

    raw_rates = os.environ.get(
        "NOVA_MODEL_PRICING_USD_PER_MILLION",
        "",
    ).strip()

    if not raw_rates:
        return {
            "provider_cost_usd": None,
            "provider_cost_estimated": None,
            "provider_cost_currency": "USD",
            "provider_pricing_source": None,
        }

    try:
        pricing = json.loads(raw_rates)
    except (TypeError, ValueError):
        return {
            "provider_cost_usd": None,
            "provider_cost_estimated": None,
            "provider_cost_currency": "USD",
            "provider_pricing_source": None,
        }

    model_key = str(model or "unknown").strip().casefold()
    rate = next(
        (
            value
            for key, value in pricing.items()
            if str(key).strip().casefold() == model_key
        ),
        None,
    )

    if not isinstance(rate, dict):
        return {
            "provider_cost_usd": None,
            "provider_cost_estimated": None,
            "provider_cost_currency": "USD",
            "provider_pricing_source": None,
        }

    try:
        input_rate = float(rate["input"])
        output_rate = float(rate["output"])

        if (
            input_rate < 0
            or output_rate < 0
            or not math.isfinite(input_rate)
            or not math.isfinite(output_rate)
        ):
            raise ValueError("Invalid provider pricing")

        cost = (
            max(0, int(input_tokens)) * input_rate
            + max(0, int(output_tokens)) * output_rate
        ) / 1_000_000

    except (KeyError, TypeError, ValueError, OverflowError):
        return {
            "provider_cost_usd": None,
            "provider_cost_estimated": None,
            "provider_cost_currency": "USD",
            "provider_pricing_source": None,
        }

    return {
        "provider_cost_usd": round(cost, 10),
        "provider_cost_estimated": bool(estimated_tokens),
        "provider_cost_currency": "USD",
        "provider_pricing_source": rate.get("source"),
    }

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
        "by_user": {},
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
    data.setdefault("by_user", {})
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

    token_counts_estimated = not bool(
        official_total or official_input or official_output
    )

    event = {
        "timestamp": utc_now_iso(),
        "session_id": session_id or "",
        "user_id": user_id or "",
        "username": username or "",
        "model": model or "unknown",
        "input_tokens": final_input,
        "output_tokens": final_output,
        "total_tokens": final_total,
        "estimated": token_counts_estimated,
        "provider_usage": provider_usage,
        "meta": meta,
    }

    event.update(
        _nova_provider_cost_estimate(
            model=model,
            input_tokens=final_input,
            output_tokens=final_output,
            estimated_tokens=token_counts_estimated,
        )
    )

    with _USAGE_LOCK:
        ledger = load_usage_ledger()
        ledger["events"].append(event)

        totals = ledger.setdefault("totals", {})
        totals["input_tokens"] = int(totals.get("input_tokens", 0)) + final_input
        totals["output_tokens"] = int(totals.get("output_tokens", 0)) + final_output
        totals["total_tokens"] = int(totals.get("total_tokens", 0)) + final_total
        totals["calls"] = int(totals.get("calls", 0)) + 1

        _add_to_bucket(
            ledger.setdefault("by_user", {}),
            user_id or username or "unknown",
            final_input,
            final_output,
            final_total,
        )

        _add_to_bucket(
            ledger.setdefault("by_session", {}),
            session_id or "unknown",
            final_input,
            final_output,
            final_total,
        )

        _add_to_bucket(
            ledger.setdefault("by_model", {}),
            model or "unknown",
            final_input,
            final_output,
            final_total,
        )

        # Keep the file from growing forever during early dev.
        max_events = int(os.environ.get("NOVA_USAGE_MAX_EVENTS", "5000"))
        if len(ledger["events"]) > max_events:
            ledger["events"] = ledger["events"][-max_events:]

        save_usage_ledger(ledger)

    return event


def usage_summary(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
) -> Dict[str, Any]:
    ledger = load_usage_ledger()
    events = ledger.get("events", [])

    if user_id or username:
        user_id = str(user_id or "").strip()
        username = str(username or "").strip().casefold()

        events = [
            event for event in events
            if (
                user_id
                and str(event.get("user_id") or "").strip() == user_id
            ) or (
                username
                and str(event.get("username") or "").strip().casefold()
                == username
            )
        ]

    if session_id:
        events = [
            event for event in events
            if event.get("session_id") == session_id
        ]

    totals = {
        "input_tokens": sum(
            int(event.get("input_tokens") or 0) for event in events
        ),
        "output_tokens": sum(
            int(event.get("output_tokens") or 0) for event in events
        ),
        "total_tokens": sum(
            int(event.get("total_tokens") or 0) for event in events
        ),
        "calls": len(events),
    }

    result = {
        "ok": True,
        "totals": totals,
        "recent_events": events[-50:],
        "updated_at": ledger.get("updated_at"),
    }

    if session_id:
        result["session_id"] = session_id

    if user_id:
        result["user_id"] = user_id

    return result