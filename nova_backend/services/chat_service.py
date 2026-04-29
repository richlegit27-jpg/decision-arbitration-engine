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
from nova_backend.services.response_rewrite_service import ResponseRewriteService
from nova_backend.services.recon_service import ReconService
from nova_backend.services.session_service import SessionService
from nova_backend.services.web_service import WebService
from nova_backend.services.tool_service import ToolService
from nova_backend.services.execution_service import ExecutionService
from nova_backend.services.intent_service import IntentService



class ChatService:
    ROUTE_GENERAL_CHAT = "general_chat"
    ROUTE_IMAGE_GENERATION = "image_generation"
    ROUTE_WEB_FETCH = "web_fetch"
    ROUTE_ATTACHMENT_ANALYSIS = "attachment_analysis"
    ROUTE_PLANNING = "planning"
    ROUTE_MEMORY_RECALL = "memory_recall"

    def _source_quality_score(self, url: str = "", title: str = "") -> int:
        text = f"{url} {title}".lower()

        bad_domains = [
            "instagram.com",
            "facebook.com",
            "tiktok.com",
            "pinterest.com",
            "threads.net",
        ]

        if any(domain in text for domain in bad_domains):
            return -999

        official_sources = [
            "nba.com",
            "pistons.com",
        ]

        top_news_sources = [
            "usatoday.com",
            "sportsillustrated.com",
            "si.com",
            "espn.com",
            "apnews.com",
            "reuters.com",
        ]

        decent_sources = [
            "heavy.com",
            "yahoo.com",
            "cbssports.com",
            "bleacherreport.com",
        ]

        if any(domain in text for domain in official_sources):
            return 100

        if any(domain in text for domain in top_news_sources):
            return 80

        if any(domain in text for domain in decent_sources):
            return 55

        return 10

    def __init__(
        self,
        session_service: SessionService,
        memory_service: MemoryService,
        artifact_service: ArtifactService,
        web_service: WebService,
        recon_service: ReconService,
    ):
        self.session_service = session_service
        self.memory_service = memory_service
        self.artifact_service = artifact_service
        self.web_service = web_service
        self.recon_service = recon_service
        self.rewrite_service = ResponseRewriteService()

        self.sessions = session_service
        self.memory = memory_service
        self.artifacts = artifact_service
        self.web = web_service
        self.recon = recon_service

        self.image_model = os.getenv("NOVA_IMAGE_MODEL", "gpt-image-1")
        self.image_size = os.getenv("NOVA_IMAGE_SIZE", "1024x1024")
        self.chat_model = os.getenv("OPENAI_MODEL", "gpt-5.4")
        self.model = self.chat_model
        print("MODEL CHECK:", hasattr(self, "model"), self.model)
        self.memory_limit = int(os.getenv("NOVA_MEMORY_LIMIT", "3"))
        self.execution_service = ExecutionService()
        self.intent_service = IntentService()
        self.uploads_dir = Path(
            os.getenv("UPLOADS_DIR", r"C:\Users\Owner\nova\uploads")
        )
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        print("CHATSERVICE INIT uploads_dir =", self.uploads_dir)

        self.client = OpenAI()
        self.agent = AgentService()
        self.memory_ranker = MemoryRankerService()
        self.tools = ToolService(base_dir=os.getcwd())

        self.autonomy = AutonomyService(
            web_service=self.web,
            recon_service=self.recon,
            memory_service=self.memory,
            artifact_service=self.artifacts,
            max_steps=5,
            max_deep_js=5,
            max_follow_links=5,
        )

 
    def _build_user_message(self, text: str, attachments=None, meta=None) -> dict:
        attachments = attachments or []
        meta = meta or {}
        return {
            "role": "user",
            "text": self._safe_str(text),
            "attachments": attachments,
            "meta": meta,
        }

    def _build_assistant_message(
        self,
        text: str,
        attachments=None,
        meta=None,
        memory_used=None,
    ) -> dict:
        attachments = attachments or []
        meta = meta or {}

        return {
            "role": "assistant",
            "text": self._safe_str(text),
            "attachments": attachments,
            "meta": meta,
            "memory_used": memory_used or [],
        }

    def _finalize_response(
        self,
        session_id: str = "",
        user_text: str = "",
        user_msg=None,
        assistant_msg=None,
        decision=None,
        saved_artifact=None,
        working_context_payload=None,
        should_inject_working_context=False,
    ) -> dict:

        decision = decision if isinstance(decision, dict) else {}

        session_id = self._ensure_session_id(session_id)

        session = self._get_session_payload(session_id) or {}
        messages = session.get("messages")
        if not isinstance(messages, list):
            messages = []

        if isinstance(user_msg, dict):
            messages.append(user_msg)

        if isinstance(assistant_msg, dict):
            messages.append(assistant_msg)

        session["id"] = session_id
        session["messages"] = messages

        try:
            existing = self.sessions.get_session(session_id)
            existing_messages = existing.get("messages", []) if isinstance(existing, dict) else []
            existing_count = len(existing_messages) if isinstance(existing_messages, list) else 0

            for msg in messages[existing_count:]:
                self.sessions.append_message(session_id, msg)

        except Exception as e:
            print("SESSION SAVE ERROR:", e)

        return {
            "ok": True,
            "assistant_message": assistant_msg,
            "session": {
                **session,
                "id": session_id,
            },
            "active_session_id": session_id,
            "session_id": session_id,
            "saved_artifact": saved_artifact,
            "artifacts": self._get_artifacts_list(),
            "memory": self._get_memory_list(),
            "sessions": self._get_sessions_list(),
            "debug": {
                "decision": decision,
                "route": "chat_service.handle",
                "route_taken": decision.get("route") if isinstance(decision, dict) else "",
            },
        }

    def _execute_general_chat(
        self,
        decision=None,
        user_text: str = "",
        session_id: str = "",
        attachments=None,
        memory_context="",
        working_context_block="",
        working_state=None,
    ) -> dict:

        decision = decision if isinstance(decision, dict) else {}
        attachments = attachments or []

        original_user_text = user_text
        text_lc = (user_text or "").lower()

        execution_keywords = [
            "build", "create", "make", "fix", "implement",
            "add", "write", "generate", "set up"
        ]
        is_execution = any(k in text_lc for k in execution_keywords)

        continue_triggers = ["continue", "next", "run it", "go"]
        is_continue = any(k == text_lc.strip() for k in continue_triggers)

        session = self._get_session_payload(session_id)
        state = session.get("working_state") if isinstance(session, dict) else {}
        state = state or {}

        mission_mode = self._safe_str(state.get("mission_mode"))

        active_task = self._safe_str(state.get("active_task"))
        next_step = self._safe_str(state.get("next_step"))

        if is_continue:
            mission = decision.get("mission") if isinstance(decision, dict) else {}
            mission = mission if isinstance(mission, dict) else {}

            if active_task:
                user_text = f"Continue task: {active_task}. Next step: {next_step}"
            else:
                user_text = (
                    "Continue current Nova build phase. "
                    f"Mission mode: {mission.get('mode') or 'continue'}. "
                    f"Next move: {mission.get('next_move') or 'Choose the next concrete implementation step.'}"
                )

        user_msg = self._build_user_message(
            original_user_text,
            attachments=attachments,
        )

        if not memory_context:
            memory_context = self._build_memory_context_for_chat(user_text, decision)

        model_messages = self._compose_model_messages(
            user_text=user_text,
            session=session,
            decision=decision,
            memory_context=memory_context,
        )

        if is_execution or active_task:
            model_messages.insert(0, {
                "role": "system",
                "content": (
                    "You are an execution-focused AI.\n"
                    f"Current task: {active_task or original_user_text}\n"
                    f"Next step hint: {next_step}\n\n"
                    "Rules:\n"
                    "- Be direct.\n"
                    "- Output real work: code, commands, files, or exact actions.\n"
                    "- Do not stop at explanation.\n"
                    "- Always move the task forward."
                )
            })

        mission = decision.get("mission") if isinstance(decision, dict) else {}
        mission_mode = str(mission.get("mode") or "").lower()

        if is_continue and mission_mode == "debugging":
            assistant_text = (
                "Next move:\n\n"
                "Paste the exact compile error so we can fix it."
            )

            assistant_msg = self._build_assistant_message(
                text=assistant_text,
                attachments=[],
                meta={"forced": "continue_debug"},
            )

            return self._finalize_response(
                session_id=session_id,
                user_text=original_user_text,
                user_msg=user_msg,
                assistant_msg=assistant_msg,
                decision=decision,
                saved_artifact=None,
            ) 
        if mission_mode == "full_file":
            assistant_text = (
                "SMFF mode active.\n\n"
                "Send the file name, function, or task.\n"
                "I will return full file or full replacement.\n"
                "No partial snippets."
            )

            assistant_msg = self._build_assistant_message(
                text=assistant_text,
                attachments=[],
                meta={"forced": "smff"},
            )

            return self._finalize_response(
                session_id=session_id,
                user_text=original_user_text,
                user_msg=user_msg,
                assistant_msg=assistant_msg,
                decision=decision,
                saved_artifact=None,
            )

        try:
            response = self.client.responses.create(
                model=self.chat_model,
                input=model_messages,
            )
            assistant_text = self._extract_response_text(response)

        except Exception as e:
            print("GENERAL CHAT ERROR:", e)
            assistant_text = "Something went wrong."

        if not assistant_text:
            assistant_text = "No response generated."

        intelligence_result = self._apply_response_intelligence(
            user_text=user_text,
            assistant_text=assistant_text,
            decision=decision,
        )

        assistant_text = intelligence_result.get("assistant_text", assistant_text)
        intelligence = intelligence_result.get("intelligence", {})
        self_check = intelligence_result.get("self_check", {})
        hard_override_applied = bool(intelligence_result.get("hard_override_applied"))

        # Optional: enforce short mode hard clamp
        if isinstance(intelligence, dict):
            answer_length = str(intelligence.get("answer_length") or "").lower()
            if answer_length == "short" and len(assistant_text.split()) > 120:
                assistant_text = " ".join(assistant_text.split()[:120])

        # === INTELLIGENCE LAYER END ===

        next_step_out = ""
        try:
            for line in (assistant_text or "").split("\n"):
                if "step" in line.lower():
                    next_step_out = line.strip()
                    break
        except Exception:
            pass

        used_memory_items = getattr(self, "_last_used_memory_items", []) or []

        memory_text = " ".join([
            self._safe_str(m.get("text"))
            for m in used_memory_items
            if isinstance(m, dict)
        ]).lower()

        if "name is richard" in memory_text:
            if "your name is" in (assistant_text or "").lower():
                assistant_text = "Your name is Richard."

        try:
            if any(x in memory_text for x in ["prefer direct", "be direct", "no fluff", "keep answers short"]):
                assistant_text = (assistant_text or "").strip()
        except Exception as e:
            print("STYLE CLAMP ERROR:", e)

        used_memory_full = [
            {
                "id": self._safe_str(m.get("id")),
                "text": self._safe_str(m.get("text")),
                "kind": self._safe_str(m.get("kind")),
                "pinned": bool(m.get("pinned")),
                "weight": m.get("weight", 1),
            }
            for m in used_memory_items
            if isinstance(m, dict) and self._safe_str(m.get("text"))
        ]

        meta_payload = {
            "memory_dominance": {
                "enabled": True,
                "used_count": len(used_memory_full),
                "top_memory": used_memory_full[:3],
            },

            # === CHAT POLISH: STRATEGY / MISSION FEED ===
            "mission": decision.get("mission", {}) if isinstance(decision, dict) else {},
            "strategy": decision.get("strategy", "") if isinstance(decision, dict) else "",

            # === MEMORY ===
            "used_memory": used_memory_full,
            "used_memory_count": len(used_memory_full),
            "memory_confidence": 1.0,

            # === EXECUTION STATE ===
            "execution_mode": bool(is_execution or active_task),
            "active_task": (
                active_task or original_user_text
                if is_execution
                else active_task
            ),
            "next_step": next_step_out,
        }

        # === BUILD FINAL MESSAGE ===
        if assistant_text:
            assistant_msg = self._build_assistant_message(
                text=assistant_text,
                attachments=[],
                meta=meta_payload,
            )
        else:
            assistant_msg = self._build_assistant_message(
                text="No response generated.",
                attachments=[],
                meta=meta_payload,
            )

        return self._finalize_response(
            session_id=session_id,
            user_text=original_user_text,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            decision=decision,
            saved_artifact=None,
        )

    def _resolve_answer_length_preference(self, user_text: str, memory_items: list) -> str:
        """
        Returns: "short" | "long" | "normal"
        Priority:
        1. current user message
        2. latest preference memory
        3. default
        """

        user_text_lc = str(user_text or "").lower().strip()

        # ðŸ”¥ 1. HARD USER OVERRIDE (strongest)
        if any(p in user_text_lc for p in [
            "don't give short",
            "dont give short",
            "no short answers",
            "long answers",
            "full answers",
            "more detail",
            "explain more",
        ]):
            return "long"

        if any(p in user_text_lc for p in [
            "short answers",
            "keep it short",
            "be concise",
            "quick answer",
            "one sentence",
        ]):
            return "short"

        # ðŸ”¥ 2. MEMORY (most recent wins)
        for m in reversed(memory_items or []):
            if not isinstance(m, dict):
                continue

            text = str(m.get("text") or "").lower()

            if "long answers" in text or "full answers" in text:
                return "long"

            if "short answers" in text:
                return "short"

        # ðŸ”¥ 3. DEFAULT
        return "normal"

    def _apply_pending_fix(self, session_id: str) -> dict:
        session = self._get_session_payload(session_id)

        pending_file_path = ""
        pending_fix_code = ""

        if isinstance(session, dict):
            state = session.get("working_state") or {}
            pending_file_path = self._safe_str(state.get("pending_fix_file_path"))
            pending_fix_code = self._safe_str(state.get("pending_fix_code"))

        user_msg = self._build_user_message("apply fix")

        decision = {
            "route": "auto_fix_apply",
            "intent": "debugging",
        }

        if not pending_file_path or not pending_fix_code:
            assistant_msg = self._build_assistant_message(
                text="No pending fix found. Run `fix this file` first."
            )
            return self._finalize_response(
                session_id=session_id,
                user_text="apply fix",
                user_msg=user_msg,
                assistant_msg=assistant_msg,
                decision=decision,
            )

        try:
            with open(pending_file_path, "r", encoding="utf-8") as f:
                current_content = f.read()

            backup_path = pending_file_path + ".autofix.bak"

            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(current_content)

            with open(pending_file_path, "w", encoding="utf-8") as f:
                f.write(pending_fix_code)

            self._set_session_meta(session_id, "pending_fix_file_path", "")
            self._set_session_meta(session_id, "pending_fix_code", "")

            assistant_msg = self._build_assistant_message(
                text=f"Fix applied.\n\nBackup created:\n{backup_path}\n\nFile updated:\n{pending_file_path}"
            )

            return self._finalize_response(
                session_id=session_id,
                user_text="apply fix",
                user_msg=user_msg,
                assistant_msg=assistant_msg,
                decision=decision,
            )

        except Exception as e:
            print("APPLY FIX FAILED:", e)

            assistant_msg = self._build_assistant_message(
                text=f"Could not apply pending fix: {type(e).__name__}: {self._safe_str(e)}"
            )

        return self._finalize_response(
            session_id=session_id,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            decision=decision,
        )

    def _fuse_response_intelligence(
        self,
        user_text: str = "",
        assistant_text: str = "",
        decision=None,
    ) -> dict:

        decision = decision if isinstance(decision, dict) else {}

        user_lc = str(user_text or "").lower().strip()
        assistant_lc = str(assistant_text or "").lower().strip()

        route = str(decision.get("route") or "").lower()
        mode = str(decision.get("mode") or "").lower()
        intent = str(decision.get("intent") or mode or route or "chat").lower()

        needs_explanation = any(
            phrase in user_lc
            for phrase in [
                "why",
                "what does",
                "what is",
                "explain",
                "how does",
                "how do",
            ]
        )

        is_debugging = any(
            phrase in user_lc
            for phrase in [
                "bug",
                "fix",
                "error",
                "traceback",
                "exception",
                "broken",
                "not working",
                "500",
                "syntaxerror",
                "indentationerror",
                "taberror",
            ]
        )

        wants_code = any(
            phrase in user_lc
            for phrase in [
                "smff",
                "full file",
                "full code",
                "replace",
                "paste this",
                "code",
                "function",
                "class",
            ]
        )

        wants_short = any(
            phrase in user_lc
            for phrase in [
                "short",
                "quick",
                "tldr",
                "direct",
                "no yapping",
                "don't talk too much",
            ]
        )

        if is_debugging:
            intent = "debugging"
        elif wants_code:
            intent = "coding"
        elif needs_explanation:
            intent = "explanation"

        if wants_short:
            answer_length = "short"
        elif intent in ["debugging", "coding"]:
            answer_length = "actionable"
        elif needs_explanation:
            answer_length = "normal"
        else:
            answer_length = "short"

        style_rules = []

        if intent == "debugging":
            style_rules.extend([
                "Give the likely cause first.",
                "Give the exact next fix or command.",
                "Do not ask for pasted files unless there is no actionable next step.",
                "Prefer file path, anchor, and replacement instructions.",
            ])

        elif intent == "coding":
            style_rules.extend([
                "Prefer full-file or exact replacement code.",
                "Include the file path when known.",
                "Avoid partial vague snippets.",
            ])

        elif intent == "explanation":
            style_rules.extend([
                "Explain clearly.",
                "Use concrete terms.",
                "Keep the answer structured but not bloated.",
            ])

        else:
            style_rules.extend([
                "Be concise.",
                "Answer directly.",
                "Avoid generic chatbot filler.",
            ])

        if intent == "debugging":
            next_action = "Give exact fix, command, file path, or anchor."
        elif intent == "coding":
            next_action = "Provide full-file code or exact replacement instructions."
        elif intent == "explanation":
            next_action = "Explain clearly, then summarize the core takeaway."
        else:
            next_action = "Answer directly and avoid filler."

        return {
            "intent": intent,
            "route": route,
            "mode": mode,
            "answer_length": answer_length,
            "needs_explanation": needs_explanation,
            "is_debugging": is_debugging,
            "wants_code": wants_code,
            "wants_short": wants_short,
            "style_rules": style_rules,
            "assistant_word_count": len(assistant_lc.split()),
        }

    def _self_check_response(
        self,
        user_text: str = "",
        assistant_text: str = "",
        intelligence=None,
    ) -> dict:

        intelligence = intelligence if isinstance(intelligence, dict) else {}

        user_text_lc = str(user_text or "").lower().strip()
        assistant_text = str(assistant_text or "").strip()
        assistant_lc = assistant_text.lower()

        answer_length = str(intelligence.get("answer_length") or "normal").lower()
        needs_explanation = bool(intelligence.get("needs_explanation"))
        intent = str(intelligence.get("intent") or "").lower()
        mode = str(intelligence.get("mode") or "").lower()

        word_count = len(assistant_text.split())
        issues = []
        should_revise = False

        debugging_signals = [
            "bug",
            "fix",
            "error",
            "traceback",
            "exception",
            "broken",
            "not working",
            "500",
            "syntaxerror",
            "indentationerror",
            "taberror",
        ]

        weak_phrases = [
            "paste it here",
            "paste the bug context",
            "send me the file",
            "send the code",
            "send one of these",
            "send the code and",
            "whatâ€™s the symptom",
            "what's the symptom",
            "tell me what you need",
            "i can help",
            "if you want",
            "provide more details",
            "please provide",
        ]

        is_debugging = (
            intent == "debugging"
            or mode == "debugging"
            or any(signal in user_text_lc for signal in debugging_signals)
        )

        if not assistant_text:
            issues.append("empty_response")
            should_revise = True

        if any(phrase in assistant_lc for phrase in weak_phrases):
            issues.append("weak_generic_phrase")
            should_revise = True

        if is_debugging and word_count < 35:
            issues.append("debugging_answer_too_thin")
            should_revise = True

        if is_debugging and "paste" in assistant_lc and "exact" not in assistant_lc:
            issues.append("lazy_debugging_response")
            should_revise = True

        if needs_explanation and word_count < 35:
            issues.append("too_short_for_explanation")
            should_revise = True

        if "what is" in user_text_lc and word_count < 25:
            issues.append("weak_definition")
            should_revise = True

        if answer_length == "short" and word_count > 120:
            issues.append("too_long_for_short_mode")
            should_revise = True

        return {
            "should_revise": should_revise,
            "issues": issues,
            "word_count": word_count,
            "is_debugging": is_debugging,
        }

    def _build_response_policy(self, user_text: str = "", decision=None) -> dict:
        """
        Central response policy layer.

        This does NOT answer the user.
        It tells Nova HOW to answer:
        - short/direct
        - SMFF/full-file mode
        - debugging mode
        - frustrated user mode
        - latest/news mode
        - command-first mode
        """

        decision = decision if isinstance(decision, dict) else {}
        text = str(user_text or "").strip()
        lower = text.lower()

        policy = {
            "mode": "normal",
            "answer_length": "normal",
            "tone": "direct",
            "needs_steps": False,
            "needs_full_file": False,
            "needs_commands": False,
            "needs_latest": False,
            "needs_debug": False,
            "user_frustrated": False,
            "avoid_examples": False,
            "prefer_power_shell": True,
            "instruction": "",
        }

        # -----------------------------
        # User frustration / urgency
        # -----------------------------
        frustration_markers = [
            "fuck",
            "wtf",
            "this sucks",
            "waste of time",
            "madness",
            "annoying",
            "broken again",
            "i don't know what to do",
            "im lost",
            "i'm lost",
        ]

        if any(marker in lower for marker in frustration_markers):
            policy["user_frustrated"] = True
            policy["tone"] = "calm_direct"
            policy["answer_length"] = "short"
            policy["needs_steps"] = True

            policy["instruction"] += (
                "User is frustrated. Do not lecture. Do not explain feelings. "
                "Give the fix first. Use short confident language. "
                "One path forward only. Maximum 5 lines unless full code is requested.\n"
            )

        # -----------------------------
        # SMFF / full-file mode
        # -----------------------------
        smff_markers = [
            "smff",
            "full file",
            "whole file",
            "give me the whole",
            "full replacement",
            "replace the whole",
        ]

        if any(marker in lower for marker in smff_markers):
            policy["mode"] = "smff"
            policy["needs_full_file"] = True
            policy["answer_length"] = "full"
            policy["avoid_examples"] = True
            policy["instruction"] += (
                "User wants SMFF/full-file style. Provide complete replacement code "
                "or a complete helper block with exact file path and anchor. "
                "Avoid tiny partial snippets unless the user only pasted a small block.\n"
            )

        # -----------------------------
        # Debugging mode
        # -----------------------------
        debug_markers = [
            "error",
            "traceback",
            "syntaxerror",
            "indentationerror",
            "taberror",
            "uncaught",
            "404",
            "500",
            "not found",
            "failed to load",
            "broken",
            "compile",
        ]

        if any(marker in lower for marker in debug_markers):
            policy["needs_debug"] = True
            policy["needs_steps"] = True
            policy["needs_commands"] = True
            policy["answer_length"] = "short"
            policy["instruction"] += (
                "User is debugging. Identify the root cause first, then give the exact "
                "replacement or exact command. Do not wander.\n"
            )

        # -----------------------------
        # Next-step mode
        # -----------------------------
        next_markers = [
            "next",
            "what now",
            "what next",
            "go",
            "continue",
            "keep going",
        ]

        if lower in next_markers:
            policy["mode"] = "next_step"
            policy["needs_steps"] = True
            policy["answer_length"] = "ultra_short"
            policy["instruction"] += (
                "User said next. Reply with ONE concrete next action only. "
                "No explanation. No menu. No markdown essay. Maximum 3 short lines.\n"
            )

        # -----------------------------
        # Latest/news mode
        # -----------------------------
        latest_markers = [
            "latest",
            "fresh",
            "today",
            "current",
            "right now",
            "news",
            "update",
        ]

        if any(marker in lower for marker in latest_markers):
            policy["needs_latest"] = True
            policy["instruction"] += (
                "User wants current information. Prefer fresh web/search route when available. "
                "Answer in words first, then sources if useful.\n"
            )

        # -----------------------------
        # PowerShell / command mode
        # -----------------------------
        command_markers = [
            "powershell",
            "command",
            "run this",
            "compile",
            "restart",
            "test",
        ]

        if any(marker in lower for marker in command_markers):
            policy["needs_commands"] = True
            policy["prefer_power_shell"] = True
            policy["instruction"] += (
                "Use PowerShell commands when commands are needed.\n"
            )

        # -----------------------------
        # User dislikes examples
        # -----------------------------
        no_example_markers = [
            "no examples",
            "don't give examples",
            "dont give examples",
            "just the code",
            "only the code",
        ]

        if any(marker in lower for marker in no_example_markers):
            policy["avoid_examples"] = True
            policy["instruction"] += (
                "Avoid examples. Give the exact needed code or action only.\n"
            )

        return policy

    def _apply_response_intelligence(
        self,
        user_text: str = "",
        assistant_text: str = "",
        decision=None,
    ) -> dict:
        decision = decision if isinstance(decision, dict) else {}
        assistant_text = self._safe_str(assistant_text).strip()

        user_text_lc = self._safe_str(user_text).lower().strip()

        # =============================
        # HARD COMMON-PROMPT OVERRIDE (FIXED)
        # =============================

        stuck_signals = [
            "fix this",
            "not working",
            "it's not working",
            "its not working",
            "broken",
            "error",
            "stuck",
            "idk",
            "i dont know",
            "i don't know",
            "what now",
            "help",
            "confused",
        ]

        if any(signal in user_text_lc for signal in stuck_signals):
            return {
                "assistant_text": (
                    "Do this:\n"
                    "1. Paste the error\n"
                    "2. Paste the file path\n\n"
                    "I’ll fix it."
                ),
                "intelligence": {
                    "strategy": "force_next_step",
                },
                "self_check": {
                    "should_revise": False,
                    "issues": [],
                },
                "hard_override_applied": True,
            }

        mission = decision.get("mission") if isinstance(decision.get("mission"), dict) else {}
        mission_mode = str(mission.get("mode") or "").lower().strip()

        hard_override_applied = False

        if not assistant_text:
            assistant_text = "No response generated."

        try:
            intelligence = self._fuse_response_intelligence(
                user_text=user_text,
                assistant_text=assistant_text,
                decision=decision,
            )
        except Exception as e:
            print("INTELLIGENCE_FUSE_ERROR:", e)
            intelligence = {}

        intelligence = intelligence if isinstance(intelligence, dict) else {}

        try:
            strategy = self._decide_response_strategy(
                user_text=user_text,
                decision=decision,
                intelligence=intelligence,
            )
        except Exception as e:
            print("STRATEGY_ERROR:", e)
            strategy = {}

        strategy = strategy if isinstance(strategy, dict) else {}

        intelligence["strategy"] = strategy.get("strategy")
        intelligence["next_move"] = strategy.get("next_move")
        intelligence["response_strategy"] = strategy

        try:
            self_check = self._self_check_response(
                user_text=user_text,
                assistant_text=assistant_text,
                intelligence=intelligence,
            )
        except Exception as e:
            print("SELF_CHECK_ERROR:", e)
            self_check = {"should_revise": False, "issues": []}

        self_check = self_check if isinstance(self_check, dict) else {
            "should_revise": False,
            "issues": [],
        }

        response_policy = self._build_response_policy(
            user_text=user_text,
            decision=decision,
        )

        try:
            assistant_text = self._clean_final_response_text(
                assistant_text,
                response_policy=response_policy,
                mission_mode=mission_mode,
                user_text=user_text,
            )
        except Exception as e:
            print("FINAL_CLEAN_ERROR:", e)

        return {
            "assistant_text": assistant_text,
            "intelligence": intelligence,
            "self_check": self_check,
            "hard_override_applied": hard_override_applied,
        }

    def _clean_final_response_text(
        self,
        text: str,
        response_policy=None,
        mission_mode: str = "",
        user_text: str = "",
    ) -> str:
        text = self._safe_str(text).strip()
        user_text_raw = self._safe_str(user_text).strip()
        user_text_lc = user_text_raw.lower()
        response_policy = response_policy if isinstance(response_policy, dict) else {}

        print("CLEAN_FINAL_HIT:", user_text_raw)

        if not text:
            return "Done."

        vague_fix_inputs = [
            "fix this",
            "it's not working",
            "its not working",
            "not working",
            "broken",
            "error",
        ]

        if any(user_text_lc == v or user_text_lc.startswith(v) for v in vague_fix_inputs):
            return (
                "Paste:\n"
                "- the error\n"
                "- the file path\n\n"
                "I’ll fix it."
            )

        if user_text_lc in ["help", "what do we do", "what now", "next"]:
            return (
                "Tell me what you're trying to do.\n\n"
                "I’ll give you the next step."
            )

        kill_phrases = [
            "i can help",
            "let me know",
            "if you want",
            "feel free",
            "hopefully",
            "in conclusion",
            "overall",
            "you might want",
            "one option is",
        ]

        lines = []
        for line in text.split("\n"):
            clean = line.strip()
            lc = clean.lower()

            if not clean:
                continue

            if any(p in lc for p in kill_phrases):
                continue

            lines.append(clean)

        text = "\n".join(lines).strip()

        if user_text_lc.startswith("latest"):
            useful = [line for line in text.split("\n") if line.strip()]
            return "\n".join(useful[:4]).strip() or text

        if any(line.strip().startswith(("1.", "2.", "3.", "4.", "5.")) for line in text.split("\n")):
            text = "\n".join(text.split("\n")[:5]).strip()

        if response_policy.get("answer_length") == "short":
            text = "\n".join(text.split("\n")[:6]).strip()

        if response_policy.get("user_frustrated"):
            text = text.replace("please", "").replace("kindly", "").strip()

        return text or "Done."

    def _decide_response_strategy(
        self,
        user_text: str = "",
        decision=None,
        intelligence=None,
    ) -> dict:

        decision = decision if isinstance(decision, dict) else {}
        intelligence = intelligence if isinstance(intelligence, dict) else {}

        text = self._safe_str(user_text).lower().strip()

        route = self._safe_str(decision.get("route")).lower()
        mode = self._safe_str(decision.get("mode")).lower()
        intent = self._safe_str(intelligence.get("intent") or decision.get("intent") or mode or route or "chat").lower()

        wants_full_file = any(
            phrase in text
            for phrase in [
                "smff",
                "full file",
                "full code",
                "send me full file",
                "whole file",
            ]
        )

        wants_exact_edit = any(
            phrase in text
            for phrase in [
                "replace",
                "anchor",
                "where",
                "what do i replace",
                "what line",
                "indent",
                "fix this block",
            ]
        )

        wants_continue = text in [
            "next",
            "continue",
            "go",
            "keep going",
            "next step",
        ]

        is_debugging = (
            intent == "debugging"
            or mode == "debugging"
            or any(
                phrase in text
                for phrase in [
                    "bug",
                    "error",
                    "traceback",
                    "exception",
                    "broken",
                    "not working",
                    "500",
                    "syntaxerror",
                    "indentationerror",
                    "taberror",
                ]
            )
        )

        is_learning = any(
            phrase in text
            for phrase in [
                "what is",
                "what does",
                "why",
                "how does",
                "how do",
                "explain",
            ]
        )

        if wants_full_file:
            strategy = "full_file"
            next_move = "Return the full file or full replacement code."

        elif wants_exact_edit:
            strategy = "exact_edit"
            next_move = "Give the exact anchor, replacement block, and placement."

        elif is_debugging:
            strategy = "debug_triage"
            next_move = "Lead with likely cause, then give the fastest verification command."

        elif wants_continue:
            strategy = "continue_mission"
            next_move = "Infer the current mission and give the next concrete step."

        elif is_learning:
            strategy = "teach_clear"
            next_move = "Explain clearly, then give the core takeaway."

        else:
            strategy = "direct_answer"
            next_move = "Answer directly with no filler."

        return {
            "strategy": strategy,
            "next_move": next_move,
            "intent": intent,
            "route": route,
            "mode": mode,
            "wants_full_file": wants_full_file,
            "wants_exact_edit": wants_exact_edit,
            "wants_continue": wants_continue,
            "is_debugging": is_debugging,
            "is_learning": is_learning,
        }

    def _shape_response_with_strategy(
        self,
        user_text: str = "",
        assistant_text: str = "",
        intelligence=None,
    ) -> str:

        intelligence = intelligence if isinstance(intelligence, dict) else {}

        text = self._safe_str(assistant_text).strip()
        user_lc = self._safe_str(user_text).lower().strip()

        strategy = self._safe_str(
            intelligence.get("strategy") or ""
        ).lower().strip()

        if not text:
            return text

        # === HARD COMMAND LOCKS ===
        if user_lc in ["smff", "snff", "ff"]:
            return (
                "SMFF mode active.\n\n"
                "Send the file name, function, or task.\n"
                "I will return full file or full replacement.\n"
                "No partial snippets."
            )

        if user_lc in ["next", "continue", "go", "keep going", "next step"]:
            if not text.lower().startswith("next"):
                return "Next move:\n\n" + text
            return text

        # === DEBUG LOCK ===
        if strategy in ["debug_triage", "debugging"]:
            if "error" not in user_lc:
                return (
                    "Likely cause:\n\n"
                    "No actual bug details were provided yet.\n\n"
                    "Next move:\n\n"
                    "Paste the exact error/traceback and the file path."
                )

        # =============================
        # EXECUTION DOMINANCE
        # =============================
        execution_triggers = [
            "build", "create", "make", "fix", "implement",
            "add", "write", "generate", "set up"
        ]

        is_execution_intent = any(k in user_lc for k in execution_triggers)

        if is_execution_intent:
            # If response is explanation-heavy, force actionable output
            if not any(x in text.lower() for x in ["def ", "class ", "import ", "```", "powershell", "cd "]):
                return (
                    "Next move:\n\n"
                    "Start implementation immediately.\n"
                    "Provide code, command, or exact file change.\n"
                    "Do not stop at explanation."
                )

            if not text.lower().startswith("likely cause"):
                return "Likely cause:\n\n" + text

            return text

        # === PLAN LOCK ===
        if strategy in ["planner", "planning", "plan"]:
            if not text.lower().startswith("plan"):
                return "Plan:\n\n" + text
            return text

        return text.strip()

    def _decide_response_strategy(
        self,
        user_text: str = "",
        decision=None,
        intelligence=None,
    ) -> dict:

        decision = decision if isinstance(decision, dict) else {}
        intelligence = intelligence if isinstance(intelligence, dict) else {}

        text = self._safe_str(user_text).lower().strip()

        route = self._safe_str(decision.get("route")).lower()
        mode = self._safe_str(decision.get("mode")).lower()
        intent = self._safe_str(intelligence.get("intent") or decision.get("intent") or mode or route or "chat").lower()

        wants_full_file = any(
            phrase in text
            for phrase in [
                "smff",
                "full file",
                "full code",
                "send me full file",
                "whole file",
            ]
        )

        wants_exact_edit = any(
            phrase in text
            for phrase in [
                "replace",
                "anchor",
                "where",
                "what do i replace",
                "what line",
                "indent",
                "fix this block",
            ]
        )

        wants_continue = text in [
            "next",
            "continue",
            "go",
            "keep going",
            "next step",
        ]

        is_debugging = (
            intent == "debugging"
            or mode == "debugging"
            or any(
                phrase in text
                for phrase in [
                    "bug",
                    "error",
                    "traceback",
                    "exception",
                    "broken",
                    "not working",
                    "500",
                    "syntaxerror",
                    "indentationerror",
                    "taberror",
                ]
            )
        )

        is_learning = any(
            phrase in text
            for phrase in [
                "what is",
                "what does",
                "why",
                "how does",
                "how do",
                "explain",
            ]
        )

        if wants_full_file:
            strategy = "full_file"
            next_move = "Return the full file or full replacement code."

        elif wants_exact_edit:
            strategy = "exact_edit"
            next_move = "Give the exact anchor, replacement block, and placement."

        elif is_debugging:
            strategy = "debug_triage"
            next_move = "Lead with likely cause, then give the fastest verification command."

        elif wants_continue:
            strategy = "continue_mission"
            next_move = "Infer the current mission and give the next concrete step."

        elif is_learning:
            strategy = "teach_clear"
            next_move = "Explain clearly, then give the core takeaway."

        else:
            strategy = "direct_answer"
            next_move = "Answer directly with no filler."

        return {
            "strategy": strategy,
            "next_move": next_move,
            "intent": intent,
            "route": route,
            "mode": mode,
            "wants_full_file": wants_full_file,
            "wants_exact_edit": wants_exact_edit,
            "wants_continue": wants_continue,
            "is_debugging": is_debugging,
            "is_learning": is_learning,
        }

    def _build_response_policy_prompt(
        self,
        user_text: str = "",
        decision=None,
        intelligence=None,
    ) -> str:

        decision = decision if isinstance(decision, dict) else {}
        intelligence = intelligence if isinstance(intelligence, dict) else {}

        strategy = self._safe_str(intelligence.get("strategy") or "direct_answer")
        next_move = self._safe_str(intelligence.get("next_move") or "")
        user_lc = self._safe_str(user_text).lower().strip()

        return (
            "NOVA RESPONSE POLICY:\n"
            "- Answer like an execution-focused AI, not a generic chatbot.\n"
            "- Be direct, useful, and specific.\n"
            "- Do not add filler, soft disclaimers, or fake helpfulness.\n"
            "- Do not ask clarification questions unless the task is truly blocked.\n"
            "- Infer the likely next move from the current mission.\n"
            "- When the user says next, continue the current task instead of asking what they want.\n"
            "- When the user asks for code, provide complete usable code or exact replacement blocks.\n"
            "- For code edits, include the file path, anchor text, placement, and compile/test command.\n"
            "- For Python/Flask/Nova work, prefer PowerShell commands.\n"
            "- For debugging, lead with likely cause, then give the fastest verification/fix.\n"
            "- For explanations, explain clearly and finish with the core takeaway.\n"
            "- Never say 'if you want'.\n"
            "- Never say 'provide more details' unless there is no actionable path.\n"
            "- Never give vague snippets when the user is asking for implementation.\n\n"
            f"Detected strategy: {strategy}\n"
            f"Recommended next move: {next_move}\n"
            f"Current user message: {user_lc}\n"
        )

    def _web_search(self, query: str) -> dict:
        query = self._safe_str(query).strip()
        if not query:
            return {"results": []}

        import requests
        import re
        from urllib.parse import quote_plus, urlparse
        from xml.etree import ElementTree as ET

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        # -------------------------
        # 1. DuckDuckGo HTML
        # -------------------------
        try:
            url = "https://duckduckgo.com/html/?q=" + quote_plus(query)
            res = requests.get(url, headers=headers, timeout=10)

            html = res.text or ""
            results = []

            for match in re.finditer(
                r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                html,
                re.S
            ):
                link = match.group(1).replace("&amp;", "&")
                title = re.sub(r"<.*?>", "", match.group(2)).strip()

                snippet_match = re.search(
                    r'class="result__snippet"[^>]*>(.*?)</',
                    html[match.end():match.end() + 500],
                    re.S
                )

                snippet = ""
                if snippet_match:
                    snippet = re.sub(r"<.*?>", "", snippet_match.group(1)).strip()

                title = re.sub(r"\s+", " ", title).strip()
                snippet = re.sub(r"\s+", " ", snippet).strip()

                if not title or title.lower() in ["here", "click", "link"]:
                    continue

                if "duckduckgo.com" in link:
                    continue

                results.append({
                    "title": title,
                    "snippet": snippet,
                    "content": snippet,
                    "url": link,
                })

                if len(results) >= 5:
                    break

            if results:
                print("SEARCH: DuckDuckGo HTML success")
                return {"results": results}

        except Exception as e:
            print("DDG HTML FAILED:", e)

        # -------------------------
        # 2. DuckDuckGo Lite
        # -------------------------
        try:
            url = "https://lite.duckduckgo.com/lite/?q=" + quote_plus(query)
            res = requests.get(url, headers=headers, timeout=10)

            html = res.text or ""
            results = []

            for match in re.finditer(
                r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                html,
                re.S
            ):
                link = match.group(1)
                title = re.sub(r"<.*?>", "", match.group(2))
                title = re.sub(r"\s+", " ", title).strip()

                if not title or title.lower() in ["here", "click", "link"]:
                    continue

                if "http" not in link:
                    continue

                if "duckduckgo.com" in link:
                    continue

                results.append({
                    "title": title,
                    "snippet": "",
                    "content": "",
                    "url": link,
                })

                if len(results) >= 5:
                    break

            if results:
                print("SEARCH: DuckDuckGo Lite success")
                return {"results": results}

        except Exception as e:
            print("DDG LITE FAILED:", e)

        # -------------------------
        # 3. Google News RSS
        # -------------------------
        try:
            url = "https://news.google.com/rss/search?q=" + quote_plus(query)
            res = requests.get(url, headers=headers, timeout=10)

            root = ET.fromstring(res.content)
            results = []

            for item in root.findall(".//item"):
                title = item.findtext("title") or ""
                link = item.findtext("link") or ""
                description = item.findtext("description") or ""

                description = re.sub(r"<.*?>", "", description)
                description = re.sub(r"\s+", " ", description).strip()

                real_source = ""
                if " - " in title:
                    parts = title.split(" - ")
                    if len(parts) >= 2:
                        real_source = parts[-1].strip()

                domain = urlparse(link).netloc.replace("www.", "")
                source_label = real_source or domain

                results.append({
                    "title": title.split(" - ")[0].strip(),
                    "snippet": description,
                    "content": description,
                    "url": link,
                    "source": source_label,
                })

                if len(results) >= 5:
                    break

            if results:
                print("SEARCH: Google News RSS success")
                return {"results": results}

        except Exception as e:
            print("GOOGLE RSS FAILED:", e)

        print("SEARCH: ALL FALLBACKS FAILED")
        return {"results": []}

    def _execute_web_fetch(
        self,
        user_text: str,
        session_id: str,
        attachments=None,
        decision=None,
    ) -> dict:
        decision = decision if isinstance(decision, dict) else {}
        attachments = attachments or []

        mission = decision.get("mission") if isinstance(decision, dict) else {}
        mission = mission if isinstance(mission, dict) else {}
        mission_mode = str(mission.get("mode") or "").lower()

        user_msg = self._build_user_message(
            user_text,
            attachments=attachments,
        )

        query = self._safe_str(
            decision.get("query")
            or decision.get("search_query")
            or decision.get("url")
            or user_text
        ).strip()

        freshness_words = [
            "latest",
            "today",
            "right now",
            "current",
            "breaking",
            "recent",
            "news",
            "update",
            "updates",
        ]

        wants_fresh = any(word in query.lower() for word in freshness_words)

        if wants_fresh and "today" not in query.lower():
            query = query + " today"

        web_result = {}

        try:
            if hasattr(self, "_web_search"):
                web_result = self._web_search(query)

            if not web_result or not web_result.get("results"):
                print("WEB_FETCH_FALLBACK: using duckduckgo")

                import requests
                from bs4 import BeautifulSoup

                url = f"https://duckduckgo.com/html/?q={query}"
                res = requests.get(url, timeout=10)
                soup = BeautifulSoup(res.text, "html.parser")

                results = []

                for a in soup.select("a.result__a")[:5]:
                    title = a.get_text(strip=True)
                    link = a.get("href")

                    results.append({
                        "title": title,
                        "url": link,
                        "snippet": "",
                        "source": "duckduckgo",
                    })

                web_result = {"results": results}

        except Exception as exc:
            print("WEB_FETCH_TOTAL_FAIL:", exc)
            web_result = {"results": []}

        except Exception as exc:
            print("WEB_FETCH_PRIMARY_FAILED:", exc)
            web_result = {}

        print("WEB_FETCH_QUERY:", query)
        print("WEB_FETCH_RESULT_TYPE:", type(web_result))
        print("WEB_FETCH_RESULT:", web_result)

        if not isinstance(web_result, dict):
            web_result = {"body": str(web_result or ""), "results": []}

        results = web_result.get("results")
        if not isinstance(results, list):
            results = []

        body = self._safe_str(
            web_result.get("body")
            or web_result.get("text")
            or web_result.get("content")
            or ""
        ).strip()

        source_urls = []
        source_lines = []

        stale_words = [
            "march 28",
            "march 27",
            "march 26",
            "march 25",
            "2025",
            "last season",
            "schedule update",
            "added on march",
        ]

        fresh_words = [
            "today",
            "latest",
            "injury report",
            "updated",
            "update",
            "announced",
            "breaking",
            "starter",
            "starters",
            "tonight",
            "game vs",
            "vs.",
            "april 2026",
            "2026",
        ]

        filtered_results = []

        for item in results[:12]:
            if not isinstance(item, dict):
                continue

            title = self._safe_str(item.get("title") or item.get("name") or "").strip()
            url = self._safe_str(item.get("url") or item.get("href") or item.get("link") or "").strip()
            snippet = self._safe_str(item.get("snippet") or item.get("description") or item.get("body") or "").strip()
            source = self._safe_str(item.get("source") or item.get("domain") or "").strip()

            combined = f"{title} {snippet} {source} {url}".lower()

            is_stale = any(word in combined for word in stale_words)
            looks_fresh = any(word in combined for word in fresh_words)

            if wants_fresh:
                if is_stale and not looks_fresh:
                    continue

            filtered_results.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": source,
            })

        # ðŸ”¥ fallback if filter removed everything
        if not filtered_results:
            filtered_results = results[:5]

        for item in filtered_results[:5]:
            title = item["title"]
            url = self._resolve_google_news_url(item["url"])
            snippet = item["snippet"]
            source = item["source"]

            if not title and not url:
                continue

            if url:
                source_urls.append(url)

            label = title
            if source:
                label = f"{source} â€” {title}" if title else source

            source_lines.append(label)

            if snippet and snippet not in body:
                body += "\n\n" + snippet

        if not body and source_lines:
            body = "\n".join(source_lines)

        if not body:
            assistant_text = (
                "No verified fresh web results were retrieved.\n\n"
                "Try a more specific query with a team, person, date, or source."
            )
        else:
            prompt = (
                "Give a clear, confident, concise summary of the latest news using ONLY the fetched web text below.\n"
                "Prioritize the most recent and relevant items.\n"
                "Do not hedge with phrases like 'freshness is uncertain' unless absolutely necessary.\n"
                "Do not invent facts. Keep it direct and readable.\n\n"
                f"User asked:\n{user_text}\n\n"
                f"Web results:\n{body}\n"
            )

            assistant_text = ""

            try:
                model_messages = [
                    {
                        "role": "system",
                        "content": (
                            "You summarize fresh web results. Be direct. "
                            "Do not make up dates, scores, injuries, trades, or news."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ]

                response = self.client.chat.completions.create(
                    model=getattr(self, "model", "gpt-4o-mini"),
                    messages=model_messages,
                    temperature=0.2,
                )

                assistant_text = (
                    response.choices[0].message.content
                    if response and response.choices
                    else ""
                ).strip()

            except Exception as exc:
                print("WEB_FETCH_SUMMARY_FAILED:", exc)
                assistant_text = body[:1800].strip()

            if source_lines:
                assistant_text += "\n\nâ€” Top sources â€”\n"

                query_lc = str(query or user_text or "").lower()

                wants_injury = any(k in query_lc for k in [
                    "injury", "injuries", "status", "available",
                    "availability", "playing", "playing today",
                    "is he playing", "out", "questionable"
                ])

                wants_betting = any(k in query_lc for k in [
                    "odds", "betting", "spread", "prediction",
                    "parlay", "prop bet", "props", "best bets", "picks"
                ])

                ranked_lines = []

                for line in source_lines:
                    text = str(line or "").lower()

                    # âŒ kill garbage
                    if any(bad in text for bad in [
                        "instagram.com",
                        "facebook.com",
                        "tiktok.com",
                    ]):
                        continue

                    score = 10

                    # normalize HARD
                    t = text.strip()
                    tl = t.lower()

                    # --- INJURY SIGNAL BOOST ---
                    injury_keywords = [
                        "injury", "injuries", "status", "report",
                        "update", "out", "questionable",
                        "available", "availability",
                        "playing", "playing today", "is he playing",
                        "is he out", "starting", "lineup", "starting lineup"
                    ]

                    has_injury_signal = any(k in tl for k in injury_keywords)

                    if has_injury_signal and wants_injury:
                        score += 120

                    # --- MIXED / LOW VALUE PENALTY ---
                    mixed_keywords = [
                        "odds", "betting", "spread", "prediction",
                        "parlay", "stream", "live stream",
                        "how to watch", "tickets"
                    ]
                    has_mixed_signal = any(k in tl for k in mixed_keywords)

                    if has_mixed_signal and not wants_betting:
                        score -= 80

                    if has_mixed_signal and wants_injury:
                        score -= 120

                    pure_betting_sites = [
                        "sportsbook wire", "covers.com", "covers â€”",
                        "odds shark", "action network", "draftkings",
                        "fanduel", "betmgm"
                    ]

                    if any(site in tl for site in pure_betting_sites) and wants_injury:
                        score -= 70

                    real_news_sources = [
                        "detroit free press", "freep.com",
                        "usa today", "yahoo sports",
                        "sports illustrated", "si.com",
                        "espn", "nba.com"
                    ]

                    if any(site in tl for site in real_news_sources):
                        score += 35

                    # --- CLEAN INJURY BONUS ---
                    if has_injury_signal and wants_injury and not has_mixed_signal:
                        score += 60

                    # ðŸ”¥ SOURCE BOOST (DO NOT RESET SCORE)
                    if "nba â€”" in t or t.startswith("nba") or " nba " in t:
                        score += 120

                    elif "usa today" in tl:
                        score += 100

                    elif "sports illustrated" in tl or "si.com" in tl:
                        score += 95

                    elif "espn" in tl:
                        score += 85

                    elif "heavy.com" in tl or "heavy â€”" in t:
                        score += 60

                    elif "yahoo" in tl:
                        score += 50

                    # --- DIRECT AVAILABILITY / INJURY ARTICLE OVERRIDE ---
                    if wants_injury and any(k in tl for k in [
                        "playing today",
                        "is cade cunningham playing",
                        "injury",
                        "injuries",
                        "status",
                        "availability"
                    ]):
                        score += 700

                    # --- HARD BETTING FARM DROP WHEN INJURY IS REQUESTED ---
                    if wants_injury and any(k in tl for k in [
                        "sportsbook wire",
                        "covers.com",
                        "best bets",
                        "picks & best bets",
                        "prop bets"
                    ]):
                        score -= 200

                    # --- FINAL HARD OVERRIDE (WINNER TAKE TOP) ---
                    if wants_injury and "free press" in tl and any(k in tl for k in [
                        "playing", "injury", "injuries", "status"
                    ]):
                        score = 9999

                    if (
                        wants_injury
                        and "detroit free press" in tl
                        and any(k in tl for k in ["playing", "injury", "injuries", "status"])
                    ):
                        score = 9999

                    ranked_lines.append((score, line))

                ranked_lines.sort(key=lambda x: x[0], reverse=True)

                # --- LOCK OUTPUT ORDER: INJURY WINNER FIRST ---
                if wants_injury:
                    injury_winners = []
                    others = []

                    for item in ranked_lines:
                        _, line = item
                        line_lc = str(line or "").lower()

                        if "free press" in line_lc and any(k in line_lc for k in [
                            "playing",
                            "playing today",
                            "injury",
                            "injuries",
                            "status",
                            "availability",
                        ]):
                            injury_winners.append(item)
                        else:
                            others.append(item)

                    ranked_lines = injury_winners + others

                ranked_lines = ranked_lines[:5]

                assistant_text += "\n"

                for index, (_, line) in enumerate(ranked_lines, start=1):
                    assistant_text += f"{index}. {line}\n"

        assistant_msg = self._build_assistant_message(
            assistant_text,
            meta={
                "route": "web",
                "query": query,
                "fresh": wants_fresh,
                "source_urls": source_urls[:5],
            },
        )

        return self._finalize_response(
            session_id,
            user_msg,
            assistant_msg,
            decision,
        )

    def _resolve_google_news_url(self, url: str) -> str:
        try:
            import requests
            res = requests.get(url, timeout=5, allow_redirects=True)
            return res.url
        except Exception:
            return url

    def _is_image_generation_request(self, user_text: str) -> bool:
        text = str(user_text or "").strip().lower()

        if not text:
            return False

        if text.startswith("/image") or "/image" in text:
            return True

        keywords = ["generate", "create", "make", "draw", "render", "design"]
        image_words = ["image", "picture", "photo", "art", "scene", "visual"]

        if any(k in text for k in keywords) and any(i in text for i in image_words):
            return True

        if any(k in text for k in keywords):
            return True

        return False

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

    def _detect_mission_state(self, user_text: str = "", decision=None) -> dict:
        decision = decision if isinstance(decision, dict) else {}
        text = self._safe_str(user_text).lower().strip()

        mission = {
            "mode": "general",
            "current_task": "",
            "next_move": "",
            "needs_full_file": False,
        }

        if any(x in text for x in ["fix my bug", "fix bug", "error", "traceback", "syntaxerror", "indentationerror"]):
            mission.update({
                "mode": "debugging",
                "current_task": "Fix current Nova bug",
                "next_move": "Run compile, inspect exact error, apply smallest safe fix.",
                "needs_full_file": True,
            })
            return mission

        if text in ["smff", "snff"] or "smff" in text:
            mission.update({
                "mode": "full_file",
                "current_task": "Provide full-file or full-block replacement",
                "next_move": "Use exact file path, anchor, replacement, and test command.",
                "needs_full_file": True,
            })
            return mission

        if text in ["next", "continue", "go", "keep going", "next step"]:
            mission.update({
                "mode": "continue",
                "current_task": "Continue current Nova build phase",
                "next_move": "Choose the next concrete implementation step.",
                "needs_full_file": False,
            })
            return mission

        if "latest" in text or "news" in text or str(decision.get("route") or "").lower() == "web":
            mission.update({
                "mode": "web_fetch",
                "current_task": "Fetch and summarize current information",
                "next_move": "Return concise summary with sources when available.",
                "needs_full_file": False,
            })
            return mission

        return mission

    def handle(self, user_text: str, session_id: str = "", attachments=None):
        print("HANDLE IS BEING CALLED")
        attachments = attachments or []

        session_id = self._ensure_session_id(session_id)
        user_text = self._safe_str(user_text)
        user_lc = user_text.lower().strip()

        print("CHAT_SERVICE_HANDLE_HIT:", user_text)

        # === LIGHT CONTEXT MEMORY ===
        last_intent = ""
        try:
            session = self._get_session_payload(session_id)
            state = session.get("working_state") if isinstance(session, dict) else {}
            state = state if isinstance(state, dict) else {}
            last_intent = str(state.get("mission_mode") or "").lower().strip()
        except Exception:
            last_intent = ""

        decision = {}
        try:
            decision = self._decide(user_text=user_text)
        except Exception as e:
            print("DECISION_ERROR:", e)
            decision = {}

        decision = decision if isinstance(decision, dict) else {}

        # === HARD INTENT RESET ===
        if user_lc in ["hi", "hello", "yo", "hey"]:
            mission = {
                "mode": "general",
                "current_task": "",
                "next_move": "",
                "needs_full_file": False,
            }
            decision["strategy"] = "direct_answer"

        elif user_lc in ["make a plan", "plan", "make plan"]:
            mission = {
                "mode": "planning",
                "current_task": "Create a general plan",
                "next_move": "Return a clear structured plan.",
                "needs_full_file": False,
            }
            decision["strategy"] = "planning"

        elif user_lc in ["next", "continue", "go", "keep going", "next step"]:
            mission = {
                "mode": last_intent or "continue",
                "current_task": "Continue current Nova build phase",
                "next_move": "Choose the next concrete implementation step.",
                "needs_full_file": False,
            }
            decision["strategy"] = "continue"

        else:
            mission = self._detect_mission_state(
                user_text=user_text,
                decision=decision,
            )
            decision["strategy"] = mission.get("mode")

        decision["mission"] = mission
        decision["strategy"] = str(decision.get("strategy") or "").lower().strip()

        print("MISSION_STATE:", mission)

        try:
            if mission.get("mode") not in ["general"]:
                session = self._get_session_payload(session_id)
                state = session.get("working_state") if isinstance(session, dict) else {}
                state = state if isinstance(state, dict) else {}

                state["active_task"] = mission.get("current_task") or user_text
                state["next_step"] = mission.get("next_move") or ""
                state["mission_mode"] = mission.get("mode") or "general"

                self.session_service.update_working_state(session_id, state)
                print("MISSION_MEMORY_SAVED:", state)
        except Exception as e:
            print("MISSION_MEMORY_SAVE_ERROR:", e)

        route = str(decision.get("route") or "").lower()

        try:
            if route == "web":
                return self._execute_web_fetch(
                    user_text=user_text,
                    session_id=session_id,
                    attachments=attachments,
                    decision=decision,
                )

            return self._execute_general_chat(
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
                decision=decision,
            )

        except Exception as e:
            print("EXECUTION_ERROR:", e)
            return {
                "ok": False,
                "error": str(e),
                "session": session_id,
                "debug": {
                    "route": route,
                },
            }

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
        t = self._safe_str(text).lower()

        # preference
        if any(x in t for x in ["i prefer", "i like", "i usually", "i always", "i want"]):
            return "preference"

        # identity / profile
        if any(x in t for x in ["my name is", "i am", "i'm", "i was", "i live"]):
            return "profile"

        # project
        if any(x in t for x in ["i'm building", "my project", "i'm working on", "app", "nova"]):
            return "project"

        # goal
        if any(x in t for x in ["i want to", "my goal", "i plan to"]):
            return "goal"

        # default
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


    def _clean_working_state_value(self, value, limit=160):
        text = self._safe_str(value).strip()
        if not text:
            return ""

        text = text.replace("\r", " ").replace("\n", " ")
        text = re.sub(r"\s+", " ", text).strip()

        bad_starts = (
            "yes",
            "agreed",
            "recommended next step",
            "current project truth says",
            "what this means",
            "in short",
        )
        lower = text.lower()
        if any(lower.startswith(x) for x in bad_starts):
            return ""

        return text[:limit]

    def _should_inject_working_context(self, decision, user_text, assistant_msg):
        decision = decision or {}
        user_text = self._safe_str(user_text).lower()
        user_lc = user_text.lower().strip()
        assistant_text = self._safe_str((assistant_msg or {}).get("text")).lower()

        route = self._safe_str(decision.get("route")).lower()
        mode = self._safe_str(decision.get("mode")).lower()

        continuity_triggers = [
            "what are we doing now",
            "where are we now",
            "what's next",
            "next step",
            "next move",
            "current task",
            "active task",
            "current bug",
            "current file",
            "checkpoint",
            "pick up where we left off",
            "continue",
            "resume",
            "status",
            "progress",
        ]

        assistant_triggers = [
            "next step",
            "next move",
            "current bug",
            "current file",
            "active task",
            "checkpoint",
            "working on",
            "resume",
            "continue",
        ]

        if route in {"memory", "planning"}:
            return True

        if mode in {"planning", "analysis"}:
            return True

        if any(trigger in user_text for trigger in continuity_triggers):
            return True

        if any(trigger in assistant_text for trigger in assistant_triggers):
            return True

        return False

    def _build_working_context_block(self, session_id: str):
        state = self._get_working_state(session_id)

        rows = [
            ("Active task", state.get("active_task", "")),
            ("Current file", state.get("current_file", "")),
            ("Current bug", state.get("current_bug", "")),
            ("Last success", state.get("last_success", "")),
            ("Next move", state.get("next_move", "")),
            ("Checkpoint", state.get("checkpoint", "")),
        ]

        lines = []
        for label, value in rows:
            value = self._clean_working_state_value(value)
            if value:
                lines.append(f"{label}: {value}")

        if not lines:
            return ""

        return "Working context:\n" + "\n".join(lines)

    def _build_working_context_payload(self, session_id: str) -> dict:
        state = self._get_working_state(session_id)

        if not isinstance(state, dict):
            state = {}

        cleaned = {
            "active_task": self._clean_working_state_value(state.get("active_task", "")),
            "current_file": self._clean_working_state_value(state.get("current_file", "")),
            "current_bug": self._clean_working_state_value(state.get("current_bug", "")),
            "last_success": self._clean_working_state_value(state.get("last_success", "")),
            "next_move": self._clean_working_state_value(state.get("next_move", "")),
            "checkpoint": self._clean_working_state_value(state.get("checkpoint", "")),
            "updated_at": self._safe_str(state.get("updated_at", "")),
        }

        text_lines = []
        if cleaned["active_task"]:
            text_lines.append(f"- Active task: {cleaned['active_task']}")
        if cleaned["current_file"]:
            text_lines.append(f"- Current file: {cleaned['current_file']}")
        if cleaned["current_bug"]:
            text_lines.append(f"- Current bug: {cleaned['current_bug']}")
        if cleaned["last_success"]:
            text_lines.append(f"- Last success: {cleaned['last_success']}")
        if cleaned["next_move"]:
            text_lines.append(f"- Next move: {cleaned['next_move']}")
        if cleaned["checkpoint"]:
            text_lines.append(f"- Checkpoint: {cleaned['checkpoint']}")

        text = ""
        if text_lines:
            text = "Working context:\n" + "\n".join(text_lines)

        return {
            "show": bool(text_lines),
            "text": text,
            "state": cleaned,
            "collapsed": False,
        }

    def _score_memory_for_text(self, memory_item, user_text: str) -> float:
        user_text = self._safe_str(user_text).strip().lower()
        if not user_text:
            return 0.0

        if isinstance(memory_item, dict):
            text = self._safe_str(memory_item.get("text"))
            kind = self._safe_str(memory_item.get("kind"))
        else:
            text = self._safe_str(memory_item)
            kind = ""

        haystack = f"{kind} {text}".strip().lower()
        if not haystack:
            return 0.0

        score = 0.0

        project_query_triggers = [
            "what am i working on",
            "what project",
            "my project",
            "current project",
            "what are we building",
            "what am i building",
        ]

        if any(trigger in user_text for trigger in project_query_triggers):
            if kind.lower() == "project":
                score += 100.0
            if "nova" in haystack:
                score += 100.0

        user_words = [w for w in re.findall(r"[a-zA-Z0-9_:\\.-]+", user_text) if len(w) > 2]
        if not user_words:
            return 0.0

        for word in user_words:
            if word in haystack:
                score += 1.0

        if user_text in haystack:
            score += 4.0

        if kind and kind.lower() in user_text:
            score += 2.0

        return score


    def _select_relevant_memory(self, user_text: str, limit: int = 3):
        all_memory = self._safe_list(self._load_memory())
        if not all_memory:
            return []

        ranked = []
        for item in all_memory:
            score = self._score_memory_for_text(item, user_text)
            if score > 0:
                ranked.append((score, item))

        ranked.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in ranked[:limit]]


    def _format_memory_context(self, memory_items) -> str:
        memory_items = memory_items or []
        lines = []

        for item in memory_items:
            if isinstance(item, dict):
                kind = self._safe_str(item.get("kind")).strip()
                text = self._safe_str(item.get("text")).strip()
            else:
                kind = ""
                text = self._safe_str(item).strip()

            if not text:
                continue

            if kind:
                lines.append(f"- [{kind}] {text}")
            else:
                lines.append(f"- {text}")

        return "\n".join(lines).strip()

    def _build_memory_context_for_chat(self, user_text: str, decision=None) -> str:
        decision = decision or {}
        use_memory = bool(decision.get("use_memory", True))
        memory_limit = int(decision.get("memory_limit", 3) or 3)

        if not use_memory:
            return ""

        # Step 1: try relevant memory
        relevant_items = self._select_relevant_memory(user_text, limit=memory_limit)

        # Step 2: fallback Ã¢â€ â€™ recent memory
        if not relevant_items:
            try:
                if hasattr(self, "memory") and self.memory:
                    if hasattr(self.memory, "all"):
                        all_items = self.memory.all() or []
                        relevant_items = all_items[:memory_limit]
            except Exception:
                relevant_items = []

        if not relevant_items:
            return ""

        return self._format_memory_context(relevant_items)

    def _build_memory_recall_text(self, session_id: str = "", user_text: str = "", limit: int = 5) -> str:
        items = []

        try:
            if hasattr(self, "memory") and self.memory and hasattr(self.memory, "all"):
                items = self.memory.all() or []
        except Exception:
            items = []

        if not items:
            return "I do not have any saved memory yet."

        ranked = []
        for item in items:
            score = self._score_memory_for_text(item, user_text)
            ranked.append((score, item))

        ranked.sort(key=lambda x: x[0], reverse=True)
        best = [item for score, item in ranked if score > 0][:limit]

        chosen = best if best else items[:limit]

        lines = []
        for item in chosen:
            if not isinstance(item, dict):
                text = self._safe_str(item).strip()
                if not text:
                    continue

                bad_patterns = [
                    "wouldn't you want to",
                    "get laid",
                    "say hi",
                    "hello",
                    "hi",
                    "thanks",
                    "thank you",
                    "lol",
                    "lmao",
                    "bro",
                    "nigga",
                ]
                if any(p in text.lower() for p in bad_patterns):
                    continue

                lines.append(f"- {text}")
                continue

            text = self._safe_str(item.get("text")).strip()
            kind = self._safe_str(item.get("kind")).strip()
            item_session_id = self._safe_str(item.get("session_id")).strip()

            if not text:
                continue

            bad_patterns = [
                "wouldn't you want to",
                "get laid",
                "say hi",
                "hello",
                "hi",
                "thanks",
                "thank you",
                "lol",
                "lmao",
                "bro",
                "nigga",
            ]

            if any(p in text.lower() for p in bad_patterns):
                continue

            prefix = "- "
            if kind:
                prefix = f"- [{kind}] "

            if session_id and item_session_id and item_session_id == session_id:
                prefix = prefix.rstrip() + " [this session] "

            lines.append(f"{prefix}{text}")

        if not lines:
            return "I do not have any saved memory yet."

        return "HereÃ¢â‚¬â„¢s what I remember:\n" + "\n".join(lines)

    def answer_from_web_results(self, query: str, results: list[dict] | None = None) -> str:
        query = str(query or "").strip()
        items = results if isinstance(results, list) else []

        cleaned: list[dict] = []
        source_urls: list[str] = []

        for item in items[:5]:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title") or "").strip()
            snippet = str(item.get("snippet") or "").strip()
            url = str(item.get("url") or "").strip()
            domain = str(item.get("domain") or "").strip()

            if not (title or snippet or url):
                continue

            if url:
                source_urls.append(url)

            cleaned.append(
                {
                    "title": title,
                    "snippet": snippet,
                    "url": url,
                    "domain": domain,
                }
            )

        if not cleaned:
            return f'I couldnâ€™t find strong live results for "{query}".'

        context_blocks: list[str] = []
        for idx, item in enumerate(cleaned, start=1):
            parts: list[str] = []
            if item["title"]:
                parts.append(f"Title: {item['title']}")
            if item["snippet"]:
                parts.append(f"Snippet: {item['snippet']}")
            if item["domain"]:
                parts.append(f"Source: {item['domain']}")
            if item["url"]:
                parts.append(f"URL: {item['url']}")
            context_blocks.append(f"[Result {idx}]\n" + "\n".join(parts))

        web_context = "\n\n".join(context_blocks)

        system_prompt = (
            "You are answering a user's web question using retrieved live results. "
            "Write a direct, useful answer in plain language. "
            "Do not say 'based on the search results' or 'I found'. "
            "If the results are weak, be honest but still give the best concise answer possible. "
            "Do not invent facts beyond the provided results. "
            "Keep it short and natural. "
            "When you include a Top sources list, include each source URL on the line directly after that source."
        )

        user_prompt = (
            f"User question:\n{query}\n\n"
            f"Live web results:\n{web_context}\n\n"
            "Write the answer now."
        )

        try:
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            text = ""
            if hasattr(response, "output_text") and response.output_text:
                text = str(response.output_text).strip()
            else:
                text = str(response).strip()

            if text:
                sources_block = ""

                if cleaned:
                    lines = []
                    lines.append("\nâ€” Top sources â€”")

                    ranked_sources = []




                    for item in cleaned:
                        if not isinstance(item, dict):
                            continue

                        url = str(item.get("url") or "")
                        title = str(item.get("title") or "")
                        domain = str(item.get("domain") or "")

                        score = self._source_quality_score(url, title + " " + domain)

                        if score <= -999:
                            continue

                        item["_quality_score"] = score
                        ranked_sources.append(item)

                    ranked_sources.sort(
                        key=lambda x: x.get("_quality_score", 0),
                        reverse=True,
                    )

                    cleaned = ranked_sources[:5]

                    for idx, item in enumerate(cleaned, start=1):
                        title = str(item.get("title") or "").strip()
                        domain = str(item.get("domain") or "").strip()
                        url = str(item.get("url") or "").strip()

                        lines.append(f"{idx}. {domain} â€” {title}")

                        if url:
                            lines.append(url)
                            source_urls.append(url)

                    sources_block = "\n" + "\n".join(lines)

                return {
                    "text": text + sources_block,
                    "source_urls": source_urls,
                }

        except Exception:
            pass

        top = cleaned[0]
        fallback_parts = []
        if top.get("title"):
            fallback_parts.append(str(top["title"]))
        if top.get("snippet"):
            fallback_parts.append(str(top["snippet"]))
        if top.get("url"):
            fallback_parts.append(str(top["url"]))

        return "\n".join(fallback_parts).strip() or f'Hereâ€™s what I found for "{query}".'

    # =========================
    # EXECUTION GUARD HELPERS (STEP TRUTH ENFORCEMENT)
    # =========================

    def _text_has_placeholder_debug_content(self, text: str) -> bool:
        text = self._safe_str(text).strip().lower()
        if not text:
            return True

        placeholder_markers = [
            "paste exact error here",
            "step 1",
            "step 2",
            "step 3",
            "how to reproduce:",
        ]
        return any(marker in text for marker in placeholder_markers)

    def _has_real_debug_context(self, user_text: str, execution: dict, attachments=None) -> bool:
        attachments = attachments or []
        text = self._safe_str(user_text)
        lowered = text.lower()

        if self._text_has_placeholder_debug_content(text):
            return False

        if attachments:
            return True

        signals = 0

        if "traceback" in lowered or "error" in lowered:
            signals += 1

        if "expected:" in lowered and "actual:" in lowered:
            signals += 1

        if "reproduce" in lowered:
            signals += 1

        if "def " in text or "class " in text:
            signals += 1

        if len(text.strip()) >= 120:
            signals += 1

        return signals >= 2

    def _step_requires_real_change(self, step_title: str) -> bool:
        return "apply" in self._safe_str(step_title).lower()

    def _step_requires_verification(self, step_title: str) -> bool:
        return "verify" in self._safe_str(step_title).lower()

    def _step_output_indicates_real_change(self, step_output: str) -> bool:
        lowered = self._safe_str(step_output).lower()
        return any(x in lowered for x in ["changed", "updated", "patched", "modified"])

    def _step_output_indicates_real_verification(self, step_output: str) -> bool:
        lowered = self._safe_str(step_output).lower()
        return any(x in lowered for x in ["verified", "tested", "confirmed", "passes"])

    def _can_advance_execution_step(self, execution, user_text, step_title, step_output, attachments=None):
        execution = execution or {}
        attachments = attachments or []

        goal_text = self._safe_str(execution.get("goal"))
        current_step_text = self._safe_str(execution.get("current_step"))
        combined_text = "\n".join(
            part for part in [
                self._safe_str(user_text),
                goal_text,
                current_step_text,
            ]
            if self._safe_str(part).strip()
        )

        if not self._has_real_debug_context(combined_text, execution, attachments):
            missing_parts = []

            lowered_text = combined_text.lower()

            if len(combined_text.strip()) < 10:
                missing_parts.append("clear problem description")

            if "traceback" not in lowered_text and "error" not in lowered_text and "exception" not in lowered_text and "500" not in lowered_text:
                missing_parts.append("exact error or traceback")

            if "def " not in combined_text and ".py" not in lowered_text and "line " not in lowered_text and "\\" not in combined_text and "/" not in combined_text:
                missing_parts.append("relevant code snippet or file path")

            instruction_lines = [
                "Step blocked.",
                "",
                "To continue, send:",
            ]

            for i, part in enumerate(missing_parts, start=1):
                instruction_lines.append(f"{i}. {part}")

            if not missing_parts:
                instruction_lines.append("1. more detailed context")

            instruction_lines.append("")
            instruction_lines.append("Example:")
            instruction_lines.append("Error: ...")
            instruction_lines.append("Code: ...")
            instruction_lines.append("Expected: ...")

            return False, "\n".join(instruction_lines)

        if self._step_requires_real_change(step_title):
            if not self._step_output_indicates_real_change(step_output):
                return False, "No real code change detected."

        if self._step_requires_verification(step_title):
            if not self._step_output_indicates_real_verification(step_output):
                return False, "No real verification detected."

        return True, ""

    # =========================
    # EXECUTION RENDER NORMALIZATION LOCK
    # =========================

    def _execution_status_label(self, execution):
        execution = execution or {}
        steps = execution.get("steps") or []

        total = len(steps)
        done = sum(1 for s in steps if (s or {}).get("done"))

        if total > 0 and done >= total:
            return "complete"

        idx = execution.get("current_step_index", 0) or 0
        if 0 <= idx < total:
            title = str((steps[idx] or {}).get("title") or "").strip()
            if title:
                return title

        return "in progress"

    def _render_execution(self, execution, include_prefix=False):
        execution = self._normalize_execution_state(dict(execution or {}))
        goal = str(execution.get("goal") or "").strip()
        steps = execution.get("steps") or []

        print("RENDER EXECUTION =", execution)
        print("RENDER STEPS =", steps)

        total = len(steps)
        done = sum(1 for s in steps if (s or {}).get("status") == "done")

        current_index = int(execution.get("current_step_index", 0) or 0)
        if 0 <= current_index < total:
            current_step = str((steps[current_index] or {}).get("title") or "").strip() or "Untitled step"
        elif total > 0:
            current_step = "complete"
        else:
            current_step = ""

        lines = []

        if include_prefix:
            prefix = (
                "Auto-execution complete."
                if total > 0 and done >= total
                else "Auto-execution advanced."
            )
            lines.append(prefix)
            lines.append("")

        if goal:
            lines.append(f"Goal: {goal}")
            lines.append("")

        lines.append("Steps:")
        for s in steps:
            s = s or {}
            title = str(s.get("title") or "").strip() or "Untitled step"
            status = str(s.get("status") or "pending").strip().lower()

            if status == "done":
                mark = "[x]"
            elif status == "current":
                mark = "[>]"
            else:
                mark = "[ ]"

            lines.append(f"{mark} {title}")

        lines.append("")
        lines.append(f"Progress: {done}/{total} complete")
        lines.append(f"Current step: {current_step}")

        return "\n".join(lines).strip()

    def _build_execution_assistant_text(self, execution):
        return self._render_execution(execution, include_prefix=True)

    def _build_execution_artifact_body(self, execution):
        return self._render_execution(execution, include_prefix=False)

    def _normalize_working_state(self, working_state):
        working_state = working_state or {}
        keys = [
            "active_task",
            "current_file",
            "current_bug",
            "last_success",
            "next_move",
            "checkpoint",
        ]

        clean = {}
        for key in keys:
            value = working_state.get(key, "")
            if value is None:
                value = ""
            value = str(value).strip()
            if value:
                clean[key] = value

        return clean


    def _build_working_state_summary(self, working_state):
        ws = self._normalize_working_state(working_state)
        if not ws:
            return ""

        lines = []

        mapping = [
            ("active_task", "Active task"),
            ("current_file", "Current file"),
            ("current_bug", "Current bug"),
            ("last_success", "Last success"),
            ("next_move", "Next move"),
            ("checkpoint", "Checkpoint"),
        ]

        for key, label in mapping:
            value = ws.get(key, "").strip()
            if value:
                lines.append(f"{label}: {value}")

        if not lines:
            return ""

        return "Working context:\n" + "\n".join(lines)


    def _build_continuity_context(self, session=None):
        session = session or {}
        working_state = session.get("working_state") or {}

        summary = self._build_working_state_summary(working_state)

        if not summary:
            return ""

        return summary


    def _build_system_prompt(self, decision=None):
        parts = []

        parts.append(
            "You are Nova, a focused AI workspace assistant. "
            "Be clear, direct, continuity-aware, and useful. "
            "Prefer action over explanation. "
            "Do not ramble. "
            "Preserve the user's momentum."
        )

        parts.append(
            "When coding or project-building, be precise and operational. "
            "Keep outputs structured and grounded in the user's active work."
        )

        parts.append(
            "Response style rules: "
            "be concise, confident, and practical. "
            "Prefer direct answers first. "
            "Avoid generic assistant filler. "
            "When relevant, anchor the reply to the user's active file, bug, or next move. "
            "Do not repeat the working context unless it improves the reply. "
            "Use it quietly to stay aligned."
        )

        if decision and isinstance(decision, dict):
            mode = (decision.get("mode") or "").strip()
            if mode:
                parts.append(f"Current operating mode: {mode}.")

        intent = self._safe_str((decision or {}).get("intent")).lower()

        if intent == "debugging":
            parts.append(
                "DEBUGGING MODE: Do not give generic debugging checklists. "
                "Do not list frameworks. "
                "Do not say 'check logs' without giving the exact command. "
                "Prefer PowerShell commands, exact file paths, search anchors, and full-file fixes. "
                "If the exact file is unknown, ask for ONE specific missing item: the file path or error log. "
                "Use the user's style: direct, endgame, no filler."
            )

        return "\n\n".join([p for p in parts if p]).strip()

    def _compose_model_messages(self, user_text, session=None, decision=None, memory_context=None):
        session = session or {}
        memory_context = self._safe_str(memory_context).strip()

        system_prompt = self._build_system_prompt(decision=decision)
        continuity_context = self._build_continuity_context(session=session)

        execution_text = ""
        try:
            latest = self._find_latest_execution_artifact(session_id=session.get("id", ""))
            if latest:
                execution = latest.get("execution") or {}
                if execution:
                    execution_text = self._render_execution(execution)
        except Exception:
            execution_text = ""

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        if continuity_context:
            messages.append({
                "role": "system",
                "content": continuity_context
            })

        if execution_text:
            messages.append({
                "role": "system",
                "content": f"Current execution:\n{execution_text}"
            })

        if memory_context:
            messages.append({
                "role": "system",
                "content": (
                    "Memory about the user (use this as ground truth when relevant):\n"
                    f"{memory_context}"
                )
            })

        messages.append({
            "role": "user", 
            "content": user_text or ""
        })

        return messages

    def _maybe_update_working_state(self, session_id: str, user_text: str):
        session_id = self._safe_str(session_id).strip()
        if not session_id:
            return {}

        current_state = self._get_working_state(session_id)
        updates = self._extract_working_state_updates(user_text, current_state)

        if not isinstance(updates, dict) or not updates:
            return current_state

        return self._update_working_state(session_id, updates)

    def _is_valid_state_value(self, value):
        if not value:
            return False

        value = str(value).strip()

        if len(value) > 120:
            return False

        if "\n" in value:
            return False

        bad_patterns = [
            "recommended order",
            "next, improve",
            "current project truth",
            "if you want",
        ]

        lower = value.lower()
        for p in bad_patterns:
            if p in lower:
                return False

        return True

    def _load_memory(self):
        """
        Real memory loader wired to Nova MemoryService.
        """
        try:
            if hasattr(self, "memory") and self.memory:
                if hasattr(self.memory, "all"):
                    result = self.memory.all()
                    if isinstance(result, list):
                        return result

            return []

        except Exception:
            return []
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

    def _normalize_memory_text_for_save(self, text) -> str:
        raw = self._safe_str(text).strip()
        if not raw:
            return ""

        lowered = raw.lower().strip()

        junk_exact = {
            "hi",
            "hello",
            "hey",
            "ok",
            "okay",
            "yes",
            "no",
            "run it",
            "continue",
            "next",
            "thanks",
            "thank you",
        }

        if lowered in junk_exact:
            return ""

        blocked_starts = (
            "what do you remember",
            "what do u remember",
            "do you remember",
            "tell me what you remember",
        )

        if lowered.startswith(blocked_starts):
            return ""


        return raw

    def _should_save_memory_text(self, text, kind=None) -> bool:
        cleaned = self._normalize_memory_text_for_save(text)
        if not cleaned:
            return False

        kind = self._safe_str(kind).lower().strip()
        lowered = cleaned.lower()

        junk_patterns = (
            "traceback",
            "attributeerror",
            "nameerror",
            "unboundlocalerror",
            "taberror",
            "syntaxerror",
            "indentationerror",
            "internal error",
            "chat_service.py",
            "nova_backend",
            "copy regenerate",
        )

        if any(pattern in lowered for pattern in junk_patterns):
            return False

        if kind in {"profile", "project", "preference", "goal", "note", "style"}:
            return True

        strong_signals = (
            "my name is",
            "user's name is",
            "user prefers to be called",
            "i am ",
            "i'm ",
            "i work on",
            "i'm working on",
            "i am working on",
            "user is working on",
            "user is building",
        )

        if any(s in lowered for s in strong_signals):
            return True

        weak_signals = (
            "i prefer",
            "user preference",
            "remember",
            "from now on",
            "going forward",
        )

        return any(s in lowered for s in weak_signals)

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

        return "IÃ¢â‚¬â„¢m here, but the model returned an empty response."

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
        attachments=None,
        session_id: str = "",
    ) -> dict:

        user_text = self._safe_str(user_text)
        lower_text = user_text.lower()

        attachments = attachments or []

        # =========================
        # IMAGE GENERATION (PRIORITY)
        # =========================
        image_triggers = (
            "generate an image",
            "make an image",
            "create an image",
            "draw ",
            "picture of",
            "image of",
            "render ",
        )

        if any(trigger in lower_text for trigger in image_triggers):
            return {
                "route": self.ROUTE_IMAGE_GENERATION,   # ðŸ”¥ use constant
                "mode": "image_generation",
                "confidence": 0.95,
                "reasons": ["image_generation_intent"],
                "save_artifact": True,
                "save_memory": False,
                "use_memory": False,
                "prompt": user_text,
            }

        # =========================
        # IMAGE ANALYSIS (attachments)
        # =========================
        if attachments:
            return {
                "route": self.ROUTE_ATTACHMENT_ANALYSIS,
                "mode": "image_analysis",
                "confidence": 0.9,
                "reasons": ["attachment_present"],
                "save_artifact": True,
                "save_memory": False,
                "use_memory": False,
            }

        # =========================
        # WEB SEARCH
        # =========================
        web_triggers = (
            "latest",
            "news",
            "today",
            "current",
            "price",
            "stock",
            "bitcoin",
            "nvidia",
        )

        if any(trigger in lower_text for trigger in web_triggers):
            return {
                "route": self.ROUTE_WEB_FETCH,   # ðŸ”¥ use constant
                "mode": "web_fetch",
                "confidence": 0.85,
                "reasons": ["web_intent"],
                "save_artifact": True,
                "save_memory": False,
                "use_memory": False,
            }

        # =========================
        # DEFAULT CHAT
        # =========================
        return {
            "route": self.ROUTE_GENERAL_CHAT,
            "mode": "chat",
            "confidence": 0.6,
            "reasons": ["default_chat"],
            "save_artifact": False,
            "save_memory": True,
            "use_memory": True,
        }

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


    def _looks_like_execution(self, user_text: str, decision: dict | None = None) -> bool:
        text = str(user_text or "").strip().lower()

        if not text:
            return False


        # ðŸ”¥ PLAN CREATION
        if any(x in text for x in ["plan", "steps", "how to", "next steps"]):
            return True

        # ðŸ”¥ FALLBACK: coding / structured intent
        if decision and decision.get("mode") in {"coding", "analysis"}:
            return True

        return False


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


    def _get_persisted_execution_artifact(self, session_id: str):
        session_id = self._safe_str(session_id)
        if not session_id:
            return None

        try:
            sessions = self.session_service.list_sessions()
        except Exception as e:
            print("GET PERSISTED EXECUTION LOAD SESSIONS FAILED:", e)
            return None

        if isinstance(sessions, dict):
            if isinstance(sessions.get("sessions"), list):
                sessions = sessions.get("sessions") or []
            elif isinstance(sessions.get("items"), list):
                sessions = sessions.get("items") or []
            else:
                sessions = []

        if not isinstance(sessions, list):
            return None

        for session in sessions:
            if not isinstance(session, dict):
                continue

            if self._safe_str(session.get("id")) != session_id:
                continue

            persisted = session.get("active_execution")
            if isinstance(persisted, dict):
                return persisted

            persisted = session.get("execution")
            if isinstance(persisted, dict):
                return persisted

            persisted = session.get("working_execution")
            if isinstance(persisted, dict):
                return persisted

            return None

        return None

    def _persist_execution_artifact(self, session_id: str, execution: dict | None) -> None:
        session_id = self._safe_str(session_id)
        if not session_id:
            return

        if not isinstance(execution, dict):
            execution = {}

        execution = self._normalize_execution_state(dict(execution or {}))
        execution["session_id"] = session_id
        execution["active"] = True

        try:
            sessions = self.session_service.list_sessions()
        except Exception as e:
            print("PERSIST EXECUTION LOAD SESSIONS FAILED:", e)
            return

        if isinstance(sessions, dict):
            items = sessions.get("sessions")
            if not isinstance(items, list):
                return
            sessions["sessions"] = items
            wrapped = True
        elif isinstance(sessions, list):
            items = sessions
            wrapped = False
        else:
            return

        updated = False

        for session in items:
            if not isinstance(session, dict):
                continue
            if self._safe_str(session.get("id")) != session_id:
                continue

            session["active_execution"] = dict(execution)
            updated = True
            break

        if not updated:
            return

        try:
            if wrapped:
                self.session_service.save_sessions(sessions)
            else:
                self.session_service.save_sessions(items)
        except Exception as e:
            print("PERSIST EXECUTION SAVE SESSIONS FAILED:", e)

    def _find_latest_execution_artifact(self, session_id: str = ""):
        session_id = self._safe_str(session_id)

        try:
            artifacts = []

            if hasattr(self, "artifact_service") and hasattr(self.artifact_service, "list_all"):
                artifacts = self.artifact_service.list_all()
            elif hasattr(self, "artifacts") and hasattr(self.artifacts, "list_all"):
                artifacts = self.artifacts.list_all()

            artifacts = artifacts or []

            print("ALL ARTIFACTS =", artifacts)

            matches = []

            for a in artifacts:
                a = a or {}

                if session_id and self._safe_str(a.get("session_id")) != session_id:
                    continue

                execution = a.get("execution") or ((a.get("meta") or {}).get("execution")) or {}

                if execution:
                    print("MATCHED EXECUTION ARTIFACT =", a)
                    matches.append(a)

            matches.sort(
                key=lambda x: self._safe_str(x.get("created_at")),
                reverse=True,
            )

            latest = matches[0] if matches else None

            print("FINAL LATEST =", latest)

            return latest

        except Exception as e:
            print("FIND EXECUTION FAILED =", e)
            return None

    def _attach_execution(self, payload, user_text, assistant_msg, decision, session_id=""):
        execution = self._build_execution(
            user_text=user_text,
            assistant_text=str(assistant_msg.get("text") or ""),
            decision=decision,
        )

        return payload

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

