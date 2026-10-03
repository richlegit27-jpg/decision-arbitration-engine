"""Luma Agents API adapter for Nova's provider-neutral video jobs."""
from __future__ import annotations

import json
import ipaddress
import socket
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from nova_backend.services.video_generation_service import VideoGenerationError


API_ROOT = "https://agents.lumalabs.ai/v1"
SUPPORTED_MODELS = {"ray-3.2"}
SUPPORTED_ASPECT_RATIOS = {"9:16", "3:4", "1:1", "4:3", "16:9", "21:9"}
SUPPORTED_RESOLUTIONS = {"540p", "720p", "1080p"}
SUPPORTED_DURATIONS = {"5s", "10s"}


class LumaVideoProvider:
    name = "luma"

    def __init__(self, api_key: str | None = None, *, opener=None, timeout: int = 30):
        import os

        self.api_key = str(api_key if api_key is not None else (
            os.getenv("LUMA_AGENTS_API_KEY") or os.getenv("LUMA_API_KEY") or ""
        )).strip()
        self.opener = opener or urllib.request.urlopen
        self.timeout = max(1, int(timeout))

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _provider_error(status: int, body: bytes) -> VideoGenerationError:
        detail = body.decode("utf-8", errors="replace")[:4000]
        lowered = detail.lower()
        if status == 402 or any(
            marker in lowered
            for marker in ("rate_limit.budget.exceeded", "insufficient credits", "not enough credits", "budget exceeded")
        ):
            return VideoGenerationError("budget_exhausted", detail)
        if any(word in lowered for word in ("moderation", "safety", "policy_violation", "content_policy")):
            return VideoGenerationError("safety", detail)
        if status in {401, 403}:
            return VideoGenerationError("authentication", detail)
        if status == 429:
            return VideoGenerationError("rate_limit", detail)
        if status >= 500:
            return VideoGenerationError("unavailable", detail)
        return VideoGenerationError("invalid_input", detail)

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        if not self.api_key:
            raise VideoGenerationError("configuration", "LUMA_AGENTS_API_KEY is not configured")
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{API_ROOT}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                response_body = response.read(1024 * 1024 + 1)
                if len(response_body) > 1024 * 1024:
                    raise VideoGenerationError("invalid_response", "Provider response exceeded limit")
                status = getattr(response, "status", 200)
        except urllib.error.HTTPError as exc:
            raise self._provider_error(exc.code, exc.read(4000)) from exc
        except TimeoutError as exc:
            raise VideoGenerationError("timeout", str(exc)) from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError):
                raise VideoGenerationError("timeout", str(reason)) from exc
            raise VideoGenerationError("unavailable", str(reason)) from exc
        except OSError as exc:
            raise VideoGenerationError("unavailable", str(exc)) from exc
        if status < 200 or status >= 300:
            raise self._provider_error(status, response_body)
        try:
            result = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VideoGenerationError("invalid_response", "Provider returned invalid JSON") from exc
        if not isinstance(result, dict):
            raise VideoGenerationError("invalid_response", "Provider returned an invalid response")
        return result

    @staticmethod
    def _validate_image_url(image_url: str) -> str:
        parts = urlsplit(str(image_url or ""))
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise VideoGenerationError("invalid_input", "Image reference must be an HTTPS URL")
        return image_url

    def submit_generation(
        self,
        prompt: str,
        *,
        model: str = "ray-3.2",
        aspect_ratio: str = "16:9",
        resolution: str = "720p",
        duration: str = "5s",
        image_url: str = "",
    ) -> dict:
        if model not in SUPPORTED_MODELS:
            raise VideoGenerationError("invalid_input", "Unsupported Luma video model")
        if aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
            raise VideoGenerationError("invalid_input", "Unsupported video aspect ratio")
        if resolution not in SUPPORTED_RESOLUTIONS:
            raise VideoGenerationError("invalid_input", "Unsupported video resolution")
        if duration not in SUPPORTED_DURATIONS:
            raise VideoGenerationError("invalid_input", "Unsupported video duration")
        payload: dict[str, Any] = {
            "prompt": prompt,
            "model": model,
            "type": "video",
            "aspect_ratio": aspect_ratio,
            "video": {"resolution": resolution, "duration": duration},
        }
        if image_url:
            payload["video"]["start_frame"] = {"url": self._validate_image_url(image_url)}
        result = self._request("POST", "/generations", payload)
        generation_id = str(result.get("id") or "").strip()
        try:
            generation_id = str(UUID(generation_id))
        except (ValueError, AttributeError, TypeError):
            raise VideoGenerationError("invalid_response", "Provider response omitted its generation ID")
        return {"id": generation_id, "state": str(result.get("state") or "queued")}

    def get_generation(self, generation_id: str) -> dict:
        try:
            generation_id = str(UUID(str(generation_id or "")))
        except (ValueError, AttributeError, TypeError):
            raise VideoGenerationError("invalid_response", "Invalid provider generation ID")
        return self._request("GET", f"/generations/{generation_id}")

    def download_video(self, url: str, *, max_bytes: int) -> tuple[bytes, str]:
        parts = urlsplit(str(url or ""))
        host = str(parts.hostname or "").lower().rstrip(".")
        allowed_host = (
            host == "storage.cdn-luma.com"
            or host.endswith(".cdn-luma.com")
            or host == "lumalabs.ai"
            or host.endswith(".lumalabs.ai")
            or host.endswith(".amazonaws.com")
        )
        if parts.scheme != "https" or not allowed_host or parts.username or parts.password or parts.port not in (None, 443):
            raise VideoGenerationError("invalid_response", "Provider returned an untrusted video URL")
        try:
            addresses = {result[4][0] for result in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
            if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
                raise VideoGenerationError("invalid_response", "Provider video host did not resolve publicly")
        except VideoGenerationError:
            raise
        except (OSError, ValueError) as exc:
            raise VideoGenerationError("unavailable", "Provider video host could not be verified") from exc
        request = urllib.request.Request(url, headers={"Accept": "video/mp4"})
        safe_opener = urllib.request.build_opener(_NoRedirectHandler())
        try:
            with safe_opener.open(request, timeout=self.timeout) as response:
                mime = str(response.headers.get("Content-Type", "")).split(";", 1)[0].strip().lower()
                if mime != "video/mp4":
                    raise VideoGenerationError("invalid_response", "Provider video had an unexpected content type")
                content = response.read(max_bytes + 1)
                if len(content) > max_bytes:
                    raise VideoGenerationError("invalid_response", "Provider video exceeded the size limit")
                return content, mime
        except VideoGenerationError:
            raise
        except urllib.error.HTTPError as exc:
            raise self._provider_error(exc.code, exc.read(4000)) from exc
        except urllib.error.URLError as exc:
            raise VideoGenerationError("unavailable", str(getattr(exc, "reason", exc))) from exc
        except OSError as exc:
            raise VideoGenerationError("unavailable", str(exc)) from exc


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, new_url):
        return None

