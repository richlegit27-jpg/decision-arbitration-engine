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

    def _rank_memory_context(self, user_text: str, limit: int = 3) -> list[dict]:
        try:
            items = self._get_memory_list()
            if not items:
                return []

            if hasattr(self.memory_ranker, "rank"):
                ranked = self.memory_ranker.rank(
                    query=user_text,
                    memory_items=items,
                    limit=limit,
                )
                if isinstance(ranked, list):
                    return ranked[:limit]
        except Exception as e:
            print("MEMORY RANK ERROR:", e)

        return self._safe_list(self._get_memory_list())[:limit]

    def _format_memory_context(self, memory_items: list[dict]) -> str:
        if not memory_items:
            return ""

        lines = []
        for item in memory_items:
            if not isinstance(item, dict):
                continue
            text = self._safe_str(item.get("text"))
            if text:
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
        kind = "general"

        if "my name is " in lowered:
            should_save = True
            kind = "profile"
        elif "i prefer" in lowered or "from now on" in lowered:
            should_save = True
            kind = "preference"
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

    def _handle_web_fetch(self, url: str) -> dict:
        if not url:
            return {
                "ok": False,
                "title": "",
                "summary": "No URL provided.",
                "source_url": "",
                "saved_artifact": None,
            }

        try:
            result = self._call_first(
                self.web,
                ["fetch_url", "fetch", "get_url", "read_url"],
                url,
            )
            if not isinstance(result, dict):
                result = {}

            title = self._safe_str(result.get("title")) or url
            summary = (
                self._safe_str(result.get("summary"))
                or self._safe_str(result.get("content"))[:1000]
                or f"Fetched {url}"
            )

            return {
                "ok": True,
                "title": title,
                "summary": summary,
                "source_url": self._safe_str(result.get("url")) or url,
                "raw": result,
                "saved_artifact": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "title": url,
                "summary": f"Web fetch failed: {e}",
                "source_url": url,
                "raw": {},
                "saved_artifact": None,
            }

    def _handle_attachment_analysis(self, user_text: str, attachments: list) -> dict:
        names = []
        for item in attachments:
            if isinstance(item, dict):
                name = self._safe_str(item.get("name") or item.get("filename"))
                if name:
                    names.append(name)

        if names:
            summary = f"I analyzed the uploaded attachment(s): {', '.join(names)}."
        else:
            summary = "I analyzed the uploaded attachment(s)."

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

    def _build_chat_input(self, user_text: str, decision: dict) -> str:
        if not decision.get("use_memory"):
            return user_text

        memory_items = self._rank_memory_context(
            user_text=user_text,
            limit=int(decision.get("memory_limit") or self.memory_limit),
        )
        memory_block = self._format_memory_context(memory_items)
        if not memory_block:
            return user_text

        return (
            "Relevant memory:\n"
            f"{memory_block}\n\n"
            "User message:\n"
            f"{user_text}"
        )

    def _run_chat_model(self, user_text: str, decision: dict) -> str:
        prompt = self._build_chat_input(user_text, decision)

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
        assistant_text = self._run_chat_model(user_text, decision)

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
        )

        if memory_items:
            lines = []
            limit = int(decision.get("memory_limit") or self.memory_limit)
            for item in memory_items[:limit]:
                text = self._safe_str(item.get("text"))
                if text:
                    lines.append(f"- {text}")
            assistant_text = "Here’s what I remember right now:\n" + "\n".join(lines)
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
        assistant_text = self._run_chat_model(user_text, decision)

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
        web_result = self._handle_web_fetch(self._safe_str(decision.get("url")))

        assistant_msg = self._build_assistant_message(
            text=self._safe_str(web_result.get("summary")) or "Web fetch completed.",
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
            saved_artifact=web_result.get("saved_artifact"),
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
        artifact_id = (
            self._safe_str(saved_artifact.get("id"))
            or self._safe_str(result.get("parent_artifact_id"))
        )

        assistant_msg = self._build_assistant_message(
            text=self._safe_str(result.get("text")) or f"Generated image for: {prompt}",
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