# =========================
# EXECUTION PROGRESSION (PHASE 5)
# =========================

    def _looks_like_execution_progression(self, user_text: str) -> bool:
        text = self._safe_str(user_text).strip().lower()
        if not text:
            return False

        normalized = " ".join(text.split())
        print("PROGRESS_MATCH_NORMALIZED =", repr(normalized))

        triggers = {
            "run it",
            "continue",
            "go on",
            "next step",
            "advance",
            "proceed",
            "keep going",
        }

        if normalized in triggers:
            return True

        if normalized.endswith(" run it"):
            return True

        if "run it" in normalized and len(normalized) <= 40:
            return True

        return False

    def _normalize_execution_state(self, execution):
        if not isinstance(execution, dict):
            execution = {}

        execution.setdefault("goal", "")
        execution.setdefault("steps", [])
        execution.setdefault("current_step_index", 0)
        execution.setdefault("status", "running")
        execution.setdefault("progress", 0)
        execution.setdefault("current_step", "")

        raw_steps = execution.get("steps") or []
        clean_steps = []

        for raw in raw_steps:
            if isinstance(raw, dict):
                title = str(raw.get("title") or "").strip()
            else:
                title = str(raw).strip()

            if not title:
                continue

            clean_steps.append({
                "title": title,
                "status": "pending",
            })

        step_count = len(clean_steps)

        if step_count == 0:
            execution["steps"] = []
            execution["current_step_index"] = 0
            execution["progress"] = 0
            execution["current_step"] = "complete" if execution.get("status") == "complete" else ""
            execution["status"] = "complete"
            return execution

        try:
            current_index = int(execution.get("current_step_index", 0) or 0)
        except Exception:
            current_index = 0

        if current_index < 0:
            current_index = 0
        if current_index > step_count:
            current_index = step_count

        status = str(execution.get("status") or "running").strip().lower()
        if status not in ["running", "complete", "blocked"]:
            status = "running"

        if status == "complete" or current_index >= step_count:
            current_index = step_count
            for step in clean_steps:
                step["status"] = "done"
            progress = step_count
            current_step = "complete"
            status = "complete"
        else:
            for idx, step in enumerate(clean_steps):
                if idx < current_index:
                    step["status"] = "done"
                elif idx == current_index:
                    step["status"] = "current"
                else:
                    step["status"] = "pending"

            progress = current_index
            current_step = clean_steps[current_index]["title"]

        execution["steps"] = clean_steps
        execution["current_step_index"] = current_index
        execution["progress"] = progress
        execution["current_step"] = current_step
        execution["status"] = status
        return execution


    def _advance_execution_one_step(self, execution):
        execution = self._normalize_execution_state(dict(execution or {}))

        steps = execution.get("steps") or []
        step_count = len(steps)
        current_index = int(execution.get("current_step_index", 0) or 0)

        if step_count == 0:
            execution["status"] = "complete"
            execution["current_step_index"] = 0
            execution["progress"] = 0
            execution["current_step"] = "complete"
            execution["steps"] = []
            return execution

        if current_index >= step_count:
            execution["current_step_index"] = step_count
            execution["progress"] = step_count
            execution["current_step"] = "complete"
            execution["status"] = "complete"
            return self._normalize_execution_state(execution)

        next_index = current_index + 1
        execution["current_step_index"] = next_index

        if next_index >= step_count:
            execution["status"] = "complete"
            execution["current_step"] = "complete"
            execution["progress"] = step_count
        else:
            execution["status"] = "running"
            execution["current_step"] = steps[next_index]["title"]
            execution["progress"] = next_index

        return self._normalize_execution_state(execution)

    def _extract_text_response(self, response) -> str:
        try:
            if hasattr(response, "output_text") and response.output_text:
                return response.output_text

            if hasattr(response, "output") and response.output:
                parts = []
                for item in response.output:
                    if hasattr(item, "content"):
                        for c in item.content:
                            if hasattr(c, "text"):
                                parts.append(c.text)
                return "\n".join(parts)

            return str(response)
        except Exception as e:
            return f"[extract_error] {e}"

    def _advance_execution_request(self, user_text: str, session_id: str = "", attachments=None):
        attachments = attachments or []
        session_id = self._safe_str(session_id)
        user_text = self._safe_str(user_text)
        assistant_text = ""

        print("ADVANCE SESSION_ID =", session_id)

        persisted_execution = self._get_persisted_execution_artifact(session_id=session_id)
        latest_artifact = self._find_latest_execution_artifact(session_id=session_id)

        print("ADVANCE PERSISTED EXECUTION =", persisted_execution)
        print("ADVANCE LATEST ARTIFACT =", latest_artifact)

        user_msg = self._build_user_message(
            user_text,
            attachments=attachments,
        )

        execution = {}
        if isinstance(persisted_execution, dict) and persisted_execution:
            execution = persisted_execution
        execution = {}
        if isinstance(persisted_execution, dict) and persisted_execution:
            execution = persisted_execution
        elif isinstance(latest_artifact, dict):
            execution = latest_artifact.get("execution") or {}
        else:
            execution = {}

        execution = self._normalize_execution_state(execution)

        if self._safe_str(execution.get("status")).lower() == "complete":
            execution = {}

        if self._safe_str(execution.get("status")).lower() == "complete":
            execution = {}

        if not execution:
            assistant_msg = self._build_assistant_message(
                text="No execution found. Start with a plan first.",
                attachments=[],
            )
            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=user_msg,
                assistant_msg=assistant_msg,
                decision={
                    "route": "execution",
                    "mode": "execution_progress",
                    "save_artifact": False,
                    "save_memory": False,
                    "use_memory": True,
                },
                saved_artifact=None,
            )

        goal_text = self._safe_str(execution.get("goal")).lower()
        step_index = int(execution.get("current_step_index", 0) or 0)

        if "plan" in goal_text:
            if step_index == 0:
                step_output = "State inspected. Missing inputs identified. Ready to proceed."
            elif step_index == 1:
                step_output = "Proceeding with a general-purpose plan structure using assumptions."
            elif step_index == 2:
                step_output = """Plan:

Goal:
Create a clear actionable plan.

Steps:
1. Define the objective
2. Break into tasks
3. Prioritize tasks
4. Assign timeline
5. Identify resources
6. Execute
7. Review and adjust

Next action:
Write the exact goal in one sentence.
"""
            elif step_index == 3:
                step_output = "Plan structure verified for completeness and usability."
            elif step_index >= 4:
                step_output = "Plan created. Next step: refine based on real inputs."
            else:
                step_output = "Step executed."
        else:
            step_output = "Step executed."

        execution = self._advance_execution_one_step(execution)
        execution = self._normalize_execution_state(execution)

        saved_artifact = None

        artifact_payload = {
            "kind": "execution",
            "title": "Execution Plan",
            "body": self._render_execution(execution),
            "summary": f"Execution plan for: {self._safe_str(execution.get('goal'))}",
            "preview": self._render_execution(execution)[:140],
            "session_id": session_id,
            "source": "execution",
            "execution": execution,
            "meta": {
                "auto_generated": True,
                "auto_executed": False,
                "complete": self._safe_str(execution.get("status")).lower() == "complete",
                "done": int(execution.get("progress", 0) or 0),
                "total": len(execution.get("steps") or []),
                "paused": False,
                "active_execution": self._safe_str(execution.get("status")).lower() != "complete",
            },
        }

        try:
            saved_artifact = self._call_first(
                self.artifacts,
                ["save_artifact", "create_artifact", "add_artifact", "save", "create"],
                artifact_payload,
            )
        except Exception as e:
            print("ADVANCE EXECUTION SAVE FAILED (positional):", e)
            saved_artifact = None

        if not saved_artifact:
            try:
                saved_artifact = self._call_first(
                    self.artifacts,
                    ["save_artifact", "create_artifact", "add_artifact", "save", "create"],
                    artifact=artifact_payload,
                )
            except Exception as e:
                print("ADVANCE EXECUTION SAVE FAILED (keyword artifact):", e)
                saved_artifact = None

        try:
            self._persist_execution_artifact(session_id=session_id, execution=execution)
        except Exception as e:
            print("ADVANCE EXECUTION PERSIST FAILED:", e)

        plan_body = self._render_execution(execution)

        if step_output:
            assistant_text = step_output
            if plan_body:
                assistant_text += "\n\n" + plan_body
        else:
            assistant_text = "Step processed."
            if plan_body:
                assistant_text += "\n\n" + plan_body

        assistant_msg = self._build_assistant_message(
            text=assistant_text,
            attachments=[],
        )

        return self._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            decision={
                "route": "execution",
                "mode": "execution_progress",
                "save_artifact": bool(saved_artifact),
                "save_memory": False,
                "use_memory": True,
            },
            saved_artifact=saved_artifact,
        )

    # =========================
    # AUTO EXECUTION LOOP (PHASE 6)
    # =========================

    def _looks_like_auto_execution_request(self, user_text: str) -> bool:
        text = self._safe_str(user_text).strip().lower()

        return text in {
            "run all",
            "auto execute",
            "finish the plan",
            "do it all",
            "complete it",
        }

    def _looks_like_plan_request(self, user_text: str) -> bool:
        text = self._safe_str(user_text).strip().lower()
        if not text:
            return False

        triggers = [
            "plan ",
            "make a plan",
            "create a plan",
            "build a plan",
            "debug ",
            "fix ",
            "implement ",
            "next steps",
            "step by step",
        ]

        return any(trigger in text for trigger in triggers)

    # =========================
    # EXECUTION STEP LOCK HELPERS
    # =========================

    def _execution_step_count(self, execution):
        steps = execution.get("steps") or []
        return len(steps)

    def _execution_current_index(self, execution):
        try:
            value = int(execution.get("current_step_index", 0))
        except Exception:
            value = 0

        step_count = self._execution_step_count(execution)
        if step_count <= 0:
            return 0

        if value < 0:
            return 0
        if value > step_count:
            return step_count
        return value

    def _execution_progress_count(self, execution):
        steps = execution.get("steps") or []
        done = 0
        for step in steps:
            if isinstance(step, dict) and step.get("status") == "done":
                done += 1
        return done
 
    def _get_execution_artifacts_source(self):
        artifacts = []

        try:
            artifacts = self._call_first(
                self.artifacts,
                [
                    "list_artifacts",
                    "get_artifacts",
                    "get_all",
                    "list",
                    "all",
                    "load_artifacts",
                ],
            ) or []
        except Exception:
            artifacts = []

        if not isinstance(artifacts, list) or not artifacts:
            try:
                fallback = self._get_artifacts_list()
                if isinstance(fallback, list):
                    artifacts = fallback
            except Exception:
                pass

        if isinstance(artifacts, dict):
            artifacts = list(artifacts.values())

        if not isinstance(artifacts, list):
            return []

        return [a for a in artifacts if isinstance(a, dict)]

    def _build_execution_plan(self, user_text: str, session_id: str):
        goal = self._safe_str(user_text).strip() or "Complete the requested task"

        steps = [
            "Inspect the current state and constraints",
            "Choose the safest implementation path",
            "Apply the required change",
            "Verify the result",
            "Summarize outcome and next move",
        ]

        execution = self._normalize_execution_state({
            "goal": goal,
            "steps": [
                {"title": s, "status": "current" if i == 0 else "pending"}
                for i, s in enumerate(steps)
            ],
            "current_step_index": 0,
            "progress": 0,
            "current_step": steps[0],
            "status": "running",
        })

        body = self._render_execution(execution)

        artifact_payload = {
            "kind": "execution",
            "title": "Execution Plan",
            "body": body,
            "summary": f"Execution plan for: {goal}",
            "preview": body[:140],
            "session_id": session_id,
            "source": "execution",
            "execution": execution,
            "meta": {
                "auto_generated": True,
                "auto_executed": False,
                "complete": False,
                "done": 0,
                "total": len(steps),
                "paused": False,
                "active_execution": True,
            },
        }

        saved_artifact = None

        try:
            saved_artifact = self._call_first(
                self.artifacts,
                ["save_artifact", "create_artifact", "add_artifact", "save", "create"],
                artifact_payload,
            )
        except Exception as e:
            print("BUILD EXECUTION PLAN FAILED (positional):", e)
            saved_artifact = None

        if not saved_artifact:
            try:
                saved_artifact = self._call_first(
                    self.artifacts,
                    ["save_artifact", "create_artifact", "add_artifact", "save", "create"],
                    artifact=artifact_payload,
                )
            except Exception as e:
                print("BUILD EXECUTION PLAN FAILED (keyword artifact):", e)
                saved_artifact = None

        artifact_id = ""
        if isinstance(saved_artifact, dict):
            artifact_id = self._safe_str(saved_artifact.get("id"))

        execution["artifact_id"] = artifact_id
        execution["session_id"] = session_id
        execution["active"] = True

        try:
            self._persist_execution_artifact(session_id=session_id, execution=execution)
        except Exception as e:
            print("BUILD EXECUTION PLAN PERSIST EXECUTION FAILED:", e)

        print("BUILD EXECUTION PLAN SAVED =", bool(saved_artifact))
        print("BUILD EXECUTION PLAN SESSION =", session_id)
        print("BUILD EXECUTION PLAN ARTIFACT =", saved_artifact)
        print("BUILD EXECUTION PLAN ACTIVE EXECUTION =", execution)

        return saved_artifact

    def _extract_execution_lines(self, body: str):
        lines = self._safe_str(body).splitlines()
        step_indexes = []
        current_index = -1

        for i, line in enumerate(lines):
            if any(x in line for x in ["[ ]", "[>]", "[x]", "[X]", "âœ”", "Ã¢Å“â€"]):
                step_indexes.append(i)

            if "[>]" in line:
                current_index = i

        return lines, step_indexes, current_index

    def _refresh_execution_header(self, body: str):
        lines = self._safe_str(body).splitlines()

        total = sum(1 for line in lines if any(x in line for x in ["[ ]", "[>]", "[x]", "[X]", "âœ”", "Ã¢Å“â€"]))
        done = sum(1 for line in lines if any(x in line for x in ["[x]", "[X]", "âœ”", "Ã¢Å“â€"]))

        updated = "\n".join(lines)
        updated = re.sub(
            r"Progress:\s*\d+/\d+",
            f"Progress: {done}/{total}",
            updated,
        )

        current_line = ""
        for line in lines:
            if "[>]" in line:
                current_line = (
                    line.replace("[>]", "")
                    .replace("[ ]", "")
                    .replace("[x]", "")
                    .replace("[X]", "")
                    .replace("âœ”", "")
                    .replace("Ã¢Å“â€", "")
                    .strip(" -")
                    .strip()
                )
                break

        if current_line:
            updated = re.sub(
                r"Current step:\s*.*",
                f"Current step: {current_line}",
                updated,
            )
        elif done == total and total > 0:
            updated = re.sub(
                r"Current step:\s*.*",
                "Current step: Complete",
                updated,
            )

        return updated, done, total

    def _auto_execute_request(self, user_text: str, session_id: str = "", attachments=None):
        # ðŸ”’ Execution system disabled during stabilization
        return self._execute_general_chat(
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
            decision={
                "route": self.ROUTE_GENERAL_CHAT,
                "intent": "chat",
                "save_artifact": False,
                "save_memory": True,
            },
        )
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

    def _set_session_meta(self, session_id: str, key: str, value):
        try:
            if hasattr(self.session_service, "update_working_state"):
                patch = {key: value}
                self.session_service.update_working_state(session_id, patch)
                return
        except Exception as e:
            print("SET SESSION META FAILED:", e)

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

    def _build_working_state_prompt_block(self, session_id: str) -> str:
        state = self._get_working_state(session_id) or {}
        if not isinstance(state, dict) or not state:
            return ""

        ordered_fields = [
            ("active_task", "Active task"),
            ("current_file", "Current file"),
            ("current_bug", "Current bug"),
            ("last_success", "Last success"),
            ("next_move", "Next move"),
            ("checkpoint", "Checkpoint"),
        ]

        lines = []
        for key, label in ordered_fields:
            value = self._safe_str(state.get(key)).strip()
            if value:
                lines.append(f"- {label}: {value}")

        if not lines:
            return ""

        return "Working state:\n" + "\n".join(lines)

    def _derive_working_state_patch_from_step_output(
        self,
        step_title: str,
        step_output: str,
        current_state: dict | None = None,
    ) -> dict:
        current_state = current_state if isinstance(current_state, dict) else {}
        step_title = self._safe_str(step_title).strip()
        step_output = self._safe_str(step_output).strip()

        if not step_output:
            return {}

        patch = {}

        # basic success memory
        patch["last_success"] = step_title or "Completed execution step"

        lowered = step_output.lower()

        next_markers = [
            "next implication",
            "next move",
            "next step",
        ]

        extracted_next = ""
        for marker in next_markers:
            idx = lowered.find(marker)
            if idx != -1:
                raw = step_output[idx:]
                parts = raw.split("\n", 1)
                if len(parts) > 1:
                    extracted_next = parts[1].strip()
                else:
                    extracted_next = raw.strip()
                break

        if extracted_next:
            first_line = extracted_next.splitlines()[0].strip(" -:\t")
            if first_line:
                patch["next_move"] = first_line

        if step_title and not self._safe_str(current_state.get("active_task")).strip():
            patch["active_task"] = step_title

        return patch

        # ==============================
        # WORKING STATE (PHASE 3)
        # ==============================

    def _get_working_state(self, session_id: str):
            state = self._call_first(
                self.sessions,
                ["get_working_state"],
                session_id,
                default={},
            )

            if not isinstance(state, dict):
                state = {}

            cleaned = {}
            for key in (
                "active_task",
                "current_file",
                "current_bug",
                "last_success",
                "next_move",
                "checkpoint",
                "updated_at",
            ):
                value = state.get(key, "")
                if key == "updated_at":
                    cleaned[key] = self._safe_str(value)
                else:
                    cleaned[key] = self._clean_working_state_value(value)

            return cleaned

    def _handle_where_are_we(self, session_id: str, user_text: str = "") -> str:
            state = self._get_working_state(session_id) or {}

            active_task = self._safe_str(state.get("active_task")).strip()
            current_file = self._safe_str(state.get("current_file")).strip()
            current_bug = self._safe_str(state.get("current_bug")).strip()
            last_success = self._safe_str(state.get("last_success")).strip()
            next_move = self._safe_str(state.get("next_move")).strip()
            checkpoint = self._safe_str(state.get("checkpoint")).strip()

            lowered = self._safe_str(user_text).lower().strip()

            if not any([active_task, current_file, current_bug, last_success, next_move, checkpoint]):
                return "I do not have a working context locked in yet."

            if any(
                phrase in lowered
                for phrase in [
                    "what file are we in",
                    "current file",
                    "which file",
                    "what file",
                ]
            ):
                if current_file:
                    return f"WeÃ¢â‚¬â„¢re in `{current_file}`."
                return "I do not have the current file locked in yet."

            if any(
                phrase in lowered
                for phrase in [
                    "what broke",
                    "what is broken",
                    "current bug",
                    "bug",
                    "issue",
                    "error",
                ]
            ):
                if current_bug:
                    return f"What broke: {current_bug}"
                return "I do not have a current bug locked in."

            if any(
                phrase in lowered
                for phrase in [
                    "what did we fix",
                    "what was fixed",
                    "last success",
                    "what worked",
                    "what is working",
                ]
            ):
                if last_success:
                    return f"What we fixed: {last_success}"
                return "I do not have a last success locked in yet."

            if any(
                phrase in lowered
                for phrase in [
                    "what's next",
                    "whats next",
                    "what is next",
                    "next move",
                    "next step",
                    "now what",
                ]
            ):
                if next_move:
                    return f"Next: {next_move}"
                return "I do not have a next move locked in yet."

            if any(
                phrase in lowered
                for phrase in [
                    "checkpoint",
                    "save point",
                    "phase",
                ]
            ):
                if checkpoint:
                    return f"Checkpoint: {checkpoint}"
                return "I do not have a checkpoint locked in yet."

            lines = []

            if active_task:
                lines.append(f"Active task: {active_task}")
            if current_bug:
                lines.append(f"Current bug: {current_bug}")
            if current_file:
                lines.append(f"Current file: `{current_file}`")
            if last_success:
                lines.append(f"Last success: {last_success}")
            if next_move:
                lines.append(f"Next move: {next_move}")
            if checkpoint:
                lines.append(f"Checkpoint: {checkpoint}")

            if not lines:
                return "I do not have a working context locked in yet."

            if active_task and next_move:
                return (
                    f"WeÃ¢â‚¬â„¢re {active_task}. "
                    f"Next: {next_move}"
                    + (f" Current file: `{current_file}`." if current_file else "")
                    + (f" Current bug: {current_bug}." if current_bug else "")
                )

            return "\n".join(lines)

        # =========================
        # WORKING STATE HELPERS
        # =========================

    def _clean_working_state_value(self, value, limit=120):
            text = self._safe_str(value).strip()
            if not text:
                return ""

            text = text.replace("\r", " ").replace("\n", " ")
            text = re.sub(r"\s+", " ", text).strip()

            bad_starts = (
                "yes",
                "agreed",
                "recommended",
                "in short",
                "what this means",
            )

            lower = text.lower()
            if any(lower.startswith(x) for x in bad_starts):
                return ""

            for splitter in [" and ", " but ", " so "]:
                if splitter in text:
                    text = text.split(splitter)[0].strip()

            return text[:limit]

    def _is_valid_state_value(self, value):
            if not value:
                return False

            value = str(value).strip()
            if not value:
                return False

            if len(value) > 120:
                return False

            if "\n" in value:
                return False

            bad_patterns = [
                "recommended order",
                "if you want",
                "you can also",
                "for example",
            ]

            lower = value.lower()
            for p in bad_patterns:
                if p in lower:
                    return False

            return True

    def _merge_working_state(self, current_state, updates):
            current_state = current_state if isinstance(current_state, dict) else {}
            updates = updates if isinstance(updates, dict) else {}

            merged = {
                "active_task": "",
                "current_file": "",
                "current_bug": "",
                "last_success": "",
                "next_move": "",
                "checkpoint": "",
            }

            for key in merged.keys():
                old_value = self._clean_working_state_value(current_state.get(key, ""))
                new_value = self._clean_working_state_value(updates.get(key, ""))

                merged[key] = new_value if new_value else old_value

            from datetime import datetime, timezone
            merged["updated_at"] = datetime.now(timezone.utc).isoformat()

            return merged  

    def _extract_working_state_updates(self, user_text: str, current_state: dict | None = None) -> dict:
        text = self._safe_str(user_text).strip()
        if not text:
            return {}

        current_state = current_state if isinstance(current_state, dict) else {}
        lowered = text.lower()
        updates = {}

        field_aliases = {
            "active_task": [
                "active task",
                "task",
            ],
            "current_file": [
                "current file",
                "file",
            ],
            "current_bug": [
                "current bug",
                "bug",
            ],
            "last_success": [
                "last success",
            ],
            "next_move": [
                "next move",
            ],
            "checkpoint": [
                "checkpoint",
            ],
        }

        def _clean_value(value: str) -> str:
            value = self._safe_str(value).strip()
            value = value.strip("+    â† (FOUR SPACES â€” press space 4 times)\r\n-:;,.")
            return value

        def _set_if_present(field_name: str, value: str):
            value = _clean_value(value)
            if value:
                updates[field_name] = value

        # -----------------------------
        # explicit "set X to Y" patterns
        # -----------------------------
        for field_name, aliases in field_aliases.items():
            for alias in aliases:
                patterns = [
                    f"set {alias} to ",
                    f"update {alias} to ",
                    f"change {alias} to ",
                    f"{alias} is ",
                    f"{alias}: ",
                ]
                for marker in patterns:
                    idx = lowered.find(marker)
                    if idx != -1:
                        raw_value = text[idx + len(marker):]
                        _set_if_present(field_name, raw_value)
                        break
                if field_name in updates:
                    break

        # -----------------------------------
        # compact continuity / status patterns
        # -----------------------------------
        continuity_markers = [
            ("working on ", "active_task"),
            ("i'm working on ", "active_task"),
            ("im working on ", "active_task"),
            ("current task is ", "active_task"),
            ("my current task is ", "active_task"),
            ("focus is ", "active_task"),
            ("next move is ", "next_move"),
            ("the next move is ", "next_move"),
            ("current bug is ", "current_bug"),
            ("the bug is ", "current_bug"),
            ("last success was ", "last_success"),
            ("checkpoint is ", "checkpoint"),
            ("current file is ", "current_file"),
        ]

        for marker, field_name in continuity_markers:
            idx = lowered.find(marker)
            if idx != -1 and field_name not in updates:
                raw_value = text[idx + len(marker):]
                _set_if_present(field_name, raw_value)

        # -----------------------------
        # file path extraction
        # -----------------------------
        if "current_file" not in updates:
            path_match = re.search(
                r"([A-Za-z]:\\[^\r\n\"'<>|?*]+(?:\.[A-Za-z0-9_]+)?)",
                text,
            )
            if path_match:
                _set_if_present("current_file", path_match.group(1))

        # -----------------------------------------
        # preserve state if user says "where are we"
        # or similar continuity-checking questions
        # -----------------------------------------
        continuity_queries = [
            "where are we",
            "what are we doing",
            "what were we doing",
            "what now",
            "what's next",
            "whats next",
            "status",
            "recap",
        ]
        if any(q in lowered for q in continuity_queries):
            return {}

        # -----------------------------------------
        # strip values that just repeat old state
        # -----------------------------------------
        deduped = {}
        for key, value in updates.items():
            existing = self._safe_str(current_state.get(key)).strip()
            if self._safe_str(value).strip() and self._safe_str(value).strip() != existing:
                deduped[key] = value

        return deduped

    def _format_working_state(self, state):
            def c(x): return x if x else " "
            return (
                f"Active task: {c(state.get('active_task'))}\n"
                f"Current file: {c(state.get('current_file'))}\n"
                f"Current bug: {c(state.get('current_bug'))}\n"
                f"Last success: {c(state.get('last_success'))}\n"
                f"Next move: {c(state.get('next_move'))}\n"
                f"Checkpoint: {c(state.get('checkpoint'))}"
            )

    # =========================
    # WORKING STATE HELPERS
    # =========================
            
    def _format_working_state_context(self, session_id: str) -> str:
            state = self._get_working_state(session_id)
            if not isinstance(state, dict) or not state:
                return ""

            lines = []

            if self._safe_str(state.get("active_task")):
                lines.append(f"- Active task: {self._safe_str(state.get('active_task'))}")
            if self._safe_str(state.get("current_file")):
                lines.append(f"- Current file: {self._safe_str(state.get('current_file'))}")
            if self._safe_str(state.get("current_bug")):
                lines.append(f"- Current bug: {self._safe_str(state.get('current_bug'))}")
            if self._safe_str(state.get("last_success")):
                lines.append(f"- Last success: {self._safe_str(state.get('last_success'))}")
            if self._safe_str(state.get("next_move")):
                lines.append(f"- Next move: {self._safe_str(state.get('next_move'))}")
            if self._safe_str(state.get("checkpoint")):
                lines.append(f"- Checkpoint: {self._safe_str(state.get('checkpoint'))}")

            if not lines:
                return ""

            return "Working context:\n" + "\n".join(lines)

    # ===============================
    # WORKING STATE (PHASE 3)
    # ===============================

    def _get_working_state(self, session_id: str) -> dict:
        session_id = self._safe_str(session_id).strip()
        if not session_id:
            return {}

        try:
            session = self.sessions.get_session(session_id) or {}
        except Exception:
            session = {}

        state = session.get("working_state")

        if isinstance(state, dict):
            return dict(state)

        return {}

    def _update_working_state(self, session_id: str, patch: dict):
        session_id = self._safe_str(session_id).strip()
        if not session_id:
            return {}

        if not isinstance(patch, dict):
            patch = {}

        current_state = self._get_working_state(session_id)
        merged = dict(current_state)

        for key, value in patch.items():
            if value is None:
                continue
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    continue
            merged[key] = value

        merged["updated_at"] = self._iso_now()

        print("WORKING_STATE_MERGED =", merged)

        # primary path
        try:
            updated = self.sessions.update_session(
                session_id,
                {"working_state": merged},
            ) or {}
            persisted = updated.get("working_state")
            print("WORKING_STATE_UPDATED_SESSION =", persisted)
            if isinstance(persisted, dict):
                print("FINAL_WORKING_STATE_BEFORE_RETURN =", persisted)
                return dict(persisted)
        except Exception as e:
            print("WORKING_STATE_UPDATE_SESSION_FAILED =", e)

        # fallback: force write into session store
        try:
            session = self.sessions.get_session(session_id) or {}
            if isinstance(session, dict):
                session["working_state"] = dict(merged)

                sessions = self.sessions.list_sessions() or []

                replaced = False
                for i, s in enumerate(sessions):
                    if isinstance(s, dict) and s.get("id") == session_id:
                        sessions[i] = session
                        replaced = True
                        break

                if not replaced:
                    sessions.append(session)

                save_all = getattr(self.sessions, "_save_sessions", None)
                if callable(save_all):
                    save_all(sessions)

                refreshed = self.sessions.get_session(session_id) or {}
                persisted = refreshed.get("working_state")
                print("WORKING_STATE_FALLBACK_PERSISTED =", persisted)

                if isinstance(persisted, dict) and any(
                    (str(v).strip() if v is not None else "") for v in persisted.values()
                ):
                    print("FINAL_WORKING_STATE_BEFORE_RETURN =", persisted)
                    return dict(persisted)

        except Exception as e:
            print("WORKING_STATE_FALLBACK_FAILED =", e)

        print("FINAL_WORKING_STATE_BEFORE_RETURN =", merged)
        return dict(merged)

    # ==============================
    # MEMORY HELPERS
    # ==============================

    def _rank_memory_context(self, user_text: str, limit: int = 5, session_id: str = ""):
        user_text = self._safe_str(user_text).lower()

        memory = self._get_memory_list()
        scored = []

        for item in memory:
            if not isinstance(item, dict):
                continue

            text = self._safe_str(item.get("text")).lower()
            kind = self._safe_str(item.get("kind")).lower()

            score = 0

            # ðŸ”¥ keyword match (stronger)
            for word in user_text.split():
                if word and word in text:
                    score += 3

            # ðŸ”¥ HIGH PRIORITY TYPES
            if kind in ("project", "goal"):
                score += 8

            # ðŸ”¥ MEDIUM PRIORITY
            if kind in ("identity", "preference"):
                score += 5

            # ðŸ”¥ penalize junk
            if kind == "note":
                score -= 2

            # ðŸ”¥ longer meaningful memories get slight boost
            if len(text) > 20:
                score += 1

            scored.append((score, item))

        # sort by score
        scored.sort(key=lambda x: x[0], reverse=True)

        # ðŸ”¥ ALWAYS include at least 1 important memory if exists
        top = [item for score, item in scored if score > 0]

        if not top:
            # fallback: still give latest memory
            return memory[-5:]

        return top[:limit]
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

    def _shape_assistant_response(self, assistant_text: str, user_text: str = "") -> str:
        return self._safe_str(assistant_text).strip()

    def _maybe_write_memory(self, decision: dict, user_text: str, session_id: str) -> None:
        if not isinstance(decision, dict):
            return

        text = self._normalize_memory_text_for_save(user_text)
        lowered = text.lower()

        if not text:
            return

        should_save = False
        kind = "note"

        # ===== MEMORY CLASSIFICATION =====

        if any(x in lowered for x in [
            "my name is",
            "call me",
            "prefers to be called",
        ]):
            should_save = True
            kind = "profile"

        elif any(x in lowered for x in [
            "answer me",
            "talk to me",
            "respond with",
            "be direct",
            "no fluff",
            "tldr",
            "smff",
            "i prefer",
            "from now on",
            "going forward",
        ]):
            should_save = True
            kind = "preference"

        elif any(x in lowered for x in [
            "my project",
            "i'm building",
            "i am building",
            "i'm working on",
            "i am working on",
            "my app",
            "my system",
        ]):
            should_save = True
            kind = "project"

        elif any(x in lowered for x in [
            "my goal",
            "i want to",
            "i need to",
            "i plan to",
        ]):
            should_save = True
            kind = "goal"

        elif "remember that" in lowered or "remember this" in lowered:
            should_save = True
            kind = "note"

        # ===== FILTER =====

        if len(text.split()) < 4:
            should_save = False

        if lowered.strip() in (
            "hello", "hi", "ok", "okay", "thanks", "lol", "next", "go", "test"
        ):
            should_save = False

        if not should_save:
            return

        if not self._should_save_memory_text(text, kind=kind):
            return

        # ===== DUPLICATE PREVENTION =====
        try:
            existing_items = []
            if hasattr(self, "memory") and self.memory and hasattr(self.memory, "all"):
                existing_items = self.memory.all() or []

            for item in existing_items:
                if not isinstance(item, dict):
                    continue

                existing_text = self._normalize_memory_text_for_save(item.get("text", ""))
                existing_kind = self._safe_str(item.get("kind")).lower().strip()
                existing_session = self._safe_str(item.get("session_id")).strip()

                if (
                    existing_text
                    and existing_text.lower() == text.lower()
                    and existing_kind == kind
                    and existing_session == self._safe_str(session_id)
                ):
                    return

        except Exception:
            pass

        # ===== SAVE =====
        try:
            self.memory.add_memory({
                "text": text,
                "kind": kind,
                "source": "auto",
                "session_id": session_id,
            })
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

        if k in {"profile", "identity"}:
            return 9.0

        if k in {"style"}:
            return 8.0   # ðŸ”¥ NEW â€” how you want responses

        if k in {"preference"}:
            return 7.0

        if k in {"project", "goal"}:
            return 6.0

        if k in {"instruction", "workflow"}:
            return 5.0

        if k in {"note"}:
            return 2.0

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
            return 0.75   # â†“ reduced from 1.5

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
                (overlap_score * 2.0)
                + exact_phrase_score
                + (contains_named_value * 1.5)
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

        # explicit command
        if text.startswith("/image") or "/image" in text:
            return True

        # strong keyword detection
        keywords = [
            "generate", "create", "make", "draw", "render", "design"
        ]

        image_words = [
            "image", "picture", "photo", "art", "scene", "visual"
        ]

        # ðŸ”¥ detect intent: action + image concept
        if any(k in text for k in keywords) and any(i in text for i in image_words):
            return True

        return False


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
                    "kind": "image",
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
                "saved_artifact": saved_artifact,
            }

        except Exception as e:
            print("IMAGE GENERATION FAILED:", e)
            return {
                "ok": False,
                "text": f"Image generation failed: {e}",
                "error": str(e),
                "image_url": "",
                "prompt": prompt,
                "revised_prompt": "",
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

            source_url = self._safe_str(meta.get("source_url")) or self._safe_str(result.get("final_url") or result.get("url") or normalized_url)

            source_urls = []
            if source_url:
                source_urls.append(source_url)

            return {
                "ok": bool(result.get("ok", True)),
                "text": summary or f"Fetched {title}",
                "artifact": final_artifact,
                "viewer": viewer,
                "url": self._safe_str(result.get("final_url") or result.get("url") or normalized_url),
                "source_url": source_url,
                "source_urls": source_urls,
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

                assistant_text = self._extract_response_text(response)

            except Exception:
                assistant_text = "I couldnâ€™t analyze that image."

        else:
            assistant_text = "I couldnâ€™t find an image attachment to analyze."

        return {
            "ok": True,
            "assistant_text": assistant_text,
            "assistant_message": {
                "role": "assistant",
                "text": assistant_text,
            },
            "debug": {
                "route_taken": "attachment_analysis",
                "image_name": image_name,
                "has_image": bool(image_url),
            },
        }

        # ==============================
        # MODEL HELPERS
        # ==============================

    def _format_response_policy_for_prompt(self, response_policy=None) -> str:
        response_policy = response_policy if isinstance(response_policy, dict) else {}

        instruction = self._safe_str(response_policy.get("instruction")).strip()
        mode = self._safe_str(response_policy.get("mode")).strip()
        answer_length = self._safe_str(response_policy.get("answer_length")).strip()
        tone = self._safe_str(response_policy.get("tone")).strip()

        if not instruction and not mode:
            return ""

        return (
            "\n\nRESPONSE POLICY — HIGH PRIORITY:\n"
            f"- Mode: {mode or 'normal'}\n"
            f"- Answer length: {answer_length or 'normal'}\n"
            f"- Tone: {tone or 'direct'}\n"
            f"- Needs full file: {bool(response_policy.get('needs_full_file'))}\n"
            f"- Needs debug: {bool(response_policy.get('needs_debug'))}\n"
            f"- Needs commands: {bool(response_policy.get('needs_commands'))}\n"
            f"- User frustrated: {bool(response_policy.get('user_frustrated'))}\n\n"
            "Follow these rules above generic assistant behavior.\n"
            "When policy conflicts with normal style, policy wins.\n"
            f"{instruction}\n"
        )

def _build_chat_input(
    self,
    user_text: str,
    decision: dict,
    session_id: str = "",
    working_context_block: str = "",
    memory_context: str = "",
) -> str:

    user_text = self._safe_str(user_text)
    decision = decision if isinstance(decision, dict) else {}

    memory_items = self._rank_memory_context(
        user_text=user_text,
        limit=20,
        session_id=session_id,
    )

    selected_memory = []
    seen = set()

    def add_memory_item(item):
        if not isinstance(item, dict):
            return

        text = self._safe_str(item.get("text"))
        key = text.lower().strip()

        if not key or key in seen:
            return

        seen.add(key)
        selected_memory.append(item)

    # 1. Pinned memories always win.
    for item in memory_items:
        if isinstance(item, dict) and item.get("pinned"):
            add_memory_item(item)

    # 2. High-value memory types come next.
    for item in memory_items:
        if not isinstance(item, dict):
            continue

        if item.get("pinned"):
            continue

        kind = self._safe_str(item.get("kind")).lower()
        if kind in ["preference", "goal", "project", "profile"]:
            add_memory_item(item)

    # 3. Heavy weighted memories next.
    for item in memory_items:
        if not isinstance(item, dict):
            continue

        if item in selected_memory:
            continue

        try:
            weight_num = float(item.get("weight", 1))
        except Exception:
            weight_num = 1.0

        if weight_num >= 2:
            add_memory_item(item)

    # 4. Fill the rest with normal ranked memories.
    for item in memory_items:
        if len(selected_memory) >= 10:
            break

        add_memory_item(item)

    selected_memory = selected_memory[:10]

    memory_block = self._format_memory_context(selected_memory)
    self._last_used_memory_items = selected_memory

    if memory_context:
        memory_block = self._safe_str(memory_context)

    session = self._get_session_payload(session_id)
    messages = session.get("messages", []) if isinstance(session, dict) else []

    recent_lines = []
    for msg in messages[-8:]:
        if not isinstance(msg, dict):
            continue

        role = self._safe_str(msg.get("role"))
        text = self._safe_str(msg.get("text"))

        if not role or not text:
            continue

        recent_lines.append(f"{role}: {text}")

    recent_block = "\n".join(recent_lines)

    # ==============================
    # RESPONSE POLICY INJECTION
    # ==============================

    response_policy = self._build_response_policy(
        user_text=user_text,
        decision=decision,
    )

    response_policy_block = self._format_response_policy_for_prompt(response_policy)

    sections = []

    if memory_block:
        sections.append(
            "IMPORTANT USER MEMORY:\n"
            "Use this memory as active instruction context. "
            "Prefer it over generic assistant behavior when relevant.\n"
            f"{memory_block}"
        )

    if working_context_block:
        sections.append(
            "CURRENT WORKING CONTEXT:\n"
            f"{working_context_block}"
        )

    if recent_block:
        sections.append(
            "RECENT CONVERSATION:\n"
            f"{recent_block}"
        )

    sections.append(
        "USER MESSAGE:\n"
        f"{user_text}"
    )

    sections.append(
        "RESPONSE RULES:\n"
        "- Be direct.\n"
        "- Use the user's saved preferences when relevant.\n"
        "- For code help, prefer full-file or exact replacement blocks.\n"
        "- Include file paths when discussing project files.\n"
        "- Do not give generic chatbot filler."
        + response_policy_block
    )

    final_chat_input = "\n\n".join(sections).strip()

    print("MEMORY_DOMINANCE_USED_COUNT:", len(selected_memory))
    print("MEMORY_DOMINANCE_BLOCK_PRESENT:", bool(memory_block))

    return final_chat_input

    def _build_common_state_payload(self, session_id: str = "") -> dict:
        session = self._get_session_payload(session_id)

        return {
            "ok": True,
            "active_session_id": session_id,
            "session_id": session_id,
            "session": session if isinstance(session, dict) else {},
            "active_session": session if isinstance(session, dict) else {},
            "messages": session.get("messages", []) if isinstance(session, dict) else [],
            "artifacts": self._list_artifacts_for_session(session_id),
            "memory": self._list_memory_for_session(session_id),
        }

        # ==============================
        # RESPONSE BUILDERS
        # ==============================


    def _execute_memory_recall(
            self,
            decision: dict,
            user_text: str,
            session_id: str,
            attachments=None,
        ) -> dict:
            attachments = attachments or []

            user_msg = self._build_user_message(
                user_text,
                attachments=attachments,
            )

            assistant_text = self._build_memory_recall_text(
                session_id=session_id,
                user_text=user_text,
                limit=int(decision.get("memory_limit") or self.memory_limit),
            )

            assistant_msg = self._build_assistant_message(
                text=assistant_text,
                meta={
                    "memory_recall": True,
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
                        "save_artifact": False,
                        "save_memory": False,
                        "use_memory": False,
                    },
                    saved_artifact=None,
                )

            summary = f"Web operator is not fully wired yet.\n\nTarget: {base_url}"

            user_msg = self._build_user_message(user_text, attachments=[])
            assistant_msg = self._build_assistant_message(
                text=summary,
                meta={"web_operator": True, "url": base_url},
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
                    "save_artifact": False,
                    "save_memory": False,
                    "use_memory": False,
                },
                saved_artifact=None,
            )
        except Exception as e:
            user_msg = self._build_user_message(user_text, attachments=[])
            assistant_msg = self._build_assistant_message(
                text=f"Web operator failed: {e}",
                meta={"web_operator": True, "error": True},
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
                    "save_artifact": False,
                    "save_memory": False,
                    "use_memory": False,
                },
                saved_artifact=None,
            )


    def _ensure_session_payload(self, session_id: str) -> dict:
        session = self._call_first(
            self.sessions,
            ["get_session", "read_session", "get", "load_session"],
            session_id,
        )

        if isinstance(session, dict):
            session.setdefault("id", session_id)
            session.setdefault("messages", [])
            session.setdefault("working_state", {})
            return session

        created = self._call_first(
            self.sessions,
            ["create_session", "new_session", "create", "start_session"],
        )
        if isinstance(created, dict):
            created_id = self._safe_str(created.get("id")) or session_id
            session = self._call_first(
                self.sessions,
                ["get_session", "read_session", "get", "load_session"],
                created_id,
            )
            if isinstance(session, dict):
                session.setdefault("id", created_id)
                session.setdefault("messages", [])
                session.setdefault("working_state", {})
                return session

            return {
                "id": created_id,
                "messages": [],
                "working_state": {},
            }

        return {
            "id": session_id,
            "messages": [],
            "working_state": {},
        }

    def _execute_current_step(self, execution: dict, user_text: str, session_id: str = "", attachments=None) -> dict:
        attachments = attachments or []
        execution = self._normalize_execution_state(dict(execution or {}))

        steps = execution.get("steps") or []
        current_index = self._execution_current_index(execution)

        if not steps or current_index >= len(steps):
            execution["status"] = "complete"
            execution["current_step"] = "complete"
            execution["progress"] = len(steps)
            execution.setdefault("step_results", [])
            return {
                "execution": execution,
                "step_output": "No remaining execution step.",
                "saved_artifact": {
                    "kind": "execution",
                    "title": self._safe_str(execution.get("goal")) or "Execution",
                    "body": self._render_execution(execution),
                    "execution": execution,
                    "meta": {
                        "execution": execution,
                        "execution_id": self._safe_str(execution.get("id")),
                        "status": self._safe_str(execution.get("status")) or "complete",
                        "progress": execution.get("progress", len(steps)),
                        "current_step": self._safe_str(execution.get("current_step")) or "complete",
                        "goal": self._safe_str(execution.get("goal")),
                    },
                },
            }

        current_step = steps[current_index] or {}
        step_title = self._safe_str(current_step.get("title")) or f"Step {current_index + 1}"
        goal = self._safe_str(execution.get("goal"))
        execution.setdefault("step_results", [])

        system_prompt = (
            "You are executing one step in Nova's task engine. "
            "Be concrete, operational, and brief. "
            "Return useful progress for the current step only."
        )

        user_prompt_parts = [
            f"Goal: {goal}",
            f"Current step ({current_index + 1}/{len(steps)}): {step_title}",
        ]

        if user_text.strip():
            user_prompt_parts.append(f"Latest user input: {user_text}")

        if attachments:
            attachment_lines = []
            for item in attachments:
                if not isinstance(item, dict):
                    continue
                name = self._safe_str(item.get("filename") or item.get("name") or item.get("stored_name"))
                url = self._safe_str(item.get("url"))
                mime_type = self._safe_str(item.get("mime_type") or item.get("mime"))
                bits = [bit for bit in [name, mime_type, url] if bit]
                if bits:
                    attachment_lines.append(" - " + " | ".join(bits))
            if attachment_lines:
                user_prompt_parts.append("Attachments:\n" + "\n".join(attachment_lines))

        user_prompt = "\n\n".join(part for part in user_prompt_parts if part)

        step_output = ""
        tool_bundle = {}

        try:
            response = self.client.responses.create(
                model=self.chat_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            step_output = self._extract_text_response(response).strip()
        except Exception as exc:
            step_output = f"Step execution failed: {exc}"

        if not step_output:
            step_output = f"Completed step: {step_title}"

        step_result = {
            "step_index": current_index,
            "step_title": step_title,
            "output": step_output,
            "completed_at": self._iso_now(),
        }
        execution["step_results"].append(step_result)

        next_index = current_index + 1
        execution["current_step_index"] = next_index
        execution["progress"] = next_index

        if next_index >= len(steps):
            execution["status"] = "complete"
            execution["current_step"] = "complete"
            execution["current_step_index"] = len(steps)
            execution["progress"] = len(steps)
        else:
            execution["status"] = "in_progress"
            next_step = steps[next_index] or {}
            execution["current_step"] = self._safe_str(next_step.get("title")) or f"Step {next_index + 1}"

        artifact_payload = {
            "kind": "execution",
            "title": goal or "Execution",
            "body": self._render_execution(execution),
            "execution": execution,
            "meta": {
                "execution": execution,
                "goal": goal,
                "step_index": current_index,
                "step_title": step_title,
                "execution_id": self._safe_str(execution.get("id")),
                "tool_bundle": tool_bundle or {},
                "status": self._safe_str(execution.get("status")),
                "progress": execution.get("progress", 0),
                "current_step": self._safe_str(execution.get("current_step")),
            },
        }

        return {
            "execution": execution,
            "step_output": step_output,
            "saved_artifact": artifact_payload,
        }

    def _maybe_execute_tool(self, step_title: str, user_text: str, execution: dict | None = None) -> dict:
        tool_decision = self._decide_tool_for_step(
            step_title=step_title,
            user_text=user_text,
            execution=execution,
        )

        if not tool_decision:
            return {}

        tool_result = self._run_tool_decision(tool_decision)
        return {
            "decision": tool_decision,
            "result": tool_result,
        }

    def _guess_path_from_text(self, text: str) -> str:
        text = self._safe_str(text)

        windows_path_match = re.search(r"([A-Za-z]:\\[^\n\r\t\"']+)", text)
        if windows_path_match:
            return windows_path_match.group(1).strip()

        py_path_match = re.search(r"([A-Za-z0-9_./\\-]+\.py)\b", text)
        if py_path_match:
            raw = py_path_match.group(1).strip()
            if os.path.isabs(raw):
                return raw
            return os.path.abspath(raw)

        return ""

    def _guess_search_query_from_text(self, text: str) -> str:
        text = self._safe_str(text)

        m = re.search(r"search for\s+(.+)", text, flags=re.IGNORECASE)
        if m:
            return self._safe_str(m.group(1))

        m = re.search(r"find\s+(.+)", text, flags=re.IGNORECASE)
        if m:
            return self._safe_str(m.group(1))

        return ""

    def _decide_tool_for_step(self, step_title: str, user_text: str, execution: dict | None = None) -> dict:
        step_title = self._safe_str(step_title).lower()
        user_text = self._safe_str(user_text)
        lowered = user_text.lower()
        execution = execution or {}

        path = self._guess_path_from_text(user_text) or self._guess_path_from_text(
            self._safe_str(execution.get("goal"))
        )

        # read file
        if any(
            x in step_title
            for x in [
                "inspect",
                "review",
                "analyze",
                "read",
                "verify",
                "current state",
                "constraints",
            ]
        ):
            if path:
                return {
                    "tool_name": "read_file",
                    "args": {"path": path},
                    "reason": "step suggests inspection and a file path is available",
                }

        # search inside file
        if any(x in step_title for x in ["search", "find", "locate", "verify"]):
            query = self._guess_search_query_from_text(user_text)
            if path and query:
                return {
                    "tool_name": "search_in_file",
                    "args": {"path": path, "query": query},
                    "reason": "step suggests search and both path/query are available",
                }

        # list dir
        if any(x in step_title for x in ["list files", "directory", "folder", "project structure"]):
            if path:
                dir_path = path if os.path.isdir(path) else os.path.dirname(path)
                if dir_path:
                    return {
                        "tool_name": "list_dir",
                        "args": {"path": dir_path},
                        "reason": "step suggests directory inspection",
                    }

        # apply change -> only suggest for now, do not write yet
        if any(x in step_title for x in ["apply", "change", "modify", "fix"]):
            if path:
                return {
                    "tool_name": "read_file",
                    "args": {"path": path},
                    "reason": "step suggests code change; read file first before any write",
                }

        # fallback heuristic from raw user text
        if path and any(x in lowered for x in ["bug", "error", "debug", "fix", ".py", "traceback"]):
            return {
                "tool_name": "read_file",
                "args": {"path": path},
                "reason": "debugging request with file path detected",
            }

        return {}

    def _run_tool_decision(self, tool_decision: dict) -> dict:
        if not isinstance(tool_decision, dict):
            return {}

        tool_name = self._safe_str(tool_decision.get("tool_name"))
        args = tool_decision.get("args") or {}

        if not tool_name:
            return {}

        try:
            if tool_name == "read_file":
                return self.tools.read_file(args.get("path", ""))
            if tool_name == "search_in_file":
                return self.tools.search_in_file(
                    args.get("path", ""),
                    args.get("query", ""),
                )
            if tool_name == "list_dir":
                return self.tools.list_dir(args.get("path", ""))
        except Exception as e:
            return {"ok": False, "error": str(e), "tool_name": tool_name}

        return {"ok": False, "error": f"Unknown tool: {tool_name}", "tool_name": tool_name}

    def _cleanup_memory_items(self) -> None:
        try:
            memories = getattr(self.memory_service, "memories", None)
            if not isinstance(memories, list):
                return

            cleaned = []
            seen = set()

            for memory in memories:
                text = self._safe_str(memory.get("text")).strip().lower()

                if not text or len(text) < 4:
                    continue

                if text in ["ok","hi","yo","test","next","go"]:
                    continue

                if text in seen:
                    continue

                seen.add(text)
                cleaned.append(memory)

            self.memory_service.memories = cleaned

            if hasattr(self.memory_service, "_save"):
                self.memory_service._save()

        except Exception as e:
            print("MEMORY CLEANUP FAILED:", e)
