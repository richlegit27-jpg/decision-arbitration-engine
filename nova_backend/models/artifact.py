from __future__ import annotations

import uuid
from typing import Any, Dict

from nova_backend.utils.time_utils import iso_now, ensure_iso


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _trim(text: str, limit: int) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "â€¦"


def new_artifact(
    kind: str = "artifact",
    title: str = "Untitled",
    body: str = "",
    session_id: str = "",
    source: str = "",
    meta: Dict[str, Any] | None = None,
) -> dict:
    now = iso_now()
    return {
        "id": f"artifact_{uuid.uuid4().hex}",
        "kind": _safe_str(kind, "artifact").strip() or "artifact",
        "title": _safe_str(title, "Untitled").strip() or "Untitled",
        "body": _safe_str(body, ""),
        "preview": _trim(body, 180),
        "session_id": _safe_str(session_id, "").strip(),
        "source": _safe_str(source, "").strip(),
        "meta": _safe_dict(meta),
        "created_at": now,
        "updated_at": now,
        "viewer": {
            "kind": _safe_str(kind, "artifact").strip() or "artifact",
            "title": _safe_str(title, "Untitled").strip() or "Untitled",
            "body": _safe_str(body, ""),
            "source_url": "",
            "image_url": "",
            "video_url": "",
            "audio_url": "",
            "analysis_text": "",
            "bullets": [],
        },
    }


def normalize_artifact(raw: Dict[str, Any]) -> dict:
    if not isinstance(raw, dict):
        return new_artifact()

    meta = _safe_dict(raw.get("meta"))
    viewer = _safe_dict(raw.get("viewer"))

    kind = _safe_str(raw.get("kind"), "artifact").strip() or "artifact"
    title = _safe_str(raw.get("title"), "Untitled").strip() or "Untitled"
    body = _safe_str(raw.get("body"), raw.get("content", ""))

    preview = _safe_str(raw.get("preview"), "").strip()
    if not preview:
        preview = _trim(body, 180)

    source_url = (
        _safe_str(viewer.get("source_url"), "").strip()
        or _safe_str(meta.get("source_url"), "").strip()
        or _safe_str(meta.get("url"), "").strip()
    )

    image_url = (
        _safe_str(viewer.get("image_url"), "").strip()
        or _safe_str(meta.get("image_url"), "").strip()
        or _safe_str(meta.get("url"), "").strip()
        if kind in ("image_generation", "image_analysis")
        else _safe_str(viewer.get("image_url"), "").strip()
        or _safe_str(meta.get("image_url"), "").strip()
    )

    video_url = (
        _safe_str(viewer.get("video_url"), "").strip()
        or _safe_str(meta.get("video_url"), "").strip()
    )

    audio_url = (
        _safe_str(viewer.get("audio_url"), "").strip()
        or _safe_str(meta.get("audio_url"), "").strip()
    )

    analysis_text = (
        _safe_str(viewer.get("analysis_text"), "").strip()
        or _safe_str(meta.get("analysis_text"), "").strip()
    )

    bullets = viewer.get("bullets")
    if not isinstance(bullets, list):
        bullets = []

    normalized_viewer = {
        "kind": _safe_str(viewer.get("kind"), kind).strip() or kind,
        "title": _safe_str(viewer.get("title"), title).strip() or title,
        "body": _safe_str(viewer.get("body"), body),
        "source_url": source_url,
        "image_url": image_url,
        "video_url": video_url,
        "audio_url": audio_url,
        "analysis_text": analysis_text,
        "bullets": [str(x).strip() for x in bullets if str(x).strip()],
    }

    return {
        "id": _safe_str(raw.get("id"), f"artifact_{uuid.uuid4().hex}"),
        "kind": kind,
        "title": title,
        "body": body,
        "preview": preview,
        "session_id": _safe_str(raw.get("session_id"), "").strip(),
        "source": _safe_str(raw.get("source"), "").strip(),
        "meta": meta,
        "created_at": ensure_iso(raw.get("created_at")),
        "updated_at": ensure_iso(raw.get("updated_at")),
        "viewer": normalized_viewer,
    }


def artifact_preview(artifact: dict) -> str:
    try:
        preview = _safe_str(artifact.get("preview"), "").strip()
        if preview:
            return preview

        body = _safe_str(artifact.get("body"), "").strip()
        if body:
            return _trim(body, 180)

        viewer = _safe_dict(artifact.get("viewer"))
        viewer_body = _safe_str(viewer.get("body"), "").strip()
        if viewer_body:
            return _trim(viewer_body, 180)

        analysis_text = _safe_str(viewer.get("analysis_text"), "").strip()
        if analysis_text:
            return _trim(analysis_text, 180)

        return ""
    except Exception:
        return ""


def artifact_viewer_payload(artifact: dict) -> dict:
    normalized = normalize_artifact(artifact)
    return normalized["viewer"]

