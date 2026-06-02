from __future__ import annotations

import base64
import os
import re
import uuid
import logging
import shutil
import tempfile
import py_compile

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

from nova_backend.services.execution_handler import (
    ExecutionHandler,
    NextMove,
    default_executor,
)

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
from nova_backend.services.execution_loop_service import ExecutionLoopService
from nova_backend.services.brain.brain_core import BrainCore
from nova_backend.services.brain.strategy import StrategyEngine
from nova_backend.services.memory.memory_core import MemoryCore
from nova_backend.services.execution.executor import Executor
from nova_backend.services.python_runner_service import PythonRunnerService
from nova_backend.services.runtime_bootstrap import (
    RuntimeBootstrap,
)
from nova_backend.services.runtime_cognitive_injection_service import (
    RuntimeCognitiveInjectionService,
)

from nova_backend.services.runtime_cognitive_firewall import (
    RuntimeCognitiveFirewall,
)

logger = logging.getLogger("nova.execution")
DEBUG_EXECUTION = False


def exec_debug(*args):
    if DEBUG_EXECUTION:
        logger.debug(" ".join(str(arg) for arg in args))


class ChatService:
    ROUTE_GENERAL_CHAT = "general_chat"
    ROUTE_IMAGE_GENERATION = "image_generation"
    ROUTE_WEB_FETCH = "web_fetch"
    ROUTE_ATTACHMENT_ANALYSIS = "attachment_analysis"
    ROUTE_PLANNING = "planning"
    ROUTE_MEMORY_RECALL = "memory_recall"

    def _get_working_state(self, session_id: str) -> dict:
        session_id = self._safe_str(session_id).strip()

        if not session_id:
            return {}

        try:
            session = self._get_session_payload(session_id)

            if not isinstance(session, dict):
                return {}

            state = session.get("working_state")

            if isinstance(state, dict):
                return state

            return {}

        except Exception as e:
            exec_debug("GET WORKING STATE FAILED:", e)
            return {}

    def _is_control_command_value(self, value):

        text = self._safe_str(
            value
        ).strip().lower()

        blocked = {
            "run_step",
            "run step",
            "run_all",
            "run all",
            "run it",
            "execute",
            "execute all",
            "continue",
            "resume",
            "next",
            "nex",
            "k",
            "kk",
            "what now",
            "what next",
            "retry",
            "retry_failed",
            "retry failed",
            "try again",
            "stop",
            "cancel",
            "go",
        }

        return text in blocked

    def _update_working_state(self, session_id: str, patch: dict) -> dict:
        session_id = self._safe_str(session_id).strip()

        if not session_id:
            return {}

        if not isinstance(patch, dict):
            patch = {}

        blocked_state_values = {
            "",
            "continuity_working",
            "working_state_resume_context",
            "no active work to resume.",
        }

        protected_keys = {
            "last_success",
            "checkpoint",
            "next_move",
            "active_task",
            "current_bug",
        }

        try:
            current = self._get_working_state(session_id)
            current = current if isinstance(current, dict) else {}

            for key, value in patch.items():
                key = self._safe_str(key).strip()

                if key in {
                    "active_task",
                    "next_move",
                    "mission",
                }:

                    if self._is_control_command_value(value):
                        continue

                if not key:
                    continue

                # allow explicit clearing
                if value in [None, "", [], {}]:

                    if key in current:
                        del current[key]

                    continue

                # preserve structured state dictionaries
                if isinstance(value, dict):
                    current[key] = value
                    continue

                normalized_value = self._safe_str(value).lower().strip()

                if (
                    key == "checkpoint"
                    and normalized_value == "execution_plan_created"
                ):

                    execution_state = (
                        self._get_session_meta(
                            session_id,
                            "execution_state",
                        )
                        or {}
                    )

                    steps = (
                        execution_state.get("steps")
                        or []
                    )

                    if not steps:
                        continue

                if key in protected_keys and normalized_value in blocked_state_values:
                    if key in current:
                        del current[key]
                    continue

                current[key] = value

            if hasattr(self.sessions, "update_working_state"):
                self.sessions.update_working_state(
                    session_id,
                    current,
                )
                return current

            sessions = self.sessions._load_sessions()

            index = self.sessions._find(
                sessions,
                session_id,
            )

            if index is not None:
                sessions[index]["working_state"] = current

                self.sessions._save_sessions(
                    sessions,
                    self.sessions.get_active_session_id(),
                )

            return current

        except Exception as e:
            exec_debug("UPDATE WORKING STATE FAILED:", e)
            return {}


    def _normalize_working_state(self, working_state):
        if isinstance(working_state, dict):
            return working_state
        if working_state is None:
            return {}
        if isinstance(working_state, str):
            try:
                import json
                parsed = json.loads(working_state)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

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
            value = str(ws.get(key, "")).strip()
            if value:
                lines.append(f"{label}: {value}")

        if not lines:
            return ""

        return "Working context:\n" + "\n".join(lines)


    def _decide_route(self, user_text="", attachments=None, memory_context="", working_context_block="", session_id=""):
        return {
            "route": self.ROUTE_GENERAL_CHAT,
            "mode": "chat",
            "confidence": 0.6,
            "reasons": ["fallback_decide_route"],
            "save_artifact": False,
            "save_memory": True,
            "use_memory": True,
        }

    def _build_memory_context_for_chat(self, user_text="", decision=None, session_id=""):
        decision = decision if isinstance(decision, dict) else {}

        if decision.get("use_memory") is False:
            return ""

        memory_limit = int(decision.get("memory_limit") or self.memory_limit or 6)
        memory_limit = max(1, min(memory_limit, 12))

        lines = []

        try:
            ranked_items = self._rank_memory_context(
                user_text=user_text,
                limit=memory_limit,
                session_id=session_id,
            )

            if isinstance(ranked_items, list) and ranked_items:
                lines.append("[RANKED MEMORY + WORKING STATE]")
                for item in ranked_items:
                    if not isinstance(item, dict):
                        continue

                    kind = self._safe_str(item.get("kind") or "memory").strip()
                    source = self._safe_str(item.get("source") or "").strip()
                    text = self._safe_str(
                        item.get("text")
                        or item.get("content")
                        or ""
                    ).strip()

                    if not text:
                        continue

                    label = kind
                    if source:
                        label = f"{kind} / {source}"

                    lines.append(f"- {label}: {text[:1000]}")

        except Exception as e:
            exec_debug("BUILD_RANKED_MEMORY_CONTEXT_FAILED:", e)

        try:
            session = self._get_session_payload(session_id) if session_id else {}
            messages = session.get("messages", []) if isinstance(session, dict) else []

            if isinstance(messages, list) and messages:
                recent = messages[-8:]
                lines.append("\n[RECENT SESSION CONTEXT]")
                for msg in recent:
                    if not isinstance(msg, dict):
                        continue

                    role = self._safe_str(msg.get("role") or "").strip()
                    text = self._safe_str(
                        msg.get("text")
                        or msg.get("content")
                        or msg.get("message")
                        or ""
                    ).strip()

                    if role and text:

                        lines.append(f"{role}: {text[:800]}")

        except Exception as e:
            exec_debug("BUILD_RECENT_SESSION_CONTEXT_FAILED:", e)

        return "\n".join(lines).strip()

    def _build_system_prompt(
        self,
        decision=None,
    ):

        parts = []

        parts.append(
            "You are Nova, an intelligent "
            "continuity-aware AI workspace assistant. "
            "Track conversational order carefully "
            "and prioritize the latest user corrections "
            "and facts. "
            "Do not contradict recent conversation "
            "context. "
            "Avoid robotic one-word replies unless "
            "explicitly requested. "
            "Respond naturally, directly, and with "
            "conversational continuity. "
            "Preserve the user's momentum and active "
            "context."
        )

        parts.append(
            "When coding or project-building, "
            "be precise and operational. "
            "Keep outputs structured and grounded "
            "in the user's active work."
        )

        parts.append(
            "Response style rules: "
            "be concise, confident, and practical. "
            "Prefer direct answers first. "
            "Avoid generic assistant filler. "
            "When relevant, anchor the reply to the "
            "user's active file, bug, or next move. "
            "Do not repeat the working context unless "
            "it improves the reply. "
            "Use it quietly to stay aligned."
        )

        if (
            decision
            and isinstance(decision, dict)
        ):

            mode = (
                decision.get("mode")
                or ""
            ).strip()

            if mode:
                parts.append(
                    f"Current operating mode: "
                    f"{mode}."
                )

        intent = self._safe_str(
            (decision or {}).get("intent")
        ).lower()

        if intent == "debugging":

            parts.append(
                "DEBUGGING MODE: "
                "Do not give generic debugging "
                "checklists. "
                "Do not list frameworks. "
                "Do not say 'check logs' without "
                "giving the exact command. "
                "Prefer PowerShell commands, exact "
                "file paths, search anchors, and "
                "full-file fixes. "
                "If the exact file is unknown, ask "
                "for ONE specific missing item: "
                "the file path or error log. "
                "Use the user's style: direct, "
                "endgame, no filler."
            )

        return "\n\n".join(
            [p for p in parts if p]
        ).strip()

    def _auto_advance_execution(self, session_id):
        return None


    def _execute_step_logic(self, session_id, step):
        try:
            step["status"] = "running"

            step_action = self._safe_str(
                step.get("action")
            ).lower()

            print(
                "STEP ACTION =",
                repr(step_action),
            )

            target_file = self._safe_str(
                step.get("target_file")
            )

            python_result = None

            if (
                step_action == "implement"
                and target_file
            ):

                Path(target_file).parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                Path(target_file).write_text(
                    '''
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


if __name__ == "__main__":
    print("Calculator app created.")
    print("2 + 3 =", add(2, 3))
'''.strip()
                    + "\n",
                    encoding="utf-8",
                )

                step["result"] = (
                    f"Created file: {target_file}"
                )

                step["error"] = None

            elif (
                step_action in {
                    "test",
                    "run",
                    "execute",
                }
                and target_file
                and hasattr(self, "python_runner")
            ):

                python_result = (
                    self.python_runner.run_file(
                        target_file
                    )
                )

                result = (
                    f"STDOUT="
                    f"{python_result.get('stdout')} | "
                    f"STDERR="
                    f"{python_result.get('stderr')} | "
                    f"ERROR="
                    f"{python_result.get('error')}"
                )

                step["result"] = result

                step["error"] = (
                    None
                    if python_result.get("ok")
                    else result
                )

            else:

                step["result"] = (
                    "step executed"
                )

                step["error"] = None

            step["status"] = "completed"

        except Exception as e:
            step["status"] = "failed"
            step["error"] = str(e)

    def _resume_execution_if_needed(self, session_id):
        session = self.sessions.get(session_id)

        if not session:
            return None

        state = session.get("working_state") or {}
        execution = state.get("execution_state") or {}

        if execution.get("status") == "running":
            return {
                "resume": True,
                "step_index": execution.get("current_index", 0),
                "steps": execution.get("steps", []),
            }

        return None

    def _continue_execution(self, session_id, resume_data):
        return {
            "ok": False,
            "assistant_message": self._build_assistant_message(
                text="Legacy execution path disabled."
            ),
            "session": self._get_session_payload(session_id),
        }

    def _continue_last_answer(self, session_id: str):
        last_text = self._get_session_meta(session_id, "last_answer_text") or ""

        if not last_text.strip():
            return {
                "ok": True,
                "assistant_message": self._build_assistant_message(
                    "Nothing to continue yet."
                ),
                "session": self._get_session_payload(session_id),
            }

        prompt = f"""Continue this answer:

{last_text}

Rules:
- Do not restart
- Continue naturally
- Add useful depth
"""

        return self._execute_general_chat(
            user_text=prompt,
            session_id=session_id,
            attachments=[],
            decision={"route": self.ROUTE_GENERAL_CHAT},
        )

    def _detect_answer_depth(self, user_text: str) -> str:
        text = self._safe_str(user_text).lower().strip()

        deep_triggers = (
            "explain",
            "why",
            "how does",
            "how do",
            "break down",
            "walk me through",
            "teach me",
            "go deep",
            "details",
            "in detail",
            "full explanation",
        )

        short_triggers = (
            "quick",
            "short",
            "simple",
            "tldr",
            "brief",
            "one sentence",
            "summarize",
        )

        if any(trigger in text for trigger in short_triggers):
            return "short"

        if any(trigger in text for trigger in deep_triggers):
            return "deep"

        if len(text) > 180:
            return "medium"

        return "short"

    def _normalize_python_indentation(self, code: str) -> str:
        if not code:
            return code

        # 1. convert tabs → 4 spaces
        code = code.replace("\t", "    ")

        # 2. normalize line endings
        lines = code.splitlines()

        fixed_lines = []
        for line in lines:
            # strip trailing whitespace
            line = line.rstrip()

            # prevent weird mixed indentation
            leading_spaces = len(line) - len(line.lstrip(" "))
            if leading_spaces % 4 != 0:
                leading_spaces = (leading_spaces // 4) * 4
                line = (" " * leading_spaces) + line.lstrip()

            fixed_lines.append(line)

        return "\n".join(fixed_lines) + "\n"

    def _safe_write_file(self, file_path: str, new_code: str) -> dict:
        try:
            target = Path(file_path)

            if not target.exists():
                return {
                    "ok": False,
                    "error": "File not found",
                    "file": str(target),
                }

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = target.with_suffix(target.suffix + f".bak_{stamp}")
            shutil.copy2(target, backup_path)

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=target.suffix or ".tmp",
                mode="w",
                encoding="utf-8",
            ) as tmp:
                tmp.write(new_code)
                tmp_path = Path(tmp.name)

            if target.suffix.lower() == ".py":
                try:
                    py_compile.compile(str(tmp_path), doraise=True)
                except Exception as e:
                    return {
                        "ok": False,
                        "error": "Compile failed. Original file was not changed.",
                        "details": self._safe_str(e),
                        "backup": str(backup_path),
                        "temp_file": str(tmp_path),
                    }

            shutil.copy2(tmp_path, target)

            return {
                "ok": True,
                "message": "Safe write applied.",
                "file": str(target),
                "backup": str(backup_path),
            }

        except Exception as e:
            return {
                "ok": False,
                "error": self._safe_str(e),
            }

    def _validate_python_code(self, code: str) -> tuple[bool, str]:
        import os
        import py_compile
        import tempfile
        import traceback

        tmp_path = ""

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                delete=False,
                suffix=".py",
                encoding="utf-8",
            ) as tmp:
                tmp.write(code or "")
                tmp_path = tmp.name

            py_compile.compile(tmp_path, doraise=True)
            return True, ""

        except Exception:
            return False, traceback.format_exc().strip()

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _safe_dict(self, value) -> dict:
        return value if isinstance(value, dict) else {}

    def _safe_str(self, value) -> str:
        try:
            if value is None:
                return ""
            if isinstance(value, str):
                return value
            return str(value)
        except Exception:
            return ""

    def _store_pending_fix(self, session_id: str, file_path: str, fixed_code: str) -> bool:
        session_id = str(session_id or "").strip()
        file_path = str(file_path or "").strip()
        fixed_code = str(fixed_code or "")

        if not session_id or not file_path or not fixed_code.strip():
            return False

        try:
            session = self.session_service.get_session(session_id)
            if not isinstance(session, dict):
                return False

            working_state = session.get("working_state")
            if not isinstance(working_state, dict):
                working_state = {}

            working_state["pending_fix_file_path"] = file_path
            working_state["pending_fix_code"] = fixed_code
            session["working_state"] = working_state

            if hasattr(self.session_service, "update_working_state"):
                self.session_service.update_working_state(session_id, working_state)
                return True

            return False

        except Exception as e:
            exec_debug("STORE PENDING FIX ERROR:", e)
            return False

    def _auto_execute_request(
        self,
        user_text: str,
        session_id: str = "",
        attachments=None,
    ):
        text = str(user_text or "").lower().strip()
        session_id = str(session_id or "").strip()

        execution = {}

        try:
            if (
                hasattr(self, "execution_handler")
                and hasattr(self.execution_handler, "states")
            ):
                execution = self.execution_handler.states.get(session_id) or {}

            elif (
                hasattr(self, "execution_handler")
                and hasattr(self.execution_handler, "get_state")
            ):
                execution = self.execution_handler.get_state(session_id) or {}

        except Exception as e:
            exec_debug("EXECUTION STATE LOAD ERROR:", e)
            execution = {}

        status = str(execution.get("status") or "").lower()

        mission_status = ""

        try:
            session = self._get_session_payload(session_id)

            working_state = (
                session.get("working_state", {})
                if isinstance(session, dict)
                else {}
            )

            mission = (
                working_state.get("mission", {})
                if isinstance(working_state, dict)
                else {}
            )

            mission_status = str(mission.get("status") or "").lower()

        except Exception:
            mission_status = ""

        if text in {"test_fail", "test fail"}:
            action = "test_fail"

        elif text in {
            "next",
            "nex",
            "k",
            "kk",
            "continue",
            "continue on",
            "keep going",
            "go",
            "run next",
            "next step",
            "what next",
            "what now",
        }:
            if status in ("error", "failed") or mission_status in ("error", "failed"):
                action = "retry_failed"
            else:
                action = "run_step"

        elif text in {
            "retry",
            "retry_failed",
            "retry failed",
            "try again",
            "rerun failed",
        }:
            action = "retry_failed"

        elif text in {
            "run_all",
            "run all",
            "run it",
            "execute",
            "execute all",
            "auto",
            "auto mode",
            "autopilot",
        }:
            action = "run_all"

        elif text in {
            "run_step",
            "run step",
        }:
            action = "run_step"

        else:
            action = "run_all"

        try:
            exec_debug(
                "EXECUTION HANDLER ABOUT TO RUN:",
                action,
                session_id,
            )

            execution_state = (
                self._get_session_meta(
                    session_id,
                    "execution_state",
                )
                or self._get_working_state(session_id).get("execution_state")
                or {}
            )

            session = self.session_service.get_session(
                session_id
            )

            if not isinstance(
                session,
                dict,
            ):
                session = {}

            execution_state = (
                session.get(
                    "execution_state"
                )
                or session.get(
                    "active_execution"
                )
                or execution_state
                or {}
            )

            execution_state = self._process_execution(
                execution_state,
                session_id,
            )

            steps = execution_state.get("steps") or []

            current = int(
                execution_state.get("current_step", 0) or 0
            )

            total = len(steps)

            assistant_text = f"""Execution advanced.

Status: {execution_state.get("status")}

Progress: {current}/{total}

Current step:
{execution_state.get("current_step_title", "")}
""".strip()

            assistant_msg = self._build_assistant_message(
                text=assistant_text,
                attachments=[],
                meta={
                    "route": "execution",
                    "strategy": "execution_progress",
                    "execution_action": action,
                    "execution_state": execution_state,
                },
            )

            return {
                "ok": True,
                "assistant_message": assistant_msg,
                "session": self._get_session_payload(session_id),
                "debug": {
                    "route": "execution",
                    "strategy": "execution_progress",
                    "execution_action": action,
                    "execution_state": execution_state,
                },
            }

        except Exception as e:
            exec_debug("EXECUTION ROUTE ERROR:", e)

            assistant_msg = self._build_assistant_message(
                text=f"Execution route failed:\n\n{e}",
                attachments=[],
                meta={
                    "route": "execution_exception",
                    "execution_action": action,
                },
            )

            return {
                "ok": False,
                "assistant_message": assistant_msg,
                "error": str(e),
                "session": self._get_session_payload(session_id),
            }


    def _save_mission_state(self, session_id: str, mission: dict) -> None:
        if not session_id or not isinstance(mission, dict):
            return

        try:
            existing = self._get_session_payload(session_id)
            working_state = existing.get("working_state", {}) if isinstance(existing, dict) else {}

            if not isinstance(working_state, dict):
                working_state = {}

            has_real_execution = any([
                working_state.get("active_task"),
                working_state.get("current_file"),
                working_state.get("current_bug"),
                working_state.get("next_move"),
                working_state.get("checkpoint"),
            ])

            if has_real_execution:
                working_state["mission"] = mission

            else:
                working_state.pop("mission", None)
            if hasattr(self.sessions, "update_working_state"):
                self.sessions.update_working_state(session_id, working_state)

        except Exception as e:
            logger.error(f"[mission] failed to save mission state: {e}")

    def _resolve_mission_command(self, user_text: str, session_id: str = "") -> dict:
        text = self._safe_str(user_text).lower().strip()

        session = self._get_session_payload(session_id)
        working_state = (
            session.get("working_state", {})
            if isinstance(session, dict)
            else {}
        )

        if not isinstance(working_state, dict):
            working_state = {}

        mission = (
            working_state.get("mission", {})
            if isinstance(working_state, dict)
            else {}
        )

        if not isinstance(mission, dict):
            mission = {}

        execution_state = (
            self._load_execution_state(
                session_id
            )
            or {}
        )

        if not isinstance(
            execution_state,
            dict,
        ):
            execution_state = {}

        steps = (
            execution_state.get("steps")
            or []
        )

        current_index = int(
            execution_state.get(
                "current_index",
                0,
            )
            or 0
        )

        if not isinstance(
            steps,
            list,
        ):
            steps = []

        if current_index < 0:
            current_index = 0

        if current_index >= len(steps):
            current_index = len(steps)

        print(
            "EXECUTION DEBUG BEFORE COMPLETE CHECK =",
            {
                "command": user_text,
                "current_index": current_index,
                "steps_len": len(steps),
                "status": execution_state.get(
                    "status"
                ),
                "current_step": execution_state.get(
                    "current_step"
                ),
            },
        )

        print(
            "EXECUTION ABOUT TO PROCESS COMMAND",
            user_text,
        )

        if not steps:

            execution_state["status"] = (
                "idle"
            )

            execution_state["current_step"] = ""

            execution_state["progress"] = 0

            self._save_execution_state(
                session_id,
                execution_state,
            )

        working_state = (
            self._get_working_state(session_id)
            or {}
        )

        # SHORT_COMMAND_K_BRAIN_LOCK
        if text in {"next", "nex", "k", "kk", "continue", "resume"}:

            has_real_state = any(
                [
                    working_state.get("active_task"),
                    working_state.get("current_file"),
                    working_state.get("current_bug"),
                    working_state.get("next_move"),
                    working_state.get("checkpoint"),
                ]
            )

            has_real_execution = any(
                [
                    bool(execution_state.get("steps")),
                    execution_state.get("current_step"),
                    self._safe_str(
                        execution_state.get("status")
                    ).lower().strip()
                    == "running",
                ]
            )

            if not has_real_state and not has_real_execution:
                message = (
                    "No active work to resume."
                    if text == "resume"
                    else "No active execution to continue. Start one with: auto-plan <goal>"
                )

                return {
                    "ok": True,
                    "is_mission": True,
                    "type": "empty_next_guard",
                    "next_action": "none",
                    "mission": {},
                    "assistant_message": self._build_assistant_message(
                        message
                    ),
                    "execution": execution_state,
                }

            return {
                "ok": True,
                "is_mission": True,
                "type": "continue",
                "mission": mission,
                "next_action": (
                    "retry_failed"
                    if self._safe_str(
                        mission.get("status")
                    ).lower().strip()
                    in {"error", "failed"}
                    else mission.get("next_action") or "run_step"
                ),
                "execution": execution_state,
            }

        if text in {"run it", "run", "execute", "go"}:
            return {
                "ok": True,
                "is_mission": True,
                "type": "execute",
                "mission": mission,
                "next_action": mission.get("next_action") or "run_execution",
                "execution": execution_state,
            }

        if text in {"what next", "what now"}:
            return {
                "ok": True,
                "is_mission": True,
                "type": "inspect",
                "mission": mission,
                "next_action": mission.get("next_action") or "inspect_state",
                "execution": execution_state,
            }

        return {
            "ok": True,
            "is_mission": False,
            "type": "",
            "mission": mission,
            "next_action": "",
            "execution": execution_state,
        }

    def _handle_mission_command_result(
        self,
        mission_command=None,
        session_id: str = "",
    ):
        if not isinstance(mission_command, dict):
            return None

        mission_type = self._safe_str(
            mission_command.get("type")
        ).lower().strip()

        if mission_type == "empty_next_guard":
            return {
                "ok": True,
                "assistant_message": (
                    mission_command.get("assistant_message")
                    or self._build_assistant_message(
                        "No active execution to continue."
                    )
                ),
                "execution": mission_command.get("execution") or {},
                "session": self._get_session_payload(session_id),
                "debug": {
                    "route_taken": "empty_next_guard",
                },
            }

        if mission_command.get("is_mission") is not True:
            return None

        next_action = self._safe_str(
            mission_command.get("next_action")
        ).lower().strip()

        execution_state = mission_command.get("execution") or {}

        if mission_type in {"continue", "execute"}:

            persisted_execution_state = (
                self._load_execution_state(
                    session_id
                )
                or {}
            )

            selected_execution_state = (
                persisted_execution_state
                if persisted_execution_state.get(
                    "steps"
                )
                else execution_state
            )

            selected_execution_state[
                "_execution_dispatch_handled"
            ] = True

            return self._process_execution_command(
                command=next_action or "run_step",
                session_id=session_id,
                execution_state=selected_execution_state,
            )

        if mission_type == "inspect":
            mission = mission_command.get("mission") or {}

            return {
                "ok": True,
                "assistant_message": self._build_assistant_message(
                    mission.get("recommended_next_move")
                    or "Inspect current mission state."
                ),
                "execution": execution_state,
                "session": self._get_session_payload(session_id),
                "debug": {
                    "route_taken": "mission_inspect",
                },
            }

        return None

    def _load_execution_state(
        self,
        session_id="",
    ):
        session_id = self._safe_str(
            session_id
        ).strip()

        if not session_id:
            return {}

        cache = getattr(
            self,
            "_execution_state_cache",
            {},
        )

        fallback_state = (
            cache.get(session_id)
            or {}
        )

        return (
            fallback_state
            if isinstance(fallback_state, dict)
            else {}
        )

    def _save_execution_state(
        self,
        session_id="",
        execution_state=None,
    ):
        session_id = self._safe_str(session_id).strip()

        if not session_id:
            return {}

        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        execution_state["_execution_processing"] = False
        execution_state["lock"] = False

        working_state = (
            self._get_working_state(session_id)
            or {}
        )

        working_state["execution_state"] = execution_state

        self._update_working_state(
            session_id,
            working_state,
        )


        self._execution_state_cache = getattr(
            self,
            "_execution_state_cache",
            {},
        )

        self._execution_state_cache[
            session_id
        ] = execution_state

        self._set_session_meta(
            session_id,
            "execution_state",
            execution_state,
        )

        self._set_session_meta(
            session_id,
            "active_execution",
            execution_state,
        )

        sessions = self.sessions.load()

        index = self.sessions._find(
            sessions,
            session_id,
        )

        if index is not None:
            sessions[index]["execution_state"] = execution_state

            sessions[index]["active_execution"] = (
                execution_state
                if (
                    isinstance(execution_state, dict)
                    and execution_state.get("steps")
                    and self._safe_str(
                        execution_state.get("status")
                    ).lower()
                    not in {
                        "complete",
                        "completed",
                        "done",
                        "cancelled",
                        "canceled",
                    }
                )
                else {}
            )

            meta = sessions[index].get("meta")

            if not isinstance(meta, dict):
                meta = {}

            meta["execution_state"] = execution_state
            meta["active_execution"] = execution_state

            sessions[index]["meta"] = meta

            self.sessions.save(sessions)

        return execution_state

    def _get_session_meta(self, session_id: str, key: str = "", default=None):
        session_id = self._safe_str(session_id).strip()
        key = self._safe_str(key).strip()

        if not session_id or not key:
            return default

        try:
            session = self._get_session_payload(session_id)

            if not isinstance(session, dict):
                return default

            meta = session.get("meta")

            if not isinstance(meta, dict):
                meta = {}

            return meta.get(key, default)

        except Exception as e:
            exec_debug("GET SESSION META FAILED:", e)
            return default

    def _set_session_meta(self, session_id: str, key: str, value) -> bool:
        session_id = self._safe_str(session_id).strip()
        key = self._safe_str(key).strip()

        if not session_id or not key:
            return False

        try:
            sessions = self.sessions._load_sessions()
            index = self.sessions._find(sessions, session_id)

            if index is None:
                return False

            meta = sessions[index].get("meta")

            if not isinstance(meta, dict):
                meta = {}

            meta[key] = value
            sessions[index]["meta"] = meta

            self.sessions._save_sessions(
                sessions,
                self.sessions.get_active_session_id(),
            )

            return True

        except Exception as e:
            exec_debug("SET SESSION META FAILED:", e)
            return False

    def _maybe_write_memory(
        self,
        decision=None,
        user_text: str = "",
        session_id: str = "",
    ) -> bool:
        decision = decision if isinstance(decision, dict) else {}

        if decision.get("save_memory") is False:
            return False

        text = self._safe_str(user_text).strip()
        if not text:
            return False

        if not self._should_save_memory_text(text):
            return False

        payload = {
            "text": text,
            "kind": "user_fact",
            "session_id": session_id,
        }

        for method_name in (
            "add_memory",
            "append_memory",
            "save_memory",
            "remember",
            "add",
        ):
            method = getattr(self.memory, method_name, None)
            if callable(method):
                method(payload)
                return True

        exec_debug("MEMORY WRITE FAILED: no supported memory write method")
        return False

    def _get_memory_list(self):
        try:
            if not hasattr(self, "memory") or not self.memory:
                return []

            if hasattr(self.memory, "list_memories"):
                result = self.memory.list_memories()
                if isinstance(result, list):
                    return result

            if hasattr(self.memory, "_read_store"):
                data = self.memory._read_store()
                if isinstance(data, dict):
                    return data.get("memory", [])

            return []

        except Exception:
            return []

    def _get_sessions_list(self) -> list:
        try:
            data = self._call_first(
                self.sessions,
                ["list_sessions", "get_sessions", "list", "all_sessions"],
            )

            if isinstance(data, dict) and isinstance(data.get("sessions"), list):
                return data.get("sessions")

            if isinstance(data, dict) and isinstance(data.get("items"), list):
                return data.get("items")

            if isinstance(data, list):
                return data

            return []

        except Exception as e:
            exec_debug("GET SESSIONS LIST FAILED:", e)
            return []

    def _get_artifacts_list(self) -> list:
        try:
            data = self._call_first(
                self.artifacts,
                ["list_artifacts", "get_artifacts", "list", "all_artifacts"],
            )

            if isinstance(data, dict) and isinstance(data.get("artifacts"), list):
                return data.get("artifacts")

            if isinstance(data, list):
                return data

            return []

        except Exception as e:
            exec_debug("GET ARTIFACTS LIST FAILED:", e)
            return []

    def _get_session_payload(self, session_id: str = "") -> dict:
        sid = self._ensure_session_id(session_id)

        payload = {}

        if hasattr(self.sessions, "get_session"):
            found = self.sessions.get_session(sid)
            if isinstance(found, dict):
                payload = found

        if not payload and hasattr(self.sessions, "get"):
            found = self.sessions.get(sid)
            if isinstance(found, dict):
                payload = found

        if not payload:
            payload = {
                "id": sid,
                "messages": [],
                "meta": {},
            }

        meta = payload.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            payload["meta"] = meta

        live_execution = (
            payload.get(
                "active_execution"
            )
            or payload.get(
                "execution_state"
            )
            or {}
        )

        # HARD BLOCK RESURRECTION FROM PAYLOAD

        payload["active_execution"] = (
            live_execution
        )

        payload["execution_state"] = (
            live_execution
        )
        # =========================
        # INVALID EXECUTION SANITIZER
        # =========================

        goal_text = self._safe_str(
            live_execution.get("goal")
        ).lower().strip()

        invalid_goal = (
            "respond normally" in goal_text
            or (
                isinstance(live_execution.get("goal"), dict)
                and self._safe_str(
                    live_execution["goal"].get("goal")
                ).lower().strip() == "respond normally"
            )
        )

        invalid_general_execution = (
            invalid_goal
            or self._safe_str(
                live_execution.get("original_user_text")
            ).lower().strip() == "run_step"
        )

        if invalid_general_execution:

            print(
                "SANITIZER CLEARED INVALID EXECUTION"
            )

            live_execution = {}

            meta["active_execution"] = {}
            meta["execution_state"] = {}

        execution_status = self._safe_str(
            live_execution.get("status")
        ).lower()

        execution_complete = (
            execution_status in {
                "complete",
                "completed",
                "done",
                "cancelled",
                "canceled",
            }
            or live_execution.get("complete") is True
        )

        if execution_complete:
            live_execution = {}

        payload["active_execution"] = live_execution
        payload["execution_state"] = live_execution

        return payload

    def _ensure_session_id(self, session_id: str = "") -> str:
        sid = self._safe_str(session_id).strip()

        if (
            sid.startswith("session_")
            and " " not in sid
            and len(sid) >= 20
        ):
            return sid

        created = None

        if hasattr(self.sessions, "create_session"):
            created = self.sessions.create_session()

        elif hasattr(self.sessions, "new_session"):
            created = self.sessions.new_session()

        if isinstance(created, dict):

            created_id = self._safe_str(
                created.get("id")
            ).strip()

            if (
                created_id.startswith("session_")
                and " " not in created_id
                and len(created_id) >= 20
            ):
                return created_id

        import uuid

        return f"session_{uuid.uuid4().hex}"

    def _analyze_execution_state(self, execution_state=None, last_error: str = "") -> dict:
        execution_state = self._safe_dict(execution_state)
        last_error = self._safe_str(last_error).strip()

        status = self._safe_str(execution_state.get("status")).lower()
        current_step = execution_state.get("current_step")
        steps = execution_state.get("steps") or []
        history = execution_state.get("history") or []

        failed = status in {"error", "failed", "failure"}

        if last_error:
            lowered_error = last_error.lower()

            if "syntaxerror" in lowered_error or "indentationerror" in lowered_error or "taberror" in lowered_error:
                return {
                    "status": "failed",
                    "problem_type": "python_compile_error",
                    "next_action": "fix_code_then_retry",
                    "message": "Python compile error detected. Fix the file, compile it, then retry execution.",
                    "needs_file_fix": True,
                }

            if "attributeerror" in lowered_error:
                return {
                    "status": "failed",
                    "problem_type": "missing_method_or_bad_object",
                    "next_action": "inspect_missing_attribute",
                    "message": "Missing attribute detected. Add the missing method or fix the object being used.",
                    "needs_file_fix": True,
                }

            if "modulenotfounderror" in lowered_error or "importerror" in lowered_error:
                return {
                    "status": "failed",
                    "problem_type": "import_error",
                    "next_action": "fix_import_or_dependency",
                    "message": "Import problem detected. Fix the import path or install the missing dependency.",
                    "needs_file_fix": True,
                }

        if failed:
            return {
                "status": "failed",
                "problem_type": "execution_failed",
                "next_action": "retry_failed",
                "message": "Execution failed. Inspect the error and retry after fixing.",
                "needs_file_fix": True,
            }

        if status in {"complete", "completed", "done"}:
            return {
                "status": "complete",
                "problem_type": "",
                "next_action": "complete",
                "message": "Execution is complete.",
                "needs_file_fix": False,
            }

        if steps and isinstance(current_step, int) and current_step >= len(steps):
            return {
                "status": "complete",
                "problem_type": "",
                "next_action": "complete",
                "message": "Execution is complete.",
                "needs_file_fix": False,
            }

        if steps and isinstance(current_step, int) and current_step < len(steps):
            return {
                "status": "running",
                "problem_type": "",
                "next_action": "run_step",
                "message": "Execution can continue to the next step.",
                "needs_file_fix": False,
            }

        return {
            "status": status or "unknown",
            "problem_type": "",
            "next_action": "inspect_state",
            "message": "Execution state needs inspection.",
            "needs_file_fix": False,
        }

    def _reflect_on_execution_state(
        self,
        session_id: str = "",
        execution_state=None,
        user_text: str = "",
        last_error: str = "",
    ) -> dict:
        session_id = self._safe_str(session_id).strip()
        user_text = self._safe_str(user_text).strip()
        last_error = self._safe_str(last_error).strip()

        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        status = self._safe_str(
            execution_state.get("status")
        ).lower().strip()

        steps = execution_state.get("steps") or []
        current_index = int(
            execution_state.get("current_index")
            or 0
        )

        failed_steps = [
            step
            for step in steps
            if isinstance(step, dict)
            and self._safe_str(step.get("status")).lower().strip()
            in {"failed", "error"}
        ]

        reflection = {
            "status": status,
            "has_error": bool(last_error),
            "failed_step_count": len(failed_steps),
            "current_index": current_index,
            "risk": "low",
            "recommended_action": "continue",
            "reason": "Execution appears stable.",
        }

        if status in {"failed", "error"} or failed_steps:
            reflection["risk"] = "high"
            reflection["recommended_action"] = "recover"
            reflection["reason"] = (
                "Execution failure detected. Inspect failed step before retry."
            )

        elif status in {"complete", "completed"}:
            reflection["risk"] = "low"
            reflection["recommended_action"] = "stop"
            reflection["reason"] = (
                "Execution is already complete. Do not resurrect stale state."
            )

        elif not steps and user_text.lower() in {"next", "continue", "resume"}:
            reflection["risk"] = "medium"
            reflection["recommended_action"] = "empty_guard"
            reflection["reason"] = (
                "Continuation requested without active execution steps."
            )

        self._update_working_state(
            session_id,
            {
                "last_reflection_action": reflection.get(
                    "recommended_action"
                ),
                "last_reflection_reason": reflection.get("reason"),
                "last_reflection_risk": reflection.get("risk"),
            },
        )

        return reflection
    def _choose_execution_recovery_strategy(self, session_id: str, command: str, status: str, error_text: str = ""):
        session_id = self._safe_str(session_id).strip()
        command = self._safe_str(command).strip().lower()
        status = self._safe_str(status).strip().lower()
        error_text = self._safe_str(error_text).strip()

        working_state = self._get_working_state(session_id) or {}

        reflection = self._reflect_on_execution_state(
            session_id=session_id,
            execution_state=(
                self._get_session_meta(
                    session_id,
                    "execution_state",
                )
                or {}
            ),
            user_text=command,
            last_error=error_text,
        )

        failure_count = int(
            working_state.get("execution_failure_count")
            or 0
        )

        score = int(
            working_state.get("execution_reward_score")
            or 0
        )

        if reflection.get("recommended_action") == "stop":
            strategy = "stop_completed_execution"
            next_move = "await_new_mission"

        elif reflection.get("recommended_action") == "empty_guard":
            strategy = "block_empty_continuation"
            next_move = "await_new_mission"

        elif reflection.get("recommended_action") == "recover":
            strategy = "inspect_failed_execution"
            next_move = "inspect_error_context"

        elif failure_count <= 0:
            strategy = "retry_same_step"
            next_move = "retry_failed"

        elif failure_count == 1:
            strategy = "inspect_error_context"
            next_move = "auto_fix_failure"

        elif failure_count == 2:
            strategy = "use_smaller_patch_scope"
            next_move = "function_scoped_auto_fix"

        else:
            strategy = "stop_and_request_traceback"
            next_move = "request_traceback"

        if score <= -15 and strategy not in {
            "stop_completed_execution",
            "block_empty_continuation",
        }:
            strategy = "stop_and_change_plan"
            next_move = "manual_review_required"

        self._update_working_state(
            session_id,
            {
                "execution_recovery_strategy": strategy,
                "next_move": next_move,
                "last_strategy_command": command,
                "last_strategy_status": status,
                "last_strategy_error": error_text,
                "last_reflection_action": reflection.get(
                    "recommended_action"
                ),
                "last_reflection_reason": reflection.get("reason"),
                "last_reflection_risk": reflection.get("risk"),
            },
        )

        return strategy

    def _record_execution_reward(self, session_id: str, command: str, status: str, error_text: str = ""):
        session_id = self._safe_str(session_id).strip()
        command = self._safe_str(command).strip().lower()
        status = self._safe_str(status).strip().lower()
        error_text = self._safe_str(error_text).strip()

        reward = 0

        if status in {"success", "complete", "completed", "passed"}:
            reward += 10

        elif status in {"failed", "error"}:
            reward -= 5

        elif status in {"cancelled", "canceled"}:
            reward -= 1

        working_state = self._get_working_state(session_id) or {}

        current_score = int(
            working_state.get("execution_reward_score")
            or 0
        )

        new_score = current_score + reward

        self._update_working_state(
            session_id,
            {
                "execution_reward_score": new_score,
                "last_execution_reward": reward,
                "last_reward_command": command,
                "last_reward_status": status,
                "last_reward_error": error_text,
            },
        )

        return reward

    def _process_execution_command(
        self,
        command="",
        session_id="",
        execution_state=None,
    ):

        persisted_execution_state = {}

        execution_state = (
            execution_state
            if isinstance(
                execution_state,
                dict,
            )
            else {}
        )

        command = self._safe_str(
            command
        ).strip().lower()

        intelligence_intent = self._safe_str(
            execution_state.get("intent")
            or execution_state.get("mode")
            or ""
        ).strip().lower()

        if intelligence_intent in {
            "resume_execution",
            "continue_waiting_execution",
        }:
            command = "run_step"

        elif intelligence_intent == "run_all_steps":
            command = "run_all"

        elif intelligence_intent == "retry_failed_step":
            command = "retry_failed"

        elif intelligence_intent == "cancel_execution":
            command = "cancel"

        working_state = (
            self._get_working_state(session_id)
            or {}
        )

        persisted_execution_state = (
            self._load_execution_state(
                session_id
            )
            or {}
        )

        persisted_has_state = bool(
            persisted_execution_state.get(
                "steps"
            )
        )

        incoming_has_state = bool(
            execution_state.get(
                "steps"
            )
        )

        if persisted_has_state:

            execution_state = (
                persisted_execution_state
            )

        elif incoming_has_state:

            execution_state = (
                execution_state
            )

        else:

            execution_state = {}

        steps = (
            execution_state.get("steps")
            or []
        )

        current_index = int(
            execution_state.get(
                "current_index",
                0,
            )
            or 0
        )

        if not isinstance(
            steps,
            list,
        ):
            steps = []

        if current_index < 0:
            current_index = 0

        if current_index >= len(steps):
            current_index = len(steps)

        print(
            "EXECUTION DEBUG BEFORE COMPLETE CHECK =",
            {
                "command": command,
                "current_index": current_index,
                "steps_len": len(steps),
                "status": execution_state.get(
                    "status"
                ),
                "current_step": execution_state.get(
                    "current_step"
                ),
            },
        )

        # =========================
        # NEXT AFTER COMPLETION
        # =========================

        if command in {
            "next",
            "continue",
            "keep going",
            "run next",
        }:

            command = "run_step"

            current_index = int(
                execution_state.get(
                    "current_index",
                    0,
                )
                or 0
            )

            execution_state["current_index"] = (
                current_index
            )

            execution_state["status"] = (
                "running"
            )

            execution_state["waiting"] = False

            execution_state["complete"] = False

            self._save_execution_state(
                session_id,
                execution_state,
            )

        # =========================
        # RUN STEP
        # =========================
        if command in {
            "run_step",
            "run step",
        }:

            if not steps:

                persisted_execution = (
                    self._load_execution_state(
                        session_id
                    )
                    or {}
                )

                if (
                    isinstance(
                        persisted_execution,
                        dict,
                    )
                    and persisted_execution.get(
                        "steps"
                    )
                ):
                    execution_state = (
                        persisted_execution
                    )

                    current_index = int(
                        execution_state.get(
                            "current_index",
                            0,
                        )
                        or 0
                    )

                    steps = (
                        execution_state.get(
                            "steps",
                            [],
                        )
                    )

                    current_index = int(
                        execution_state.get(
                            "current_index",
                            0,
                        )
                    )

            if not steps:
                return {
                    "ok": False,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "No active execution plan. "
                            "Start one with: auto-plan <goal>"
                        ),
                    },
                    "execution": execution_state,
                }

            if current_index >= len(steps):
                execution_state["status"] = "complete"
                execution_state["next_moves"] = []
                execution_state["current_index"] = len(steps)
                execution_state["lock"] = False
                execution_state["waiting"] = False
                execution_state["complete"] = True
                execution_state["current_step"] = ""
                execution_state["current_step_title"] = ""

            while (
                current_index < len(steps)
                and self._safe_str(
                    steps[current_index].get(
                        "status"
                    )
                ).lower().strip()
                in {
                    "completed",
                    "done",
                }
            ):
                current_index += 1

            execution_state["current_index"] = (
                current_index
            )

            if current_index >= len(steps):

                execution_state["status"] = (
                    "complete"
                )

                execution_state["next_moves"] = []

                execution_state["waiting"] = False

                execution_state["complete"] = True

                execution_state["current_step"] = ""

                execution_state[
                    "current_step_title"
                ] = ""

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "All execution steps completed."
                        ),
                    },
                    "execution": execution_state,
                }

            refreshed_execution = (
                self._load_execution_state(
                    session_id
                )
                or execution_state
            )

            refreshed_steps = (
                refreshed_execution.get(
                    "steps"
                )
                or []
            )

            if (
                not isinstance(
                    refreshed_steps,
                    list,
                )
                or current_index >= len(
                    refreshed_steps
                )
            ):
                refreshed_steps = steps

            step = refreshed_steps[
                current_index
            ]

            execution_state = (
                refreshed_execution
            )

            steps = refreshed_steps
            execution_state["current_index"] = current_index

            if current_index >= len(steps):
                execution_state["status"] = "complete"
                execution_state["next_moves"] = []
                execution_state["waiting"] = False
                execution_state["complete"] = True
                execution_state["current_step"] = ""
                execution_state["current_step_title"] = ""

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                return {

                        "ok": True,
                        "assistant_message": {
                            "role": "assistant",
                            "text": "All execution steps completed.",
                        },
                        "execution": execution_state,
                    }

            refreshed_execution = (
                self._load_execution_state(
                    session_id
                )
                or execution_state
            )

            refreshed_steps = (
                refreshed_execution.get(
                    "steps"
                )
                or []
            )

            if (
                not isinstance(
                    refreshed_steps,
                    list,
                )
                or current_index >= len(
                    refreshed_steps
                )
            ):
                refreshed_steps = steps

            original_step = (
                steps[current_index]
                if current_index < len(steps)
                and isinstance(steps[current_index], dict)
                else {}
            )

            refreshed_step = (
                refreshed_steps[current_index]
                if current_index < len(refreshed_steps)
                and isinstance(refreshed_steps[current_index], dict)
                else {}
            )

            step = {
                **original_step,
                **refreshed_step,
            }

            execution_state = (
                refreshed_execution
            )
            steps = refreshed_steps

            step["status"] = "running"

            execution_state["status"] = "running"
            execution_state["current_step"] = (
                step.get("title")
                or ""
            )
            execution_state["current_step_title"] = (
                step.get("title")
                or ""
            )

            result = self._execute_step_logic(
                session_id=session_id,
                step=step,
            )


            step["status"] = "completed"

            if result:
                step["result"] = result

            execution_state["steps"][
                current_index
            ] = dict(step)

            steps = execution_state["steps"]

            result = step.get(
                "result",
                "",
            )

            execution_state["history"] = (
                execution_state.get("history")
                or []
            )

            execution_state["history"].append(
                f"completed: {step.get('title')}"
            )

            execution_state["current_index"] = (
                current_index + 1
            )

            execution_state["current_step_index"] = (
                current_index + 1
            )

            execution_state["progress"] = (
                current_index + 1
            )

            execution_state["waiting"] = True

            execution_state["_execution_processing"] = False

            next_index = execution_state.get(
                "current_index",
                current_index + 1,
            )

            if next_index < len(steps):
                next_step = steps[next_index]

                execution_state["current_step"] = (
                    next_step.get("title")
                    or ""
                )

                execution_state["current_step_title"] = (
                    next_step.get("title")
                    or ""
                )
            execution_state["_execution_processing"] = False

            next_index = execution_state["current_index"]

            if next_index < len(steps):
                next_step = steps[next_index]

                execution_state["current_step"] = (
                    next_step.get("title")
                    or ""
                )

                execution_state["current_step_title"] = (
                    next_step.get("title")
                    or ""
                )

            if (
                execution_state["current_index"]
                >= len(steps)
            ):
                execution_state["status"] = (
                    "complete"
                )

                execution_state["next_moves"] = []

                execution_state["waiting"] = (
                    False
                )

                execution_state["complete"] = (
                    True
                )

                execution_state["current_step"] = ""

                execution_state[
                    "current_step_title"
                ] = ""

            self._save_execution_state(
                session_id,
                execution_state,
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": (
                        f"Completed step: "
                        f"{step.get('title')}"
                    ),
                },
                "execution": execution_state,
                "step_output": result,
            }

        # =========================
        # RUN ALL
        # =========================
        if command == "run_all":

            outputs = []
            loop_guard = 0

            while True:

                loop_guard += 1
                if loop_guard > 100:
                    return {
                        "ok": False,
                        "assistant_message": {
                            "role": "assistant",
                            "text": "Execution stopped because the run_all loop guard was reached.",
                        },
                        "execution": execution_state,
                    }

                current_index = int(
                    execution_state.get("current_index", 0)
                    or 0
                )

                if current_index >= len(steps):
                    execution_state["status"] = "complete"
                    execution_state["next_moves"] = []
                    execution_state["waiting"] = False
                    execution_state["complete"] = True
                    execution_state["current_step"] = ""
                    execution_state["current_step_title"] = ""
                    execution_state["_execution_processing"] = False
                    break

                step = steps[current_index]

                step["status"] = "running"

                execution_state["steps"][
                    current_index
                ] = dict(step)

                execution_state["status"] = "running"
                execution_state["current_step"] = (
                    step.get("title")
                    or ""
                )
                execution_state["current_step_title"] = (
                    step.get("title")
                    or ""
                )
                execution_state["_execution_processing"] = False

                self._save_active_execution(
                    session_id,
                    execution_state,
                )

                result = self._execute_step_logic(
                    session_id=session_id,
                    step=step,
                )

                print(
                    "AFTER EXECUTE STEP OBJECT =",
                    step,
                )

                print(
                    "AFTER EXECUTE EXECUTION STEPS BEFORE WRITEBACK =",
                    execution_state.get("steps"),
                )

                step["status"] = "completed"

                if result:
                    step["result"] = result

                execution_state["steps"][
                    current_index
                ] = dict(step)

                steps = execution_state["steps"]

                print(
                    "AFTER EXECUTE EXECUTION STEPS AFTER WRITEBACK =",
                    execution_state.get("steps"),
                )

                execution_state["history"] = (
                    execution_state.get("history")
                    or []
                )

                step_title = self._safe_str(
                    step.get("title")
                )

                step_action = self._safe_str(
                    step.get("action")
                ).lower()

                target_file = self._safe_str(
                    step.get("target_file")
                )

                python_result = None

                if (
                    step_action == "implement"
                    and target_file
                ):

                    Path(target_file).parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    Path(target_file).write_text(
                        '''
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


if __name__ == "__main__":
    print("Calculator app created.")
    print("2 + 3 =", add(2, 3))
'''.strip()
                        + "\n",
                        encoding="utf-8",
                    )

                    step["result"] = (
                        f"Created file: {target_file}"
                    )

                    step["error"] = None

                elif (
                    step_action in {
                        "test",
                        "run",
                        "execute",
                    }
                    and target_file
                    and hasattr(self, "python_runner")
                ):

                    python_result = (
                        self.python_runner.run_file(
                            target_file
                        )
                    )

                    step["result"] = (
                        python_result.get("stdout")
                        or python_result.get("stderr")
                        or python_result.get("error")
                        or "python executed"
                    )

                    step["error"] = (
                        None
                        if python_result.get("ok")
                        else step["result"]
                    )

                else:

                    step["result"] = (
                        "step executed"
                    )

                    step["error"] = None

                execution_state["history"].append(
                    f"completed: {step_title}"
                )

                execution_state["current_index"] = (
                    current_index + 1
                )

                execution_state["progress"] = (
                    current_index + 1
                )

                outputs.append(
                    f"Completed step: {step_title}"
                )

                if execution_state["current_index"] >= len(steps):
                    execution_state["status"] = "complete"
                    execution_state["next_moves"] = []
                    execution_state["waiting"] = False
                    execution_state["complete"] = True
                    execution_state["current_step"] = ""
                    execution_state["current_step_title"] = ""
                    break


            self._save_active_execution(
                session_id,
                execution_state,
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": "\n".join(outputs),
                },
                "execution": execution_state,
            }

        # =========================
        # RETRY FAILED
        # =========================
        if command == "retry_failed":

            execution_state["failure_count"] = int(
                execution_state.get("failure_count")
                or 0
            ) + 1

            failed_index = None

            for idx, step in enumerate(steps):
                if step.get("status") == "failed":
                    failed_index = idx
                    break

            if failed_index is None:
                return {
                    "ok": False,
                    "assistant_message": {
                        "role": "assistant",
                        "text": "No failed execution step found to retry.",
                    },
                    "execution": execution_state,
                }

            execution_state["current_index"] = failed_index

            failure_count = int(
                execution_state.get("failure_count")
                or 0
            )

            if failure_count == 1:
                execution_state["retry_strategy"] = "retry_step"

            elif failure_count == 2:
                execution_state["retry_strategy"] = (
                    "retry_with_smaller_scope"
                )

            elif failure_count == 3:
                execution_state["retry_strategy"] = (
                    "retry_with_file_scope"
                )

            else:
                execution_state["retry_strategy"] = "change_strategy"

            self._save_execution_state(
                session_id,
                execution_state,
            )

            return self._process_execution_command(
                command="run_step",
                session_id=session_id,
                execution_state=execution_state,
            )

        # =========================
        # CANCEL
        # =========================
        if command == "cancel":

            execution_state["status"] = "cancelled"
            execution_state["waiting"] = False
            execution_state["lock"] = False
            execution_state["next_moves"] = []
            execution_state["current_step"] = ""
            execution_state["current_step_title"] = ""

            self._save_execution_state(
                session_id,
                execution_state,
            )

            self._save_execution_state(
                session_id,
                {},
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": "Execution cancelled.",
                },
                "execution": execution_state,
            }

        # =========================
        # EXECUTION COMPLETE FALLBACK
        # =========================
        if (
            False
            and steps
            and current_index >= len(steps)
        ):

            execution_state["status"] = "complete"
            execution_state["next_moves"] = []
            execution_state["current_index"] = len(steps)
            execution_state["lock"] = False
            execution_state["waiting"] = False
            execution_state["complete"] = True
            execution_state["current_step"] = ""
            execution_state["current_step_title"] = ""

            self._save_execution_state(
                session_id,
                execution_state,
            )

            self._save_execution_state(
                session_id,
                {},
            )

            return {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": (
                        "Execution complete. "
                        "Type 'next' to restart "
                        "or 'auto-plan <task>'."
                    ),
                },
                "execution": execution_state,
            }

        return {
            "ok": False,
            "assistant_message": {
                "role": "assistant",
                "text": (
                    f"Unknown execution command: "
                    f"{command}"
                ),
            },
            "execution": execution_state,
        }

    def _build_brain_state(self, execution_state, working_state, session, user_text):

        memory = self._get_session_meta(session, "memory") or []

        return {
            "input": user_text,

            "execution": execution_state or {},
            "working": working_state or {},
            "session_id": session,

            "memory": memory[-10:],
            "memory_size": len(memory),

            "signals": {
                "has_memory": len(memory) > 0,
                "is_continuation": user_text.lower() in {
                    "next", "continue", "keep going", "run next",
                    "what next", "what now"
                },
                "is_failure_state": (execution_state or {}).get("status") == "failed",
            },

            "tool_state": {
                "strategy": "default",
                "available_tools": [
                    "run_step",
                    "run_all",
                    "retry_failed",
                    "apply_auto_fix"
                ]
            }
        }

    def _select_strategy(self, brain_state):

        text = (brain_state.get("input") or "").lower()

        if brain_state["signals"]["is_failure_state"]:
            return "repair"

        if "build" in text:
            return "build"

        if brain_state["signals"]["is_continuation"]:
            return "continue"

        return "default"

    def _agent_context(self, brain_state):

        return {
            "goal": brain_state.get("goal_state", {}).get("active_goal"),
            "step": brain_state.get("current_step"),
            "status": brain_state.get("status"),
            "decision": brain_state.get("decision"),
        }

    def _decide_brain_action(self, brain_state):

        strategy = self._select_strategy(brain_state)
        text = brain_state.get("input", "").lower()

        # -------------------------
        # STRATEGY LAYER (PRIMARY)
        # -------------------------
        if strategy == "repair":
            return "retry_failed"

        if strategy == "build":
            return "run_all"

        if strategy == "continue":
            return "run_step"

        # -------------------------
        # DIRECT COMMAND OVERRIDES
        # -------------------------
        if text in {"stop", "cancel"}:
            return "cancel"

        if text in {"apply_auto_fix", "autofix"}:
            return "apply_auto_fix"

        return "chat"


    def _reflect(self, brain_state, execution_result):

        reflection = {
            "action": brain_state.get("decision"),
            "input": brain_state.get("input"),
            "status": execution_result.get("status"),
            "success": execution_result.get("status") == "complete",
            "failed": execution_result.get("status") == "failed",
            "lesson_weight": 0
        }

        # -------------------------
        # LEARNING SIGNALS
        # -------------------------
        if reflection["success"]:
            reflection["lesson_weight"] = 1

        if reflection["failed"]:
            reflection["lesson_weight"] = -1

        # -------------------------
        # PERSIST MEMORY
        # -------------------------
        session = brain_state.get("session_id")
        memory = self._get_session_meta(session, "memory") or []

        memory.append(reflection)

        # keep memory bounded
        memory = memory[-200:]

        self._set_session_meta(session, "memory", memory)

        return reflection

    def _get_relevant_memory(self, memory, action):

        relevant = []

        for m in memory[-50:]:
            if m.get("action") == action:
                relevant.append(m)

        return relevant[-10:]

    def _mutate_plan(self, brain_state, execution_state):

        plan = execution_state.get("plan") or []
        status = execution_state.get("status")
        current_index = execution_state.get("current_index", 0)

        # -------------------------
        # FAILURE RECOVERY MUTATION
        # -------------------------
        if status == "failed":

            # insert recovery step right after failed point
            plan.insert(current_index + 1, {
                "step": "auto-retry failed step with correction"
            })

        # -------------------------
        # COMPLETION EXPANSION
        # -------------------------
        if status == "complete" and current_index >= len(plan):
            return plan

        return plan

    def _memory_score(self, memory, action):

        score = 0

        for m in memory[-20:]:
            if m.get("action") == action:
                score += m.get("lesson_weight", 0)

        return score

    def _build_plan(self, brain_state):

        text = brain_state["input"].lower()

        existing_plan = brain_state.get("plan") or []

        if "login" in text:
            return [
                {"step": "design login flow"},
                {"step": "implement authentication"},
                {"step": "test login system"}
            ]

        if "build" in text:
            return [
                {"step": "design structure"},
                {"step": "implement core logic"},
                {"step": "test system"}
            ]

        if existing_plan:
            return existing_plan

        return []

    def _source_quality_score(
        self,
        url: str = "",
        text: str = "",
    ) -> int:
        try:
            url = self._safe_str(url).lower()
            text = self._safe_str(text).lower()

            score = 0

            trusted = [
                "reuters.com",
                "apnews.com",
                "bbc.com",
                "openai.com",
                "ft.com",
                "cnbc.com",
                "bloomberg.com",
                "theverge.com",
                "techcrunch.com",
            ]

            for domain in trusted:
                if domain in url:
                    score += 100

            if "rumor" in text:
                score -= 25

            if "opinion" in text:
                score -= 15

            return score

        except Exception:
            return 0

    def _clean_web_results(self, results: list) -> list:
        cleaned = []
        seen_domains = set()

        for item in results or []:
            if not isinstance(item, dict):
                continue

            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or "").strip()
            snippet = str(item.get("snippet") or item.get("content") or "").strip()

            if not url or not title:
                continue

            low_url = url.lower()

            # decode duckduckgo redirect instead of skipping
            if "duckduckgo.com" in low_url:
                try:
                    from urllib.parse import parse_qs, unquote, urlparse
                    parsed = urlparse(url)
                    qs = parse_qs(parsed.query)
                    if "uddg" in qs:
                        url = unquote(qs["uddg"][0])
                        low_url = url.lower()
                except Exception:
                    continue

            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.lower().replace("www.", "")
            except Exception:
                domain = ""

            # only dedupe by domain
            if domain and domain in seen_domains and len(cleaned) >= 3:
                continue

            if domain:
                seen_domains.add(domain)

            cleaned.append({
                "title": title,
                "snippet": snippet,
                "content": snippet,
                "url": url,
            })

        cleaned = sorted(
            cleaned,
            key=lambda item: self._source_quality_score(
                item.get("url", ""),
                item.get("title", ""),
            ),
            reverse=True,
        )

        return cleaned[:5]

    def _web_search(self, query: str) -> dict:
        query = self._safe_str(query).strip()
        if not query:
            return {"results": []}

        import requests
        import re
        from urllib.parse import quote_plus
        from xml.etree import ElementTree as ET

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        all_results = []

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
                    try:
                        from urllib.parse import parse_qs, unquote, urlparse
                        parsed = urlparse(link)
                        qs = parse_qs(parsed.query)
                        if "uddg" in qs:
                            link = unquote(qs["uddg"][0])
                    except Exception:
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
                exec_debug("SEARCH: DuckDuckGo HTML success")
                all_results.extend(results)

        except Exception as e:
            exec_debug("DDG HTML FAILED:", e)

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
                exec_debug("SEARCH: DuckDuckGo Lite success")
                all_results.extend(results)

        except Exception as e:
            exec_debug("DUCKDUCKGO_LITE_FAILED:", e)

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

                if "news.google.com" in link.lower():
                    continue

                results.append({
                    "title": title,
                    "snippet": description,
                    "content": description,
                    "url": link,
                })

                if len(results) >= 5:
                    break

            if results:
                exec_debug("SEARCH: Google News RSS success")
                all_results.extend(results)

        except Exception as e:
            exec_debug("GOOGLE RSS FAILED:", e)

        # -------------------------
        # FINAL CLEAN + RETURN
        # -------------------------
        cleaned = self._clean_web_results(all_results)

        return {"results": cleaned}

    def __init__(
        self,
        session_service: SessionService,
        memory_service: MemoryService,
        artifact_service: ArtifactService,
        web_service: WebService,
        recon_service: ReconService,
    ):

        self.runtime_cognitive_firewall = RuntimeCognitiveFirewall()

        # =========================
        # CORE SERVICES
        # =========================

        self.session_service = session_service
        self.memory_service = memory_service
        self.artifact_service = artifact_service
        self.web_service = web_service
        self.recon_service = recon_service

        # =========================
        # EXISTING ALIASES
        # DO NOT REMOVE
        # =========================

        self.sessions = session_service
        self.memory = memory_service
        self.memories = memory_service
        self.artifacts = artifact_service
        self.web = web_service
        self.recon = recon_service

        # =========================
        # CONFIG
        # =========================

        self.image_model = os.getenv(
            "NOVA_IMAGE_MODEL",
            "gpt-image-1",
        )

        self.image_size = os.getenv(
            "NOVA_IMAGE_SIZE",
            "1024x1024",
        )

        self.chat_model = os.getenv(
            "OPENAI_MODEL",
            "gpt-5.4",
        )

        self.model = self.chat_model

        exec_debug(
            "MODEL CHECK:",
            hasattr(
                self,
                "model",
            ),
            self.model,
        )

        self.memory_limit = int(
            os.getenv(
                "NOVA_MEMORY_LIMIT",
                "3",
            )
        )

        # =========================
        # UPLOADS
        # =========================

        self.uploads_dir = Path(
            os.getenv(
                "UPLOADS_DIR",
                r"C:\Users\Owner\nova\uploads",
            )
        )

        self.uploads_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        exec_debug(
            "CHATSERVICE INIT uploads_dir =",
            self.uploads_dir,
        )

        # =========================
        # CORE CLIENTS
        # =========================

        self.client = OpenAI()
        self.agent = AgentService()
        self.memory_ranker = MemoryRankerService()
        self.tools = ToolService(
            base_dir=os.getcwd()
        )

        # =========================
        # RESPONSE / INTENT SERVICES
        # =========================

        self.rewrite_service = ResponseRewriteService()
        self.intent_service = IntentService()
        self.python_runner = PythonRunnerService()

        # =========================
        # RUNTIME COGNITION
        # =========================

        self.runtime_cognitive_injection = (
            RuntimeCognitiveInjectionService()
        )

        self.runtime_brain = None

        # =========================
        # EXECUTION ENGINE
        # =========================

        self.execution_handler = ExecutionHandler(
            default_executor
        )

        self.runtime = RuntimeBootstrap.build(
            chat_service=self
        )

        self.execution_loop = ExecutionLoopService(
            execution_handler=self.execution_handler,
            runtime_service=self.runtime,
        )

        self.execution_service = ExecutionService()

        # =========================
        # AUTONOMY
        # =========================

        self.autonomy = AutonomyService(
            web_service=self.web,
            recon_service=self.recon,
            memory_service=self.memory,
            artifact_service=self.artifacts,
            max_steps=5,
            max_deep_js=5,
            max_follow_links=5,
        )

        # =========================
        # AGENT CORE (NEW ARCHITECTURE)
        # =========================

        self.brain = BrainCore()
        self.strategy = StrategyEngine()
        self.memory_core = MemoryCore()
        self.executor = Executor()

    # =========================
    # DEBUG / TEST HARNESS LAYER
    # =========================

    def _debug(self, *args):
        exec_debug(*args)

    def _build_runtime_cognition(self):

        runtime_summary = {}
        runtime_decision = {}

        runtime = getattr(
            self,
            "runtime_brain",
            None,
        )

        if runtime is None:

            return {
                "has_runtime_cognition": False,
            }

        if hasattr(
            runtime,
            "get_summary",
        ):

            runtime_summary = runtime.get_summary()

        elif hasattr(
            runtime,
            "summary",
        ):

            runtime_summary = runtime.summary()

        elif hasattr(
            runtime,
            "runtime_state",
        ):

            runtime_summary = getattr(
                runtime,
                "runtime_state",
                {},
            )

        if hasattr(
            runtime,
            "last_decision",
        ):

            runtime_decision = getattr(
                runtime,
                "last_decision",
                {},
            )

        return self.runtime_cognitive_injection.build(
            runtime_summary=runtime_summary,
            runtime_decision=runtime_decision,
        )

    def _run_test_harness(self, session_id):

        tests = [
            "run step",
            "next",
            "next",
            "run all",
            "apply_auto_fix",
            "next",
        ]

        results = []

        for t in tests:

            result = self.handle(
                user_text=t,
                session_id=session_id
            )

            results.append({
                "input": t,
                "output": result.get("debug", {}),
                "status": result.get("execution", {}).get("status"),
            })

            exec_debug("TEST RUN:", t, "?", result.get("execution", {}).get("status"))

        return {
            "ok": True,
            "results": results
        }

    def _auto_diagnose(self, user_text, brain_state, execution_state, error=None):

        diagnosis = {
            "input": user_text,
            "status": execution_state.get("status"),
            "step": execution_state.get("current_index"),
            "decision": brain_state.get("decision"),
            "error": str(error) if error else None,
            "root_cause": None,
            "fix_suggestion": None
        }

        # -------------------------
        # FAILURE CASE
        # -------------------------
        if execution_state.get("status") == "failed":

            diagnosis["root_cause"] = "execution step failed during runtime"

            if execution_state.get("current_index") is not None:
                diagnosis["root_cause"] += f" at step {execution_state.get('current_index')}"

            diagnosis["fix_suggestion"] = "retry step or adjust plan mutation logic"

        # -------------------------
        # STALL CASE
        # -------------------------
        elif execution_state.get("status") is None:

            diagnosis["root_cause"] = "execution state not updated (possible routing issue)"
            diagnosis["fix_suggestion"] = "check decision ? executor wiring"

        # -------------------------
        # DEFAULT CASE
        # -------------------------
        else:
            diagnosis["root_cause"] = "system behaving normally"
            diagnosis["fix_suggestion"] = "no action required"

        return diagnosis

    def _build_user_message(self, text: str, attachments=None, meta=None) -> dict:
        attachments = attachments or []
        meta = meta or {}
        return {
            "role": "user",
            "text": self._safe_str(text),
            "attachments": attachments,
            "meta": meta,
        }

    def _normalize_assistant_message(self, message):
        if message is None:
            return self._build_assistant_message(text="")

        if isinstance(message, dict):
            text = (
                message.get("text")
                or message.get("content")
                or message.get("assistant_message")
                or ""
            )

            meta = message.get("meta")
            if not isinstance(meta, dict):
                meta = {}

            message["text"] = text
            message["content"] = text
            message["meta"] = meta
            return message

        try:
            self._reflect(
                brain_state=getattr(self, "_last_intelligence_state", {}) or {},
                execution_result={}
            )
        except Exception:
            pass

        return self._build_assistant_message(
            text=str(message),
            meta={},
        )

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

    def _finalize_assistant_response(self, assistant_msg, fallback_text=""):
        """
        Safety wrapper: guarantees assistant message always exists and is valid.
        Prevents null/undefined exit paths from breaking execution flow.
        """

        if not assistant_msg:
            assistant_msg = self._build_assistant_message(
                text=fallback_text or "Execution complete."
            )

        # Ensure structure consistency
        if isinstance(assistant_msg, str):
            assistant_msg = self._build_assistant_message(text=assistant_msg)

        return assistant_msg


    def _safe_return(self, assistant_msg=None, fallback_text="Execution complete.", **meta):
        """
        Hard enforcement return gate.
        Every response MUST pass through here.
        """

        assistant_msg = self._finalize_assistant_response(
            assistant_msg,
            fallback_text=fallback_text,
        )

        if isinstance(assistant_msg, dict) and isinstance(meta, dict):
            existing_meta = assistant_msg.get("meta")

            if not isinstance(existing_meta, dict):
                existing_meta = {}

            existing_meta.update(meta)
            assistant_msg["meta"] = existing_meta

        return assistant_msg

    def _mark_ready_to_return(self, assistant_msg):
        """
        Internal final exit wrapper.
        ALL responses MUST pass through this.
        """
        return self._safe_return(assistant_msg)

    def _build_goal(self, user_text: str):
        """
        Converts raw input into a structured goal.
        """

        text = (user_text or "").lower()

        if "fix" in text or "error" in text or "bug" in text:
            return {
                "type": "debug",
                "goal": "debug and fix issue",
            }

        if "build" in text or "create" in text:
            return {
                "type": "build",
                "goal": "create requested system",
            }

        if "analyze" in text:
            return {
                "type": "analysis",
                "goal": "analyze provided input",
            }

        return {
            "type": "general",
            "goal": "respond normally",
        }

    def _build_plan(self, goal_obj: dict):
        """
        Turns a goal into structured execution steps.
        """

        goal_type = str(goal_obj.get("type") or "").strip().lower()

        if goal_type == "debug":
            return [
                {"action": "analyze", "input": "find issue"},
                {"action": "fix", "input": "apply correction"},
                {"action": "validate", "input": "check result"},
            ]

        if goal_type == "analysis":
            return [
                {"action": "analyze", "input": "inspect input"},
                {"action": "summarize", "input": "generate insights"},
            ]

        if goal_type == "build":
            return [
                {
                    "action": "design",
                    "input": "create structure",
                },
                {
                    "action": "implement",
                    "input": "build core logic",
                    "target_file": r"C:\Users\Owner\nova\nova_backend\sandbox\agent_target.py",
                    "target_function": "placeholder_function",
                },
                {
                    "action": "test",
                    "input": "validate output",
                    "target_file": r"C:\Users\Owner\nova\nova_backend\sandbox\agent_target.py",
                },
            ]

        return [
            {"action": "respond", "input": "direct reply"},
        ]

    def _execute_tool(self, step: dict):
        action = step.get("action")
        input_data = step.get("input")

        if action == "analyze":
            return f"analyzed: {input_data}"

        if action == "fix":
            return f"fixed: {input_data}"

        if action == "validate":
            return f"validated: {input_data}"

        if action == "web_search":
            return f"web result for: {input_data}"

        if action == "design":
            return f"designed: {input_data}"

        if action == "implement":
            return f"implemented: {input_data}"

        if action == "test":
            return f"tested: {input_data}"

        if action == "respond":
            return f"response: {input_data}"

        return f"unknown action: {action}"

    def _run_next_step(self, execution_state: dict):

        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        # =========================
        # RUNTIME INFLUENCE LAYER
        # =========================
        if runtime and isinstance(execution_state, dict):

            signal = execution_state.get("runtime_signal")

            if signal == "runtime_requested_failure_inspection":
                execution_state["debug_mode"] = True

            elif signal == "runtime_idle":
                execution_state["throttle"] = True

            elif signal == "runtime_stabilized_success":
                execution_state["lock"] = False

        runtime_override_index = None

        if runtime and isinstance(execution_state, dict):

            if signal == "runtime_requested_failure_inspection":
                runtime_override_index = max(current - 1, 0)

            elif signal == "runtime_idle":
                runtime_override_index = current

            elif signal == "runtime_stabilized_success":
                runtime_override_index = current + 1

        steps = execution_state.get("steps")
        if not isinstance(steps, list):
            steps = []

        current = self._execution_current_index(
            execution_state
        )

        runtime = getattr(self, "runtime", None)

        runtime_override_index = None

        # =========================
        # BOUNDS CHECK
        # =========================
        if current >= len(steps):
            execution_state = self._mark_execution_complete(
                execution_state,
            )
            return execution_state

        if runtime_override_index is not None:
            current = runtime_override_index

        current = max(0, min(current, len(steps) - 1))

        step = steps[current]

        # =========================
        # STEP MUTATION LAYER (ADD HERE)
        # =========================

        # =========================
        # PLAN MUTATION LAYER (AUTONOMY)
        # =========================
        if runtime and isinstance(execution_state, dict):

            signal = execution_state.get("runtime_signal")

            if signal == "runtime_requested_failure_inspection":

                steps.append({
                    "title": "runtime_recovery_step",
                    "action": "inspect",
                    "status": "pending",
                })

            elif signal == "runtime_idle":

                steps.append({
                    "title": "runtime_stabilization_step",
                    "action": "wait",
                    "status": "pending",
                })

            elif signal == "runtime_stabilized_success":

                steps.append({
                    "title": "runtime_acceleration_step",
                    "action": "optimize",
                    "status": "pending",
                })

            execution_state["steps"] = steps

        if runtime and isinstance(step, dict):

            signal = execution_state.get("runtime_signal")

            if signal == "runtime_requested_failure_inspection":
                step["mode"] = "debug"
                step["retries"] = step.get("retries", 0) + 1

            elif signal == "runtime_idle":
                step["mode"] = "paused"

            elif signal == "runtime_stabilized_success":
                step["mode"] = "accelerated"
                step["priority"] = "high"

        # =========================
        # APPLY RUNTIME EFFECTS
        # =========================
        if execution_state.get("debug_mode"):
            step["debug"] = True

        if execution_state.get("throttle"):
            step["throttled"] = True

        # =========================
        # EXECUTE STEP
        # =========================
        # existing execution logic continues here...

        result = self._execute_tool(step)

        step["result"] = result
        step["status"] = "completed"

        execution_state["steps"] = steps

        # =========================
        # HISTORY TRACKING
        # =========================
        history = execution_state.get("history")

        if not isinstance(history, list):
            history = []

        history.append(step)
        execution_state["history"] = history

        # =========================
        # ADVANCE POINTERS
        # =========================
        next_index = current + 1

        execution_state = self._sync_execution_state(
            execution=execution_state,
            current_index=next_index,
            current_step=(
                steps[next_index].get("title", "")
                if next_index < len(steps)
                else "complete"
            ),
            progress=next_index,
        )

        # =========================
        # STATE UPDATE
        # =========================
        if next_index < len(steps):
            execution_state["current_step_title"] = execution_state.get(
                "current_step",
                "",
            )
            execution_state = (
                self._mark_execution_running(
                    execution_state,
                    step_index=current,
                    current_step=(
                        execution_state.get(
                            "current_step",
                            "",
                        )
                    ),
                    waiting=(
                        not execution_state.get(
                            "auto_mode"
                        )
                    ),
                )
            )

        else:

            execution_state = (
                self._mark_execution_complete(
                    execution_state,
                )
            )

        return execution_state

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

        try:
            self._maybe_write_memory(decision, user_text, session_id)
        except Exception as e:
            exec_debug("FINALIZE_MEMORY_WRITE_ERROR:", e)

        if isinstance(assistant_msg, dict):
            existing_meta = assistant_msg.get("meta")
            meta = existing_meta if isinstance(existing_meta, dict) else {}

            # preserve existing keys (like sources)
            meta.setdefault("sources", meta.get("sources", []))
            meta.setdefault("source_urls", meta.get("source_urls", []))

            if not meta.get("sources"):
                import re

                assistant_text = self._safe_str(
                    assistant_msg.get("text")
                    or assistant_msg.get("content")
                    or ""
                )

                found_urls = re.findall(r"https?://[^\s\)\]\}<>\"']+", assistant_text)

                parsed_sources = []
                parsed_urls = []

                for found_url in found_urls[:10]:
                    clean_url = found_url.rstrip(".,;:")
                    if not clean_url:
                        continue

                    domain = clean_url.split("/")[2] if "://" in clean_url else clean_url
                    slug = clean_url.rstrip("/").split("/")[-1]
                    clean_title = slug.replace("-", " ").replace("_", " ").strip().title()
                    clean_domain = domain.replace("www.", "")
                    clean_homepage = clean_url.rstrip("/").lower()

                    if clean_homepage in {
                        f"https://{domain}".lower(),
                        f"http://{domain}".lower(),
                        f"https://{clean_domain}".lower(),
                        f"http://{clean_domain}".lower(),
                    }:
                        clean_title = clean_domain

                    if not clean_title or clean_title.lower() in {"news", "changelog", "docs"}:
                        clean_title = clean_domain

                    parsed_sources.append({
                        "title": clean_title or clean_url,
                        "url": clean_url,
                        "source": domain.replace("www.", ""),
                        "snippet": "",
                    })

                if parsed_sources:
                    meta["sources"] = parsed_sources
                    meta["source_urls"] = parsed_urls

            used_memory_items = []

            for key in ("memory_used", "used_memory", "memories_used"):
                value = meta.get(key)
                if isinstance(value, list):
                    used_memory_items = value
                    break

            if not used_memory_items:

                try:

                    used_memory_items = (
                        getattr(
                            self,
                            "_last_used_memory_items",
                            [],
                        )
                        or []
                    )

                except Exception as e:

                    exec_debug(
                        "FINALIZE_MEMORY_USED_ERROR:",
                        e,
                    )

                    used_memory_items = []

                except Exception as e:
                    exec_debug(
                        "FINALIZE_MEMORY_USED_ERROR:",
                        e,
                    )

            meta["memory_used"] = used_memory_items
            meta["used_memory"] = used_memory_items
            meta["memory_used_count"] = len(used_memory_items)
            meta["used_memory_count"] = len(used_memory_items)
            assistant_msg["meta"] = meta

        session = self._get_session_payload(session_id) or {}
        messages = session.get("messages")

        if not isinstance(messages, list):
            messages = []

        if isinstance(user_msg, dict):
            user_id = str(user_msg.get("id", "")).strip()

            already_has_user = any(
                isinstance(m, dict) and
                str(m.get("id", "")).strip() == user_id
                for m in messages
            )

            if not already_has_user:
                messages.append(user_msg)

        if isinstance(assistant_msg, dict):

            assistant_id = str(
                assistant_msg.get("id")
                or f"msg_{uuid.uuid4().hex}"
            ).strip()

            assistant_msg["id"] = assistant_id

            already_has_assistant = any(
                isinstance(m, dict) and
                str(m.get("id", "")).strip() == assistant_id
                for m in messages
            )

            if not already_has_assistant:
                messages.append(assistant_msg)

        session["id"] = session_id
        session["messages"] = messages

        try:
            existing = self.sessions.get_session(session_id)

            existing_messages = (
                existing.get("messages", [])
                if isinstance(existing, dict)
                else []
            )

            existing_count = (
                len(existing_messages)
                if isinstance(existing_messages, list)
                else 0
            )

            exec_debug(
                "FINALIZE SAVE DEBUG:",
                {
                    "existing_count": existing_count,
                    "message_count": len(messages),
                    "messages": messages,
                },
            )

            for msg in messages[existing_count:]:
                self.sessions.append_message(session_id, msg)

        except Exception as e:
            exec_debug("SESSION SAVE ERROR:", e)

        try:
            assistant_text_for_tracking = ""

            if isinstance(assistant_msg, dict):
                assistant_text_for_tracking = self._safe_str(
                    assistant_msg.get("text")
                )

            self._auto_track_working_state(
                session_id=session_id,
                user_text=user_text,
                assistant_text="",
            )

        except Exception as e:
            exec_debug("AUTO_TRACK_WORKING_STATE_ERROR:", e)

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
            "debug": {
                "decision": decision,
                "route": "chat_service.handle",
                "route_taken": (
                    decision.get("route")
                    if isinstance(decision, dict)
                    else ""
                ),
            },
        }

    def _execute_auto_fix_file(
        self,
        user_text: str,
        session_id: str,
        attachments=None,
    ) -> dict:
        exec_debug("AUTO_FIX_FILE_HIT:", user_text)

        import os
        import time
        import py_compile
        import shutil
        import textwrap
        import traceback
        import re

        attachments = attachments or []

        user_text = self._safe_str(user_text)

        path = self._guess_path_from_text(user_text)

        if not path:
            assistant_text = (
                "Auto-fix failed.\n\n"
                "Reason: no file path detected.\n\n"
                "Send like:\n"
                "fix this file C:\\Users\\Owner\\nova\\path\\file.py\n"
                "error: paste the traceback"
            )

            assistant_msg = self._build_assistant_message(text=assistant_text)

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self._build_user_message(user_text),
                assistant_msg=assistant_msg,
                decision={"route": "auto_fix_failed"},
            )

        file_path = path.strip()
        pending_fix_mode = self._get_session_meta(session_id, "pending_fix_mode") or "file"

        if "_process_execution_command" in user_text:
            pending_fix_mode = "function"
            self._set_session_meta(
                session_id,
                "pending_fix_mode",
                "function",
            )
            self._set_session_meta(
                session_id,
                "pending_fix_func_name",
                "_process_execution_command",
            )

        traceback_func_match = re.findall(
            r'in\s+([A-Za-z_][A-Za-z0-9_]*)',
            user_text,
        )
        traceback_func_name = traceback_func_match[-1] if traceback_func_match else ""

        if pending_fix_mode == "function" and traceback_func_name:
            self._set_session_meta(session_id, "pending_fix_func_name", traceback_func_name)

        if "```" in file_path:
            file_path = file_path.split("```", 1)[0].strip()

        if "python" in file_path.lower():
            file_path = file_path.split("python", 1)[0].strip()

        code_match = re.search(
            r"```(?:python|py)?\s*(.*?)```",
            user_text,
            re.IGNORECASE | re.DOTALL,
        )

        raw_code = code_match.group(1).strip() if code_match else ""

        if not raw_code:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_code = f.read()
            except Exception as e:
                assistant_text = (
                    "Auto-fix failed.\n\n"
                    f"File: {file_path}\n\n"
                    f"Reason: could not read file: {type(e).__name__}: {self._safe_str(e)}"
                )

                assistant_msg = self._build_assistant_message(text=assistant_text)

                return self._finalize_response(
                    session_id=session_id,
                    user_text=user_text,
                    user_msg=self._build_user_message(user_text),
                    assistant_msg=assistant_msg,
                    decision={"route": "auto_fix_read_failed"},
                )

        if pending_fix_mode != "function" and len(raw_code) > 12000:
            assistant_text = (
                "Auto-fix paused.\n\n"
                f"File:\n{file_path}\n\n"
                "Reason: file is too large for safe whole-file auto-fix.\n\n"
                "Use a targeted function, pasted block, or traceback instead."
            )

            assistant_msg = self._build_assistant_message(text=assistant_text)

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self._build_user_message(user_text),
                assistant_msg=assistant_msg,
                decision={"route": "auto_fix_too_large"},
            )

        if pending_fix_mode == "function":
            func_name = self._get_session_meta(session_id, "pending_fix_func_name") or ""

            pattern = rf"(def\s+{re.escape(func_name)}\s*\(.*?\):\n(?:\s+.*\n)*)"
            match = re.search(pattern, raw_code, re.DOTALL)
            extracted_function = match.group(1) if match else raw_code

            fix_prompt = (
                "You are fixing a Python function.\n"
                "Return ONLY the corrected function.\n"
                "Do NOT return the full file.\n"
                "No markdown. No explanation.\n\n"

                f"ERROR CONTEXT:\n{user_text}\n\n"

                f"TARGET FUNCTION:\n{func_name}\n\n"

                "FUNCTION CODE:\n"
                f"{extracted_function}\n\n"

                "Fix the root cause of the error. Do not rewrite unrelated logic."
            )
        else:
            fix_prompt = (
                "You are fixing a Python file.\n"
                "Return ONLY the complete corrected Python file.\n"
                "No markdown. No explanation. No code fences.\n\n"

                f"ERROR CONTEXT:\n{user_text}\n\n"

                f"FILE PATH:\n{file_path}\n\n"

                "CURRENT FILE CONTENT:\n"
                f"{raw_code}\n\n"

                "Fix the root cause of the error. Preserve architecture."
            )

        try:
            model_response = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert Python repair engine. "
                            "Preserve existing architecture. "
                            "Fix only what is necessary. "
                            "Return only the corrected code requested by the user prompt."
                        ),
                    },
                    {
                        "role": "user",
                        "content": fix_prompt,
                    },
                ],
            )

            fixed_code = self._safe_str(model_response.output_text).strip()

            if fixed_code.startswith("```"):
                fixed_code = re.sub(r"^```(?:python|py)?\s*", "", fixed_code, flags=re.IGNORECASE)
                fixed_code = re.sub(r"\s*```$", "", fixed_code).strip()

            if not fixed_code:
                raise ValueError("model returned empty fixed code")

        except Exception as e:
            error_text = self._safe_str(e)
            error_name = type(e).__name__
            lowered_error = error_text.lower()

            if (
                "ratelimiterror" in error_name.lower()
                or "insufficient_quota" in lowered_error
                or "exceeded your current quota" in lowered_error
            ):
                assistant_text = (
                    "Auto-fix paused: OpenAI quota unavailable.\n\n"
                    f"File: {file_path}\n\n"
                    "Nova kept the failure context safe. "
                    "Fix generation can resume after API quota is available."
                )

                route = "auto_fix_quota_paused"

            else:
                assistant_text = (
                    "Auto-fix failed.\n\n"
                    f"File: {file_path}\n"
                    f"Reason: model fix failed: {error_name}: {error_text}"
                )

                route = "auto_fix_model_failed"

            assistant_msg = self._build_assistant_message(
                text=assistant_text
            )

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self._build_user_message(user_text),
                assistant_msg=assistant_msg,
                decision={"route": route},
            )

        backup_path = None

        # =============================
        # SAVE AS PENDING FIX (NO WRITE)
        # =============================

        try:
            self._set_session_meta(session_id, "pending_fix_file_path", file_path)

            fixed_code = self._normalize_python_indentation(fixed_code)

            self._set_session_meta(session_id, "pending_fix_code", fixed_code)
            self._set_session_meta(session_id, "pending_fix_mode", pending_fix_mode)

            if pending_fix_mode == "function":
                self._set_session_meta(
                    session_id,
                    "pending_fix_func_name",
                    self._get_session_meta(session_id, "pending_fix_func_name") or "",
                )

            assistant_text = (
                "Auto-fix prepared.\n\n"
                f"File:\n{file_path}\n\n"
                "Preview of fix:\n"
                "```python\n"
                f"{fixed_code[:2000]}\n"
                "```\n\n"
                "Fix is ready but not applied.\n\n"
                "Say `apply fix` to write it."
            )

            assistant_msg = self._build_assistant_message(text=assistant_text)

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self._build_user_message(user_text),
                assistant_msg=assistant_msg,
                decision={
                    "route": "auto_fix_prepare",
                    "pending_fix_mode": pending_fix_mode,
                },
            )

        except Exception as e:
            assistant_text = (
                "Auto-fix failed.\n\n"
                f"File: {file_path}\n"
                f"Error: {type(e).__name__}: {self._safe_str(e)}"
            )

            assistant_msg = self._build_assistant_message(text=assistant_text)

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self._build_user_message(user_text),
                assistant_msg=assistant_msg,
                decision={"route": "auto_fix_error"},
            )

        except Exception as e:
            assistant_text = (
                "Auto-fix failed.\n\n"
                f"File: {file_path}\n"
                f"Error: {type(e).__name__}: {self._safe_str(e)}"
            )

            assistant_msg = self._build_assistant_message(text=assistant_text)

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self._build_user_message(user_text),
                assistant_msg=assistant_msg,
                decision={"route": "auto_fix_error"},
            )

            compile_ok = True
            compile_output = ""

            try:
                py_compile.compile(file_path, doraise=True)
            except Exception:
                compile_ok = False
                compile_output = traceback.format_exc().strip()

            assistant_text = (
                "Auto-fix applied.\n\n"
                f"File: {file_path}\n"
                f"Backup: {backup_path or 'none'}\n\n"
                "Fix:\n"
                "- normalized indentation\n"
                "- replaced tabs with 4 spaces\n\n"
                "Result:\n"
                "```python\n"
                f"{fixed_code.strip()}\n"
                "```\n\n"
                f"Compile check: {'passed' if compile_ok else 'failed'}"
            )

            if compile_output:
                assistant_text += f"\n\n{compile_output}"

            return {
                "assistant_message": {"text": assistant_text},
                "session": self._get_session_payload(session_id),
                "ok": True,
            }

        except Exception as e:
            assistant_text = (
                "Auto-fix failed.\n\n"
                f"File: {file_path}\n"
                f"Error: {e}"
            )

            return {
                "assistant_message": {"text": assistant_text},
                "session": self._get_session_payload(session_id),
                "ok": False,
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

        # =====================================
        # NOVA EXECUTION FLOW (ORDERED LOGIC)
        # =====================================
        # 1. Load state
        # 2. Inject memory
        # 3. Parse intent
        # 4. Execute logic
        # 5. Generate response
        # 6. Apply UX cleanup
        # 7. Return final output

        decision = decision if isinstance(decision, dict) else {}
        attachments = attachments or []

        original_user_text = self._safe_str(
            user_text
        )

        text_lc = original_user_text.lower().strip()

        # =====================================
        # AUTO IDENTITY / PREFERENCE REINFORCEMENT
        # =====================================

        try:

            identity_patterns = [
                "my name is ",
                "i am ",
                "i'm ",
            ]

            preference_patterns = [
                "i prefer ",
                "remember ",
                "from now on ",
                "always ",
                "never ",
            ]

            if any(
                pattern in text_lc
                for pattern in identity_patterns
            ):

                self._reinforce_memory(
                    session_id=session_id,
                    memory_text=(
                        f"User identity/context: "
                        f"{original_user_text}"
                    ),
                    category="profile",
                    amount=3,
                )

            if any(
                pattern in text_lc
                for pattern in preference_patterns
            ):

                self._reinforce_memory(
                    session_id=session_id,
                    memory_text=(
                        f"User preference/correction: "
                        f"{original_user_text}"
                    ),
                    category="preference",
                    amount=3,
                )

        except Exception as e:

            exec_debug(
                "IDENTITY_PREFERENCE_REINFORCEMENT_FAILED:",
                e,
            )

        # =====================================
        # AUTO FILE DETECTION
        # =====================================

        try:

            detected_file = ""
            detected_bug = ""

            file_patterns = [
                r"[A-Za-z]:\\\\[^\n\r\t\"']+\.py",
                r"[A-Za-z]:\\\\[^\n\r\t\"']+\.js",
                r"[A-Za-z]:\\\\[^\n\r\t\"']+\.html",
                r"[A-Za-z]:\\\\[^\n\r\t\"']+\.css",
                r"[A-Za-z]:\\\\[^\n\r\t\"']+\.json",
            ]

            for pattern in file_patterns:

                match = re.search(
                    pattern,
                    original_user_text,
                    re.IGNORECASE,
                )

                if match:

                    detected_file = (
                        match.group(0).strip()
                    )

                    break

            traceback_match = re.search(
                r'File "([^"]+)"',
                original_user_text,
                re.IGNORECASE,
            )

            if traceback_match:

                detected_file = str(
                    traceback_match.group(1)
                ).strip()

            bug_markers = [
                "traceback",
                "error",
                "exception",
                "syntaxerror",
                "indentationerror",
                "nameerror",
                "typeerror",
                "attributeerror",
                "valueerror",
                "failed",
            ]

            if any(
                marker in text_lc
                for marker in bug_markers
            ):

                detected_bug = (
                    original_user_text[:1200]
                    .strip()
                )

            if detected_file:

                ws = (
                    self._get_working_state(
                        session_id
                    )
                    or {}
                )

                self._update_working_state(
                    session_id,
                    {
                        "current_file":
                            detected_file,

                        "active_task":
                            (
                                ws.get(
                                    "active_task"
                                )
                                or "active debugging"
                            ),

                        "current_bug":
                            detected_bug,

                        "checkpoint":
                            (
                                "auto_bug_detected"
                                if detected_bug
                                else "auto_file_detected"
                            ),
                    },
                )

                self._reinforce_memory(
                    session_id=session_id,
                    memory_text=(
                        f"Current file: "
                        f"{detected_file}"
                    ),
                    category="operational",
                    amount=2,
                )

                if detected_bug:

                    self._reinforce_memory(
                        session_id=session_id,
                        memory_text=(
                            f"Current bug: "
                            f"{detected_bug[:500]}"
                        ),
                        category="correction",
                        amount=2,
                    )

        except Exception as e:

            exec_debug(
                "AUTO_FILE_DETECTION_FAILED:",
                e,
            )

        # =====================================
        # OPERATIONAL CONTEXT INTERCEPTS
        # =====================================

        if text_lc in {
            "what file are we in",
            "which file",
            "current file",
            "what file",
        }:

            ws = (
                self._get_working_state(
                    session_id
                )
                or {}
            )

            current_file = str(
                ws.get("current_file") or ""
            ).strip()

            if not current_file:

                current_file = (
                    "No active file is currently tracked."
                )

            assistant_msg = (
                self._build_assistant_message(
                    text=(
                        f"Current file:\n"
                        f"{current_file}"
                    )
                )
            )

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg={
                    "role": "user",
                    "text": user_text,
                    "attachments": [],
                    "meta": {},
                },
                assistant_msg=assistant_msg,
                saved_artifact=None,
            )

        if text_lc in {
            "what is the active task",
            "active task",
            "what are we doing",
        }:

            ws = (
                self._get_working_state(
                    session_id
                )
                or {}
            )

            active_task = str(
                ws.get("active_task") or ""
            ).strip()

            if not active_task:

                active_task = (
                    "No active task is currently tracked."
                )

            assistant_msg = (
                self._build_assistant_message(
                    text=(
                        f"Active task:\n"
                        f"{active_task}"
                    )
                )
            )

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg={
                    "role": "user",
                    "text": user_text,
                    "attachments": [],
                    "meta": {},
                },
                assistant_msg=assistant_msg,
                saved_artifact=None,
            )

        if text_lc in {
            "what did i just say",
            "what did i say",
            "what was my last message",
        }:

            print("RECALL INTERCEPT HIT")

            all_sessions = self.sessions.list_sessions()

            session_messages = []

            for s in all_sessions:
                if (
                    isinstance(s, dict)
                    and str(s.get("id")) == str(session_id)
                ):
                    session_messages = s.get(
                        "messages",
                        []
                    )
                    break

            previous_user = ""

            user_messages = [
                m for m in session_messages
                if isinstance(m, dict)
                and m.get("role") == "user"
            ]

            if len(user_messages) >= 2:
                previous_user = str(
                    user_messages[-2].get("text", "")
                ).strip()

            if not previous_user:
                previous_user = (
                    "I could not find a previous message."
                )

            assistant_msg = (
                self._build_assistant_message(
                    text=(
                        f'Your previous message was: '
                        f'"{previous_user}"'
                    )
                )
            )

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg={
                    "role": "user",
                    "text": user_text,
                    "attachments": [],
                    "meta": {},
                },
                assistant_msg=assistant_msg,
                saved_artifact=None,
            )

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg={
                    "role": "user",
                    "text": user_text,
                    "attachments": [],
                    "meta": {},
                },
                assistant_msg=assistant_msg,
                saved_artifact=None,
            )

        assistant_text = ""
        assistant_msg = None

        route = self._safe_str(
            decision.get("route")
        ).lower()

        try:
            ws = self._get_working_state(session_id) or {}

            memory_brain = []

            for key, label in (
                ("active_task", "Task"),
                ("current_file", "File"),
                ("current_bug", "Bug"),
                ("checkpoint", "Checkpoint"),
                ("next_move", "Next"),
                ("last_success", "Last success"),
                ("last_error", "Last error"),
            ):
                value = ws.get(key)

                if value:
                    memory_brain.append(
                        f"{label}: {value}"
                    )

            execution_keywords = {
                "next",
                "continue",
                "run step",
                "run all",
                "execute",
                "retry",
                "test fail",
                "fix",
                "debug",
                "traceback",
                "error",
                "bug",
            }

            should_attach_operational_context = any(
                x in text_lc
                for x in execution_keywords
            )

            if memory_brain and should_attach_operational_context:
                brain_context = "\n".join(memory_brain)

                user_text = (
                    "[NOVA ACTIVE CONTEXT]\n"
                    f"{brain_context}\n\n"
                    "[USER MESSAGE]\n"
                    f"{original_user_text}"
                )

        except Exception as e:
            exec_debug(
                "MEMORY_PRIORITY_LAYER_ERROR:",
                e,
            )

        # =====================================
        # CONTINUITY MEMORY PERSISTENCE LAYER
        # =====================================
        try:
            ws = self._get_working_state(session_id) or {}

            if original_user_text:
                ws["last_user_input"] = original_user_text

            if text_lc:
                ws["last_intent"] = text_lc

            self._update_working_state(session_id, ws)

        except Exception as e:
            exec_debug(
                "CONTINUITY_MEMORY_PERSIST_FAILED:",
                e,
            )

        if text_lc.strip() in {
            "regen",
            "regenerate",
            "redo image",
            "make another",
            "another image",
        }:
            last_prompt = self._get_session_meta(
                session_id,
                "last_image_prompt",
            ) or "generate an image"

            return self._handle_image_generation(
                prompt=last_prompt,
                session_id=session_id,
                parent_artifact_id="",
                source_type="regenerated",
            )

        regen_commands = {
            "regen",
            "regenerate",
            "redo image",
            "make another",
            "another image",
        }

        if text_lc.strip() in regen_commands:
            last_prompt = self._get_session_meta(
                session_id,
                "last_image_prompt",
            ) or ""

            last_prompt = self._safe_str(last_prompt).strip()

            if not last_prompt or last_prompt in regen_commands:
                last_prompt = "generate an image"

            return self._handle_image_generation(
                prompt=last_prompt,
                session_id=session_id,
                parent_artifact_id=parent_artifact_id,
                source_type="regenerated",
            )

        if self._is_image_generation_request(user_text):
            return self._handle_image_generation(
                prompt=user_text,
                session_id=session_id,
                parent_artifact_id=(
                    parent_artifact_id
                    if "parent_artifact_id" in locals()
                    else ""
                ),
            )

        explicit_execution_commands = {
            "next",
            "nex",
            "continue",
            "continue on",
            "keep going",
            "go",
            "run next",
            "next step",
            "run_step",
            "run step",
            "run_all",
            "run all",
            "run it",
            "execute",
            "execute all",
            "retry",
            "retry_failed",
            "retry failed",
            "try again",
            "rerun failed",
            "test_fail",
            "test fail",
            "stop",
            "cancel",
        }

        lowered = (
            str(user_text or "")
            .strip()
            .lower()
        )

        planner_prefixes = (
            "auto-plan",
            "build ",
            "create ",
            "make ",
            "implement ",
            "fix ",
            "repair ",
        )

        is_execution = (
            lowered.strip() in explicit_execution_commands
            or lowered.startswith(planner_prefixes)
        )

        if is_execution and text_lc.strip() not in {
            "continue",
            "next",
            "run it",
            "go",
            "run next",
            "next step",
            "what next",
            "what now",
        }:
            exec_debug(
                "EXECUTION INTERCEPT HIT",
                lowered,
            )

            execution_state = (
                self._process_goal_and_plan(
                    user_text,
                    session_id,
                )
            )

            exec_debug(
                "PLAN RESULT =",
                execution_state,
            )

            if execution_state:

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                try:
                    session_obj = (
                        self.sessions.get_session(session_id)
                        or {}
                    )

                    session_obj["execution_state"] = execution_state

                    session_obj["active_execution"] = (
                        execution_state
                        if (
                            isinstance(execution_state, dict)
                            and execution_state.get("steps")
                            and self._safe_str(
                                execution_state.get("status")
                            ).lower() != "complete"
                        )
                        else {}
                    )

                    self.sessions.update_session(
                        session_id,
                        session_obj,
                    )

                except Exception as e:
                    exec_debug(
                        "EXECUTION SESSION SAVE FAILED:",
                        e,
                    )

            if execution_state:

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

            working_state = (
                self._get_working_state(session_id)
                or {}
            )

            execution_state = (
                execution_state
                if isinstance(execution_state, dict)
                else {}
            )

            mission_state = self._build_mission_state(
                working_state=working_state,
                execution_state=execution_state,
            )

            if (
                execution_state.get("steps")
                and self._safe_str(
                    execution_state.get("status")
                ).lower()
                in {
                    "running",
                    "adapting",
                    "waiting",
                }
            ):

                self._update_working_state(
                    session_id,
                    {
                        "mission": mission_state,

                        "active_task": user_text,

                        "next_move": "run_step",

                        "checkpoint": (
                            "execution_plan_created"
                        ),

                        "execution_status": "running",
                    },
                )

            print(
                "EXECUTION RETURNING PROCESS COMMAND",
                "run_step",
            )

            return self._process_execution_command(
                command="run_step",
                session_id=session_id,
                execution_state=execution_state,
            )

        is_continue = text_lc.strip() in {
            "continue",
            "next",
            "run it",
            "go",
        }

        # SINGLE SOURCE OF TRUTH
        state = self._get_working_state(session_id) or {}
        session = self._get_session_payload(session_id)

        mission_mode = self._safe_str(state.get("mission_mode"))

        active_task = self._safe_str(state.get("active_task"))
        next_step = self._safe_str(state.get("next_move"))

        # === EXECUTION LOCK DISABLED ===
        # Execution now only runs through _maybe_lock_execution_flow().
        # Normal chat should not be hijacked just because working_state exists.
        if False:
            exec_debug("FORCING EXECUTION MODE FROM WORKING STATE")

        operational_queries = {
            "what file are we in",
            "which file",
            "current file",
            "what file",
            "what is the active task",
            "active task",
            "what are we doing",
            "resume mission",
            "resume task",
            "show mission",
            "show working state",
            "show execution",
            "where are we now",
        }

        if text_lc in operational_queries:

            working_state = (
                self._get_working_state(session_id)
                or {}
            )

            has_real_state = any([
                working_state.get("active_task"),
                working_state.get("current_file"),
                working_state.get("current_bug"),
                working_state.get("next_move"),
                working_state.get("checkpoint"),
            ])

            if not has_real_state:

                mission = {}

                dominant_memory = (
                    self._rank_memory_context(
                        user_text=user_text,
                        memories=(
                            self.memories.all()
                            or []
                        ),
                        working_state=working_state,
                        execution_state={},
                        limit=5,
                    )
                    or []
                )

                memory_lines = []
                fallback_lines = []
                seen_memory = set()

                blocked_internal_phrases = {
                    "execution handler",
                    "next move",
                    "internal reasoning",
                    "thinking step",
                    "need to run",
                }

                for item in dominant_memory:

                    if not isinstance(item, dict):
                        continue

                    text = self._safe_str(
                        item.get("text")
                        or item.get("content")
                    ).strip()

                    if not text:
                        continue

                    text_lower = text.lower()

                    if any(
                        phrase in text_lower
                        for phrase in blocked_internal_phrases
                    ):
                        continue

                    normalized = text_lower.strip()

                    if normalized in seen_memory:
                        continue

                    seen_memory.add(normalized)

                    memory_lines.append(
                        f"- {text}"
                    )

                if memory_lines:

                    fallback_lines.extend(
                        [
                            "Recent context available (trimmed for safety):",
                            *memory_lines[:3],
                        ]
                    )

                if not fallback_lines:

                    fallback_lines.append(
                        "No active working state is currently tracked."
                    )

                clean_fallback = []

                for line in fallback_lines:

                    line_str = self._safe_str(line).strip()

                    if not line_str:
                        continue

                    if (
                        "Recovered operational context"
                        in line_str
                    ):
                        continue

                    clean_fallback.append(line_str)

                assistant_msg = (
                    self._build_assistant_message(
                        text="\n".join(clean_fallback)
                        or (
                            "No active working state "
                            "is currently tracked."
                        )
                    )
                )

                return self._finalize_response(
                    session_id=session_id,
                    user_text=user_text,
                    user_msg={
                        "role": "user",
                        "text": user_text,
                        "attachments": [],
                        "meta": {},
                    },
                    assistant_msg=assistant_msg,
                )

            working_state = (
                self._get_working_state(session_id)
                or {}
            )

            persisted_execution_state = self._load_execution_state(
                session_id
            )

            if (
                isinstance(persisted_execution_state, dict)
                and persisted_execution_state.get("steps")
            ):
                execution_state = persisted_execution_state
            else:
                execution_state = {}

            reconciled = self._reconcile_execution_state(
                session_id=session_id,
                working_state=working_state,
                execution_state=execution_state,
            )

            working_state = (
                reconciled.get("working_state")
                or {}
            )

            execution_state = (
                reconciled.get("execution_state")
                or {}
            )

            mission_state = self._build_mission_state(
                working_state=working_state,
                execution_state=execution_state,
            )

            assistant_text = self._format_mission_state(
                mission_state
            ) 

            return {
                "ok": True,
                "assistant_message": (
                    self._build_assistant_message(
                        "No active working state is currently tracked."
                    )
                ),
                "session": self._get_session_payload(
                    session_id
                ),
                "saved_artifact": None,
                "artifacts": [],
                "debug": {
                    "route_taken": (
                        "mission_state_continuity_suppressed"
                    ),
                },
            }

        route = self._safe_str(
            decision.get("route")
        ).lower()

        isolated_routes = {
            self.ROUTE_WEB_FETCH,
            self.ROUTE_IMAGE_GENERATION,
        }

        # =========================
        # RUNTIME ROUTE
        # =========================

        if route == "runtime":

            runtime_command = self._safe_str(
                decision.get("runtime_command")
            ).strip().lower()

            execution_state = (
                self._get_session_meta(
                    session_id,
                    "execution_state",
                )
                or {}
            )

            try:

                if runtime_command == "/runtime state":

                    runtime_result = {
                        "runtime_attached": bool(
                            getattr(
                                self,
                                "runtime",
                                None,
                            )
                        ),
                        "runtime_class": (
                            self.runtime.__class__.__name__
                            if getattr(
                                self,
                                "runtime",
                                None,
                            )
                            else ""
                        ),
                        "cycle_count": getattr(
                            self.runtime,
                            "cycle_count",
                            0,
                        ),
                        "last_reflection": getattr(
                            self.runtime,
                            "last_reflection",
                            {},
                        ),
                        "last_decision": getattr(
                            self.runtime,
                            "last_decision",
                            {},
                        ),
                    }

                    return self._build_assistant_message(
                        text=str(runtime_result)
                    )

                elif text_lc in {
                    "/runtime replays",
                    "/runtime replay",
                    "/runtime replay list",
                }:

                    runtime = getattr(
                        self,
                        "runtime",
                        None,
                    )

                    if (
                        not runtime
                        or not hasattr(
                            runtime,
                            "get_recent_replays",
                        )
                    ):
                        return self._build_assistant_message(
                            text=str(
                                {
                                    "ok": False,
                                    "error": (
                                        "runtime_replay_unavailable"
                                    ),
                                }
                            )
                        )

                    return self._build_assistant_message(
                        text=str(
                            {
                                "ok": True,
                                "replays": (
                                    runtime.get_recent_replays(
                                        limit=10,
                                    )
                                ),
                            }
                        )
                    )

                elif text_lc.startswith(
                    "/runtime replay explain"
                ):

                    runtime = getattr(
                        self,
                        "runtime",
                        None,
                    )
                    replay_id = runtime_command.replace(
                        "/runtime replay explain",
                        "",
                        1,
                    ).strip()

                    if (
                        not runtime
                        or not hasattr(
                            runtime,
                            "explain_replay",
                        )
                    ):
                        return self._build_assistant_message(
                            text=str(
                                {
                                    "ok": False,
                                    "error": (
                                        "runtime_replay_unavailable"
                                    ),
                                }
                            )
                        )

                    return self._build_assistant_message(
                        text=str(
                            runtime.explain_replay(
                                replay_id=replay_id,
                            )
                        )
                    )

                else:

                    runtime_result = (
                        self.runtime.run_cycle(

                            execution_state=execution_state,
                            world_state={},
                            scheduler_state={},
                            knowledge_graph=None,
                        )
                    )

            except Exception as e:

                runtime_result = {
                    "ok": False,
                    "runtime_error": type(e).__name__,
                    "message": str(e),
                }

            assistant_msg = self._build_assistant_message(
                text=str(runtime_result)
            )

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=self._build_user_message(
                    original_user_text,
                    attachments=attachments,
                ),
                assistant_msg=assistant_msg,
                decision=decision,
            )

        if route in isolated_routes:
            memory_context = ""

            if route == self.ROUTE_WEB_FETCH:
                return self._execute_web_fetch(
                    decision=decision,
                    user_text=user_text,
                    session_id=session_id,
                    attachments=attachments,
                )

        user_msg = self._build_user_message(
            original_user_text,
            attachments=attachments,
        )
        if not memory_context:
            memory_context = self._build_memory_context_for_chat(
                user_text,
                decision,
                session_id,
            )

        dominant_memory = []
        memory_dominance_debug = []

        used_memories = []

        try:

            used_memories = (
                getattr(
                    self,
                    "_last_used_memory_items",
                    [],
                )
                or []
            )

        except Exception:

            used_memories = []

        working_state = (
            self._get_working_state(
                session_id
            )
            or {}
        )

        execution_state = (
            self._get_session_meta(
                session_id,
                "execution_state",
            )
            or {}
        )

        try:

            has_real_state = any([
                (
                    working_state.get("active_task")
                    and not self._is_control_command_value(
                        working_state.get("active_task")
                    )
                ),

                working_state.get("current_file"),

                working_state.get("current_bug"),

                (
                    working_state.get("next_move")
                    and not self._is_control_command_value(
                        working_state.get("next_move")
                    )
                ),

                (
                    working_state.get("checkpoint")
                    and working_state.get("checkpoint")
                    != "execution_plan_created"
                ),
            ])

            has_real_execution = any([
                execution_state.get("steps"),
                execution_state.get("current_step"),
                execution_state.get("status") == "running",
            ])

            if (
                not has_real_state
                and not has_real_execution
            ):
                used_memories = []
                dominant_memory = []
                memory_dominance_debug = []
                ranked_memories = []

            else:
                ranked_memories = self._rank_memory_context(
                    memories=used_memories,
                    user_text=user_text,
                    working_state=working_state,
                    execution_state=execution_state,
                    limit=5,
                )

            for mem in ranked_memories:

                if isinstance(mem, dict):

                    text = str(
                        mem.get("content")
                        or mem.get("text")
                        or mem.get("memory")
                        or ""
                    ).strip()

                else:
                    text = str(mem).strip()

                if text:

                    dominant_memory.append(
                        f"- {text}"
                    )





                    memory_dominance_debug.append(
                        text[:300]
                    )

        except Exception as e:

            print(
                "[MEMORY DOMINANCE ERROR]",
                e,
            )

        dominance_block = ""

        continuity_queries = [
            "continue",
            "resume",
            "what's next",
            "next step",
            "next move",
            "active task",
            "current file",
            "show working state",
            "show mission",
            "execution",
            "checkpoint",
        ]

        should_apply_dominance = any(
            q in text_lc
            for q in continuity_queries
        )

        if dominant_memory and should_apply_dominance:
            dominance_block = (
                "\n\n"
                "HIGH PRIORITY MEMORY:\n"
                "The following memory MUST dominate continuity, "
                "identity, operational awareness, and response generation.\n\n"
                + "\n".join(dominant_memory)
            )

        memory_context += dominance_block

        answer_depth = self._get_session_meta(session_id, "answer_depth") or "short"

        depth_instruction = {
            "short": "Answer briefly: 2-6 lines unless more detail is clearly needed.",
            "medium": "Answer with enough detail to be useful, but avoid long essays.",
            "deep": "Give a deeper explanation with clear structure and useful detail.",
        }.get(answer_depth, "Answer briefly unless more detail is needed.")

        if memory_context:
            memory_context = f"{memory_context}\n\nAnswer depth instruction:\n{depth_instruction}"
        else:
            memory_context = f"Answer depth instruction:\n{depth_instruction}"

        if route in isolated_routes:
            model_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are operating in isolated tool mode. "
                        "Do not use prior conversation context, "
                        "memory, execution state, or continuity."
                    ),
                },
                {
                    "role": "user",
                    "content": user_text,
                },
            ]
        else:
            model_messages = self._compose_model_messages(
                user_text=user_text,
                session=session,
                decision=decision,
                memory_context=memory_context,
            )

        recall_text = original_user_text.lower().strip()

        if recall_text in {
            "what did i just say",
            "what did i say",
            "what was my last message",
        }:

            session_messages = (
                session.get("messages", [])
                if isinstance(session, dict)
                else []
            )

            previous_user = ""

            for msg in reversed(session_messages):

                if not isinstance(msg, dict):
                    continue

                role = self._safe_str(msg.get("role"))
                text = self._safe_str(msg.get("text")).strip()

                if role != "user":
                    continue

                # block corrupted context leaks
                lowered = text.lower()

                blocked = [
                    "mission:",
                    "working state:",
                    "next move:",
                    "target file:",
                    "resumed context",
                    "we're still lined up",
                ]

                if any(b in lowered for b in blocked):
                    continue

                previous_user = text
                break

            user_messages = [
                m for m in session_messages
                if isinstance(m, dict)
                and m.get("role") == "user"
            ]

            if len(user_messages) >= 2:
                previous_user = str(
                    user_messages[-2].get("text", "")
                ).strip()

            if not previous_user:
                previous_user = (
                    "I could not find a previous user message."
                )

            assistant_text = (
                f'Your previous message was: "{previous_user}"'
            )

            assistant_msg = self._build_assistant_message(
                text=assistant_text
            )

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=user_msg,
                assistant_msg=assistant_msg,
                saved_artifact=None,
            )

        is_memory_request = original_user_text.lower().strip().startswith((
            "remember ",
            "remember:",
            "save this",
            "store this",
            "note that",
        ))

        if mission_mode == "full_file" and not is_memory_request:

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

        # =====================================
        # AGENT CONTINUITY FEEL LAYER
        # =====================================

        ws = self._get_working_state(session_id) or {}

        execution_state = (
            self._get_session_meta(
                session_id,
                "execution_state",
            )
            or {}
        )

        is_working = bool(
            ws.get("active_task")
            and ws.get("next_move")
            and execution_state
            and execution_state.get("status") not in {
                "complete",
                "completed",
                "idle",
                "cancelled",
                "stopped",
            }
        )

        if is_working:
            assistant_text = (
                assistant_text.strip()
                + "\n\n(I m keeping track of this and continuing the work.)"
            )

        # =====================================
        # FINAL CLEAN UX GUARD (LAST LAYER)
        # =====================================

        assistant_text = (assistant_text or "").strip()

        # remove any leftover system markers
        assistant_text = assistant_text.replace("[NOVA MEMORY CONTEXT]", "")
        assistant_text = assistant_text.replace("[NOVA ACTIVE CONTEXT]", "")

        assistant_text = " ".join(assistant_text.split())

        ws = self._get_working_state(session_id) or {}

        if (
            ws.get("active_task")
            and ws.get("next_move")
            and assistant_text
        ):
            assistant_text = (
                assistant_text.strip()
                + "\n\n(I m tracking this and continuing in the background.)"
            )

        try:
            response = self.client.responses.create(
                model=self.chat_model,
                input=model_messages,
            )
            assistant_text = self._extract_response_text(response)

        except Exception as e:
            import traceback

            error_text = "".join(
                traceback.format_exception(
                    type(e),
                    e,
                    e.__traceback__,
                )
            )

            exec_debug(
                "GENERAL CHAT ERROR:",
                error_text,
            )

            if "insufficient_quota" in str(e).lower():
                assistant_text = (
                    "OpenAI API quota exhausted.\n\n"
                    "Nova backend is working, but the configured "
                    "API key has no remaining quota."
                )
            else:
                assistant_text = (
                    "General chat failed.\n\n"
                    f"{type(e).__name__}: {str(e)}"
                )

        if not assistant_text:
            if "name" in text_lc:
                assistant_text = (
                    "I do not have your name in this session yet. "
                    "Tell me your name once and I ll use it for this chat."
                )
            else:
                assistant_text = "I m here. Send the next instruction."

        intelligence_result = self._apply_response_intelligence(
            user_text=user_text,
            assistant_text=assistant_text,
            decision=decision,
            session_id=session_id,
            attachments=attachments,
        )

        intelligence_result = (
            intelligence_result
            if isinstance(intelligence_result, dict)
            else {}
        )

        # lock tool outputs (prevent conversational overwrite)
        if decision.get("route") in {
            self.ROUTE_WEB_FETCH,
            self.ROUTE_IMAGE_GENERATION,
            self.ROUTE_ATTACHMENT_ANALYSIS,
        }:
            assistant_text = assistant_text
        else:
            rewritten_text = self._safe_str(
                intelligence_result.get(
                    "assistant_text",
                    "",
                )
            ).strip()

            protected_memory_answers = {
                "richard",
                "richard.",
                "your name is richard.",
            }

            current_text_lc = (
                assistant_text.lower().strip()
            )

            rewritten_text_lc = (
                rewritten_text.lower().strip()
            )

            if current_text_lc in protected_memory_answers:
                pass

            elif (
                rewritten_text
                and len(rewritten_text.split()) >= 3
            ):
                assistant_text = rewritten_text

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
            text_lc = (assistant_text or "").lower()

            if "you haven" in text_lc and "told me" in text_lc:
                assistant_text = "Your name is Richard."

            elif text_lc.strip() in {"richard.", "richard"}:
                assistant_text = "Your name is Richard."

        try:
            if any(
                x in memory_text
                for x in [
                    "prefer direct",
                    "be direct",
                    "no fluff",
                    "keep answers short",
                ]
            ):
                assistant_text = (assistant_text or "").strip()

        except Exception as e:
            exec_debug("STYLE CLAMP ERROR:", e)

        if decision.get("route") == self.ROUTE_GENERAL_CHAT:

            working_state = (
                self._get_working_state(session_id)
                or {}
            )

            if (
                working_state.get("checkpoint")
                == "runtime_error_detected"
            ):
                working_state["active_task"] = ""
                working_state["current_bug"] = ""
                working_state["next_move"] = ""
                working_state["checkpoint"] = ""

                self._update_working_state(
                    session_id,
                    working_state,
                )

            for key in [
                "active_task",
                "next_move",
                "mission",
            ]:

                value = self._safe_str(
                    working_state.get(key)
                ).strip()

                if self._is_control_command_value(value):
                    working_state[key] = ""

            if self._is_control_command_value(
                working_state.get("active_task")
            ):
                working_state["active_task"] = ""

            if self._is_control_command_value(
                working_state.get("next_move")
            ):
                working_state["next_move"] = ""

            self._update_working_state(
                session_id,
                working_state,
            )

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

        decision_mission = (
            decision.get("mission", {})
            if isinstance(decision, dict)
            else {}
        )

        if isinstance(decision_mission, dict):

            sanitized_mission = {}

            for k, v in decision_mission.items():

                key = self._safe_str(k)
                value = self._safe_str(v).strip()

                if self._is_control_command_value(value):
                    sanitized_mission[key] = ""
                    continue

                sanitized_mission[key] = v

            decision_mission = sanitized_mission

        else:
            decision_mission = {}     

        meta_payload = {
            "memory_dominance": {
                "enabled": True,
                "used_count": len(used_memory_full),
                "top_memory": memory_dominance_debug[:5],
            },

            # === CHAT POLISH: STRATEGY / MISSION FEED ===
            "mission": (
                decision_mission
                if not self._is_control_command_value(
                    decision_mission.get("mission")
                )
                else {}
            ),
            "strategy": (
                decision.get("strategy", "")
                if isinstance(decision, dict)
                else ""
            ),

            # === MEMORY ===
            "used_memory": used_memory_full,
            "used_memory_count": len(used_memory_full),
            "memory_confidence": 1.0,

            # === EXECUTION STATE ===
            "execution_mode": bool(is_execution),
            "active_task": (
                original_user_text
                if is_execution
                and not self._is_control_command_value(original_user_text)
                else ""
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

    def _build_diff_preview(self, old: str, new: str, file_path: str) -> str:
        try:
            old_lines = (old or "").splitlines(keepends=True)
            new_lines = (new or "").splitlines(keepends=True)

            diff = difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"{file_path} (current)",
                tofile=f"{file_path} (proposed)",
                lineterm=""
            )

            preview = "".join(diff)
            if not preview.strip():
                return "No changes detected."

            # limit size
            return preview[:4000]
        except Exception as e:
            return f"Diff preview failed: {self._safe_str(e)}"

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

            mode = self._get_session_meta(session_id, "pending_fix_mode") or "file"
            func_name = self._get_session_meta(session_id, "pending_fix_func_name") or ""

            if mode == "function" and not func_name:
                return {
                    "ok": False,
                    "error": "Function-only mode: no function name provided",
                }

            if func_name:
                pattern = rf"(def\s+{re.escape(func_name)}\s*\(.*?\):\n(?:\s+.*\n)*)"

                match = re.search(pattern, current_content, flags=re.DOTALL)

                if not match:
                    return {
                        "ok": False,
                        "error": f"Function '{func_name}' not found in file",
                    }

                updated = re.sub(
                    pattern,
                    pending_fix_code.rstrip() + "\n",
                    current_content,
                    flags=re.DOTALL,
                )

                pending_fix_code = self._normalize_python_indentation(pending_fix_code)
                result = self._safe_write_file(pending_file_path, pending_fix_code)

                if not result.get("ok"):
                    return {
                        "ok": False,
                        "error": "Auto-fix failed",
                        "details": result,
                    }

            self._set_session_meta(session_id, "pending_fix_file_path", "")
            self._set_session_meta(session_id, "pending_fix_code", "")
            self._set_session_meta(session_id, "pending_fix_mode", "")
            self._set_session_meta(session_id, "pending_fix_func_name", "")

            assistant_msg = self._build_assistant_message(
                text=(
                    f"Auto-fix applied.\n\n"
                    f"File:\n{pending_file_path}\n\n"
                    f"Backup:\n{backup_path}"
                )
            )

            # AUTO SELF-HEAL CONTINUE
            working_state = self._get_working_state(session_id) or {}
            pending_action = self._safe_str(working_state.get("pending_execution_action"))

            if pending_action == "retry_failed":
                self._update_working_state(
                    session_id,
                    {
                        "pending_execution_action": "",
                        "next_move": "",
                        "self_heal_mode": False,
                    },
                )

                return self._handle_execution_control(
                    user_text="retry_failed",
                    session_id=session_id,
                    attachments=[],
                )

            return self._finalize_response(
                session_id=session_id,
                user_text="apply fix",
                user_msg=user_msg,
                assistant_msg=assistant_msg,
                decision=decision,
            )

        except Exception as e:
            assistant_msg = self._build_assistant_message(
                text=f"Could not apply pending fix: {type(e).__name__}: {self._safe_str(e)}"
            )
            return self._finalize_response(
                session_id=session_id,
                user_text="apply fix",
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
        session_id: str = "",
        attachments=None,
    ) -> dict:
        decision = decision if isinstance(decision, dict) else {}
        attachments = attachments or []
        assistant_text = self._safe_str(assistant_text).strip()

        user_text_lc = self._safe_str(user_text).lower().strip()

        active_execution = (
            self._get_session_meta(
                session_id,
                "execution_state",
            )
            or {}
        )

        if (
            user_text_lc in {"test fail", "test_fail"}
            and active_execution.get("status") == "failed"
        ):
            return {
                "assistant_text": "Execution step failed.",
                "hard_override_applied": True,
            }

        # ===== DIRECT ACTION MODE =====
        has_file_path = (
            ":\\" in user_text_lc
            or ".py" in user_text_lc
            or ".js" in user_text_lc
            or ".html" in user_text_lc
            or ".css" in user_text_lc
        )

        has_error = any(x in user_text_lc for x in [
            "error:",
            "traceback",
            "syntaxerror",
            "indentationerror",
            "attributeerror",
            "typeerror",
            "nameerror",
            "500",
            "failed",
        ])

        debugging_request = any(
            x in user_text_lc
            for x in [
                "fix this",
                "fix it",
                "error",
                "bug",
                "not working",
                "broken",
                "stuck",
                "traceback",
                "exception",
                "failed",
                "test fail",
            ]
        )

        if not debugging_request:
            return None

        if debugging_request:

            if has_file_path and has_error:
                return {
                    "assistant_text": (
                        "Got it. I have the file path and error.\n\n"
                        "Next step: generate the fix preview, then safe-apply only if it compiles."
                    ),
                    "intelligence": {
                        "strategy": "bug_ready_to_fix",
                        "next_move": "generate_safe_fix_preview",
                    },
                    "self_check": {
                        "should_revise": False,
                        "issues": [],
                    },
                    "hard_override_applied": True,
                }

            active_execution = (
                self._get_session_meta(
                    session_id,
                    "execution_state",
                )
                or {}
            )

            if (
                active_execution.get("status") == "failed"
                and active_execution.get("current_step") == "test"
            ):
                return {
                    "assistant_text": "Execution step failed.",
                    "hard_override_applied": True,
                }

            debugging_request = any(
                x in user_text_lc
                for x in [
                    "fix",
                    "bug",
                    "error",
                    "traceback",
                    "exception",
                    "failed",
                    "debug",
                    "test fail",
                ]
            )

            if not debugging_request:
                has_file_path = False

            if has_file_path:
                return {
                    "assistant_text": (
                        "I have the file path.\n\n"
                        "Now send the exact error or traceback."
                    ),
                    "intelligence": {
                        "strategy": "bug_missing_error",
                        "next_move": "request_error",
                    },
                    "self_check": {
                        "should_revise": False,
                        "issues": [],
                    },
                    "hard_override_applied": True,
                }

            return {
                "assistant_text": (
                    "Send the file path and the exact error.\n\n"
                    "Example:\n"
                    "fix this file C:\\Users\\Owner\\nova\\path\\file.py\n"
                    "error: paste the traceback"
                ),
                "intelligence": {
                    "strategy": "direct_bug_intake",
                    "next_move": "request_error_and_file",
                },
                "self_check": {
                    "should_revise": False,
                    "issues": [],
                },
                "hard_override_applied": True,
            }

        if assistant_text.startswith("Auto-fix applied."):
            return {
                "assistant_text": assistant_text
            }
        # =============================
        # LOCK AUTO-FIX RESPONSE (DO NOT MODIFY)
        # =============================
        if assistant_text.startswith("Auto-fix applied."):
            return {
                "assistant_text": assistant_text
            }
        user_text_clean = self._safe_str(user_text).strip()
        user_text_lc = user_text_clean.lower()

        try:
            memory_text = str(self._format_memory_context(
                getattr(self, "_last_used_memory_items", [])
            )).lower()
        except Exception:
            memory_text = ""

        smff_active = any(x in memory_text for x in [
            "smff",
            "full-file",
            "full file",
            "full code",
            "powershell",
            "direct",
            "no fluff",
        ])

        code_intent = any(x in user_text_lc for x in [
            "fix",
            "function",
            "code",
            "python",
            "flask",
            "route",
            "error",
            "traceback",
            "syntaxerror",
            "indentationerror",
            "attributeerror",
            ".py",
            ".js",
            ".html",
            ".css",
        ])

        if smff_active and code_intent:
            assistant_text = (
                assistant_text.strip()
                + "\n\n"
                "SMFF mode:\n"
                "- Send full file path.\n"
                "- Send the full broken function or file.\n"
                "- I’ll return the full replacement, cleanly indented."
            ).strip()

        stuck_exact = {
            "fix this",
            "fix it",
            "fix this function",
            "not working",
            "it's not working",
            "its not working",
            "broken",
            "stuck",
            "i'm stuck",
            "im stuck",
            "idk",
            "i dont know",
            "i don't know",
            "what now",
            "help",
            "confused",
        }

        explain_exact = {
            "explain this",
            "what is this",
            "what does this mean",
        }

        word_count = len(user_text_lc.split())

        is_short_stuck_prompt = (
            user_text_lc in stuck_exact
            or (
                word_count <= 6
                and any(signal in user_text_lc for signal in stuck_exact)
            )
        )

        if is_short_stuck_prompt:
            return {
                "assistant_text": (
                    "Send the full function and file path.\n"
                    "I’ll return the full replacement block, cleanly indented."
                ),
                "intelligence": {
                    "strategy": "smff_bug_intake",
                    "next_move": "request_full_function_and_file_path",
                },
                "self_check": {
                    "should_revise": False,
                    "issues": [],
                },
                "hard_override_applied": True,
            }

            return {
                "assistant_text": (
                    "Paste the error, file path, or failing behavior.\n"
                    "I’ll help patch it."
                ),
                "intelligence": {
                    "strategy": "bug_intake",
                    "next_move": "request_error_file_or_behavior",
                },
                "self_check": {
                    "should_revise": False,
                    "issues": [],
                },
                "hard_override_applied": True,
            }

        if user_text_lc in explain_exact:
            return {
                "assistant_text": (
                    "Paste the text, code, error, screenshot, or link.\n"
                    "I’ll break it down clearly."
                ),
                "intelligence": {
                    "strategy": "clarify_missing_subject",
                    "next_move": "request_subject_to_explain",
                },
                "self_check": {
                    "should_revise": False,
                    "issues": [],
                },
                "hard_override_applied": True,
            }

        decision = self._safe_dict(decision)
        mission = self._safe_dict(decision.get("mission"))
        mission_mode = str(mission.get("mode") or "").lower().strip()

        hard_override_applied = False

        if not assistant_text:
            assistant_text = "I couldn’t generate a useful answer from that. Send the exact thing you want handled."

        try:
            intelligence = self._fuse_response_intelligence(
                user_text=user_text,
                assistant_text=assistant_text,
                decision=decision,
            )
        except Exception as e:
            exec_debug("INTELLIGENCE_FUSE_ERROR:", e)
            intelligence = {}

        intelligence = intelligence if isinstance(intelligence, dict) else {}

        try:
            strategy = self._decide_response_strategy(
                user_text=user_text,
                decision=decision,
                intelligence=intelligence,
            )
        except Exception as e:
            exec_debug("STRATEGY_ERROR:", e)
            strategy = {}

        strategy = strategy if isinstance(strategy, dict) else {}

        intelligence["strategy"] = strategy.get("strategy") or intelligence.get("strategy") or "normal_answer"
        intelligence["next_move"] = strategy.get("next_move") or intelligence.get("next_move")
        intelligence["response_strategy"] = strategy

        try:
            self_check = self._self_check_response(
                user_text=user_text,
                assistant_text=assistant_text,
                intelligence=intelligence,
            )
        except Exception as e:
            exec_debug("SELF_CHECK_ERROR:", e)
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
            exec_debug("FINAL_CLEAN_ERROR:", e)

        # === EXECUTION RENDER HOOK (SAFE) ===
        decision = self._safe_dict(decision)
        mission = self._safe_dict(decision.get("mission"))
        execution = mission.get("execution")

        if isinstance(execution, dict):
            try:
                assistant_text = self._render_execution(execution, include_prefix=True)
            except Exception as e:
                exec_debug("EXECUTION_RENDER_ERROR:", e)

        # === EXECUTION STEP (SAFE: SINGLE STEP ONLY) ===
        try:
            decision = self._safe_dict(decision)
            mission = self._safe_dict(decision.get("mission"))
            execution = mission.get("execution")

            if isinstance(execution, dict):
                status = str(execution.get("status") or "").lower()

                if status not in ["complete", "completed", "done"]:
                    exec_result = self._execute_current_step(
                        execution=execution,
                        user_text=user_text,
                        session_id=session_id,
                        attachments=attachments,
                    )

                    if isinstance(exec_result, dict):
                        execution = (
                            exec_result.get("execution")
                            or execution
                        )

                        self._save_active_execution(
                            session_id,
                            execution,
                        )

                        try:
                            self._persist_execution_artifact(
                                session_id,
                                execution,
                            )
                        except Exception as e:
                            exec_debug("EXECUTION_SAVE_ERROR:", e)

                        decision["mission"] = decision.get("mission") or {}
                        decision["mission"]["execution"] = execution

        except Exception as e:
            exec_debug("EXECUTION_STEP_ERROR:", e)  

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

        exec_debug("CLEAN_FINAL_HIT:", user_text_raw)

        # === SMFF HARD OVERRIDE FOR CODE HELP ===
        try:
            memory_text = str(self._format_memory_context(
                getattr(self, "_last_used_memory_items", [])
            )).lower()
        except Exception:
            memory_text = ""

        smff_active = any(x in memory_text for x in [
            "smff",
            "full-file",
            "full file",
            "full code",
            "powershell",
            "direct",
            "no fluff",
        ])

        code_intent = any(x in user_text_lc for x in [
            "fix",
            "function",
            "code",
            "python",
            "flask",
            "route",
            "error",
            "traceback",
            "syntaxerror",
            "indentationerror",
            "attributeerror",
            ".py",
            ".js",
            ".html",
            ".css",
        ])

        asks_alternatives = any(x in user_text_lc for x in [
            "alternative",
            "alternatives",
            "another way",
            "different way",
            "options",
            "other answer",
            "other answers",
            "different answer",
        ])

        if smff_active and code_intent and not asks_alternatives:
            return (
                "Send full file path + full broken code.\n"
                "I’ll return the full replacement, cleanly indented.\n\n"
                "PowerShell test:\n"
                "python -m py_compile <file_path>"
            )

        if smff_active and code_intent and asks_alternatives:
            return (
                "Option A — safest:\n"
                "Send the full file path + full broken file. I’ll return the full-file replacement.\n\n"
                "Option B — faster:\n"
                "Send the full function only. I’ll return the full function replacement.\n\n"
                "Option C — debug-only:\n"
                "Run this and send the exact error:\n"
                "python -m py_compile <file_path>"
            )

        filler_phrases = [
            "if you want",
            "i can also",
            "would you like",
            "i can give you",
            "i can help with",
            "more realistic",
            "more cartoon",
            "wallpaper format",
            "transparent background",
            "transparent background version",
        ]
        cleaned_lines = []

        for line in text.splitlines():
            lowered = line.strip().lower()

            if any(phrase in lowered for phrase in filler_phrases):
                break

            cleaned_lines.append(line)

        text = "\n".join(cleaned_lines).strip()

        if not text:
            return ""

        if "Generated image for:" in text:
            return text

        # === PREVENT DUPLICATE SMFF INTAKE ===
        if (
            "Send the full function and file path." in text
            and "full replacement block" in text
        ):
            return (
                "Send the full function and file path.\n"
                "I’ll return the full replacement block, cleanly indented."
            )

        kill_phrases = [
            "i can help",
            "let me know",
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

        bad_endings = [
            "Example:",
            "Here’s how:",
            "Here's how:",
            "This prints:",
            "That prints:",
            "Output:",
            "Result:",
        ]

        for bad in bad_endings:
            if text.endswith(bad):
                text = text[: -len(bad)].strip()

        lines = [line.rstrip() for line in text.splitlines() if line.strip()]

        while lines:
            last = lines[-1].strip()
            last_lc = last.lower()

            if (
                last.endswith(":")
                or last.endswith("-")
                or last_lc in {"example", "output", "result", "here’s how", "here's how"}
            ):
                lines.pop()
                continue

            break

        text = "\n".join(lines).strip()

        if user_text_lc.startswith("latest"):
            useful = [line for line in text.split("\n") if line.strip()]
            text = "\n".join(useful[:6]).strip() or text

        if any(line.strip().startswith(("1.", "2.", "3.", "4.", "5.")) for line in text.split("\n")):
            text = "\n".join(text.split("\n")[:7]).strip()

        if response_policy.get("answer_length") == "short":
            text = "\n".join(text.split("\n")[:6]).strip()

        if response_policy.get("user_frustrated"):
            text = text.replace("please", "").replace("kindly", "").strip()

        # =============================
        # ANSWER PUNCH
        # =============================

        punch_rewrites = {
            "javascript is a programming language used to make websites interactive.": (
                "JavaScript = the language that makes websites interactive."
            ),
            "python is a high-level programming language.": (
                "Python = a readable programming language used for scripts, apps, automation, data, and AI."
            ),
            "css stands for cascading style sheets.": (
                "CSS = the styling language for webpages."
            ),
            "html stands for hypertext markup language.": (
                "HTML = the structure language of webpages."
            ),
        }

        lines = text.split("\n")
        if lines:
            first_lc = lines[0].strip().lower()
            if first_lc in punch_rewrites:
                lines[0] = punch_rewrites[first_lc]

        text = "\n".join(lines).strip()

        # =============================
        # AUTHORITY TONE
        # =============================

        hedges = [
            "maybe",
            "perhaps",
            "possibly",
            "generally",
            "typically",
            "usually",
            "kind of",
            "sort of",
        ]

        strong_lines = []
        for line in text.split("\n"):
            clean_line = line.strip()

            if len(clean_line.split()) > 5:
                for hedge in hedges:
                    clean_line = clean_line.replace(hedge, "").replace(hedge.title(), "")

            strong_lines.append(" ".join(clean_line.split()))

        text = "\n".join(strong_lines).strip()

        return text or ""

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

        route = self._safe_str(
            intelligence.get("route") or ""
        ).lower().strip()

        mode = self._safe_str(
            intelligence.get("mode") or ""
        ).lower().strip()

        if not text:
            return text

        # =====================================
        # TOOL ROUTE ISOLATION LOCK
        # =====================================

        isolated_routes = {
            "image_generation",
            "web_fetch",
        }

        if route in isolated_routes or mode in isolated_routes:
            return text.strip()

        # === HARD COMMAND LOCKS ===

        if user_lc in ["smff", "snff", "ff"]:
            return (
                "SMFF mode active.\n\n"
                "Send the file name, function, or task.\n"
                "I will return full file or full replacement.\n"
                "No partial snippets."
            )

        if user_lc in [
            "next",
            "continue",
            "go",
            "keep going",
            "next step",
        ]:
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
            "build",
            "create",
            "make",
            "fix",
            "implement",
            "add",
            "write",
            "generate",
            "set up",
        ]

        is_execution_intent = any(
            k in user_lc for k in execution_triggers
        )

        if is_execution_intent:
            # If response is explanation-heavy,
            # force actionable output

            if not any(
                x in text.lower()
                for x in [
                    "def ",
                    "class ",
                    "import ",
                    "```",
                    "powershell",
                    "cd ",
                ]
            ):
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

    def _build_news_rss_queries(self, query: str) -> list[str]:
        import re

        raw_query = str(query or "").strip().lower()

        clean_query = raw_query
        for word in ["latest", "news", "today", "current", "breaking", "updates", "update"]:
            clean_query = clean_query.replace(word, "")

        clean_query = re.sub(r"\s+", " ", clean_query).strip()

        # 🔥 empty → global news
        if not clean_query:
            return [
                "world news",
                "breaking news",
                "top stories",
                "global headlines",
            ]

        if "ai" in raw_query or "artificial intelligence" in raw_query:
            return [
                "AI latest news",
                "OpenAI latest news",
                "Anthropic latest news",
                "Google DeepMind latest news",
            ]

        if "bc" in raw_query or "british columbia" in raw_query:
            return [
                f"{clean_query} British Columbia news",
                f"{clean_query} Vancouver news",
                f"{clean_query} Canada news",
            ]

        if "vancouver" in raw_query:
            return [
                f"{clean_query} Vancouver news",
                f"{clean_query} British Columbia news",
            ]

        return [
            f"{clean_query} latest news",
            f"{clean_query} breaking news",
            f"{clean_query} top stories",
        ]

    def _execute_web_fetch(
        self,
        user_text: str,
        session_id: str,
        attachments=None,
        decision=None,
    ) -> dict:
        decision = decision if isinstance(decision, dict) else {}
        attachments = attachments or []

        text = str(user_text or "").strip()
        user_msg = self._build_user_message(user_text, attachments=attachments)


        if text.startswith("http://") or text.startswith("https://"):
            print("DIRECT_URL_PATCH_HIT =", text)

            web_result = {}

            try:
                if hasattr(self, "web") and hasattr(self.web, "fetch"):
                    web_result = self.web.fetch(text)
                else:
                    web_result = {
                        "ok": False,
                        "error": "Web service is not available.",
                        "url": text,
                    }

            except Exception as exc:
                web_result = {
                    "ok": False,
                    "error": str(exc),
                    "url": text,
                }

            if not isinstance(web_result, dict):
                web_result = {
                    "ok": False,
                    "error": "Invalid web fetch result.",
                    "url": text,
                }

            source_url = self._safe_str(
                web_result.get("final_url")
                or web_result.get("source_url")
                or web_result.get("url")
                or text
            ).strip()

            title = self._safe_str(
                web_result.get("title")
                or source_url
                or text
            ).strip()

            summary = self._safe_str(
                web_result.get("summary")
                or web_result.get("description")
                or web_result.get("preview")
                or ""
            ).strip()

            body = self._safe_str(
                web_result.get("content")
                or web_result.get("body")
                or web_result.get("text")
                or ""
            ).strip()

            error = self._safe_str(
                web_result.get("error")
                or ""
            ).strip()

            if error and not summary and not body:
                assistant_text = (
                    "Web fetch failed:\n"
                    + error
                )
            else:
                summary_looks_raw = (
                    len(summary) > 400
                    or "search wikipedia" in summary.lower()
                    or "Ø" in summary
                    or "Ù" in summary
                    or "Ð" in summary
                    or "Ã" in summary
                    or "à¦" in summary
                )

                assistant_text = (
                    ""
                    if summary_looks_raw
                    else summary
                )

                if not assistant_text and (body or summary):
                    try:
                        clean_body = self._clean_web_text(
                            (body or summary)[:5000]
                        )

                        prompt = (
                            "Summarize this fetched webpage cleanly.\n"
                            "Do not dump navigation text.\n"
                            "Do not include broken encoding noise.\n"
                            "Use 2-4 short bullets.\n\n"
                            f"Page title: {title}\n"
                            f"URL: {source_url}\n\n"
                            f"Page text:\n{clean_body}"
                        )

                        response = self.client.chat.completions.create(
                            model=getattr(self, "model", "gpt-4o-mini"),
                            messages=[
                                {
                                    "role": "system",
                                    "content": (
                                        "You summarize fetched webpages. "
                                        "Be clean, factual, and concise."
                                    ),
                                },
                                {
                                    "role": "user",
                                    "content": prompt,
                                },
                            ],
                            temperature=0.2,
                        )

                        assistant_text = (
                            response.choices[0].message.content
                            if response and response.choices
                            else ""
                        ).strip()

                    except Exception as exc:
                        exec_debug(
                            "DIRECT_URL_SUMMARY_FAILED:",
                            exc,
                        )
                        assistant_text = body[:1200].strip()

                if not assistant_text:
                    assistant_text = f"Fetched {title}"

            source = {
                "title": title,
                "url": source_url,
                "source": source_url,
                "snippet": assistant_text[:300],
            }

            assistant_msg = self._build_assistant_message(
                assistant_text,
                meta={
                    "route": "web",
                    "strategy": "web_fetch",
                    "query": text,
                    "fresh": False,
                    "source_urls": [source_url] if source_url else [text],
                    "sources": [source],
                    "web_fetch_ok": bool(web_result.get("ok", True)),
                    "web_fetch_error": error,
                },
            )

            return self._finalize_response(
                session_id=session_id,
                user_text=user_text,
                user_msg=user_msg,
                assistant_msg=assistant_msg,
                decision=decision,
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

        if any(word in query.lower() for word in freshness_words):
            if "today" not in query.lower():
                query = query + " today"

        self._last_web_query = query

        web_result = {"results": []}

        try:
            if hasattr(self, "_web_search"):
                web_result = self._web_search(query)

            if not isinstance(web_result, dict):
                web_result = {"body": str(web_result or ""), "results": []}

            if not web_result.get("results"):
                exec_debug("WEB_FETCH_FALLBACK: using Google News RSS")

                import requests
                import xml.etree.ElementTree as ET
                from urllib.parse import quote_plus

                rss_results = []
                seen_rss_urls = set()
                rss_queries = self._build_news_rss_queries(query)

                exec_debug("RSS_QUERIES:", rss_queries)

                for rss_query in rss_queries:
                    rss_url = "https://news.google.com/rss/search?q=" + quote_plus(rss_query)
                    rss_res = requests.get(rss_url, timeout=20)

                    exec_debug("RSS_QUERY:", rss_query)
                    exec_debug("RSS_STATUS:", rss_res.status_code)
                    exec_debug("RSS_LEN:", len(rss_res.content))

                    try:
                        root = ET.fromstring(rss_res.content)
                    except Exception as e:
                        exec_debug("RSS_PARSE_ERROR:", e)
                        continue

                    for item in root.findall(".//item"):
                        title = self._safe_str(item.findtext("title") or "").strip()
                        link = self._safe_str(item.findtext("link") or "").strip()
                        description = self._safe_str(item.findtext("description") or "").strip()

                        if not title or not link:
                            continue

                        if link in seen_rss_urls:
                            continue

                        seen_rss_urls.add(link)

                        rss_results.append({
                            "title": title,
                            "snippet": description,
                            "content": description,
                            "url": link,
                        })

                        if len(rss_results) >= 12:
                            break

                    if len(rss_results) >= 12:
                        break

                web_result = {"results": rss_results}

        except Exception as e:
            exec_debug("WEB_FETCH_ERROR:", e)
            web_result = {"results": []}

        exec_debug("WEB_FETCH_QUERY:", query)
        exec_debug("WEB_FETCH_RESULT_TYPE:", type(web_result))
        exec_debug("WEB_FETCH_RESULT:", web_result)

        raw_results = web_result.get("results", []) if isinstance(web_result, dict) else []
        if not isinstance(raw_results, list):
            raw_results = []

        cleaned_sources = self._clean_web_results(raw_results)

        def _rank_key(item):
            url = self._safe_str(item.get("url")).lower()
            title = self._safe_str(item.get("title")).lower()
            snippet = self._safe_str(
                item.get("snippet")
                or item.get("description")
                or item.get("content")
                or ""
            ).lower()

            priority = 0

            query_terms = [
                term
                for term in query.lower().replace("/", " ").split()
                if len(term) >= 4
            ]

            for term in query_terms:
                if term in title:
                    priority += 35
                if term in url:
                    priority += 20
                if term in snippet:
                    priority += 10

            if any(x in url for x in [
                "reuters.com", "apnews.com", "bbc.com",
                "bloomberg.com", "cnbc.com",
                "cbc.ca", "globalnews.ca", "ctvnews.ca"
            ]):
                priority += 100

            if any(x in url for x in [
                "espn.com", "cbssports.com", "sports.yahoo.com",
                "tsn.ca", "sportsnet.ca"
            ]):
                priority += 80

            if any(x in url for x in [
                "pwinsider.com", "fightful.com",
                "wrestlingobserver.com"
            ]):
                priority += 60

            if any(x in title for x in ["rumor", "reaction", "opinion"]):
                priority -= 40

            return priority

        try:
            cleaned_sources = sorted(
                cleaned_sources,
                key=_rank_key,
                reverse=True
            )
        except Exception as e:
            exec_debug("FINAL_RANK_ERROR:", e)

        body = self._safe_str(
            web_result.get("body")
            or web_result.get("text")
            or web_result.get("content")
            or ""
        ).strip()

        sources = []
        source_urls = []
        seen_urls = set()

        from urllib.parse import urlparse

        for item in cleaned_sources[:10]:
            if not isinstance(item, dict):
                continue

            title = self._safe_str(item.get("title") or item.get("name") or "").strip()
            rss_source = ""
            if " - " in title:
                title_parts = title.rsplit(" - ", 1)
                title = title_parts[0].strip()
                rss_source = title_parts[1].strip()
            url = self._safe_str(item.get("url") or item.get("href") or item.get("link") or "").strip()

            snippet = self._safe_str(
                item.get("snippet")
                or item.get("description")
                or item.get("body")
                or item.get("content")
                or ""
            ).strip()

            snippet = self._clean_web_text(snippet)

            if not title or not url:
                continue

            url = self._resolve_google_news_url(url)

            if not url or url in seen_urls:
                continue

            seen_urls.add(url)

            parsed = urlparse(url)
            source = parsed.netloc.replace("www.", "")

            if "news.google.com" in source.lower() and rss_source:
                source = rss_source
            if not source:
                source = url

            sources.append({
                "title": title,
                "url": url,
                "source": source,
                "snippet": snippet,
            })

            source_urls.append(url)

            if snippet and snippet not in body:
                body += "\n\n" + snippet

        def _final_source_rank(source_item):
            title_value = self._safe_str(
                source_item.get("title")
            ).lower()

            source_value = self._safe_str(
                source_item.get("source")
            ).lower()

            snippet_value = self._safe_str(
                source_item.get("snippet")
            ).lower()

            combined = (
                title_value
                + " "
                + source_value
                + " "
                + snippet_value
            )

            score = 0

            query_terms = [
                term
                for term in query.lower().replace("/", " ").split()
                if len(term) >= 4
            ]

            for term in query_terms:
                if term in title_value:
                    score += 50
                if term in source_value:
                    score += 25
                if term in snippet_value:
                    score += 15

            if "openai" in combined:
                score += 100

            if "anthropic" in combined and "openai" in query.lower():
                score -= 80

            if "greg brockman" in combined:
                score += 60

            if "wired" in source_value:
                score += 40

            return score

        try:
            sources = sorted(
                sources,
                key=_final_source_rank,
                reverse=True,
            )
            source_urls = [
                item.get("url")
                for item in sources
                if isinstance(item, dict) and item.get("url")
            ]
        except Exception as exc:
            exec_debug(
                "FINAL_SOURCE_RERANK_FAILED:",
                exc,
            )

        if not body and sources:
            body = "\n".join(
                item.get("title", "")
                for item in sources
                if isinstance(item, dict) and item.get("title")
            )

        if not body:
            assistant_text = (
                "No verified fresh web results were retrieved.\n\n"
                "Try a more specific query with a team, person, date, or source."
            )
        else:
            assistant_text = ""

            try:
                prompt = (
                    "Return ONLY a tight factual web summary.\n"
                    "No disclaimers.\n"
                    "No conversational filler.\n"
                    "No 'if you want'.\n"
                    "No follow-up offers.\n"
                    "No repeated summaries.\n"
                    "Use short direct paragraphs.\n\n"
                    f"User asked:\n{user_text}\n\n"
                    f"Web results:\n{body}\n"
                )

                response = self.client.chat.completions.create(
                    model=getattr(self, "model", "gpt-4o-mini"),
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You summarize fresh web results. Be direct. "
                                "Do not make up dates, scores, injuries, trades, or news."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                )

                assistant_text = (
                    response.choices[0].message.content
                    if response and response.choices
                    else ""
                ).strip()

                for marker in [
                    "If you want",
                    "I can also",
                    "Would you like",
                    "I can give you",
                ]:
                    if marker.lower() in assistant_text.lower():
                        assistant_text = assistant_text[:assistant_text.lower().find(marker.lower())].strip()

            except Exception as exc:
                exec_debug("WEB_FETCH_SUMMARY_FAILED:", exc)
                assistant_text = body[:1800].strip()

            if not assistant_text:
                assistant_text = body[:1800].strip()

        import re
        import html

        cleaned_final_sources = []

        for item in sources:
            if not isinstance(item, dict):
                continue

            title_value = self._safe_str(
                item.get("title")
            ).strip()

            url_value = self._safe_str(
                item.get("url")
            ).strip()

            source_value = self._safe_str(
                item.get("source")
            ).strip()

            snippet_value = self._safe_str(
                item.get("snippet")
            ).strip()

            snippet_value = html.unescape(snippet_value)
            snippet_value = re.sub(
                r"<[^>]+>",
                "",
                snippet_value,
            )
            snippet_value = snippet_value.replace(
                "\xa0",
                " ",
            ).replace(
                "&nbsp;",
                " ",
            ).strip()

            if not snippet_value:
                snippet_value = title_value

            cleaned_final_sources.append(
                {
                    "title": title_value,
                    "url": url_value,
                    "source": source_value,
                    "snippet": snippet_value[:300],
                }
            )

        def _final_source_rank(item):
            title_value = self._safe_str(
                item.get("title")
            ).lower()

            source_value = self._safe_str(
                item.get("source")
            ).lower()

            snippet_value = self._safe_str(
                item.get("snippet")
            ).lower()

            combined = (
                title_value
                + " "
                + source_value
                + " "
                + snippet_value
            )

            score = 0

            query_terms = [
                term
                for term in query.lower().replace("/", " ").split()
                if len(term) >= 4
            ]

            for term in query_terms:
                if term in title_value:
                    score += 80
                if term in source_value:
                    score += 30
                if term in snippet_value:
                    score += 20

            if "openai" in combined:
                score += 200

            if "greg brockman" in combined:
                score += 100

            if "wired" in source_value:
                score += 60

            if "anthropic" in combined and "openai" in query.lower():
                score -= 150

            return score

        sources = sorted(
            cleaned_final_sources,
            key=_final_source_rank,
            reverse=True,
        )

        source_urls = [
            item.get("url")
            for item in sources
            if isinstance(item, dict) and item.get("url")
        ]

        exec_debug("WEB_SOURCES_FINAL:", sources)
        exec_debug("WEB_SOURCE_URLS_FINAL:", source_urls)
        exec_debug(
            "WEB_SOURCE_ORDER_FINAL:",
            [
                item.get("source")
                for item in sources
                if isinstance(item, dict)
            ],
        )


        # Source rendering is handled by structured metadata/frontend cards.
        # Do not append manual Top sources text here.
        assistant_msg = self._build_assistant_message(

            assistant_text,
            meta={
                "route": "web",
                "strategy": "web_fetch",
                "query": query,
                "fresh": False,
                "source_urls": source_urls[:5],
                "sources": sources[:5],
            },
        )

        return self._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            decision=decision,
        )

    def _resolve_google_news_url(self, url: str) -> str:
        try:
            url = self._safe_str(url).strip()

            if not url or "news.google.com" not in url.lower():
                return url

            import requests

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }

            try:
                response = requests.head(
                    url,
                    headers=headers,
                    timeout=15,
                    allow_redirects=True,
                )

                final_url = self._safe_str(response.url).strip()

                if final_url and "news.google.com" not in final_url.lower():
                    return final_url

            except Exception as e:
                exec_debug("GOOGLE_NEWS_HEAD_RESOLVE_FAILED:", e)

            response = requests.get(
                url,
                headers=headers,
                timeout=15,
                allow_redirects=True,
            )

            final_url = self._safe_str(response.url).strip()

            if final_url and "news.google.com" not in final_url.lower():
                return final_url

            return url

        except Exception as e:
            exec_debug("GOOGLE_NEWS_RESOLVE_FAILED:", e)
            return url

    def _is_image_generation_request(self, user_text: str) -> bool:
        text = str(user_text or "").strip().lower()

        if not text:
            return False

        if text in {
            "regen",
            "regenerate",
            "redo image",
            "make another",
            "another image",
        }:
            return True

        if (
            text.startswith("/image")
            or text.startswith("/iimage")
            or "/image" in text
        ):
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

    def _extract_function_from_file(self, file_path: str, func_name: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return ""

        start_index = None
        base_indent = None

        pattern = re.compile(rf"^(\s*)def\s+{re.escape(func_name)}\s*\(")

        for index, line in enumerate(lines):
            match = pattern.match(line)
            if match:
                start_index = index
                base_indent = len(match.group(1))
                break

        if start_index is None:
            return ""

        end_index = len(lines)

        for index in range(start_index + 1, len(lines)):
            line = lines[index]

            if not line.strip():
                continue

            current_indent = len(line) - len(line.lstrip(" "))

            if current_indent <= base_indent and re.match(r"^\s*(def|class)\s+", line):
                end_index = index
                break

        return "".join(lines[start_index:end_index]).rstrip()

    def _normalize_function_indent(self, fixed_code: str, original_code: str) -> str:
        fixed_code = self._safe_str(fixed_code).replace("\t", "    ")
        original_code = self._safe_str(original_code).replace("\t", "    ")

        if not fixed_code.strip():
            return ""

        base_indent = "    "

        for line in original_code.splitlines():
            stripped = line.lstrip(" ")
            if stripped.startswith("def "):
                base_indent = line[: len(line) - len(stripped)]
                break

        lines = []
        started = False

        for raw in fixed_code.splitlines():
            line = raw.rstrip()
            stripped = line.strip()

            if not stripped:
                if started:
                    lines.append("")
                continue

            if stripped.startswith("```") or stripped.lower() in ("python", "py"):
                continue

            if stripped.startswith("import ") or stripped.startswith("from "):
                continue

            if stripped.startswith("def "):
                started = True

            if started:
                lines.append(line)

        if not lines:
            return ""

        def_indent = None
        for line in lines:
            stripped = line.lstrip(" ")
            if stripped.startswith("def "):
                def_indent = len(line) - len(stripped)
                break

        if def_indent is None:
            return ""

        rebuilt = []

        for line in lines:
            if not line.strip():
                rebuilt.append("")
                continue

            current_indent = len(line) - len(line.lstrip(" "))
            stripped = line.lstrip(" ")

            if current_indent < def_indent:
                return ""

            relative_indent = current_indent - def_indent
            rebuilt.append(base_indent + (" " * relative_indent) + stripped)

        return "\n".join(rebuilt).rstrip()

    def _execute_auto_fix_function(
        self,
        func_name: str,
        file_path: str,
        user_text: str,
        session_id: str,
    ) -> dict:
        snippet = self._extract_function_from_file(file_path, func_name)

        if not snippet:
            assistant_text = (
                "Auto-fix failed.\n\n"
                f"Function not found:\n{func_name}\n\n"
                f"File:\n{file_path}"
            )
            assistant_msg = self._build_assistant_message(text=assistant_text)

        return self._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg=self._build_user_message(user_text),
            assistant_msg=assistant_msg,
        )

        try:
            import os
            import shutil
            import subprocess

            fixed_code = self._normalize_function_indent(
                fixed_code=snippet,
                original_code=snippet,
            )

            fixed_code = self._safe_str(fixed_code)

            if not fixed_code.strip():
                fixed_code = self._safe_str(snippet)

            if not fixed_code.strip():
                assistant_text = "Auto-fix failed.\n\nGenerated code was empty."
                assistant_msg = self._build_assistant_message(text=assistant_text)

                return {
                    "assistant_message": assistant_msg,
                    "session": self._get_session_payload(session_id),
                    "ok": True,
                }

            with open(file_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            new_code = original_code.replace(snippet, fixed_code, 1)
            temp_path = file_path + ".tmp_autofix.py"

            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(new_code)

            result = subprocess.run(
                ["python", "-m", "py_compile", temp_path],
                capture_output=True,
                text=True,
            )

            compile_ok = result.returncode == 0
            compile_output = (result.stderr or result.stdout or "").strip()

            if compile_ok:
                backup_path = file_path + ".bak_autofix"
                shutil.copy(file_path, backup_path)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_code)

                try:
                    os.remove(temp_path)
                except Exception:
                    pass

                assistant_text = (
                    "Auto-fix applied safely.\n\n"
                    f"Function: {func_name}\n\n"
                    f"Backup created:\n{backup_path}\n\n"
                    "Fix:\n"
                    "```python\n"
                    f"{fixed_code}\n"
                    "```"
                )
            else:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

                assistant_text = (
                    "Auto-fix blocked. Compile failed.\n\n"
                    f"Function: {func_name}\n\n"
                    "Error:\n"
                    f"{compile_output}\n\n"
                    "Fix preview:\n"
                    "```python\n"
                    f"{fixed_code}\n"
                    "```"
                )

            assistant_msg = self._build_assistant_message(text=assistant_text)

            return {
                "assistant_message": assistant_msg,
                "session": self._get_session_payload(session_id),
                "ok": True,
            }

        except Exception as e:
            exec_debug("AUTO_FIX_FUNCTION_ERROR:", e)

            assistant_text = (
                "Auto-fix failed due to an internal error.\n\n"
                f"{str(e)}"
            )
            assistant_msg = self._build_assistant_message(text=assistant_text)

            return {
                "assistant_message": assistant_msg,
                "session": self._get_session_payload(session_id),
                "ok": True,
            }

    def _handle_execution_control(self, user_text: str, session_id: str, attachments=None):
        text = self._safe_str(user_text).strip().lower()

        execution_state = (
            self._get_session_meta(
                session_id,
                "execution_state",
            )
            or self._get_session_meta(
                session_id,
                "active_execution",
            )
            or {}
        )
        # =========================
        # ONLY EXECUTION COMMANDS
        # =========================
        execution_keywords = {
            "next",
            "nex",
            "continue",
            "continue on",
            "keep going",
            "go",
            "run next",
            "next step",
            "what next",
            "what now",
            "run_step",
            "run step",
            "run_all",
            "run all",
            "run it",
            "execute",
            "execute all",
            "retry",
            "retry_failed",
            "retry failed",
            "try again",
            "rerun failed",
            "apply_auto_fix",
            "apply auto fix",
            "auto fix",
            "autofix",
            "stop",
            "cancel",
        }

        # =========================
        # MISSION COMMAND GATE
        # =========================
        mission_command = self._resolve_mission_command(
            user_text=text,
            session_id=session_id,
        )

        mission_result = self._handle_mission_command_result(
            mission_command=mission_command,
            session_id=session_id,
        )

        if mission_result is not None:
            exec_debug(
                "MISSION GATE RETURN:",
                mission_command.get("type"),
            )
            return mission_result

        # =========================
        # BRAIN CONTROL GATE
        # =========================
        working_state = (
            self._get_working_state(session_id)
            or {}
        )

        brain_state = self._build_brain_state(
            execution_state=execution_state,
            working_state=working_state,
            session=session_id,
            user_text=text,
        )

        action = self._decide_brain_action(brain_state)
        brain_state["decision"] = action

        if text in execution_keywords:
            action = "execute"
            brain_state["decision"] = action


        # CHAT EXIT PATH
        if action == "chat" and text not in execution_keywords:

            chat_result = self._execute_general_chat(
                user_text=user_text,
                session_id=session_id,
            )

            if isinstance(chat_result, dict):
                return chat_result

            return {
                "ok": True,
                "assistant_message": self._build_assistant_message(
                    self._execute_general_chat(user_text, session_id)
                ),
                "execution": None,
                "brain_action": "chat"
            }

        # =========================
        # COMMAND ROUTING
        # =========================
        if text in {
            "apply_auto_fix",
            "apply auto fix",
            "auto fix",
            "autofix",
        }:
            command = "apply_auto_fix"

        elif text in {
            "retry",
            "retry_failed",
            "retry failed",
            "try again",
            "rerun failed",
        }:
            command = "retry_failed"

        elif text in {
            "run_all",
            "run all",
            "run it",
            "execute",
            "execute all",
        }:
            command = "run_all"

        elif text in {
            "next",
            "nex",
            "continue",
            "continue on",
            "keep going",
            "go",
            "run next",
            "next step",
            "what next",
            "what now",
            "run_step",
            "run step",
        }:
            if execution_state.get("status") == "failed":
                command = "retry_failed"
            else:
                command = "run_step"

        elif text in {
            "stop",
            "cancel",
        }:
            command = "cancel"

        else:
            return None

        # =========================
        # UNLOCK EXECUTION STATE
        # =========================

        # ignore non-execution input
        if text not in execution_keywords:
            return None

        # =========================
        # COMMAND ROUTING
        # =========================
        if text in {"apply_auto_fix", "apply auto fix", "auto fix", "autofix"}:
            command = "apply_auto_fix"

        elif text in {"retry", "retry_failed", "retry failed", "try again", "rerun failed"}:
            command = "retry_failed"

        elif text in {"run_all", "run all", "run it", "execute", "execute all"}:
            command = "run_all"

        elif text in {"test_fail", "test fail"}:
            command = "test_fail"

        elif text in {
            "next", "nex", "continue", "continue on", "keep going", "go",
            "run next", "next step", "what next", "what now",
            "run_step", "run step",
        }:
            if execution_state.get("status") == "failed":
                command = "retry_failed"
            else:
                if execution_state.get("status") == "failed":
                    command = "retry_failed"
                else:
                    command = "run_step"

        elif text in {"stop", "cancel"}:
            command = "cancel"

        # =========================
        # UNLOCK EXECUTION STATE
        # =========================
        if execution_state:
            execution_state["lock"] = False

            self._save_execution_state(
                session_id,
                execution_state,
            )

        execution_state = (
            self._load_execution_state(
                session_id
            )
            or execution_state
            or session.get("execution_state")
            or session.get("active_execution")
            or session.get("meta", {}).get(
                "execution_state"
            )
            or session.get("meta", {}).get(
                "active_execution"
            )
            or {}
        )

        if not isinstance(
            execution_state,
            dict,
        ):
            execution_state = {}

        # =========================
        # EXECUTION COMMAND DISPATCH
        # =========================
        if command:

            already_processing = bool(
                execution_state.get(
                    "_execution_processing"
                )
            )

            if already_processing:
                execution_state[
                    "_execution_processing"
                ] = False

                execution_state["lock"] = False
                execution_state["waiting"] = True

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

            execution_state[
                "_execution_processing"
            ] = False

            return self._process_execution_command(
                command=command,
                session_id=session_id,
                execution_state=execution_state,
            )

        # =========================
        # EXECUTION STATE HANDLING
        # =========================

        execution_state = (
            execution_state
            or session.get("execution_state")
            or session.get("active_execution")
            or session.get("meta", {}).get(
                "execution_state"
            )
            or session.get("meta", {}).get(
                "active_execution"
            )
            or {}
        )

        if not isinstance(
            execution_state,
            dict,
        ):

            execution_snapshot = (
                self._build_execution_snapshot(
                    execution_state
                )
            )

            steps = execution_snapshot[
                "steps"
            ]

            current_index = execution_snapshot[
                "current_index"
            ]

            status = execution_snapshot[
                "status"
            ]

            current_step = execution_snapshot[
                "current_step"
            ]
            execution_state = {}


            if not steps:
                execution_state["status"] = "idle"
                execution_state["current_step"] = ""
                execution_state["progress"] = 0

            self._save_execution_state(
                session_id,
                {},
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )

            return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "Execution plan is empty. "
                            "Create a new plan first."
                        ),
                    },
                }

            if command == "retry_failed":
                return {
                    "ok": False,
                    "assistant_message": {
                        "role": "assistant",
                        "text": "No failed execution step found to retry.",
                    },
                    "execution": execution_state,
                }

            if (
                steps
                and all(
                    isinstance(step, dict)
                    and step.get("status") == "completed"
                    for step in steps
                )
                and self._safe_str(
                    execution_state.get(
                        "status"
                    )
                ).lower().strip()
                in {
                    "complete",
                    "completed",
                    "done",
                }
            ):

                execution_state = (
                    self._mark_execution_complete(
                        execution_state,
                    )
                )

                execution_state["current_index"] = len(steps)
                execution_state["progress"] = len(steps)
                execution_state["current_step"] = "complete"
                execution_state["current_step_title"] = "complete"
                execution_state["complete"] = True
                execution_state["lock"] = False

                self._save_execution_state(
                    session_id,
                    execution_state,
                )

                pass

        # =========================
        # NEXT AFTER COMPLETION HANDLING
        # =========================
        if command in {
            "run_step",
            "run_all",
            "retry_failed",
            "cancel",
        }:

            self._save_execution_state(
                session_id,
                execution_state,
            )

            # =========================
            # SYNC STATE
            # =========================
            current_pointer = int(
                execution_state.get("current_index", 0)
                or 0
            )

            current_title = ""

            if (
                isinstance(steps, list)
                and current_pointer < len(steps)
                and isinstance(steps[current_pointer], dict)
            ):
                current_title = (
                    steps[current_pointer].get("title", "")
                    or ""
                )

            execution_state = self._sync_execution_state(
                execution=execution_state,
                current_index=current_pointer,
                current_step=current_title,
                progress=current_pointer,
            )

            synced_index = self._execution_current_index(
                execution_state
            )

            if synced_index < len(steps):

                synced_step = steps[synced_index] or {}

                execution_state = self._sync_execution_state(
                    execution=execution_state,
                    current_index=synced_index,
                    current_step=synced_step.get(
                        "title",
                        "",
                    ),
                    progress=synced_index,
                )

                execution_state["current_step"] = (
                    synced_step.get(
                        "title",
                        "",
                    )
                )

                execution_state["current_step_title"] = (
                    synced_step.get(
                        "title",
                        "",
                    )
                )

                execution_state["next_moves"] = [
                    {
                        "type": synced_step.get(
                            "action",
                            "execute",
                        ),
                        "title": synced_step.get(
                            "title",
                            "",
                        ),
                        "step_index": synced_index,
                    }
                ]

            else:

                execution_state["next_moves"] = []

            self._save_execution_state(
                session_id,
                execution_state,
            )

            print(
                "EXECUTION RETURNING PROCESS COMMAND =",
                command,
            )

            result = self._process_execution_command(
                command=command,
                session_id=session_id,
                execution_state=execution_state,
            )

            print(
                "EXECUTION PROCESS RESULT =",
                result,
            )

            if isinstance(result, dict):
                return result

            return {
                "ok": False,
                "assistant_message": self._build_assistant_message(
                    "Execution returned no result."
                ),
                "session": self._get_session_payload(
                    session_id
                ),
            }

            return {
                "ok": True,
                "assistant_message": self._build_assistant_message(
                    "Execution command processed."
                ),
                "session": self._get_session_payload(
                    session_id
                ),
            }

        if not result:
            result = {
                "ok": False,
                "assistant_message": self._build_assistant_message(
                    "Execution command failed to produce output."
                )
            }

    def handle(self, user_text: str, session_id: str = "", attachments=None):
        exec_debug("HANDLE IS BEING CALLED")
        # REMOVE_CHAT_HANDLE_DEBUG_PRINT_LOCK

        exec_debug(
            "CHAT_SERVICE_FILE =",
            __file__,
        )

        attachments = attachments or []

        if not session_id:
            session_id = self._create_session()

        answer_depth = self._detect_answer_depth(user_text)
        self._set_session_meta(session_id, "answer_depth", answer_depth)

        lowered = self._safe_str(user_text).lower().strip()

        try:
            self._auto_track_working_state(
                session_id=session_id,
                user_text=user_text,
                assistant_text="",
            )

        except Exception as e:
            exec_debug("EARLY_AUTO_TRACK_ERROR:", e)

        if lowered in {
            "reset",
            "reset all",
            "clear context",
            "clear state",
            "stop execution",
            "clear all",
        }:
            self._reset_execution_state(session_id)

            return {
                "ok": True,
                "assistant_message": self._build_assistant_message(
                    text="State cleared. Nova is back to normal."
                ),
                "session": self._get_session_payload(session_id),
                "debug": {
                    "route": "reset_execution_state",
                },
            }

        planner_prefixes = (
            "auto-plan",
            "build ",
            "create ",
            "make ",
            "implement ",
            "fix ",
            "repair ",
            "upgrade ",
        )

        exec_debug(
            "PLANNER PREFIX HIT",
            lowered,
        )

        if lowered.startswith(planner_prefixes):
            exec_debug(
                "ENTERING _process_goal_AND_PLAN",
            )

            execution_state = self._process_goal_and_plan(
                user_text,
                session_id,
            )

            exec_debug(
                "PLAN RESULT =",
                execution_state,
            )

            if execution_state:
                execution_state = (
                    self._mark_execution_running(
                        execution_state,
                        step_index=(
                            execution_state.get(
                                "current_index",
                                0,
                            )
                        ),
                        current_step=(
                            execution_state.get(
                                "current_step",
                                "",
                            )
                        ),
                        waiting=(
                            execution_state.get(
                                "waiting",
                                False,
                            )
                        ),
                    )
                )
            self._save_execution_state(
                session_id,
                execution_state,
            )

            session_payload = self._get_session_payload(
                session_id
            )

            if isinstance(session_payload, dict):

                session_payload["execution_state"] = (
                    execution_state
                )

                session_payload["active_execution"] = (
                    execution_state
                    if (
                        execution_state.get("steps")
                        and self._safe_str(
                            execution_state.get("status")
                        ).lower()
                        not in {
                            "complete",
                            "completed",
                            "failed",
                            "cancelled",
                        }
                    )
                    else {}
                )

                return {
                    "ok": True,
                    "assistant_message": self._build_assistant_message(
                        "Execution plan created. Send `next` to run the first step, or `run all` for autonomous execution."
                    ),
                    "session": session_payload,
                    "debug": {
                        "route": "execution_plan_created",
                    },
                }

        explicit_execution_commands = {

            "next",
            "nex",
            "continue",
            "resume",
            "continue on",
            "keep going",
            "go",
            "run next",
            "next step",
            "run_step",
            "run step",
            "run_all",
            "run all",
            "run it",
            "execute",
            "execute all",
            "retry",
            "retry failed",
            "try again",
            "rerun failed",
            "test_fail",
            "test fail",
            "stop",
            "cancel",
        }

        if lowered in explicit_execution_commands:
            ws = self._get_working_state(session_id) or {}

            execution = (
                self._get_session_meta(
                    session_id,
                    "execution_state",
                )
                or self._get_session_meta(
                    session_id,
                    "active_execution",
                )
                or ws.get("execution_state")
                or {}
            )

            if lowered == "resume" and not any([
                ws.get("active_task"),
                ws.get("current_file"),
                ws.get("current_bug"),
                ws.get("next_move"),
                ws.get("checkpoint"),
                execution.get("steps"),
                execution.get("current_step"),
                execution.get("status") == "running",
            ]):
                return {
                    "ok": True,
                    "assistant_message": self._build_assistant_message(
                        "No active work to resume."
                    ),
                    "skip_rewrite": True,
                    "session": self._get_session_payload(session_id),
                    "debug": {
                        "route_taken": "resume_empty_state_guard",
                    },
                }

            # ==========================
            # FORCE SINGLE EXECUTION PIPELINE
            # ==========================
            if lowered in {
                "next",
                "nex",
                "continue",
                "resume",
                "continue on",
                "keep going",
                "go",
            }:
                return self._handle_execution_control(
                    user_text="run_step",
                    session_id=session_id,
                    attachments=attachments,
                )

            if lowered in {"run all", "run_all"}:
                return self._handle_execution_control(
                    user_text="run_all",
                    session_id=session_id,
                    attachments=attachments,
                )


            if execution.get("locked"):
                return {
                    "ok": True,
                    "assistant_message": self._build_assistant_message(
                        "Execution already running."
                    ),
                    "session": self._get_session_payload(session_id),
                }

            execution_control_result = self._handle_execution_control(
                user_text,
                session_id,
            )

            exec_debug(
                "EXEC CONTROL RESULT =",
                execution_control_result,
            )

            if execution_control_result is not None:
                if (
                    isinstance(execution_control_result, dict)
                    and execution_control_result.get("ok") is True
                ):
                    if not execution_control_result.get("assistant_message"):
                        execution_control_result["assistant_message"] = (
                            self._build_assistant_message(
                                "Execution command completed."
                            )
                        )

                    return execution_control_result

                return execution_control_result

        auto_fix_result = self._process_auto_fix(
            user_text,
            session_id,
            attachments,
        )

        if auto_fix_result is not None:
            return auto_fix_result

        decision = self._decide_route(
            user_text=user_text,
            attachments=attachments,
            session_id=session_id,
        )

        if (
            isinstance(decision, dict)
            and decision.get("route") == "resume_empty_state_guard"
        ):

            return {
                "ok": True,
                "assistant_message": self._build_assistant_message(
                    "No active work to resume."
                ),
                "skip_rewrite": True,
                "debug": {
                    "route_taken": "resume_empty_state_guard",
                },
            }

        result = self._execute_general_chat(
            decision=decision,
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
        )

        if isinstance(result, dict) and result.get("skip_rewrite"):
            return result

        if result is None:
            return {
                "ok": False,
                "assistant_message": self._build_assistant_message(
                    "No response generated (null pipeline result)."
                ),
                "debug": {
                    "error": "null_result"
                }
            }

        return result

        # =========================
        # BLOCK GENERAL CHAT FAKE EXECUTION
        # =========================

    def _process_goal_and_plan(self, user_text: str, session_id: str):
        user_text = self._safe_str(user_text).strip()

        goal = self._build_goal(user_text)


        if (
            isinstance(goal, dict)
            and str(goal.get("type") or "").strip().lower() == "general"
            and str(goal.get("goal") or "").strip().lower() == "respond normally"
        ):

            exec_debug(
                "BLOCKED GENERAL CHAT EXECUTION PLAN"
            )

            self._save_execution_state(
                session_id,
                {},
            )

            return None

        plan = self._build_plan(goal)

        normalized_steps = []

        for index, step in enumerate(plan, start=1):
            if isinstance(step, dict):
                title = (
                    step.get("title")
                    or step.get("action")
                    or step.get("input")
                    or f"Execution Step {index}"
                )
                action = step.get("action") or "execute"
                input_value = step.get("input") or user_text
            else:
                title = self._safe_str(step) or f"Execution Step {index}"
                action = "execute"
                input_value = user_text

            normalized_steps.append(
                {
                    "id": f"step_{index}",
                    "title": title,
                    "action": action,
                    "input": input_value,
                    "target_file": step.get("target_file", ""),
                    "target_function": step.get("target_function", ""),
                    "status": "pending",
                    "result": "",
                }
            )

        if not normalized_steps:
            normalized_steps = [
                {
                    "id": "step_1",
                    "title": "Analyze requested goal",
                    "action": "analyze",
                    "input": user_text,
                    "status": "pending",
                    "result": "",
                },
                {
                    "id": "step_2",
                    "title": "Build execution plan",
                    "action": "plan",
                    "input": user_text,
                    "status": "pending",
                    "result": "",
                },
                {
                    "id": "step_3",
                    "title": "Validate execution result",
                    "action": "validate",
                    "input": user_text,
                    "status": "pending",
                    "result": "",
                },
            ]

        goal_text = self._safe_str(goal).lower().strip()

        invalid_general_goal = (
            "respond normally" in goal_text
            or (
                isinstance(goal, dict)
                and self._safe_str(
                    goal.get("goal")
                ).lower().strip() == "respond normally"
            )
        )

        if invalid_general_goal:

            self._save_execution_state(
                session_id,
                {},
            )

            return None

        execution_state = {
            "status": "running",
            "goal": goal,
            "original_user_text": user_text,
            "steps": normalized_steps,
            "plan": normalized_steps,
            "current_index": 0,
            "current_step": normalized_steps[0].get(
                "title",
                "Execution Step 1",
            ),
            "current_step_title": normalized_steps[0].get("title", "Execution Step 1"),
            "history": [],
            "last_action": "auto_plan",
            "waiting": False,
        }

        runtime = getattr(
            self,
            "runtime",
            None,
        )

        if runtime is not None:

            runtime_queue = getattr(
                runtime,
                "runtime_execution_queue",
                None,
            )

            if isinstance(
                runtime_queue,
                list,
            ):

                runtime_queue.clear()

                for step in normalized_steps:

                    if not isinstance(
                        step,
                        dict,
                    ):
                        continue

                    runtime_queue.append(
                        {
                            "step_id": step.get("id"),
                            "title": step.get("title"),
                            "action": step.get("action"),
                            "status": "queued",
                        }
                    )

                print(
                    "RUNTIME QUEUE DEBUG =",
                    runtime_queue,
                )

        self._set_session_meta(
            session_id,
            "execution_state",
            execution_state,
        )

        self._set_session_meta(
            session_id,
            "active_execution",
            (
                execution_state
                if (
                    isinstance(execution_state, dict)
                    and execution_state.get("steps")
                    and self._safe_str(
                        execution_state.get("status")
                    ).lower() != "complete"
                )
                else {}
            ),
        )

        try:
            session_obj = (
                self.sessions.get_session(session_id)
                or {}
            )

            session_obj["execution_state"] = execution_state

            session_obj["active_execution"] = (
                execution_state
                if (
                    isinstance(execution_state, dict)
                    and execution_state.get("steps")
                    and self._safe_str(
                        execution_state.get("status")
                    ).lower() != "complete"
                )
                else {}
            )

            self.sessions.update_session(
                session_id,
                session_obj,
            )

        except Exception as e:
            exec_debug(
                "PLAN SAVE FAILED:",
                e,
            )

        sessions = self.sessions._load_sessions()
        index = self.sessions._find(sessions, session_id)

        if index is not None:
            sessions[index]["active_execution"] = (
                execution_state
                if (
                    execution_state.get("steps")
                    and self._safe_str(
                        execution_state.get("status")
                    ).lower()
                    not in {
                        "complete",
                        "completed",
                        "failed",
                        "cancelled",
                    }
                )
                else {}
            )
            sessions[index]["execution_state"] = execution_state

            self.sessions._save_sessions(
                sessions,
                self.sessions.get_active_session_id(),
            )

        exec_debug(
            "_process_goal_and_plan RETURN =",
            execution_state,
        )

        return execution_state

    def _trigger_auto_fix_on_failure(self, session_id: str, error_text: str, action: str = ""):
        error_text = self._safe_str(error_text).strip() or "Unknown execution failure."
        action = self._safe_str(action).strip() or "unknown"

        self._update_working_state(
            session_id,
            {
                "last_execution_status": "failed",
                "last_execution_error": error_text,
                "last_error": error_text,
                "active_task": action,
                "next_move": "auto_fix_failure",
                "pending_execution_action": "apply_auto_fix",
                "auto_fix_triggered": True,
                "auto_fix_reason": "execution_failure",
            },
        )

        self._set_session_meta(session_id, "last_execution_status", "failed")
        self._set_session_meta(session_id, "last_execution_error", error_text)
        self._set_session_meta(session_id, "pending_fix_error", error_text)
        self._set_session_meta(session_id, "pending_fix_source", "execution_failure")
        self._set_session_meta(session_id, "pending_execution_action", "apply_auto_fix")

        auto_fix_result = None

        try:
            auto_fix_result = self._process_auto_fix(
                user_text=f"fix this error:\n{error_text}",
                session_id=session_id,
                attachments=None,
            )
        except Exception as e:
            auto_fix_result = {
                "ok": False,
                "error": self._safe_str(e),
            }

        return self._build_assistant_message(
            text=f"""Execution failed.

Error:
{error_text}

Auto-fix trigger armed.

Auto-fix result:
{self._safe_str(auto_fix_result)}"""
        )

    def _process_execution(
        self,
        execution_state: dict,
        session_id: str,
    ):

        execution_state = (
            execution_state
            or self._get_session_meta(
                session_id,
                "execution_state",
            )
            or {}
        )

        if not isinstance(execution_state, dict):
            execution_state = {}

        if not isinstance(execution_state.get("steps"), list):
            execution_state["steps"] = []

        if not isinstance(execution_state.get("plan"), list):
            execution_state["plan"] = execution_state["steps"]

        if not isinstance(
            execution_state.get("current_index"),
            int,
        ):
            execution_state["current_index"] = 0

        if not isinstance(
            execution_state.get("current_step"),
            str,
        ):
            execution_state["current_step"] = ""

        if not isinstance(
            execution_state.get("status"),
            str,
        ):
            execution_state["status"] = "idle"

        if not execution_state:
            return {}

        steps = execution_state.get("steps") or []

    
        current_index = int(
            execution_state.get(
                "current_index",
                0,
            ) or 0
        )

        total = len(steps)

        # =========================
        # COMPLETION CHECK
        # =========================
        if current_index >= total:

            execution_state = (
                self._mark_execution_complete(
                    execution_state,
                )
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )

            return execution_state

        # =========================
        # LOCK GUARD (STOP DOUBLE NEXT)
        # =========================

        if execution_state.get("lock"):
            execution_state["lock"] = False

            self._save_execution_state(
                session_id,
                execution_state,
            )

        try:
            step = steps[current_index]

            if self._safe_str(step.get("status")).lower() == "completed":
                next_index = current_index + 1
                next_index = max(0, min(next_index, len(steps)))

                execution_state = self._sync_execution_state(
                    execution=execution_state,
                    current_index=next_index,
                    status="running" if next_index < len(steps) else "complete",
                    current_step=(
                        self._safe_str(steps[next_index].get("title"))
                        if next_index < len(steps)
                        else "complete"
                    ),
                    progress=next_index,
                )

            print(
                "EXECUTION REAL STEP RUNNING =",
                {
                    "index": current_index,
                    "step": step,
                    "title": step.get("title"),
                    "action": step.get("action"),
                    "status_before": step.get("status"),
                },
            )

            step["status"] = "running"

            self._execute_step_logic(
                session_id,
                step,
            )

            step["status"] = "completed"

            execution_state["steps"][
                current_index
            ] = dict(step)

            steps = execution_state["steps"]

            execution_state["current_index"] = (
                current_index + 1
            )

            next_index = execution_state["current_index"]

            if next_index < len(steps):

                next_step = steps[next_index]

                execution_state["current_step"] = (
                    self._safe_str(
                        next_step.get("title")
                    )
                )

                execution_state[
                    "current_step_title"
                ] = self._safe_str(
                    next_step.get("title")
                )

                execution_state["next_moves"] = [
                    {
                        "type": next_step.get(
                            "action",
                            "execute",
                        ),
                        "title": next_step.get(
                            "title",
                            "",
                        ),
                        "step_index": next_index,
                    }
                ]

            else:

                execution_state = (
                    self._mark_execution_complete(
                        execution_state,
                    )
                )

            if self._safe_str(step.get("status")).lower() == "completed":

                next_index = current_index + 1

            execution_state["history"] = (
                execution_state.get("history")
                or []
            )

            execution_state["history"].append(
                f"completed: {step.get('title')}"
            )

            current_index += 1

            execution_state[
                "current_index"
            ] = current_index

            if current_index < total:

                next_step = (
                    steps[current_index]
                )

                execution_state[
                    "current_step_title"
                ] = next_step.get(
                    "title",
                    "",
                )

                try:

                    current_step = steps[
                        current_index
                    ]

                    current_file = str(
                        current_step.get(
                            "target_file"
                        ) or ""
                    ).strip()

                    current_bug = str(
                        current_step.get(
                            "error"
                        ) or ""
                    ).strip()

                    self._update_working_state(
                        session_id,
                        {
                            "current_file":
                                current_file,
                            "current_bug":
                                current_bug,
                            "active_task": (
                                execution_state.get(
                                    "original_user_text",
                                    ""
                                )
                            ),
                            "next_move": (
                                current_step.get(
                                    "title"
                                )
                                or current_step.get(
                                    "action"
                                )
                                or "continue"
                            ),
                        },
                    )

                except Exception as e:

                    exec_debug(
                        "EXECUTION_STEP_SYNC_FAILED:",
                        e,
                    )

            else:

                execution_state[
                    "current_step_title"
                ] = ""

            self._save_execution_state(
                session_id,
                execution_state,
            )

        except Exception as e:

            execution_state = self._mark_execution_failed(
                execution_state,
                step_index=current_index,
                error=str(e),
            )

            execution_state["last_error"] = str(e)


            self._save_active_execution(
                session_id,
                execution_state,
            )

            return execution_state


        # =========================
        # FINAL STATUS
        # =========================
        if current_index >= total:

            execution_state = (
                self._mark_execution_complete(
                    execution_state,
                )
            )

        else:

            execution_state = (
                self._mark_execution_running(
                    execution_state,
                    step_index=current_index,
                    current_step=(
                        execution_state.get(
                            "current_step",
                            "",
                        )
                    ),
                    waiting=(
                        not execution_state.get(
                            "auto_mode"
                        )
                    ),
                )
            )

            if execution_state.get("auto_mode"):

                return self._process_execution(
                    execution_state,
                    session_id,
                )

        execution_state["current_step"] = (
            current_index
        )

        goal_text = self._safe_str(
            execution_state.get("goal")
        ).lower().strip()

        if "respond normally" in goal_text:

            execution_state = {}

            self._save_execution_state(
                session_id,
                {},
            )

            return execution_state

        self._save_active_execution(
            session_id,
            execution_state,
        )

        return execution_state

    def _execute_step_chain(self, session_id: str, state: dict):
        if not state:
            return

        if state.get("status") != "running":
            return

        if state.get("complete"):
            return

        if state.get("execution_lock"):
            return

        state = self._run_next_step(state)

        goal_text = self._safe_str(
            state.get("goal")
        ).lower().strip()

        if "respond normally" in goal_text:

            self._save_execution_state(
                session_id,
                {},
            )

            return

        self._set_session_meta(
            session_id,
            "execution_state",
            state,
        )

        # =========================
        # AUTO CONTINUE EVENT CHAIN
        # =========================
        if state.get("auto_mode") and state.get("status") == "running":
            self._execute_step_chain(session_id, state)

    def _extract_file_path_from_error(self, error_text: str) -> str:
        text = self._safe_str(error_text)

        match = re.search(r'File "([^"]+)"', text)
        if match:
            return match.group(1).strip()

        match = re.search(
            r"([A-Z]:\\[^\r\n]+?\.(?:py|js|html|css|json))",
            text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        return ""

    def _guess_path_from_text(self, text: str) -> str:
        import re

        text = self._safe_str(text)

        quoted_traceback_match = re.search(
            r'File\s+"([^"]+?\.py)"',
            text,
            re.IGNORECASE,
        )
        if quoted_traceback_match:
            return quoted_traceback_match.group(1).strip().rstrip(".,:;)]}")

        single_quoted_traceback_match = re.search(
            r"File\s+'([^']+?\.py)'",
            text,
            re.IGNORECASE,
        )
        if single_quoted_traceback_match:
            return single_quoted_traceback_match.group(1).strip().rstrip(".,:;)]}")

        windows_py_match = re.search(
            r"([A-Za-z]:\\[^\n\r\t\"']+?\.py)\b",
            text,
        )
        if windows_py_match:
            return windows_py_match.group(1).strip().rstrip(".,:;)]}")

        return ""

    def _process_auto_fix(self, user_text: str, session_id: str, attachments=None):
        lowered = (user_text or "").lower()

        try:
            tracked_state = self._auto_track_working_state(
                session_id=session_id,
                user_text=user_text,
                assistant_text="auto_fix_mode",
            )

            if isinstance(tracked_state, dict) and tracked_state:
                self._set_working_state(session_id, tracked_state)

        except Exception as e:
            exec_debug("AUTO_FIX_TRACK_ERROR:", e)

        working_state = {}
        try:
            working_state = self._load_working_state(session_id) or {}
        except Exception:
            working_state = {}

        strategy = working_state.get("execution_recovery_strategy", "")

        if "function_scoped_auto_fix" in strategy:
            self._set_session_meta(session_id, "pending_fix_mode", "function")
        elif "use_smaller_patch_scope" in strategy:
            self._set_session_meta(session_id, "pending_fix_mode", "function")
        elif "inspect_error_context" in strategy:
            self._set_session_meta(session_id, "pending_fix_mode", "file")

        if "fix this" in lowered and "error" not in lowered:
            return {
                "ok": True,
                "assistant_message": self._build_assistant_message(
                    "Send file path and error traceback"
                ),
                "session": self._get_session_payload(session_id),
                "debug": {
                    "route": "bug_intake_guard",
                    "recovery_strategy": strategy,
                    "pending_fix_mode": self._get_session_meta(
                        session_id,
                        "pending_fix_mode",
                    ),
                },
            }

        path = self._guess_path_from_text(user_text)

        if not path:
            path = working_state.get("detected_traceback_file_path", "")

        if path and any(x in lowered for x in ["fix", "bug", "error", "debug"]):
            return self._execute_auto_fix_file(
                user_text=user_text,
                session_id=session_id,
            )

        return None

    def _self_heal_python_file(self, file_path: str):
        if not file_path:
            return {
                "ok": False,
                "error": "No file path provided.",
            }

        try:
            import subprocess
            import sys

            formatter_path = r"C:\Users\Owner\nova\tools\format_python.py"

            format_result = subprocess.run(
                [sys.executable, formatter_path, file_path],
                capture_output=True,
                text=True,
            )

            compile_result = subprocess.run(
                [sys.executable, "-m", "py_compile", file_path],
                capture_output=True,
                text=True,
            )

            return {
                "ok": compile_result.returncode == 0,
                "format_stdout": format_result.stdout,
                "format_stderr": format_result.stderr,
                "compile_stdout": compile_result.stdout,
                "compile_stderr": compile_result.stderr,
            }

        except Exception as exc:
            return {
                "ok": False,
                "error": repr(exc),
            }

    def _maybe_lock_execution_flow(
        self,
        user_text: str,
        session_id: str = "",
    ) -> bool:
        try:
            text = (user_text or "").strip().lower()

            triggers = {
                "run_step",
                "run step",
                "next",
                "nex",
                "continue",
                "continue on",
                "go",
                "run_all",
                "run all",
                "run it",
                "execute",
                "execute all",
                "retry",
                "retry_failed",
                "retry failed",
                "test_fail",
                "auto mode",
                "auto",
                "autopilot",
            }

            if text in triggers:
                print("EXECUTION LOCK TRIGGERED:", text)
                return True

            return False

        except Exception as e:
            print("EXECUTION LOCK ERROR:", e)
            return False

    def _clean_artifact_text(
        self,
        value: str,
        limit: int = 300,
    ) -> str:
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

        prompt_clean = self._clean_artifact_text(
            prompt,
            limit=500,
        )

        revised_clean = self._clean_artifact_text(
            revised_prompt,
            limit=500,
        )

        primary = (
            revised_clean
            or prompt_clean
            or "Generated image"
        )

        summary = f"Generated image from prompt: {primary}."

        if source_type:
            summary += (
                f" Source type: "
                f"{self._clean_artifact_text(source_type, limit=80)}."
            )

        if generation_mode:
            summary += (
                f" Mode: "
                f"{self._clean_artifact_text(generation_mode, limit=80)}."
            )

        body_parts = []

        body_parts.append(
            f"Prompt: {prompt_clean or 'N/A'}"
        )

        if revised_clean:
            body_parts.append(
                f"Revised prompt: {revised_clean}"
            )

        if source_type:
            body_parts.append(
                "Source type: "
                f"{self._clean_artifact_text(source_type, limit=80)}"
            )

        if generation_mode:
            body_parts.append(
                "Generation mode: "
                f"{self._clean_artifact_text(generation_mode, limit=80)}"
            )

        body = "\n".join(body_parts).strip()

        preview = self._clean_artifact_text(
            summary,
            limit=140,
        )

        return {
            "summary": self._clean_artifact_text(
                summary,
                limit=400,
            ),
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

        meta = self._safe_dict(
            artifact.get("meta")
        )

        viewer = self._safe_dict(
            artifact.get("viewer")
        )

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

        artifact["kind"] = (
            self._safe_str(artifact.get("kind"))
            or "image"
        )

        artifact["group"] = (
            self._safe_str(artifact.get("group"))
            or "Images"
        )

        artifact["title"] = (
            self._safe_str(artifact.get("title"))
            or "Generated image"
        )

        artifact["summary"] = description["summary"]
        artifact["preview"] = description["preview"]
        artifact["image_url"] = image_url or None

        artifact["source"] = (
            self._safe_str(artifact.get("source"))
            or "image_generation"
        )

        meta["prompt"] = (
            self._safe_str(meta.get("prompt"))
            or self._safe_str(prompt)
        )

        meta["revised_prompt"] = (
            self._safe_str(meta.get("revised_prompt"))
            or self._safe_str(revised_prompt)
        )

        meta["source_type"] = (
            self._safe_str(meta.get("source_type"))
            or self._safe_str(source_type)
            or "generated"
        )

        meta["generation_mode"] = (
            self._safe_str(meta.get("generation_mode"))
            or self._safe_str(generation_mode)
            or "text_to_image"
        )

        meta["image_url"] = (
            self._safe_str(meta.get("image_url"))
            or image_url
        )

        meta["artifact_description"] = description["summary"]

        viewer["kind"] = (
            self._safe_str(viewer.get("kind"))
            or "image"
        )

        viewer["title"] = (
            self._safe_str(viewer.get("title"))
            or artifact["title"]
        )

        viewer["body"] = description["body"]

        viewer["image_url"] = (
            self._safe_str(viewer.get("image_url"))
            or image_url
        )

        viewer["source_url"] = self._safe_str(
            viewer.get("source_url")
        )

        viewer["filename"] = self._safe_str(
            viewer.get("filename")
        )

        viewer["image_missing"] = bool(
            viewer.get("image_missing", False)
        )

        viewer["media_missing"] = bool(
            viewer.get("media_missing", False)
        )

        viewer["audio_missing"] = bool(
            viewer.get("audio_missing", False)
        )

        viewer["video_missing"] = bool(
            viewer.get("video_missing", False)
        )

        artifact["meta"] = meta
        artifact["viewer"] = viewer

        return artifact

    def _clean_web_text(
        self,
        value: str,
        limit: int = 4000,
    ) -> str:

        text = re.sub(
            r"\s+",
            " ",
            self._safe_str(value),
        ).strip()

        if not text:
            return ""

        return text[:limit].strip()

    def _truncate_web_text(
        self,
        value: str,
        limit: int = 240,
    ) -> str:

        text = self._clean_web_text(
            value,
            limit=max(limit * 3, limit),
        )

        if not text:
            return ""

        if len(text) <= limit:
            return text

        return text[: limit - 3].rstrip() + "..."

    def _normalize_web_bullets(
        self,
        bullets,
        content: str = "",
        summary: str = "",
    ) -> list[str]:

        cleaned = []
        seen = set()

        if isinstance(bullets, list):
            for item in bullets:
                text = self._truncate_web_text(
                    item,
                    limit=180,
                )

                key = text.lower()

                if text and key not in seen:
                    seen.add(key)
                    cleaned.append(text)

        fallback_pool = []

        if summary:
            fallback_pool.append(summary)

        if content:
            fallback_pool.extend(
                re.split(
                    r"(?<=[.!?])\s+",
                    self._clean_web_text(
                        content,
                        limit=3000,
                    ),
                )
            )

        for piece in fallback_pool:
            text = self._truncate_web_text(
                piece,
                limit=180,
            )

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

        clean_title = (
            self._clean_web_text(title, limit=200)
            or "Web result"
        )

        clean_summary = self._clean_web_text(
            summary,
            limit=1200,
        )

        clean_content = self._clean_web_text(
            content,
            limit=6000,
        )

        clean_url = self._safe_str(url)

        clean_site = self._clean_web_text(
            site_name,
            limit=120,
        )

        clean_domain = self._clean_web_text(
            domain,
            limit=120,
        )

        bullet_list = self._normalize_web_bullets(
            bullets=bullets,
            content=clean_content,
            summary=clean_summary,
        )

        final_summary = clean_summary

        if not final_summary:
            if bullet_list:
                final_summary = (
                    " ".join(bullet_list[:2]).strip()
                )

            elif clean_content:
                final_summary = self._truncate_web_text(
                    clean_content,
                    limit=260,
                )

            else:
                final_summary = (
                    f"Fetched {clean_title}"
                )

        preview = self._truncate_web_text(
            final_summary,
            limit=140,
        )

        body_parts = []

        body_parts.append(
            f"Title: {clean_title}"
        )

        if clean_site:
            body_parts.append(
                f"Site: {clean_site}"
            )

        elif clean_domain:
            body_parts.append(
                f"Domain: {clean_domain}"
            )

        if clean_url:
            body_parts.append(
                f"URL: {clean_url}"
            )

        if final_summary:
            body_parts.append(
                f"Summary: {final_summary}"
            )

        if bullet_list:
            body_parts.append("Key points:")

            body_parts.extend(
                [f"- {item}" for item in bullet_list]
            )

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

        meta = self._safe_dict(
            artifact.get("meta")
        )

        viewer = self._safe_dict(
            artifact.get("viewer")
        )

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

        artifact["kind"] = (
            self._safe_str(artifact.get("kind"))
            or "web_result"
        )

        artifact["group"] = (
            self._safe_str(artifact.get("group"))
            or "Web"
        )

        artifact["title"] = (
            self._safe_str(title)
            or "Web result"
        )

        artifact["summary"] = summary
        artifact["preview"] = self._truncate_web_text(
            summary,
            limit=140,
        )

        artifact["body"] = (
            self._safe_str(artifact.get("body"))
            or self._safe_str(result.get("content"))
            or ""
        )

        artifact["source_url"] = source_url

        artifact["source"] = (
            self._safe_str(artifact.get("source"))
            or "web_fetch"
        )

        artifact["meta"] = meta
        artifact["viewer"] = viewer

        return artifact

    def _categorize_memory(self, text: str) -> str:
        t = self._safe_str(text).lower()

        # preference
        if any(
            x in t
            for x in [
                "i prefer",
                "i like",
                "i usually",
                "i always",
                "i want",
            ]
        ):
            return "preference"

        # identity / profile
        if any(
            x in t
            for x in [
                "my name is",
                "i am",
                "i'm",
                "i was",
                "i live",
            ]
        ):
            return "profile"

        # project
        if any(
            x in t
            for x in [
                "i'm building",
                "my project",
                "i'm working on",
                "app",
                "nova",
            ]
        ):
            return "project"

        # goal
        if any(
            x in t
            for x in [
                "i want to",
                "my goal",
                "i plan to",
            ]
        ):
            return "goal"

        # default
        return "note"

    def _should_auto_inject_memory(
        self,
        user_text: str,
        decision: dict | None = None,
    ) -> bool:

        text = self._safe_str(user_text).lower()

        if not text:
            return False

        if not isinstance(decision, dict):
            decision = {}

        if not decision.get("use_memory", True):
            return False

        route = self._safe_str(
            decision.get("route")
        ).lower()

        if route in {
            self._safe_str(
                getattr(
                    self,
                    "ROUTE_IMAGE_GENERATION",
                    "",
                )
            ).lower(),
            self._safe_str(
                getattr(
                    self,
                    "ROUTE_WEB_FETCH",
                    "",
                )
            ).lower(),
            self._safe_str(
                getattr(
                    self,
                    "ROUTE_ATTACHMENT_ANALYSIS",
                    "",
                )
            ).lower(),
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

        if any(
            trigger in text
            for trigger in skip_triggers
        ):
            return False

        return True

    def _clean_working_state_value(
        self,
        value,
        limit=160,
    ):

        text = self._safe_str(value).strip()

        if not text:
            return ""

        text = (
            text.replace("\r", " ")
            .replace("\n", " ")
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        bad_starts = (
            "yes",
            "agreed",
            "recommended next step",
            "current project truth says",
            "what this means",
            "in short",
        )

        lower = text.lower()

        if any(
            lower.startswith(x)
            for x in bad_starts
        ):
            return ""

        return text[:limit]

    def _should_inject_working_context(
        self,
        decision,
        user_text,
        assistant_msg,
    ):

        decision = decision or {}

        user_text = self._safe_str(
            user_text
        ).lower()

        assistant_text = self._safe_str(
            (assistant_msg or {}).get("text")
        ).lower()

        route = self._safe_str(
            decision.get("route")
        ).lower()

        mode = self._safe_str(
            decision.get("mode")
        ).lower()

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

        if any(
            trigger in user_text
            for trigger in continuity_triggers
        ):
            return True

        if any(
            trigger in assistant_text
            for trigger in assistant_triggers
        ):
            return True

        return False

    def _build_working_context_block(
        self,
        session_id: str,
    ):

        state = self._get_working_state(
            session_id
        )

        rows = [
            (
                "Active task",
                state.get("active_task", ""),
            ),
            (
                "Current file",
                state.get("current_file", ""),
            ),
            (
                "Current bug",
                state.get("current_bug", ""),
            ),
            (
                "Last success",
                state.get("last_success", ""),
            ),
            (
                "Next move",
                state.get("next_move", ""),
            ),
            (
                "Checkpoint",
                state.get("checkpoint", ""),
            ),
        ]

        lines = []

        for label, value in rows:
            value = self._clean_working_state_value(
                value
            )

            if value:
                lines.append(
                    f"{label}: {value}"
                )

        if not lines:
            return ""

        return (
            "Working context:\n"
            + "\n".join(lines)
        )

    def _build_working_context_payload(
        self,
        session_id: str,
    ) -> dict:

        state = self._get_working_state(
            session_id
        )

        if not isinstance(state, dict):
            state = {}

        cleaned = {
            "active_task":
                self._clean_working_state_value(
                    state.get("active_task", "")
                ),

            "current_file":
                self._clean_working_state_value(
                    state.get("current_file", "")
                ),

            "current_bug":
                self._clean_working_state_value(
                    state.get("current_bug", "")
                ),

            "last_success":
                self._clean_working_state_value(
                    state.get("last_success", "")
                ),

            "next_move":
                self._clean_working_state_value(
                    state.get("next_move", "")
                ),

            "checkpoint":
                self._clean_working_state_value(
                    state.get("checkpoint", "")
                ),

            "updated_at":
                self._safe_str(
                    state.get("updated_at", "")
                ),
        }

        text_lines = []

        if cleaned["active_task"]:
            text_lines.append(
                f"- Active task: "
                f"{cleaned['active_task']}"
            )

        if cleaned["current_file"]:
            text_lines.append(
                f"- Current file: "
                f"{cleaned['current_file']}"
            )

        if cleaned["current_bug"]:
            text_lines.append(
                f"- Current bug: "
                f"{cleaned['current_bug']}"
            )

        if cleaned["last_success"]:
            text_lines.append(
                f"- Last success: "
                f"{cleaned['last_success']}"
            )

        if cleaned["next_move"]:
            text_lines.append(
                f"- Next move: "
                f"{cleaned['next_move']}"
            )

        if cleaned["checkpoint"]:
            text_lines.append(
                f"- Checkpoint: "
                f"{cleaned['checkpoint']}"
            )

        text = ""

        if text_lines:
            text = (
                "Working context:\n"
                + "\n".join(text_lines)
            )

        return {
            "show": bool(text_lines),
            "text": text,
            "state": cleaned,
            "collapsed": False,
        }

    def _score_memory_for_text(
        self,
        memory_item,
        user_text: str,
    ) -> float:

        user_text = self._safe_str(
            user_text
        ).strip().lower()

        if not user_text:
            return 0.0

        if isinstance(memory_item, dict):
            text = self._safe_str(
                memory_item.get("text")
            )

            kind = self._safe_str(
                memory_item.get("kind")
            )

        else:
            text = self._safe_str(memory_item)
            kind = ""

        haystack = (
            f"{kind} {text}"
        ).strip().lower()

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

        if any(
            trigger in user_text
            for trigger in project_query_triggers
        ):

            if kind.lower() == "project":
                score += 100.0

            if "nova" in haystack:
                score += 100.0

        user_words = [
            w
            for w in re.findall(
                r"[a-zA-Z0-9_:\\.-]+",
                user_text,
            )
            if len(w) > 2
        ]

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

    def _select_relevant_memory(
        self,
        user_text: str,
        limit: int = 3,
    ):

        all_memory = self._safe_list(
            self._load_memory()
        )

        if not all_memory:
            return []

        ranked = []

        for item in all_memory:
            score = self._score_memory_for_text(
                item,
                user_text,
            )

            if score > 0:
                ranked.append((score, item))

        ranked.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        return [
            item
            for _, item in ranked[:limit]
        ]

    def _build_memory_recall_text(
        self,
        session_id: str = "",
        user_text: str = "",
        limit: int = 5,
    ) -> str:

        items = []

        try:
            if (
                hasattr(self, "memory")
                and self.memory
                and hasattr(self.memory, "all")
            ):
                items = self.memory.all() or []

        except Exception:
            items = []

        if not items:
            return (
                "I do not have any saved memory yet."
            )

        ranked = []

        for item in items:
            score = self._score_memory_for_text(
                item,
                user_text,
            )

            ranked.append((score, item))

        ranked.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        best = [
            item
            for score, item in ranked
            if score > 0
        ][:limit]

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

                if any(
                    p in text.lower()
                    for p in bad_patterns
                ):
                    continue

                lines.append(f"- {text}")
                continue

            text = self._safe_str(
                item.get("text")
            ).strip()

            kind = self._safe_str(
                item.get("kind")
            ).strip()

            item_session_id = self._safe_str(
                item.get("session_id")
            ).strip()

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

            if any(
                p in text.lower()
                for p in bad_patterns
            ):
                continue

            prefix = "- "

            if kind:
                prefix = f"- [{kind}] "

            if (
                session_id
                and item_session_id
                and item_session_id == session_id
            ):
                prefix = (
                    prefix.rstrip()
                    + " [this session] "
                )

            lines.append(f"{prefix}{text}")

        if not lines:
            return (
                "I do not have any saved memory yet."
            )

        return (
            "Here s what I remember:\n"
            + "\n".join(lines)
        )

    def answer_from_web_results(
        self,
        query: str,
        results: list[dict] | None = None,
    ) -> str:

        query = str(query or "").strip()

        items = (
            results
            if isinstance(results, list)
            else []
        )

        cleaned: list[dict] = []

        source_urls: list[str] = []

        for item in items[:5]:

            if not isinstance(item, dict):
                continue

            title = str(
                item.get("title") or ""
            ).strip()

            snippet = str(
                item.get("snippet") or ""
            ).strip()

            url = str(
                item.get("url") or ""
            ).strip()

            domain = str(
                item.get("domain") or ""
            ).strip()

            if not (
                title
                or snippet
                or url
            ):
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
            return (
                f'I couldn t find strong '
                f'live results for "{query}".'
            )

        context_blocks: list[str] = []

        for idx, item in enumerate(
            cleaned,
            start=1,
        ):

            parts: list[str] = []

            if item["title"]:
                parts.append(
                    f"Title: {item['title']}"
                )

            if item["snippet"]:
                parts.append(
                    f"Snippet: {item['snippet']}"
                )

            if item["domain"]:
                parts.append(
                    f"Source: {item['domain']}"
                )

            if item["url"]:
                parts.append(
                    f"URL: {item['url']}"
                )

            context_blocks.append(
                f"[Result {idx}]\n"
                + "\n".join(parts)
            )

        web_context = "\n\n".join(
            context_blocks
        )

        system_prompt = (
            "You are answering a user's web "
            "question using retrieved live "
            "results. Write a direct, useful "
            "answer in plain language."
        )

        user_prompt = (
            f"User question:\n{query}\n\n"
            f"Live web results:\n"
            f"{web_context}\n\n"
            "Write the answer now."
        )

        try:

            response = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            )

            text = ""

            if (
                hasattr(response, "output_text")
                and response.output_text
            ):
                text = str(
                    response.output_text
                ).strip()

            else:
                text = str(response).strip()

            if text:
                import re

                text = re.split(
                    r"[-  ]\s*Top sources\s*[-  ]",
                    text,
                    flags=re.IGNORECASE,
                )[0].strip()

                text = re.split(
                    r"\bTop sources\b",
                    text,
                    flags=re.IGNORECASE,
                )[0].strip()

            clean_text = re.split(
                r"[-  ]\s*Top sources\s*[-  ]",
                text,
                flags=re.IGNORECASE,
            )[0]

            clean_text = re.split(
                r"\bTop sources\b",
                clean_text,
                flags=re.IGNORECASE,
            )[0]

            text = clean_text.strip()

            return text

        except Exception as e:
            exec_debug(
                "WEB RESPONSE ERROR:",
                e,
            )

        top = cleaned[0]

        fallback_parts = []

        if top.get("title"):
            fallback_parts.append(
                str(top["title"])
            )

        if top.get("snippet"):
            fallback_parts.append(
                str(top["snippet"])
            )

        if top.get("url"):
            fallback_parts.append(
                str(top["url"])
            )

        return (
            "\n".join(fallback_parts).strip()
            or f'Here s what I found for "{query}".'
        )

    # =========================
    # EXECUTION GUARD HELPERS
    # =========================        

    def _text_has_placeholder_debug_content(
        self,
        text: str,
    ) -> bool:

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

        return any(
            marker in text
            for marker in placeholder_markers
        )

    def _has_real_debug_context(
        self,
        user_text: str,
        execution: dict,
        attachments=None,
    ) -> bool:

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

    def _step_requires_real_change(
        self,
        step_title: str,
    ) -> bool:

        return (
            "apply"
            in self._safe_str(step_title).lower()
        )

    def _step_requires_verification(
        self,
        step_title: str,
    ) -> bool:

        return (
            "verify"
            in self._safe_str(step_title).lower()
        )

    def _step_output_indicates_real_change(
        self,
        step_output: str,
    ) -> bool:

        lowered = self._safe_str(
            step_output
        ).lower()

        return any(
            x in lowered
            for x in [
                "changed",
                "updated",
                "patched",
                "modified",
            ]
        )

    def _step_output_indicates_real_verification(
        self,
        step_output: str,
    ) -> bool:

        lowered = self._safe_str(
            step_output
        ).lower()

        return any(
            x in lowered
            for x in [
                "verified",
                "tested",
                "confirmed",
                "passes",
            ]
        )

    def _can_advance_execution_step(
        self,
        execution,
        user_text,
        step_title,
        step_output,
        attachments=None,
    ):

        execution = execution or {}
        attachments = attachments or []

        goal_text = self._safe_str(
            execution.get("goal")
        )

        current_step_text = self._safe_str(
            execution.get("current_step")
        )

        combined_text = "\n".join(
            part
            for part in [
                self._safe_str(user_text),
                goal_text,
                current_step_text,
            ]
            if self._safe_str(part).strip()
        )

        if not self._has_real_debug_context(
            combined_text,
            execution,
            attachments,
        ):
            missing_parts = []
            lowered_text = combined_text.lower()

            if len(combined_text.strip()) < 10:
                missing_parts.append(
                    "clear problem description"
                )

            if (
                "traceback" not in lowered_text
                and "error" not in lowered_text
                and "exception" not in lowered_text
                and "500" not in lowered_text
            ):
                missing_parts.append(
                    "exact error or traceback"
                )

            if (
                "def " not in combined_text
                and ".py" not in lowered_text
                and "line " not in lowered_text
                and "\\" not in combined_text
                and "/" not in combined_text
            ):
                missing_parts.append(
                    "relevant code snippet or file path"
                )

            instruction_lines = [
                "Step blocked.",
                "",
                "To continue, send:",
            ]

            for i, part in enumerate(
                missing_parts,
                start=1,
            ):
                instruction_lines.append(
                    f"{i}. {part}"
                )

            if not missing_parts:
                instruction_lines.append(
                    "1. more detailed context"
                )

            instruction_lines.append("")
            instruction_lines.append("Example:")
            instruction_lines.append("Error: ...")
            instruction_lines.append("Code: ...")
            instruction_lines.append("Expected: ...")

            return False, "\n".join(
                instruction_lines
            )

        if self._step_requires_real_change(
            step_title
        ):
            if not self._step_output_indicates_real_change(
                step_output
            ):
                return (
                    False,
                    "No real code change detected.",
                )

        if self._step_requires_verification(
            step_title
        ):
            if not self._step_output_indicates_real_verification(
                step_output
            ):
                return (
                    False,
                    "No real verification detected.",
                )

        return True, ""

    # =========================
    # EXECUTION RENDER NORMALIZATION LOCK
    # =========================

    def _execution_status_label(
        self,
        execution,
    ):

        execution = execution or {}

        steps = execution.get("steps") or []

        total = len(steps)

        done = sum(
            1
            for s in steps
            if (s or {}).get("done")
        )

        if total > 0 and done >= total:
            return "complete"

        idx = (
            execution.get(
                "current_index",
                0,
            )
            or 0
        )

        if 0 <= idx < total:
            title = str(
                (steps[idx] or {}).get("title")
                or ""
            ).strip()

            if title:
                return title

        return "in progress"

    def _render_execution(
        self,
        execution,
        include_prefix=False,
    ):

        if not isinstance(execution, dict):
            execution = {}

        execution = self._normalize_execution_state(
            dict(execution)
        )

        goal = str(
            execution.get("goal")
            or ""
        ).strip()

        steps = execution.get("steps") or []

        exec_debug(
            "RENDER EXECUTION =",
            execution,
        )

        exec_debug(
            "RENDER STEPS =",
            steps,
        )

        total = len(steps)

        done = sum(
            1
            for s in steps
            if (s or {}).get("status") == "done"
        )

        current_index = int(
            execution.get(
                "current_index",
                0,
            )
            or 0
        )

        if 0 <= current_index < total:

            current_step = (
                str(
                    (steps[current_index] or {}).get(
                        "title"
                    )
                    or ""
                ).strip()
                or "Untitled step"
            )

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

            title = (
                str(s.get("title") or "").strip()
                or "Untitled step"
            )

            status = (
                str(
                    s.get("status")
                    or "pending"
                )
                .strip()
                .lower()
            )

            if status == "done":
                mark = "[x]"

            elif status == "current":
                mark = "[>]"

            else:
                mark = "[ ]"

            lines.append(f"{mark} {title}")

        lines.append("")

        lines.append(
            f"Progress: {done}/{total} complete"
        )

        lines.append(
            f"Current step: {current_step}"
        )

        assistant_text = "\n".join(lines)

        assistant_text = (
            assistant_text
            .replace("AUTO_EXECUTE", "")
            .replace("TEST_FAIL", "")
            .strip()
        )

        return assistant_text

    def _build_execution_assistant_text(
        self,
        execution,
    ):

        return self._render_execution(
            execution,
            include_prefix=True,
        )

    def _build_execution_artifact_body(
        self,
        execution,
    ):

        return self._render_execution(
            execution,
            include_prefix=False,
        )

    def _build_working_state_summary(
        self,
        working_state,
    ):

        ws = self._normalize_working_state(
            working_state
        )

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
                lines.append(
                    f"{label}: {value}"
                )

        if not lines:
            return ""

        return (
            "Working context:\n"
            + "\n".join(lines)
        )


    def _build_continuity_context(self, session=None):
        session = session or {}
        messages = session.get("messages") if isinstance(session, dict) else []
        if not isinstance(messages, list) or not messages:
            return ""

        recent = messages[-6:]
        lines = []

        for msg in recent:
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role") or "").strip()
            text = str(msg.get("text") or msg.get("content") or "").strip()
            if role and text:
                lines.append(f"{role}: {text[:500]}")

        if not lines:
            return ""

        return "Recent conversation:\n" + "\n".join(lines)

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
            if not hasattr(self, "memory") or not self.memory:
                return []

            # 1. correct API (if it exists)
            if hasattr(self.memory, "list_memories"):
                result = self.memory.list_memories()
                if isinstance(result, list):
                    return result

            # 2. correct fallback (your actual storage layer)
            if hasattr(self.memory, "_read_store"):
                data = self.memory._read_store()
                if isinstance(data, dict):
                    return data.get("memory", [])

            # 3. last fallback (safe empty)
            return []

        except Exception:
            return []

    def _iso_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _clean_execution_text(self, value: str | None) -> str:
        text = str(value or "").strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

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

        blocked_internal_phrases = (
            "execution handler",
            "next move",
            "internal reasoning",
            "thinking step",
            "need to run",
            "i should now",
            "i need to now",
            "run the execution",
        )

        if any(pattern in lowered for pattern in blocked_internal_phrases):
            return False

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
                    # HARD FILTER: strip known bad kwargs
                    filtered_kwargs = {
                        k: v for k, v in kwargs.items()
                        if k not in {"route"}
                    }

                    try:
                        return method(*args, **filtered_kwargs)

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

    def _decide(self, user_text: str, attachments=None, session_id: str = "") -> dict:
        return self._decide_route(
            user_text=user_text,
            attachments=attachments,
            session_id=session_id,
        )

    def _build_intelligence_state(
        self,
        user_text: str = "",
        session_id: str = "",
        attachments=None,
    ) -> dict:
        attachments = attachments or []
        text = self._safe_str(user_text).strip()
        text_lc = text.lower()

        working_state = self._get_working_state(session_id) or {}

        execution_state = (
            self._get_session_meta(session_id, "execution_state")
            or self._get_session_meta(session_id, "active_execution")
            or {}
        )

        failed_steps = []
        if isinstance(execution_state, dict):
            for step in execution_state.get("steps") or []:
                if (
                    isinstance(step, dict)
                    and self._safe_str(step.get("status")).lower() == "failed"
                ):
                    failed_steps.append(step)

        has_failed_steps = len(failed_steps) > 0

        failure_count = 0
        if isinstance(execution_state, dict):
            failure_count = int(
                execution_state.get("failure_count")
                or execution_state.get("retry_count")
                or 0
            )

        retry_strategy = "none"

        if has_failed_steps:
            if failure_count <= 0:
                retry_strategy = "retry_step"
            elif failure_count == 1:
                retry_strategy = "retry_with_smaller_scope"
            elif failure_count == 2:
                retry_strategy = "retry_with_file_scope"
            else:
                retry_strategy = "change_strategy"

        has_active_execution = (
            isinstance(execution_state, dict)
            and execution_state
            and self._safe_str(execution_state.get("status")).lower()
            not in {"complete", "completed", "done", "cancelled", "canceled"}
        )

        intent = "chat"
        route = self.ROUTE_GENERAL_CHAT
        strategy = "direct_answer"
        priority = "normal"
        confidence = 0.65
        reasons = []

        execution_commands = {
            "next",
            "nex",
            "continue",
            "continue on",
            "keep going",
            "go",
            "run next",
            "next step",
            "what next",
            "what now",
            "run_step",
            "run step",
            "run all",
            "run_all",
            "run it",
            "execute",
            "execute all",
            "retry",
            "retry failed",
            "try again",
            "stop",
            "cancel",
        }

        if text_lc in execution_commands:

            if "retry" in text_lc:
                intent = "retry_failed_step"

            elif "run all" in text_lc or text_lc == "execute all":
                intent = "run_all_steps"

            elif text_lc in {"stop", "cancel"}:
                intent = "cancel_execution"

            elif has_failed_steps:
                intent = "retry_failed_step"

            elif execution_state.get("waiting"):
                intent = "continue_waiting_execution"

            else:
                intent = "resume_execution"

            route = "execution_command"
            strategy = "execute"
            priority = "high"
            confidence = 1.0
            reasons.append("execution_command")

        elif text_lc.startswith("auto-plan "):
            intent = "planning"
            route = "execution_plan"
            strategy = "plan"
            priority = "high"
            confidence = 0.95
            reasons.append("auto_plan_command")

        elif any(x in text_lc for x in ["traceback", "syntaxerror", "indentationerror", "nameerror", "typeerror"]):
            intent = "debugging"
            route = "auto_fix_or_debug"
            strategy = "diagnose_fix"
            priority = "high"
            confidence = 0.9
            reasons.append("error_signal")

        elif "smff" in text_lc or "full file" in text_lc or "full code" in text_lc:
            intent = "full_file_code"
            route = "code_full_file"
            strategy = "provide_full_file"
            priority = "high"
            confidence = 0.9
            reasons.append("full_file_request")

        elif text_lc in {"where are we", "where are we now", "what are we doing", "what now", "status", "recap"}:
            intent = "continuity"
            route = "continuity"
            strategy = "summarize_state"
            priority = "high"
            confidence = 0.9
            reasons.append("continuity_query")

            self._update_working_state(
                session_id,
                {
                    "active_task": "",
                    "next_move": "",
                    "checkpoint": "",
                },
            )

        mission_state = self._build_mission_state(
            working_state=working_state,
            execution_state=execution_state,
        )

        autonomous_direction = ""

        if has_failed_steps:
            autonomous_direction = retry_strategy

        elif has_active_execution:
            autonomous_direction = "continue_execution"

        elif mission_state.get("recommended_next_move"):
            autonomous_direction = (
                mission_state.get("recommended_next_move")
            )

        else:
            autonomous_direction = "await_user_input"

        return {
            "route": route,
            "intent": intent,
            "mode": intent,
            "strategy": strategy,
            "priority": priority,
            "confidence": confidence,
            "reasons": reasons or ["default_intelligence_state"],

            "mission": mission_state,
            "autonomous_direction": autonomous_direction,

            "execution": execution_state,
            "failed_steps": failed_steps,
            "has_failed_steps": has_failed_steps,
            "failure_count": failure_count,
            "retry_strategy": retry_strategy,
            "has_active_execution": has_active_execution,
            "should_execute": intent == "execution_command",
            "should_plan": intent == "planning",
            "should_ask": False,
            "save_artifact": False,
            "save_memory": intent not in {"execution_command"},
            "use_memory": intent not in {"execution_command"},
        }

    def _decide_route(
        self,
        user_text: str,
        attachments=None,
        session_id: str = "",
    ) -> dict:


        user_text = self._safe_str(user_text).strip()

        text = user_text.lower().strip()
        lower_text = text

        # REMOVE_DECIDE_ROUTE_DEBUG_PRINT_LOCK

        # =========================
        # RUNTIME LANE
        # =========================

        if self._safe_str(user_text).startswith("/runtime"):

            return {
                "route": "runtime",
                "intent": "runtime",
                "mode": "runtime",
                "runtime_command": user_text,
                "confidence": 1.0,
                "reasons": [
                    "User requested runtime cognition lane."
                ],
            }

        intelligence_state = self._build_intelligence_state(
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
        )

        if (
            isinstance(intelligence_state, dict)
            and intelligence_state.get("route") != self.ROUTE_GENERAL_CHAT
        ):
            return intelligence_state

        regen_commands = {
            "regen",
            "regenerate",
            "redo image",
            "make another",
            "another image",
        }

        if lower_text.strip() in regen_commands:
            return {
                "route": self.ROUTE_IMAGE_GENERATION,
                "mode": "image_generation",
                "confidence": 1.0,
                "reasons": ["regen_command"],
            }

        attachments = attachments or []

        if lower_text.startswith("generate "):
            return {
                "route": self.ROUTE_IMAGE_GENERATION,
                "mode": "image_generation",
                "confidence": 1.0,
                "reasons": ["forced_generate_prefix"],
                "save_artifact": True,
                "save_memory": False,
                "use_memory": False,
                "prompt": user_text,
            }

        # =========================
        # IMAGE GENERATION (PRIORITY)
        # =========================

        image_triggers = (
            "generate ",
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
                "route": self.ROUTE_IMAGE_GENERATION,
                "mode": "image_generation",
                "confidence": 0.95,
                "reasons": ["image_generation_intent"],
                "save_artifact": True,
                "save_memory": False,
                "use_memory": False,
                "prompt": user_text,
            }

        # =========================
        # IMAGE / FILE ANALYSIS
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
        # WEB FETCH AUTO-DETECT LOCK
        # =========================
        has_url = (
            "http://" in lower_text
            or "https://" in lower_text
            or lower_text.startswith("www.")
        )

        live_web_triggers = (
            "latest",
            "today",
            "yesterday",
            "last night",
            "this week",
            "right now",
            "current",
            "news",
            "update",
            "updates",
            "score",
            "scores",
            "who won",
            "what happened",
            "sources",
            "source",
            "price",
            "stock",
            "bitcoin",
            "crypto",
            "nvidia",
            "nba",
            "nfl",
            "nhl",
            "mlb",
            "ufc",
        )

        if self._is_image_generation_request(user_text):
            return {
                "route": self.ROUTE_IMAGE_GENERATION,
                "mode": "image_generation",
                "confidence": 1.0,
                "reasons": ["image_generation_request"],
                "save_artifact": True,
                "save_memory": False,
                "use_memory": False,
            }

        wants_live_web = any(trigger in lower_text for trigger in live_web_triggers)

        if (
            has_url
            or wants_live_web
            or user_text.lower().strip().startswith("/web")
        ):
            return {
                "route": self.ROUTE_WEB_FETCH,
                "mode": "web_fetch",
                "confidence": 1.0,
                "reasons": ["forced_web_fetch"],
                "save_artifact": True,
                "save_memory": False,
                "use_memory": False,
                "query": user_text,
            }

        # =========================
        # DEFAULT CHAT
        # =========================

        execution_commands = {
            "next",
            "run_step",
            "run step",
            "run_all",
            "run all",
            "retry",
            "retry_failed",
            "retry failed",
            "try again",
            "rerun failed",
        }

        ws = self._get_working_state(session_id) or {}

        updated_at = self._safe_str(
            ws.get("updated_at")
        ).strip()

        has_working_mission = False

        if updated_at:

            try:
                updated_dt = datetime.fromisoformat(
                    updated_at.replace("Z", "+00:00")
                )

                now_dt = datetime.now(
                    updated_dt.tzinfo
                )

                age_seconds = (
                    now_dt - updated_dt
                ).total_seconds()

                if age_seconds <= 600:
                    has_working_mission = bool(
                        ws.get("active_task")
                        and ws.get("next_move")
                    )

            except Exception:
                has_working_mission = False

        continue_commands = {
            "next",
            "nex",
            "continue",
            "continue on",
            "keep going",
            "go",
            "next step",
        }

        if text in execution_commands:
            print("EXECUTION COMMAND TEXT =", repr(text))
            print("HAS WORKING MISSION =", has_working_mission)
            print("HAS ACTIVE EXECUTION =", has_active_execution)

            if (
                text == "resume"
                and not has_working_mission
                and not has_active_execution
            ):
                return {
                    "route": "resume_empty_state_guard",
                    "mode": "system",
                    "confidence": 1.0,
                    "reasons": ["empty_resume_guard"],
                    "save_artifact": False,
                    "save_memory": False,
                    "use_memory": False,
                }

            if (
                text == "resume"
                and not has_working_mission
                and not has_active_execution
            ):
                return {
                    "route": "resume_empty_state_guard",
                    "mode": "system",
                    "confidence": 1.0,
                    "reasons": ["empty_resume_guard"],
                    "save_artifact": False,
                    "save_memory": False,
                    "use_memory": False,
                }

            if text in continue_commands and has_working_mission:

                return {
                    "route": self.ROUTE_GENERAL_CHAT,
                    "mode": "chat",
                    "confidence": 1.0,
                    "reasons": ["working_state_continue_override"],
                    "save_artifact": False,
                    "save_memory": False,
                    "use_memory": True,
                }

            return {
                "route": "execution_command",
                "mode": "execution",
                "confidence": 1.0,
                "reasons": ["execution_command_override"],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": False,
            }

        planner_prefixes = (
            "auto-plan",
            "build ",
            "create ",
            "make ",
            "implement ",
            "fix ",
            "repair ",
        )

        if text.startswith(planner_prefixes):

            return {
                "route": "execution",
                "mode": "execution",
                "confidence": 1.0,
                "reasons": [
                    "planner_prefix_detected"
                ],
                "save_artifact": False,
                "save_memory": True,
                "use_memory": True,
            }

        return {
            "route": self.ROUTE_GENERAL_CHAT,
            "mode": "chat",
            "confidence": 0.6,
            "reasons": ["default_chat"],
            "save_artifact": False,
            "save_memory": True,
            "use_memory": True,
        }

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

    def _reconcile_execution_state(
        self,
        session_id: str,
        working_state=None,
        execution_state=None,
    ) -> dict:
        working_state = working_state if isinstance(working_state, dict) else {}
        execution_state = execution_state if isinstance(execution_state, dict) else {}

        active_execution = self._get_session_meta(session_id, "active_execution") or {}

        active_status = self._safe_str(active_execution.get("status")).strip().lower()
        execution_status = self._safe_str(execution_state.get("status")).strip().lower()

        active_complete = (
            active_status in {"complete", "completed"}
            or active_execution.get("complete") is True
        )

        execution_complete = (
            execution_status in {"complete", "completed"}
            or execution_state.get("complete") is True
        )

        if active_complete or execution_complete:
            execution_state = (
                self._mark_execution_complete(
                    execution_state,
                )
            )

            active_execution["status"] = "complete"
            active_execution["complete"] = True
            active_execution["waiting"] = False

            if working_state.get("next_move") == "retry_failed":
                working_state["next_move"] = "await_new_mission"

            if not working_state.get("last_success"):
                working_state["last_success"] = "execution_complete"

            self._save_execution_state(
                session_id,
                execution_state,
            )

            self._save_active_execution(
                session_id,
                active_execution,
            )

            self._update_working_state(
                session_id,
                working_state,
            )

        return {
            "working_state": working_state,
            "execution_state": execution_state,
            "active_execution": active_execution,
        }

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
        execution["summary"] = str(
            assistant_text or execution.get("summary") or ""
        )[:200]
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

        failed_index = 0

        if isinstance(steps, list):
            for index, step in enumerate(steps):
                if isinstance(step, dict) and step.get("status") == "running":
                    failed_index = index
                    break

        execution = self._mark_execution_failed(
            execution,
            step_index=failed_index,
            error=str(error_text or "Execution failed."),
        )

        execution["summary"] = str(
            error_text or execution.get("summary") or ""
        )[:200]
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
            exec_debug(
                "GET PERSISTED EXECUTION LOAD SESSIONS FAILED:",
                e,
            )
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

            persisted = session.get("execution_state")

            if isinstance(persisted, dict) and persisted:
                return persisted

            persisted = (
                session.get("execution_state")
                or {}
            )

            if isinstance(persisted, dict) and persisted:
                return persisted

            persisted = session.get("working_execution")

            if isinstance(persisted, dict) and persisted:
                return persisted

            return None

        return None

    def _persist_execution_artifact(self, session_id: str, execution: dict | None) -> None:
        session_id = self._safe_str(session_id)
        if not session_id:
            return

        if not isinstance(execution, dict):
            execution = {}

        if not isinstance(execution, dict):
            execution = {}

        execution = self._normalize_execution_state(
            dict(execution)
        )

        execution["session_id"] = session_id
        execution["active"] = True

        try:
            sessions = self.session_service.list_sessions()
        except Exception as e:
            exec_debug("PERSIST EXECUTION LOAD SESSIONS FAILED:", e)
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
            exec_debug("PERSIST EXECUTION SAVE SESSIONS FAILED:", e)

    def _find_latest_execution_artifact(self, session_id: str = ""):
        session_id = self._safe_str(session_id)

        try:
            artifacts = []

            if hasattr(self, "artifact_service") and hasattr(self.artifact_service, "list_all"):
                artifacts = self.artifact_service.list_all()
            elif hasattr(self, "artifacts") and hasattr(self.artifacts, "list_all"):
                artifacts = self.artifacts.list_all()

            artifacts = artifacts or []

            exec_debug("ALL ARTIFACTS =", artifacts)

            matches = []

            for a in artifacts:
                a = a or {}

                if session_id and self._safe_str(a.get("session_id")) != session_id:
                    continue

                execution = a.get("execution") or ((a.get("meta") or {}).get("execution")) or {}

                if execution:
                    exec_debug("MATCHED EXECUTION ARTIFACT =", a)
                    matches.append(a)

            matches.sort(
                key=lambda x: self._safe_str(x.get("created_at")),
                reverse=True,
            )

            latest = matches[0] if matches else None

            exec_debug("FINAL LATEST =", latest)

            return latest

        except Exception as e:
            exec_debug("FIND EXECUTION FAILED =", e)
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
        exec_debug("PROGRESS_MATCH_NORMALIZED =", repr(normalized))

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

    def _save_active_execution(
        self,
        session_id,
        execution_state,
    ):
        return self._save_execution_state(
            session_id,
            execution_state,
        )

    def _build_execution_snapshot(
        self,
        execution_state,
    ):
        execution_state = (
            self._normalize_execution_state(
                execution_state
            )
        )

        steps = (
            execution_state.get("steps")
            or []
        )

        if not isinstance(
            steps,
            list,
        ):
            steps = []

        current_index = int(
            execution_state.get(
                "current_index",
                0,
            )
            or 0
        )

        if current_index < 0:
            current_index = 0

        if (
            False
            and current_index >= len(steps)
        ):
            current_index = len(steps)

        execution_state["current_index"] = (
            current_index
        )

        current_step = ""

        if (
            steps
            and current_index < len(steps)
        ):
            step = steps[current_index]

            if isinstance(
                step,
                dict,
            ):
                current_step = (
                    step.get("title")
                    or step.get("action")
                    or ""
                )

        snapshot = {
            "status": self._safe_str(
                execution_state.get(
                    "status"
                )
            ),
            "steps": steps,
            "current_index": current_index,
            "current_step": current_step,
            "history": (
                execution_state.get(
                    "history"
                )
                or []
            ),
            "progress": (
                execution_state.get(
                    "progress"
                )
                or 0
            ),
            "waiting": bool(
                execution_state.get(
                    "waiting"
                )
            ),
            "complete": bool(
                execution_state.get(
                    "complete"
                )
            ),
            "runtime_signal": self._safe_str(
                execution_state.get(
                    "runtime_signal"
                )
            ),
            "next_moves": (
                execution_state.get(
                    "next_moves"
                )
                or []
            ),
        }

        return snapshot

    def _normalize_execution_state(self, execution):
        if not isinstance(execution, dict):
            execution = {}

        execution.setdefault("goal", "")
        execution.setdefault("steps", [])
        execution.setdefault("status", "idle")
        execution.setdefault("progress", 0)
        execution.setdefault("current_step", "")

        raw_steps = execution.get("steps") or []
        clean_steps = []

        for raw in raw_steps:
            if isinstance(raw, dict):
                title = str(raw.get("title") or "").strip()

                print(
                    "RAW STEP BEFORE CLEAN =",
                    raw,
                )

                clean_steps.append(
                    {
                        "id": raw.get("id", ""),
                        "title": title,
                        "action": raw.get("action", ""),
                        "input": raw.get("input", ""),
                        "target_file": raw.get("target_file", ""),
                        "target_function": raw.get("target_function", ""),
                        "status": raw.get("status", "pending"),
                        "result": raw.get("result", ""),
                        "error": raw.get("error", None),
                    }
                )

            else:
                title = str(raw).strip()

                clean_steps.append(
                    {
                        "id": "",
                        "title": title,
                        "action": "",
                        "input": "",
                        "target_file": "",
                        "target_function": "",
                        "status": "pending",
                        "result": "",
                        "error": None,
                    }
                )

        clean_steps = [step for step in clean_steps if step.get("title")]
        execution["steps"] = clean_steps

        step_count = len(clean_steps)
        current_index = self._execution_current_index(execution)

        status = str(execution.get("status") or "idle").strip().lower()

        if status not in {
            "running",
            "complete",
            "completed",
            "blocked",
            "idle",
        }:
            status = "idle"

        if status == "completed":
            status = "complete"

        if not clean_steps:
            execution = self._finalize_execution_state(execution)
            execution["steps"] = []

            return self._sync_execution_state(
                execution=execution,
                current_index=0,
                status="complete",
                current_step="complete",
                progress=0,
            )

        if current_index >= step_count or status == "complete":
            current_index = step_count
            status = "complete"

            for step in clean_steps:
                step["status"] = "done"

            return self._sync_execution_state(
                execution=execution,
                current_index=current_index,
                status=status,
                current_step="complete",
                progress=step_count,
            )

        status = "running" if status == "running" else status

        for idx, step in enumerate(clean_steps):

            existing_status = self._safe_str(
                step.get("status")
            ).lower().strip()

            if existing_status in {
                "completed",
                "done",
                "failed",
                "running",
            }:
                continue

            if idx < current_index:
                step["status"] = "completed"

            elif idx == current_index:
                step["status"] = "running"

            else:
                step["status"] = "pending"

        current_step = clean_steps[current_index].get("title", "")

        return self._sync_execution_state(
            execution=execution,
            current_index=current_index,
            status=status,
            current_step=current_step,
            progress=current_index,
        )
  
    def _advance_execution_one_step(self, execution):
        execution = self._normalize_execution_state(
            execution or {}
        )

        steps = execution.get("steps") or []
        step_count = len(steps)

        current_index = self._execution_current_index(execution)

        if step_count == 0:
            execution = self._finalize_execution_state(execution)
            execution["steps"] = []

            execution = self._sync_execution_state(
                execution=execution,
                current_index=0,
                progress=0,
            )

            return self._normalize_execution_state(execution)

        if current_index >= step_count:
            execution = self._finalize_execution_state(execution)

            execution = self._sync_execution_state(
                execution=execution,
                current_index=step_count,
                progress=step_count,
            )

            return self._normalize_execution_state(execution)

        next_index = current_index + 1

        if next_index >= step_count:
            execution = self._finalize_execution_state(execution)

            execution = self._sync_execution_state(
                execution=execution,
                current_index=step_count,
                progress=step_count,
            )
        else:
            execution = self._sync_execution_state(
                execution=execution,
                current_index=next_index,
                status="running",
                current_step=steps[next_index].get("title", ""),
                progress=next_index,
            )

        return self._normalize_execution_state(execution)

    # =========================================
    # LEGACY EXECUTION PATH
    # =========================================
    # This execution progression system is kept
    # temporarily for artifact compatibility.
    #
    # Canonical execution flow is now:
    #
    # _handle_execution_control
    #     -> _process_execution_command
    #     -> _execute_current_step
    #     -> _sync_execution_state
    #
    # Avoid adding new execution logic here.
    # =========================================

    def _advance_execution_request(self, user_text: str, session_id: str = "", attachments=None):
        attachments = attachments or []
        session_id = self._safe_str(session_id)
        user_text = self._safe_str(user_text)
        assistant_text = ""

        exec_debug("ADVANCE SESSION_ID =", session_id)

        persisted_execution = self._get_persisted_execution_artifact(session_id=session_id)
        latest_artifact = self._find_latest_execution_artifact(session_id=session_id)

        exec_debug("ADVANCE PERSISTED EXECUTION =", persisted_execution)
        exec_debug("ADVANCE LATEST ARTIFACT =", latest_artifact)

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

            self._save_execution_state(
                session_id,
                {},
            )

            self._update_working_state(
                session_id,
                {
                    "next_move": "",
                    "pending_execution_action": "",
                    "active_task": "",
                },
            )

        text = (user_text or "").strip().lower()

        if text == "auto mode":

            return self._handle_execution_control(
                user_text="run_all",
                session_id=session_id,
                attachments=attachments,
            )

        if text == "test_fail":

            print("TEST_FAIL HARD OVERRIDE HIT")

            live_execution = (
                self._get_session_meta(
                    session_id,
                    "execution_state",
                )
                or {}
            )

            live_execution = self._mark_execution_failed(
                execution_state=live_execution,
                step_index=max(
                    0,
                    min(
                        len(
                            live_execution.get("steps") or []
                        ) - 1,
                        int(
                            live_execution.get(
                                "current_index",
                                0,
                            )
                            or 0
                        ) - 1,
                    ),
                ),
                error="Execution step failed.",
            )

            self._save_execution_state(
                session_id,
                execution_state,
            )      

            return {
                "ok": False,
                "assistant_message": {
                    "role": "assistant",
                    "text": "Execution step failed.",
                },
                "execution": live_execution,
            }

        if not execution:
            execution = {
                "status": "ready",
                "steps": [
                    {"title": "Step 1: Start execution chain", "status": "pending"},
                    {"title": "Step 2: Advance execution chain", "status": "pending"},
                    {"title": "Step 3: Complete execution chain", "status": "pending"},
                ],
                "history": [],
                "last_action": "plan_created",
                "current_step": "",
            }

            self._update_working_state(
                session_id,
                {
                    "execution": execution,
                },
            )
        goal_text = self._safe_str(execution.get("goal")).lower()
        step_index = int(
            execution.get("current_index", 0) or 0
        )
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

        # AUTO MODE LOOP

        if text in {
            "auto mode",
            "run_all",
            "auto",
            "autopilot",
            "next",
            "nex",
            "continue",
            "continue on",
            "keep going",
            "go",
            "run next",
            "next step",
            "what next",
            "what now",
        }:
            try:
                for _ in range(10):  # safety cap
                    execution = self._advance_execution_one_step(execution)
                    execution = self._normalize_execution_state(execution)

                    status = self._safe_str(execution.get("status")).lower()

                    if status in {"complete", "completed", "error", "failed"}:
                        break

                execution = self._normalize_execution_state(execution)

            except Exception as e:
                exec_debug("AUTO LOOP ERROR:", e)
        else:
            execution = self._advance_execution_one_step(execution)
            execution = self._normalize_execution_state(execution)

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
            exec_debug("ADVANCE EXECUTION SAVE FAILED (positional):", e)
            saved_artifact = None

        if not saved_artifact:
            try:
                saved_artifact = self._call_first(
                    self.artifacts,
                    ["save_artifact", "create_artifact", "add_artifact", "save", "create"],
                    artifact=artifact_payload,
                )
            except Exception as e:
                exec_debug("ADVANCE EXECUTION SAVE FAILED (keyword artifact):", e)
                saved_artifact = None

        try:
            self._persist_execution_artifact(session_id=session_id, execution=execution)
        except Exception as e:
            exec_debug("ADVANCE EXECUTION PERSIST FAILED:", e)

        plan_body = self._render_execution(execution)

        status = self._safe_str(execution.get("status")).lower()

        if status in {"complete", "completed"}:
            assistant_text = "Auto-execution complete."
        elif step_output:
            assistant_text = step_output
        else:
            assistant_text = "Step processed."

        if plan_body:
            assistant_text += "\n\n" + plan_body

        assistant_msg = self._build_assistant_message(
            text=assistant_text,
            attachments=[],
        )

        if isinstance(assistant_msg, dict):
            content = assistant_msg.get("content") or ""
            if isinstance(content, str):
                assistant_msg["content"] = (
                    content
                    .replace("AUTO_EXECUTE", "")
                    .replace("TEST_FAIL", "")
                    .strip()
                )

        if assistant_text:
            self._set_session_meta(session_id, "last_answer_topic", self._safe_str(original_user_text)[:300])
            self._set_session_meta(session_id, "last_answer_text", self._safe_str(assistant_text)[:4000])
            self._set_session_meta(session_id, "last_answer_mode", self._get_session_meta(session_id, "answer_depth") or "short")

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
            value = int(
                execution.get(
                    "current_index",
                    0,
                )
                or 0
            )
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

    def _mark_execution_running(
        self,
        execution_state,
        step_index=0,
        current_step="",
        waiting=False,
    ):

        execution_state = dict(
            execution_state or {}
        )

        execution_state["status"] = "running"
        execution_state["complete"] = False
        execution_state["waiting"] = bool(waiting)
        execution_state["lock"] = False

        execution_state["current_index"] = step_index
        execution_state["current_step"] = current_step or ""
        execution_state["current_step_title"] = current_step or ""

        return execution_state

    def _mark_execution_complete(
        self,
        execution_state,
    ):

        execution_state = dict(
            execution_state or {}
        )

        steps = (
            execution_state.get("steps")
            or []
        )

        execution_state["status"] = (
            "complete"
        )

        execution_state["complete"] = True
        execution_state["waiting"] = False
        execution_state["lock"] = False

        execution_state["next_moves"] = []

        execution_state["current_index"] = (
            len(steps)
        )

        execution_state["current_step"] = ""
        execution_state["current_step_title"] = ""

        execution_state["progress"] = (
            len(steps)
        )

        return execution_state

    def _sync_execution_state(
        self,
        execution=None,
        current_index=None,
        status=None,
        current_step=None,
        progress=None,
        waiting=None,
    ):
        execution = (
            execution
            if isinstance(execution, dict)
            else {}
        )

        original_steps = execution.get("steps")

        execution = self._normalize_execution_state(
            execution
        )

        if isinstance(original_steps, list):
            execution["steps"] = original_steps

        steps = (
            execution.get("steps")
            if isinstance(execution.get("steps"), list)
            else []
        )

        if current_index is not None:
            try:
                current_index = int(current_index)
            except Exception:
                current_index = 0

            current_index = max(
                0,
                current_index,
            )

            if steps:
                current_index = min(
                    current_index,
                    len(steps),
                )

            execution["current_index"] = (
                current_index
            )

            execution["current_step_index"] = (
                current_index
            )

        else:
            try:
                current_index = int(
                    execution.get("current_index", 0)
                    or 0
                )
            except Exception:
                current_index = 0

            current_index = max(
                0,
                current_index,
            )

        if status is not None:
            execution["status"] = (
                self._safe_str(status)
                or execution.get("status")
                or "idle"
            )

        if current_step is not None:
            execution["current_step"] = (
                current_step
            )

            execution["current_step_title"] = (
                current_step
            )

        elif (
            steps
            and current_index < len(steps)
            and isinstance(steps[current_index], dict)
        ):
            execution["current_step"] = (
                steps[current_index].get("title", "")
            )

            execution["current_step_title"] = (
                steps[current_index].get("title", "")
            )

        if progress is not None:
            try:
                progress = int(progress)
            except Exception:
                progress = 0

            execution["progress"] = max(
                0,
                progress,
            )

        if waiting is not None:
            execution["waiting"] = bool(
                waiting
            )

        execution["lock"] = bool(
            execution.get("lock", False)
        )

        execution["complete"] = bool(
            execution.get("status") == "complete"
        )

        return execution

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
                {
                    "id": f"step_{i + 1}",
                    "title": s,
                    "action": "execute",
                    "input": s,
                    "target_file": "",
                    "target_function": "",
                    "status": (
                        "running"
                        if i == 0
                        else "pending"
                    ),
                    "result": "",
                    "error": None,
                }
                for i, s in enumerate(steps)
            ],
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
            exec_debug("BUILD EXECUTION PLAN FAILED (positional):", e)
            saved_artifact = None

        if not saved_artifact:
            try:
                saved_artifact = self._call_first(
                    self.artifacts,
                    ["save_artifact", "create_artifact", "add_artifact", "save", "create"],
                    artifact=artifact_payload,
                )
            except Exception as e:
                exec_debug("BUILD EXECUTION PLAN FAILED (keyword artifact):", e)
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
            exec_debug("BUILD EXECUTION PLAN PERSIST EXECUTION FAILED:", e)

        exec_debug("BUILD EXECUTION PLAN SAVED =", bool(saved_artifact))
        exec_debug("BUILD EXECUTION PLAN SESSION =", session_id)
        exec_debug("BUILD EXECUTION PLAN ARTIFACT =", saved_artifact)
        exec_debug("BUILD EXECUTION PLAN ACTIVE EXECUTION =", execution)

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
            exec_debug("TURN PERSIST FAILED:", e)


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

            blocked_moves = {
                "request_traceback",
                "manual_review_required",
            }

            if first_line.lower() in blocked_moves:
                first_line = ""

            if first_line:
                patch["next_move"] = first_line
        if step_title and not self._safe_str(current_state.get("active_task")).strip():
            patch["active_task"] = step_title

        return patch

        # ==============================
        # WORKING STATE (PHASE 3)
        # ==============================



    def _set_working_state(self, session_id: str, state: dict):
        session_id = self._safe_str(session_id).strip()
        if not session_id:
            return {}

        if not isinstance(state, dict):
            state = {}

        clean_state = {
            "active_task": self._safe_str(state.get("active_task")).strip(),
            "current_file": self._safe_str(state.get("current_file")).strip(),
            "current_bug": self._safe_str(state.get("current_bug")).strip(),
            "last_success": self._safe_str(state.get("last_success")).strip(),
            "next_move": self._safe_str(state.get("next_move")).strip(),
            "checkpoint": self._safe_str(state.get("checkpoint")).strip(),
            "updated_at": self._safe_str(state.get("updated_at")).strip(),
        }

        try:
            return self.sessions.update_working_state(session_id, clean_state)
        except Exception as e:
            exec_debug("SET_WORKING_STATE_DIRECT_CALL_ERROR:", e)

        return clean_state

    def _auto_track_working_state(
        self,
        session_id,
        user_text="",
        assistant_text="",
    ):

        current = (
            self._get_working_state(session_id)
            or {}
        )

        patch = {}

        lowered = (
            self._safe_str(user_text)
            .lower()
            .strip()
        )

        current_updated_at = self._safe_str(
            current.get("updated_at")
        ).strip()

        stale_state = False

        if current_updated_at:

            try:
                updated_dt = datetime.fromisoformat(
                    current_updated_at.replace("Z", "+00:00")
                )

                now_dt = datetime.now(
                    updated_dt.tzinfo
                )

                age_seconds = (
                    now_dt - updated_dt
                ).total_seconds()

                if age_seconds > 600:
                    stale_state = True

            except Exception:
                stale_state = False

        if stale_state:

            self._replace_working_state(
                session_id,
                {
                    "active_task": "",
                    "current_file": "",
                    "current_bug": "",
                    "last_success": "",
                    "next_move": "",
                    "checkpoint": "",
                    "updated_at": "",
                },
            )

            current = {
                "active_task": "",
                "current_file": "",
                "current_bug": "",
                "last_success": "",
                "next_move": "",
                "checkpoint": "",
                "updated_at": "",
            }

        if any(
            x in lowered
            for x in (
                "landing page",
                "homepage",
                "hero section",
                "product positioning",
            )
        ):
            patch["active_task"] = (
                "polish Nova landing page and product positioning"
            )

            patch["checkpoint"] = (
                "landing_page_work"
            )

            patch["next_move"] = (
                "tighten product messaging and demos"
            )

        continuity_commands = {
            "where are we",
            "resume",
            "continue",
            "what now",
            "what's next",
        }

        normalized_text = lowered.strip()

        execution_state = (
            self._get_session_meta(
                session_id,
                "execution_state",
            )
            or {}
        )

        if (
            normalized_text in continuity_commands
            and execution_state.get("status") == "running"
        ):

            if (
                execution_state.get("current_index", 0)
                < len(execution_state.get("steps") or [])
            ):

                patch["active_task"] = (
                    "continue Nova backend intelligence stabilization"
                )

                if not patch.get("checkpoint"):

                    patch["checkpoint"] = (
                        "working_state_resume_context"
                    )

                if not patch.get("next_move"):

                    patch["next_move"] = (
                        "continue backend memory and execution stabilization"
                    )

        generic_chat_inputs = {
            "hi",
            "hello",
            "hey",
            "2+2",
            "what is dns",
            "tell me a joke",
            "who is austin rivers",
            "who is jj redick",
        }

        if (
            lowered.strip() in generic_chat_inputs
            or not any(
                lowered.startswith(prefix)
                for prefix in (
                    "fix ",
                    "build ",
                    "create ",
                    "make ",
                    "implement ",
                    "upgrade ",
                    "wire ",
                    "add ",
                    "repair ",
                )
            )
        ):

            patch["active_task"] = ""
            patch["next_move"] = ""

            if not execution_state.get("status"):

                patch["checkpoint"] = ""

        if (
            user_text.strip()
            and not patch.get("active_task")
            and normalized_text not in generic_chat_inputs
        ):

            if any(
                user_text.lower()
                .strip()
                .startswith(prefix)
                for prefix in (
                    "fix ",
                    "build ",
                    "create ",
                    "make ",
                    "implement ",
                    "upgrade ",
                    "wire ",
                    "add ",
                    "repair ",
                )
            ):

                patch["active_task"] = (
                    user_text.strip()[:240]
                )

                patch["checkpoint"] = (
                    "task_detected"
                )

                patch["next_move"] = (
                    "continue task implementation"
                )

        if not patch:
            return (
                self._get_working_state(session_id)
                or {}
            )

        if (
            patch.get("active_task")
            or patch.get("current_file")
            or patch.get("checkpoint")
            or patch.get("next_move")
        ):
            patch["updated_at"] = self._now_iso()

        self._update_working_state(
            session_id,
            patch,
        )

        return (
            self._get_working_state(session_id)
            or {}
        )

    def _replace_working_state(self, session_id: str, new_state: dict):
        session_id = self._safe_str(session_id).strip()

        if not session_id:
            return {}

        if not isinstance(new_state, dict):
            new_state = {}

        from datetime import datetime, timezone

        clean_state = dict(new_state)
        clean_state["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._set_working_state(session_id, clean_state)

        return clean_state


    def _archive_execution_state(
        self,
        session_id: str,
        execution_state: dict,
        command: str = "",
    ):
        try:
            from datetime import datetime, timezone

            execution_state = execution_state or {}

            completed_steps = (
                self.execution_loop.completed_step_titles(
                    execution_state
                )
            )

            failed_steps = (
                self.execution_loop.failed_step_titles(
                    execution_state
                )
            )

            if not completed_steps and not failed_steps:
                return

            if completed_steps == [
                "No saved execution plan found"
            ]:
                return

            archive_entry = {
                "status": str(
                    execution_state.get("status")
                    or ""
                ).strip(),
                "command": str(
                    command
                    or ""
                ).strip(),
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "last_action": str(
                    execution_state.get("last_action")
                    or ""
                ).strip(),
                "completed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            sessions = self.sessions._load_sessions()

            index = self.sessions._find(
                sessions,
                session_id,
            )

            if index is None:
                return

            history = (
                sessions[index].get("execution_history")
                or []
            )

            cleaned_history = []

            for item in history:
                if not isinstance(item, dict):
                    continue

                completed = item.get("completed_steps") or []

                if completed == [
                    "No saved execution plan found"
                ]:
                    continue

                if (
                    not completed
                    and not item.get("failed_steps")
                ):
                    continue

                cleaned_history.append(item)

            history = cleaned_history

            if not isinstance(history, list):
                history = []

            history.append(archive_entry)

            sessions[index]["execution_history"] = history[-25:]

            self.sessions._save_sessions(
                sessions,
                self.sessions.get_active_session_id(),
            )

        except Exception as e:
            exec_debug(
                "ARCHIVE EXECUTION STATE FAILED:",
                e,
            )

    def _finalize_execution_state(self, execution_state: dict | None = None) -> dict:
        execution_state = dict(execution_state or {})

        execution_state["status"] = "idle"
        execution_state["waiting"] = False
        execution_state["complete"] = False
        execution_state["active"] = False

        execution_state["steps"] = []
        execution_state["plan"] = []
        execution_state["current_index"] = 0
        execution_state["history"] = []

        execution_state["current_step"] = ""
        execution_state["current_step_title"] = ""
        execution_state["last_action"] = ""

        return execution_state

    def _reset_execution_state(self, session_id: str):
        previous_state = self._get_working_state(session_id) or {}

        last_success = self._safe_str(
            previous_state.get("last_success")
        ).strip()

        checkpoint = self._safe_str(
            previous_state.get("checkpoint")
        ).strip()

        last_success = ""
        checkpoint = ""

        self._replace_working_state(
            session_id,
            {
                "active_task": "",
                "current_file": "",
                "current_bug": "",
                "last_success": last_success,
                "next_move": "",
                "checkpoint": checkpoint,
            },
        )

        self._set_session_meta(
            session_id,
            "execution_state",
            {},
        )

        self._set_session_meta(
            session_id,
            "active_execution",
            {},
        )

        self._set_session_meta(
            session_id,
            "mission",
            {},
        )

        self._update_working_state(
            session_id,
            {
                "active_task": "",
                "current_file": "",
                "current_bug": "",
                "next_move": "",
                "checkpoint": "",
                "execution_status": "",
            },
        )

        try:
            sessions = self.sessions._load_sessions()

            index = self.sessions._find(
                sessions,
                session_id,
            )

            if index is not None:

                sessions[index]["execution_state"] = {}

                sessions[index]["active_execution"] = {}

                sessions[index]["working_state"] = {
                    "active_task": "",
                    "current_file": "",
                    "current_bug": "",
                    "last_success": last_success,
                    "next_move": "",
                    "checkpoint": "",
                    "updated_at": "",
                }

                sessions[index]["mission"] = {}

                if not isinstance(sessions[index].get("meta"), dict):
                    sessions[index]["meta"] = {}

                sessions[index]["meta"]["mission"] = {}

                self.sessions._save_sessions(
                    sessions,
                    self.sessions.get_active_session_id(),
                )

        except Exception as e:
            exec_debug(
                "RESET EXECUTION SESSION CLEAR FAILED:",
                e,
            )

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

            friendly_state_map = {
                "execution_cycle_complete": "continuity stabilization",
                "execution_complete": "execution pipeline stabilized",
                "retry_failed": "execution recovery and polish",
                "run_step": "step-by-step execution flow",
                "run_all": "autonomous execution mode",
            }

            def friendly(value):
                value = self._safe_str(value).strip()
                return friendly_state_map.get(value, value)

            if self._safe_str(state.get("active_task")):
                lines.append(
                    f"- Active task: {self._safe_str(state.get('active_task'))}"
                )

            if self._safe_str(state.get("current_file")):
                lines.append(
                    f"- Current file: {self._safe_str(state.get('current_file'))}"
                )

            if self._safe_str(state.get("current_bug")):
                lines.append(
                    f"- Current bug: {self._safe_str(state.get('current_bug'))}"
                )

            if self._safe_str(state.get("last_success")):
                lines.append(
                    f"- Last success: {friendly(state.get('last_success'))}"
                )

            if self._safe_str(state.get("next_move")):
                lines.append(
                    f"- Next move: {friendly(state.get('next_move'))}"
                )

            if self._safe_str(state.get("checkpoint")):
                lines.append(
                    f"- Checkpoint: {friendly(state.get('checkpoint'))}"
                )

            if not lines:
                return ""

            return "Working context:\n" + "\n".join(lines)

    def _build_mission_state(
        self,
        working_state=None,
        execution_state=None,
    ) -> dict:
        working_state = working_state if isinstance(working_state, dict) else {}
        execution_state = execution_state if isinstance(execution_state, dict) else {}

        active_task = self._safe_str(working_state.get("active_task")).strip()
        current_file = self._safe_str(working_state.get("current_file")).strip()
        current_bug = self._safe_str(working_state.get("current_bug")).strip()
        last_success = self._safe_str(working_state.get("last_success")).strip()
        next_move = self._safe_str(working_state.get("next_move")).strip()
        checkpoint = self._safe_str(working_state.get("checkpoint")).strip()

        execution_status = self._safe_str(execution_state.get("status")).strip()
        execution_goal = self._safe_str(execution_state.get("goal")).strip()

        invalid_execution_goal = (
            "respond normally" in execution_goal.lower()
        )

        if invalid_execution_goal:

            execution_status = ""
            execution_goal = ""

            execution_state = {}

        blockers = []
        priorities = []

        blocked_state_values = {
            "",
            "continuity_working",
            "working_state_resume_context",
            "no active work to resume.",
        }

        if last_success.lower() in blocked_state_values:
            last_success = ""

        if next_move.lower() in blocked_state_values:
            next_move = ""

        if checkpoint.lower() in blocked_state_values:
            checkpoint = ""

        if active_task.lower() in blocked_state_values:
            active_task = ""

        mission = "Stabilize Nova intelligence and autonomous execution."

        execution_is_complete = (
            execution_status in {"complete", "completed"}
            or execution_state.get("complete") is True
            or last_success == "execution_complete"
            or checkpoint == "execution_cycle_complete"
        )

        if "retry_failed" in next_move and execution_is_complete:
            next_move = "await_new_mission"
            priorities.append("Execution is complete. Await a new mission instead of retrying stale state.")

        elif "retry_failed" in next_move:
            blockers.append("Execution recovery is still leaking retry state.")
            priorities.append("Inspect failed execution steps before retry logic runs.")

        if "execution_cycle_complete" in checkpoint:
            priorities.append("Convert raw execution checkpoints into mission-aware summaries.")

        if "execution_complete" in last_success:
            priorities.append("Lock completed execution state so it does not resurrect as running.")

        if current_bug:
            blockers.append(current_bug)

        if current_file:
            priorities.append(f"Continue safely inside {current_file}.")

        if active_task:
            mission = active_task

        if not priorities:
            priorities.extend(
                [
                    "Improve continuity answers.",
                    "Restore memory dominance cleanly.",
                    "Strengthen autonomous planning and recovery.",
                ]
            )

        mission = self._safe_str(
            mission
        ).strip()

        if self._is_control_command_value(mission):
            mission = ""

        if self._is_control_command_value(next_move):
            next_move = ""

        recommended_next_move = (
            next_move
            if (
                next_move
                and next_move != "retry_failed"
                and execution_status
                in {
                    "running",
                    "adapting",
                    "waiting",
                }
            )
            else ""
        )

        return {
            "mission": mission,
            "priorities": priorities[:5],
            "blockers": blockers[:5],
            "recommended_next_move": recommended_next_move,
            "checkpoint": checkpoint,
            "last_success": last_success,
            "execution_status": execution_status,
            "execution_goal": execution_goal,
        }

    def _format_mission_state(
        self,
        mission_state=None,
    ) -> str:
        mission_state = mission_state if isinstance(mission_state, dict) else {}

        mission = self._safe_str(mission_state.get("mission")).strip()
        recommended_next_move = self._safe_str(
            mission_state.get("recommended_next_move")
        ).strip()

        priorities = mission_state.get("priorities")
        blockers = mission_state.get("blockers")

        priorities = priorities if isinstance(priorities, list) else []
        blockers = blockers if isinstance(blockers, list) else []

        lines = []

        if mission:
            lines.append(f"Mission: {mission}")

        if recommended_next_move:
            lines.append(f"Next move: {recommended_next_move}")

        if priorities:
            lines.append("")
            lines.append("Priorities:")
            for item in priorities[:5]:
                item = self._safe_str(item).strip()
                if item:
                    lines.append(f"- {item}")

        if blockers:
            lines.append("")
            lines.append("Blockers:")
            for item in blockers[:5]:
                item = self._safe_str(item).strip()
                if item:
                    lines.append(f"- {item}")

        return "\n".join(lines).strip()

    def _run_execution_next_move(self, active_task: str, next_move: str, session_id: str) -> str:
        active_task = self._safe_str(active_task).strip()
        next_move = self._safe_str(next_move).strip()
        session_id = self._safe_str(session_id).strip() or "default"

        combined_text = f"{next_move} {active_task}".strip().lower()

        move_type = "plan"

        if "build execution loop" in combined_text or "build_execution_loop" in combined_text:
            move_type = "plan"
        elif "verify execution loop" in combined_text or "verify_execution_loop" in combined_text:
            move_type = "verify_execution_loop"
        elif "persist execution result" in combined_text or "persist_execution_result" in combined_text:
            move_type = "persist_execution_result"
        elif "review execution result" in combined_text or "review_execution_result" in combined_text:
            move_type = "review_execution_result"

        if "fix this file" in combined_text:
            results = self.execution_handler.run_chain(
                NextMove(
                    id=f"{session_id}:apply_fix",
                    type="apply_file_fix",
                    payload={
                        "file_path": active_task,
                        "content": next_move,
                    },
                )
            )

            last_result = results[-1] if results else None

            if last_result and last_result.status == "success":
                return str(last_result.output)

            if last_result:
                return f"File fix failed:\n{last_result.error}"

            return "File fix produced no result."

        if "fix this function" in combined_text:
            return (
                "Function-level auto-fix trigger is ready.\n\n"
                "Send the exact function replacement code next, like:\n\n"
                "fix this function _run_execution_next_move in C:\\Users\\Owner\\nova\\nova_backend\\services\\chat_service.py\n"
                "```python\n"
                "def _run_execution_next_move(...):\n"
                "    ...\n"
                "```"
            )

        move = NextMove(
            id=f"{session_id}:chain",
            type="chain",
            payload={
                "next": [
                    {
                        "type": "log",
                        "payload": {
                            "task": active_task,
                            "raw": next_move,
                            "session_id": session_id,
                        },
                    },
                    {
                        "type": move_type,
                        "payload": {
                            "message": "Execution chain continued.",
                            "task": active_task,
                            "next_move": next_move,
                        },
                    },
                ]
            },
        )

        results = self.execution_handler.run_chain(move)
        last_result = results[-1] if results else None

        if last_result and last_result.status == "success":
            next_step_text = "review execution result and choose the next move"

            output = last_result.output

            if isinstance(output, dict):
                echo_data = output.get("echo")

                if isinstance(echo_data, dict):
                    current_next = str(echo_data.get("next_move") or "").strip().lower()

                    if current_next in {"build execution loop", "build_execution_loop"}:
                        next_step_text = "verify execution loop"
                    elif current_next in {"verify execution loop", "verify_execution_loop"}:
                        next_step_text = "persist execution result"
                    elif current_next in {"persist execution result", "persist_execution_result"}:
                        next_step_text = "choose next autonomous task"

            followup_results = []

            if next_step_text == "persist execution result":
                followup_move = NextMove(
                    id=f"{session_id}:persist",
                    type="persist_execution_result",
                    payload={
                        "task": active_task,
                        "source": move_type,
                        "result": last_result.output,
                    },
                )

                followup_results = self.execution_handler.run_chain(followup_move)

                if followup_results:
                    last_followup = followup_results[-1]

                    if last_followup and last_followup.status == "success":
                        last_result = last_followup

            total_steps = len(results) + len(followup_results)

            try:
                self._update_working_state(
                    session_id,
                    {
                        "next_move": next_step_text,
                        "last_execution_status": "success",
                        "last_execution_steps": total_steps,
                        "last_execution_output": last_result.output,
                    },
                )
            except Exception:
                pass

            return (
                f"Continuing: {active_task or 'saved task'}\n"
                f"Executed: {move_type}\n\n"
                f"Steps: {total_steps}\n"
                f"Next Move: {next_step_text}\n\n"
                f"Last Result:\n{last_result.output}"
            )

        if last_result:
            try:
                self._update_working_state(
                    session_id,
                    {
                        "last_execution_status": "failed",
                        "last_execution_steps": len(results),
                        "last_execution_error": last_result.error,
                    },
                )

            except Exception:
                pass

            # SELF-HEAL TRIGGER
            try:
                state = self._get_working_state(session_id) or {}
                attempts = int(state.get("self_heal_attempts") or 0)
            except Exception:
                attempts = 0

            if attempts < 3:
                try:
                    self._update_working_state(
                        session_id,
                        {
                            "self_heal_attempts": attempts + 1,
                            "next_move": "self_heal_fix_file",
                            "last_error": last_result.error,
                        },
                    )
                except Exception:
                    pass

            return (
                f"Continuing: {active_task or 'saved task'}\n"
                f"Execution failed: {move_type}\n\n"
                f"Steps: {len(results)}\n"
                f"Error:\n{last_result.error}"
            )

        return (
            f"Continuing: {active_task or 'saved task'}\n"
            f"Execution produced no result."
        )

    def _run_execution_autoloop(self, session_id: str, max_steps: int = 5) -> str:
        """
        Runs execution loop automatically with self-healing.
        """

        state = self._get_working_state(session_id) or {}

        active_task = self._safe_str(state.get("active_task"))
        next_move = self._safe_str(state.get("next_move"))

        if not active_task:
            return "No active task to execute."

        results_log = []

        for step in range(max_steps):
            if next_move == "self_heal_fix_file":
                error_text = self._safe_str(state.get("last_error"))

                fix_result = self._attempt_self_fix(
                    session_id=session_id,
                    active_task=active_task,
                    error_text=error_text,
                )

                results_log.append("SELF-HEAL ATTEMPT:\n" + fix_result)

            else:
                result = self._run_execution_next_move(
                    active_task=active_task,
                    next_move=next_move,
                    session_id=session_id,
                )

                results_log.append(result)

                self.execution_loop.record_history(
                    history_callback=self._record_execution_history,
                    session_id=session_id,
                    event_type="step_result",
                    details={
                        "step": step + 1,
                        "next_move": next_move,
                        "result": result,
                    },
                )

                if isinstance(result, str) and "Execution failed" in result:
                    fix_result = self._attempt_self_fix(
                        session_id=session_id,
                        active_task=active_task,
                        error_text=result,
                    )

                    results_log.append("AUTO-FIX ATTEMPT:\n" + fix_result)

                    retry_result = self._run_execution_next_move(
                        active_task=active_task,
                        next_move=next_move,
                        session_id=session_id,
                    )

                    results_log.append("RETRY RESULT:\n" + retry_result)

            state = self._get_working_state(session_id) or {}
            next_move = self._safe_str(state.get("next_move"))

            if not next_move:
                break

            if next_move.lower() in {
                "choose next autonomous task",
                "complete",
                "done",
            }:
                break

        return "\n\n--- AUTO LOOP ---\n\n".join(results_log)

    def _attempt_function_self_fix(self, session_id: str, active_task: str, error_text: str) -> str:
        """
        Safer self-fix path for function-scoped repairs.
        """

        session_id = self._safe_str(session_id).strip() or "default"
        active_task = self._safe_str(active_task).strip()
        error_text = self._safe_str(error_text).strip()

        if not active_task:
            return "Function self-fix skipped: no active task."

        try:
            fix_move = NextMove(
                id=f"{session_id}:function_auto_fix",
                type="apply_function_fix",
                payload={
                    "target": active_task,
                    "error": error_text,
                },
            )

            results = self.execution_handler.run_chain(fix_move)
            last = results[-1] if results else None

            if last and last.status == "success":
                return str(last.output)

            if last:
                return f"Function auto-fix failed:\n{last.error}"

            return "Function auto-fix produced no result."

        except Exception as e:
            return f"Function auto-fix exception:\n{str(e)}"

    def _record_execution_history(
        self,
        session_id: str,
        event_type: str,
        details: dict | None = None,
    ) -> None:
        session_id = self._safe_str(session_id).strip()
        event_type = self._safe_str(event_type).strip() or "execution_event"
        details = details if isinstance(details, dict) else {}

        if not session_id:
            return

        try:
            state = self._get_working_state(session_id) or {}
            history = state.get("execution_history")

            if not isinstance(history, list):
                history = []

            history.append(
                {
                    "type": event_type,
                    "details": details,
                }
            )

            self._update_working_state(
                session_id,
                {
                    "execution_history": history[-50:],
                },
            )

        except Exception:
            pass

    def _classify_execution_error(self, error_text: str) -> str:
        error_text_lc = self._safe_str(error_text).lower()

        if "indentationerror" in error_text_lc or "taberror" in error_text_lc:
            return "indentation"

        if "syntaxerror" in error_text_lc:
            return "syntax"

        if "modulenotfounderror" in error_text_lc or "importerror" in error_text_lc:
            return "import"

        if "nameerror" in error_text_lc:
            return "name"

        if "attributeerror" in error_text_lc:
            return "attribute"

        if "typeerror" in error_text_lc:
            return "type"

        if "keyerror" in error_text_lc:
            return "key"

        if "filenotfounderror" in error_text_lc:
            return "missing_file"

        return "unknown"

    def _attempt_self_fix(self, session_id: str, active_task: str, error_text: str) -> str:
        """
        Smart self-fix dispatcher.
        Tries safer function-level fix first, then falls back to file-level fix.
        """

        session_id = self._safe_str(session_id).strip() or "default"
        active_task = self._safe_str(active_task).strip()
        error_text = self._safe_str(error_text).strip()

        if not active_task:
            return "Auto-fix skipped: no active task."

        error_kind = self._classify_execution_error(error_text)

        if error_kind in {"import", "missing_file"}:
            return (
                f"Auto-fix paused: {error_kind} error needs file/dependency context.\n\n"
                f"Error:\n{error_text}"
            )

        function_fix_result = self._attempt_function_self_fix(
            session_id=session_id,
            active_task=active_task,
            error_text=error_text,
        )

        if "failed" not in function_fix_result.lower() and "exception" not in function_fix_result.lower():
            return function_fix_result

        try:
            fix_move = NextMove(
                id=f"{session_id}:file_auto_fix",
                type="apply_file_fix",
                payload={
                    "file_path": active_task,
                    "content": error_text,
                },
            )

            results = self.execution_handler.run_chain(fix_move)
            last = results[-1] if results else None

            if last and last.status == "success":
                return str(last.output)

            if last:
                return (
                    "Function auto-fix failed, then file auto-fix failed:\n\n"
                    f"Function result:\n{function_fix_result}\n\n"
                    f"File error:\n{last.error}"
                )

            return (
                "Function auto-fix failed, then file auto-fix produced no result.\n\n"
                f"Function result:\n{function_fix_result}"
            )

        except Exception as e:
            return (
                "Function auto-fix failed, then file auto-fix raised an exception:\n\n"
                f"Function result:\n{function_fix_result}\n\n"
                f"File exception:\n{str(e)}"
            )

    def _reinforce_memory(
        self,
        session_id: str,
        memory_text: str,
        category: str = "operational",
        amount: int = 1,
    ):

        memory_text = str(memory_text or "").strip()

        if not memory_text:
            return

        memories = self._get_memory_list() or []
        matched = False

        for mem in memories:
            if not isinstance(mem, dict):
                continue

            existing = str(
                mem.get("content")
                or mem.get("text")
                or ""
            ).strip()

            if existing.lower() == memory_text.lower():
                current_weight = float(mem.get("weight") or 1)
                mem["weight"] = current_weight + amount
                matched = True
                break

        if not matched:
            self.memory.add_memory(
                {
                    "content": memory_text,
                    "category": category,
                    "weight": amount,
                }
            )

    def _rank_memory_context(
        self,
        memories=None,
        user_text: str = "",
        working_state=None,
        execution_state=None,
        limit: int = 12,
        session_id: str = "",
        memory_items=None,
    ):

        if memories is None and memory_items is not None:
            memories = memory_items

        memories = memories or self._get_memory_list()
        working_state = working_state or {}
        execution_state = execution_state or {}

        text_lc = str(user_text or "").lower().strip()

        is_execution_chat = any(
            x in text_lc
            for x in (
                "run",
                "execute",
                "next",
                "continue",
                "retry",
                "auto fix",
                "autofix",
                "run_step",
                "run_all",
                "execution",
            )
        )

        casual_query = any(
            x in text_lc
            for x in (
                "hi",
                "hello",
                "hey",
                "yo",
                "sup",
                "what is",
                "who is",
                "tell me",
                "joke",
                "2+2",
                "how are you",
            )
        )

        operational_query = any(
            x in text_lc
            for x in (
                "continue",
                "resume",
                "next",
                "what next",
                "active task",
                "where are we",
                "current file",
                "fix",
                "execution",
                "run step",
                "run all",
            )
        )

        priority_terms = []

        if is_execution_chat:

            priority_terms.extend(
                [
                    str(working_state.get("active_task") or "").lower(),
                    str(working_state.get("current_file") or "").lower(),
                    str(working_state.get("current_bug") or "").lower(),
                    str(working_state.get("next_move") or "").lower(),
                    str(working_state.get("checkpoint") or "").lower(),
                ]
            )

            priority_terms.extend(
                [
                    str(execution_state.get("status") or "").lower(),
                    str(execution_state.get("goal") or "").lower(),
                    str(
                        execution_state.get("current_step_title")
                        or execution_state.get("current_step")
                        or ""
                    ).lower(),
                ]
            )

        priority_terms = [
            term
            for term in priority_terms
            if term
        ]

        has_real_state = any(
            [
                working_state.get("active_task"),
                working_state.get("current_file"),
                working_state.get("current_bug"),
                working_state.get("next_move"),
                working_state.get("checkpoint"),
                execution_state.get("steps"),
                execution_state.get("current_step"),
                execution_state.get("status") == "running",
            ]
        )

        ranked = []

        for index, memory in enumerate(memories):

            kind = ""
            category = ""
            content = ""
            created_at = ""
            updated_at = ""
            raw_weight = 1

            if isinstance(memory, dict):

                content = str(
                    memory.get("content")
                    or memory.get("text")
                    or memory.get("memory")
                    or memory.get("summary")
                    or ""
                ).strip()

                category = str(
                    memory.get("category")
                    or memory.get("type")
                    or memory.get("kind")
                    or ""
                ).lower()

                kind = str(
                    memory.get("kind")
                    or memory.get("type")
                    or memory.get("category")
                    or ""
                ).lower()

                created_at = str(
                    memory.get("created_at")
                    or ""
                ).lower()

                updated_at = str(
                    memory.get("updated_at")
                    or ""
                ).lower()

                raw_weight = memory.get(
                    "weight",
                    1,
                )

            else:

                content = str(memory or "").strip()

            if not content:
                continue

            content_lc = content.lower()

            blocked_runtime_memory_patterns = [
                "big butts",
                "cannot lie",
                "joke memory",
                "meme memory",
                "temporary joke",
            ]

            if any(
                pattern in content_lc
                for pattern in blocked_runtime_memory_patterns
            ):
                continue

            try:
                score = float(raw_weight)
            except Exception:
                score = 1.0

            for word in text_lc.split():

                if len(word) >= 4 and word in content_lc:
                    score += 2.0

            if (
                casual_query
                and not operational_query
                and (
                    "operational" in category
                    or "execution" in category
                    or "working" in category
                )
            ):
                score -= 25.0

            if is_execution_chat and "operational" in category:
                score += 15.0

            if (
                is_execution_chat
                and (
                    "working" in category
                    or "state" in category
                )
            ):
                score += 14.0

            if is_execution_chat and "execution" in category:
                score += 13.0

            if (
                is_execution_chat
                and (
                    "correction" in category
                    or "fix" in category
                )
            ):
                score += 12.0

            if (
                "profile" in category
                or "identity" in category
                or "preference" in category
            ):
                score += 10.0

            if (
                is_execution_chat
                and (
                    "project" in category
                    or "nova" in content_lc
                )
            ):
                score += 9.0



            if not has_real_state:

                blocked_categories = {
                    "operational",
                    "execution",
                    "working",
                }

                blocked_kinds = {
                    "goal",
                    "task",
                    "mission",
                }

                if (
                    category in blocked_categories
                    or kind in blocked_kinds
                ):
                    score -= 100.0

            for term in priority_terms:

                if term and term in content_lc:
                    score += 20.0

            if (
                "name is" in content_lc
                or "user's name" in content_lc
                or "user is" in content_lc
            ):
                score += 18.0

            if (
                "prefers" in content_lc
                or "from now on" in content_lc
                or "always" in content_lc
            ):
                score += 12.0

            if (
                "correction" in content_lc
                or "fixed" in content_lc
                or "do not" in content_lc
            ):
                score += 8.0

            stale_markers = [
                "outdated",
                "deprecated",
                "old approach",
                "no longer",
                "wrong",
                "contradicted",
                "ignore this",
                "do not use",
            ]

            if any(
                marker in content_lc
                for marker in stale_markers
            ):
                score -= 20.0

            if updated_at or created_at:
                score += 1.0

            ranked.append(
                {
                    "score": score,
                    "index": index,
                    "content": content,
                    "memory": memory,
                }
            )

        ranked.sort(
            key=lambda item: (
                item["score"],
                -item["index"],
            ),
            reverse=True,
        )

        try:

            should_debug_memory_dominance = any(
                (
                    isinstance(item, dict)
                    and isinstance(item.get("memory"), dict)
                    and self._safe_str(
                        item.get("memory", {}).get("category")
                    ).lower()
                    in {
                        "operational",
                        "execution",
                        "working",
                    }
                )
                for item in ranked[:5]
            )

            if should_debug_memory_dominance:

                print(
                    "[MEMORY DOMINANCE TOP]",
                    [
                        {
                            "score": item.get("score"),
                            "content": str(
                                item.get("content")
                                or ""
                            )[:120],
                        }
                        for item in ranked[:5]
                    ],
                )

        except Exception as e:

            exec_debug(
                "MEMORY_DOMINANCE_AUDIT_FAILED:",
                e,
            )

        top = ranked[: max(1, int(limit or 12))]

        return [
            item["memory"]
            for item in top
        ]

    def _memory_text_tokens(
        self,
        value: str,
    ) -> set[str]:

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

        return {
            token
            for token in tokens
            if token not in stop_words
        }

    def _format_memory_context(
        self,
        memory_items: list[dict],
        user_text: str = "",
    ) -> str:

        if hasattr(self, "runtime_cognitive_firewall"):
            memory_items = self.runtime_cognitive_firewall.filter_for_runtime(
                memory_items,
                user_text=user_text,
            )

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

    def _memory_text_tokens(
        self,
        value: str,
    ) -> set[str]:

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

        tokens = set(
            re.findall(r"[a-z0-9_]{2,}", text)
        )

        return {
            token
            for token in tokens
            if token not in stop_words
        }


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
        saved = self.artifacts.save_artifact(artifact)

        if isinstance(saved, dict):
            return saved

        if saved:
            return artifact

        return artifact

    except Exception as e:
        exec_debug("ARTIFACT SAVE FAILED:", e)
        exec_debug("ARTIFACT PAYLOAD:", artifact)

        return artifact

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

            filename = (
                f"generated_{uuid.uuid4().hex}.png"
            )

            save_path = os.path.join(
                self.uploads_dir,
                filename,
            )

            with open(save_path, "wb") as f:
                f.write(image_bytes)

            image_url = f"/api/uploads/{filename}"

            saved_artifact = None

            try:
                saved_artifact = self.artifacts.create_artifact(
                    kind="image",
                    type="image_generation",
                    title="Generated image",
                    body=prompt,
                    summary=f"Generated image for: {prompt}",
                    preview=image_url,
                    session_id=session_id,
                    source="generated",
                    image_url=image_url,
                    prompt=prompt,
                    revised_prompt="",
                    parent_id=parent_artifact_id or None,
                    meta={
                        "image_url": image_url,
                        "prompt": prompt,
                        "generation_mode": "text_to_image",
                        "source_type": source_type,
                    },
                )
            except Exception as exc:
                exec_debug("IMAGE ARTIFACT FALLBACK SAVE FAILED:", exc)

            try:
                if (
                    session_id
                    and hasattr(self, "artifact_service")
                    and self.artifact_service
                ):
                    self.artifact_service.sync_artifacts_to_session(
                        session_id
                    )
            except Exception as e:
                exec_debug("FORCED ARTIFACT SYNC FAILED:", e)
            assistant_image_message = {
                "role": "assistant",
                "text": f"Generated image for: {prompt}",
                "attachments": [
                    {
                        "id": filename,
                        "filename": filename,
                        "stored_name": filename,
                        "url": image_url,
                        "mime_type": "image/png",
                        "size": len(image_bytes),
                    }
                ],
                "meta": {
                    "source": "image_generation",
                    "artifact_id": (
                        saved_artifact.get("id", "")
                        if isinstance(saved_artifact, dict)
                        else ""
                    ),
                },
            }
            try:
                self.sessions.append_message(
                    session_id,
                    assistant_image_message,
                )
            except Exception as exc:
                exec_debug(
                    "IMAGE SESSION MESSAGE SAVE FAILED:",
                    exc,
                )

            refreshed_session = self.sessions.get_session(
                session_id
            )

            return {
                "ok": True,
                "skip_rewrite": True,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": f"Generated image for: {prompt}",
                    "image_url": image_url,
                },
                "image_url": image_url,
                "prompt": prompt,
                "revised_prompt": "",
                "saved_artifact": saved_artifact,
                "session": refreshed_session,
            }

        except Exception as e:
            exec_debug("IMAGE GENERATION FAILED:", e)

            return {
                "ok": False,
                "skip_rewrite": True,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": f"Image generation failed: {e}",
                },
                "error": str(e),
                "image_url": "",
                "prompt": prompt,
                "revised_prompt": "",
                "saved_artifact": None,
                "session": self._get_session_payload(
                    session_id
                ),
            }

    def _handle_web_fetch(self, url: str, session_id: str = "") -> dict:
        raw_url = self._safe_str(url)
        normalized_url = raw_url

        if normalized_url and not re.match(
            r"^https?://",
            normalized_url,
            re.IGNORECASE,
        ):
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
            if (
                hasattr(self.web, "build_artifact_payload")
                and callable(self.web.build_artifact_payload)
            ):
                artifact = self.web.build_artifact_payload(result) or {}

        except Exception as e:
            artifact = {
                "kind": "web_result",
                "title": self._safe_str(result.get("title"))
                or normalized_url,
                "summary": self._safe_str(result.get("summary")),
                "body": self._safe_str(result.get("content")),
                "preview": self._safe_str(result.get("preview")),
                "source_url": self._safe_str(
                    result.get("final_url")
                    or result.get("url")
                    or normalized_url
                ),
                "meta": {
                    "description": self._safe_str(
                        result.get("description")
                    ),
                    "site_name": self._safe_str(
                        result.get("site_name")
                    ),
                    "domain": self._safe_str(result.get("domain")),
                    "content": self._safe_str(result.get("content")),
                    "url": self._safe_str(
                        result.get("final_url")
                        or result.get("url")
                        or normalized_url
                    ),
                    "status_code": result.get("status_code"),
                    "ssl_verified": result.get("ssl_verified"),
                    "artifact_build_error": str(e),
                },
                "viewer": {
                    "kind": "web_result",
                    "title": self._safe_str(result.get("title"))
                    or normalized_url,
                    "body": self._safe_str(result.get("content")),
                    "analysis_text": self._safe_str(
                        result.get("summary")
                    ),
                    "bullets": self._safe_list(
                        result.get("bullets")
                    ),
                    "links": self._safe_list(result.get("links")),
                    "images": self._safe_list(result.get("images")),
                    "source_url": self._safe_str(
                        result.get("final_url")
                        or result.get("url")
                        or normalized_url
                    ),
                },
            }

        if isinstance(artifact, dict):
            artifact["session_id"] = (
                session_id or artifact.get("session_id", "")
            )
            artifact.setdefault("created_at", fetched_at)
            artifact["updated_at"] = fetched_at

        artifact = self._upgrade_web_artifact_payload(
            artifact=artifact,
            result=result,
            url=normalized_url,
        )

        saved_artifact = (
            self._save_artifact_fallback(artifact)
            if artifact
            else None
        )

        final_artifact = self._upgrade_web_artifact_payload(
            artifact=saved_artifact or artifact,
            result=result,
            url=normalized_url,
        )

        summary = (
            self._safe_str(final_artifact.get("summary"))
            if isinstance(final_artifact, dict)
            else ""
        )

        body = (
            self._safe_str(final_artifact.get("body"))
            if isinstance(final_artifact, dict)
            else ""
        )

        title = (
            self._safe_str(final_artifact.get("title"))
            if isinstance(final_artifact, dict)
            else normalized_url
        )

        viewer = (
            self._safe_dict(final_artifact.get("viewer"))
            if isinstance(final_artifact, dict)
            else {}
        )

        meta = (
            self._safe_dict(final_artifact.get("meta"))
            if isinstance(final_artifact, dict)
            else {}
        )

        source_url = (
            self._safe_str(meta.get("source_url"))
            or self._safe_str(
                result.get("final_url")
                or result.get("url")
                or normalized_url
            )
        )

        source_urls = []

        if source_url:
            source_urls.append(source_url)

        return {
            "ok": bool(result.get("ok", True)),
            "text": summary or f"Fetched {title}",
            "artifact": final_artifact,
            "viewer": viewer,
            "url": self._safe_str(
                result.get("final_url")
                or result.get("url")
                or normalized_url
            ),
            "source_url": source_url,
            "source_urls": source_urls,
            "title": title,
            "summary": summary,
            "body": body,
            "meta": meta,
            "debug": {
                "route_taken": "web_fetch",
                "status_code": result.get("status_code"),
                "artifact_kind": (
                    self._safe_str(final_artifact.get("kind"))
                    if isinstance(final_artifact, dict)
                    else "web_result"
                ),
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

        route = self._safe_str(
            decision.get("route")
        ).lower()

        tool_locked_routes = {
            self.ROUTE_WEB_FETCH,
            self.ROUTE_IMAGE_GENERATION,
        }

        if route in tool_locked_routes:
            memory_context = ""
            working_context_block = ""

        working_state = (
            self._get_working_state(session_id)
            or {}
        )

        execution_state = (
            self._get_session_meta(
                session_id,
                "execution_state",
            )
            or {}
        )

        has_real_state = any([
            working_state.get("active_task"),
            working_state.get("current_file"),
            working_state.get("current_bug"),
            working_state.get("next_move"),
            working_state.get("checkpoint"),
            execution_state.get("steps"),
            execution_state.get("current_step"),
            execution_state.get("status") == "running",
        ])

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

            text = self._safe_str(
                item.get("text") or item.get("content")
            )

            key = text.lower().strip()

            blocked_memory_values = {
                "",
                "continuity_working",
                "working_state_resume_context",
                "no active work to resume.",
            }

            if key in blocked_memory_values:
                return

            if not key or key in seen:
                return

            seen.add(key)
            selected_memory.append(item)

        # =========================
        # PINNED MEMORY FIRST
        # =========================

        for item in memory_items:

            if not isinstance(item, dict):
                continue

            if not item.get("pinned"):
                continue

            category = self._safe_str(
                item.get("category")
            ).lower()

            kind = self._safe_str(
                item.get("kind")
            ).lower()

            if not has_real_state:

                blocked_categories = {
                    "operational",
                    "execution",
                    "working",
                }

                blocked_kinds = {
                    "goal",
                    "task",
                    "mission",
                }

                identity_keywords = {
                    "name",
                    "identity",
                    "profile",
                    "user",
                }

                if (
                    category in identity_keywords
                    or kind in identity_keywords
                ):
                    add_memory_item(item)
                    continue

                identity_keywords = {
                    "name",
                    "identity",
                    "profile",
                    "user",
                    "preference",
                }

                if (
                    category in identity_keywords
                    or kind in identity_keywords
                ):
                    cleaned_memory.append(item)
                    continue

                if (
                    category in blocked_categories
                    or kind in blocked_kinds
                ):
                    continue

            add_memory_item(item)

        # =========================
        # IMPORTANT MEMORY TYPES
        # =========================

        for item in memory_items:

            if not isinstance(item, dict):
                continue

            if item.get("pinned"):
                continue

            kind = self._safe_str(
                item.get("kind")
            ).lower()

            if not has_real_state and kind in {
                "goal",
                "task",
                "mission",
            }:
                continue

            if not has_real_state and kind in {
                "profile",
                "identity",
                "preference",
            }:
                add_memory_item(item)
                continue

            if kind in [
                "preference",
                "goal",
                "project",
                "profile",
            ]:
                add_memory_item(item)

        # =========================
        # HIGH WEIGHT MEMORIES
        # =========================

        for item in memory_items:

            if not isinstance(item, dict):
                continue

            if item in selected_memory:
                continue

            category = self._safe_str(
                item.get("category")
            ).lower()

            kind = self._safe_str(
                item.get("kind")
            ).lower()

            if not has_real_state:

                blocked_categories = {
                    "operational",
                    "execution",
                    "working",
                }

                blocked_kinds = {
                    "goal",
                    "task",
                    "mission",
                }

                if (
                    category in blocked_categories
                    or kind in blocked_kinds
                ):
                    continue

            try:
                weight_num = float(
                    item.get("weight", 1)
                )

            except Exception:
                weight_num = 1.0

            if weight_num >= 2:
                add_memory_item(item)

        # =========================
        # FILL REMAINING SLOTS
        # =========================

        for item in memory_items:

            if len(selected_memory) >= 10:
                break

            category = self._safe_str(
                item.get("category")
            ).lower()

            kind = self._safe_str(
                item.get("kind")
            ).lower()

            if not has_real_state:

                blocked_categories = {
                    "operational",
                    "execution",
                    "working",
                }

                blocked_kinds = {
                    "goal",
                    "task",
                    "mission",
                }

                if (
                    category in blocked_categories
                    or kind in blocked_kinds
                ):
                    continue

            add_memory_item(item)

        memory_block = self._format_memory_context(
            selected_memory,
            user_text=user_text,
        )

        if not has_real_state:

            cleaned_memory = []

            blocked_categories = {
                "operational",
                "execution",
                "working",
            }

            blocked_kinds = {
                "goal",
                "task",
                "mission",
            }

            for item in selected_memory:

                if not isinstance(item, dict):
                    continue

                category = self._safe_str(
                    item.get("category")
                ).lower()

                kind = self._safe_str(
                    item.get("kind")
                ).lower()

                if (
                    category in blocked_categories
                    or kind in blocked_kinds
                ):
                    continue

                cleaned_memory.append(item)

            selected_memory = cleaned_memory

        self._last_used_memory_items = selected_memory

        if memory_context:
            memory_block = self._safe_str(memory_context)

        session = self._get_session_payload(session_id)
        messages = (
            session.get("messages", [])
            if isinstance(session, dict)
            else []
        )

        cleaned_messages = []

        for msg in messages[-8:]:

            if not isinstance(msg, dict):
                continue

            role = self._safe_str(msg.get("role"))
            text = self._safe_str(msg.get("text"))

            if not role or not text:
                continue

            lowered = text.lower()

            if role == "assistant":

                blocked_patterns = [
                    "mission:",
                    "working state:",
                    "next move:",
                    "target file:",
                    "resumed context",
                    "we're still lined up",
                    "focus:",
                    "priorities:",
                ]

                if any(p in lowered for p in blocked_patterns):
                    continue

            cleaned_messages.append(msg)

        recent_lines = []

        for msg in cleaned_messages:

            role = self._safe_str(msg.get("role"))
            text = self._safe_str(msg.get("text"))

            if not role or not text:
                continue

            recent_lines.append(f"{role}: {text}")

        recent_block = "\n".join(recent_lines)

        memory_style_block = ""
        try:
            memory_text = (
                str(memory_block or "")
                + " "
                + str(memory_context or "")
            ).lower()

            if (
                "smff" in memory_text
                or "full-file" in memory_text
                or "full file" in memory_text
                or "powershell" in memory_text
                or "direct answers" in memory_text
            ):
                memory_style_block = (
                    "USER STYLE OVERRIDE FROM MEMORY:\n"
                    "- When helping with code, respond in SMFF style.\n"
                    "- Give full-file or full-block replacements instead of tiny snippets.\n"
                    "- Include exact file paths when useful.\n"
                    "- Use PowerShell commands for Windows steps.\n"
                    "- Be direct, practical, and avoid unnecessary back-and-forth."
                )

        except Exception as e:
            exec_debug("MEMORY_STYLE_INJECTION_ERROR:", e)

        parts = []

        if memory_block:
            parts.append("MEMORY CONTEXT:\n" + memory_block)

        if working_context_block:
            parts.append("WORKING CONTEXT:\n" + working_context_block)

        if recent_block:
            parts.append("RECENT CONVERSATION:\n" + recent_block)

        if memory_style_block:
            parts.append(memory_style_block)

        parts.append("USER MESSAGE:\n" + user_text)

        return "\n\n".join(parts).strip()

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

            return self._get_session_payload(created_id)

        return self._get_session_payload(session_id)

    def _execute_current_step(
        self,
        execution: dict,
        user_text: str,
        session_id: str = "",
        attachments=None,
    ) -> dict:

        attachments = attachments or []

        execution = self._normalize_execution_state(
            execution or {}
        )

        steps = execution.get("steps") or []

        current_index = self._execution_current_index(
            execution
        )

        # =========================
        # EXECUTION COMPLETE
        # =========================

        if (
            steps
            and current_index >= len(steps)
            and execution.get("status") != "failed"
        ):

            execution = self._sync_execution_state(
                execution=execution,
                current_index=len(steps),
                status="complete",
                current_step="complete",
                progress=len(steps),
            )

            execution["current_step_title"] = (
                "complete"
            )

            execution["complete"] = True

            execution.setdefault(
                "step_results",
                [],
            )

            self._update_working_state(
                session_id,
                {
                    "next_move": "",
                    "active_task": "",
                    "current_file": "",
                    "current_bug": "",
                    "checkpoint": (
                        "execution_complete"
                    ),
                    "last_success": (
                        self._safe_str(
                            execution.get("goal")
                        )
                        or "execution_complete"
                    ),
                    "execution_status": (
                        "complete"
                    ),
                },
            )

            return {
                "execution": execution,
                "step_output": (
                    "No remaining execution step."
                ),
                "saved_artifact": {
                    "kind": "execution",
                    "title": (
                        self._safe_str(
                            execution.get("goal")
                        )
                        or "Execution"
                    ),
                    "body": self._render_execution(
                        execution
                    ),
                    "execution": execution,
                    "meta": {
                        "execution": execution,
                        "execution_id": (
                            self._safe_str(
                                execution.get("id")
                            )
                        ),
                        "status": (
                            self._safe_str(
                                execution.get(
                                    "status"
                                )
                            )
                            or "complete"
                        ),
                        "progress": execution.get(
                            "progress",
                            len(steps),
                        ),
                        "current_step": (
                            self._safe_str(
                                execution.get(
                                    "current_step"
                                )
                            )
                            or "complete"
                        ),
                        "goal": self._safe_str(
                            execution.get("goal")
                        ),
                    },
                },
            }

        # =========================
        # CURRENT STEP
        # =========================

        current_step = (
            steps[current_index] or {}
        )

        step_title = (
            self._safe_str(
                current_step.get("title")
            )
            or f"Step {current_index + 1}"
        )

        goal = self._safe_str(
            execution.get("goal")
        )

        execution.setdefault(
            "step_results",
            [],
        )

        system_prompt = (
            "You are executing one step in "
            "Nova's task engine. "
            "Be concrete, operational, "
            "and brief. "
            "Return useful progress for "
            "the current step only."
        )

        user_prompt_parts = [
            f"Goal: {goal}",
            (
                f"Current step "
                f"({current_index + 1}/{len(steps)}): "
                f"{step_title}"
            ),
        ]

        if user_text.strip():

            user_prompt_parts.append(
                f"Latest user input: {user_text}"
            )

        if attachments:

            attachment_lines = []

            for item in attachments:

                if not isinstance(item, dict):
                    continue

                name = self._safe_str(
                    item.get("filename")
                    or item.get("name")
                    or item.get("stored_name")
                )

                url = self._safe_str(
                    item.get("url")
                )

                mime_type = self._safe_str(
                    item.get("mime_type")
                    or item.get("mime")
                )

                bits = [
                    bit
                    for bit in [
                        name,
                        mime_type,
                        url,
                    ]
                    if bit
                ]

                if bits:

                    attachment_lines.append(
                        " - " + " | ".join(bits)
                    )

            if attachment_lines:

                user_prompt_parts.append(
                    "Attachments:\n"
                    + "\n".join(
                        attachment_lines
                    )
                )

        user_prompt = "\n\n".join(
            part
            for part in user_prompt_parts
            if part
        )

        step_output = ""

        tool_bundle = {}

        try:

            response = (
                self.client.responses.create(
                    model=self.chat_model,
                    input=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                )
            )

            step_output = (
                self._extract_text_response(
                    response
                ).strip()
            )

        except Exception as exc:

            step_output = (
                f"Step execution failed: {exc}"
            )

        if not step_output:

            step_output = (
                f"Completed step: {step_title}"
            )

        step_result = {
            "step_index": current_index,
            "step_title": step_title,
            "output": step_output,
            "completed_at": self._iso_now(),
        }

        execution["step_results"].append(
            step_result
        )

        next_index = max(
            0,
            min(
                current_index + 1,
                len(steps),
            ),
        )

        # =========================
        # COMPLETE VS NEXT STEP
        # =========================

        if next_index >= len(steps):

            execution = self._sync_execution_state(
                execution=execution,
                current_index=len(steps),
                status="complete",
                current_step="complete",
                progress=len(steps),
            )

            execution["current_step_title"] = (
                "complete"
            )

            execution["complete"] = True

        else:

            next_step = (
                steps[next_index] or {}
            )

            execution = self._sync_execution_state(
                execution=execution,
                current_index=next_index,
                status="running",
                current_step=(
                    self._safe_str(
                        next_step.get("title")
                    )
                    or (
                        f"Step "
                        f"{next_index + 1}"
                    )
                ),
                progress=max(
                    0,
                    next_index,
                ),
            )

            next_step_title = (
                self._safe_str(
                    next_step.get("title")
                )
                or (
                    f"Step "
                    f"{next_index + 1}"
                )
            )

            execution["current_step"] = (
                next_step_title
            )

            execution["current_step_title"] = (
                next_step_title
            )

        artifact_payload = {
            "kind": "execution",
            "title": (
                goal or "Execution"
            ),
            "body": self._render_execution(
                execution
            ),
            "execution": execution,
            "meta": {
                "execution": execution,
                "goal": goal,
                "step_index": current_index,
                "step_title": step_title,
                "execution_id": (
                    self._safe_str(
                        execution.get("id")
                    )
                ),
                "tool_bundle": (
                    tool_bundle or {}
                ),
                "status": self._safe_str(
                    execution.get("status")
                ),
                "progress": execution.get(
                    "progress",
                    0,
                ),
                "current_step": (
                    self._safe_str(
                        execution.get(
                            "current_step"
                        )
                    )
                ),
            },
        }

        # =========================
        # UNLOCK EXECUTION
        # =========================

        execution["lock"] = False

        self._set_session_meta(
            session_id,
            "execution_state",
            execution,
        )

        self._save_active_execution(
            session_id,
            execution,
        )

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
        import os
        import re

        text = self._safe_str(text)

        traceback_paths = re.findall(
            r'File\s+["\']([^"\']+?\.py)["\']',
            text,
            re.IGNORECASE,
        )

        if traceback_paths:
            project_paths = [
                p for p in traceback_paths
                if "\\nova\\" in p.lower() or "/nova/" in p.lower()
            ]

            chosen_path = project_paths[-1] if project_paths else traceback_paths[-1]
            return chosen_path.strip().rstrip(".,:;)]}")

        windows_py_match = re.search(r"([A-Za-z]:\\[^\n\r\t\"']+?\.py)\b", text)
        if windows_py_match:
            return windows_py_match.group(1).strip().rstrip(".,:;)]}")

        windows_path_match = re.search(r"([A-Za-z]:\\[^\n\r\t\"']+)", text)
        if windows_path_match:
            raw = windows_path_match.group(1).strip()
            raw = re.split(
                r"\s+error\s*:|\s+traceback\s*:|\s+bug\s*:",
                raw,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip()
            return raw.rstrip(".,:;)]}")

        py_path_match = re.search(r"([A-Za-z0-9_./\\-]+\.py)\b", text)
        if py_path_match:
            raw = py_path_match.group(1).strip().rstrip(".,:;)]}")
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

        working_state = execution.get("working_state") or {}

        path = (
            self._guess_path_from_text(user_text)
            or self._guess_path_from_text(self._safe_str(execution.get("goal")))
            or working_state.get("detected_traceback_file_path", "")
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

        # =============================
        # FIX INTENT DETECTION
        # =============================

        is_fix_intent = any(x in lowered for x in [
            "fix this",
            "fix this file",
            "fix bug",
            "fix error",
            "fix",
            "debug",
            "broken",
            "not working",
        ])

        if "apply fix" in lowered:
            return {
                "tool_name": "apply_pending_fix",
                "args": {},
                "reason": "user confirmed apply fix",
            }

        if path and is_fix_intent:
            return {
                "tool_name": "auto_fix_file",
                "args": {"path": path, "user_text": user_text},
                "reason": "fix intent with file path detected",
            }

        if is_fix_intent and not path:
            return {
                "tool_name": "bug_intake",
                "args": {"user_text": user_text},
                "reason": "fix intent without file path",
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
            if tool_name == "bug_intake":
                return {
                    "ok": True,
                    "tool_name": "bug_intake",
                    "result": (
                        "Send the file path and the exact error.\n\n"
                        "Use:\n"
                        "fix this file C:\\Users\\Owner\\nova\\path\\file.py\n"
                        "error: paste the traceback or broken behavior"
                    ),
                }

            if tool_name == "auto_fix_file":
                path = self._safe_str(args.get("path")).strip()
                user_text = self._safe_str(args.get("user_text")).strip()

                return {
                    "ok": True,
                    "tool_name": "auto_fix_file",
                    "path": path,
                    "user_text": user_text,
                    "result": (
                        f"Auto-fix target detected:\n"
                        f"{path}\n\n"
                        f"Next: generate pending fix from this file and bug details."
                    ),
                }

            if tool_name == "apply_pending_fix":
                return {
                    "ok": True,
                    "tool_name": "apply_pending_fix",
                    "result": "Apply-fix command detected. Next: wire this to pending_fix_code.",
                }

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
            exec_debug("MEMORY CLEANUP FAILED:", e)

def _chatservice_archive_execution_state_patch(
    self,
    session_id: str,
    execution_state: dict | None = None,
    command: str = "",
) -> None:
    try:
        return None
    except Exception:
        return None


ChatService._archive_execution_state = _chatservice_archive_execution_state_patch

def _nova_runtime_handle_image_generation(
    self,
    prompt: str,
    session_id: str = "",
    parent_artifact_id: str = "",
    source_type: str = "generated",
) -> dict:
    print("RUNTIME IMAGE HIT PROMPT =", repr(prompt))

    saved_artifact = None

    regen_commands = {
        "regen",
        "regenerate",
        "redo image",
        "make another",
        "another image",
    }

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

        if self._safe_str(prompt).strip().lower() not in regen_commands:
            self._set_session_meta(
                session_id,
                "last_image_prompt",
                prompt,
            )

        self._set_session_meta(
            session_id,
            "last_image_url",
            image_url,
        )

        try:
            saved_artifact = self.artifacts.save_artifact({
                "kind": "image_generation",
                "type": "image_generation",
                "title": "Generated image",
                "body": prompt,
                "summary": f"Generated image for: {prompt}",
                "preview": image_url,
                "session_id": session_id,
                "source": source_type,
                "image_url": image_url,
                "prompt": prompt,
                "revised_prompt": "",
                "parent_id": parent_artifact_id or None,
                "meta": {
                    "image_url": image_url,
                    "prompt": prompt,
                    "generation_mode": "text_to_image",
                    "source_type": source_type,
                },
            })

            exec_debug("IMAGE ARTIFACT RESULT:", saved_artifact)

        except Exception as e:
            exec_debug("IMAGE ARTIFACT SAVE FAILED:", e)
            exec_debug("IMAGE ARTIFACT RESULT:", saved_artifact)

        except Exception as e:
            exec_debug("IMAGE ARTIFACT SAVE FAILED:", e)

        return {
            "ok": True,
            "skip_rewrite": True,
            "skip_cleanup": True,
            "skip_post_processing": True,
            "assistant_message": {
                "role": "assistant",
                "text": f"Generated image for: {prompt}",
                "image_url": image_url,
            },
            "image_url": image_url,
            "prompt": prompt,
            "revised_prompt": "",
            "saved_artifact": saved_artifact,
            "session": self._get_session_payload(session_id),
        }

    except Exception as e:
        exec_debug("IMAGE GENERATION FAILED:", e)

        return {
            "ok": False,
            "skip_rewrite": True,
            "skip_cleanup": True,
            "skip_post_processing": True,
            "assistant_message": {
                "role": "assistant",
                "text": f"Image generation failed: {e}",
            },
            "error": str(e),
            "image_url": "",
            "prompt": prompt,
            "revised_prompt": "",
            "saved_artifact": saved_artifact,
            "session": self._get_session_payload(session_id),
        }

ChatService._handle_image_generation = _nova_runtime_handle_image_generation

# ============================================================
# CHAT SERVICE METHOD BRIDGE
# Repairs methods that were accidentally defined outside class.
# ============================================================
# SAFE STATIC METHOD REGISTRY ONLY
CHAT_SERVICE_METHODS = [
    "_handle_image_generation",
]

for name in CHAT_SERVICE_METHODS:
    if hasattr(ChatService, name):
        continue
    obj = globals().get(name)
    if callable(obj):
        setattr(ChatService, name, obj)
