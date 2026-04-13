from __future__ import annotations

import base64
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from urllib.parse import unquote, urlparse

from openai import OpenAI

from nova_backend.config import UPLOADS_DIR
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
    # EXECUTION SYSTEM
    # ==============================

    # ==============================
    # EXECUTION SYSTEM
    # ==============================

    def _iso_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _clean_execution_text(self, value: str | None) -> str:
        text = str(value or "").strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

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

        if "plan" in lowered:
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

    def _execution_mark_running(self, execution: dict | None, step_index: int = 0) -> dict | None:
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

    def _execution_mark_completed(self, execution: dict | None, assistant_text: str = "") -> dict | None:
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

    def _execution_mark_failed(self, execution: dict | None, error_text: str = "") -> dict | None:
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

        if not hasattr(self.artifacts, "get_latest_execution_run_for_session"):
            return False

        latest = self.artifacts.get_latest_execution_run_for_session(session_id)
        if not latest:
            return False

        latest_meta = latest.get("meta") if isinstance(latest, dict) else {}
        latest_execution = (
            latest_meta.get("execution")
            if isinstance(latest_meta, dict)
            else {}
        )
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

        if hasattr(self.artifacts, "save_execution_run"):
            self.artifacts.save_execution_run(
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


    def handle(self, user_text: str, session_id: str = "", attachments=None):
        attachments = attachments or []
        user_text = str(user_text or "").strip()

        user_msg = new_message(
            role="user",
            text=user_text,
            attachments=attachments,
            meta={},
        )

        if not user_text:
            assistant_msg = new_message(
                role="assistant",
                text="Please enter a message.",
                attachments=[],
                meta={},
            )
            return {
                "ok": True,
                "assistant_message": assistant_msg,
                "session": {
                    "id": session_id or "",
                    "messages": [user_msg, assistant_msg] if user_text else [assistant_msg],
                },
                "debug": {
                    "route": "chat_service.handle",
                    "attachments_count": len(attachments),
                    "empty_input": True,
                },
            }

        def extract_response_text(resp) -> str:
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

        debug = {
            "route": "chat_service.handle",
            "attachments_count": len(attachments),
        }

        try:
            response = self.client.responses.create(
                model="gpt-5.4",
                input=user_text,
            )
            assistant_text = extract_response_text(response)
            debug["model"] = "gpt-5.4"
            debug["used_openai"] = True
        except Exception as e:
            assistant_text = f"Model error: {e}"
            debug["used_openai"] = False
            debug["model_error"] = str(e)

        assistant_msg = new_message(
            role="assistant",
            text=assistant_text,
            attachments=[],
            meta={},
        )

        payload = {
            "ok": True,
            "assistant_message": assistant_msg,
            "session": {
                "id": session_id or "",
                "messages": [user_msg, assistant_msg],
            },
            "debug": debug,
        }

        return self._attach_execution(
            payload,
            user_text,
            assistant_msg,
            {},
            session_id=session_id,
        )

      
    def _execution_step_titles_for_goal(self, goal: str) -> list[str]:
        lowered = str(goal or "").lower()

        if "hosting" in lowered:
            return [
                "Identify hosting options",
                "Compare tradeoffs",
                "Recommend best fit",
            ]

        if "plan" in lowered:
            return [
                "Define the goal",
                "Break into steps",
                "Return recommendation",
            ]

        return [
            "Understand request",
            "Process task",
            "Return result",
        ]

    def _build_execution_planned(
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

        steps = []
        for i, title in enumerate(step_titles, start=1):
            steps.append(
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
            "steps": steps,
            "started_at": now_iso,
            "updated_at": now_iso,
        }

    def _execution_mark_running(self, execution: dict | None, step_index: int = 0) -> dict | None:
        if not isinstance(execution, dict):
            return execution

        steps = execution.get("steps")
        if not isinstance(steps, list) or not steps:
            execution["status"] = "running"
            execution["updated_at"] = self._iso_now()
            return execution

        for step in steps:
            if isinstance(step, dict) and step.get("status") not in ("completed", "failed"):
                step["status"] = "planned"

        target = steps[min(max(step_index, 0), len(steps) - 1)]
        if isinstance(target, dict):
            target["status"] = "running"
            execution["current_step"] = str(target.get("title") or "").strip()

        execution["status"] = "running"
        execution["updated_at"] = self._iso_now()
        return execution

    def _execution_mark_completed(self, execution: dict | None, assistant_text: str = "") -> dict | None:
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

    def _execution_mark_failed(self, execution: dict | None, error_text: str = "") -> dict | None:
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

    # ==============================
    # IMAGE HELPERS
    # ==============================

    def _is_image_generation_request(self, user_text: str) -> bool:
        text = str(user_text or "").strip().lower()
        if not text:
            return False

        triggers = (
            "/image",
            "generate an image",
            "generate image",
            "make an image",
            "create an image",
            "draw ",
            "draw me ",
        )
        return any(text.startswith(trigger) for trigger in triggers)

    def _image_prompt_from_text(self, user_text: str) -> str:
        text = str(user_text or "").strip()
        lowered = text.lower()

        # /image command support
        if lowered.startswith("/image"):
            prompt = text[6:].strip()
            return prompt or "Generate an image."

        # natural language triggers
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

        # fallback → return original text
        return text or "Generate an image."