from __future__ import annotations

import base64
import os
import re
import uuid
import logging
import shutil
import tempfile
import py_compile


from nova_backend.services.execution_bridge_service import ExecutionBridgeService
from nova_backend.services.chat.handlers.execution_handler import ExecutionHandler
from nova_backend.services.planner.decision_service import DecisionService
from nova_backend.core.nova_orchestrator import NovaOrchestrator
from nova_backend.services.chat.response import ChatResponseHandler
from nova_backend.services.chat.project_brain import install_project_brain_patch
from nova_backend.services.chat.execution import ChatExecutionHandler
from nova_backend.services.chat.router import ChatRouter
from nova_backend.services.planner_service import PlannerService
from nova_backend.services.execution.service import ExecutionService
from nova_backend.services.intelligence.router import IntelligenceRouter
from nova_backend.services.auto_fix.service import AutoFixService
from nova_backend.services.error_reporting_service import ErrorReportingService
from nova_backend.services.response_mojibake_cleanup_service import ResponseMojibakeCleanupService
from nova_backend.services.chat_response_cleanup_service import ChatResponseCleanupService
from nova_backend.services.chat_response_policy_service import ChatResponsePolicyService
from nova_backend.services.attachment_analysis_service import AttachmentAnalysisService
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List
from nova_backend.services.accidental_input_guard_service import AccidentalInputGuardService
from nova_backend.services.execution_handler import (
    ExecutionHandler,
    NextMove,
    default_executor,
)
from nova_backend.services.chat_execution_service import (
    chat_execution_service,
)
from nova_backend.services.execution_mutation_service import (
    ExecutionMutationService,
)
from nova_backend.services.chat.execution_patches import (
    install_execution_planner_runtime_patches,
)
from nova_backend.core.nova_orchestrator import (
    NovaOrchestrator,
)
from openai import OpenAI
from nova_backend.services.model_gateway_service import (
    chat_completions_create,
    responses_create,
)
from nova_backend.services.repair_execution_service import RepairExecutionService
from nova_backend.services.execution_orchestrator_service import ExecutionOrchestratorService
from nova_backend.services.execution_step_service import ExecutionStepService
from nova_backend.services.execution_approval_service import ExecutionApprovalService
from nova_backend.models.session import new_message
from nova_backend.services.agent_service import AgentService
from nova_backend.services.artifact_service import ArtifactService
from nova_backend.services.autonomy_service import AutonomyService
from nova_backend.services.memory_ranker_service import MemoryRankerService
from nova_backend.services.memory_service import MemoryService
from nova_backend.services.error_reporting_service import (
    ErrorReportingService,
)
from nova_backend.services.response_rewrite_service import ResponseRewriteService
from nova_backend.services.nova_behavior_signal_builder import (
    behavior_signal_builder,
)
from nova_backend.services.image_generation_runtime_service import (
    install_image_generation_runtime,
)
from nova_backend.services.runtime_uploads_normalizer_service import (
    RuntimeUploadsNormalizerService,
)
from nova_backend.services.attachment_web_suppression_service import (
    install_attachment_web_suppression,
)
from nova_backend.services.token_usage_finalize_service import (
    install_token_usage_finalize_wrapper,
)
from nova_backend.services.nova_behavior_observer import (
    behavior_observer,
)
from nova_backend.services.recon_service import ReconService
from nova_backend.services.session_service import SessionService
from nova_backend.services.web_service import WebService
from nova_backend.services.tool_service import ToolService
from nova_backend.services.intent_service import IntentService
from nova_backend.services.execution_loop_service import ExecutionLoopService
from nova_backend.services.brain.brain_core import BrainCore
from nova_backend.services.brain.strategy import StrategyEngine
from nova_backend.services.memory.memory_core import MemoryCore
from nova_backend.services.execution.executor import Executor
from nova_backend.services.python_runner_service import PythonRunnerService
from nova_backend.services.auth_context import get_current_user_id
from nova_backend.services.upload_ownership_service import UploadOwnershipService
from nova_backend.services.runtime_bootstrap import (
    RuntimeBootstrap,
)
from nova_backend.services.runtime_cognitive_firewall import (
    RuntimeCognitiveFirewall,
)
from nova_backend.services.non_web_source_leak_guard_service import (
    install_non_web_source_leak_guard,
)
from nova_backend.services.runtime_cognitive_injection_service import (
    RuntimeCognitiveInjectionService,
)
from nova_backend.services.nova_self_improvement_coordinator import (
    process_behavior_observation,
)
from nova_backend.services.chat_turn_pipeline import build_chat_turn_from_request, build_model_messages

logger = logging.getLogger("nova.execution")
DEBUG_EXECUTION = False

def exec_debug(*args):
    if DEBUG_EXECUTION:
        logger.debug(" ".join(str(arg) for arg in args))

    def _observe_response_behavior(
        self,
        user_text="",
        assistant_text="",
        context=""
    ):
        """
        Observe completed response behavior.

        Learning failures must never affect chat.
        """

        try:

            evaluation = (
                behavior_signal_builder.build(
                    user_text=user_text,
                    assistant_text=assistant_text,
                    context=context,
                )
            )

            print(
                "[NOVA BEHAVIOR EVALUATION DEBUG]",
                evaluation
            )

            result = (
                behavior_observer.observe(
                    evaluation
                )
            )

            print(
                "[NOVA BEHAVIOR OBSERVER RESULT]",
                result
            )


            try:

                improvement = (
                    process_behavior_observation(
                        result
                    )
                )

                print(
                    "[NOVA SELF IMPROVEMENT RESULT]",
                    improvement
                )


            except Exception as exc:

                print(
                    "[NOVA SELF IMPROVEMENT FAILED]",
                    type(exc).__name__,
                    str(exc)
                )

            return result

        except Exception as exc:

            print(
                "[NOVA BEHAVIOR OBSERVER FAILED]",
                type(exc).__name__,
                str(exc)
            )

            return {
                "observed": False,
                "reason": "behavior_observer_failed",
                "error_type": type(exc).__name__,
            }


