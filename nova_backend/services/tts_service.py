from pathlib import Path
from typing import Optional
from uuid import uuid4


def create_tts_audio(
    text: str,
    uploads_dir: str,
    voice: str = "alloy",
) -> dict:
    clean_text = str(text or "").strip()

    if not clean_text:
        return {
            "ok": False,
            "error": "Missing text for TTS.",
            "audio_url": "",
            "audio_path": "",
        }

    uploads_path = Path(uploads_dir).resolve()
    uploads_path.mkdir(parents=True, exist_ok=True)

    filename = f"tts_{uuid4().hex}.mp3"
    output_path = uploads_path / filename

    try:
        from openai import OpenAI

        client = OpenAI()

        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=clean_text,
        ) as response:
            response.stream_to_file(output_path)

        return {
            "ok": True,
            "error": "",
            "audio_url": f"/api/uploads/{filename}",
            "audio_path": str(output_path),
            "filename": filename,
            "voice": voice,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": f"TTS failed: {exc}",
            "audio_url": "",
            "audio_path": "",
        }