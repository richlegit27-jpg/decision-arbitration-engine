from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from flask import jsonify, send_file

from nova_backend.services.auth_context import get_current_user_id


LOGGER = logging.getLogger("nova.video")
MAX_VIDEO_BYTES = 200 * 1024 * 1024


class VideoGenerationError(Exception):
    """Provider adapter error with a safe, stable failure category."""

    def __init__(self, category: str, message: str = ""):
        super().__init__(message or category)
        self.category = category


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_video_error(error: Exception) -> tuple[str, str]:
    category = str(getattr(error, "category", "") or "").strip().lower()
    detail = f"{type(error).__name__} {error}".lower()
    if category in {"safety", "moderation", "blocked"} or any(
        term in detail for term in ("moderation", "safety", "policy_violation", "blocked prompt")
    ):
        return "safety_rejected", "Nova couldn't generate that video because the request was blocked by the video safety system. Try changing the description."
    if isinstance(error, TimeoutError) or category == "timeout" or "timed out" in detail:
        return "timeout", "Video generation took too long and couldn't finish. Please try again later."
    if category in {"authentication", "configuration"} or any(
        term in detail for term in ("invalid api key", "unauthorized", "authentication", "not configured")
    ):
        return "provider_configuration", "Video generation isn't configured correctly on this Nova server yet. Please try again later."
    if category == "rate_limit" or "rate limit" in detail or "too many requests" in detail:
        return "rate_limited", "The video service is busy right now. Please try again shortly."
    if isinstance(error, (ConnectionError, OSError)) or category == "unavailable":
        return "provider_unavailable", "The video service is temporarily unavailable. Please try again later."
    return "generation_failed", "Nova couldn't finish generating that video. Please try again."