class ChatService:

    def _nova_use_chat_turn_messages_enabled(self):
        # NOVA_CHAT_TURN_FEATURE_FLAG_ADAPTER_20260705
        value = str(os.getenv("NOVA_USE_CHAT_TURN_MESSAGES", "")).strip().lower()

        return value in {
            "1",
            "true",
            "yes",
            "on",
            "enabled",
        }

    def _nova_select_model_messages(self, fallback_messages):
        # NOVA_CHAT_TURN_FEATURE_FLAG_ADAPTER_20260705
        if not self._nova_use_chat_turn_messages_enabled():
            return fallback_messages

        shadow_messages = getattr(self, "_last_chat_turn_messages_shadow", None)

        if not shadow_messages:
            return fallback_messages

        return shadow_messages

    def __init__(
        self,
        session_service: SessionService,
        memory_service: MemoryService,
        artifact_service: ArtifactService,
        web_service: WebService,
        recon_service: ReconService,
        memory_context_service=None,
        working_state_service=None,
        execution_state_service=None,
        runtime_uploads_normalizer_service=None,
    ):

        self.chat_execution_service = chat_execution_service

        self.orchestrator = (
            NovaOrchestrator(
                execution_state_service=execution_state_service,
                memory_service=memory_service,
            )
        )

        self.chat_response_cleanup_service = ChatResponseCleanupService()
        self.chat_response_policy_service = ChatResponsePolicyService()
        self.runtime_cognitive_firewall = RuntimeCognitiveFirewall()
        self.attachment_analysis_service = AttachmentAnalysisService()
        self.accidental_input_guard_service = AccidentalInputGuardService()
        self.response_mojibake_cleanup_service = ResponseMojibakeCleanupService()
        self.error_reporting_service = ErrorReportingService()

        # =========================
        # CORE SERVICES
        # =========================

        self.execution_handler = ExecutionHandler(self)

        if self.chat_execution_service:
            self.chat_execution_service.execution_handler = (
                self.execution_handler
            )

        self.chat_execution_service.set_session_service(
            session_service
        )

        print(
            "DEBUG CHAT SERVICE EXECUTION WIRING",
            self.chat_execution_service,
            self.chat_execution_service.session_service,
            flush=True,
        )

        self.response_handler = ChatResponseHandler(self)
        self.chat_router = ChatRouter(self)
        self.planner_service = PlannerService(self)
        self.intelligence_router = IntelligenceRouter(self)

        self.orchestrator = (
            NovaOrchestrator(
                execution_state_service=execution_state_service,
                memory_service=memory_service,
            )
        )

        self.decision_service = DecisionService(
            self
        )

        self.auto_fix_service = AutoFixService(self)

        self.session_service = session_service
        self.memory_service = memory_service
        self.runtime_uploads_normalizer_service = runtime_uploads_normalizer_service
        self.artifact_service = artifact_service
        self.web_service = web_service
        self.recon_service = recon_service
        self.memory_context_service = memory_context_service

        if working_state_service is None:
            from nova_backend.services.working_state_service import (
                WorkingStateService,
            )

            working_state_service = WorkingStateService(
                session_service
            )

        self.working_state_service = working_state_service
        self.execution_state_service = execution_state_service

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
                Path(__file__).resolve().parents[2] / "uploads",
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

        # FORCE_CHAT_SERVICE_OPENAI_KEY_LOCK
        # Load the exact Nova .env key before creating the OpenAI client.



        self.agent = AgentService()
        self.memory_ranker = MemoryRankerService()
        self.tools = ToolService(base_dir=os.getcwd())

        # =========================
        # RESPONSE / INTENT SERVICES
        # =========================

        self.rewrite_service = ResponseRewriteService()
        self.intent_service = IntentService()
        self.python_runner = PythonRunnerService()

        # =========================
        # RUNTIME COGNITION
        # =========================

        self.runtime_cognitive_injection = RuntimeCognitiveInjectionService()

        self.runtime_brain = None

        # =========================
        # EXECUTION ENGINE
        # =========================

        self.default_executor = default_executor

        self.repair_execution_service = RepairExecutionService(
            execution_handler=self.execution_handler,
        )
        self.execution_mutation_service = ExecutionMutationService(
            execution_state_service=self.execution_state_service,
        )
        self.execution_approval_service = (
            ExecutionApprovalService()
        )

        self.execution_step_service = ExecutionStepService(
            safe_str=self._safe_str,
            python_runner=self.python_runner,
            approval_service=self.execution_approval_service,

        )

        self.execution_orchestrator_service = ExecutionOrchestratorService(
            execution_state_service=self.execution_state_service,
            working_state_service=self.working_state_service,
            execution_mutation_service=self.execution_mutation_service,
            safe_str=self._safe_str,
            execution_step_service=self.execution_step_service,
        )

        self.runtime = RuntimeBootstrap.build(chat_service=self)

        self.execution_loop = ExecutionLoopService(
            execution_handler=self.execution_handler,
            runtime_service=self.runtime,
        )

        self.execution_service = ExecutionService(self)
        self.execution_bridge_service = ExecutionBridgeService(
            chat_execution_service=self.chat_execution_service,
            logger=logger,
            chat_service=self,
        )

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

    def _looks_like_live_market_request(self, user_text):
        text = str(user_text or "").lower()

        markers = [
            "bitcoin price",
            "btc price",
            "btc",
            "bitcoin",
            "ethereum price",
            "eth price",
            "stock price",
            "share price",
            "market price",
            "price right now",
            "current price",
            "live price",
        ]

        return any(
            marker in text
            for marker in markers
        )

    def handle(
        self,
        user_text: str,
        session_id: str = "",
        attachments=None,
    ):

        print(
            "DEBUG CHAT_SERVICE HANDLE SESSION=",
            repr(session_id),
            flush=True,
        )

        guard_result = self.accidental_input_guard_service.handle(
            user_text=user_text,
            session_id=session_id,
        )

        if guard_result:
            return guard_result

        target_capture_result = (
            self.execution_bridge_service
            .try_execution_target_capture(
                session_id,
                user_text,
            )
        )

        if target_capture_result is not None:
            return target_capture_result

        from nova_backend.services.chat.handle import chat_handle

        attachments = attachments or []

        if self._looks_like_live_market_request(user_text):
            print(
                "DEBUG LIVE MARKET BYPASS EXECUTION",
                user_text,
                flush=True,
            )

            brain_state = {
                "decision": {
                    "route": "web_fetch",
                    "mode": "web_fetch",
                    "intent": "live_market",
                }
            }

        else:

            current_execution = self.chat_execution_service.get_state(
                session_id
            )

            if (
                self.chat_execution_service.is_execution_trigger(user_text)
                and current_execution.get("complete") is True
            ):
                return {
                    "status": "complete",
                    "execution_state": current_execution,
                }

            execution_result = self._handle_execution_control(
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
            )

            print(
                "DEBUG EXECUTION CONTROL RESULT =",
                execution_result,
            )

            if execution_result is not None:

                if (
                    isinstance(execution_result, dict)
                    and "execution" in execution_result
                    and "execution_state" not in execution_result
                ):
                    execution_result["execution_state"] = (
                        execution_result["execution"]
                    )

                return execution_result

            session_payload = self._get_session_payload(
                session_id
            )

            brain_state = self.orchestrator.run(
                user_text=user_text,
                session_context=session_payload,
                session_id=session_id,
            )

        print(
            "DEBUG BRAIN STATE:",
            brain_state,
        )

        execution_state = (
            brain_state.get("execution")
            if isinstance(brain_state, dict)
            else {}
        )

        if execution_state:
            self._save_execution_state(
                session_id,
                execution_state,
            )

        response = chat_handle(
            self,
            user_text,
            session_id,
            attachments,
            brain_state=brain_state,
            decision=(
                brain_state.get("decision")
                if isinstance(brain_state, dict)
                else None
            ),
        )

        memory_result = self._maybe_write_memory(
            decision=(
                brain_state.get("decision")
                if isinstance(brain_state, dict)
                else {}
            ),
            user_text=user_text,
            session_id=session_id,
        )

        print(
            "DEBUG HANDLE MEMORY RESULT =",
            memory_result,
            flush=True,
        )

        response["brain_state"] = brain_state

        if memory_result:
            response.setdefault(
                "debug",
                {},
            )["memory_saved"] = True


        print(
            "DEBUG AFTER CHAT_HANDLE META =",

            response.get("assistant_message", {}).get("meta")
            if isinstance(response, dict)
            and isinstance(response.get("assistant_message"), dict)
            else None,
        )

        response["brain_state"] = brain_state

        decision = (
            brain_state.get("decision")
            if isinstance(brain_state, dict)
            else {}
        )

        if isinstance(response, dict):

            debug = response.get("debug")

            if not isinstance(debug, dict):
                debug = {}

            if isinstance(decision, dict):

                route = decision.get("route")

                if route:
                    debug["route"] = route
                    debug["route_taken"] = route

            response["debug"] = debug

        return response

    def _nova_boot_log_20260701(*args, **kwargs):
        import os as _nova_boot_log_os_20260701

        if str(
            _nova_boot_log_os_20260701.getenv(
                "NOVA_VERBOSE_BOOT_LOGS",
                "",
            )
        ).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            print(*args, **kwargs)




    def _nova_is_local_project_status_question_20260607(
        user_text
    ):
        clean = " ".join(
            str(user_text or "").lower().split()
        )

        triggers = [
            "what did we fix",
            "what we fixed",
            "what did you fix",
            "explain what we fixed",
            "summarize what we fixed",
            "what have we done",
            "what did we do",
            "what are we working on",
            "what is broken",
            "what's broken",
            "what is left",
            "what's left",
            "what should we do now",
            "what do you suggest",
            "status",
            "progress",
            "this session",
            "nova",
            "mobile",
            "composer",
            "attachment",
            "frontend",
            "backend",
        ]

        project_words = [
            "nova",
            "mobile",
            "composer",
            "bar",
            "button",
            "buttons",
            "icons",
            "attachment",
            "preview",
            "session",
            "frontend",
            "backend",
            "cache",
            "flask",
            "template",
            "css",
            "js",
            "fixed",
            "fix",
            "working",
        ]

        if clean in [
            "status",
            "progress",
            "what now",
            "next",
            "what next",
        ]:
            return True

        if (
            any(
                trigger in clean
                for trigger in triggers
            )
            and any(
                word in clean
                for word in project_words
            )
        ):
            return True

        if "explain what we fixed today" in clean:
            return True

        return False


    def _nova_local_project_status_answer_20260607(
        user_text
    ):
        return (
            "Here is what we fixed in this checkpoint:\n\n"
            "- Fixed the mobile composer buttons so the send, voice, attach, and tools buttons stopped stretching and now keep a clean square size.\n"
            "- Fixed the mojibake icon problem where symbols were appearing as corrupted text.\n"
            "- Fixed the stale frontend cache problem where the mobile page kept loading an outdated JavaScript bundle instead of the patched version.\n"
            "- Slimmed the mobile input and composer bar so the text area and main composer buttons are 40 pixels high.\n"
            "- Identified stale web and search context leaking into normal project questions.\n\n"
            "Next move: prevent stale web and search context from affecting normal Nova project and session questions."
        )

    def get_global_chat_turn_shadow_snapshot(cls):
        # NOVA_CHAT_TURN_GLOBAL_DEBUG_SNAPSHOT_20260705
        instance = cls.__new__(cls)
        instance._last_chat_turn_shadow = getattr(cls, "_nova_last_chat_turn_shadow", None)
        instance._last_chat_turn_messages_shadow = getattr(cls, "_nova_last_chat_turn_messages_shadow", [])
        return instance.get_chat_turn_shadow_snapshot()


    def get_chat_turn_shadow_snapshot(self):
        # NOVA_CHAT_TURN_DEBUG_SNAPSHOT_20260705
        turn = getattr(self, "_last_chat_turn_shadow", None)
        messages = getattr(self, "_last_chat_turn_messages_shadow", []) or []

        if turn is None:
            return {
                "ok": True,
                "has_shadow_turn": False,
                "turn": None,
                "messages": {
                    "count": 0,
                    "roles": [],
                },
            }

        attachments = []
        for item in getattr(turn, "attachments", []) or []:
            attachments.append(
                {
                    "id": getattr(item, "id", ""),
                    "filename": getattr(item, "filename", ""),
                    "mime_type": getattr(item, "mime_type", ""),
                    "kind": getattr(item, "kind", ""),
                    "has_url": bool(getattr(item, "url", "")),
                }
            )

        user_text = getattr(turn, "user_text", "") or ""

        return {
            "ok": True,
            "has_shadow_turn": True,
            "turn": {
                "request_id": getattr(turn, "request_id", ""),
                "session_id": getattr(turn, "session_id", ""),
                "intent": getattr(turn, "intent", ""),
                "model": getattr(turn, "model", ""),
                "created_at": getattr(turn, "created_at", ""),
                "user_text_preview": user_text[:160],
                "user_text_length": len(user_text),
                "attachment_count": len(attachments),
                "attachments": attachments,
                "history_count": len(getattr(turn, "history", []) or []),
                "memory_count": len(getattr(turn, "memory", []) or []),
                "attachment_context_count": len(getattr(turn, "attachment_context", []) or []),
                "tool_result_count": len(getattr(turn, "tool_results", []) or []),
                "metadata": getattr(turn, "metadata", {}) or {},
            },
            "messages": {
                "count": len(messages),
                "roles": [
                    (message.get("role") if isinstance(message, dict) else "")
                    for message in messages
                ],
                "content_lengths": [
                    len(message.get("content", "")) if isinstance(message, dict) else 0
                    for message in messages
                ],
            },
        }


    def _nova_build_chat_turn_shadow(
        self,
        payload=None,
        *,
        history=None,
        memory=None,
        attachment_context=None,
        tool_results=None,
        metadata=None,
    ):
        # NOVA_CHAT_TURN_HELPER_20260705
        if not isinstance(payload, dict):
            payload = {}

        turn = build_chat_turn_from_request(
            payload,
            history=history or [],
            memory=memory or [],
            attachment_context=attachment_context or [],
            tool_results=tool_results or [],
            model=str(
                getattr(self, "chat_model", "")
                or getattr(self, "model", "")
                or ""
            ),
            metadata=metadata or {"source": "chat_service.shadow_helper"},
        )

        messages = build_model_messages(turn)

        self._last_chat_turn_shadow = turn
        self._last_chat_turn_messages_shadow = messages

        # NOVA_CHAT_TURN_GLOBAL_SNAPSHOT_SET_20260705
        try:
            self.__class__._nova_last_chat_turn_shadow = turn
            self.__class__._nova_last_chat_turn_messages_shadow = messages
        except Exception:
            pass

        return turn, messages


    # NOVA_WEB_NEWS_BLOCKS_IMAGE_GENERATION_BRANCHES_20260609
    def _nova_is_web_news_intent_20260609(self, value) -> bool:
        probe = " ".join(str(value or "").split("\n", 1)[0].lower().split())
        terms = (
            "latest news",
            "news about",
            "today in",
            "what happened today",
            "current news",
            "breaking news",
            "recent news",
            "latest tech news",
            "latest sports",
            "weather",
            "forecast",
            "current events",
        )
        return any(term in probe for term in terms)

    ROUTE_GENERAL_CHAT = "general_chat"
    ROUTE_IMAGE_GENERATION = "image_generation"
    ROUTE_WEB_FETCH = "web_fetch"
    ROUTE_ATTACHMENT_ANALYSIS = "attachment_analysis"
    ROUTE_PLANNING = "planning"
    ROUTE_MEMORY_RECALL = "memory_recall"

    # NOVA_IMAGE_ATTACHMENT_HELPER_20260607

    def _nova_has_image_attachment_20260607(self, attachments=None) -> bool:
        attachments = attachments or []

        if not isinstance(attachments, list):
            return False

        for item in attachments:
            if not isinstance(item, dict):
                continue


            name = self.safe_str(
                item.get("filename")
                or item.get("original_filename")
                or item.get("name")
                or item.get("url")
                or item.get("file_url")
            ).lower()

            mime_type = self.safe_str(
                item.get("mime_type")
                or item.get("type")
            ).lower()

            if mime_type.startswith("image/"):
                return True

            if name.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                return True

            if "/api/uploads/" in name and any(ext in name for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
                return True

        return False


    def _process_goal_and_plan(
        self,
        user_text: str,
        session_id: str,
    ):

        existing_execution = (
            self._load_execution_state(
                session_id
            )
            or {}
        )

        print(
            "DEBUG PROCESS GOAL EXISTING EXECUTION =",
            existing_execution,
        )

        print(
            "[DEBUG LOADED EXECUTION STATUS]",
            existing_execution.get("status"),
        )

        print(
            "[DEBUG LOADED EXECUTION STEPS]",
            existing_execution.get("steps"),
        )

        if (
            isinstance(
                existing_execution,
                dict,
            )
            and existing_execution.get(
                "status"
            ) in {
                "ready",
                "running",
                "waiting",
            }
            and existing_execution.get(
                "steps"
            )
        ):
            return self.execution_handler.run_next_move(
                action="run_step",
                session_id=session_id,
                execution_state=existing_execution,
            )

        goal = self._build_goal(
            user_text,
            session_id,
        )

        plan = self._build_plan(
            goal,
        )

        execution = self._build_execution(
            user_text,
            plan,
            {
                "route": "planner",
                "intent": "planning",
            },
        )

        if execution and (
            execution.get("steps")
            or execution.get("goal")
        ):
            execution["status"] = (
                execution.get("status")
                or "ready"
            )
            execution["current_index"] = (
                execution.get("current_index")
                or 0
            )

            execution["current_step"] = (
                execution.get("current_step")
                or (
                    execution.get("steps", [{}])[0].get("title")
                    if execution.get("steps")
                    else ""
                )
            )

            self._save_execution_state(
                session_id,
                execution,
            )

        return execution or {}

    def _get_working_state(self, session_id: str) -> dict:
        return self.working_state_service.get_working_state(
            session_id
        )

    def _is_control_command_value(self, value):

        text = self.safe_str(value).strip().lower()

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

    def _build_goal(self, *args, **kwargs):
        return self.execution_service._build_goal(*args, **kwargs)

    def _build_plan(self, *args, **kwargs):
        return self.execution_service._build_plan(*args, **kwargs)

    def _build_execution(self, *args, **kwargs):
        return self.execution_service._build_execution(*args, **kwargs)

    def _execution_mark_running(self, *args, **kwargs):
        return self.execution_service._execution_mark_running(*args, **kwargs)

    def _execution_mark_completed(self, *args, **kwargs):
        return self.execution_service._execution_mark_completed(*args, **kwargs)

    def _execution_mark_failed(self, *args, **kwargs):
        return self.execution_service._execution_mark_failed(*args, **kwargs)

    def _update_working_state(
        self,
        session_id: str,
        patch: dict,
    ) -> dict:
        return self.working_state_service.update_working_state(
            session_id,
            patch,
        )


    def _build_system_prompt(
        self,
        decision=None,
        memory_items=None,
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
            "Nova identity: "
            "You are a direct thinking partner, not a generic assistant. "
            "Lead with the useful answer. "
            "Avoid empty praise, filler acknowledgements, and unnecessary reassurance. "
            "Do not assume the user's emotions or describe how they feel. "
            "Be calm, precise, and honest about uncertainty. "
            "Challenge weak assumptions respectfully when it improves the outcome. "
            "Prioritize progress, clarity, and practical next actions."
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

        if decision and isinstance(decision, dict):

            mode = (decision.get("mode") or "").strip()

            if mode:
                parts.append(f"Current operating mode: " f"{mode}.")

        intent = self.safe_str((decision or {}).get("intent")).lower()

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

        if memory_items:
            memory_lines = []

            for item in memory_items[:8]:
                if not isinstance(item, dict):
                    continue

                text = (
                    item.get("text")
                    or item.get("content")
                    or ""
                )

                if text:
                    memory_lines.append(
                        f"- {text}"
                    )

            if memory_lines:
                parts.append(
                    "Relevant saved memory:\n"
                    + "\n".join(memory_lines)
                )

        return "\n\n".join([p for p in parts if p]).strip()

    def _resume_execution_if_needed(self, session_id):
        session = self.sessions.get(session_id)

        if not session:
            return None

        state = session.get("working_state") or {}

        execution = (
            state.get("active_execution")
            or state.get("execution_state")
            or {}
        )

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
        text = self.safe_str(user_text).lower().strip()

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

        # 1. convert tabs ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ 4 spaces
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
                        "details": self.safe_str(e),
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
                "error": self.safe_str(e),
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


    def _safe_str(self, value) -> str:
        try:
            if value is None:
                return ""

            if isinstance(value, str):
                return value

            return str(value)

        except Exception:
            return ""

    def safe_str(self, value):
        return self._safe_str(value)

    def _save_mission_state(
        self,
        session_id: str,
        mission: dict,
    ) -> None:
        if not session_id or not isinstance(mission, dict):
            return

        try:
            working_state = self._get_working_state(
                session_id
            ) or {}


            self._update_working_state(
                session_id,
                {
                    "mission": (
                        mission
                        if has_real_execution
                        else {}
                    ),
                },
            )

        except Exception as e:
            logger.error(
                f"[mission] failed to save mission state: {e}"
            )

    def _resolve_mission_command(
        self,
        user_text: str,
        session_id: str = "",
    ) -> dict:
        text = self.safe_str(
            user_text
        ).lower().strip()

        if text in {
            "stop",
            "cancel",
            "abort",
            "halt",
        }:

            execution_state = (
                self._load_execution_state(
                    session_id
                )
                or {}
            )

            return {
                "ok": True,
                "is_mission": True,
                "type": "cancel",
                "mission": {},
                "next_action": "cancel",
                "continue_request": False,
                "execution": execution_state,
            }

        if text in {
            "stop",
            "cancel",
            "abort",
            "halt",
        }:
            execution_state = (
                self._load_execution_state(
                    session_id
                )
                or {}
            )

            return {
                "ok": True,
                "is_mission": True,
                "type": "cancel",
                "mission": {},
                "next_action": "cancel",
                "continue_request": False,
                "execution": execution_state,
            }

        working_state = (
            self._get_working_state(
                session_id
            )
            or {}
        )

        if not isinstance(
            working_state,
            dict,
        ):
            working_state = {}

        mission = (
            working_state.get("mission")
            if isinstance(
                working_state.get("mission"),
                dict,
            )
            else {}
        )

        execution_state = (
            self._load_execution_state(
                session_id
            )
            or (
                working_state.get("execution_state")
                if isinstance(
                    working_state.get("execution_state"),
                    dict,
                )
                else {}
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

        if current_index > len(steps):
            current_index = len(steps)

        if text in {
            "next",
            "nex",
            "k",
            "kk",
            "continue",
            "resume",
        }:
            has_saved_mission = bool(
                mission
                or execution_state.get("goal")
                or execution_state.get("steps")
                or execution_state.get("current_step")
            )

            has_real_execution = any(
                [
                    bool(execution_state.get("steps")),
                    execution_state.get("current_step"),
                    self.safe_str(
                        execution_state.get("status")
                    ).lower().strip()
                    in {
                        "running",
                        "waiting",
                        "paused",
                    },
                ]
            )

            if (
                not has_saved_mission
                and not has_real_execution
            ):
                return {
                    "ok": True,
                    "is_mission": True,
                    "type": "empty_next_guard",
                    "next_action": "none",
                    "mission": {},
                    "assistant_message": self._build_assistant_message(
                        "No active execution to continue. "
                        "Start one with: auto-plan <goal>"
                    ),
                    "execution": execution_state,
                }

            return {
                "ok": True,
                "is_mission": True,
                "type": "continue",
                "mission": mission,
                "next_action": "run_step",
                "continue_request": False,
                "execution": execution_state,
            }

        if text in {
            "run it",
            "run",
            "execute",
            "go",
        }:
            has_real_execution = any(
                [
                    bool(execution_state.get("steps")),
                    execution_state.get("current_step"),
                    execution_state.get("status")
                    in {
                        "running",
                        "waiting",
                        "paused",
                    },
                ]
            )

            if (
                text == "go"
                and not has_real_execution
            ):
                return {
                    "ok": True,
                    "is_mission": True,
                    "type": "empty_go_guard",
                    "mission": {},
                    "next_action": "none",
                    "execution": execution_state,
                    "assistant_message": self._build_assistant_message(
                        "No active mission to run. "
                        "Start one with: auto-plan <goal>"
                    ),
                }

            return {
                "ok": True,
                "is_mission": True,
                "type": "execute",
                "mission": mission,
                "next_action": "run_execution",
                "execution": execution_state,
            }

        if text in {
            "what next",
            "what now",
        }:
            return {
                "ok": True,
                "is_mission": True,
                "type": "continue",
                "mission": mission,
                "next_action": (
                    mission.get("next_action")
                    or "run_step"
                ),
                "execution": execution_state,
            }

        if text.startswith("auto-plan"):
            goal = (
                user_text[len("auto-plan"):].strip()
            )

            return {
                "ok": True,
                "is_mission": True,
                "type": "start",
                "mission": {},
                "next_action": "start_execution",
                "continue_request": False,
                "goal": goal,
                "execution": execution_state,
            }

        if text.startswith("auto-plan"):
            goal = (
                user_text[len("auto-plan"):].strip()
            )

            return {
                "ok": True,
                "is_mission": True,
                "type": "start",
                "mission": {},
                "next_action": "start_execution",
                "continue_request": False,
                "goal": goal,
                "execution": execution_state,
            }

        return {
            "ok": True,
            "is_mission": False,
            "type": "",
            "mission": mission,
            "next_action": "",
            "execution": {},
        }

    def _handle_mission_command_result(
        self,
        mission_command=None,
        session_id: str = "",
    ):
        if not isinstance(mission_command, dict):
            return None

        mission_type = self.safe_str(
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
                "execution": (
                    mission_command.get("execution")
                    or {}
                ),
                "session": self._get_session_payload(
                    session_id
                ),
                "debug": {
                    "route_taken": "empty_next_guard",
                },
            }

        if mission_command.get("is_mission") is not True:
            return None

        next_action = self.safe_str(
            mission_command.get("next_action")
        ).lower().strip()

        execution_state = (
            mission_command.get("execution")
            or {}
        )

        if execution_state:
            execution_state["session_id"] = session_id

            self._save_execution_state(
                session_id,
                execution_state,
            )

        if mission_type == "cancel":
            return self.execution_orchestrator_service.process_execution(
                session_id=session_id,
                state=execution_state,
                command="cancel",
            )

        if mission_type == "inspect":
            mission = (
                mission_command.get("mission")
                or {}
            )

            return {
                "ok": True,
                "assistant_message": self._build_assistant_message(
                    mission.get("recommended_next_move")
                    or "Inspect current mission state."
                ),
                "execution": execution_state,
                "session": self._get_session_payload(
                    session_id
                ),
                "debug": {
                    "route_taken": "mission_inspect",
                },
            }

        if mission_type == "start":
            goal = self.safe_str(
                mission_command.get("goal")
            ).strip()

            if not goal:
                goal = "Untitled mission"

            return self.execution_bridge_service.try_execution_autoplan_start(
                session_id=session_id,
                user_text=(
                    "auto-plan "
                    + self.safe_str(
                        mission_command.get("goal")
                    )
                ),
            )

        selected_execution_state = dict(
            execution_state or {}
        )

        continue_requested = bool(
            mission_command.get("continue_request")
        )

        if mission_type in {
            "continue",
            "execute",
        }:
            persisted_execution_state = (
                self._load_execution_state(
                    session_id
                )
                or {}
            )

            if execution_state.get("steps"):
                selected_execution_state = execution_state

            elif (
                persisted_execution_state.get("steps")
                and str(
                    persisted_execution_state.get("status")
                    or ""
                ).lower()
                not in {
                    "complete",
                    "completed",
                    "done",
                }
            ):
                selected_execution_state = (
                    persisted_execution_state
                )

        if continue_requested:
            selected_execution_state[
                "continue_request"
            ] = True

            selected_execution_state[
                "command"
            ] = "continue"

        elif mission_command.get("next_action"):
            selected_execution_state[
                "command"
            ] = mission_command.get(
                "next_action"
            )

        else:
            selected_execution_state[
                "command"
            ] = next_action or "run_step"

        print(
            "K DISPATCH CHECK =",
            {
                "continue_request": selected_execution_state.get(
                    "continue_request"
                ),
                "command": selected_execution_state.get(
                    "command"
                ),
                "next_action": next_action,
                "status": selected_execution_state.get(
                    "status"
                ),
            },
        )

        if (
            selected_execution_state.get("status") == "complete"
            or selected_execution_state.get("complete") is True
        ):
            exec_debug(
                "EXECUTION DISPATCH SKIPPED: already complete",
                selected_execution_state,
            )
            return {
                "status": "complete",
                "execution_state": selected_execution_state,
            }


        exec_debug(
            "DISPATCH EXECUTION STATE DEBUG",
            {
                "goal": selected_execution_state.get(
                    "goal"
                ),
                "status": selected_execution_state.get(
                    "status"
                ),
                "steps": len(
                    selected_execution_state.get(
                        "steps",
                        []
                    )
                    or []
                ),
                "command": next_action,
            },
        )

        print(
            "EXECUTION STATE BEFORE ORCHESTRATOR =",
            selected_execution_state,
        )

        if (
            isinstance(selected_execution_state, dict)
            and not selected_execution_state.get("steps")
        ):
            output_state = (
                selected_execution_state.get("output")
                or {}
            )

            if (
                isinstance(output_state, dict)
                and output_state.get("steps")
            ):
                selected_execution_state = output_state

            elif (
                selected_execution_state.get(
                    "plan",
                    {},
                ).get("steps")
            ):
                selected_execution_state = {
                    **selected_execution_state,
                    "steps": selected_execution_state[
                        "plan"
                    ]["steps"],
                }

        if selected_execution_state.get(
            "continue_request"
        ):
            selected_execution_state[
                "command"
            ] = "run_step"

            selected_execution_state[
                "waiting"
            ] = False

            selected_execution_state[
                "status"
            ] = "ready"

            self._save_execution_state(
                session_id,
                selected_execution_state,
            )

            return self.execution_orchestrator_service.process_execution(
                session_id=session_id,
                state=selected_execution_state,
                command="run_step",
            )

        print(
            "FINAL ORCHESTRATOR DISPATCH =",
            {
                "goal": selected_execution_state.get("goal"),
                "steps": len(
                    selected_execution_state.get("steps", [])
                ),
                "current_index": selected_execution_state.get(
                    "current_index"
                ),
                "command": next_action or "run_step",
                "status": selected_execution_state.get("status"),
            },
            flush=True,
        )

        return self.execution_orchestrator_service.process_execution(
            session_id=session_id,
            state=selected_execution_state,
            command=(
                next_action
                or "run_step"
            ),
        )

        return self.execution_orchestrator_service.process_execution(
            session_id=session_id,
            state=selected_execution_state,
            command=(
                next_action
                or "run_step"
            ),
        )


    def _load_execution_state(
        self,
        session_id="",
    ):

        try:
            if self.chat_execution_service:
                execution_state = (
                    self.chat_execution_service.get_state(
                        session_id
                    )
                )

                if (
                    isinstance(execution_state, dict)
                    and execution_state.get("steps")
                ):
                    return execution_state

        except Exception as exc:
            print(
                "[EXECUTION SERVICE LOAD FAILED]",
                exc,
            )

        session_payload = self._get_session_payload(
            session_id
        )

        if isinstance(session_payload, dict):
            direct_state = session_payload.get(
                "execution_state"
            )

            if (
                isinstance(direct_state, dict)
                and direct_state.get("steps")
            ):
                return direct_state

        meta_state = self._get_session_meta(
            session_id,
            "execution_state",
            {},
        )

        if (
            isinstance(meta_state, dict)
            and meta_state.get("steps")
        ):
            return meta_state

        return {}

    def _save_execution_state(
        self,
        session_id="",
        execution_state=None,
    ):
        if not isinstance(
            execution_state,
            dict,
        ):
            return

        if self.execution_state_service:
            self.execution_state_service.save_execution_state(
                session_id,
                execution_state,
            )

        # Persist into session payload/meta
        try:
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

        except Exception as e:
            exec_debug(
                "SESSION EXECUTION META SAVE FAILED:",
                e,
            )

        if (
            hasattr(self, "chat_execution_service")
            and self.chat_execution_service
        ):
            try:
                existing_state = (
                    self.chat_execution_service.get_state(
                        session_id
                    )
                    or {}
                )

                if (
                    existing_state.get("steps")
                    or existing_state.get("current_step")
                    or existing_state.get("goal")
                    or existing_state.get("status")
                    not in {
                        None,
                        "idle",
                    }
                ):
                    exec_debug(
                        "CHAT EXECUTION SYNC SKIPPED: existing execution",
                        existing_state,
                    )
                else:
                    self.chat_execution_service.start(
                        session_id=session_id,
                        goal=(
                            execution_state.get("goal")
                            or "Untitled mission"
                        ),
                        steps=(
                            execution_state.get("steps")
                            or []
                        ),
                        context={
                            "task_type": (
                                execution_state.get("task_type")
                                or "general"
                            ),
                        },
                    )

            except Exception as e:
                exec_debug(
                    "CHAT EXECUTION STATE SYNC FAILED:",
                    e,
                )

    def _get_session_meta(self, session_id: str, key: str = "", default=None):
        session_id = self.safe_str(session_id).strip()
        key = self.safe_str(key).strip()

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
        session_id = self.safe_str(session_id).strip()
        key = self.safe_str(key).strip()

        if not session_id or not key:
            return False

        try:
            return self.session_service.set_session_meta(
                session_id,
                key,
                value,
            )

        except Exception as e:
            exec_debug(
                "SET SESSION META FAILED:",
                e,
            )
            return False


    def _should_auto_title_session(self, title):
        title = self.safe_str(title).strip().lower()

        return title in (
            "",
            "new chat",
            "untitled session",
        )


    def _build_session_title_from_message(self, user_msg):
        text = ""

        if isinstance(user_msg, dict):
            text = self.safe_str(
                user_msg.get("text")
                or user_msg.get("content")
                or ""
            ).strip()

        if not text:
            return ""

        words = text.split()

        title = " ".join(words[:8])

        return title[:60]

    def _maybe_write_memory(
        self,
        decision=None,
        user_text: str = "",
        session_id: str = "",
    ) -> bool:

        print(
            "MEMORY FUNCTION HIT",
            repr(user_text),
        )

        print(
            "DEBUG MEMORY ENTERED =",
            "NOVA_MEMORY_TEST_009_REACHED",
            repr(session_id),
        )

        decision = decision if isinstance(decision, dict) else {}

        user_text_lc = self.safe_str(user_text).lower().strip()

        memory_preference_request = any(
            marker in user_text_lc
            for marker in [
                "i prefer",
                "i always want",
                "i like",
                "i love",
                "my favorite",
                "my favourite",
                "remember my",
                "remember that",
                "remember this",
                "my preference",
                "from now on",
            ]
        )

        if memory_preference_request:
            decision["save_memory"] = True
            decision["intent"] = "memory"
            decision["route"] = "memory"

        if (
            decision.get("route")
            == "project_brain_general_intelligence"
            or decision.get("mode")
            == "project_brain_general_intelligence"
            or decision.get("intent")
            == "mission_control"
        ):
            return None

        text = self.safe_str(user_text).strip()

        if not text:
            return False

        memory_kind = "user_fact"

        # DO NOT SAVE MEMORY QUESTIONS
        question_memory_block = (
            "what is my name",
            "what's my name",
            "who am i",
            "what do you know about me",
            "what do you remember about me",
            "tell me my name",
        )

        text_lower = text.lower()

        if any(
            marker in text_lower
            for marker in question_memory_block
        ):
            print(
                "MEMORY BLOCKED QUESTION =",
                text,
                flush=True,
            )
            return False

        if any(
            marker in text.lower()
            for marker in (
                "i prefer",
                "i always want",
                "i like",
                "remember my",
                "going forward",
                "from now on",
            )
        ):
            memory_kind = "preference"

        if any(
            marker in text.lower()
            for marker in (
                "my name is",
                "call me",
                "my name's",
            )
        ):
            memory_kind = "user_fact"

        if "remember that" in text.lower():
            memory_kind = "project"

        if any(
            marker in text.lower()
            for marker in (
                "favorite color",
                "favourite color",
                "favorite movie",
                "favourite movie",
                "favorite drink",
                "favourite drink",
                "favorite animal",
                "favourite animal",
                "call me",
                "my name is",
            )
        ):
            memory_kind = "user_fact"

        if any(
            marker in text.lower()
            for marker in (
                "favorite color",
                "favourite color",
                "favorite movie",
                "favourite movie",
                "favorite drink",
                "favourite drink",
                "favorite animal",
                "favourite animal",
                "call me",
                "my name is",
            )
        ):
            memory_kind = "user_fact"

        if any(
            marker in text.lower()
            for marker in (
                "i prefer",
                "i always",
                "i like",
                "remember that",
                "going forward",
                "from now on",
            )
        ):
            memory_kind = "preference"

        print(
            "MEMORY CLASSIFY:",
            text,
            memory_kind,
        )

        print(
            "MEMORY FILTER CHECK =",
            repr(text),
            "kind=",
            memory_kind,
        )

        print(
            "DEBUG MEMORY BEFORE FILTER =",
            {
                "text": text,
                "kind": memory_kind,
                "decision": decision,
            },
        )

        if not self._should_save_memory_text(
            text,
            kind=memory_kind,
        ):
            exec_debug("MEMORY REJECTED TEXT =", text)
            return False

        payload = {
            "text": text,
            "kind": memory_kind,
            "session_id": session_id,
            "source": "chat_service_memory_save",
        }

        print(
            "DEBUG MEMORY PAYLOAD =",
            payload,
        )

        for method_name in (
            "add_memory",
        ):

            method = getattr(
                self.memory,
                method_name,
                None,
            )

            if callable(method):

                print(
                    "DEBUG MEMORY CALLING =",
                    method_name,
                )

                result = method(payload)

                print(
                    "DEBUG MEMORY METHOD RETURNED =",
                    method_name,
                    repr(result),
                )

                print(
                    "DEBUG MEMORY RESULT =",
                    result,
                )

                return True

        exec_debug(
            "MEMORY WRITE FAILED: no supported memory write method"
        )

        return False

    def _is_memory_recall_question(self, text: str) -> bool:
        text = str(text or "").strip().lower()

        recall_patterns = (
            "what do i like",
            "what is my name",
            "what do you remember",
            "do you remember",
            "what color do i like",
            "what are my preferences",
        )

        return any(
            pattern in text
            for pattern in recall_patterns
        )

    def _get_memory_list(self):
        if self.memory_service:
            try:
                if hasattr(self.memory_service, "all"):
                    result = self.memory_service.all()

                elif hasattr(self.memory_service, "list_memories"):
                    result = self.memory_service.list_memories()

                elif hasattr(self.memory_service, "build_list_payload"):
                    result = self.memory_service.build_list_payload()

                else:
                    result = []

                print(
                    "[MEMORY SERVICE RESULT]",
                    type(result),
                    result,
                )

                if isinstance(result, list):
                    return result

            except Exception as e:
                print(
                    "[MEMORY SERVICE ERROR]",
                    e,
                )

        print("[MEMORY SERVICE EMPTY]")
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

    def _ensure_session_id(self, session_id):
        sid = str(session_id or "").strip()

        # A non-empty caller-provided session ID is authoritative.
        # SessionBootstrapService already ensures requested chat sessions
        # exist before ChatService handles the request.
        if sid:
            return sid

        try:
            created = self.session_service.create_session()

            if isinstance(created, dict):
                return str(
                    created.get("id")
                    or created.get("session_id")
                    or ""
                ).strip()

        except Exception:
            pass

        return ""

    def _get_session_payload(self, session_id: str = "") -> dict:
        sid = self._ensure_session_id(session_id)

        payload = {}

        if hasattr(self.sessions, "get_session"):
            found = self.sessions.get_session(sid)

            print(
                "[NOVA CONTINUITY DEBUG]",
                "sid=",
                sid,
                "found_type=",
                type(found),
                "messages=",
                len(found.get("messages", []))
                if isinstance(found, dict)
                else "NO_DICT",
            )

            if isinstance(found, dict):
                payload = found

        if not payload and hasattr(self.sessions, "get"):
            found = self.sessions.get(sid)
            if isinstance(found, dict):
                payload = found

        if not payload:
            auth_user_id = ""

            try:
                from flask import g

                user = getattr(g, "nova_auth_user", None) or {}

                auth_user_id = str(
                    user.get("id") or ""
                ).strip()

            except Exception:
                auth_user_id = ""

            if not auth_user_id:
                try:
                    from flask import session as flask_session

                    auth_user_id = str(
                        flask_session.get("nova_user_id") or ""
                    ).strip()

                except Exception:
                    auth_user_id = ""

            payload = {
                "id": sid,
                "messages": [],
                "meta": {},
                "user_id": auth_user_id,
            }

        meta = payload.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            payload["meta"] = meta

        live_execution = (
            payload.get("active_execution")
            or payload.get("execution_state")
            or {}
        )

        if isinstance(live_execution, dict):

            status = self.safe_str(
                live_execution.get("status")
            ).strip().lower()

            if (
                status in {
                    "complete",
                    "completed",
                    "done",
                }
                or live_execution.get("complete") is True
            ):
                live_execution = {}

        # HARD BLOCK RESURRECTION FROM PAYLOAD

        payload["active_execution"] = live_execution
        payload["execution_state"] = live_execution


        goal_text = self.safe_str(live_execution.get("goal")).lower().strip()

        invalid_goal = "respond normally" in goal_text or (
            isinstance(live_execution.get("goal"), dict)
            and self.safe_str(live_execution["goal"].get("goal")).lower().strip()
            == "respond normally"
        )

        invalid_general_execution = (
            invalid_goal
            or self.safe_str(live_execution.get("original_user_text")).lower().strip()
            == "run_step"
        )

        if invalid_general_execution:

            print("SANITIZER CLEARED INVALID EXECUTION")

            live_execution = {}

            meta["active_execution"] = {}
            meta["execution_state"] = {}

        execution_status = self.safe_str(live_execution.get("status")).lower()

        execution_complete = (
            execution_status
            in {
                "complete",
                "completed",
                "done",
                "cancelled",
                "canceled",
            }
            or live_execution.get("complete") is True
        )

        if execution_complete:
            live_execution["archived"] = True

        payload["active_execution"] = live_execution
        payload["execution_state"] = live_execution

        return payload

    def _create_session(self, session_id: str = "") -> str:
        sid = self.safe_str(session_id).strip()

        auth_user_id = ""

        try:
            from flask import g

            user = getattr(g, "nova_auth_user", None) or {}

            auth_user_id = str(
                user.get("id") or ""
            ).strip()

        except Exception:
            auth_user_id = ""

        if not auth_user_id:
            try:
                from flask import session as flask_session

                auth_user_id = str(
                    flask_session.get("nova_user_id") or ""
                ).strip()

            except Exception:
                auth_user_id = ""

        if (
            sid
            and " " not in sid
            and len(sid) >= 8
        ):
            existing = self.sessions.get_session(
                sid,
                user_id=auth_user_id,
            )

            if existing:
                return sid

        created = None

        if hasattr(self.sessions, "create_session"):
            created = self.sessions.create_session(
                user_id=auth_user_id,
            )

        elif hasattr(self.sessions, "new_session"):
            created = self.sessions.new_session(
                user_id=auth_user_id,
            )

        if isinstance(created, dict):
            created_id = self.safe_str(
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




    def _record_execution_reward(
        self, session_id: str, command: str, status: str, error_text: str = ""
    ):
        session_id = self.safe_str(session_id).strip()
        command = self.safe_str(command).strip().lower()
        status = self.safe_str(status).strip().lower()
        error_text = self.safe_str(error_text).strip()

        reward = 0

        if status in {"success", "complete", "completed", "passed"}:
            reward += 10

        elif status in {"failed", "error"}:
            reward -= 5

        elif status in {"cancelled", "canceled"}:
            reward -= 1

        working_state = self._get_working_state(session_id) or {}

        current_score = int(working_state.get("execution_reward_score") or 0)

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
                "is_continuation": user_text.lower()
                in {
                    "next",
                    "continue",
                    "keep going",
                    "run next",
                    "what next",
                    "what now",
                },
                "is_failure_state": (execution_state or {}).get("status") == "failed",
            },
            "tool_state": {
                "strategy": "default",
                "available_tools": [
                    "run_step",
                    "run_all",
                    "retry_failed",
                    "apply_auto_fix",
                ],
            },
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
            "lesson_weight": 0,
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
            plan.insert(
                current_index + 1, {"step": "auto-retry failed step with correction"}
            )

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



    def _source_quality_score(
        self,
        url: str = "",
        text: str = "",
    ) -> int:
        try:
            url = self.safe_str(url).lower()
            text = self.safe_str(text).lower()

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

            # NOVA_NEWS_JUNK_RESULT_FILTER_20260622
            # These are recurring false positives for generic top-news searches.
            # They are not useful broad news cards.
            _nova_news_junk_probe = " ".join([
                str(title or ""),
                str(snippet or ""),
                str(url or ""),
            ]).lower()

            _nova_news_junk_terms = (
                "school assembly news headlines",
                "assembly news headlines today",
                "curated for you",
                "you're my favorite song",
                "youÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢re my favorite song",
                "introduces today's new top stars",
                "introduces todayÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢s new top stars",
                "gma network",
                "kanak news odisha",
                "odia news",
                "kanak shorts",
                "top 50 english-language news sites",
                "traffic drops in may",
                "indian brands hit hardest by traffic drops",
                "press gazette",
            )

            if any(term in _nova_news_junk_probe for term in _nova_news_junk_terms):
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

            cleaned.append(
                {
                    "title": title,
                    "snippet": snippet,
                    "content": snippet,
                    "url": url,
                }
            )

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
        query = self.safe_str(query).strip()
        if not query:
            return {"results": []}

        import requests
        import re
        from urllib.parse import quote_plus
        from xml.etree import ElementTree as ET

        headers = {"User-Agent": "Mozilla/5.0"}

        all_results = []

        # NOVA_GENERIC_NEWS_QUERY_FIX_20260622
        # Generic "latest news" must not use a vague open-ended news search.
        # It must use broad trusted news sources only.
        clean_news_query = " ".join(str(query or "").lower().strip().split())
        generic_news_queries = {
            "latest news",
            "tell me the latest news",
            "what is the latest news",
            "whats the latest news",
            "what's the latest news",
            "top news",
            "top headlines",
            "breaking news",
            "current news",
            "world news",
            "top world news",
            "latest world news",
            "what happened today",
            "current events",
        }

        is_generic_news_query = (
            clean_news_query in generic_news_queries
            or (
                clean_news_query.startswith(("tell me ", "show me ", "give me "))
                and any(
                    phrase in clean_news_query
                    for phrase in (
                        "latest news",
                        "top news",
                        "top headlines",
                        "breaking news",
                        "world news",
                        "current events",
                    )
                )
            )
        )

        if is_generic_news_query:
            trusted_source_queries = [
                "top world news today site:bbc.com/news",
                "top world news today site:reuters.com/world",
                "top world news today site:apnews.com",
                "top world news today site:cbc.ca/news/world",
                "top world news today site:aljazeera.com/news",
                "top world news today site:theguardian.com/world",
            ]

            trusted_domains = (
                "bbc.com",
                "reuters.com",
                "apnews.com",
                "cbc.ca",
                "aljazeera.com",
                "theguardian.com",
            )

            trusted_results = []
            trusted_seen = set()

            try:
                from urllib.parse import urlparse

                for trusted_query in trusted_source_queries:
                    try:
                        trusted_url = "https://duckduckgo.com/html/?q=" + quote_plus(trusted_query)
                        trusted_response = requests.get(trusted_url, headers=headers, timeout=10)
                        trusted_html = trusted_response.text or ""

                        for match in re.finditer(
                            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                            trusted_html,
                            re.S,
                        ):
                            link = match.group(1).replace("&amp;", "&")
                            title = re.sub(r"<.*?>", "", match.group(2)).strip()
                            title = re.sub(r"\s+", " ", title).strip()

                            snippet_match = re.search(
                                r'class="result__snippet"[^>]*>(.*?)</',
                                trusted_html[match.end() : match.end() + 500],
                                re.S,
                            )

                            snippet = ""
                            if snippet_match:
                                snippet = re.sub(r"<.*?>", "", snippet_match.group(1)).strip()
                                snippet = re.sub(r"\s+", " ", snippet).strip()

                            if "duckduckgo.com" in link:
                                try:
                                    from urllib.parse import parse_qs, unquote

                                    parsed = urlparse(link)
                                    qs = parse_qs(parsed.query)
                                    if "uddg" in qs:
                                        link = unquote(qs["uddg"][0])
                                except Exception:
                                    continue

                            try:
                                domain = urlparse(link).netloc.lower().replace("www.", "")
                            except Exception:
                                domain = ""

                            if not any(domain.endswith(item) or item in domain for item in trusted_domains):
                                continue

                            key = (title.lower(), domain)
                            if not title or key in trusted_seen:
                                continue

                            trusted_seen.add(key)

                            trusted_results.append({
                                "title": title,
                                "snippet": snippet,
                                "content": snippet,
                                "url": link,
                            })

                            if len(trusted_results) >= 6:
                                break

                        if len(trusted_results) >= 6:
                            break

                    except Exception:
                        continue

            except Exception:
                trusted_results = []

            cleaned_trusted_results = self._clean_web_results(trusted_results)

            if cleaned_trusted_results:
                return {
                    "results": cleaned_trusted_results,
                    "sources": cleaned_trusted_results,
                    "source_urls": [
                        item.get("url")
                        for item in cleaned_trusted_results
                        if isinstance(item, dict) and item.get("url")
                    ],
                }

            # Last fallback: do not allow vague "latest news" to hit dirty Google News.
            query = "top world news today BBC Reuters AP CBC Al Jazeera Guardian"

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
                re.S,
            ):
                link = match.group(1).replace("&amp;", "&")
                title = re.sub(r"<.*?>", "", match.group(2)).strip()

                snippet_match = re.search(
                    r'class="result__snippet"[^>]*>(.*?)</',
                    html[match.end() : match.end() + 500],
                    re.S,
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

                results.append(
                    {
                        "title": title,
                        "snippet": snippet,
                        "content": snippet,
                        "url": link,
                    }
                )

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
                r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S
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

                results.append(
                    {
                        "title": title,
                        "snippet": "",
                        "content": "",
                        "url": link,
                    }
                )

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

                results.append(
                    {
                        "title": title,
                        "snippet": description,
                        "content": description,
                        "url": link,
                    }
                )

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





    def _debug(self, *args):
        exec_debug(*args)


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

            result = self.handle(user_text=t, session_id=session_id)

            results.append(
                {
                    "input": t,
                    "output": result.get("debug", {}),
                    "status": result.get("execution", {}).get("status"),
                }
            )

            exec_debug("TEST RUN:", t, "?", result.get("execution", {}).get("status"))

        return {"ok": True, "results": results}


    def _build_user_message(self, text: str, attachments=None, meta=None) -> dict:
        attachments = attachments or []
        meta = meta or {}
        return {
            "role": "user",
            "text": self.safe_str(text),
            "attachments": attachments,
            "meta": meta,
        }

    def _normalize_assistant_message(self, message):
        if message is None:
            return self._build_assistant_message(
                text="I'm here. Send the next instruction."
            )

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
                execution_result={},
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

        safe_text = self.safe_str(text).strip()

        if not safe_text:
            safe_text = "I'm here. Send the next instruction."

        return {
            "role": "assistant",
            "text": safe_text,
            "attachments": attachments,
            "meta": meta,
            "memory_used": memory_used or [],
        }



    def _safe_return(
        self, assistant_msg=None, fallback_text="Execution complete.", **meta
    ):
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


    def _execute_auto_fix_file(
        self,
        user_text: str,
        session_id: str,
        attachments=None,
    ) -> dict:
        return self.auto_fix_service.execute_file_fix(
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
        )


    def _build_diff_preview(self, old: str, new: str, file_path: str) -> str:
        try:
            old_lines = (old or "").splitlines(keepends=True)
            new_lines = (new or "").splitlines(keepends=True)

            diff = difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"{file_path} (current)",
                tofile=f"{file_path} (proposed)",
                lineterm="",
            )

            preview = "".join(diff)
            if not preview.strip():
                return "No changes detected."

            # limit size
            return preview[:4000]
        except Exception as e:
            return f"Diff preview failed: {self.safe_str(e)}"

    def _apply_pending_fix(self, session_id: str) -> dict:
        state = self._get_working_state(
            session_id
        ) or {}

        pending_file_path = self.safe_str(
            state.get("pending_fix_file_path")
        )

        pending_fix_code = self.safe_str(
            state.get("pending_fix_code")
        )

        print(
            "DEBUG PENDING FIX STATE =",
            {
                "pending_file_path": pending_file_path,
                "pending_fix_code": pending_fix_code[:500],
                "state_keys": list(state.keys()),
            },
            flush=True,
        )

        user_msg = self._build_user_message("apply fix")

        decision = {
            "route": "apply_pending_fix",
            "intent": "execution",
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
            func_name = (
                self._get_session_meta(session_id, "pending_fix_func_name") or ""
            )

            if mode == "function" and not func_name:
                return {
                    "ok": False,
                    "error": "Function-only mode: no function name provided",
                }

            if func_name:
                pattern = rf"(def\s+{re.escape(func_name)}\s*\(.*?\):\n(?:\s+.*\n)*)"

                match = re.search(
                    pattern,
                    current_content,
                    flags=re.DOTALL,
                )

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

                pending_fix_code = updated

            pending_fix_code = self._normalize_python_indentation(
                pending_fix_code
            )

            result = self._safe_write_file(
                pending_file_path,
                pending_fix_code,
            )

            if not result.get("ok"):
                return {
                    "ok": False,
                    "error": "Auto-fix failed",
                    "details": result,
                }

            self._update_working_state(
                session_id,
                {
                    "pending_fix_file_path": "",
                    "pending_fix_code": "",
                },
            )

            self._set_session_meta(
                session_id,
                "pending_fix_mode",
                "",
            )


            self._set_session_meta(
                session_id,
                "pending_fix_func_name",
                "",
            )

            assistant_msg = self._build_assistant_message(
                text=(
                    f"Auto-fix applied.\n\n"
                    f"File:\n{pending_file_path}\n\n"
                    f"Backup:\n{backup_path}"
                )
            )

            # AUTO SELF-HEAL CONTINUE
            working_state = self._get_working_state(session_id) or {}
            pending_action = self.safe_str(
                working_state.get("pending_execution_action")
            )

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
                text=f"Could not apply pending fix: {type(e).__name__}: {self.safe_str(e)}"
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
            style_rules.extend(
                [
                    "Give the likely cause first.",
                    "Give the exact next fix or command.",
                    "Do not ask for pasted files unless there is no actionable next step.",
                    "Prefer file path, anchor, and replacement instructions.",
                ]
            )

        elif intent == "coding":
            style_rules.extend(
                [
                    "Prefer full-file or exact replacement code.",
                    "Include the file path when known.",
                    "Avoid partial vague snippets.",
                ]
            )

        elif intent == "explanation":
            style_rules.extend(
                [
                    "Explain clearly.",
                    "Use concrete terms.",
                    "Keep the answer structured but not bloated.",
                ]
            )

        else:
            style_rules.extend(
                [
                    "Be concise.",
                    "Answer directly.",
                    "Avoid generic chatbot filler.",
                ]
            )

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
            "whatÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢s the symptom",
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

    def _finalize_response(
        self,
        *args,
        **kwargs,
    ):
        return self.response_handler._finalize_response(
            *args,
            **kwargs,
        )

    def _decide_route(
        self,
        user_text,
        session_id="",
        attachments=None,
    ):
        return self.decision_service._decide_route(
            user_text,
            attachments,
            session_id,
        )

    def _build_response_policy(
        self,
        user_text: str = "",
        decision=None,
    ) -> dict:
        return self.chat_response_policy_service.build_response_policy(
            user_text=user_text,
            decision=decision,
        )

    def _apply_response_intelligence(
        self,
        user_text: str = "",
        assistant_text: str = "",
        decision=None,
        session_id: str = "",
        attachments=None,
    ) -> dict:
        decision = decision if isinstance(decision, dict) else {}

        if (
            decision.get("route")
            == "project_brain_general_intelligence"
            or decision.get("mode")
            == "project_brain_general_intelligence"
            or decision.get("intent")
            == "mission_control"
        ):
            return None

        attachments = attachments or []
        assistant_text = self.safe_str(assistant_text).strip()

        user_text_lc = self.safe_str(user_text).lower().strip()

        explanation_request = any(
            x in user_text_lc
            for x in [
                "what is",
                "what does",
                "explain",
                "meaning of",
                "how does",
            ]
        )

        code_explanation_request = (
            "what is" in user_text_lc
            or "what does" in user_text_lc
            or "explain" in user_text_lc
            or "meaning of" in user_text_lc
        )

        quoted_code_request = (
            '"' in user_text
            or "'" in user_text
            or "`" in user_text
            or "print(" in user_text_lc
            or "def " in user_text_lc
            or "class " in user_text_lc
        )

        if any(
            marker in user_text_lc
            for marker in [
                "what does this failure mean",
                "failure report",
                "failed smoke",
                "smoke failed",
                "assertionerror",
                "missing expected signals",
                "nova answer quality smoke",
                "project brain failure interpreter",
            ]
        ):
            return None

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

        has_error = any(
            x in user_text_lc
            for x in [
                "error:",
                "traceback",
                "syntaxerror",
                "indentationerror",
                "attributeerror",
                "typeerror",
                "nameerror",
                "500",
                "failed",
            ]
        )

        debugging_request = any(
            x in user_text_lc
            for x in [
                "fix",
                "bug",
                "error",
                "traceback",
                "exception",
                "failed",
                "debug this",
                "debug the",
                "debug issue",
                "debug error",
                "test fail",
            ]
        ) and not explanation_request

        if (
            code_explanation_request
            or quoted_code_request
        ):
            has_file_path = False
            debugging_request = False

        if not debugging_request:
            has_file_path = False

        if not debugging_request:
            return None

        explanation_request = any(
            x in user_text_lc
            for x in [
                "what is",
                "what does",
                "explain",
                "meaning of",
                "how does",
            ]
        )

        code_explanation_request = (
            "what is" in user_text_lc
            or "what does" in user_text_lc
            or "explain" in user_text_lc
            or "meaning of" in user_text_lc
        )

        quoted_code_request = (
            '"' in user_text
            or "'" in user_text
            or "`" in user_text
            or "print(" in user_text_lc
            or "def " in user_text_lc
            or "class " in user_text_lc
        )

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
                    "debug this",
                    "debug the",
                    "debug issue",
                    "debug error",
                    "test fail",
                ]
            ) and not explanation_request

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
            return {"assistant_text": assistant_text}
        # =============================
        # LOCK AUTO-FIX RESPONSE (DO NOT MODIFY)
        # =============================
        if assistant_text.startswith("Auto-fix applied."):
            return {"assistant_text": assistant_text}
        user_text_clean = self.safe_str(user_text).strip()
        user_text_lc = user_text_clean.lower()

        try:
            memory_text = str(
                self.memory_context_service.format_memory_context(
                    getattr(self, "_last_used_memory_items", [])
                )
            ).lower()
        except Exception:
            memory_text = ""

        smff_active = any(
            x in memory_text
            for x in [
                "smff",
                "full-file",
                "full file",
                "full code",
                "powershell",
                "direct",
                "no fluff",
            ]
        )

        code_intent = any(
            x in user_text_lc
            for x in [
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
            ]
        )

        if smff_active and code_intent:
            assistant_text = (
                assistant_text.strip() + "\n\n"
                "SMFF mode:\n"
                "- Send full file path.\n"
                "- Send the full broken function or file.\n"
                "- IÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ll return the full replacement, cleanly indented."
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

        is_short_stuck_prompt = user_text_lc in stuck_exact or (
            word_count <= 6 and any(signal in user_text_lc for signal in stuck_exact)
        )

        if is_short_stuck_prompt:
            return {
                "assistant_text": (
                    "Send the full function and file path.\n"
                    "IÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ll return the full replacement block, cleanly indented."
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
                    "IÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ll help patch it."
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
                    "IÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ll break it down clearly."
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
            assistant_text = "I couldnÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢t generate a useful answer from that. Send the exact thing you want handled."

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

        intelligence["strategy"] = (
            strategy.get("strategy") or intelligence.get("strategy") or "normal_answer"
        )
        intelligence["next_move"] = strategy.get("next_move") or intelligence.get(
            "next_move"
        )
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

        self_check = (
            self_check
            if isinstance(self_check, dict)
            else {
                "should_revise": False,
                "issues": [],
            }
        )

        response_policy = self._build_response_policy(
            user_text=user_text,
            decision=decision,
        )

        try:
            assistant_text = self.response_handler._clean_final_response_text(
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

                    decision["mission"] = (
                        decision.get("mission")
                        or {}
                    )

                    decision["mission"]["execution"] = execution

                    self._set_session_meta(
                        session_id,
                        "execution_state",
                        execution,
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
                        exec_debug(
                            "EXECUTION_SAVE_ERROR:",
                            e,
                        )

        except Exception as e:
            exec_debug("EXECUTION_STEP_ERROR:", e)

        return {
            "assistant_text": assistant_text,
            "intelligence": intelligence,
            "self_check": self_check,
            "hard_override_applied": hard_override_applied,
        }

    def _decide_response_strategy(
        self,
        user_text: str = "",
        decision=None,
        intelligence=None,
    ) -> dict:

        decision = decision if isinstance(decision, dict) else {}

        print(
            "[RESPONSE INTELLIGENCE DECISION DEBUG]",
            decision,
        )

        attachments = attachments or []
        assistant_text = self.safe_str(assistant_text).strip()
        intelligence = intelligence if isinstance(intelligence, dict) else {}

        text = self.safe_str(user_text).lower().strip()

        # NOVA_FORCE_IMAGE_ATTACHMENTS_ATTACHMENT_ANALYSIS_20260607
        if self._nova_has_image_attachment_20260607(attachments):
            decision = decision if isinstance(decision, dict) else {}
            decision["route"] = self.ROUTE_ATTACHMENT_ANALYSIS
            decision["mode"] = "image_analysis"
            decision["confidence"] = 1.0
            decision["reasons"] = list(decision.get("reasons") or []) + ["forced_image_attachment_analysis"]
            decision["save_artifact"] = False
            decision["save_memory"] = False
            decision["use_memory"] = False
            decision["source_urls"] = []
            decision["sources"] = []
        route = self.safe_str(decision.get("route")).lower()
        mode = self.safe_str(decision.get("mode")).lower()
        intent = self.safe_str(
            intelligence.get("intent")
            or decision.get("intent")
            or mode
            or route
            or "chat"
        ).lower()

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
            next_move = (
                "Lead with likely cause, then give the fastest verification command."
            )

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

    def _build_news_rss_queries(self, query: str) -> list[str]:
        import re

        raw_query = str(query or "").strip().lower()

        clean_query = raw_query
        for word in [
            "latest",
            "news",
            "current",
            "breaking",
            "updates",
            "update",
        ]:
            clean_query = clean_query.replace(word, "")

        clean_query = re.sub(r"\s+", " ", clean_query).strip()

        # ÃƒÆ’Ã‚Â°Ãƒâ€¦Ã‚Â¸ÃƒÂ¢Ã¢â€šÂ¬Ã‚ÂÃƒâ€šÃ‚Â¥ empty ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ global news
        if not clean_query:
            return [
                "world news",
                "breaking news",
                "top stories",
                "global headlines",
            ]

        # NOVA_WEBFETCH_OPENAI_RSS_QUERY_EXPANSION_20260607
        # Check OpenAI before generic "ai" because "openai" contains "ai".
        if "openai" in raw_query:
            return [
                "OpenAI latest news",
                "OpenAI announcement",
                "OpenAI blog",
                "OpenAI product update",
                "site:openai.com OpenAI news",
                "site:openai.com/blog OpenAI",
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

        print(
            "DEBUG ENTERED EXECUTE WEB FETCH",
            {
                "user_text": user_text,
                "decision": decision,
            },
            flush=True,
        )

        decision = decision if isinstance(decision, dict) else {}
        attachments = attachments or []
        # NOVA_WEBFETCH_INTERNAL_IMAGE_BOUNCE_20260607
        try:
            _nova_image_probe_parts = [
                self.safe_str(user_text),
                self.safe_str(decision.get("query") if isinstance(decision, dict) else ""),
                self.safe_str(decision.get("text") if isinstance(decision, dict) else ""),
            ]

            if isinstance(attachments, list):
                for _nova_attachment in attachments:
                    if isinstance(_nova_attachment, dict):
                        _nova_image_probe_parts.extend([
                            self.safe_str(_nova_attachment.get("filename")),
                            self.safe_str(_nova_attachment.get("original_filename")),
                            self.safe_str(_nova_attachment.get("name")),
                            self.safe_str(_nova_attachment.get("mime_type")),
                            self.safe_str(_nova_attachment.get("url")),
                            self.safe_str(_nova_attachment.get("file_url")),
                        ])

            _nova_image_probe = " ".join(_nova_image_probe_parts).lower()

            _nova_has_image_attachment = any(_nova_marker in _nova_image_probe for _nova_marker in (
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".gif",
                "image/jpeg",
                "image/png",
                "image/webp",
                "image/gif",
                "/api/uploads/",
                "attachment analysis failed:",
                "session attachment memory:",
            ))

            if _nova_has_image_attachment:
                user_msg = self._build_user_message(user_text, attachments=attachments)
                result = self._handle_attachment_analysis(user_text, attachments)

                assistant_msg = self._build_assistant_message(
                    meta={
                        "attachment_analysis": True,
                        "web_fetch_blocked_for_image": True,
                        "source_urls": [],
                        "sources": [],
                    },
                    attachments=[],
                )

                if isinstance(decision, dict):
                    decision["route"] = self.ROUTE_ATTACHMENT_ANALYSIS
                    decision["mode"] = "image_analysis"
                    decision["intent"] = "image_analysis"
                    decision["strategy"] = "webfetch_internal_image_bounce"
                    decision["source_urls"] = []
                    decision["sources"] = []

                return self._finalize_response(
                    session_id=session_id,
                    user_text=user_text,
                    user_msg=user_msg,
                    assistant_msg=assistant_msg,
                    decision=decision if isinstance(decision, dict) else {},
                    saved_artifact=None,
                )
        except Exception as _nova_webfetch_image_bounce_error:
            print("[NOVA_WEBFETCH_INTERNAL_IMAGE_BOUNCE] failed:", _nova_webfetch_image_bounce_error)


        text = str(user_text or "").strip()
        user_msg = self._build_user_message(user_text, attachments=attachments)

        # NOVA_WEBFETCH_CODE_COMMAND_BOUNCE_20260622
        # If a normal code/command prompt accidentally enters web_fetch after a prior news request,
        # answer as code instead of using stale web/news context.
        try:
            _code_probe = text.lower()

            _code_markers = (
                "powershell",
                "code block",
                "```",
                "terminal",
                "command",
                "cmd",
                "bash",
                "shell",
            )

            _code_verbs = (
                "show me",
                "give me",
                "write",
                "make",
                "create",
                "generate",
                "example",
            )

            _is_code_command_request = (
                any(_marker in _code_probe for _marker in _code_markers)
                and any(_verb in _code_probe for _verb in _code_verbs)
            )

            if _is_code_command_request:
                if "powershell" in _code_probe:
                    _reply = "```powershell\nGet-Process\n```"
                elif "bash" in _code_probe or "shell" in _code_probe or "terminal" in _code_probe:
                    _reply = "```bash\nls -la\n```"
                else:
                    _reply = "```text\nexample command\n```"

                assistant_msg = self._build_assistant_message(
                    _reply,
                    meta={
                        "route": "final_session_detail_response_cache",
                        "strategy": "code_command_bounced_from_web_fetch",
                        "web_fetch_blocked_for_code": True,
                        "source_urls": [],
                        "sources": [],
                    },
                )

                return self._finalize_response(
                    session_id=session_id,
                    user_msg=user_msg,
                    assistant_msg=assistant_msg,
                    saved_artifact=None,
                )
        except Exception as _nova_code_bounce_error:
            print("[NOVA_WEBFETCH_CODE_COMMAND_BOUNCE] failed:", _nova_code_bounce_error)

        # EXECUTE_WEB_FETCH_ATTACHMENT_CHOKE_LOCK
        # app.py injects attachment text into user_text, then suppresses raw attachments before chat_service.
        # That means attachments can be empty here even though this is an attachment request.
        # If attachment-injected text reaches the web fetch lane, answer from the attachment text instead
        # of opening cached Google News / direct URLs.
        try:
            import re as _nova_attach_re

            _attach_text = str(user_text or "")
            _attach_lower = _attach_text.lower()

            _has_injected_attachment = (
                "attachment content:" in _attach_lower
                or "uploaded attachment context below" in _attach_lower
                or "extracted attachment text" in _attach_lower
                or "[mobile quick action attachment context active]" in _attach_lower
                or "uploaded pdf attachment" in _attach_lower
                or "uploaded attachment" in _attach_lower
            )

            if _has_injected_attachment:
                _noise_exact = {
                    "attachment <unknown> content:",
                    "attachment content:",
                    "uploaded attachment content:",
                    "[pdf page 1]",
                    "search",
                    "images",
                    "videos",
                    "create",
                    "inspiration",
                    "keypoints",
                    "continue",
                    "summarize",
                    "summary",
                    "cop",
                    "filt",
                    "moderate",
                    "amazon",
                    "bath",
                    "related content",
                }

                _noise_contains = (
                    "wayfair",
                    "save big",
                    "prices you'll love",
                    "eye-catching prints",
                    "url removed from extracted attachment text",
                    "free_shipping",
                    "furniture & dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cor",
                    "kitchen appliances",
                    "love, horror and more themes",
                    "plain field in front of mountain peak",
                    "free stock photo",
                    "news.google.com",
                    "direct_url_patch_hit",
                )

                _lines = []
                _seen = set()

                for _raw in _attach_text.splitlines():
                    _line = _nova_attach_re.sub(
                        r"^\s*\d+\.\s*", "", str(_raw or "")
                    ).strip()
                    _line = _line.replace("Attachment <unknown>", "uploaded attachment")
                    _line = _line.replace("Attachment content:", "").strip()
                    _line = _nova_attach_re.sub(r"\s+", " ", _line).strip()

                    if not _line:
                        continue

                    _low = _line.lower().strip(" :;-ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¢*|")
                    _compact = _nova_attach_re.sub(r"[^a-z0-9]+", " ", _low).strip()

                    if _compact in _noise_exact:
                        continue

                    if any(_bad in _low for _bad in _noise_contains):
                        continue

                    if _line.startswith("http://") or _line.startswith("https://"):
                        continue

                    if len(_line) <= 2:
                        continue

                    if _low.startswith("typed user text"):
                        continue

                    if _low.startswith("uploaded attachment context below"):
                        continue

                    if _low.startswith("extracted attachment text"):
                        continue

                    if _low.startswith(
                        "[mobile quick action attachment context active]"
                    ):
                        continue

                    if not _compact or _compact in _seen:
                        continue

                    _seen.add(_compact)
                    _lines.append(_line)

                _top = _lines[:8]

                _bad_context_markers = (
                    "project-aware context for nova:",
                    "relevant persistent memory:",
                    "recent session context:",
                    "persistent memory:",
                    "[preference]",
                    "[user_fact]",
                    "[people]",
                )

                if any(
                    _marker in str(user_text or "").lower()
                    for _marker in _bad_context_markers
                ):
                    raise RuntimeError("ignored injected Nova context as attachment text")

                if _top:
                    _topic = "; ".join(_top[:3])

                    _reply = "Attachment summary:\n"
                    _reply += f"{_topic}\n\n"

                    _reply += "Extracted highlights:\n"
                    for _i, _item in enumerate(_top, start=1):
                        _reply += f"{_i}. {_item}\n"

                    _reply += "\nPreview:\n" + "\n".join(_top[:6])
                else:
                    _reply = (
                        "Attachment received:\n"
                        "The attachment was received and text was extracted, but the available extraction looks too noisy to summarize cleanly."
                    )

                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": _reply.strip(),
                    },
                    "debug": {
                        "route": "execute_web_fetch_attachment_choke",
                        "blocked_web_hijack": True,
                    },
                    "skip_cleanup": True,
                    "skip_post_processing": True,
                    "skip_rewrite": True,
                }

        except Exception:
            pass

        # OPEN_WEB_SOURCE_FOLLOWUP_HANDLER_LOCK
        # ATTACHMENT_SOURCE_ROUTER_GUARD_LOCK: source/web follow-up routes must not hijack attachment messages.
        if (not attachments) and (
            self.safe_str(decision.get("strategy")).strip().lower()
            == "open_web_source_followup"
        ):
            import re

            source_index = 0
            lowered = text.lower()

            index_map = {
                "first": 0,
                "one": 0,
                "1": 0,
                "second": 1,
                "two": 1,
                "2": 1,
                "third": 2,
                "three": 2,
                "3": 2,
                "fourth": 3,
                "four": 3,
                "4": 3,
                "fifth": 4,
                "five": 4,
                "5": 4,
            }

            for marker, idx in index_map.items():
                if re.search(rf"\b{re.escape(marker)}\b", lowered):
                    source_index = idx
                    break

            prior_urls = []
            prior_sources = []

            try:
                session_payload = self._get_session_payload(session_id)
                messages = (
                    session_payload.get("messages")
                    if isinstance(session_payload, dict)
                    else []
                )
                messages = messages if isinstance(messages, list) else []

                for msg in reversed(messages):
                    if not isinstance(msg, dict):
                        continue

                    if self.safe_str(msg.get("role")).lower() != "assistant":
                        continue

                    meta = msg.get("meta") if isinstance(msg.get("meta"), dict) else {}
                    urls = meta.get("source_urls")
                    sources = meta.get("sources")

                    if isinstance(urls, list) and urls:
                        prior_urls = [
                            self.safe_str(url).strip()
                            for url in urls
                            if self.safe_str(url).strip()
                        ]
                        prior_sources = sources if isinstance(sources, list) else []
                        break
            except Exception as exc:
                exec_debug("OPEN_WEB_SOURCE_FOLLOWUP_LOOKUP_FAILED:", exc)

            # ATTACHMENT_SOURCE_ROUTER_GUARD_LOCK: source/web follow-up routes must not hijack attachment messages.
            if (not attachments) and (
                (not prior_urls or source_index >= len(prior_urls))
                and isinstance(getattr(self, "_last_web_source_urls", None), list)
            ):
                cached_urls = [
                    self.safe_str(url).strip()
                    for url in getattr(self, "_last_web_source_urls", [])
                    if self.safe_str(url).strip()
                ]

                # ATTACHMENT_SOURCE_ROUTER_GUARD_LOCK: source/web follow-up routes must not hijack attachment messages.
                if (not attachments) and (cached_urls):
                    prior_urls = cached_urls
                    cached_sources = getattr(self, "_last_web_sources", [])
                    prior_sources = (
                        cached_sources if isinstance(cached_sources, list) else []
                    )

            # WEB_FOLLOWUP_DURABLE_SOURCE_CACHE_LOCK
            # ATTACHMENT_SOURCE_ROUTER_GUARD_LOCK: source/web follow-up routes must not hijack attachment messages.
            if (not attachments) and (
                not prior_urls or source_index >= len(prior_urls)
            ):
                try:
                    import json
                    from pathlib import Path

                    cache_path = Path(
                        r"C:\Users\Owner\nova\data\nova_last_web_sources.json"
                    )

                    if cache_path.exists():
                        cache_data = json.loads(
                            cache_path.read_text(encoding="utf-8") or "{}"
                        )
                        cached_urls = cache_data.get("source_urls")
                        cached_sources = cache_data.get("sources")

                        if isinstance(cached_urls, list) and cached_urls:
                            prior_urls = [
                                self.safe_str(url).strip()
                                for url in cached_urls
                                if self.safe_str(url).strip()
                            ]
                            prior_sources = (
                                cached_sources
                                if isinstance(cached_sources, list)
                                else []
                            )
                except Exception as exc:
                    exec_debug("WEB_FOLLOWUP_DURABLE_SOURCE_CACHE_READ_FAILED:", exc)

            # ATTACHMENT_SOURCE_ROUTER_GUARD_LOCK: source/web follow-up routes must not hijack attachment messages.
            # CHAT_SERVICE_ATTACHMENT_SOURCE_GUARD_LOCK
            attachment_language = any(
                phrase in str(user_text or "").lower()
                for phrase in (
                    "attachment",
                    "attached",
                    "upload",
                    "uploaded",
                    "image",
                    "picture",
                    "photo",
                    "file",
                    "pdf",
                    "screenshot",
                    "what is in this",
                    "what's in this",
                    "analyze this",
                    "describe this",
                    "summarize this",
                )
            )

            if attachment_language and (
                not prior_urls or source_index >= len(prior_urls)
            ):
                assistant_msg = self._build_assistant_message(
                    "I see you are asking about an uploaded attachment, but I did not receive usable attachment data in this chat request. Re-upload the image/file, then send the question again.",
                    meta={
                        "strategy": "attachment_expected_but_missing",
                        "source_index": source_index,
                        "source_urls": prior_urls,
                        "sources": (
                            prior_sources[:5] if isinstance(prior_sources, list) else []
                        ),
                    },
                )

                return self._finalize_response(
                    session_id=session_id,
                    user_text=user_text,
                    user_msg=user_msg,
                    assistant_msg=assistant_msg,
                    messages=messages,
                    memory_items=locals().get("memory_items")
                    or locals().get("memory_context")
                    or [],
                    started_at=locals().get("started_at")
                    or locals().get("now_iso")
                    or "",
                    route="attachment_expected_but_missing",
                    intent="attachment",
                )

            if (not attachments) and (
                not prior_urls or source_index >= len(prior_urls)
            ):
                assistant_msg = self._build_assistant_message(
                    "I could not find a previous source to open. Run a fresh web search first.",
                    meta={
                        "strategy": "open_web_source_followup",
                        "source_index": source_index,
                        "source_urls": prior_urls,
                        "sources": (
                            prior_sources[:5] if isinstance(prior_sources, list) else []
                        ),
                    },
                )

                return self._finalize_response(
                    session_id=session_id,
                    user_text=user_text,
                    user_msg=user_msg,
                    assistant_msg=assistant_msg,
                    decision=decision,
                )

            selected_url = prior_urls[source_index]
            decision["mode"] = "direct_url"
            decision["url"] = selected_url
            decision["source_index"] = source_index

            text = selected_url

        # DIRECT_URL_TRUE_REASON_ONLY_LOCK
        # Only run direct URL fetch when route decision originally classified the USER input as a direct URL.
        # Cached source URLs / Google News URLs can also get copied into `text`, but they must not hijack
        # attachment quick actions like Summarize / Keypoints / Continue.
        original_user_text_for_direct_url = self.safe_str(user_text).strip()
        direct_url_reasons = (
            decision.get("reasons") if isinstance(decision, dict) else []
        )
        direct_url_reasons = (
            direct_url_reasons if isinstance(direct_url_reasons, list) else []
        )

        if (
            (not attachments)
            and ("direct_url" in direct_url_reasons)
            and (
                original_user_text_for_direct_url.startswith("http://")
                or original_user_text_for_direct_url.startswith("https://")
            )
            and (text.startswith("http://") or text.startswith("https://"))
        ):
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

            source_url = self.safe_str(
                web_result.get("final_url")
                or web_result.get("source_url")
                or web_result.get("url")
                or text
            ).strip()

            title = self.safe_str(
                web_result.get("title") or source_url or text
            ).strip()

            summary = self.safe_str(
                web_result.get("summary")
                or web_result.get("description")
                or web_result.get("preview")
                or ""
            ).strip()

            body = self.safe_str(
                web_result.get("content")
                or web_result.get("body")
                or web_result.get("text")
                or ""
            ).strip()

            error = self.safe_str(web_result.get("error") or "").strip()

            if error and not summary and not body:
                assistant_text = "Web fetch failed:\n" + error
            else:
                summary_looks_raw = (
                    len(summary) > 400
                    or "search wikipedia" in summary.lower()
                    or "ÃƒÆ’Ã†â€™Ãƒâ€¹Ã…â€œ" in summary
                    or "ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢" in summary
                    or "ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â" in summary
                    or "ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢" in summary
                    or "ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¦" in summary
                )

                assistant_text = "" if summary_looks_raw else summary

                if not assistant_text and (body or summary):
                    try:
                        clean_body = self._clean_web_text((body or summary)[:5000])

                        prompt = (
                            "Summarize this fetched webpage cleanly.\n"
                            "Do not dump navigation text.\n"
                            "Do not include broken encoding noise.\n"
                            "Use 2-4 short bullets.\n\n"
                            f"Page title: {title}\n"
                            f"URL: {source_url}\n\n"
                            f"Page text:\n{clean_body}"
                        )

                        response = chat_completions_create(
                            nova_username=getattr(self, "username", None) or os.getenv("NOVA_DEFAULT_USERNAME") or "richard",
                            nova_session_id=locals().get("session_id") or getattr(getattr(self, "session_service", None), "active_session_id", "") or "",
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

        query = self.safe_str(
            decision.get("query")
            or decision.get("search_query")
            or decision.get("url")
            or user_text
        ).strip()

        freshness_words = [
            "latest",
            "right now",
            "current",
            "breaking",
            "recent",
            "news",
            "update",
            "updates",
        ]

        sports_history_words = [
            "knicks",
            "spurs",
            "nba finals",
            "finals",
            "game 5",
            "viewership",
            "watched",
            "ratings",
        ]

        is_sports_history_query = any(
            word in query.lower()
            for word in sports_history_words
        )

        if is_sports_history_query:
            query = query.replace(" today", "").strip()

        if (
            not is_sports_history_query
            and any(word in query.lower() for word in freshness_words)
        ):
            if "today" not in query.lower():
                query = query + " today"


        self._last_web_query = query

        conversation_context = ""
        previous_web_context = {}

        try:
            session = (
                self._get_session_payload(session_id)
                or self.session_service.get_session(session_id)
                or {}
            )
            messages = (
                session.get("messages", [])
                if isinstance(session, dict)
                else []
            )

            context_lines = []

            for message in messages[-10:]:
                if not isinstance(message, dict):
                    continue

                role = self.safe_str(
                    message.get("role") or "unknown"
                ).strip()

                content = self.safe_str(
                    message.get("text")
                    or message.get("content")
                    or ""
                ).strip()

                if not content:
                    continue

                context_lines.append(
                    f"{role}: {content[:1200]}"
                )

            previous_web_context = (
                self._get_session_meta(
                    session_id,
                    "last_verified_web_exchange",
                )
                or {}
            )

            if isinstance(previous_web_context, dict):
                previous_query = self.safe_str(
                    previous_web_context.get("query")
                ).strip()
                previous_answer = self.safe_str(
                    previous_web_context.get("answer")
                ).strip()

                if previous_query:
                    context_lines.append(
                        "Previous verified web question: "
                        + previous_query[:1200]
                    )

                if previous_answer:
                    context_lines.append(
                        "Previous verified web answer: "
                        + previous_answer[:2400]
                    )

            conversation_context = "\n".join(
                context_lines
            )[-6000:]

        except Exception as exc:
            exec_debug(
                "WEB_CONVERSATION_CONTEXT_ERROR:",
                exc,
            )

        resolved_search_query = query
        query_lc = query.lower()

        contextual_followup_markers = (
            " they ",
            " them ",
            " their ",
            " he ",
            " she ",
            " it ",
            " that ",
            " those ",
            " the final",
            "what about",
            "how about",
            "and what",
        )

        padded_query = f" {query_lc} "

        if (
            isinstance(previous_web_context, dict)
            and previous_web_context
            and any(
                marker in padded_query
                for marker in contextual_followup_markers
            )
        ):
            previous_query = self.safe_str(
                previous_web_context.get("query")
            ).strip()
            previous_answer = self.safe_str(
                previous_web_context.get("answer")
            ).strip()

            resolved_search_query = (
                "Resolve and research this conversational follow-up.\n"
                f"Previous verified question: {previous_query}\n"
                f"Previous verified answer: {previous_answer}\n"
                f"Follow-up question: {query}"
            )

        web_result = {"results": []}

        try:
            search_service = (
                getattr(self, "web_service", None)
                or getattr(self, "web", None)
            )

            if (
                search_service is not None
                and callable(
                    getattr(search_service, "search", None)
                )
            ):
                web_result = search_service.search(
                    resolved_search_query,
                    max_results=10,
                    context=conversation_context,
                )
            elif hasattr(self, "_web_search"):
                web_result = self._web_search(query)

            if not isinstance(web_result, dict):
                web_result = {"body": str(web_result or ""), "results": []}

            if (
                web_result.get("ok")
                and web_result.get("results")
            ):
                try:
                    verified_answer = self.safe_str(
                        web_result.get("body")
                        or web_result.get("summary")
                        or ""
                    ).strip()

                    verified_exchange = {
                        "query": query,
                        "answer": verified_answer[:4000],
                        "source_type": self.safe_str(
                            web_result.get("source_type")
                        ),
                    }

                    if isinstance(decision, dict):
                        decision[
                            "last_verified_web_exchange"
                        ] = verified_exchange

                    try:
                        self._set_session_meta(
                            session_id,
                            "last_verified_web_exchange",
                            verified_exchange,
                        )
                    except Exception:
                        pass

                except Exception as exc:
                    exec_debug(
                        "SAVE_VERIFIED_WEB_EXCHANGE_ERROR:",
                        exc,
                    )


        except Exception as e:
            exec_debug("WEB_FETCH_ERROR:", e)
            web_result = {"results": []}

        exec_debug("WEB_FETCH_QUERY:", query)
        exec_debug("WEB_FETCH_RESULT_TYPE:", type(web_result))
        exec_debug("WEB_FETCH_RESULT:", web_result)

        raw_results = (
            web_result.get("results", []) if isinstance(web_result, dict) else []
        )
        # ATTACHMENT_SOURCE_ROUTER_GUARD_LOCK: source/web follow-up routes must not hijack attachment messages.
        if (not attachments) and (not isinstance(raw_results, list)):
            raw_results = []

        # NOVA_WEBFETCH_SITE_DOMAIN_LOCK_20260607
        # If the user explicitly uses site:domain, keep only matching-domain results.
        # This prevents generic Google News / AI-adjacent results from polluting exact-site searches.
        try:
            import re as _nova_site_re
            from urllib.parse import urlparse as _nova_site_urlparse

            _nova_site_match = _nova_site_re.search(
                r"\bsite:([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b",
                query or "",
            )

            if _nova_site_match:
                _nova_site_domain = _nova_site_match.group(1).lower().strip()
                _nova_filtered_results = []

                for _nova_item in raw_results if isinstance(raw_results, list) else []:
                    if not isinstance(_nova_item, dict):
                        continue

                    _nova_url = self.safe_str(
                        _nova_item.get("url")
                        or _nova_item.get("href")
                        or _nova_item.get("link")
                        or ""
                    ).strip()

                    _nova_title = self.safe_str(_nova_item.get("title") or "").lower()
                    _nova_snippet = self.safe_str(
                        _nova_item.get("snippet")
                        or _nova_item.get("description")
                        or _nova_item.get("content")
                        or ""
                    ).lower()

                    _nova_host = ""
                    try:
                        _nova_host = _nova_site_urlparse(_nova_url).netloc.lower().replace("www.", "")
                    except Exception:
                        _nova_host = ""

                    # NOVA_WEBFETCH_SITE_DOMAIN_STRICT_LOCK_20260607
                    # For explicit site:domain searches, only the actual URL host counts.
                    # Do not keep news.google.com or unrelated articles merely because
                    # the snippet/title mentions the requested domain.
                    if (
                        _nova_host == _nova_site_domain
                        or _nova_host.endswith("." + _nova_site_domain)
                    ):
                        _nova_filtered_results.append(_nova_item)

                raw_results = _nova_filtered_results
                exec_debug("NOVA_WEBFETCH_SITE_DOMAIN_LOCK_DOMAIN:", _nova_site_domain)
                exec_debug("NOVA_WEBFETCH_SITE_DOMAIN_LOCK_COUNT:", len(raw_results))
        except Exception as _nova_site_exc:
            exec_debug("NOVA_WEBFETCH_SITE_DOMAIN_LOCK_FAILED:", _nova_site_exc)

        cleaned_sources = self._clean_web_results(raw_results)

        # NOVA_WEBFETCH_OPENAI_ENTITY_FILTER_LOCK_20260607
        # If the user specifically asks about OpenAI, do not surface generic AI-news
        # results that never mention OpenAI in title/snippet/source/url.
        try:
            _nova_openai_probe = " ".join([
                self.safe_str(query),
                self.safe_str(user_text),
                self.safe_str(decision.get("query") if isinstance(decision, dict) else ""),
                self.safe_str(decision.get("search_query") if isinstance(decision, dict) else ""),
            ]).lower()

            if "openai" in _nova_openai_probe and isinstance(cleaned_sources, list):
                _nova_openai_sources = []

                for _nova_item in cleaned_sources:
                    if not isinstance(_nova_item, dict):
                        continue

                    _nova_blob = " ".join([
                        self.safe_str(_nova_item.get("title")),
                        self.safe_str(_nova_item.get("snippet")),
                        self.safe_str(_nova_item.get("content")),
                        self.safe_str(_nova_item.get("source")),
                        self.safe_str(_nova_item.get("url")),
                    ]).lower()

                    if "openai" in _nova_blob:
                        _nova_openai_sources.append(_nova_item)

                cleaned_sources = _nova_openai_sources
                exec_debug("NOVA_WEBFETCH_OPENAI_ENTITY_FILTER_COUNT:", len(cleaned_sources))

                # NOVA_WEBFETCH_OPENAI_OFFICIAL_FALLBACK_SOURCES_20260607
                # If OpenAI-specific search returns no surviving results, provide official
                # OpenAI source pages instead of returning unrelated generic AI news.
                if not cleaned_sources:
                    cleaned_sources = [
                        {
                            "title": "OpenAI News",
                            "snippet": "Official OpenAI news and announcements.",
                            "content": "Official OpenAI news and announcements.",
                            "source": "openai.com",
                            "url": "https://openai.com/news/",
                        },
                        {
                            "title": "OpenAI Company Announcements",
                            "snippet": "Official OpenAI company announcement feed.",
                            "content": "Official OpenAI company announcement feed.",
                            "source": "openai.com",
                            "url": "https://openai.com/news/company-announcements/",
                        },
                        {
                            "title": "OpenAI Product Releases",
                            "snippet": "Official OpenAI product release feed.",
                            "content": "Official OpenAI product release feed.",
                            "source": "openai.com",
                            "url": "https://openai.com/news/product-releases/",
                        },
                        {
                            "title": "OpenAI Research",
                            "snippet": "Official OpenAI research news feed.",
                            "content": "Official OpenAI research news feed.",
                            "source": "openai.com",
                            "url": "https://openai.com/news/research/",
                        },
                        {
                            "title": "OpenAI Developer Blog",
                            "snippet": "Official OpenAI developer updates and technical posts.",
                            "content": "Official OpenAI developer updates and technical posts.",
                            "source": "developers.openai.com",
                            "url": "https://developers.openai.com/blog/",
                        },
                    ]
                    exec_debug("NOVA_WEBFETCH_OPENAI_OFFICIAL_FALLBACK_COUNT:", len(cleaned_sources))
        except Exception as _nova_openai_filter_exc:
            exec_debug("NOVA_WEBFETCH_OPENAI_ENTITY_FILTER_FAILED:", _nova_openai_filter_exc)

        # NOVA_WEBFETCH_GENERIC_NEWS_BAD_SOURCE_FILTER_20260608
        # For broad news prompts, remove generic landing-page / homepage results
        # before ranking and final source-card construction.
        try:
            _nova_generic_news_probe = " ".join([
                self.safe_str(query),
                self.safe_str(user_text),
            ]).lower()

            _nova_is_generic_news_query = any(
                phrase in _nova_generic_news_probe
                for phrase in [
                    "whats on the news",
                    "what's on the news",
                    "what is on the news",
                    "latest news",
                    "news today",
                    "headlines",
                ]
            )

            if _nova_is_generic_news_query and isinstance(cleaned_sources, list):
                _nova_filtered_news_sources = []

                for _nova_item in cleaned_sources:
                    if not isinstance(_nova_item, dict):
                        continue

                    _nova_title = self.safe_str(_nova_item.get("title")).lower()
                    _nova_snippet = self.safe_str(
                        _nova_item.get("snippet")
                        or _nova_item.get("description")
                        or _nova_item.get("content")
                        or ""
                    ).lower()
                    _nova_source = self.safe_str(_nova_item.get("source")).lower()
                    _nova_url = self.safe_str(
                        _nova_item.get("url")
                        or _nova_item.get("href")
                        or _nova_item.get("link")
                        or ""
                    ).lower()

                    _nova_blob = " ".join([
                        _nova_title,
                        _nova_snippet,
                        _nova_source,
                        _nova_url,
                    ])

                    _nova_bad_landing = any(
                        bad in _nova_blob
                        for bad in [
                            "nbc news - breaking headlines",
                            "breaking headlines and video reports",
                            "new york stock exchange",
                            "the new york stock exchange",
                            "nyse homepage",
                            " | nyse",
                        ]
                    )

                    if _nova_bad_landing:
                        exec_debug(
                            "NOVA_WEBFETCH_GENERIC_NEWS_BAD_SOURCE_SKIPPED:",
                            {
                                "title": _nova_item.get("title"),
                                "source": _nova_item.get("source"),
                                "url": _nova_item.get("url"),
                            },
                        )
                        continue

                    _nova_filtered_news_sources.append(_nova_item)

                cleaned_sources = _nova_filtered_news_sources
                exec_debug("NOVA_WEBFETCH_GENERIC_NEWS_BAD_SOURCE_COUNT:", len(cleaned_sources))
        except Exception as _nova_bad_source_filter_exc:
            exec_debug("NOVA_WEBFETCH_GENERIC_NEWS_BAD_SOURCE_FILTER_FAILED:", _nova_bad_source_filter_exc)
        def _rank_key(item):
            url = self.safe_str(item.get("url")).lower()
            title = self.safe_str(item.get("title")).lower()
            snippet = self.safe_str(
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

            if any(
                x in url
                for x in [
                    "reuters.com",
                    "apnews.com",
                    "bbc.com",
                    "bloomberg.com",
                    "cnbc.com",
                    "cbc.ca",
                    "globalnews.ca",
                    "ctvnews.ca",
                ]
            ):
                priority += 100

            if any(
                x in url
                for x in [
                    "espn.com",
                    "cbssports.com",
                    "sports.yahoo.com",
                    "tsn.ca",
                    "sportsnet.ca",
                ]
            ):
                priority += 80

            if any(
                x in url
                for x in ["pwinsider.com", "fightful.com", "wrestlingobserver.com"]
            ):
                priority += 60

            if any(x in title for x in ["rumor", "reaction", "opinion"]):
                priority -= 40

            return priority

        try:
            cleaned_sources = sorted(cleaned_sources, key=_rank_key, reverse=True)
        except Exception as e:
            exec_debug("FINAL_RANK_ERROR:", e)

        body = self.safe_str(
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

            title = self.safe_str(item.get("title") or item.get("name") or "").strip()
            rss_source = ""
            if " - " in title:
                title_parts = title.rsplit(" - ", 1)
                title = title_parts[0].strip()
                rss_source = title_parts[1].strip()
            url = self.safe_str(
                item.get("url") or item.get("href") or item.get("link") or ""
            ).strip()

            snippet = self.safe_str(
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

            sources.append(
                {
                    "title": title,
                    "url": url,
                    "source": source,
                    "snippet": snippet,
                }
            )

            source_urls.append(url)

            if snippet and snippet not in body:
                body += "\n\n" + snippet

        # NOVA_WEBFETCH_FINAL_NEWS_BAD_SOURCE_FILTER_20260608
        # Final guard: remove broad landing pages after source cards are built.
        try:
            _nova_final_news_probe = " ".join([
                self.safe_str(query),
                self.safe_str(user_text),
            ]).lower()

            _nova_final_is_news = any(
                phrase in _nova_final_news_probe
                for phrase in [
                    "whats on the news",
                    "what's on the news",
                    "what is on the news",
                    "latest news",
                    "news today",
                    "headlines",
                ]
            )

            if _nova_final_is_news and isinstance(sources, list):
                _nova_clean_final_sources = []

                for _nova_source_item in sources:
                    if not isinstance(_nova_source_item, dict):
                        continue

                    _nova_blob = " ".join([
                        self.safe_str(_nova_source_item.get("title")),
                        self.safe_str(_nova_source_item.get("snippet")),
                        self.safe_str(_nova_source_item.get("source")),
                        self.safe_str(_nova_source_item.get("url")),
                    ]).lower()

                    _nova_bad_final_source = any(
                        bad in _nova_blob
                        for bad in [
                            "nbc news - breaking headlines",
                            "breaking headlines and video reports",
                            "new york stock exchange",
                            "the new york stock exchange",
                            " | nyse",
                        ]
                    )

                    if _nova_bad_final_source:
                        exec_debug(
                            "NOVA_WEBFETCH_FINAL_NEWS_BAD_SOURCE_SKIPPED:",
                            {
                                "title": _nova_source_item.get("title"),
                                "source": _nova_source_item.get("source"),
                                "url": _nova_source_item.get("url"),
                            },
                        )
                        continue

                    _nova_clean_final_sources.append(_nova_source_item)

                sources = _nova_clean_final_sources
                source_urls = [
                    item.get("url")
                    for item in sources
                    if isinstance(item, dict) and item.get("url")
                ]
                exec_debug("NOVA_WEBFETCH_FINAL_NEWS_BAD_SOURCE_COUNT:", len(sources))
        except Exception as _nova_final_news_filter_exc:
            exec_debug("NOVA_WEBFETCH_FINAL_NEWS_BAD_SOURCE_FILTER_FAILED:", _nova_final_news_filter_exc)
        def _final_source_rank(source_item):
            title_value = self.safe_str(source_item.get("title")).lower()

            source_value = self.safe_str(source_item.get("source")).lower()

            snippet_value = self.safe_str(source_item.get("snippet")).lower()

            combined = title_value + " " + source_value + " " + snippet_value

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

        # ATTACHMENT_SOURCE_ROUTER_GUARD_LOCK: source/web follow-up routes must not hijack attachment messages.
        if (not attachments) and (not body and sources):
            body = "\n".join(
                item.get("title", "")
                for item in sources
                if isinstance(item, dict) and item.get("title")
            )

        # ATTACHMENT_SOURCE_ROUTER_GUARD_LOCK: source/web follow-up routes must not hijack attachment messages.
        if (not attachments) and (not body):
            # NOVA_WEBFETCH_SITE_EMPTY_MESSAGE_LOCK_20260607
            try:
                import re as _nova_empty_site_re
                # NOVA_WEBFETCH_SITE_EMPTY_USER_TEXT_LOCK_20260607
                _nova_empty_site_probe = " ".join([
                    str(query or ""),
                    str(user_text or ""),
                    str(decision.get("query") if isinstance(decision, dict) else ""),
                    str(decision.get("search_query") if isinstance(decision, dict) else ""),
                ])

                _nova_empty_site_match = _nova_empty_site_re.search(
                    r"\bsite:([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b",
                    _nova_empty_site_probe,
                )
            except Exception:
                _nova_empty_site_match = None

            if _nova_empty_site_match:
                _nova_empty_site_domain = _nova_empty_site_match.group(1).lower().strip()
                assistant_text = (
                    f"No matching results were found from {_nova_empty_site_domain}.\n\n"
                    f"I did not use unrelated sources because the search was constrained to site:{_nova_empty_site_domain}."
                )
            else:
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

                response = chat_completions_create(
                    nova_username=getattr(self, "username", None) or os.getenv("NOVA_DEFAULT_USERNAME") or "richard",
                    nova_session_id=locals().get("session_id") or getattr(getattr(self, "session_service", None), "active_session_id", "") or "",
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
                        assistant_text = assistant_text[
                            : assistant_text.lower().find(marker.lower())
                        ].strip()

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

            title_value = self.safe_str(item.get("title")).strip()

            url_value = self.safe_str(item.get("url")).strip()

            source_value = self.safe_str(item.get("source")).strip()

            snippet_value = self.safe_str(item.get("snippet")).strip()

            snippet_value = html.unescape(snippet_value)
            snippet_value = re.sub(
                r"<[^>]+>",
                "",
                snippet_value,
            )
            snippet_value = (
                snippet_value.replace(
                    "\xa0",
                    " ",
                )
                .replace(
                    "&nbsp;",
                    " ",
                )
                .strip()
            )

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
            title_value = self.safe_str(item.get("title")).lower()

            source_value = self.safe_str(item.get("source")).lower()

            snippet_value = self.safe_str(item.get("snippet")).lower()

            combined = title_value + " " + source_value + " " + snippet_value

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

        # WEB_FOLLOWUP_LAST_SOURCE_CACHE_LOCK
        try:
            self._last_web_source_urls = [
                self.safe_str(url).strip()
                for url in source_urls[:5]
                if self.safe_str(url).strip()
            ]
            self._last_web_sources = sources[:5] if isinstance(sources, list) else []
        except Exception as exc:
            exec_debug("WEB_FOLLOWUP_LAST_SOURCE_CACHE_FAILED:", exc)

        try:
            import json
            from pathlib import Path

            cache_path = Path(r"C:\Users\Owner\nova\data\nova_last_web_sources.json")
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            cache_payload = {
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "session_id": self.safe_str(session_id),
                "query": self.safe_str(query),
                "source_urls": [
                    self.safe_str(url).strip()
                    for url in source_urls[:5]
                    if self.safe_str(url).strip()
                ],
                "sources": sources[:5] if isinstance(sources, list) else [],
            }

            cache_path.write_text(
                json.dumps(cache_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            exec_debug("WEB_FOLLOWUP_DURABLE_SOURCE_CACHE_WRITE_FAILED:", exc)

        exec_debug("WEB_SOURCES_FINAL:", sources)
        exec_debug("WEB_SOURCE_URLS_FINAL:", source_urls)
        exec_debug(
            "WEB_SOURCE_ORDER_FINAL:",
            [item.get("source") for item in sources if isinstance(item, dict)],
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
            url = self.safe_str(url).strip()

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

                final_url = self.safe_str(response.url).strip()

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

            final_url = self.safe_str(response.url).strip()

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

        if text.startswith("/image"):
            return True

        explicit_image_requests = (
            "generate an image",
            "generate image",
            "create an image",
            "create image",
            "make an image",
            "make image",
            "draw me",
            "draw a",
            "draw an",
        )

        return text.startswith(explicit_image_requests)

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

    def _handle_execution_control(
        self,
        user_text: str,
        session_id: str,
        attachments=None,
    ):

        print(
            "DEBUG EXEC CONTROL ENTRY",
            {
                "session_id": session_id,
                "user_text": user_text,
            },
        )

        text = self.safe_str(
            user_text
        ).strip().lower()
        active_execution = (
            self._load_execution_state(
                session_id
            )
            or {}
        )

        if not active_execution.get("steps"):
            meta_execution = self._get_session_meta(
                session_id,
                "active_execution",
                {},
            )

            if (
                isinstance(meta_execution, dict)
                and meta_execution.get("steps")
            ):
                active_execution = meta_execution

        active_steps = (
            active_execution.get("steps")
            or []
        )

        active_index = int(
            active_execution.get(
                "current_index",
                0,
            )
            or 0
        )

        if (
            active_steps
            and active_index < len(active_steps)
        ):
            active_step = active_steps[
                active_index
            ]

            if (
                active_step.get(
                    "next_action"
                )
                == "request_target"
                and text not in {
                    "next",
                    "continue",
                    "go",
                    "run",
                }
            ):
                execution_result = (
                    self.chat_execution_service.advance(
                        session_id,
                        user_text=user_text,
                    )
                )

                if isinstance(
                    execution_result,
                    dict,
                ):
                    execution_state = (
                        execution_result.get(
                            "execution_state"
                        )
                        or execution_result.get(
                            "execution"
                        )
                        or execution_result
                    )

                    if isinstance(
                        execution_state,
                        dict,
                    ):
                        self._save_execution_state(
                            session_id,
                            execution_state,
                        )

                return execution_result
        print(
            "MISSION COMMAND DEBUG =",
            {
                "text": text,
                "session_id": session_id,
            },
            flush=True,
        )

        print(
            "DEBUG BEFORE RESOLVE",
            {
                "user_text": user_text,
                "session_id": session_id,
            },
            flush=True,
        )

        # NOVA_DIRECT_REPAIR_REQUEST_GATE
        # Explicit repair requests should enter auto-fix instead of general chat.

        if any(
            phrase in text
            for phrase in [
                "apply the repair",
                "apply repair",
                "apply the fix",
                "apply fix",
                "write the fix",
                "write fix",
                "commit fix",
            ]
        ):
            return self._apply_pending_fix(
                session_id
            )


        if (
            "repair " in text
            or (
                "fix " in text
                and (
                    ".py" in text
                    or "file" in text
                    or "function" in text
                )
            )
        ):

            repair_result = self._process_auto_fix(
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
            )

            if repair_result is not None:
                return repair_result

        execution_state = (
            self._load_execution_state(session_id)
            or {}
        )

        steps = execution_state.get("steps") or []
        current_index = int(
            execution_state.get(
                "current_index",
                0,
            )
            or 0
        )

        if (
            steps
            and current_index < len(steps)
        ):
            current_step = steps[current_index]

            if (
                current_step.get("next_action")
                == "request_target"
                and text not in {
                    "next",
                    "continue",
                    "go",
                    "run",
                }
            ):
                target_capture = (
                    self.execution_bridge_service.try_execution_target_capture(
                        session_id=session_id,
                        user_text=user_text,
                    )
                )

                if target_capture:
                    return target_capture

                return self.chat_execution_service.advance(
                    session_id,
                    user_text=user_text,
                )

        target_capture = (
            self.execution_bridge_service.try_execution_target_capture(
                session_id=session_id,
                user_text=user_text,
            )
        )

        if target_capture:
            return target_capture

        mission_command = self._resolve_mission_command(
            user_text=user_text,
            session_id=session_id,
        )


        if self.safe_str(
            user_text
        ).strip().lower() in {
            "stop",
            "cancel",
            "abort",
            "halt",
        }:
            execution_state = (
                self._load_execution_state(
                    session_id
                )
                or {}
            )

            return self.execution_orchestrator_service.process_execution(
                session_id=session_id,
                state=execution_state,
                command="cancel",
            )

        print(
            "DEBUG AFTER RESOLVE",
            mission_command,
            flush=True,
        )

        print(
            "DEBUG STOP RESOLVE RESULT =",
            {
                "user_text": user_text,
                "type": (
                    mission_command.get("type")
                    if isinstance(
                        mission_command,
                        dict,
                    )
                    else None
                ),
                "next_action": (
                    mission_command.get("next_action")
                    if isinstance(
                        mission_command,
                        dict,
                    )
                    else None
                ),
                "continue_request": (
                    mission_command.get(
                        "continue_request"
                    )
                    if isinstance(
                        mission_command,
                        dict,
                    )
                    else None
                ),
            },
            flush=True,
        )

        print(
            "DEBUG MISSION COMMAND RESULT =",
            mission_command,
            flush=True,
        )

        print(
            "DEBUG BEFORE MISSION RESULT SESSION=",
            repr(session_id),
            flush=True,
        )

        mission_result = (
            self._handle_mission_command_result(
                mission_command=mission_command,
                session_id=session_id,
            )
        )

        if mission_result is not None:
            return mission_result

        current_execution = (
            self._load_execution_state(
                session_id
            )
            or {}
        )

        if (
            current_execution.get("waiting")
            and current_execution.get("steps")
        ):
            current_index = int(
                current_execution.get(
                    "current_index",
                    0,
                )
                or 0
            )

            steps = current_execution.get(
                "steps",
                [],
            )

            if (
                current_index < len(steps)
                and steps[current_index].get(
                    "next_action"
                )
                == "request_target"
            ):
                return self.chat_execution_service.advance(
                    session_id=session_id,
                    user_text=user_text,
                )

        if text in {
            "apply_auto_fix",
            "apply auto fix",
            "auto fix",
            "autofix",
        }:
            return self._apply_pending_fix(session_id)

        command = None

        if text in {
            "approve",
            "approved",
            "approve step",
            "approve execution",
        }:
            command = "approve"

        elif text in {
            "deny",
            "denied",
            "deny step",
            "deny execution",
            "reject",
        }:
            command = "deny"

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
            "auto",
            "auto mode",
            "autopilot",
        }:
            command = "run_all"

        elif text in {
            "k",
            "kk",
            "next",
            "nex",
            "continue",
            "continue on",
            "keep going",
            "go",
            "resume",
            "run next",
            "next step",
            "what next",
            "what now",
            "run_step",
            "run step",
        }:
            command = "run_step"

        elif text in {
            "stop",
            "cancel",
        }:
            command = "cancel"

        else:
            current_execution = (
                self._load_execution_state(
                    session_id
                )
                or {}
            )

            if (
                current_execution.get("waiting")
                and current_execution.get("steps")
            ):
                current_index = int(
                    current_execution.get(
                        "current_index",
                        0,
                    )
                    or 0
                )

                steps = current_execution.get(
                    "steps",
                    [],
                )

                if (
                    current_index < len(steps)
                    and steps[current_index].get(
                        "next_action"
                    )
                    == "request_target"
                ):
                    return self.chat_execution_service.advance(
                        session_id=session_id,
                        user_text=user_text,
                    )

            return None

        execution_state = (
            self._load_execution_state(session_id)
            or {}
        )

        if not isinstance(execution_state, dict):
            execution_state = {}

        existing_state = (
            self.active_execution_cache.get(session_id)
            or {}
        )

        if not isinstance(existing_state, dict):
            existing_state = {}

        execution_state = {
            **existing_state,
            **execution_state,
        }

        if not execution_state.get("steps") and existing_state.get("steps"):
            execution_state["steps"] = existing_state["steps"]

        if not execution_state.get("goal") and existing_state.get("goal"):
            execution_state["goal"] = existing_state["goal"]

        if (
            execution_state.get("current_index") is None
            and existing_state.get("current_index") is not None
        ):
            execution_state["current_index"] = (
                existing_state["current_index"]
            )

        if (
            command == "run_step"
            and self.safe_str(
                execution_state.get("status")
            ).strip().lower()
            == "failed"
        ):
            command = "retry_failed"

        execution_state["lock"] = False
        execution_state["_execution_processing"] = False
        execution_state["command"] = command

        print(
            "DEBUG EXEC CONTROL BEFORE ORCHESTRATOR",
            {
                "session_id": session_id,
                "goal": execution_state.get("goal"),
                "status": execution_state.get("status"),
                "current_index": execution_state.get("current_index"),
                "command": command,
            },
        )

        if (
            "current_index" not in execution_state
            and "current_step_index" in execution_state
        ):
            execution_state["current_index"] = execution_state.get(
                "current_step_index",
                0,
            )

        return self.execution_orchestrator_service.process_execution(
            session_id=session_id,
            state=execution_state,
            command=command,
        )

    def _looks_like_live_store_hours_request(self, user_text: str) -> bool:
        """
        LIVE_STORE_HOURS_ROUTE_V1

        Detect questions that require current business/store-hour lookup.
        These must go through web search instead of normal memory/chat.
        """
        text = (user_text or "").strip().lower()
        if not text:
            return False

        hours_terms = (
            "open now",
            "open right now",
            "are they open",
            "is it open",
            "still open",
            "closed now",
            "closing time",
            "what time do they close",
            "what time does it close",
            "what time are they open",
            "store hours",
            "business hours",
            "hours today",
            "holiday hours",
            "open today",
            "close today",
            "closed today",
        )

        business_terms = (
            "tim hortons",
            "tims",
            "starbucks",
            "mcdonald",
            "wendy",
            "subway",
            "restaurant",
            "coffee shop",
            "cafe",
            "store",
            "shop",
            "pharmacy",
            "clinic",
            "bank",
            "mall",
            "gas station",
            "costco",
            "walmart",
            "superstore",
            "save on foods",
            "safeway",
            "shoppers",
        )

        location_terms = (
            " near me",
            " vancouver",
            " bc",
            " british columbia",
            " keefer",
            " street",
            " st ",
            " ave",
            " avenue",
            " road",
            " rd ",
            " drive",
            " dr ",
            " downtown",
            " chinatown",
            " address",
            " location",
        )

        padded = f" {text} "
        has_hours_intent = (
            any(term in text for term in hours_terms)
            or " hours" in text
            or text.endswith(" hours")
        )
        has_business = any(term in text for term in business_terms)
        has_location = any(term in padded for term in location_terms)

        return has_hours_intent and (has_business or has_location)

    def _rewrite_live_store_hours_query(self, user_text: str, location=None) -> str:
        """
        LIVE_STORE_HOURS_QUERY_V2

        Keep live business-hours searches close to a normal Google-style query.
        Detection/routing can use keywords, but the actual web query should stay simple.
        """
        query = (user_text or "").strip()

        if location and isinstance(location, dict):
            city = location.get("city") or location.get("name") or ""
            region = location.get("region") or location.get("province") or location.get("state") or ""
            extra = f"{city} {region}".strip()
            if extra and extra.lower() not in query.lower():
                query = f"{query} {extra}".strip()

        lowered = query.lower()

        has_hours_word = any(
            term in lowered
            for term in (
                "hours",
                "open",
                "closed",
                "closing",
                "close",
                "open now",
                "right now",
            )
        )

        if not has_hours_word:
            query = f"{query} hours"

        return " ".join(query.split())

    def _normalize_live_store_hours_result(self, result):
        """
        LIVE_STORE_HOURS_FALLBACK_V2

        Cleans generic web-fetch failure text for any business/location hours request.
        Applies to restaurants, stores, banks, clinics, gas stations, malls, etc.
        """
        fallback = (
            "I could not verify live hours for that exact business or location from the current web route. "
            "Check Google Maps, the business's official store locator, or the official website for the most "
            "current open/closed status. For a better check, include the exact address, business name, "
            "or nearby cross street."
        )

        if not isinstance(result, dict):
            return result

        found_text_parts = []

        for key in ("text", "answer", "content"):
            value = result.get(key)
            if value:
                found_text_parts.append(str(value))

        assistant_message = result.get("assistant_message")
        if isinstance(assistant_message, dict):
            for key in ("text", "content", "answer"):
                value = assistant_message.get(key)
                if value:
                    found_text_parts.append(str(value))

        combined_text = "\n".join(found_text_parts)

        combined_lower = combined_text.lower()

        bad_web_fallback = (
            "no verified fresh web results were retrieved" in combined_lower
            or "try a more specific query with a team, person, date, or source" in combined_lower
            or "use the web route to verify" in combined_lower
            or "can't directly browse from here" in combined_lower
            or "cannot directly browse from here" in combined_lower
            or "i canÃ¢â‚¬â„¢t directly browse from here" in combined_lower
            or "i can't directly browse from here" in combined_lower
            or "fastest exact query is" in combined_lower
            or "paste the listing here" in combined_lower
            or "likely location:" in combined_lower
        )

        if not bad_web_fallback:
            return result

        result["text"] = fallback
        result["answer"] = fallback
        result["content"] = fallback
        result["route"] = "live_store_hours"
        result["verified"] = False

        if isinstance(assistant_message, dict):
            assistant_message["text"] = fallback
            assistant_message["content"] = fallback
            assistant_message["answer"] = fallback

        session = result.get("session")
        if isinstance(session, dict):
            working_state = session.get("working_state")
            if isinstance(working_state, dict):
                working_state["last_assistant_message"] = fallback

        return result

    def _handle_live_store_hours_request(self, user_text: str, session_id: str = "", attachments=None, location=None):
        """
        Route live business/location-hours questions through Nova's existing web pipeline.
        """
        web_query = self._rewrite_live_store_hours_query(user_text, location=location)

        decision = {
            "route": "web_search",
            "web_intent": "live_store_hours",
            "reason": "User asked for current business open/closed/store-hours information.",
        }

        handler = getattr(self, "_handle_web_request", None)
        if callable(handler):
            attempts = (
                lambda: handler(web_query, session_id=session_id, attachments=attachments, decision=decision),
                lambda: handler(web_query, session_id=session_id, attachments=attachments),
                lambda: handler(web_query, session_id),
                lambda: handler(web_query),
            )

            for attempt in attempts:
                try:
                    result = attempt()
                    return self._normalize_live_store_hours_result(result)
                except TypeError:
                    continue

        fetcher = getattr(self, "_execute_web_fetch", None)
        if callable(fetcher):
            attempts = (
                lambda: fetcher(web_query, session_id=session_id, attachments=attachments, decision=decision),
                lambda: fetcher(web_query, session_id=session_id, attachments=attachments),
                lambda: fetcher(web_query, session_id),
                lambda: fetcher(web_query),
            )

            for attempt in attempts:
                try:
                    result = attempt()
                    return self._normalize_live_store_hours_result(result)
                except TypeError:
                    continue

        return self._normalize_live_store_hours_result({
            "ok": True,
            "text": "No verified fresh web results were retrieved.",
            "answer": "No verified fresh web results were retrieved.",
            "content": "No verified fresh web results were retrieved.",
            "route": "live_store_hours",
            "verified": False,
        })



    def _extract_file_path_from_error(self, error_text: str) -> str:
        text = self.safe_str(error_text)

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
        text = re.sub(r"\s+", " ", self.safe_str(value)).strip()

        if not text:
            return ""

        return text[:limit].strip()

    def _clean_web_text(
        self,
        value: str,
        limit: int = 4000,
    ) -> str:

        text = re.sub(
            r"\s+",
            " ",
            self.safe_str(value),
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

    def _score_memory_for_text(
        self,
        memory_item,
        user_text: str,
    ) -> float:

        user_text = self.safe_str(user_text).strip().lower()

        if not user_text:
            return 0.0

        if isinstance(memory_item, dict):
            text = self.safe_str(memory_item.get("text"))

            kind = self.safe_str(memory_item.get("kind"))

        else:
            text = self.safe_str(memory_item)
            kind = ""

        haystack = (f"{kind} {text}").strip().lower()

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

        all_memory = self._safe_list(self._load_memory())

        if not all_memory:
            return []

        ranked = []

        memory_recall_query = any(
            phrase in str(user_text or "").lower()
            for phrase in [
                "what did i ask you to remember",
                "what did i tell you to remember",
                "show my memories",
                "what memories do you have",
            ]
        )

        for item in items:
            score = self._score_memory_for_text(
                item,
                user_text,
            )

            if memory_recall_query and isinstance(item, dict):
                kind = str(
                    item.get("kind")
                    or item.get("category")
                    or ""
                ).lower()

                text = str(
                    item.get("text")
                    or item.get("content")
                    or ""
                ).lower()

                if (
                    "remember this" in text
                    or "remember that" in text
                    or kind in {
                        "memory",
                        "note",
                        "user_fact",
                    }
                ):
                    score += 50

                if kind in {
                    "preference",
                    "profile",
                    "identity",
                }:
                    score -= 20

            ranked.append((score, item))

        ranked.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        return [item for _, item in ranked[:limit]]

    def _build_memory_recall_text(
        self,
        session_id: str = "",
        user_text: str = "",
        limit: int = 5,
    ) -> str:

        normalized_recall_text = " ".join(str(user_text or "").lower().strip().rstrip("?!.").split())
        project_state_questions = {
            "what is the current project",
        }
            
        if normalized_recall_text in project_state_questions:
            try:
                import json as _nova_project_memory_json_20260701
                from pathlib import Path as _nova_project_memory_path_20260701

                memory_path = _nova_project_memory_path_20260701("data/nova_memory.json")
                memory_data = _nova_project_memory_json_20260701.loads(
                    memory_path.read_text(encoding="utf-8") or "{}"
                )
                memory_items = memory_data.get("memory") or []

                project_items = [
                    item for item in memory_items
                    if isinstance(item, dict)
                    and (
                        str(item.get("kind") or "").strip().lower() == "project_state"
                        or str(item.get("category") or "").strip().lower() == "project_state"
                    )
                ]

                project_items.sort(
                    key=lambda item: (
                        0 if bool(item.get("pinned")) else 1,
                        -float(item.get("weight") or 0.0),
                        str(item.get("updated_at") or ""),
                    )
                )

                for item in project_items:
                    project_text = str(item.get("text") or item.get("content") or "").strip()
                    if project_text:
                        return project_text

            except Exception as _nova_project_memory_error_20260701:
                try:
                    print("[NOVA_PROJECT_STATE_MEMORY_RECALL_20260701] failed:", _nova_project_memory_error_20260701)
                except Exception:
                    pass

        items = []

        try:
            if hasattr(self, "memory") and self.memory and hasattr(self.memory, "all"):
                items = self.memory.all() or []
                print("[MEMORY RECALL DEBUG]", items[-5:])

        except Exception:
            items = []

        if not items:
            return "I do not have any saved memory yet."

        ranked = []

        memory_recall_query = any(
            phrase in str(user_text or "").lower()
            for phrase in [
                "what did i ask you to remember",
                "what did i tell you to remember",
                "show my memories",
                "what memories do you have",
            ]
        )

        for item in items:
            score = self._score_memory_for_text(
                item,
                user_text,
            )

            if memory_recall_query and isinstance(item, dict):
                kind = str(
                    item.get("kind")
                    or item.get("category")
                    or ""
                ).lower()

                text = str(
                    item.get("text")
                    or item.get("content")
                    or ""
                ).lower()

                if kind in {
                    "memory",
                    "note",
                    "user_fact",
                }:
                    score += 50

                if "remember this" in text or "remember that" in text:
                    score += 100

                if kind in {
                    "preference",
                    "profile",
                    "identity",
                }:
                    score -= 30

            ranked.append((score, item))

        ranked.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        best = [item for score, item in ranked if score > 0][:limit]

        chosen = best if best else items[:limit]

        lines = []

        for item in chosen:

            if not isinstance(item, dict):
                text = self.safe_str(item).strip()

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

            text = self.safe_str(item.get("text")).strip()

            kind = self.safe_str(item.get("kind")).strip()

            item_session_id = self.safe_str(item.get("session_id")).strip()

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

        return (
            "I remember these saved items:\n"
            + "\n".join(lines)
        )

    def _text_has_placeholder_debug_content(
        self,
        text: str,
    ) -> bool:

        text = self.safe_str(text).strip().lower()

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

    def _has_real_debug_context(
        self,
        user_text: str,
        execution: dict,
        attachments=None,
    ) -> bool:

        attachments = attachments or []
        text = self.safe_str(user_text)
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

        return "apply" in self.safe_str(step_title).lower()

    def _step_requires_verification(
        self,
        step_title: str,
    ) -> bool:

        return "verify" in self.safe_str(step_title).lower()

    def _step_output_indicates_real_change(
        self,
        step_output: str,
    ) -> bool:

        lowered = self.safe_str(step_output).lower()

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

        lowered = self.safe_str(step_output).lower()

        return any(
            x in lowered
            for x in [
                "verified",
                "tested",
                "confirmed",
                "passes",
            ]
        )

    def _execution_status_label(
        self,
        execution,
    ):

        execution = execution or {}

        steps = execution.get("steps") or []

        total = len(steps)

        done = sum(1 for s in steps if (s or {}).get("done"))

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
            title = str((steps[idx] or {}).get("title") or "").strip()

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

        execution = self._normalize_execution_state(dict(execution))

        goal = str(execution.get("goal") or "").strip()

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

        done = sum(1 for s in steps if (s or {}).get("status") == "done")

        current_index = int(
            execution.get(
                "current_index",
                0,
            )
            or 0
        )

        if 0 <= current_index < total:

            current_step = (
                str((steps[current_index] or {}).get("title") or "").strip()
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

        assistant_text = "\n".join(lines)

        assistant_text = (
            assistant_text.replace("AUTO_EXECUTE", "").replace("TEST_FAIL", "").strip()
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

    def _build_continuity_context(
        self,
        session=None,
        limit: int = 14,
        user_text: str = "",
    ):
        session = session or {}

        continuity_query_words = [
            "checkpoint",
            "blocker",
            "what are we working on",
            "working on right now",
            "current state",
            "project status",
            "latest status",
            "next move",
            "where are we",
            "resume",
            "continue",
        ]

        is_continuity_query = any(
            word in str(user_text).lower()
            for word in continuity_query_words
        )

        if not is_continuity_query:
            return ""

        messages = (
            session.get("messages")
            if isinstance(session, dict)
            else []
        )

    def _compose_model_messages(
        self,
        user_text,
        session=None,
        decision=None,
        memory_context=None,
    ):
        session = session or {}
        memory_context = self.safe_str(
            memory_context
        ).strip()

        system_prompt = self._build_system_prompt(
            decision=decision,
            memory_items=memory_items,
        )

        continuity_context = self._build_continuity_context(
            session=session,
            user_text=user_text,
        )

        execution_text = ""

        try:
            latest = self._find_latest_execution_artifact(
                session_id=session.get("id", "")
            )

            if latest:
                execution = latest.get("execution") or {}

                if execution:
                    execution_text = self._render_execution(
                        execution
                    )

        except Exception:
            execution_text = ""

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

        if continuity_context:
            messages.append(
                {
                    "role": "system",
                    "content": continuity_context,
                }
            )

        if execution_text:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        f"Current execution:\n"
                        f"{execution_text}"
                    ),
                }
            )

        if memory_context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Memory about the user "
                        "(use this as ground truth when relevant):\n"
                        f"{memory_context}"
                    ),
                }
            )

        messages.append(
            {
                "role": "user",
                "content": user_text or "",
            }
        )

        return messages

    def _maybe_update_working_state(self, session_id: str, user_text: str):
        session_id = self.safe_str(session_id).strip()
        if not session_id:
            return {}

        current_state = self._get_working_state(session_id)
        updates = self._extract_working_state_updates(user_text, current_state)

        if not isinstance(updates, dict) or not updates:
            return current_state

        return self._update_working_state(session_id, updates)


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
        raw = self.safe_str(text).strip()
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

        kind = self.safe_str(kind).lower().strip()
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

        weak_memory_patterns = (
            "temporary",
            " temp",
            "test",
            " trace",
            "debug",
            "debugging",
            "experiment",
            "testing",
            "sample",
        )

        if any(
            pattern in lowered
            for pattern in weak_memory_patterns
        ):
            return False

        if kind in {
            "profile",
            "project",
            "goal",
            "note",
            "style",
        }:
            return True

        if kind == "user_fact":
            strong_fact_signals = (
                "my name is",
                "call me",
                "i am ",
                "i'm ",
                "i work on",
                "i'm working on",
                "i am working on",
                "i live in",
            )

            if any(
                signal in lowered
                for signal in strong_fact_signals
            ):
                return True

            return False

        if kind == "preference":
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
            "i like ",
            "i love ",
            "i enjoy ",
            "i dislike ",
            "i hate ",
            "user preference",
            "remember this",
            "remember that",
            "from now on",
            "going forward",
            "favorite color",
            "favourite color",
            "favorite movie",
            "favourite movie",
            "favorite drink",
            "favourite drink",
            "favorite animal",
            "favourite animal",
        )

        # NOVA_PROJECT_BRAIN_MEMORY_CONCEPT_BYPASS_20260714
        # Architecture questions about memory are not memory-save requests.
        memory_concept_questions = (
            "what nova remembers",
            "what nova is actively doing",
            "separate what",
            "separate memory",
            "memory from execution",
            "remembered from active",
        )

        if any(
            marker in lowered
            for marker in memory_concept_questions
        ):
            return False


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
                        k: v for k, v in kwargs.items() if k not in {"route"}
                    }

                    try:
                        return method(*args, **filtered_kwargs)

                    except TypeError:
                        continue

        return None


    # ==============================
    # DECISION CONTRACT
    # ==============================

    def _looks_like_url(self, text: str) -> bool:
        t = self.safe_str(text).lower()
        if not t:
            return False
        if "http://" in t or "https://" in t:
            return True
        return bool(re.search(r"\bwww\.[^\s]+\.[^\s]+\b", t))

    def _extract_first_url(self, text: str) -> str:
        t = self.safe_str(text)
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
        t = self.safe_str(text).lower()
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
        t = self.safe_str(text).lower()
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

    def _decide(
        self,
        user_text: str,
        attachments=None,
        session_id: str = "",
    ) -> dict:

        result = self._decide_route(
            user_text=user_text,
            attachments=attachments,
            session_id=session_id,
        )

        print(
            "DECIDE RESULT =",
            result,
        )

        return result

    def _looks_like_execution(
        self,
        user_text: str,
        decision: dict | None = None,
    ) -> bool:
        text = str(user_text or "").strip().lower()

        if not text:
            return False

        execution_markers = [
            "auto-plan",
            "start execution",
            "start mission",
            "run plan",
            "execute plan",
            "execute steps",
            "run steps",
            "begin task",
        ]

        if any(x in text for x in execution_markers):
            return True

        # Planning requests should create execution state.
        if decision and decision.get("route") in {
            "execution",
            "execution_plan",
            "execution_command",
        }:
            return True

        if decision and decision.get("intent") in {
            "start_execution",
            "execute_plan",
            "execution_command",
        }:
            return True

        return False

    def _execution_step_titles_for_goal(self, goal: str) -> list[str]:
        lowered = str(goal or "").lower()

        if "hosting" in lowered:
            return [
                "Research hosting requirements",
                "Compare available hosting solutions",
                "Select recommended hosting approach",
            ]

        if (
            "plan" in lowered
            or "project" in lowered
            or "next steps" in lowered
        ):
            return [
                "Analyze project goal and requirements",
                "Create project phases and milestones",
                "Define tasks, priorities, and timeline",
                "Review risks and success criteria",
            ]

        if any(
            word in lowered
            for word in (
                "analyze",
                "audit",
                "review",
                "inspect",
            )
        ):
            return [
                "Analyze provided information",
                "Identify important findings",
                "Create recommendations",
            ]

        return [
            "Understand user objective",
            "Determine required actions",
            "Provide completed response",
        ]

    def _reconcile_execution_state(
        self,
        session_id: str,
        working_state=None,
        execution_state=None,
    ) -> dict:
        working_state = working_state if isinstance(working_state, dict) else {}
        execution_state = execution_state if isinstance(execution_state, dict) else {}

        active_execution = self._get_session_meta(session_id, "active_execution") or {}

        active_status = self.safe_str(active_execution.get("status")).strip().lower()
        execution_status = self.safe_str(execution_state.get("status")).strip().lower()

        active_complete = (
            active_status in {"complete", "completed"}
            or active_execution.get("complete") is True
        )

        execution_complete = (
            execution_status in {"complete", "completed"}
            or execution_state.get("complete") is True
        )

        if active_complete or execution_complete:
            execution_state = self.execution_mutation_service.mark_complete(
                execution_state,
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
        latest_execution = (
            latest_meta.get("execution") if isinstance(latest_meta, dict) else {}
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

    def _persist_execution_artifact(
        self,
        session_id: str,
        execution: dict | None,
    ) -> None:
        session_id = self.safe_str(session_id).strip()

        if not session_id:
            return

        if not isinstance(execution, dict):
            execution = {}

        execution = self._normalize_execution_state(
            dict(execution)
        )

        execution["session_id"] = session_id
        execution["active"] = True

        if self.execution_state_service:
            self.execution_state_service.persist_execution(
                session_id,
                execution,
            )

    def _find_latest_execution_artifact(self, session_id: str = ""):
        session_id = self.safe_str(session_id)

        try:
            artifacts = []

            if hasattr(self, "artifact_service") and hasattr(
                self.artifact_service,
                "list_all",
            ):
                artifacts = self.artifact_service.list_all()

            elif hasattr(self, "artifacts") and hasattr(
                self.artifacts,
                "list_all",
            ):
                artifacts = self.artifacts.list_all()

            artifacts = artifacts or []

            exec_debug(
                "ALL ARTIFACTS =",
                artifacts,
            )

            matches = []

            for a in artifacts:
                a = a or {}

                if (
                    session_id
                    and self.safe_str(a.get("session_id")) != session_id
                ):
                    continue

                execution = (
                    a.get("execution")
                    or ((a.get("meta") or {}).get("execution"))
                    or {}
                )

                if execution:
                    exec_debug(
                        "MATCHED EXECUTION ARTIFACT =",
                        a,
                    )
                    matches.append(a)

            active_matches = []

            for artifact in matches:
                execution = (
                    artifact.get("execution")
                    or ((artifact.get("meta") or {}).get("execution"))
                    or {}
                )

                status = self.safe_str(
                    execution.get("status")
                ).lower().strip()

                is_complete = (
                    execution.get("complete") is True
                    or status in {
                        "complete",
                        "completed",
                        "done",
                    }
                )

                has_steps = bool(
                    execution.get("steps")
                )

                if has_steps and not is_complete:
                    active_matches.append(
                        artifact
                    )

            selected = (
                active_matches
                if active_matches
                else matches
            )

            selected.sort(
                key=lambda x: self.safe_str(
                    x.get("created_at")
                ),
                reverse=True,
            )

            latest = (
                selected[0]
                if selected
                else None
            )

            exec_debug(
                "FINAL LATEST =",
                latest,
            )

            return latest

        except Exception as e:
            exec_debug(
                "FIND EXECUTION FAILED =",
                e,
            )
            return None
    def _attach_execution(
        self, payload, user_text, assistant_msg, decision, session_id=""
    ):
        execution = self._build_execution(
            user_text=user_text,
            assistant_text=str(assistant_msg.get("text") or ""),
            decision=decision,
        )

        if not execution:
            return payload

        steps = (
            execution.get("steps") if isinstance(execution.get("steps"), list) else []
        )
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
        text = self.safe_str(user_text).strip().lower()
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
                        title = str(
                            raw.get("title")
                            or raw.get("text")
                            or raw.get("name")
                            or ""
                        ).strip()
                    else:
                        title = str(raw).strip()

                    if not title:
                        continue

                    clean_steps.append(
                        {
                            "title": title,
                            "action": (
                                raw.get("action")
                                if isinstance(raw, dict)
                                else None
                            ),
                            "target_file": (
                                raw.get("target_file")
                                if isinstance(raw, dict)
                                else ""
                            ),
                            "target_function": (
                                raw.get("target_function")
                                if isinstance(raw, dict)
                                else ""
                            ),
                            "mutation_mode": (
                                raw.get("mutation_mode")
                                if isinstance(raw, dict)
                                else ""
                            ),
                            "status": (
                                raw.get("status", "pending")
                                if isinstance(raw, dict)
                                else "pending"
                            ),
                            "result": (
                                raw.get("result", "")
                                if isinstance(raw, dict)
                                else ""
                            ),
                            "error": (
                                raw.get("error")
                                if isinstance(raw, dict)
                                else None
                            ),
                        }
                    )

                step_count = len(clean_steps)

                if step_count == 0:
                    execution["steps"] = []
                    execution["current_step_index"] = 0
                    execution["progress"] = 0
                    execution["current_step"] = (
                        "complete"
                        if execution.get("status") == "complete"
                        else ""
                    )
                    execution["status"] = "complete"
                    execution["complete"] = True
                    return execution

                try:
                    current_index = int(
                        execution.get(
                            "current_step_index",
                            execution.get("current_index", 0),
                        )
                        or 0
                    )
                except Exception:
                    current_index = 0

                if current_index < 0:
                    current_index = 0

                if current_index > step_count:
                    current_index = step_count

                status = str(
                    execution.get("status") or "running"
                ).strip().lower()

                if status not in {
                    "running",
                    "complete",
                    "blocked",
                    "waiting_approval",
                }:
                    status = "running"

                if status == "complete" or current_index >= step_count:
                    current_index = step_count

                    for step in clean_steps:
                        step["status"] = "done"

                    progress = step_count
                    current_step = "complete"
                    status = "complete"
                    execution["complete"] = True

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
                    execution["complete"] = False

                execution["steps"] = clean_steps
                execution["current_step_index"] = current_index
                execution["current_index"] = current_index
                execution["progress"] = progress
                execution["current_step"] = current_step
                execution["status"] = status

                return execution

    def _looks_like_auto_execution_request(self, user_text: str) -> bool:
        text = self.safe_str(user_text).strip().lower()

        return text in {
            "run all",
            "auto execute",
            "finish the plan",
            "do it all",
            "complete it",
        }

    def _looks_like_plan_request(self, user_text: str) -> bool:
        text = self.safe_str(user_text).strip().lower()
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


    def _sync_execution_state(
        self,
        execution=None,
        current_index=None,
        status=None,
        current_step=None,
        progress=None,
        waiting=None,
    ):
        execution = execution if isinstance(execution, dict) else {}

        original_steps = execution.get("steps")

        execution = self._normalize_execution_state(execution)

        if isinstance(original_steps, list):
            execution["steps"] = original_steps

        steps = (
            execution.get("steps") if isinstance(execution.get("steps"), list) else []
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

            execution["current_index"] = current_index

            execution["current_step_index"] = current_index

        else:
            try:
                current_index = int(execution.get("current_index", 0) or 0)
            except Exception:
                current_index = 0

            current_index = max(
                0,
                current_index,
            )

        if status is not None:
            execution["status"] = (
                self.safe_str(status) or execution.get("status") or "idle"
            )

        if current_step is not None:
            execution["current_step"] = current_step

            execution["current_step_title"] = current_step

        elif (
            steps
            and current_index < len(steps)
            and isinstance(steps[current_index], dict)
        ):
            execution["current_step"] = steps[current_index].get("title", "")

            execution["current_step_title"] = steps[current_index].get("title", "")

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
            execution["waiting"] = bool(waiting)

        execution["lock"] = bool(execution.get("lock", False))

        execution["complete"] = bool(execution.get("status") == "complete")

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
            artifacts = (
                self._call_first(
                    self.artifacts,
                    [
                        "list_artifacts",
                        "get_artifacts",
                        "get_all",
                        "list",
                        "all",
                        "load_artifacts",
                    ],
                )
                or []
            )
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


    def _extract_execution_lines(self, body: str):
        lines = self.safe_str(body).splitlines()
        step_indexes = []
        current_index = -1

        for i, line in enumerate(lines):
            if any(
                x in line
                for x in [
                    "[ ]",
                    "[>]",
                    "[x]",
                    "[X]",
                    "✓",
                    "✔",
                    "→",
                    "➡",
                ]
            ):
                step_indexes.append(i)

            if "[>]" in line:
                current_index = i

        return lines, step_indexes, current_index


    def _persist_message_fallback(self, session_id: str, message: dict) -> None:
        if self.session_service:
            try:
                print(
                    "[PERSISTING MESSAGE]",
                    session_id,
                    message,
                )

                self.session_service.append_message(
                    session_id,
                    message,
                )

            except Exception as e:
                exec_debug(
                    "MESSAGE PERSIST FAILED:",
                    e,
                )

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
            value = self.safe_str(state.get(key)).strip()
            if value:
                lines.append(f"- {label}: {value}")

        if not lines:
            return ""

        return "Working state:\n" + "\n".join(lines)


        # ==============================
        # WORKING STATE (PHASE 3)
        # ==============================

    def _set_working_state(self, session_id: str, state: dict):
        session_id = self.safe_str(session_id).strip()
        if not session_id:
            return {}

        if not isinstance(state, dict):
            state = {}

        clean_state = {
            "active_task": self.safe_str(state.get("active_task")).strip(),
            "current_file": self.safe_str(state.get("current_file")).strip(),
            "current_bug": self.safe_str(state.get("current_bug")).strip(),
            "last_success": self.safe_str(state.get("last_success")).strip(),
            "next_move": self.safe_str(state.get("next_move")).strip(),
            "checkpoint": self.safe_str(state.get("checkpoint")).strip(),
            "updated_at": self.safe_str(state.get("updated_at")).strip(),
        }

        try:
            return self.working_state_service.set_working_state(
                session_id,
                clean_state,
            )

        except Exception as e:
            exec_debug(
                "SET_WORKING_STATE_SERVICE_ERROR:",
                e,
            )

            return clean_state

    def _auto_track_working_state(
        self,
        session_id,
        user_text="",
        assistant_text="",
    ):

        current = self._get_working_state(session_id) or {}

        patch = {}

        lowered = self.safe_str(user_text).lower().strip()

        current_updated_at = self.safe_str(current.get("updated_at")).strip()

        stale_state = False

        if current_updated_at:

            try:
                updated_dt = datetime.fromisoformat(
                    current_updated_at.replace("Z", "+00:00")
                )

                now_dt = datetime.now(updated_dt.tzinfo)

                age_seconds = (now_dt - updated_dt).total_seconds()

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
            patch["active_task"] = "polish Nova landing page and product positioning"

            patch["checkpoint"] = "landing_page_work"

            patch["next_move"] = "tighten product messaging and demos"

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

            if execution_state.get("current_index", 0) < len(
                execution_state.get("steps") or []
            ):

                patch["active_task"] = (
                    "continue Nova backend intelligence stabilization"
                )

                if not patch.get("checkpoint"):

                    patch["checkpoint"] = "working_state_resume_context"

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

        if lowered.strip() in generic_chat_inputs or not any(
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
                user_text.lower().strip().startswith(prefix)
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

                patch["active_task"] = user_text.strip()[:240]

                patch["checkpoint"] = "task_detected"

                patch["next_move"] = "continue task implementation"

        if not patch:
            return self._get_working_state(session_id) or {}

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

        return self._get_working_state(session_id) or {}

    def _replace_working_state(self, session_id: str, new_state: dict):
        session_id = self.safe_str(session_id).strip()

        if not session_id:
            return {}

        if not isinstance(new_state, dict):
            new_state = {}

        from datetime import datetime, timezone

        clean_state = dict(new_state)
        clean_state["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._set_working_state(session_id, clean_state)

        return clean_state


    def _finalize_execution_state(self, execution_state: dict | None = None) -> dict:
        return self.execution_mutation_service.reset(
            execution_state,
        )
    def _reset_execution_state(self, session_id: str):
        previous_state = self._get_working_state(session_id) or {}

        last_success = self.safe_str(previous_state.get("last_success")).strip()

        checkpoint = self.safe_str(previous_state.get("checkpoint")).strip()

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
            self.session_service.reset_execution_session(
                session_id,
                last_success,
            )

        except Exception as e:
            exec_debug(
                "RESET EXECUTION SESSION CLEAR FAILED:",
                e,
            )

    def _extract_working_state_updates(
        self, user_text: str, current_state: dict | None = None
    ) -> dict:
        text = self.safe_str(user_text).strip()

        if not text:
            return {}

        current_state = (
            current_state
            if isinstance(current_state, dict)
            else {}
        )

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
            value = self.safe_str(value).strip()
            value = value.strip(
                "+ ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â\r\n-:;,.\""
            )
            return value

        def _set_if_present(field_name: str, value: str):
            value = _clean_value(value)
            if value:
                updates[field_name] = value

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

        # file path extraction
        if "current_file" not in updates:
            path_match = re.search(
                r"([A-Za-z]:\\[^\r\n\"'<>|?*]+(?:\.[A-Za-z0-9_]+)?)",
                text,
            )

            if path_match:
                _set_if_present(
                    "current_file",
                    path_match.group(1),
                )

        # remove values that are unchanged
        deduped = {}

        for key, value in updates.items():
            existing = self.safe_str(
                current_state.get(key)
            ).strip()

            if (
                self.safe_str(value).strip()
                and self.safe_str(value).strip() != existing
            ):
                deduped[key] = value

            return deduped

        def c(x):
            return x if x else " "

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

    def _build_mission_state(
        self,
        working_state=None,
        execution_state=None,
    ) -> dict:
        working_state = working_state if isinstance(working_state, dict) else {}
        execution_state = execution_state if isinstance(execution_state, dict) else {}

        active_task = self.safe_str(working_state.get("active_task")).strip()
        current_file = self.safe_str(working_state.get("current_file")).strip()
        current_bug = self.safe_str(working_state.get("current_bug")).strip()
        last_success = self.safe_str(working_state.get("last_success")).strip()
        next_move = self.safe_str(working_state.get("next_move")).strip()
        checkpoint = self.safe_str(working_state.get("checkpoint")).strip()

        execution_status = self.safe_str(execution_state.get("status")).strip()
        execution_goal = self.safe_str(execution_state.get("goal")).strip()

        invalid_execution_goal = "respond normally" in execution_goal.lower()

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
            priorities.append(
                "Execution is complete. Await a new mission instead of retrying stale state."
            )

        elif "retry_failed" in next_move:
            blockers.append("Execution recovery is still leaking retry state.")
            priorities.append("Inspect failed execution steps before retry logic runs.")

        if "execution_cycle_complete" in checkpoint:
            priorities.append(
                "Convert raw execution checkpoints into mission-aware summaries."
            )

        if "execution_complete" in last_success:
            priorities.append(
                "Lock completed execution state so it does not resurrect as running."
            )

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

        mission = self.safe_str(mission).strip()

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

        mission = self.safe_str(mission_state.get("mission")).strip()
        recommended_next_move = self.safe_str(
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
                item = self.safe_str(item).strip()
                if item:
                    lines.append(f"- {item}")

        if blockers:
            lines.append("")
            lines.append("Blockers:")
            for item in blockers[:5]:
                item = self.safe_str(item).strip()
                if item:
                    lines.append(f"- {item}")

        return "\n".join(lines).strip()

    def _run_execution_next_move(
        self, active_task: str, next_move: str, session_id: str
    ) -> str:
        active_task = self.safe_str(active_task).strip()
        next_move = self.safe_str(next_move).strip()
        session_id = self.safe_str(session_id).strip() or "default"

        combined_text = f"{next_move} {active_task}".strip().lower()

        move_type = "plan"

        if (
            "build execution loop" in combined_text
            or "build_execution_loop" in combined_text
        ):
            move_type = "plan"
        elif (
            "verify execution loop" in combined_text
            or "verify_execution_loop" in combined_text
        ):
            move_type = "verify_execution_loop"
        elif (
            "persist execution result" in combined_text
            or "persist_execution_result" in combined_text
        ):
            move_type = "persist_execution_result"
        elif (
            "review execution result" in combined_text
            or "review_execution_result" in combined_text
        ):
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
                    elif current_next in {
                        "verify execution loop",
                        "verify_execution_loop",
                    }:
                        next_step_text = "persist execution result"
                    elif current_next in {
                        "persist execution result",
                        "persist_execution_result",
                    }:
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




    def _record_execution_history(
        self,
        session_id: str,
        event_type: str,
        details: dict | None = None,
    ) -> None:
        session_id = self.safe_str(session_id).strip()
        event_type = self.safe_str(event_type).strip() or "execution_event"
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

            existing = str(mem.get("content") or mem.get("text") or "").strip()

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

    def _build_memory_context_for_chat(self, user_text="", decision=None, session_id=""):
        decision = decision if isinstance(decision, dict) else {}

        if decision.get("use_memory") is False:
            return ""

        memory_limit = int(
            decision.get("memory_limit")
            or getattr(self, "memory_limit", 6)
            or 6
        )
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

                    kind = self.safe_str(
                        item.get("kind") or "memory"
                    ).strip()

                    source = self.safe_str(
                        item.get("source") or ""
                    ).strip()

                    text = self.safe_str(
                        item.get("text")
                        or item.get("content")
                        or ""
                    ).strip()

                    if not text:
                        continue

                    label = kind

                    if source:
                        label = f"{kind} / {source}"

                    lines.append(
                        f"- {label}: {text[:1000]}"
                    )

        except Exception as e:
            exec_debug(
                "BUILD_RANKED_MEMORY_CONTEXT_FAILED:",
                e,
            )

        try:
            session = (
                self._get_session_payload(session_id)
                if session_id
                else {}
            )

            messages = (
                session.get("messages", [])
                if isinstance(session, dict)
                else []
            )

            if isinstance(messages, list) and messages:
                recent = messages[-8:]

                lines.append(
                    "\n[RECENT SESSION CONTEXT]"
                )

                for msg in recent:
                    if not isinstance(msg, dict):
                        continue

                    role = self.safe_str(
                        msg.get("role") or ""
                    ).strip()

                    text = self.safe_str(
                        msg.get("text")
                        or msg.get("content")
                        or msg.get("message")
                        or ""
                    ).strip()

                    if role and text:
                        lines.append(
                            f"{role}: {text[:800]}"
                        )

        except Exception as e:
            exec_debug(
                "BUILD_RECENT_SESSION_CONTEXT_FAILED:",
                e,
            )

        return "\n".join(lines).strip()

    def _format_memory_context(self, memory_items=None) -> str:
        memory_items = memory_items or []
        lines = []

        for item in memory_items:
            if isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("content")
                    or item.get("value")
                    or item.get("memory")
                    or ""
                )
            else:
                text = str(item or "")

            text = str(text).strip()

            if text:
                lines.append(f"- {text}")

        return "\n".join(lines).strip()


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
        print(
            "[MEMORY DEBUG INPUT]",
            len(memories),
            memories[:3],
        )
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

        priority_terms = [term for term in priority_terms if term]

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

        ranked = self.memory_context_service.rank_memory_items(
            memories=memories,
            user_text=user_text,
            limit=limit,
            priority_terms=priority_terms,
            is_execution_chat=is_execution_chat,
            casual_query=casual_query,
            operational_query=operational_query,
            has_real_state=has_real_state,

        )
        try:

            should_debug_memory_dominance = any(
                (
                    isinstance(item, dict)
                    and isinstance(item.get("memory"), dict)
                    and self.safe_str(item.get("memory", {}).get("category")).lower()
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
                            "content": str(item.get("content") or "")[:120],
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

        selected_memory = [
            item["memory"]
            for item in top
        ]

        self._last_used_memory_items = selected_memory

        return selected_memory


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
        artifact_text = f'Generated image: {clean_prompt}'

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
                "analysis_text": (
                    f"This image was generated from the prompt: {clean_prompt}"
                    if clean_prompt
                    else artifact_text
                ),
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
            image_bytes = b""
            filename = (
                f"generated_{uuid.uuid4().hex}.png"
            )

            from nova_backend.services.model_gateway_service import (
                images_generate_create,
            )

            result = images_generate_create(
                model=self.image_model,
                prompt=prompt,
                size=self.image_size,
            )

            first = result.data[0] if getattr(result, "data", None) else None
            image_b64 = getattr(first, "b64_json", None) if first else None
            remote_image_url = getattr(first, "url", None) if first else None

            if remote_image_url:
                image_url = remote_image_url
            else:
                if not image_b64:
                    raise ValueError("Image API returned no image data")

                image_bytes = base64.b64decode(image_b64)
                save_path = os.path.join(
                    self.uploads_dir,
                    filename,
                )

                with open(save_path, "wb") as f:
                    f.write(image_bytes)

                try:
                    owner_id = get_current_user_id()
                    if owner_id:
                        UploadOwnershipService().register_upload(
                            filename,
                            owner_id,
                        )
                except Exception:
                    pass

                image_url = f"/api/uploads/{filename}"

            saved_artifact = None

            try:
                saved_artifact = self.artifacts.create(
                    {
                        "kind": "image",
                        "type": "image_generation",
                        "title": "Generated image",
                        "body": prompt,
                        "summary": (
                            f"Generated image: {prompt}"
                        ),
                        "preview": image_url,
                        "session_id": session_id,
                        "source": "generated",
                        "image_url": image_url,
                        "prompt": prompt,
                        "revised_prompt": "",
                        "parent_id": (
                            parent_artifact_id or None
                        ),
                        "viewer": {
                            "type": "image",
                            "image_url": image_url,
                        },
                        "meta": {
                            "image_url": image_url,
                            "prompt": prompt,
                            "generation_mode": (
                                "text_to_image"
                            ),
                            "source_type": source_type,
                        },
                    }
                )
            except Exception as exc:
                exec_debug(
                    "IMAGE ARTIFACT FALLBACK SAVE FAILED:",
                    exc,
                )

            try:
                if (
                    session_id
                    and hasattr(self, "artifact_service")
                    and self.artifact_service
                ):
                    self.artifact_service.sync_artifacts_to_session(session_id)
            except Exception as e:
                exec_debug("FORCED ARTIFACT SYNC FAILED:", e)
            assistant_image_message = {
                "role": "assistant",
                "text": f"Generated image: {prompt}",
                "content": f"Generated image: {prompt}",
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

            refreshed_session = self.sessions.get_session(session_id)

            return {
                "ok": True,
                "skip_rewrite": True,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "assistant_message": {
                    **assistant_image_message,
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
                "session": self._get_session_payload(session_id),
            }


    # NOVA_OPENAI_VISION_ATTACHMENT_ANALYSIS_20260607
    def _nova_describe_image_with_openai_20260607(
        self,
        image_url: str,
        image_name: str = "",
        user_text: str = "",
    ) -> str:
        try:
            import base64
            import mimetypes
            import os
            from pathlib import Path


            raw_url = self.safe_str(image_url).strip()
            raw_name = self.safe_str(image_name).strip()

            if not raw_url:
                return ""

            filename = ""

            if "/api/uploads/" in raw_url:
                filename = raw_url.split("/api/uploads/", 1)[1].split("?", 1)[0].split("#", 1)[0]
            elif raw_url.startswith("uploads/") or raw_url.startswith("uploads\\"):
                filename = Path(raw_url).name
            elif raw_name:
                filename = Path(raw_name).name

            if not filename:
                filename = Path(raw_url).name

            filename = filename.replace("\\", "/").split("/")[-1].strip()

            if not filename:
                return ""

            candidates = [
                Path.cwd() / "uploads" / filename,
                Path.cwd() / "static" / "uploads" / filename,
                Path(__file__).resolve().parents[2] / "uploads" / filename,
                Path(__file__).resolve().parents[1] / "uploads" / filename,
            ]

            image_path = None

            for candidate in candidates:
                try:
                    if candidate.exists() and candidate.is_file():
                        image_path = candidate
                        break
                except Exception:
                    continue

            if image_path is None:
                return ""

            mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"

            with open(image_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode("utf-8")

            data_url = f"data:{mime_type};base64,{encoded}"

            prompt_text = self.safe_str(user_text).strip() or "Describe this image clearly."

            

            response = chat_completions_create(
                nova_username=getattr(self, "username", None) or os.getenv("NOVA_DEFAULT_USERNAME") or "richard",
                nova_session_id=locals().get("session_id") or getattr(getattr(self, "session_service", None), "active_session_id", "") or "",
                model=os.getenv("NOVA_VISION_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Nova's image analysis module. "
                            "Describe the attached image directly and honestly. "
                            "If the image contains readable text, include the important text. "
                            "Do not use web search. Do not mention unrelated news."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt_text,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": data_url,
                                },
                            },
                        ],
                    },
                ],
                temperature=0.2,
                max_tokens=500,
            )

            return self.safe_str(response.choices[0].message.content).strip()

        except Exception as exc:
            print("[NOVA_OPENAI_VISION_ATTACHMENT_ANALYSIS] failed:", exc)
            return ""

    def _handle_attachment(
        self,
        user_text: str,
        attachments=None,
        session_id: str = "",
    ) -> dict:
        result = self._handle_attachment_analysis(
            user_text=user_text,
            attachments=attachments or [],
        )

        if not isinstance(result, dict):
            result = {
                "ok": False,
                "assistant_message": {
                    "role": "assistant",
                    "text": "Attachment analysis returned no result.",
                },
            }

        result.setdefault(
            "session_id",
            session_id,
        )
        result.setdefault(
            "active_session_id",
            session_id,
        )
        result.setdefault(
            "session",
            self._get_session_payload(session_id),
        )

        return result
    def _handle_attachment_analysis(
        self,
        user_text: str,
        attachments: list,
    ) -> dict:
        attachments = attachments or []

        for item in attachments:
            if not isinstance(item, dict):
                continue

            name = self.safe_str(
                item.get("original_filename")
                or item.get("name")
                or item.get("filename")
                or item.get("stored_name")
                or "attachment"
            )

            existing_summary = (
                self.attachment_analysis_service.existing_attachment_text(
                    item
                )
            )

            if (
                existing_summary
                and "PK" not in existing_summary[:20]
            ):
                preview = existing_summary[:6000].strip()

                return {
                    "ok": True,
                    "text": (
                        "Attachment analysis:\n"
                        f"Attachment {name} content:\n"
                        f"{preview}"
                    ),
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "Attachment analysis:\n"
                            f"Attachment {name} content:\n"
                            f"{preview}"
                        ),
                    },
                    "attachment_analysis": True,
                    "vision_used": False,
                    "ocr_used": False,
                    "source_urls": [],
                    "sources": [],
                    "saved_artifact": None,
                }

            att_type = self.safe_str(
                item.get("type")
            ).lower()

            mime_type = self.safe_str(
                item.get("mime_type")
                or item.get("content_type")
            ).lower()

            url = self.safe_str(
                item.get("url")
                or item.get("file_url")
            )

            if url and (
                att_type == "image"
                or mime_type.startswith("image/")
            ):
                vision_text = (
                    self._nova_describe_image_with_openai_20260607(
                        image_url=url,
                        image_name=name,
                        user_text=user_text,
                    )
                )

                if vision_text:
                    return {
                        "ok": True,
                        "text": vision_text,
                        "assistant_message": {
                            "role": "assistant",
                            "text": vision_text,
                        },
                        "attachment_analysis": True,
                        "vision_used": True,
                        "ocr_used": False,
                        "source_urls": [],
                        "sources": [],
                        "saved_artifact": None,
                    }

            text = (
                self.attachment_analysis_service.extracted_file_text(
                    item
                )
            )

            if text:
                preview = text[:6000].strip()

                return {
                    "ok": True,
                    "text": (
                        "Attachment analysis:\n"
                        f"Attachment {name} content:\n"
                        f"{preview}"
                    ),
                    "assistant_message": {
                        "role": "assistant",
                        "text": (
                            "Attachment analysis:\n"
                            f"Attachment {name} content:\n"
                            f"{preview}"
                        ),
                    },
                    "attachment_analysis": True,
                    "vision_used": False,
                    "ocr_used": False,
                    "source_urls": [],
                    "sources": [],
                    "saved_artifact": None,
                }

        fallback = (
            "Attachment received, but Nova could not extract "
            "readable text from it."
        )

        return {
            "ok": True,
            "text": fallback,
            "assistant_message": {
                "role": "assistant",
                "text": fallback,
            },
            "attachment_analysis": True,
            "vision_used": False,
            "ocr_used": False,
            "source_urls": [],
            "sources": [],
            "saved_artifact": None,
        }

    def _build_chat_input(
        self,
        user_text: str,
        decision: dict,
        session_id: str = "",
    ) -> str:
        user_text = self.safe_str(user_text)

        memory_items = self._rank_memory_context(

            user_text=user_text,
            limit=int(
                decision.get("memory_limit")
                or self.memory_limit
            ),
            session_id=session_id,
        )

        self._last_used_memory_items = memory_items

        print(
            "[MEMORY RANK RESULT]",
            len(memory_items),
            memory_items[:3],
        )


        memory_block = self._format_memory_context(
            memory_items[:3]
        )

        sections = []

        if memory_block:
            sections.append(
                "Relevant memory:\n"
                f"{memory_block}"
            )

        execution_state = decision.get(
            "execution_state"
        )

        if isinstance(
            execution_state,
            dict,
        ) and execution_state:

            sections.append(
                "Execution plan:\n"
                f"{execution_state}"
            )

        brain_plan = decision.get(
            "brain_plan"
        )

        if isinstance(
            brain_plan,
            dict,
        ) and brain_plan:

            sections.append(
                "Planner context:\n"
                f"{brain_plan}"
            )

        try:
            session = self._get_session_payload(
                session_id
            )

            continuity_context = (
                self._build_continuity_context(
                    session=session
                )
            )

            print(
                "[CONTINUITY TEST]",
                repr(continuity_context)[:1000],
            )

            if continuity_context:
                sections.append(
                    continuity_context
                )

        except Exception:
            pass

        if not sections:
            return user_text

        return (
            "\n\n".join(sections)
            + "\n\nInstructions:\n"
            + "- Answer clearly and directly.\n"
            + "- Use relevant memory when it helps.\n"
                + "- Do not claim missing context if the answer is already available.\n\n"
                + "User message:\n"
                + user_text
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
            print(
                "DEBUG GENERAL MODEL INPUT =",
                repr(prompt)[:2000],
            )

            response = responses_create(
                model=self.chat_model,
                input=prompt,
            )

            assistant_text = self.response_handler.extract_response_text(
                response
            )

            assistant_text = self._safe_str(
                assistant_text
            ).strip()

            if not assistant_text:
                assistant_text = (
                    "I can help with that. "
                    "Tell me the details you want included."
                )

            writing_placeholders = (
                "[name]",
                "[your name]",
                "[step 1]",
                "[step 2]",
                "[step 3]",
                "[insert",
                "[details]",
                "your name here",
                "recipient name",
            )

            lower_output = assistant_text.lower()

            if any(
                marker in lower_output
                for marker in writing_placeholders
            ):
                assistant_text = (
                    "Subject: Project Update\n\n"
                    "Hi,\n\n"
                    "I wanted to share a quick update on the "
                    "current progress.\n\n"
                    "The latest work has been completed successfully, "
                    "and the next steps are to review the changes, "
                    "confirm everything is working as expected, "
                    "and continue with the remaining improvements.\n\n"
                    "Thanks,\n"
                    "Richard"
                )

            exec_debug(
                "DEBUG WRITING MODEL OUTPUT =",
                repr(assistant_text),
            )

            return assistant_text

        except Exception as e:
            return f"Model error: {e}"


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

        print(
            "DEBUG MEMORY RECALL USER MESSAGE =",
            user_msg,
        )

 

    def _execute_planning(
        self,
        decision: dict,
        user_text: str,
        session_id: str,
        attachments=None,
    ) -> dict:
        print(
            "DEBUG OLD PLANNER REDIRECT ENTERED",
            {
                "user_text": user_text,
                "session_id": session_id,
            },
        )

        try:
            execution_state = self.execution_handler.handle(
                user_text=user_text,
                session_id=session_id,
            )

            print(
                "DEBUG REDIRECT EXECUTION RESULT =",
                execution_state,
            )

            decision["execution_state"] = (
                execution_state or {}
            )

        except Exception as exc:
            print(
                "DEBUG REDIRECT EXECUTION FAILED =",
                repr(exc),
            )

        user_msg = self._build_user_message(
            user_text,
            attachments=attachments or [],
        )

        assistant_text = self._run_chat_model(
            user_text=user_text,
            decision=decision,
            session_id=session_id,
        )

        assistant_msg = self._build_assistant_message(
            text=assistant_text,
            meta={
                "planning": True,
            },
            attachments=[],
        )

        print(
            "DEBUG MEMORY INPUT =",
            {
                "user_text": user_text,
                "decision": decision,
                "memory_type": type(self.memory),
                "memory_methods": [
                    x for x in dir(self.memory)
                    if "memory" in x.lower() or x in ("add", "remember")
                ],
            },
        )


        if memory_result:
            assistant_text = "Saved. I'll remember that."

            assistant_msg = self._build_assistant_message(
                text=assistant_text,
                meta={
                    "planning": True,
                    "memory_saved": True,
                },
                attachments=[],
            )

        print(
            "DEBUG AFTER MEMORY CALL",
            memory_result,
        )

        decision["DEBUG_memory_result"] = memory_result

        print(
            "RETURN MEMORY DEBUG =",
            memory_result,
            flush=True,
        )

        decision["DEBUG_user_text_seen"] = user_text
        decision["DEBUG_memory_type"] = str(type(self.memory))

        print(
            "DEBUG MEMORY GENERAL CHAT RESULT =",
            memory_result,
        )

        print(
            "DEBUG MEMORY OBJECT =",
            type(self.memory),
            getattr(self.memory, "memory_file", None),
        )
        result = self._finalize_response(

            execution_state=decision.get(
                "execution_state"
            ) or {},
            session_id=session_id,
            user_text=user_text,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            decision=decision,
            saved_artifact=None,
        )

        print(
            "[POST FINALIZE DEBUG]",
            result.get("assistant_message", {}).get("meta"),
        )

        return result

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
            created_id = self.safe_str(created.get("id")) or session_id
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

        execution = self._normalize_execution_state(execution or {})

        if execution.get("status") not in {
            "complete",
            "completed",
            "done",
        }:
            execution["status"] = "running"

        execution["waiting"] = False

        steps = execution.get("steps") or []

        current_index = self._execution_current_index(execution)

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

        execution["current_step_title"] = "complete"


        self._save_execution_state(
            session_id,
            execution,
        )

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
                "checkpoint": "execution_complete",
                "last_success": (
                    self.safe_str(execution.get("goal"))
                    or "execution_complete"
                ),
                "execution_status": "complete",
            },
        )

        return {
            "execution": execution,
            "step_output": "No remaining execution step.",
            "saved_artifact": {
                "kind": "execution",
                "title": (
                    self.safe_str(execution.get("goal"))
                    or "Execution"
                ),
                "body": self._render_execution(execution),
                "execution": execution,
                "meta": {
                    "execution": execution,
                    "execution_id": (
                        self.safe_str(execution.get("id"))
                    ),
                    "status": (
                        self.safe_str(execution.get("status"))
                        or "complete"
                    ),
                    "progress": execution.get(
                        "progress",
                        len(steps),
                    ),
                    "current_step": (
                        self.safe_str(
                            execution.get("current_step")
                        )
                        or "complete"
                    ),
                    "goal": self.safe_str(
                        execution.get("goal")
                    ),
                },
            },
        }

        # =========================
        # CURRENT STEP
        # =========================

        current_step = steps[current_index] or {}

        step_title = (
            self.safe_str(current_step.get("title")) or f"Step {current_index + 1}"
        )

        goal = self.safe_str(execution.get("goal"))

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
            (f"Current step " f"({current_index + 1}/{len(steps)}): " f"{step_title}"),
        ]

        if user_text.strip():

            user_prompt_parts.append(f"Latest user input: {user_text}")

        if attachments:

            attachment_lines = []

            for item in attachments:

                if not isinstance(item, dict):
                    continue

                name = self.safe_str(
                    item.get("filename") or item.get("name") or item.get("stored_name")
                )

                url = self.safe_str(item.get("url"))

                mime_type = self.safe_str(item.get("mime_type") or item.get("mime"))

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

                    attachment_lines.append(" - " + " | ".join(bits))

            if attachment_lines:

                user_prompt_parts.append("Attachments:\n" + "\n".join(attachment_lines))

        user_prompt = "\n\n".join(part for part in user_prompt_parts if part)

        step_output = ""

        tool_bundle = {}

        try:

            response = responses_create(
                nova_username=(
                    getattr(self, "username", None)
                    or os.getenv("NOVA_DEFAULT_USERNAME")
                    or "richard"
                ),
                nova_session_id=session_id,
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

            execution["current_step_title"] = "complete"

            execution["complete"] = True

        else:

            next_step = steps[next_index] or {}

            execution = self._sync_execution_state(
                execution=execution,
                current_index=next_index,
                status="running",
                current_step=(
                    self.safe_str(next_step.get("title"))
                    or (f"Step " f"{next_index + 1}")
                ),
                progress=max(
                    0,
                    next_index,
                ),
            )

            next_step_title = self.safe_str(next_step.get("title")) or (
                f"Step " f"{next_index + 1}"
            )

            execution["current_step"] = next_step_title

            execution["current_step_title"] = next_step_title

        artifact_payload = {
            "kind": "execution",
            "title": (goal or "Execution"),
            "body": self._render_execution(execution),
            "execution": execution,
            "meta": {
                "execution": execution,
                "goal": goal,
                "step_index": current_index,
                "step_title": step_title,
                "execution_id": (self.safe_str(execution.get("id"))),
                "tool_bundle": (tool_bundle or {}),
                "status": self.safe_str(execution.get("status")),
                "progress": execution.get(
                    "progress",
                    0,
                ),
                "current_step": (self.safe_str(execution.get("current_step"))),
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

        self._save_execution_state(
            session_id,
            execution,
        )

        return {
            "execution": execution,
            "step_output": step_output,
            "saved_artifact": artifact_payload,
        }

    def _maybe_execute_tool(
        self, step_title: str, user_text: str, execution: dict | None = None
    ) -> dict:
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

        text = self.safe_str(text)

        traceback_paths = re.findall(
            r'File\s+["\']([^"\']+?\.py)["\']',
            text,
            re.IGNORECASE,
        )

        if traceback_paths:
            project_paths = [
                p
                for p in traceback_paths
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
        text = self.safe_str(text)

        m = re.search(r"search for\s+(.+)", text, flags=re.IGNORECASE)
        if m:
            return self.safe_str(m.group(1))

        m = re.search(r"find\s+(.+)", text, flags=re.IGNORECASE)
        if m:
            return self.safe_str(m.group(1))

        return ""

    def _decide_tool_for_step(
        self, step_title: str, user_text: str, execution: dict | None = None
    ) -> dict:
        step_title = self.safe_str(step_title).lower()
        user_text = self.safe_str(user_text)
        lowered = user_text.lower()
        execution = execution or {}

        working_state = execution.get("working_state") or {}

        path = (
            self._guess_path_from_text(user_text)
            or self._guess_path_from_text(self.safe_str(execution.get("goal")))
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
        if any(
            x in step_title
            for x in ["list files", "directory", "folder", "project structure"]
        ):
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

        is_fix_intent = any(
            x in lowered
            for x in [
                "fix this",
                "fix this file",
                "fix bug",
                "fix error",
                "fix",
                "debug",
                "broken",
                "not working",
            ]
        )

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

        tool_name = self.safe_str(tool_decision.get("tool_name"))
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
                path = self.safe_str(args.get("path")).strip()
                user_text = self.safe_str(args.get("user_text")).strip()

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

        return {
            "ok": False,
            "error": f"Unknown tool: {tool_name}",
            "tool_name": tool_name,
        }

    def _cleanup_memory_items(self) -> None:
        try:
            memories = getattr(self.memory_service, "memories", None)
            if not isinstance(memories, list):
                return

            cleaned = []
            seen = set()

            for memory in memories:
                text = self.safe_str(memory.get("text")).strip().lower()

                if not text or len(text) < 4:
                    continue

                if text in ["ok", "hi", "yo", "test", "next", "go"]:
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

        active_task = self._safe_str(state.get("active_task"))
        next_step = self._safe_str(state.get("next_step"))

        if is_continue and active_task:
            user_text = f"Continue task: {active_task}. Next step: {next_step}"

        user_msg = self._build_user_message(
            original_user_text,
            attachments=attachments,
        )

        if not memory_context:
            memory_context = self._build_memory_context_for_chat(user_text, decision)

        username = ""

        if isinstance(session, dict):
            username = (
                session.get("username")
                or ""
            )

        if username:
            memory_context = (
                f"User name: {username}\n\n"
                + memory_context
            )

        print("MEMORY GOING INTO MODEL:")
        print(memory_context)

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

        try:
            assistant_text = (
                self.response_mojibake_cleanup_service.cleanup(
                    assistant_text
                )
            )
        except Exception as e:
            print(
                "MOJIBAKE CLEANUP FAILED:",
                e,
            )

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

        if "my name is" in memory_text:
            try:
                name_part = memory_text.split(
                    "my name is",
                    1,
                )[1].strip()

                name = name_part.split()[0]

                if name:
                    if "your name is" in (assistant_text or "").lower():
                        assistant_text = (
                            f"Your name is {name}."
                        )

            except Exception as e:
                print(
                    "NAME MEMORY RECALL FIX ERROR:",
                    e,
                )

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

        assistant_msg = self._build_assistant_message(
            text=assistant_text,
            attachments=[],
            meta={
                "used_memory": used_memory_full,
                "used_memory_count": len(used_memory_full),
                "memory_confidence": 1.0,
                "execution_mode": bool(is_execution or active_task),
                "active_task": active_task or original_user_text if is_execution else active_task,
                "next_step": next_step_out,
            },
            memory_used=[m.get("id") for m in used_memory_items if isinstance(m, dict)],
        )

        return self._finalize_response(
            session_id=session_id,
            user_text=original_user_text,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            decision=decision,
            saved_artifact=None,
        )


# NOVA_PLANNER_SERVICE_WIRING_20260609
# Disabled old runtime override.
# ChatService._process_goal_and_plan is now the source of truth.

pass

    # NOVA_CHATSERVICE_POST_COMPLETE_IDLE_GUARD_20260609

def install_chat_service_runtime_patches():
    install_project_brain_patch(ChatService)

    try:
        install_execution_planner_runtime_patches(ChatService)
    except Exception:
        pass

    try:
        install_token_usage_finalize_wrapper(ChatService)
    except Exception:
        pass

    try:
        install_non_web_source_leak_guard(ChatService)
    except Exception:
        pass

    try:
        install_attachment_web_suppression()
    except Exception:
        pass

def _nova_control_text_is_advance_20260609(value) -> bool:
        text = str(value or "").strip().lower()

        return text in {
            "k",
            "ok",
            "next",
            "continue",
            "run it",
            "run step",
            "execute",
            "advance",
        }


        def _nova_build_no_active_execution_response_20260609(self, user_text, session_id="", attachments=None):
            attachments = attachments or []

            try:
                execution = {}
                selected_execution_state = {}

                if hasattr(self, "_load_execution_state"):
                    execution = (
                        self._load_execution_state(session_id)
                        or {}
                    )

                if (
                    not execution
                    and hasattr(self, "_get_session_meta")
                ):
                    execution = (
                        self._get_session_meta(
                            session_id,
                            "execution_state",
                        )
                        or {}
                    )

                # Do not erase an active mission.
                if (
                    isinstance(execution, dict)
                    and execution.get("steps")
                ):
                    selected_execution_state = execution

                return self.execution_orchestrator_service.process_execution(
                    session_id=session_id,
                    state={
                        **selected_execution_state,
                        "continue_request": True,
                    },
                    command=(
                        next_action
                        or "continue"
                    ),
                )

                if False and hasattr(self, "_save_execution_state"):
                    self._save_execution_state(
                        session_id,
                        {},
                    )

                if False and hasattr(self, "_set_session_meta"):
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

                if hasattr(self, "_update_working_state"):
                    self._update_working_state(
                        session_id,
                        {
                            "active_task": "",
                            "next_move": "await_new_mission",
                            "checkpoint": "execution_complete_idle_guard",
                            "execution_status": "idle",
                        },
                    )

            except Exception:
                pass


        def _nova_advance_execution_request_post_complete_idle_20260609(
            self,
            user_text: str,
            session_id: str = "",
            attachments=None,
        ):
            attachments = attachments or []

            if _nova_control_text_is_advance_20260609(user_text):
                try:
                    execution = {}

                    if hasattr(self, "_load_execution_state"):
                        execution = (
                            self._load_execution_state(
                                session_id
                            )
                            or {}
                        )

                    if (
                        not execution
                        and hasattr(self, "_get_session_meta")
                    ):
                        execution = (
                            self._get_session_meta(
                                session_id,
                                "execution_state",
                            )
                            or {}
                        )

                    status = str(
                        (execution or {}).get("status")
                        or ""
                    ).strip().lower()

                    if (
                        status in {
                            "complete",
                            "completed",
                        }
                        or (execution or {}).get("complete") is True
                    ):
                        return _nova_build_no_active_execution_response_20260609(
                            self,
                            user_text=user_text,
                            session_id=session_id,
                            attachments=attachments,
                        )

                except Exception:
                    pass

            if callable(
                _nova_original_advance_execution_request_20260609
            ):
                return _nova_original_advance_execution_request_20260609(
                    self,
                    user_text=user_text,
                    session_id=session_id,
                    attachments=attachments,
                )

            return _nova_build_no_active_execution_response_20260609(
                self,
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
            )


        ChatService._advance_execution_request = (
            _nova_advance_execution_request_post_complete_idle_20260609
        )


        def _nova_attachment_guard_method_looks_like_result_web_route(name):
            lowered = str(name or "").lower()

            if not (
                "web" in lowered
                or "fetch" in lowered
                or "search" in lowered
                or "lookup" in lowered
            ):
                return False

            if _nova_attachment_guard_method_looks_like_bool_web_route(lowered):
                return False

            blocked = (
                "suppress",
                "guard",
                "install",
                "wrap",
                "predicate",
                "should",
                "needs",
            )

            if any(word in lowered for word in blocked):
                return False

            return True


        def install_chat_service_runtime_patches():
            install_project_brain_patch(ChatService)

            try:
                install_execution_planner_runtime_patches(ChatService)
            except Exception:
                pass

            try:
                install_token_usage_finalize_wrapper(ChatService)
            except Exception:
                pass

            try:
                install_non_web_source_leak_guard(ChatService)
            except Exception:
                pass

            try:
                install_attachment_web_suppression()
            except Exception:
                pass

# NOVA_FINAL_LIVE_MARKET_PRICE_ROUTE_AUTHORITY_20260820

try:
    _NOVA_PRE_FINAL_LIVE_MARKET_PRICE_DECIDE = ChatService._decide_route

    def _nova_live_market_price_text(args, kwargs):
        for key in (
            "user_text",
            "text",
            "message",
            "prompt",
            "query",
        ):
            value = kwargs.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        for value in args:
            if isinstance(value, str) and value.strip():
                return value.strip()

        return ""

    def _nova_is_live_market_price_request(value):
        text = " ".join(
            str(value or "")
            .lower()
            .replace("?", " ")
            .split()
        )

        if not text:
            return False

        return (
            any(
                x in text
                for x in (
                    "bitcoin",
                    "btc",
                    "crypto",
                    "stock",
                    "stocks",
                    "share",
                    "shares",
                )
            )
            and
            any(
                x in text
                for x in (
                    "price",
                    "right now",
                    "current",
                    "live",
                    "market",
                    "today",
                )
            )
        )

    def _nova_live_market_price_decide(
        self,
        *args,
        **kwargs,
    ):
        user_text = _nova_live_market_price_text(
            args,
            kwargs,
        )

        print(
            "DEBUG LIVE MARKET ROUTER CHECK:",
            user_text,
            flush=True,
        )

        if _nova_is_live_market_price_request(
            user_text
        ):
            print(
                "DEBUG LIVE MARKET FORCE WEB_FETCH",
                flush=True,
            )

            return {
                "route": self.ROUTE_WEB_FETCH,
                "mode": "web_fetch",
                "confidence": 1.0,
                "reasons": [
                    "live_market_price_force",
                ],
            }

        return _NOVA_PRE_FINAL_LIVE_MARKET_PRICE_DECIDE(
            self,
            *args,
            **kwargs,
        )

    ChatService._decide_route = (
        _nova_live_market_price_decide
    )

except Exception as e:
    print(
        "LIVE MARKET PATCH FAILED:",
        e,
    )

def _nova_attachment_guard_should_suppress_current_web_call(
    args=None,
    kwargs=None,
):
    args = args or ()
    kwargs = kwargs or {}

    user_text = ""

    payload = {}

    if len(args) > 0:
        user_text = str(args[0] or "")

    if len(args) > 1 and isinstance(args[1], dict):
        payload = args[1]

    if isinstance(kwargs.get("payload"), dict):
        payload = kwargs["payload"]

    attachments = payload.get("attachments") or []

    if not attachments:
        return False

    text = user_text.lower()

    explicit_web_terms = {
        "search",
        "look up",
        "latest",
        "news",
        "web",
        "internet",
    }

    if any(term in text for term in explicit_web_terms):
        return False

    return True


def _nova_attachment_guard_install_web_routing_suppression():

    cls = ChatService

    if hasattr(cls, "_should_use_web"):
        original_should_use_web = cls._should_use_web

        def wrapped_should_use_web(
            self,
            user_text,
            payload=None,
        ):
            if _nova_attachment_guard_should_suppress_current_web_call(
                args=(user_text, payload),
                kwargs={},
            ):
                return False

            return original_should_use_web(
                self,
                user_text,
                payload,
            )

        cls._should_use_web = wrapped_should_use_web


    if hasattr(cls, "_execute_web_search"):
        original_execute_web_search = cls._execute_web_search

        def wrapped_execute_web_search(
            self,
            user_text,
            payload=None,
        ):
            if _nova_attachment_guard_should_suppress_current_web_call(
                args=(user_text, payload),
                kwargs={},
            ):
                return {
                    "ok": False,
                    "suppressed": True,
                    "reason": "attachment_focused_turn",
                    "results": [],
                }

            return original_execute_web_search(
                self,
                user_text,
                payload,
            )

        cls._execute_web_search = wrapped_execute_web_search


    return {
        "installed": True,
        "wrapped_result_methods": [
            "_execute_web_search",
        ],
        "wrapped_bool_methods": [
            "_should_use_web",
        ],
        "guard": "attachment_web_routing_suppression",
    }

def _nova_install_attachment_guard_web_suppression():
    return _nova_attachment_guard_install_web_routing_suppression()

