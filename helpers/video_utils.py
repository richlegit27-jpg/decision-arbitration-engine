from __future__ import annotations

from pathlib import Path


def build_video_analysis_result(
    *,
    attachments,
    user_text: str,
    safe_list,
    normalize_text,
) -> dict:
    videos = []

    for item in safe_list(attachments):
        if not isinstance(item, dict):
            continue

        mime_type = str(item.get("mime_type") or item.get("mime") or "").strip()
        name = str(item.get("name") or item.get("filename") or "").strip()
        url = str(item.get("url") or item.get("path") or "").strip()
        kind = str(item.get("kind") or item.get("type") or "").lower().strip()

        is_video = False
        if "video" in kind:
            is_video = True
        elif mime_type.startswith("video/"):
            is_video = True
        elif name.lower().endswith((".mp4", ".webm", ".mov", ".m4v", ".avi")):
            is_video = True
        elif url.lower().endswith((".mp4", ".webm", ".mov", ".m4v", ".avi")):
            is_video = True

        if not is_video:
            continue

        if url and not url.startswith("/api/uploads/"):
            safe_name = Path(url).name.strip()
            if safe_name:
                url = f"/api/uploads/{safe_name}"

        try:
            size_int = int(item.get("size") or 0)
        except Exception:
            size_int = 0

        videos.append(
            {
                "url": url,
                "name": name or Path(url).name.strip() or "video",
                "mime_type": mime_type or "video/mp4",
                "size": size_int,
            }
        )

    if not videos:
        return {
            "ok": False,
            "error": "No video attachment found.",
            "summary": "",
            "analysis_text": "",
            "videos": [],
            "bullets": [],
        }

    prompt = normalize_text(user_text).strip()
    first_video = videos[0]
    video_name = str(first_video.get("name") or "video").strip()

    bullets = [
        f"Video file received: {video_name}",
        f"Detected {len(videos)} video attachment(s)",
    ]

    if prompt:
        analysis_text = (
            f"Video received for analysis.\n\n"
            f"User request: {prompt}\n\n"
            f"I can confirm the upload and preserve the video in chat and artifacts. "
            f"Deeper frame-level understanding can be layered in later without breaking this pipeline."
        )
    else:
        analysis_text = (
            "Video received for analysis.\n\n"
            "The upload has been preserved and attached to this session."
        )

    summary = normalize_text(analysis_text).strip()
    if not summary:
        summary = "Video received and analyzed."

    return {
        "ok": True,
        "summary": summary,
        "analysis_text": analysis_text,
        "videos": videos,
        "bullets": bullets,
    }