class VideoGenerationService:
    """Durable, owner-scoped asynchronous text-to-video job boundary.

    Providers implement ``generate(prompt)`` and return MP4 bytes plus optional
    factual metadata. No provider is selected by this repository today; tests
    inject a fake adapter and deployments must explicitly wire a real one.
    """

    def __init__(
        self,
        jobs_file: str | Path,
        uploads_dir: str | Path,
        *,
        provider: Any = None,
        artifact_service: Any = None,
        session_service: Any = None,
        project_service: Any = None,
        executor: Any = None,
        max_video_bytes: int = MAX_VIDEO_BYTES,
    ):
        self.jobs_file = Path(jobs_file)
        self.uploads_dir = Path(uploads_dir)
        self.provider = provider
        self.artifact_service = artifact_service
        self.session_service = session_service
        self.project_service = project_service
        self.max_video_bytes = int(max_video_bytes)
        self._lock = threading.RLock()
        self._executor = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix="nova-video")
        self.jobs_file.parent.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self._recover_interrupted_jobs()

    def _read(self) -> dict:
        if not self.jobs_file.exists():
            return {"jobs": []}
        try:
            data = json.loads(self.jobs_file.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Unable to read video job store: {self.jobs_file}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            raise ValueError("Video job store has an invalid shape")
        return data

    def _write(self, data: dict) -> None:
        self.jobs_file.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix="nova-video-", suffix=".json", dir=str(self.jobs_file.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, self.jobs_file)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def _recover_interrupted_jobs(self) -> None:
        with self._lock:
            store = self._read()
            changed = False
            for job in store["jobs"]:
                if job.get("status") in {"queued", "generating"}:
                    job.update({
                        "status": "failed",
                        "error_category": "interrupted",
                        "user_error": "Video generation was interrupted when Nova restarted. Start a new request to try again.",
                        "completed_at": _now(),
                        "updated_at": _now(),
                    })
                    changed = True
            if changed:
                self._write(store)

    def _find(self, job_id: str) -> dict | None:
        return next((job for job in self._read()["jobs"] if job.get("id") == job_id), None)

    def _update(self, job_id: str, updates: dict) -> dict | None:
        with self._lock:
            store = self._read()
            for job in store["jobs"]:
                if job.get("id") == job_id:
                    job.update(updates)
                    job["updated_at"] = _now()
                    self._write(store)
                    return dict(job)
        return None

    def _public(self, job: dict) -> dict:
        allowed = (
            "id", "provider", "prompt", "status", "progress", "created_at",
            "updated_at", "completed_at", "duration_seconds", "aspect_ratio",
            "resolution", "artifact_id", "error_category", "user_error", "session_id",
        )
        return {key: job[key] for key in allowed if key in job}

    def create_job(
        self,
        *,
        prompt: str,
        owner_id: str,
        session_id: str,
        assistant_message_id: str,
        project_id: str = "",
    ) -> dict:
        prompt = str(prompt or "").strip()
        owner_id = str(owner_id or "").strip()
        session_id = str(session_id or "").strip()
        if not owner_id:
            raise PermissionError("Authenticated user required")
        if not prompt:
            raise ValueError("A video prompt is required")
        if len(prompt) > 4000:
            raise ValueError("Video prompt is too long")
        if not session_id:
            raise ValueError("A conversation is required")

        now = _now()
        job_id = f"video_{uuid.uuid4().hex}"
        job = {
            "id": job_id,
            "owner_id": owner_id,
            "session_id": session_id,
            "assistant_message_id": str(assistant_message_id or ""),
            "project_id": str(project_id or ""),
            "provider": str(getattr(self.provider, "name", "") or "unconfigured"),
            "prompt": prompt,
            "status": "queued" if self.provider is not None else "failed",
            "progress": None,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "duration_seconds": None,
            "aspect_ratio": None,
            "resolution": None,
            "provider_job_id": None,
            "filename": None,
            "artifact_id": None,
            "error_category": None,
            "user_error": None,
            "usage": None,
            "materialized": False,
        }
        if self.provider is None:
            job.update({
                "status": "failed",
                "error_category": "provider_configuration_required",
                "user_error": "Video generation isn't available on this Nova server yet. A video provider must be configured first.",
                "completed_at": now,
            })
        with self._lock:
            store = self._read()
            store["jobs"].append(job)
            self._write(store)
        if self.provider is not None:
            self._executor.submit(self._run_job, job_id)
        return self._public(job)

    def _validate_output(self, result: Any) -> tuple[bytes, dict]:
        if not isinstance(result, dict):
            raise ValueError("Provider returned an invalid result")
        content = result.get("video_bytes")
        if not isinstance(content, (bytes, bytearray)) or not content:
            raise ValueError("Provider returned no video bytes")
        content = bytes(content)
        if len(content) > self.max_video_bytes:
            raise ValueError("Generated video exceeds the allowed size")
        mime = str(result.get("mime_type") or "").lower().split(";", 1)[0].strip()
        if mime != "video/mp4" or len(content) < 12 or content[4:8] != b"ftyp":
            raise ValueError("Provider output is not a valid MP4 container")
        return content, result

    def _run_job(self, job_id: str) -> None:
        job = self._find(job_id)
        if not job or job.get("status") != "queued":
            return
        self._update(job_id, {"status": "generating", "progress": None})
        try:
            result = self.provider.generate(str(job["prompt"]))
            content, metadata = self._validate_output(result)
            filename = f"nova_video_{uuid.uuid4().hex}.mp4"
            destination = self.uploads_dir / filename
            fd, temp_name = tempfile.mkstemp(prefix="nova-video-", suffix=".mp4", dir=str(self.uploads_dir))
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp_name, destination)
            finally:
                try:
                    os.unlink(temp_name)
                except FileNotFoundError:
                    pass
            now = _now()
            self._update(job_id, {
                "status": "completed",
                "filename": filename,
                "completed_at": now,
                "progress": None,
                "duration_seconds": metadata.get("duration_seconds") if isinstance(metadata.get("duration_seconds"), (int, float)) else None,
                "aspect_ratio": str(metadata.get("aspect_ratio") or "")[:32] or None,
                "resolution": str(metadata.get("resolution") or "")[:32] or None,
                "usage": metadata.get("usage") if isinstance(metadata.get("usage"), dict) else None,
            })
        except Exception as exc:
            LOGGER.exception("Video generation failed for job %s", job_id)
            category, message = safe_video_error(exc)
            self._update(job_id, {
                "status": "failed",
                "error_category": category,
                "user_error": message,
                "completed_at": _now(),
                "progress": None,
            })

    def _materialize(self, job: dict) -> tuple[dict, dict | None]:
        if job.get("materialized") or job.get("status") not in {"completed", "failed"}:
            return job, None
        with self._lock:
            current = self._find(str(job["id"]))
            if not current or current.get("materialized"):
                return current or job, None
            message = {
                "id": current.get("assistant_message_id") or f"msg_{uuid.uuid4().hex}",
                "role": "assistant",
                "text": current.get("user_error") or "Your video is ready.",
                "content": current.get("user_error") or "Your video is ready.",
                "attachments": [],
                "meta": {
                    "route": "video_generation",
                    "video_job_id": current["id"],
                    "video_status": current["status"],
                    "artifact_id": None,
                    "error_category": current.get("error_category"),
                },
            }
            if current.get("status") == "completed":
                video_url = f"/api/video/jobs/{current['id']}/content"
                artifact = None
                if self.artifact_service is not None:
                    artifact = self.artifact_service.save_artifact({
                        "kind": "video_generation",
                        "type": "video_generation",
                        "title": "Generated video",
                        "body": current.get("prompt", ""),
                        "preview": "Generated video",
                        "session_id": current.get("session_id", ""),
                        "project_id": current.get("project_id", "") or None,
                        "video_url": video_url,
                        "meta": {
                            "prompt": current.get("prompt", ""),
                            "provider": current.get("provider", ""),
                            "filename": current.get("filename", ""),
                            "mime_type": "video/mp4",
                            "video_url": video_url,
                            "project_id": current.get("project_id", "") or None,
                            "video_job_id": current["id"],
                            "usage": current.get("usage"),
                        },
                    }, owner_id=current.get("owner_id"))
                artifact_id = artifact.get("id") if isinstance(artifact, dict) else None
                message.update({
                    "text": "Your video is ready.",
                    "content": "Your video is ready.",
                    "attachments": [{
                        "type": "video",
                        "kind": "video",
                        "title": "Generated video",
                        "url": video_url,
                        "mime_type": "video/mp4",
                        "artifact_id": artifact_id,
                    }],
                    "meta": {
                        "route": "video_generation",
                        "video_job_id": current["id"],
                        "video_status": "completed",
                        "artifact_id": artifact_id,
                        "project_id": current.get("project_id") or None,
                    },
                })
                current = self._update(current["id"], {
                    "artifact_id": artifact_id,
                    "materialized": True,
                }) or current
            else:
                current = self._update(current["id"], {"materialized": True}) or current

            if self.session_service is not None and current.get("session_id"):
                saved_message = self.session_service.replace_message(
                    current["session_id"],
                    current.get("assistant_message_id", ""),
                    message,
                    user_id=current.get("owner_id", ""),
                )
                if saved_message:
                    message = saved_message
            return current, message

    def get_job(self, job_id: str, owner_id: str) -> dict | None:
        owner_id = str(owner_id or "").strip()
        if not owner_id:
            return None
        with self._lock:
            job = self._find(str(job_id or ""))
            if not job or job.get("owner_id") != owner_id:
                return None
            job, message = self._materialize(job)
        response = self._public(job)
        if message:
            response["assistant_message"] = message
        return response

    def content_path(self, job_id: str, owner_id: str) -> Path | None:
        job = self.get_job(job_id, owner_id)
        if not job or job.get("status") != "completed":
            return None
        with self._lock:
            record = self._find(job_id)
            filename = str(record.get("filename") or "") if record else ""
        if not filename or Path(filename).name != filename or not filename.endswith(".mp4"):
            return None
        candidate = (self.uploads_dir / filename).resolve()
        try:
            candidate.relative_to(self.uploads_dir.resolve())
        except ValueError:
            return None
        return candidate if candidate.is_file() else None

    def install_routes(self, app) -> None:
        @app.get("/api/video/jobs/<job_id>")
        def api_video_job(job_id: str):
            owner_id = get_current_user_id()
            if not owner_id:
                return jsonify({"ok": False, "error": "authentication_required"}), 401
            job = self.get_job(job_id, owner_id)
            if not job:
                return jsonify({"ok": False, "error": "video_job_not_found"}), 404
            return jsonify({"ok": True, "job": job})

        @app.get("/api/video/jobs/<job_id>/content")
        def api_video_job_content(job_id: str):
            owner_id = get_current_user_id()
            if not owner_id:
                return jsonify({"ok": False, "error": "authentication_required"}), 401
            path = self.content_path(job_id, owner_id)
            if path is None:
                return jsonify({"ok": False, "error": "video_not_found"}), 404
            return send_file(path, mimetype="video/mp4", as_attachment=False, conditional=True, download_name="nova-video.mp4")
