from __future__ import annotations

import base64
import os
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
from nova_backend.services.generated_media_service import GeneratedMediaService
from nova_backend.services.memory_ranker_service import MemoryRankerService
from nova_backend.services.memory_service import MemoryService
from nova_backend.services.memory_controller import MemoryController
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
        self.generated_media = GeneratedMediaService(UPLOADS_DIR)
        self.uploads_dir = Path(UPLOADS_DIR)

        self.web = web_service
        self.recon = recon_service

        self.client = OpenAI()

        self.agent = AgentService()
        self.memory_ranker = MemoryRankerService()
        self.memory_controller = MemoryController(self.memory)

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

        if not hasattr(self.artifacts, "get_latest_execution_run_for_session"):
            return False

        latest = self.artifacts.get_latest_execution_run_for_session(session_id)
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

        return new_goal == old_goal and new_summary == old_summary and new_steps == old_steps

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
        payload["debug"]["execution_persist_disabled"] = True

        payload.setdefault("assistant_message", {})
        payload["assistant_message"].setdefault("meta", {})
        payload["assistant_message"]["meta"]["execution"] = execution

        return payload

    def _build_memory_rules_block(
        self,
        force_memory: bool,
        memory_category: str,
        locked_preferences: dict | None = None,
    ) -> str:
        locked_preferences = locked_preferences or {}
        lines = [
            "Memory usage rules:",
            "- Do not invent personal facts.",
        ]

        if force_memory:
            if memory_category == "identity":
                lines.extend(
                    [
                        "- Memory is authoritative for identity questions.",
                        "- If the user asks who they are or what you know about them, you MUST use stored memory first.",
                        "- Do NOT say you do not know if relevant memory exists.",
                    ]
                )
            elif memory_category == "preferences":
                lines.extend(
                    [
                        "- Memory is authoritative for preference questions.",
                        "- If the user asks how they prefer things done, you MUST answer from stored memory first.",
                        "- Do NOT say you do not know if relevant memory exists.",
                    ]
                )
            elif memory_category == "project":
                lines.extend(
                    [
                        "- Memory is authoritative for project continuity questions.",
                        "- If the user asks what they are building, what is next, or where things stand, you MUST use stored memory first.",
                        "- Do NOT say you do not know if relevant memory exists.",
                    ]
                )
            else:
                lines.append("- Use memory strongly when relevant.")
        else:
            lines.append("- Use memory when clearly relevant.")

        if locked_preferences.get("response_style") == "direct":
            lines.append("- Response style is locked to direct.")

        if locked_preferences.get("full_file_only"):
            lines.append("- When giving code edits or file changes, prefer full-file responses.")

        if locked_preferences.get("powershell_only"):
            lines.append("- Prefer PowerShell commands for command-line instructions.")

        if locked_preferences.get("endgame_pace"):
            lines.append("- Keep the response efficient, decisive, and fast-moving.")

        return "\n".join(lines)

    def _response_failed_memory_use(
        self,
        user_text: str,
        response_text: str,
        relevant_memory: list,
    ) -> bool:
        user = str(user_text or "").strip().lower()
        resp = str(response_text or "").strip().lower()

        identity_like = any(
            phrase in user
            for phrase in [
                "who am i",
                "what do you know about me",
                "what do you remember about me",
                "what's my name",
                "do you remember me",
            ]
        )

        weak_patterns = [
            "i don't know who you are",
            "i do not know who you are",
            "tell me a bit about yourself",
            "from just that message",
            "i donâ€™t know who you are",
        ]

        if not identity_like:
            return False

        if not relevant_memory:
            return False

        return any(pattern in resp for pattern in weak_patterns)

    def _rewrite_identity_answer_from_memory(self, relevant_memory: list) -> str:
        memory_facts = []

        for item in relevant_memory[:6]:
            if not isinstance(item, dict):
                continue

            text = str(item.get("text") or "").strip()
            if text:
                memory_facts.append(f"- {text}")

        if not memory_facts:
            return "I know some things about you from memory, but I do not have enough clean identity context yet."

        return "From memory, hereâ€™s who you are in the ways I know you:\n" + "\n".join(memory_facts)

    def _get_relevant_memory_items(self, user_text: str, limit: int) -> list:
        try:
            if hasattr(self.memory, "get_relevant_memory"):
                items = self.memory.get_relevant_memory(user_text=user_text, limit=limit)
                if isinstance(items, list):
                    return items
        except Exception:
            pass

        try:
            if hasattr(self.memory_ranker, "get_relevant_memory"):
                items = self.memory_ranker.get_relevant_memory(
                    user_text=user_text,
                    memory_service=self.memory,
                    limit=limit,
                )
                if isinstance(items, list):
                    return items
        except Exception:
            pass

        try:
            if hasattr(self.memory, "list_memory"):
                items = self.memory.list_memory()
                if isinstance(items, list):
                    return items[:limit]
        except Exception:
            pass

        return []

    def handle(self, user_text: str, session_id: str = "", attachments=None):
        attachments = attachments or []

        user_msg = new_message(
            role="user",
            text=user_text,
            attachments=attachments,
        )

        assistant_msg = new_message(
            role="assistant",
            text="",
            attachments=[],
            meta={},
        )

        user_text = str(user_text or "").strip()
        text_lower = user_text.lower()

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

            return "Iâ€™m here, but the model returned an empty response."

        debug = {
            "route": "chat_service.handle",
            "attachments_count": len(attachments),
        }


        # ==============================
        # ATTACHMENT HANDLING
        # ==============================
        if attachments:
            try:
                assistant_msg = new_message(
                    role="assistant",
                    text="I received your attachment. Analysis coming next.",
                    attachments=[],
                    meta={"attachment_analysis": True},
                )

                return {
                    "ok": True,
                    "assistant_message": assistant_msg,
                    "debug": {
                        **debug,
                        "route_taken": "attachment_analysis",
                    },
                }

            except Exception as e:
                assistant_msg = new_message(
                    role="assistant",
                    text=f"Attachment processing failed: {e}",
                    attachments=[],
                    meta={
                        "attachment_analysis": True,
                        "attachment_error": str(e),
                    },
                )

                return {
                    "ok": True,
                    "assistant_message": assistant_msg,
                    "debug": {
                        **debug,
                        "attachment_error": str(e),
                    },
                }

        memory_decision = {
            "should_force_memory": False,
            "memory_reason": "",
            "memory_category": "general",
        }
        try:
            memory_decision = self.agent.classify_memory_priority(user_text)
        except Exception as e:
            debug["memory_decision_error"] = str(e)
            memory_decision = {
                "should_force_memory": False,
                "memory_reason": "",
                "memory_category": "general",
            }

        if "my name is" in text_lower:
            memory_decision["should_force_memory"] = True
            memory_decision["memory_category"] = "profile"

        force_memory = bool(memory_decision.get("should_force_memory"))
        memory_category = str(memory_decision.get("memory_category") or "general").strip().lower()
        memory_limit = 8 if force_memory else 4

        relevant_memory = self._get_relevant_memory_items(
            user_text=user_text,
            limit=memory_limit,
        )

        memory_control = self.memory_controller.apply(user_text, relevant_memory)
        ranked_memory = memory_control.get("ranked_memory") or relevant_memory
        if ranked_memory:
            relevant_memory = ranked_memory

        debug["memory_ranked"] = True
        debug["memory_top_scores"] = [
            {
                "text": str(m.get("text") or "")[:120],
                "score": m.get("memory_score"),
                "kind": m.get("kind"),
            }
            for m in relevant_memory[:3]
            if isinstance(m, dict)
        ]

        try:
            locked_preferences = self.agent.get_locked_preferences(relevant_memory)
        except Exception as e:
            locked_preferences = {}
            debug["locked_preferences_error"] = str(e)

        memory_lines = []
        for item in relevant_memory:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            kind = str(item.get("kind") or "memory").strip()
            if text:
                memory_lines.append(f"- ({kind}) {text}")

        memory_block = "Relevant memory:\n" + ("\n".join(memory_lines) if memory_lines else "- none")
        memory_rules = self._build_memory_rules_block(
            force_memory=force_memory,
            memory_category=memory_category,
            locked_preferences=locked_preferences,
        )

        if memory_control.get("override"):
            assistant_text = memory_control["text"]
            assistant_msg = new_message(
                role="assistant",
                text=assistant_text,
                attachments=[],
                meta={"memory_override": True},
            )

            payload = {
                "ok": True,
                "assistant_message": assistant_msg,
                "session": {
                    "id": session_id or "",
                    "messages": [user_msg, assistant_msg],
                },
                "debug": {
                    **debug,
                    "memory_override": True,
                    "memory_decision": memory_decision,
                    "memory_forced": force_memory,
                    "memory_items_used": len(relevant_memory),
                    "locked_preferences": locked_preferences,
                },
            }

            real_session_id = session_id or getattr(self.sessions, "active_session_id", "") or ""
            if real_session_id:
                try:
                    self.sessions.append_message(real_session_id, user_msg)
                    self.sessions.append_message(real_session_id, assistant_msg)
                    payload["session"] = self.sessions.get_session(real_session_id)
                    payload["sessions"] = self.sessions.get_all()
                    payload["active_session_id"] = self.sessions.active_session_id
                except Exception as e:
                    payload["debug"]["session_save_error"] = str(e)

            try:
                payload["memory"] = self.memory.list_memory()
            except Exception:
                pass

            return payload

        if self._is_image_generation_request(user_text):
            try:
                prompt = self._image_prompt_from_text(user_text)
                result = self._handle_image_generation(prompt)

                assistant_msg = new_message(
                    role="assistant",
                    text=result.get("text", "Image generated."),
                    attachments=[],
                    meta={
                        "image_generation": True,
                        "image_url": result.get("image_url", ""),
                    },
                )

                payload = {
                    "ok": True,
                    "assistant_message": assistant_msg,
                    "debug": {
                        **debug,
                        "route_taken": "image_generation",
                    },
                }

                if result.get("artifact"):
                    payload["saved_artifact"] = {
                        "saved": True,
                        "artifact": result["artifact"],
                    }

                active_session_id = session_id or ""
                if not active_session_id and hasattr(self.sessions, "create_session"):
                    created = self.sessions.create_session(title="New Chat")
                    if isinstance(created, dict):
                        active_session_id = str(created.get("id") or "").strip()

                if active_session_id:
                    try:
                        if hasattr(self.sessions, "append_message"):
                            self.sessions.append_message(active_session_id, user_msg)
                            self.sessions.append_message(active_session_id, assistant_msg)
                            payload["session"] = self.sessions.get_session(active_session_id)
                            payload["sessions"] = self.sessions.get_all()
                            payload["active_session_id"] = self.sessions.active_session_id
                        elif hasattr(self.sessions, "add_message_to_session"):
                            self.sessions.add_message_to_session(active_session_id, user_msg)
                            self.sessions.add_message_to_session(active_session_id, assistant_msg)
                    except Exception as e:
                        payload.setdefault("debug", {})
                        payload["debug"]["session_save_error"] = str(e)

                try:
                    payload["memory"] = self.memory.list_memory()
                except Exception:
                    pass

                return payload

            except Exception as e:
                import traceback
                traceback.print_exc()

                assistant_msg = new_message(
                    role="assistant",
                    text=f"Image generation failed: {e}",
                    attachments=[],
                    meta={"image_generation": True, "image_error": str(e)},
                )

                return {
                    "ok": True,
                    "assistant_message": assistant_msg,
                    "debug": {
                        **debug,
                        "route_taken": "image_generation",
                        "image_error": str(e),
                    },
                }

        try:
            prompt_parts = [
                "You are Nova, a capable local AI assistant.",
                "Respond clearly, directly, and helpfully.",
                memory_rules,
                memory_block,
                f"User message:\n{user_text}",
            ]
            composed_input = "\n\n".join(part for part in prompt_parts if part)

            response = self.client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-5.4"),
                input=composed_input,
            )
            assistant_text = extract_response_text(response)
            debug["route_taken"] = "chat"
        except Exception as e:
            assistant_text = f"I hit an error while generating a response: {e}"
            debug["model_error"] = str(e)
            debug["route_taken"] = "chat_error"

        if self._response_failed_memory_use(user_text, assistant_text, relevant_memory):
            assistant_text = self._rewrite_identity_answer_from_memory(relevant_memory)
            debug["memory_rewrite_applied"] = True

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

        payload = self._attach_execution(
            payload=payload,
            user_text=user_text,
            assistant_msg=assistant_msg,
            decision={"mode": "chat", "use_tools": False},
            session_id=session_id or "",
        )

        try:
            active_session_id = payload.get("session", {}).get("id") or session_id or ""

            if hasattr(self.sessions, "append_message"):
                if not active_session_id and hasattr(self.sessions, "create_session"):
                    created = self.sessions.create_session(title="New Chat")
                    if isinstance(created, dict):
                        active_session_id = str(created.get("id") or "").strip()

                if active_session_id:
                    self.sessions.append_message(active_session_id, user_msg)
                    self.sessions.append_message(active_session_id, assistant_msg)
                    payload["session"] = self.sessions.get_session(active_session_id)
                    payload["sessions"] = self.sessions.get_all()
                    payload["active_session_id"] = self.sessions.active_session_id

            elif hasattr(self.sessions, "add_message_to_session"):
                if not active_session_id and hasattr(self.sessions, "create_session"):
                    created = self.sessions.create_session(title="New Chat")
                    if isinstance(created, dict):
                        active_session_id = str(created.get("id") or "").strip()

                if active_session_id:
                    self.sessions.add_message_to_session(active_session_id, user_msg)
                    self.sessions.add_message_to_session(active_session_id, assistant_msg)

        except Exception as e:
            payload.setdefault("debug", {})
            payload["debug"]["session_save_error"] = str(e)

        try:
            real_session_id = payload.get("session", {}).get("id") or session_id or ""
            payload.setdefault("debug", {})
            payload["debug"]["memory_write_attempted"] = True
            payload["debug"]["memory_write_session_id"] = real_session_id

            if "my name is" in text_lower:
                remembered_name = user_text.split("my name is", 1)[1].strip()
                if remembered_name:
                    self.memory.add_memory(
                        text=f"name: {remembered_name}",
                        kind="profile",
                        source="user",
                        session_id=real_session_id,
                    )
                    payload["debug"]["memory_write_saved"] = True
                    payload["debug"]["memory_write_text"] = f"name: {remembered_name}"
                else:
                    payload["debug"]["memory_write_saved"] = False
                    payload["debug"]["memory_write_reason"] = "empty_name_after_parse"

            elif memory_decision.get("should_force_memory"):
                self.memory.add_memory(
                    text=user_text,
                    kind=memory_decision.get("memory_category", "general"),
                    source="user",
                    session_id=real_session_id,
                )
                payload["debug"]["memory_write_saved"] = True
                payload["debug"]["memory_write_text"] = user_text
            else:
                payload["debug"]["memory_write_saved"] = False
                payload["debug"]["memory_write_reason"] = "memory_decision_false"

        except Exception as e:
            payload.setdefault("debug", {})
            payload["debug"]["memory_write_error"] = str(e)

        try:
            payload["memory"] = self.memory.list_memory()
        except Exception:
            pass

        return payload

    # ==============================
    # IMAGE HELPERS
    # ==============================

    def _handle_image_generation(self, prompt: str) -> dict:
        print("[IMAGE] START")

        try:
            self.uploads_dir.mkdir(parents=True, exist_ok=True)

            print("[IMAGE] CALLING OPENAI")
            result = self.client.images.generate(
                model=os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1.5"),
                prompt=prompt,
                size="1024x1024",
            )
            print("[IMAGE] RESPONSE RECEIVED")

            image_base64 = result.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)

            filename = f"generated_{uuid.uuid4().hex}.png"
            filepath = self.uploads_dir / filename

            with open(filepath, "wb") as f:
                f.write(image_bytes)

            image_url = f"/api/uploads/{filename}"
            print("[IMAGE] SAVED:", image_url)

            artifact = {
                "id": f"artifact_{uuid.uuid4().hex}",
                "kind": "image_generation",
                "title": "Generated Image",
                "preview": prompt[:120],
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "session_id": "",
                "viewer": {
                    "kind": "image",
                    "image_url": image_url,
                    "body": prompt,
                },
                "meta": {
                    "prompt": prompt,
                    "image_url": image_url,
                },
            }

            return {
                "text": f"Generated image for: {prompt}",
                "image_url": image_url,
                "artifact": artifact,
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            print("[IMAGE] FAILED:", str(e))
            return {
                "text": f"Image generation failed: {str(e)}",
                "image_url": "",
            }

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
