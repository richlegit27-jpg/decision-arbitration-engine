from __future__ import annotations

import base64
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List
  
from openai import OpenAI

from nova_backend.models.session import new_message
from nova_backend.services.agent_service import AgentService
from nova_backend.services.artifact_service import ArtifactService
from nova_backend.services.autonomy_service import AutonomyService
from nova_backend.services.memory_ranker_service import MemoryRankerService
from nova_backend.services.memory_service import MemoryService
from nova_backend.services.recon_service import ReconService
from nova_backend.services.session_service import SessionService
from nova_backend.services.web_service import WebService


class ChatService:
    ROUTE_GENERAL_CHAT = "general_chat"
    ROUTE_IMAGE_GENERATION = "image_generation"
    ROUTE_WEB_FETCH = "web_fetch"
    ROUTE_ATTACHMENT_ANALYSIS = "attachment_analysis"
    ROUTE_PLANNING = "planning"
    ROUTE_MEMORY_RECALL = "memory_recall"

    def __init__(
        self,
        session_service: SessionService,
        memory_service: MemoryService,
        artifact_service: ArtifactService,
        web_service: WebService,
        recon_service: ReconService,
    ):
        self.sessions = session_service
        self.memory = memory_service
        self.artifacts = artifact_service
        self.web = web_service
        self.recon = recon_service

        self.image_model = os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1")
        self.image_size = os.getenv("NOVA_IMAGE_SIZE", "1024x1024")
        self.chat_model = os.getenv("OPENAI_MODEL", "gpt-5.4")
        self.memory_limit = int(os.getenv("NOVA_MEMORY_LIMIT", "3"))

        self.uploads_dir = Path(
            os.getenv("UPLOADS_DIR", r"C:\Users\Owner\nova\uploads")
        )
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        print("CHATSERVICE INIT uploads_dir =", self.uploads_dir)

        self.client = OpenAI()
        self.agent = AgentService()
        self.memory_ranker = MemoryRankerService()

        self.autonomy = AutonomyService(
            web_service=self.web,
            recon_service=self.recon,
            memory_service=self.memory,
            artifact_service=self.artifacts,
            max_steps=5,
            max_deep_js=5,
            max_follow_links=5,
        )

    def _clean_artifact_text(self, value: str, limit: int = 300) -> str:
        text = re.sub(r"\s+", " ", self._safe_str(value)).strip()
        if not text:
            return ""
        return text[:limit].strip()

    def _build_image_artifact_description(
        self,
        prompt: str,
        revised_prompt: str = "",
        source_type: str = "generated",
        generation_mode: str = "text_to_image",
    ) -> dict:
        prompt_clean = self._clean_artifact_text(prompt, limit=500)
        revised_clean = self._clean_artifact_text(revised_prompt, limit=500)

        primary = revised_clean or prompt_clean or "Generated image"
        summary = f"Generated image from prompt: {primary}."
        if source_type:
            summary += f" Source type: {self._clean_artifact_text(source_type, limit=80)}."
        if generation_mode:
            summary += f" Mode: {self._clean_artifact_text(generation_mode, limit=80)}."

        body_parts = []
        body_parts.append(f"Prompt: {prompt_clean or 'N/A'}")
        if revised_clean:
            body_parts.append(f"Revised prompt: {revised_clean}")
        if source_type:
            body_parts.append(f"Source type: {self._clean_artifact_text(source_type, limit=80)}")
        if generation_mode:
            body_parts.append(f"Generation mode: {self._clean_artifact_text(generation_mode, limit=80)}")

        body = "\n".join(body_parts).strip()
        preview = self._clean_artifact_text(summary, limit=140)

        return {
            "summary": self._clean_artifact_text(summary, limit=400),
            "preview": preview,
            "body": body,
        }

    def _upgrade_image_artifact_payload(
        self,
        artifact: dict | None,
        prompt: str,
        revised_prompt: str = "",
        source_type: str = "generated",
        generation_mode: str = "text_to_image",
    ) -> dict:
        artifact = self._safe_dict(artifact)
        meta = self._safe_dict(artifact.get("meta"))
        viewer = self._safe_dict(artifact.get("viewer"))

        description = self._build_image_artifact_description(
            prompt=prompt,
            revised_prompt=revised_prompt,
            source_type=source_type,
            generation_mode=generation_mode,
        )

        image_url = (
            self._safe_str(artifact.get("image_url"))
            or self._safe_str(meta.get("image_url"))
            or self._safe_str(viewer.get("image_url"))
        )

        artifact["kind"] = self._safe_str(artifact.get("kind")) or "image"
        artifact["group"] = self._safe_str(artifact.get("group")) or "Images"
        artifact["title"] = self._safe_str(artifact.get("title")) or "Generated image"
        artifact["summary"] = description["summary"]
        artifact["preview"] = description["preview"]
        artifact["image_url"] = image_url or None
        artifact["source"] = self._safe_str(artifact.get("source")) or "image_generation"

        meta["prompt"] = self._safe_str(meta.get("prompt")) or self._safe_str(prompt)
        meta["revised_prompt"] = self._safe_str(meta.get("revised_prompt")) or self._safe_str(revised_prompt)
        meta["source_type"] = self._safe_str(meta.get("source_type")) or self._safe_str(source_type) or "generated"
        meta["generation_mode"] = self._safe_str(meta.get("generation_mode")) or self._safe_str(generation_mode) or "text_to_image"
        meta["image_url"] = self._safe_str(meta.get("image_url")) or image_url
        meta["artifact_description"] = description["summary"]

        viewer["kind"] = self._safe_str(viewer.get("kind")) or "image"
        viewer["title"] = self._safe_str(viewer.get("title")) or artifact["title"]
        viewer["body"] = description["body"]
        viewer["image_url"] = self._safe_str(viewer.get("image_url")) or image_url
        viewer["source_url"] = self._safe_str(viewer.get("source_url"))
        viewer["filename"] = self._safe_str(viewer.get("filename"))
        viewer["image_missing"] = bool(viewer.get("image_missing", False))
        viewer["media_missing"] = bool(viewer.get("media_missing", False))
        viewer["audio_missing"] = bool(viewer.get("audio_missing", False))
        viewer["video_missing"] = bool(viewer.get("video_missing", False))

        artifact["meta"] = meta
        artifact["viewer"] = viewer
        return artifact

    def _clean_web_text(self, value: str, limit: int = 4000) -> str:
        text = re.sub(r"\s+", " ", self._safe_str(value)).strip()
        if not text:
            return ""
        return text[:limit].strip()

    def _truncate_web_text(self, value: str, limit: int = 240) -> str:
        text = self._clean_web_text(value, limit=max(limit * 3, limit))
        if not text:
            return ""
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _normalize_web_bullets(self, bullets, content: str = "", summary: str = "") -> list[str]:
        cleaned = []
        seen = set()

        if isinstance(bullets, list):
            for item in bullets:
                text = self._truncate_web_text(item, limit=180)
                key = text.lower()
                if text and key not in seen:
                    seen.add(key)
                    cleaned.append(text)

        fallback_pool = []
        if summary:
            fallback_pool.append(summary)
        if content:
            fallback_pool.extend(re.split(r"(?<=[.!?])\s+", self._clean_web_text(content, limit=3000)))

        for piece in fallback_pool:
            text = self._truncate_web_text(piece, limit=180)
            key = text.lower()
            if text and key not in seen:
                seen.add(key)
                cleaned.append(text)
            if len(cleaned) >= 5:
                break

        return cleaned[:5]

    def _build_web_artifact_description(
        self,
        title: str,
        summary: str,
        content: str,
        url: str,
        site_name: str = "",
        domain: str = "",
        bullets=None,
    ) -> dict:
        clean_title = self._clean_web_text(title, limit=200) or "Web result"
        clean_summary = self._clean_web_text(summary, limit=1200)
        clean_content = self._clean_web_text(content, limit=6000)
        clean_url = self._safe_str(url)
        clean_site = self._clean_web_text(site_name, limit=120)
        clean_domain = self._clean_web_text(domain, limit=120)

        bullet_list = self._normalize_web_bullets(
            bullets=bullets,
            content=clean_content,
            summary=clean_summary,
        )

        final_summary = clean_summary
        if not final_summary:
            if bullet_list:
                final_summary = " ".join(bullet_list[:2]).strip()
            elif clean_content:
                final_summary = self._truncate_web_text(clean_content, limit=260)
            else:
                final_summary = f"Fetched {clean_title}"

        preview = self._truncate_web_text(final_summary, limit=140)

        body_parts = []
        body_parts.append(f"Title: {clean_title}")
        if clean_site:
            body_parts.append(f"Site: {clean_site}")
        elif clean_domain:
            body_parts.append(f"Domain: {clean_domain}")
        if clean_url:
            body_parts.append(f"URL: {clean_url}")
        if final_summary:
            body_parts.append(f"Summary: {final_summary}")
        if bullet_list:
            body_parts.append("Key points:")
            body_parts.extend([f"- {item}" for item in bullet_list])
        if clean_content:
            body_parts.append("")
            body_parts.append("Content:")
            body_parts.append(clean_content[:4000])

        return {
            "summary": final_summary,
            "preview": preview,
            "body": "\n".join(body_parts).strip(),
            "bullets": bullet_list,
        }

    def _upgrade_web_artifact_payload(
        self,
        artifact: dict | None,
        result: dict | None,
        url: str = "",
    ) -> dict:
        artifact = self._safe_dict(artifact)
        result = self._safe_dict(result)
        meta = self._safe_dict(artifact.get("meta"))
        viewer = self._safe_dict(artifact.get("viewer"))

        title = (
            self._safe_str(artifact.get("title"))
            or self._safe_str(result.get("title"))
            or self._safe_str(url)
            or "Web result"
        )
        summary = (
            self._safe_str(artifact.get("summary"))
            or self._safe_str(result.get("summary"))
        )
        content = (
            self._safe_str(artifact.get("body"))
            or self._safe_str(result.get("content"))
        )
        source_url = (
            self._safe_str(artifact.get("source_url"))
            or self._safe_str(meta.get("source_url"))
            or self._safe_str(result.get("final_url"))
            or self._safe_str(result.get("url"))
            or self._safe_str(url)
        )
        site_name = self._safe_str(result.get("site_name")) or self._safe_str(meta.get("site_name"))
        domain = self._safe_str(result.get("domain")) or self._safe_str(meta.get("domain"))
        links = self._safe_list(result.get("links")) or self._safe_list(viewer.get("links"))
        images = self._safe_list(result.get("images")) or self._safe_list(viewer.get("images"))
        bullets = (
            self._safe_list(result.get("bullets"))
            or self._safe_list(viewer.get("bullets"))
            or self._safe_list(meta.get("bullets"))
        )

        description = self._build_web_artifact_description(
            title=title,
            summary=summary,
            content=content,
            url=source_url,
            site_name=site_name,
            domain=domain,
            bullets=bullets,
        )

        artifact["kind"] = self._safe_str(artifact.get("kind")) or "web_result"
        artifact["group"] = self._safe_str(artifact.get("group")) or "Web"
        artifact["title"] = self._safe_str(title) or "Web result"
        artifact["summary"] = description["summary"]
        artifact["preview"] = description["preview"]
        artifact["body"] = self._safe_str(artifact.get("body")) or self._safe_str(result.get("content")) or ""
        artifact["source_url"] = source_url
        artifact["source"] = self._safe_str(artifact.get("source")) or "web_fetch"

        meta["source_url"] = source_url
        meta["url"] = self._safe_str(result.get("url")) or source_url
        meta["final_url"] = self._safe_str(result.get("final_url")) or source_url
        meta["site_name"] = site_name
        meta["domain"] = domain
        meta["description"] = self._safe_str(result.get("description")) or self._safe_str(meta.get("description"))
        meta["status_code"] = result.get("status_code", meta.get("status_code"))
        meta["ssl_verified"] = result.get("ssl_verified", meta.get("ssl_verified"))
        meta["bullets"] = description["bullets"]
        meta["artifact_description"] = description["summary"]

        viewer["kind"] = "web_result"
        viewer["title"] = artifact["title"]
        viewer["body"] = description["body"]
        viewer["analysis_text"] = description["summary"]
        viewer["bullets"] = description["bullets"]
        viewer["links"] = links[:10]
        viewer["images"] = images[:12]
        viewer["source_url"] = source_url

        artifact["meta"] = meta
        artifact["viewer"] = viewer
        return artifact

    def _categorize_memory(self, text: str) -> str:
        t = self._safe_str(text).strip().lower()
        if not t:
            return "note"

        # project first so "I'm building ..." does not get caught by "I'm"
        if any(x in t for x in [
            "i'm building",
            "i am building",
            "my project",
            "i'm working on",
            "i am working on",
            "building nova",
            "working on nova",
        ]):
            return "project"

        # goal
        if any(x in t for x in [
            "my goal",
            "i want to",
            "i plan to",
            "i need to finish",
            "i'm trying to",
            "i am trying to",
        ]):
            return "goal"

        # preference
        if any(x in t for x in [
            "i prefer",
            "i like",
            "i usually",
            "i always",
            "my favorite",
            "my favourite",
            "please use",
            "always use",
        ]):
            return "preference"

        # identity / profile last among strong categories
        if any(x in t for x in [
            "my name is",
            "i was",
            "i live",
            "i use ",
            "i work ",
            "i am ",
            "i'm ",
        ]):
            return "profile"

        return "note"

    def _should_auto_inject_memory(self, user_text: str, decision: dict | None = None) -> bool:
        text = self._safe_str(user_text).lower()
        if not text:
            return False

        if not isinstance(decision, dict):
            decision = {}

        if not decision.get("use_memory", True):
            return False

        route = self._safe_str(decision.get("route")).lower()
        if route in {
            self._safe_str(getattr(self, "ROUTE_IMAGE_GENERATION", "")).lower(),
            self._safe_str(getattr(self, "ROUTE_WEB_FETCH", "")).lower(),
            self._safe_str(getattr(self, "ROUTE_ATTACHMENT_ANALYSIS", "")).lower(),
        }:
            return False

        skip_triggers = (
            "/image",
            "generate an image",
            "draw ",
            "make an image",
            "fetch ",
            "http://",
            "https://",
        )
        if any(trigger in text for trigger in skip_triggers):
            return False

        return True

    # ==============================
    # MEMORY INTENT HELPERS
    # ==============================

    def _normalize_memory_text(self, user_text: str) -> str:
        text = self._safe_str(user_text).strip()
        if not text:
            return ""

        prefixes = [
            "remember that ",
            "remember ",
            "note that ",
            "note this ",
            "for future reference ",
            "keep in mind that ",
            "don't forget that ",
            "do not forget that ",
            "save this: ",
            "save this ",
            "store this: ",
            "store this ",
        ]

        lowered = text.lower()
        for prefix in prefixes:
            if lowered.startswith(prefix):
                text = text[len(prefix):].strip()
                break

        text = text.strip(" .:-")
        return text

    def _infer_memory_category(self, memory_text: str) -> str:
        text = self._safe_str(memory_text).strip().lower()
        if not text:
            return "general"

        preference_markers = [
            "i prefer",
            "i like",
            "i love",
            "i want",
            "i need",
            "my favorite",
            "my favourite",
            "always use",
            "please use",
        ]
        profile_markers = [
            "my name is",
            "i am ",
            "i'm ",
            "i live",
            "i work",
            "i use ",
        ]
        project_markers = [
            "i'm building",
            "i am building",
            "my project",
            "i'm working on",
            "i am working on",
            "nova",
            "app",
            "platform",
        ]
        goal_markers = [
            "my goal",
            "i want to finish",
            "i'm trying to",
            "i am trying to",
            "i plan to",
            "i need to finish",
        ]

        if any(marker in text for marker in preference_markers):
            return "preference"
        if any(marker in text for marker in project_markers):
            return "project"
        if any(marker in text for marker in goal_markers):
            return "goal"
        if any(marker in text for marker in profile_markers):
            return "profile"
        return "general"

    def _detect_memory_intent(self, user_text: str) -> dict:
        raw_text = self._safe_str(user_text).strip()
        text = raw_text.lower()

        if not raw_text:
            return {
                "should_force_memory": False,
                "memory_text": "",
                "memory_category": "general",
                "reason": "",
                "confidence": 0.0,
            }

        explicit_prefixes = [
            "remember that ",
            "remember ",
            "note that ",
            "note this ",
            "for future reference ",
            "keep in mind that ",
            "don't forget that ",
            "do not forget that ",
            "save this ",
            "save this: ",
            "store this ",
            "store this: ",
        ]

        explicit_match = any(text.startswith(prefix) for prefix in explicit_prefixes)
        normalized = self._normalize_memory_text(raw_text)
        category = self._infer_memory_category(normalized)

        if explicit_match and normalized:
            return {
                "should_force_memory": True,
                "memory_text": normalized,
                "memory_category": category,
                "reason": "explicit_memory_command",
                "confidence": 1.0,
            }

        auto_markers = [
            "my name is",
            "i prefer",
            "i like",
            "i'm building",
            "i am building",
            "i'm working on",
            "i am working on",
            "my goal",
            "i want to finish",
            "i need",
            "always use",
            "please use",
        ]

        auto_match = any(marker in text for marker in auto_markers)
        if auto_match and normalized:
            return {
                "should_force_memory": True,
                "memory_text": normalized,
                "memory_category": category,
                "reason": "auto_memory_signal",
                "confidence": 0.8,
            }

        return {
            "should_force_memory": False,
            "memory_text": "",
            "memory_category": "general",
            "reason": "",
            "confidence": 0.0,
        }

    def _memory_already_exists(self, memory_text: str) -> bool:
        text = self._safe_str(memory_text).strip().lower()
        if not text:
            return False

        try:
            memory_items = self.memory.get_all_memory()
        except Exception:
            return False

        for item in memory_items or []:
            existing = self._safe_str((item or {}).get("text")).strip().lower()
            if existing == text:
                return True
        return False

    def _write_memory_if_needed(self, decision: dict, session_id: str) -> dict:
        result = {
            "memory_written": False,
            "memory_skipped_duplicate": False,
            "memory_error": "",
        }

        should_force = bool((decision or {}).get("should_force_memory"))
        memory_text = self._safe_str((decision or {}).get("memory_text")).strip()
        memory_category = self._safe_str((decision or {}).get("memory_category")).strip() or "general"

        if not should_force or not memory_text:
            return result

        try:
            if self._memory_already_exists(memory_text):
                result["memory_skipped_duplicate"] = True
                return result

            self.memory.add_memory(
                text=memory_text,
                kind=memory_category,
                source="router_auto",
                session_id=session_id or "",
            )
            result["memory_written"] = True
            return result
        except Exception as e:
            result["memory_error"] = str(e)
            return result

    # ==============================
    # CORE TIME / TEXT HELPERS
    # ==============================

    def _iso_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _clean_execution_text(self, value: str | None) -> str:
        text = str(value or "").strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    def _safe_str(self, value: Any) -> str:
        return str(value or "").strip()

    def _clean_text(self, value: str | None) -> str:
        text = str(value or "")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _safe_list(self, value: Any) -> list:
        return value if isinstance(value, list) else []

    def _safe_dict(self, value: Any) -> dict:
        return value if isinstance(value, dict) else {}

    def _call_first(self, obj: Any, method_names: list[str], *args, **kwargs):
        for name in method_names:
            method = getattr(obj, name, None)
            if callable(method):
                try:
                    return method(*args, **kwargs)
                except TypeError:
                    continue
        return None

    def _extract_response_text(self, resp) -> str:
        try:
            output_text = getattr(resp, "output_text", None)
            if output_text:
                return str(output_text).strip()
        except Exception:
            pass

        try:
            data = resp.model_dump()
        except Exception:
            data = None

        if isinstance(data, dict):
            text_parts = []
            output = data.get("output") or []
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content") or []
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if part.get("type") in ("output_text", "text"):
                        text_value = part.get("text")
                        if text_value:
                            text_parts.append(str(text_value))
            if text_parts:
                return "\n".join(text_parts).strip()

        return "I’m here, but the model returned an empty response."

    # ==============================
    # DECISION CONTRACT
    # ==============================

    def _looks_like_url(self, text: str) -> bool:
        t = self._safe_str(text).lower()
        if not t:
            return False
        if "http://" in t or "https://" in t:
            return True
        return bool(re.search(r"\bwww\.[^\s]+\.[^\s]+\b", t))

    def _extract_first_url(self, text: str) -> str:
        t = self._safe_str(text)
        if not t:
            return ""

        match = re.search(r"(https?://[^\s]+)", t, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

        match = re.search(r"\b(www\.[^\s]+\.[^\s]+)\b", t, flags=re.IGNORECASE)
        if match:
            return f"https://{match.group(1).strip()}"

        return ""

    def _looks_like_planning(self, text: str) -> bool:
        t = self._safe_str(text).lower()
        if not t:
            return False

        triggers = (
            "plan",
            "roadmap",
            "step by step",
            "next steps",
            "strategy",
            "architect",
            "design",
            "endgame",
            "build me a plan",
        )
        return any(trigger in t for trigger in triggers)

    def _looks_like_memory_recall(self, text: str) -> bool:
        t = self._safe_str(text).lower()
        if not t:
            return False

        triggers = (
            "what is my name",
            "remember",
            "what do you remember",
            "do you remember",
            "what did i say",
            "my preferences",
            "my memory",
        )
        return any(trigger in t for trigger in triggers)

    def _decide_route(
        self,
        user_text: str,
        session_id: str = "",
        attachments=None,
    ) -> dict:
        attachments = attachments or []
        text = self._safe_str(user_text)
        lowered = text.lower()

        decision = {
            "route": self.ROUTE_GENERAL_CHAT,
            "mode": "chat",
            "confidence": 0.50,
            "use_memory": True,
            "save_memory": True,
            "save_artifact": False,
            "has_attachments": bool(attachments),
            "url": "",
            "memory_limit": self.memory_limit,
            "reasons": [],
            "session_id": self._safe_str(session_id),
        }

        if not text:
            decision["reasons"].append("empty_input")
            return decision

        if self._is_image_generation_request(user_text):
            decision.update(
                {
                    "route": self.ROUTE_IMAGE_GENERATION,
                    "mode": "image",
                    "confidence": 0.95,
                    "save_artifact": True,
                    "save_memory": False,
                    "use_memory": False,
                    "url": "",
                    "has_attachments": bool(attachments),
                    "prompt": self._image_prompt_from_text(user_text),
                }
            )
            decision["reasons"].append("image_trigger")
            return decision

        if attachments:
            decision.update(
                {
                    "route": self.ROUTE_ATTACHMENT_ANALYSIS,
                    "mode": "analysis",
                    "confidence": 0.90,
                    "save_artifact": True,
                }
            )
            decision["reasons"].append("attachments_present")
            return decision

        url = self._extract_first_url(text)
        if url:
            decision.update(
                {
                    "route": self.ROUTE_WEB_FETCH,
                    "mode": "tool",
                    "confidence": 0.94,
                    "save_artifact": True,
                    "url": url,
                }
            )
            decision["reasons"].append("url_detected")
            return decision

        if self._looks_like_memory_recall(text):
            decision.update(
                {
                    "route": self.ROUTE_MEMORY_RECALL,
                    "mode": "memory",
                    "confidence": 0.82,
                    "save_memory": False,
                }
            )
            decision["reasons"].append("memory_recall_trigger")
            return decision

        if self._looks_like_planning(text):
            decision.update(
                {
                    "route": self.ROUTE_PLANNING,
                    "mode": "planning",
                    "confidence": 0.78,
                    "save_artifact": True,
                }
            )
            decision["reasons"].append("planning_trigger")
            return decision

        decision["reasons"].append("default_general_chat")
        return decision

    # ==============================
    # EXECUTION SYSTEM
    # ==============================

    def _normalize_steps_signature(self, steps) -> List[str]:
        if not isinstance(steps, list):
            return []

        normalized: List[str] = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            title = self._clean_execution_text(step.get("title"))
            status = self._clean_execution_text(step.get("status"))
            notes = self._clean_execution_text(step.get("notes"))
            normalized.append(f"{title}|{status}|{notes}")
        return normalized

    def _looks_like_execution(self, text: str, decision: dict | None) -> bool:
        t = str(text or "").lower().strip()
        if not t:
            return False

        triggers = [
            "plan",
            "steps",
            "step by step",
            "research",
            "compare",
            "analyze",
            "build",
            "roadmap",
            "best",
            "approach",
        ]

        if any(x in t for x in triggers):
            return True

        if isinstance(decision, dict):
            if decision.get("mode") in ("planning", "analysis"):
                return True
            if decision.get("use_tools"):
                return True

        return len(t.split()) >= 12

    def _execution_step_titles_for_goal(self, goal: str) -> list[str]:
        lowered = str(goal or "").lower()

        if "hosting" in lowered:
            return [
                "Identify hosting options",
                "Compare tradeoffs",
                "Recommend best fit",
            ]

        if "plan" in lowered or "next steps" in lowered:
            return [
                "Define the goal",
                "Break into steps",
                "Return recommendation",
            ]

        if any(word in lowered for word in ("analyze", "audit", "review", "inspect")):
            return [
                "Inspect the request",
                "Extract key findings",
                "Summarize the result",
            ]

        return [
            "Understand request",
            "Process task",
            "Return result",
        ]

    def _build_execution(
        self,
        user_text: str,
        assistant_text: str,
        decision: dict | None,
    ) -> dict | None:
        if not self._looks_like_execution(user_text, decision):
            return None

        goal = str(user_text or "").strip()
        step_titles = self._execution_step_titles_for_goal(goal)
        now_iso = self._iso_now()

        step_objs = []
        for i, title in enumerate(step_titles, start=1):
            step_objs.append(
                {
                    "id": f"s{i}",
                    "title": title,
                    "status": "planned",
                    "notes": "",
                }
            )

        return {
            "id": f"exec_{uuid.uuid4().hex[:12]}",
            "mode": "plan_run",
            "goal": goal,
            "status": "planned",
            "current_step": step_titles[0] if step_titles else "",
            "summary": str(assistant_text or "")[:200],
            "steps": step_objs,
            "started_at": now_iso,
            "updated_at": now_iso,
        }

    def _execution_mark_running(
        self,
        execution: dict | None,
        step_index: int = 0,
    ) -> dict | None:
        if not isinstance(execution, dict):
            return execution

        steps = execution.get("steps")
        if not isinstance(steps, list) or not steps:
            execution["status"] = "running"
            execution["updated_at"] = self._iso_now()
            return execution

        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            if idx < step_index and step.get("status") != "failed":
                step["status"] = "completed"
            elif idx == step_index:
                step["status"] = "running"
                execution["current_step"] = str(step.get("title") or "").strip()
            elif step.get("status") != "failed":
                step["status"] = "planned"

        execution["status"] = "running"
        execution["updated_at"] = self._iso_now()
        return execution

    def _execution_mark_completed(
        self,
        execution: dict | None,
        assistant_text: str = "",
    ) -> dict | None:
        if not isinstance(execution, dict):
            return execution

        steps = execution.get("steps")
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict) and step.get("status") != "failed":
                    step["status"] = "completed"

        execution["status"] = "completed"
        execution["current_step"] = ""
        execution["summary"] = str(assistant_text or execution.get("summary") or "")[:200]
        execution["updated_at"] = self._iso_now()
        return execution

    def _execution_mark_failed(
        self,
        execution: dict | None,
        error_text: str = "",
    ) -> dict | None:
        if not isinstance(execution, dict):
            return execution

        steps = execution.get("steps")
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict) and step.get("status") == "running":
                    step["status"] = "failed"
                    if error_text:
                        step["notes"] = str(error_text)[:200]

        execution["status"] = "failed"
        execution["summary"] = str(error_text or execution.get("summary") or "")[:200]
        execution["updated_at"] = self._iso_now()
        return execution

    def _is_duplicate_execution(self, session_id: str, execution: dict | None) -> bool:
        if not session_id or not isinstance(execution, dict):
            return False

        latest = self._call_first(
            self.artifacts,
            ["get_latest_execution_run_for_session"],
            session_id,
        )
        if not latest:
            return False

        latest_meta = latest.get("meta") if isinstance(latest, dict) else {}
        latest_execution = latest_meta.get("execution") if isinstance(latest_meta, dict) else {}
        if not isinstance(latest_execution, dict):
            return False

        new_goal = self._clean_execution_text(execution.get("goal"))
        old_goal = self._clean_execution_text(latest_execution.get("goal"))

        new_summary = self._clean_execution_text(execution.get("summary"))
        old_summary = self._clean_execution_text(latest_execution.get("summary"))

        new_steps = self._normalize_steps_signature(execution.get("steps"))
        old_steps = self._normalize_steps_signature(latest_execution.get("steps"))

        if not new_goal or not old_goal:
            return False

        return (
            new_goal == old_goal
            and new_summary == old_summary
            and new_steps == old_steps
        )

    def _persist_execution_artifact(self, session_id: str, execution: dict | None) -> None:
        if not session_id or not isinstance(execution, dict):
            return

        if self._is_duplicate_execution(session_id=session_id, execution=execution):
            return

        self._call_first(
            self.artifacts,
            ["save_execution_run"],
            session_id=session_id,
            execution=execution,
        )

    def _attach_execution(self, payload, user_text, assistant_msg, decision, session_id=""):
        execution = self._build_execution(
            user_text=user_text,
            assistant_text=str(assistant_msg.get("text") or ""),
            decision=decision,
        )

        if not execution:
            return payload

        steps = execution.get("steps") if isinstance(execution.get("steps"), list) else []
        if steps:
            for i in range(len(steps)):
                execution = self._execution_mark_running(execution, step_index=i)

        execution = self._execution_mark_completed(
            execution,
            assistant_text=str(assistant_msg.get("text") or ""),
        )

        payload["execution"] = execution
        payload.setdefault("debug", {})
        payload["debug"]["execution"] = execution

        payload.setdefault("assistant_message", {})
        payload["assistant_message"].setdefault("meta", {})
        payload["assistant_message"]["meta"]["execution"] = execution

        try:
            self._persist_execution_artifact(session_id=session_id, execution=execution)
        except Exception as e:
            payload["debug"]["execution_persist_error"] = str(e)

        return payload

    # ==============================
    # SESSION HELPERS
    # ==============================

    def _ensure_session_id(self, session_id: str = "") -> str:
        sid = self._safe_str(session_id)
        if sid:
            return sid

        created = self._call_first(
            self.sessions,
            ["create_session", "new_session", "create", "start_session"],
        )
        if isinstance(created, dict):
            return self._safe_str(created.get("id"))

        return f"session_{uuid.uuid4().hex}"

    def _persist_message_fallback(self, session_id: str, message: dict) -> None:
        if not session_id or not isinstance(message, dict):
            return

        result = self._call_first(
            self.sessions,
            ["append_message", "add_message", "save_message", "push_message"],
            session_id,
            message,
        )
        if result is not None:
            return

        self._call_first(
            self.sessions,
            ["append_message", "add_message", "save_message", "push_message"],
            session_id=session_id,
            message=message,
        )

    def _persist_turn(self, session_id: str, user_msg: dict, assistant_msg: dict) -> None:
        try:
            self._persist_message_fallback(session_id, user_msg)
            self._persist_message_fallback(session_id, assistant_msg)
        except Exception as e:
            print("TURN PERSIST FAILED:", e)

    def _get_session_payload(self, session_id: str, fallback_messages=None) -> dict:
        fallback_messages = fallback_messages or []

        session_obj = self._call_first(
            self.sessions,
            ["get_session", "read_session", "get", "load_session"],
            session_id,
        )
        if isinstance(session_obj, dict):
            return session_obj

        session_obj = self._call_first(
            self.sessions,
            ["get_session", "read_session", "get", "load_session"],
            session_id=session_id,
        )
        if isinstance(session_obj, dict):
            return session_obj

        return {
            "id": session_id,
            "messages": fallback_messages,
        }

    def _get_sessions_list(self) -> list:
        data = self._call_first(
            self.sessions,
            ["list_sessions", "get_sessions", "list", "all_sessions"],
        )
        return data if isinstance(data, list) else []

    def _get_memory_list(self) -> list:
        data = self._call_first(
            self.memory,
            ["list_memory", "get_memory", "list", "all_memory"],
        )
        if isinstance(data, dict) and isinstance(data.get("memory"), list):
            return data.get("memory")
        return data if isinstance(data, list) else []

    def _get_artifacts_list(self) -> list:
        data = self._call_first(
            self.artifacts,
            ["list_artifacts", "get_artifacts", "list", "all_artifacts"],
        )
        if isinstance(data, dict) and isinstance(data.get("artifacts"), list):
            return data.get("artifacts")
        return data if isinstance(data, list) else []

    # ==============================
    # MEMORY HELPERS
    # ==============================

    def _rank_memory_context(
        self,
        user_text: str,
        limit: int = 5,
        session_id: str = "",
    ) -> list[dict]:
        try:
            items = self._get_memory_list()
        except Exception:
            items = []

        if not isinstance(items, list):
            items = []

        scored = []
        for item in items:
            if not isinstance(item, dict):
                continue

            score = self._score_memory_item(
                item=item,
                user_text=user_text,
                session_id=session_id,
            )

            if not self._memory_is_relevant_enough(item, score, user_text):
                continue

            enriched = dict(item)
            enriched["_memory_score"] = score
            scored.append(enriched)

        scored.sort(
            key=lambda x: (
                float(x.get("_memory_score") or 0.0),
                self._safe_str(x.get("updated_at") or x.get("created_at")),
            ),
            reverse=True,
        )

        return scored[: max(int(limit or 5), 1)]

    def _format_memory_context(self, memory_items: list[dict]) -> str:
        if not isinstance(memory_items, list) or not memory_items:
            return ""

        lines = []
        for item in memory_items[: self.memory_limit]:
            if not isinstance(item, dict):
                continue

            text = self._safe_str(item.get("text"))
            kind = self._safe_str(item.get("kind"))
            if not text:
                continue

            if kind:
                lines.append(f"- [{kind}] {text}")
            else:
                lines.append(f"- {text}")

        return "\n".join(lines).strip()

    def _maybe_write_memory(self, decision: dict, user_text: str, session_id: str) -> None:
        if not isinstance(decision, dict):
            return
        if not decision.get("save_memory"):
            return

        text = self._safe_str(user_text)
        lowered = text.lower()

        should_save = False
        kind = "note"

        # profile / identity
        if any(x in lowered for x in ["my name is", "i am ", "i'm ", "call me"]):
            should_save = True
            kind = "profile"

        # preferences
        elif any(x in lowered for x in ["i prefer", "i like", "i usually", "i always", "from now on"]):
            should_save = True
            kind = "preference"

        # project / work
        elif any(x in lowered for x in ["i'm building", "i am building", "my project", "i'm working on", "working         on", "nova"]):
            should_save = True
            kind = "project"

        # goals
        elif any(x in lowered for x in ["i want to", "my goal", "i plan to"]):
            should_save = True
            kind = "goal"

        # explicit memory instruction
        elif "remember that" in lowered:
            should_save = True
            kind = "note"

        if not should_save:
            return

        try:
            self._call_first(
                self.memory,
                ["add_memory", "create_memory", "save_memory", "create"],
                text=text,
                kind=kind,
                source="router_auto",
                session_id=session_id,
            )
        except Exception as e:
            print("MEMORY WRITE FAILED:", e)

    def _memory_text_tokens(self, value: str) -> set[str]:
        text = self._safe_str(value).lower()
        if not text:
            return set()

        stop_words = {
            "the", "a", "an", "and", "or", "but", "if", "then", "than",
            "to", "of", "for", "in", "on", "at", "by", "with", "from",
            "is", "are", "was", "were", "be", "been", "being",
            "it", "this", "that", "these", "those",
            "i", "me", "my", "you", "your", "we", "our",
            "do", "does", "did", "have", "has", "had",
            "what", "when", "where", "why", "how",
            "can", "could", "should", "would", "will",
            "about", "into", "over", "under", "again", "right", "now",
        }

        tokens = set(re.findall(r"[a-z0-9_]{2,}", text))
        return {token for token in tokens if token not in stop_words}

    def _memory_kind_weight(self, kind: str) -> float:
        k = self._safe_str(kind).lower()

        if k in {"preference", "profile"}:
            return 3.0
        if k in {"project", "goal"}:
            return 2.5
        if k in {"identity", "personal"}:
            return 2.0
        if k in {"summary", "note"}:
            return 1.25
        return 1.0

    def _memory_time_bonus(self, item: dict) -> float:
        created_at = self._safe_str(item.get("updated_at") or item.get("created_at"))
        if not created_at:
            return 0.0

        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_days = max((now - dt).total_seconds() / 86400.0, 0.0)
        except Exception:
            return 0.0

        if age_days <= 1:
            return 1.5
        if age_days <= 7:
            return 1.0
        if age_days <= 30:
            return 0.5
        return 0.0

    def _memory_session_bonus(self, item: dict, session_id: str = "") -> float:
        current_session = self._safe_str(session_id)
        item_session = self._safe_str(item.get("session_id"))
        if current_session and item_session and current_session == item_session:
            return 1.5
        return 0.0

    def _score_memory_item(self, item: dict, user_text: str, session_id: str = "") -> float:
        if not isinstance(item, dict):
            return -999.0

        memory_text = self._safe_str(item.get("text"))
        if not memory_text:
            return -999.0

        query = self._safe_str(user_text)
        query_lower = query.lower()
        memory_lower = memory_text.lower()

        query_tokens = self._memory_text_tokens(query)
        memory_tokens = self._memory_text_tokens(memory_text)

        overlap = query_tokens.intersection(memory_tokens)
        overlap_score = float(len(overlap)) * 2.0

        exact_phrase_score = 0.0
        if query_lower and query_lower in memory_lower:
            exact_phrase_score += 5.0

        contains_named_value = 0.0
        for token in sorted(query_tokens, key=len, reverse=True):
            if len(token) >= 4 and token in memory_lower:
                contains_named_value += 0.75

        kind_score = self._memory_kind_weight(item.get("kind"))
        time_score = self._memory_time_bonus(item)
        session_score = self._memory_session_bonus(item, session_id=session_id)

        quality_score = 0.0
        try:
            quality_score = float(item.get("quality_score") or 0.0)
        except Exception:
            quality_score = 0.0

        generic_penalty = 0.0
        if len(memory_tokens) <= 3:
            generic_penalty -= 0.75
        if memory_lower in {"ok", "yes", "no", "thanks"}:
            generic_penalty -= 4.0

        return (
            overlap_score
            + exact_phrase_score
            + contains_named_value
            + kind_score
            + time_score
            + session_score
            + quality_score
            + generic_penalty
        )

    def _memory_is_relevant_enough(self, item: dict, score: float, user_text: str) -> bool:
        text = self._safe_str(item.get("text"))
        if not text:
            return False

        query = self._safe_str(user_text).lower()

        if any(x in query for x in ["remember", "memory", "about me", "my project"]):
            return True

        query_tokens = self._memory_text_tokens(user_text)
        memory_tokens = self._memory_text_tokens(text)
        overlap = query_tokens.intersection(memory_tokens)

        if score >= 1.5:
            return True

        if len(overlap) >= 1:
            return True

        kind = self._safe_str(item.get("kind")).lower()
        if kind in {"project", "preference", "profile", "goal"}:
            return True

        return False

    # ==============================
    # IMAGE HELPERS
    # ==============================

    def _is_image_generation_request(self, user_text: str) -> bool:
        text = str(user_text or "").strip().lower()

        if not text:
            return False

        if text.startswith("/image"):
            return True

        if "/image" in text:
            return True

        triggers = [
            "generate an image",
            "generate image",
            "make an image",
            "create an image",
            "draw ",
            "draw me ",
        ]

        return any(trigger in text for trigger in triggers)

    def _image_prompt_from_text(self, user_text: str) -> str:
        text = str(user_text or "").strip()
        lowered = text.lower()

        if lowered.startswith("/image"):
            prompt = text[6:].strip()
            return prompt or "Generate an image."

        prefixes = (
            "generate an image of ",
            "generate an image ",
            "generate image of ",
            "generate image ",
            "make an image of ",
            "make an image ",
            "create an image of ",
            "create an image ",
            "draw me ",
            "draw ",
        )

        for prefix in prefixes:
            if lowered.startswith(prefix):
                prompt = text[len(prefix):].strip()
                return prompt or text

        return text or "Generate an image."

    def _build_image_generation_meta(
        self,
        prompt: str,
        image_url: str,
        revised_prompt: str = "",
        parent_artifact_id: str = "",
        source_type: str = "generated",
        generation_mode: str = "text_to_image",
        source_session_id: str = "",
    ) -> dict:
        return {
            "prompt": str(prompt or "").strip(),
            "revised_prompt": str(revised_prompt or "").strip(),
            "image_url": str(image_url or "").strip(),
            "source_type": str(source_type or "generated").strip(),
            "parent_artifact_id": str(parent_artifact_id or "").strip(),
            "generation_mode": str(generation_mode or "text_to_image").strip(),
            "source_session_id": str(source_session_id or "").strip(),
        }

    def _build_image_generation_artifact(
        self,
        session_id: str,
        prompt: str,
        image_url: str,
        revised_prompt: str = "",
        parent_artifact_id: str = "",
        source_type: str = "generated",
        generation_mode: str = "text_to_image",
    ) -> dict:
        clean_prompt = str(prompt or "").strip()
        artifact_text = f'Generated image for: "{clean_prompt}"'

        meta = self._build_image_generation_meta(
            prompt=clean_prompt,
            image_url=image_url,
            revised_prompt=revised_prompt,
            parent_artifact_id=parent_artifact_id,
            source_type=source_type,
            generation_mode=generation_mode,
            source_session_id=session_id,
        )

        bullets = []
        if clean_prompt:
            bullets.append(f"Prompt: {clean_prompt}")
        if meta["revised_prompt"]:
            bullets.append(f"Revised prompt: {meta['revised_prompt']}")
        if meta["parent_artifact_id"]:
            bullets.append(f"Parent artifact: {meta['parent_artifact_id']}")

        return {
            "kind": "image_generation",
            "title": "Generated image",
            "body": artifact_text,
            "summary": artifact_text,
            "preview": artifact_text,
            "session_id": session_id,
            "image_url": image_url,
            "source": "image_generation",
            "meta": meta,
            "viewer": {
                "kind": "image_generation",
                "title": "Generated image",
                "body": artifact_text,
                "summary": artifact_text,
                "image_url": image_url,
                "analysis_text": f"This image was generated from the prompt: {clean_prompt}" if clean_prompt else artifact_text,
                "bullets": bullets,
                "source_url": "",
            },
        }

    def _save_artifact_fallback(self, artifact: dict):
        if not isinstance(artifact, dict) or not artifact:
            return None

        try:
            return self.artifacts.save_artifact(artifact)
        except Exception as e:
            print("ARTIFACT SAVE FAILED:", e)
            return None

    def _persist_image_generation_artifact(
        self,
        session_id: str,
        prompt: str,
        image_url: str,
        revised_prompt: str = "",
        parent_artifact_id: str = "",
        source_type: str = "generated",
        generation_mode: str = "text_to_image",
    ):
        if not session_id or not image_url:
            return None

        artifact = self._build_image_generation_artifact(
            session_id=session_id,
            prompt=prompt,
            image_url=image_url,
            revised_prompt=revised_prompt,
            parent_artifact_id=parent_artifact_id,
            source_type=source_type,
            generation_mode=generation_mode,
        )
        return self._save_artifact_fallback(artifact)

    def _handle_image_generation(
        self,
        prompt: str,
        session_id: str = "",
        parent_artifact_id: str = "",
        source_type: str = "generated",
    ) -> dict:
        try:
            result = self.client.images.generate(
                model=self.image_model,
                prompt=prompt,
                size=self.image_size,
            )

            first = result.data[0] if getattr(result, "data", None) else None
            image_b64 = getattr(first, "b64_json", None) if first else None
            if not image_b64:
                raise ValueError("Image API returned no b64_json")

            image_bytes = base64.b64decode(image_b64)
            filename = f"generated_{uuid.uuid4().hex}.png"
            filepath = self.uploads_dir / filename

            with open(filepath, "wb") as f:
                f.write(image_bytes)

            image_url = f"/api/uploads/{filename}"

            saved_artifact = None
            try:
                saved_artifact = self._persist_image_generation_artifact(
                    session_id=session_id,
                    prompt=prompt,
                    image_url=image_url,
                    revised_prompt="",
                    parent_artifact_id=parent_artifact_id,
                    source_type=source_type,
                    generation_mode="text_to_image",
                )
            except Exception as e:
                print("IMAGE ARTIFACT SAVE FAILED:", e)

            return {
                "ok": True,
                "text": f"Generated image for: {prompt}",
                "image_url": image_url,
                "prompt": prompt,
                "revised_prompt": "",
                "parent_artifact_id": parent_artifact_id,
                "source_type": source_type,
                "generation_mode": "text_to_image",
                "saved_artifact": saved_artifact,
            }
        except Exception as e:
            return {
                "ok": False,
                "text": f"Image generation failed: {e}",
                "error": str(e),
                "image_url": "",
                "prompt": prompt,
                "revised_prompt": "",
                "parent_artifact_id": parent_artifact_id,
                "source_type": source_type,
                "generation_mode": "text_to_image",
                "saved_artifact": None,
            }
    # ==============================
    # WEB / ATTACHMENT HELPERS
    # ==============================

    def _handle_web_fetch(self, url: str, session_id: str = "") -> dict:
        raw_url = self._safe_str(url)
        normalized_url = raw_url
        if normalized_url and not re.match(r"^https?://", normalized_url, re.IGNORECASE):
            normalized_url = "https://" + normalized_url

        fetched_at = datetime.now(timezone.utc).isoformat()

        try:
            result = self.web.fetch(normalized_url)
        except Exception as e:
            return {
                "ok": False,
                "error": f"Web fetch failed: {e}",
                "url": normalized_url,
                "debug": {
                    "route_taken": "web_fetch",
                    "error": str(e),
                },
            }

        if not isinstance(result, dict):
            result = {}

        artifact = {}
        try:
            if hasattr(self.web, "build_artifact_payload") and callable(self.web.build_artifact_payload):
                artifact = self.web.build_artifact_payload(result) or {}
        except Exception as e:
            artifact = {
                "kind": "web_result",
                "title": self._safe_str(result.get("title")) or normalized_url,
                "summary": self._safe_str(result.get("summary")),
                "body": self._safe_str(result.get("content")),
                "preview": self._safe_str(result.get("preview")),
                "source_url": self._safe_str(result.get("final_url") or result.get("url") or normalized_url),
                "meta": {
                    "description": self._safe_str(result.get("description")),
                    "site_name": self._safe_str(result.get("site_name")),
                    "domain": self._safe_str(result.get("domain")),
                    "content": self._safe_str(result.get("content")),
                    "url": self._safe_str(result.get("final_url") or result.get("url") or normalized_url),
                    "status_code": result.get("status_code"),
                    "ssl_verified": result.get("ssl_verified"),
                    "artifact_build_error": str(e),
                },
                "viewer": {
                    "kind": "web_result",
                    "title": self._safe_str(result.get("title")) or normalized_url,
                    "body": self._safe_str(result.get("content")),
                    "analysis_text": self._safe_str(result.get("summary")),
                    "bullets": self._safe_list(result.get("bullets")),
                    "links": self._safe_list(result.get("links")),
                    "images": self._safe_list(result.get("images")),
                    "source_url": self._safe_str(result.get("final_url") or result.get("url") or normalized_url),
                },
            }

        if isinstance(artifact, dict):
            artifact["session_id"] = session_id or artifact.get("session_id", "")
            artifact.setdefault("created_at", fetched_at)
            artifact["updated_at"] = fetched_at

        artifact = self._upgrade_web_artifact_payload(
            artifact=artifact,
            result=result,
            url=normalized_url,
        )

        saved_artifact = self._save_artifact_fallback(artifact) if artifact else None
        final_artifact = self._upgrade_web_artifact_payload(
            artifact=saved_artifact or artifact,
            result=result,
            url=normalized_url,
        )

        summary = self._safe_str(final_artifact.get("summary")) if isinstance(final_artifact, dict) else ""
        body = self._safe_str(final_artifact.get("body")) if isinstance(final_artifact, dict) else ""
        title = self._safe_str(final_artifact.get("title")) if isinstance(final_artifact, dict) else normalized_url
        viewer = self._safe_dict(final_artifact.get("viewer")) if isinstance(final_artifact, dict) else {}
        meta = self._safe_dict(final_artifact.get("meta")) if isinstance(final_artifact, dict) else {}

        return {
            "ok": bool(result.get("ok", True)),
            "text": summary or f"Fetched {title}",
            "artifact": final_artifact,
            "viewer": viewer,
            "url": self._safe_str(result.get("final_url") or result.get("url") or normalized_url),
            "source_url": self._safe_str(meta.get("source_url")) or self._safe_str(result.get("final_url") or result.get("url") or normalized_url),
            "title": title,
            "summary": summary,
            "body": body,
            "meta": meta,
            "debug": {
                "route_taken": "web_fetch",
                "status_code": result.get("status_code"),
                "artifact_kind": self._safe_str(final_artifact.get("kind")) if isinstance(final_artifact, dict) else "web_result",
            },
        }

    def _handle_attachment_analysis(self, user_text: str, attachments: list) -> dict:
        attachments = attachments or []

        image_url = ""
        image_name = ""

        for item in attachments:
            if not isinstance(item, dict):
                continue

            att_type = self._safe_str(item.get("type")).lower()
            mime_type = self._safe_str(item.get("mime_type")).lower()
            url = self._safe_str(item.get("url"))
            name = self._safe_str(item.get("name") or item.get("filename") or "image")

            if url and (att_type == "image" or mime_type.startswith("image/")):
                image_url = url
                image_name = name
                break

        if image_url:
            try:
                prompt = self._safe_str(user_text) or "what is in this image"

                response = self.client.responses.create(
                    model=self.chat_model,
                    input=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": prompt},
                                {"type": "input_image", "image_url": image_url},
                            ],
                        }
                    ],
                )

                text = self._extract_response_text(response)

                return {
                    "ok": True,
                    "text": text or f"I analyzed the image: {image_name}",
                    "saved_artifact": None,
                }

            except Exception as e:
                return {
                    "ok": False,
                    "text": f"Image analysis failed: {e}",
                    "error": str(e),
                    "saved_artifact": None,
                }

        names = []
        for item in attachments:
            if isinstance(item, dict):
                name = self._safe_str(item.get("name") or item.get("filename"))
                if name:
                    names.append(name)

        summary = (
            f"I analyzed the uploaded attachment(s): {', '.join(names)}."
            if names
            else "I analyzed the uploaded attachment(s)."
        )

        if user_text:
            summary += f" Request: {user_text}"

        return {
            "ok": True,
            "text": summary,
            "saved_artifact": None,
        }

    # ==============================
    # MODEL HELPERS
    # ==============================

    # ==============================
    # MODEL HELPERS
    # ==============================

    def _build_chat_input(
        self,
        user_text: str,
        decision: dict,
        session_id: str = "",
    ) -> str:
        user_text = self._safe_str(user_text)

        if not self._should_auto_inject_memory(user_text, decision):
            return user_text

        memory_items = self._rank_memory_context(
            user_text=user_text,
            limit=int(decision.get("memory_limit") or self.memory_limit),
            session_id=session_id,
        )

        memory_block = self._format_memory_context(memory_items[:3])
        if not memory_block:
            return user_text

        return (
            "Relevant memory:\n"
            f"{memory_block}\n\n"
            "Instructions:\n"
            "- Use the memory only if it helps answer the user naturally.\n"
            "- Do not mention memory unless it is directly relevant.\n"
            "- Do not list memories unless the user asks.\n\n"
            "User message:\n"
            f"{user_text}"
        )

    def _run_chat_model(
        self,
        user_text: str,
        decision: dict,
        session_id: str = "",
    ) -> str:
        prompt = self._build_chat_input(
            user_text=user_text,
            decision=decision,
            session_id=session_id,
        )

        try:
            response = self.client.responses.create(
                model=self.chat_model,
                input=prompt,
            )
            return self._extract_response_text(response)
        except Exception as e:
            return f"Model error: {e}"

    # ==============================
    # RESPONSE BUILDERS
    # ==============================

    def _build_user_message(self, user_text: str, attachments=None) -> dict:
        return new_message(
            role="user",
            text=user_text,
            attachments=attachments or [],
            meta={},
        )

    def _build_assistant_message(
        self,
        text: str,
        meta: dict | None = None,
        attachments=None,
    ) -> dict:
        return new_message(
            role="assistant",
            text=text,
            attachments=attachments or [],
            meta=meta or {},
        )

    def _finalize_response(
        self,
        session_id: str,
        user_text: str,
        user_msg: dict,
        assistant_msg: dict,
        decision: dict,
        saved_artifact=None,
    ) -> dict:
        self._persist_turn(session_id, user_msg, assistant_msg)
        self._maybe_write_memory(decision, user_text, session_id)

        payload = {
            "ok": True,
            "active_session_id": session_id,
            "assistant_message": assistant_msg,
            "session": self._get_session_payload(
                session_id,
                fallback_messages=[user_msg, assistant_msg],
            ),
            "saved_artifact": saved_artifact,
            "artifacts": self._get_artifacts_list(),
            "memory": self._get_memory_list(),
            "sessions": self._get_sessions_list(),
            "debug": {
                "decision": decision,
                "route": "chat_service.handle",
                "route_taken": decision.get("route"),
                "handler": f"_execute_{decision.get('route')}",
                "attachments_count": len(self._safe_list(user_msg.get("attachments"))),
            },
        }

        payload = self._attach_execution(
            payload,
            user_text,
            assistant_msg,
            decision,
            session_id=session_id,
        )
        return payload

    def _run_chat_model(
        self,
        user_text: str,
        decision: dict,
        session_id: str = "",
    ) -> str:
        prompt = self._build_chat_input(
            user_text=user_text,
            decision=decision,
            session_id=session_id,
        )

        try:
            response = self.client.responses.create(
                model=self.chat_model,
                input=prompt,
            )
            return self._extract_response_text(response)
        except Exception as e:
            return f"Model error: {e}"

    # ==============================
    # EXECUTORS
    # ==============================

    def _execute_general_chat(
        self,
        decision: dict,
        user_text: str,
        session_id: str,
        attachments=None,
    ) -> dict:
        user_msg = self._build_user_message(user_text, attachments=attachments or [])
        assistant_text = self._run_chat_model(
            user_text=user_text,
            decision=decision,
            session_id=session_id,
        )

        assistant_msg = self._build_assistant_message(
            text=assistant_text,
            meta={},
            attachments=[],
        )

        return self._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            decision=decision,
            saved_artifact=None,
        )

    def _execute_memory_recall(
        self,
        decision: dict,
        user_text: str,
        session_id: str,
        attachments=None,
    ) -> dict:
        user_msg = self._build_user_message(user_text, attachments=attachments or [])

        memory_items = self._rank_memory_context(
            user_text=user_text,
            limit=int(decision.get("memory_limit") or self.memory_limit),
            session_id=session_id,
        )

        if memory_items:
            lines = []
            limit = int(decision.get("memory_limit") or self.memory_limit)

            for item in memory_items[:limit]:
                text = self._safe_str(item.get("text"))
                kind = self._safe_str(item.get("kind"))

                if not text:
                    continue

                if kind:
                    lines.append(f"- [{kind}] {text}")
                else:
                    lines.append(f"- {text}")

            assistant_text = "Here’s what I remember that seems relevant right now:\n" + "\n".join(lines)
        else:
            assistant_text = "I do not have any relevant saved memory for that yet."

        assistant_msg = self._build_assistant_message(
            text=assistant_text,
            meta={"memory_recall": True},
            attachments=[],
        )

        return self._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            decision=decision,
            saved_artifact=None,
        )

    def _execute_planning(
        self,
        decision: dict,
        user_text: str,
        session_id: str,
        attachments=None,
    ) -> dict:
        user_msg = self._build_user_message(user_text, attachments=attachments or [])
        assistant_text = self._run_chat_model(
            user_text=user_text,
            decision=decision,
            session_id=session_id,
        )

        assistant_msg = self._build_assistant_message(
            text=assistant_text,
            meta={"planning": True},
            attachments=[],
        )

        return self._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            decision=decision,
            saved_artifact=None,
        )

    def _execute_web_fetch(
        self,
        decision: dict,
        user_text: str,
        session_id: str,
        attachments=None,
    ) -> dict:
        user_msg = self._build_user_message(user_text, attachments=attachments or [])

        web_result = self._handle_web_fetch(
            self._safe_str(decision.get("url")),
            session_id=session_id,
        )

        artifact_summary = ""
        artifact = web_result.get("artifact")
        if isinstance(artifact, dict):
            artifact_summary = self._safe_str(artifact.get("summary"))

        assistant_msg = self._build_assistant_message(
            text=artifact_summary or self._safe_str(web_result.get("summary")) or "Web fetch completed.",
            meta={
                "web_fetch": True,
                "source_url": self._safe_str(web_result.get("source_url")),
                "title": self._safe_str(web_result.get("title")),
            },
            attachments=[],
        )

        return self._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            decision=decision,
            saved_artifact=web_result.get("artifact"),
        )

    def _execute_attachment_analysis(
        self,
        decision: dict,
        user_text: str,
        session_id: str,
        attachments=None,
    ) -> dict:
        attachments = attachments or []
        user_msg = self._build_user_message(user_text, attachments=attachments)
        result = self._handle_attachment_analysis(user_text, attachments)

        assistant_msg = self._build_assistant_message(
            text=self._safe_str(result.get("text")) or "Attachment analysis completed.",
            meta={"attachment_analysis": True},
            attachments=[],
        )

        return self._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            decision=decision,
            saved_artifact=result.get("saved_artifact"),
        )

    def _execute_image_generation(
        self,
        decision: dict,
        user_text: str,
        session_id: str,
        attachments=None,
    ) -> dict:
        attachments = attachments or []

        decision = dict(decision or {})
        decision["route"] = self.ROUTE_IMAGE_GENERATION
        decision["mode"] = "image"
        decision["confidence"] = max(float(decision.get("confidence") or 0.0), 0.99)
        decision["save_artifact"] = True
        decision["save_memory"] = False
        decision["use_memory"] = False
        decision["has_attachments"] = bool(attachments)
        decision["url"] = ""
        decision["prompt"] = self._safe_str(decision.get("prompt")) or self._image_prompt_from_text(user_text)

        reasons = decision.get("reasons")
        if not isinstance(reasons, list):
            reasons = []
        if "image_executor_override" not in reasons:
            reasons.append("image_executor_override")
        decision["reasons"] = reasons

        user_msg = self._build_user_message(user_text, attachments=attachments)
        prompt = self._safe_str(decision.get("prompt")) or self._image_prompt_from_text(user_text)

        try:
            result = self._handle_image_generation(
                prompt,
                session_id=session_id,
                parent_artifact_id="",
                source_type="generated",
            )
        except Exception as e:
            assistant_msg = self._build_assistant_message(
                text=f"Image generation failed: {e}",
                meta={
                    "image_generation": True,
                    "image_error": str(e),
                    "prompt": prompt,
                },
                attachments=[],
            )
            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=user_msg,
                assistant_msg=assistant_msg,
                decision=decision,
                saved_artifact=None,
            )

        saved_artifact = result.get("saved_artifact") or {}

        saved_artifact = self._upgrade_image_artifact_payload(
            artifact=saved_artifact,
            prompt=prompt,
            revised_prompt=self._safe_str(result.get("revised_prompt")) if isinstance(result, dict) else "",
            source_type=self._safe_str(result.get("source_type")) or "generated",
            generation_mode=self._safe_str(result.get("generation_mode")) or "text_to_image",
        )

        artifact_id = (
            self._safe_str(saved_artifact.get("id"))
            or self._safe_str(result.get("parent_artifact_id"))
        )

        assistant_msg = self._build_assistant_message(
            text=self._safe_str(saved_artifact.get("summary"))
            or self._safe_str(result.get("text"))
            or f"Generated image for: {prompt}",
            meta={
                "image_generation": True,
                "image_url": self._safe_str(result.get("image_url")),
                "prompt": self._safe_str(result.get("prompt")) or prompt,
                "revised_prompt": self._safe_str(result.get("revised_prompt")),
                "artifact_id": artifact_id,
                "parent_artifact_id": self._safe_str(result.get("parent_artifact_id")),
                "source_type": self._safe_str(result.get("source_type")) or "generated",
                "generation_mode": self._safe_str(result.get("generation_mode")) or "text_to_image",
            },
            attachments=[],
        )

        return self._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            decision=decision,
            saved_artifact=saved_artifact,
        )

    def _execute_web_operator(self, user_text: str, session_id: str) -> dict:
        try:
            url_match = re.search(r"(https?://[^\s]+)", user_text or "")
            base_url = url_match.group(1) if url_match else ""

            if not base_url:
                user_msg = self._build_user_message(user_text, attachments=[])
                assistant_msg = self._build_assistant_message(
                    text="No URL detected for web operator.",
                    meta={"web_operator": True},
                    attachments=[],
                )
                return self._finalize_response(
                    session_id=session_id,
                    user_text=user_text,
                    user_msg=user_msg,
                    assistant_msg=assistant_msg,
                    decision={
                        "route": "web_operator",
                        "mode": "tool",
                        "confidence": 0.70,
                        "use_memory": False,
                        "save_memory": False,
                        "save_artifact": False,
                        "has_attachments": False,
                        "url": "",
                        "memory_limit": self.memory_limit,
                        "reasons": ["research_trigger", "no_url_detected"],
                        "session_id": self._safe_str(session_id),
                    },
                    saved_artifact=None,
                )

            primary = self.web.fetch(base_url)
            links = self._safe_list(primary.get("links"))[:3]

            collected = [primary]
            visited = [base_url]

            for link in links:
                try:
                    result = self.web.fetch(link)
                    if isinstance(result, dict) and result.get("ok"):
                        collected.append(result)
                        visited.append(link)
                except Exception:
                    continue

            combined_bullets = []
            combined_content = []

            for page in collected:
                if not isinstance(page, dict):
                    continue
                combined_bullets.extend(self._safe_list(page.get("bullets")))
                combined_content.append(self._safe_str(page.get("content")))

            deduped_bullets = []
            seen = set()
            for item in combined_bullets:
                clean = self._safe_str(item)
                key = clean.lower()
                if not clean or key in seen:
                    continue
                seen.add(key)
                deduped_bullets.append(clean)

            deduped_bullets = deduped_bullets[:10]
            combined_body = "\n\n".join([c for c in combined_content if c])[:8000]
            summary = "\n".join(deduped_bullets[:5]).strip()

            artifact = {
                "kind": "web_research",
                "title": f"Research: {base_url}",
                "summary": summary or f"Analyzed {len(visited)} page(s).",
                "body": combined_body,
                "preview": (summary or combined_body[:300]).strip(),
                "source": "web_operator",
                "session_id": session_id or "",
                "meta": {
                    "source_url": base_url,
                    "visited": visited,
                    "pages_visited": len(visited),
                },
                "viewer": {
                    "kind": "web_research",
                    "title": f"Research: {base_url}",
                    "analysis_text": summary or f"Analyzed {len(visited)} page(s).",
                    "body": combined_body,
                    "bullets": deduped_bullets,
                    "links": visited,
                    "source_url": base_url,
                },
            }

            saved_artifact = self._save_artifact_fallback(artifact)

            user_msg = self._build_user_message(user_text, attachments=[])
            assistant_text = f"Analyzed {len(visited)} pages.\n\n{summary}".strip()
            assistant_msg = self._build_assistant_message(
                text=assistant_text,
                meta={
                    "web_operator": True,
                    "source_url": base_url,
                    "pages_visited": len(visited),
                },
                attachments=[],
            )

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=user_msg,
                assistant_msg=assistant_msg,
                decision={
                    "route": "web_operator",
                    "mode": "tool",
                    "confidence": 0.97,
                    "use_memory": False,
                    "save_memory": False,
                    "save_artifact": True,
                    "has_attachments": False,
                    "url": base_url,
                    "memory_limit": self.memory_limit,
                    "reasons": ["research_trigger", "phase_6_web_operator"],
                    "session_id": self._safe_str(session_id),
                },
                saved_artifact=saved_artifact,
            )

        except Exception as e:
            user_msg = self._build_user_message(user_text, attachments=[])
            assistant_msg = self._build_assistant_message(
                text=f"Web operator failed: {e}",
                meta={"web_operator": True, "web_operator_error": str(e)},
                attachments=[],
            )
            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=user_msg,
                assistant_msg=assistant_msg,
                decision={
                    "route": "web_operator",
                    "mode": "tool",
                    "confidence": 0.40,
                    "use_memory": False,
                    "save_memory": False,
                    "save_artifact": False,
                    "has_attachments": False,
                    "url": "",
                    "memory_limit": self.memory_limit,
                    "reasons": ["research_trigger", "phase_6_web_operator_error"],
                    "session_id": self._safe_str(session_id),
                },
                saved_artifact=None,
            )

    def _execute_decision(
        self,
        decision: dict,
        user_text: str,
        session_id: str = "",
        attachments=None,
    ) -> dict:
        attachments = attachments or []
        route = self._safe_str(decision.get("route")) or self.ROUTE_GENERAL_CHAT

        if route == self.ROUTE_IMAGE_GENERATION:
            return self._execute_image_generation(
                decision=decision,
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
            )

        if route == self.ROUTE_WEB_FETCH:
            return self._execute_web_fetch(
                decision=decision,
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
            )

        if route == self.ROUTE_ATTACHMENT_ANALYSIS:
            return self._execute_attachment_analysis(
                decision=decision,
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
            )

        if route == self.ROUTE_PLANNING:
            return self._execute_planning(
                decision=decision,
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
            )

        if route == self.ROUTE_MEMORY_RECALL:
            return self._execute_memory_recall(
                decision=decision,
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
            )

        return self._execute_general_chat(
            decision=decision,
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
        )

    # ==============================
    # PUBLIC ENTRY
    # ==============================

    def handle(self, user_text: str, session_id: str = "", attachments=None):
        attachments = attachments or []
        user_text = self._safe_str(user_text)

        session_id = self._ensure_session_id(session_id)

        if "research" in (user_text or "").lower():
            return self._execute_web_operator(user_text, session_id)

        decision = self._decide_route(
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
        )

        if not user_text:
            user_msg = self._build_user_message("", attachments=attachments)
            assistant_msg = self._build_assistant_message(
                text="Please enter a message.",
                meta={"empty_input": True},
                attachments=[],
            )
            return self._finalize_response(
                session_id=session_id,
                user_text="",
                user_msg=user_msg,
                assistant_msg=assistant_msg,
                decision=decision,
                saved_artifact=None,
            )

        return self._execute_decision(
            decision=decision,
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
        )
