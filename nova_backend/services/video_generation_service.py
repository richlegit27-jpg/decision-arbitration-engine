from __future__ import annotations

import json
import hashlib
import hmac
import logging
import os
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, urlsplit

from flask import jsonify, send_file
from flask import request

from nova_backend.services.auth_context import get_current_user_id


LOGGER = logging.getLogger("nova.video")
MAX_VIDEO_BYTES = 200 * 1024 * 1024
MAX_REFERENCE_IMAGE_BYTES = 20 * 1024 * 1024


class VideoGenerationError(Exception):
    """Provider adapter error with a safe, stable failure category."""

    def __init__(self, category: str, message: str = ""):
        super().__init__(message or category)
        self.category = category


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_usage(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    allowed = {"input_tokens", "output_tokens", "total_tokens", "duration_seconds", "cost_usd"}
    result = {
        key: number
        for key, number in value.items()
        if key in allowed and isinstance(number, (int, float)) and not isinstance(number, bool)
    }
    return result or None


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
    if category == "budget_exhausted":
        return "provider_budget_exhausted", "Video generation couldn't start because the video provider account doesn't have enough credits. Please try again later."
    if category in {"invalid_input", "image_ownership"}:
        return "invalid_input", "Nova couldn't use that video request or reference image. Check the image and try again."
    if category == "rate_limit" or "rate limit" in detail or "too many requests" in detail:
        return "rate_limited", "The video service is busy right now. Please try again shortly."
    if isinstance(error, (ConnectionError, OSError)) or category == "unavailable":
        return "provider_unavailable", "The video service is temporarily unavailable. Please try again later."
    return "generation_failed", "Nova couldn't finish generating that video. Please try again."


class VideoGenerationService:
    """Durable, owner-scoped asynchronous text-to-video job boundary.

    Providers may expose the async submit/poll/download contract or the legacy
    ``generate(prompt)`` test adapter. Provider state and Nova output storage are
    kept separate so additional providers can use the same durable job boundary.
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
        upload_ownership_service: Any = None,
        reference_signing_key: str | bytes | None = None,
        public_url: str | None = None,
        provider_unavailable_message: str = "Video generation isn't available on this Nova server yet. A video provider must be configured first.",
        executor: Any = None,
        poll_wait: Callable[[float], None] | None = None,
        poll_attempts: int = 60,
        max_video_bytes: int = MAX_VIDEO_BYTES,
    ):
        self.jobs_file = Path(jobs_file)
        self.uploads_dir = Path(uploads_dir)
        self.provider = provider
        self.artifact_service = artifact_service
        self.session_service = session_service
        self.project_service = project_service
        self.upload_ownership_service = upload_ownership_service
        self.reference_signing_key = reference_signing_key
        self.public_url = str(public_url or os.getenv("NOVA_PUBLIC_URL", "")).strip().rstrip("/")
        self.provider_unavailable_message = str(provider_unavailable_message or "Video generation is unavailable on this server.")
        self.max_video_bytes = int(max_video_bytes)
        self.poll_wait = poll_wait or time.sleep
        self.poll_attempts = max(1, int(poll_attempts))
        self._lock = threading.RLock()
        self._executor = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix="nova-video")
        self.jobs_file.parent.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        for job_id in self._recover_interrupted_jobs():
            self._executor.submit(self._run_job, job_id)

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

    def _recover_interrupted_jobs(self) -> list[str]:
        with self._lock:
            store = self._read()
            changed = False
            recoverable = []
            for job in store["jobs"]:
                if job.get("status") in {"queued", "generating"}:
                    provider_job_id = str(job.get("provider_job_id") or "").strip()
                    same_provider = str(job.get("provider") or "") == str(getattr(self.provider, "name", "") or "")
                    can_resume_poll = bool(provider_job_id and same_provider and self.provider is not None and hasattr(self.provider, "get_generation"))
                    if can_resume_poll:
                        job.update({"status": "queued", "recovered": True, "updated_at": _now()})
                        recoverable.append(str(job.get("id") or ""))
                    else:
                        job.update({
                            "status": "failed",
                            "error_category": "interrupted",
                            "user_error": "Video generation was interrupted when Nova restarted before it could save a resumable provider job. Start a new request to try again.",
                            "completed_at": _now(),
                            "updated_at": _now(),
                        })
                    changed = True
            if changed:
                self._write(store)
            return [job_id for job_id in recoverable if job_id]

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
            "id", "provider", "model", "prompt", "status", "progress", "created_at",
            "updated_at", "completed_at", "duration_seconds", "aspect_ratio",
            "resolution", "artifact_id", "error_category", "user_error", "session_id",
            "assistant_message_id",
        )
        return {key: job[key] for key in allowed if key in job}

    @staticmethod
    def _is_image_attachment(item: Any) -> bool:
        if not isinstance(item, dict):
            return False
        mime = str(item.get("mime_type") or item.get("content_type") or item.get("mime") or item.get("type") or "").lower()
        name = str(item.get("original_filename") or item.get("filename") or item.get("name") or "").lower()
        return mime.startswith("image") or name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))

    def _resolve_source_image(self, attachments: list, owner_id: str) -> dict | None:
        images = [item for item in attachments if self._is_image_attachment(item)]
        if not images:
            return None
        item = images[0]
        raw_url = str(item.get("file_url") or item.get("url") or "").strip()
        prefix = "/api/uploads/"
        if not raw_url.startswith(prefix):
            raise VideoGenerationError("image_ownership", "Image must be an owned Nova upload")
        filename = raw_url[len(prefix):].split("?", 1)[0].split("#", 1)[0]
        if not filename or "\\" in filename or Path(filename).name != filename or not self.upload_ownership_service:
            raise VideoGenerationError("image_ownership", "Image must be an owned Nova upload")
        if not self.upload_ownership_service.belongs_to_user(filename, owner_id):
            raise VideoGenerationError("image_ownership", "Image is not available to this user")
        image_path = (self.uploads_dir / filename).resolve()
        try:
            image_path.relative_to(self.uploads_dir.resolve())
        except ValueError as exc:
            raise VideoGenerationError("image_ownership", "Invalid upload path") from exc
        if not image_path.is_file() or image_path.stat().st_size > MAX_REFERENCE_IMAGE_BYTES:
            raise VideoGenerationError("invalid_input", "Image is missing or exceeds the size limit")
        data = image_path.read_bytes()
        signatures = (
            (b"\x89PNG\r\n\x1a\n", "image/png"),
            (b"\xff\xd8\xff", "image/jpeg"),
            (b"GIF87a", "image/gif"),
            (b"GIF89a", "image/gif"),
        )
        detected = next((mime for signature, mime in signatures if data.startswith(signature)), None)
        if not detected and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            detected = "image/webp"
        if not detected:
            raise VideoGenerationError("invalid_input", "The selected upload is not a supported image")
        return {"filename": filename, "mime_type": detected}

    def _reference_signature(self, job: dict, expires: int) -> str:
        secret = self.reference_signing_key
        if isinstance(secret, str):
            secret = secret.encode("utf-8")
        if not secret:
            raise VideoGenerationError("configuration", "Image-to-video requires a configured signing key")
        contents = "|".join((job["id"], job["owner_id"], job["source_image"]["filename"], str(expires)))
        return hmac.new(secret, contents.encode("utf-8"), hashlib.sha256).hexdigest()

    def _reference_url(self, job: dict) -> str:
        parts = urlsplit(self.public_url)
        try:
            valid_port = parts.port in (None, 443)
        except ValueError:
            valid_port = False
        if (
            parts.scheme != "https" or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment or not valid_port
        ):
            raise VideoGenerationError("configuration", "Image-to-video requires NOVA_PUBLIC_URL with HTTPS")
        expires = int(job.get("reference_expires_at") or 0)
        signature = self._reference_signature(job, expires)
        return f"{self.public_url}/api/video/reference/{quote(job['id'])}?expires={expires}&signature={signature}"

    def create_job(
        self,
        *,
        prompt: str,
        owner_id: str,
        session_id: str,
        assistant_message_id: str,
        project_id: str = "",
        attachments: list | None = None,
        model: str = "ray-3.2",
        aspect_ratio: str = "16:9",
        resolution: str = "720p",
        duration: str = "5s",
        idempotency_key: str = "",
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
        idempotency_key = str(idempotency_key or "").strip()[:200]

        session_error = False
        get_session = getattr(self.session_service, "get_session", None)
        if callable(get_session):
            try:
                session_error = not isinstance(get_session(session_id, user_id=owner_id), dict)
            except Exception:
                LOGGER.exception("Video conversation ownership check failed")
                session_error = True

        source_image = None
        image_error = None
        try:
            source_image = self._resolve_source_image(attachments or [], owner_id)
        except VideoGenerationError as exc:
            image_error = exc
        if source_image and self.provider is not None:
            try:
                self._reference_signature({"id": "preflight", "owner_id": owner_id, "source_image": source_image}, int(time.time()) + 3600)
                parts = urlsplit(self.public_url)
                if parts.scheme != "https" or not parts.hostname:
                    raise VideoGenerationError("configuration", "Image-to-video requires NOVA_PUBLIC_URL with HTTPS")
            except VideoGenerationError as exc:
                image_error = exc

        now = _now()
        job_id = f"video_{uuid.uuid4().hex}"
        job = {
            "id": job_id,
            "owner_id": owner_id,
            "session_id": session_id,
            "assistant_message_id": str(assistant_message_id or ""),
            "project_id": str(project_id or ""),
            "provider": str(getattr(self.provider, "name", "") or "unconfigured"),
            "model": str(model or "ray-3.2"),
            "prompt": prompt,
            "status": "queued" if self.provider is not None and image_error is None and not session_error else "failed",
            "progress": None,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "duration_seconds": None,
            "aspect_ratio": str(aspect_ratio or "16:9"),
            "resolution": str(resolution or "720p"),
            "duration_seconds": 5 if str(duration or "5s") == "5s" else 10,
            "duration_option": str(duration or "5s"),
            "source_image": source_image,
            "reference_expires_at": int(time.time()) + 3600 if source_image else None,
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
                "user_error": self.provider_unavailable_message,
                "completed_at": now,
            })
        if image_error is not None:
            category, message = safe_video_error(image_error)
            if getattr(image_error, "category", "") == "image_ownership":
                category, message = "image_ownership", "I couldn't use that image. Attach an image from your account to this conversation and try again."
            job.update({"status": "failed", "error_category": category, "user_error": message, "completed_at": now})
        if session_error:
            job.update({
                "status": "failed",
                "error_category": "conversation_unavailable",
                "user_error": "I couldn't attach video generation to this conversation. Refresh the conversation and try again.",
                "completed_at": now,
            })
        with self._lock:
            store = self._read()
            if idempotency_key:
                duplicate = next((
                    existing for existing in store["jobs"]
                    if existing.get("owner_id") == owner_id
                    and existing.get("session_id") == session_id
                    and existing.get("idempotency_key") == idempotency_key
                ), None)
                if duplicate:
                    return self._public(duplicate)
                job["idempotency_key"] = idempotency_key
            store["jobs"].append(job)
            self._write(store)
        if self.provider is not None and image_error is None and not session_error:
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
        box_size = int.from_bytes(content[:4], "big") if len(content) >= 4 else 0
        if (
            mime != "video/mp4"
            or len(content) < 16
            or content[4:8] != b"ftyp"
            or box_size < 16
            or box_size > len(content)
            or not content[8:12].strip(b"\x00")
        ):
            raise ValueError("Provider output is not a valid MP4 container")
        return content, result

    def _run_job(self, job_id: str) -> None:
        job = self._find(job_id)
        if not job or job.get("status") != "queued":
            return
        self._update(job_id, {"status": "generating", "progress": None})
        try:
            if hasattr(self.provider, "submit_generation"):
                if job.get("provider_job_id"):
                    result = self._poll_provider_job(job, str(job["provider_job_id"]))
                else:
                    result = self._run_provider_job(job)
            else:
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
                "usage": _safe_usage(metadata.get("usage")),
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

    def _run_provider_job(self, job: dict) -> dict:
        source_image = job.get("source_image")
        if source_image:
            refreshed_expiry = int(time.time()) + 3600
            job = self._update(job["id"], {"reference_expires_at": refreshed_expiry}) or job
        image_url = self._reference_url(job) if source_image else ""
        submitted = self.provider.submit_generation(
            str(job["prompt"]),
            model=str(job.get("model") or "ray-3.2"),
            aspect_ratio=str(job.get("aspect_ratio") or "16:9"),
            resolution=str(job.get("resolution") or "720p"),
            duration=str(job.get("duration_option") or "5s"),
            image_url=image_url,
        )
        provider_job_id = str((submitted or {}).get("id") or "").strip()
        if not provider_job_id:
            raise VideoGenerationError("invalid_response", "Provider omitted generation ID")
        self._update(job["id"], {"provider_job_id": provider_job_id, "provider_state": str(submitted.get("state") or "queued")})
        return self._poll_provider_job(job, provider_job_id)

    def _poll_provider_job(self, job: dict, provider_job_id: str) -> dict:
        wait_seconds = 2.0
        for attempt in range(self.poll_attempts):
            if attempt:
                self.poll_wait(wait_seconds)
                wait_seconds = min(15.0, wait_seconds * 1.5)
            status = self.provider.get_generation(provider_job_id)
            state = str(status.get("state") or status.get("status") or "").lower()
            self._update(job["id"], {"provider_state": state})
            if state in {"failed", "error", "cancelled", "canceled"}:
                failure_code = str(status.get("failure_code") or "").lower()
                reason = str(status.get("failure_reason") or failure_code or status.get("error") or state)
                lowered = reason.lower()
                category = (
                    "safety" if failure_code == "content_moderated" or any(term in lowered for term in ("moderation", "safety", "policy"))
                    else "budget_exhausted" if failure_code == "rate_limit.budget.exceeded" or any(term in lowered for term in ("rate_limit.budget.exceeded", "insufficient credits", "not enough credits", "budget exceeded"))
                    else "rate_limit" if "rate_limit" in lowered or "rate limit" in lowered
                    else "generation_failed"
                )
                raise VideoGenerationError(category, reason)
            if state in {"completed", "complete", "succeeded"}:
                outputs = status.get("output") if isinstance(status.get("output"), list) else []
                output_url = next((str(item.get("url") or "") for item in outputs if isinstance(item, dict) and item.get("type") == "video"), "")
                assets = status.get("assets") if isinstance(status.get("assets"), dict) else {}
                video_url = str(output_url or assets.get("video") or status.get("video_url") or "").strip()
                if not video_url:
                    raise VideoGenerationError("invalid_response", "Completed provider response omitted video asset")
                content, mime = self.provider.download_video(video_url, max_bytes=self.max_video_bytes)
                metadata = {
                    "video_bytes": content,
                    "mime_type": mime,
                    "duration_seconds": job.get("duration_seconds"),
                    "aspect_ratio": job.get("aspect_ratio"),
                    "resolution": job.get("resolution"),
                    "usage": status.get("usage") if isinstance(status.get("usage"), dict) else None,
                }
                return metadata
            if state not in {"queued", "pending", "dreaming", "generating", "processing"}:
                raise VideoGenerationError("invalid_response", "Provider returned an unknown generation state")
        raise VideoGenerationError("timeout", "Video generation exceeded the polling limit")

    def _materialize(self, job: dict) -> tuple[dict, dict | None]:
        if job.get("status") not in {"completed", "failed"}:
            return job, None
        with self._lock:
            current = self._find(str(job["id"]))
            if not current:
                return job, None
            if current.get("materialized"):
                message = current.get("final_message")
                self._persist_final_message(current, message)
                return current, message

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
                try:
                    if self.artifact_service is None:
                        raise RuntimeError("Artifact service is unavailable")
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
                            "model": current.get("model", ""),
                            "aspect_ratio": current.get("aspect_ratio"),
                            "duration_seconds": current.get("duration_seconds"),
                            "source_image": current.get("source_image"),
                            "filename": current.get("filename", ""),
                            "mime_type": "video/mp4",
                            "video_url": video_url,
                            "project_id": current.get("project_id", "") or None,
                            "video_job_id": current["id"],
                            "usage": _safe_usage(current.get("usage")),
                        },
                    }, owner_id=current.get("owner_id"))
                    if not isinstance(artifact, dict) or not artifact.get("id"):
                        raise RuntimeError("Artifact was not persisted")
                except Exception:
                    LOGGER.exception("Video artifact persistence failed for job %s", current["id"])
                    filename = str(current.get("filename") or "")
                    if filename and Path(filename).name == filename:
                        try:
                            (self.uploads_dir / filename).unlink(missing_ok=True)
                        except OSError:
                            LOGGER.exception("Could not remove unreferenced video output for job %s", current["id"])
                    current = self._update(current["id"], {
                        "status": "failed",
                        "filename": None,
                        "error_category": "storage_failure",
                        "user_error": "Nova generated the video but couldn't save it to your conversation. Please try again.",
                        "completed_at": _now(),
                    }) or current
                    message.update({
                        "text": current["user_error"],
                        "content": current["user_error"],
                        "meta": {
                            "route": "video_generation",
                            "video_job_id": current["id"],
                            "video_status": "failed",
                            "error_category": "storage_failure",
                        },
                    })
                    current = self._update(current["id"], {
                        "materialized": True,
                        "final_message": message,
                    }) or current
                    self._persist_final_message(current, message)
                    return current, message

                artifact_id = artifact["id"]
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
                    "final_message": message,
                }) or current
            else:
                current = self._update(current["id"], {
                    "materialized": True,
                    "final_message": message,
                }) or current
            self._persist_final_message(current, message)
            return current, message

    def _persist_final_message(self, job: dict, message: dict | None) -> None:
        if not isinstance(message, dict) or self.session_service is None or not job.get("session_id"):
            return
        try:
            self.session_service.replace_message(
                job["session_id"],
                job.get("assistant_message_id", ""),
                message,
                user_id=job.get("owner_id", ""),
            )
        except Exception:
            LOGGER.exception("Video result conversation update failed for job %s", job.get("id"))

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
        @app.get("/api/video/reference/<job_id>")
        def api_video_reference(job_id: str):
            try:
                expires = int(str(request.args.get("expires") or "0"))
                signature = str(request.args.get("signature") or "")
                with self._lock:
                    job = self._find(job_id)
                now = int(time.time())
                if not job or not job.get("source_image") or expires != int(job.get("reference_expires_at") or 0):
                    return jsonify({"ok": False, "error": "image_reference_not_found"}), 404
                if expires < now or expires > now + 3600 or not hmac.compare_digest(signature, self._reference_signature(job, expires)):
                    return jsonify({"ok": False, "error": "image_reference_expired"}), 404
                filename = str(job["source_image"].get("filename") or "")
                if Path(filename).name != filename or not self.upload_ownership_service or not self.upload_ownership_service.belongs_to_user(filename, str(job.get("owner_id") or "")):
                    return jsonify({"ok": False, "error": "image_reference_not_found"}), 404
                candidate = (self.uploads_dir / filename).resolve()
                candidate.relative_to(self.uploads_dir.resolve())
                if not candidate.is_file() or candidate.stat().st_size > MAX_REFERENCE_IMAGE_BYTES:
                    return jsonify({"ok": False, "error": "image_reference_not_found"}), 404
                mime = str(job["source_image"].get("mime_type") or "image/jpeg")
                response = send_file(candidate, mimetype=mime, as_attachment=False, conditional=True)
                response.headers["Cache-Control"] = "private, no-store, max-age=0"
                response.headers["X-Content-Type-Options"] = "nosniff"
                return response
            except Exception:
                LOGGER.exception("Signed video reference request rejected")
                return jsonify({"ok": False, "error": "image_reference_not_found"}), 404

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
