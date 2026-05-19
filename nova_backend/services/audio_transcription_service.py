from pathlib import Path
from typing import Any, Dict
from urllib.parse import unquote


AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
    ".webm",
    ".flac",
}


def is_audio_attachment(attachment: Dict[str, Any]) -> bool:
    if not isinstance(attachment, dict):
        return False

    name = str(
        attachment.get("name")
        or attachment.get("filename")
        or attachment.get("stored_name")
        or attachment.get("url")
        or ""
    ).lower()

    mime_type = str(
        attachment.get("mime_type")
        or attachment.get("content_type")
        or attachment.get("type")
        or ""
    ).lower()

    return (
        mime_type.startswith("audio/")
        or Path(name).suffix.lower() in AUDIO_EXTENSIONS
    )


def _safe_upload_candidate(value: Any) -> str:
    if not value:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    text = unquote(text)
    text = text.replace("\\", "/")

    if "/api/uploads/" in text:
        text = text.split("/api/uploads/", 1)[1]

    return Path(text).name


def resolve_audio_path(attachment: Dict[str, Any], uploads_dir: str) -> Path | None:
    uploads_path = Path(uploads_dir).resolve()

    candidates = [
        attachment.get("stored_name"),
        attachment.get("filename"),
        attachment.get("name"),
        attachment.get("path"),
        attachment.get("url"),
        attachment.get("file_url"),
    ]

    for candidate in candidates:
        safe_name = _safe_upload_candidate(candidate)
        if not safe_name:
            continue

        possible_path = (uploads_path / safe_name).resolve()

        if not str(possible_path).startswith(str(uploads_path)):
            continue

        if possible_path.exists() and possible_path.is_file():
            return possible_path

    return None


def transcribe_audio_file(audio_path: Path) -> str:
    try:
        from openai import OpenAI
    except Exception as exc:
        return f"Transcription unavailable because OpenAI import failed: {exc}"

    try:
        client = OpenAI()

        with audio_path.open("rb") as audio_file:
            result = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file,
            )

        transcript = getattr(result, "text", "") or ""

        if not transcript.strip():
            return "No speech was detected in this audio."

        return transcript.strip()

    except Exception as exc:
        return f"Transcription failed: {exc}"