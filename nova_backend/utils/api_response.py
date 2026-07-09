from __future__ import annotations

from typing import Any, Dict, Optional


def ok_response(
    *,
    data: Optional[Dict[str, Any]] = None,
    message: str = "",
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "ok": True,
        "message": str(message or ""),
        "data": data or {},
        "meta": meta or {},
        "error": "",
    }


def error_response(
    *,
    error: str,
    code: str = "request_failed",
    data: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "ok": False,
        "message": "",
        "data": data or {},
        "meta": {
            **(meta or {}),
            "code": str(code or "request_failed"),
        },
        "error": str(error or "Request failed."),
    }

