from __future__ import annotations

from nova_backend.services.tool_runtime_factory import (
    build_tool_runtime,
)

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
from nova_backend.services.project_builder_service import ProjectBuilderService
from nova_backend.services.project_workspace_service import ProjectWorkspaceService
from nova_backend.services.execution.service import ExecutionService
from nova_backend.services.execution_mutation_service import ExecutionMutationService
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
from nova_backend.tools.executor import (
    execute_tool,
)

from nova_backend.tools.pending_tool_approval_service import (
    pending_tool_approval_service,
)
from nova_backend.services.chat.execution_patches import (
    install_execution_planner_runtime_patches,
)
from nova_backend.core.nova_orchestrator import (
    NovaOrchestrator,
)
from openai import OpenAI
from nova_backend.services import model_gateway_service
from nova_backend.services.repair_execution_service import RepairExecutionService
from nova_backend.services.execution_orchestrator_service import ExecutionOrchestratorService
from nova_backend.services.execution_step_service import ExecutionStepService
from nova_backend.services.execution_approval_service import ExecutionApprovalService

from nova_backend.core.execution_engine import (
    ExecutionEngine,
)

from nova_backend.core.execution_bridge import (
    ExecutionBridge,
)
from nova_backend.models.session import new_message
from nova_backend.services.agent_service import AgentService
from nova_backend.services.artifact_service import ArtifactService
from nova_backend.services.autonomy_service import AutonomyService
from nova_backend.services.memory_ranker_service import MemoryRankerService
from nova_backend.services.memory_service import MemoryService
from nova_backend.services.memory_recall_service import MemoryRecallService
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
from nova_backend.services.tool_executor import ToolExecutor
from nova_backend.tools.loader import load_tools
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

    INTERNAL_CHAT_ACTIONS = {
        "bug_intake",
        "auto_fix_file",
        "apply_pending_fix",
    }

    def _observe_response_behavior(
        self,
        *args,
        **kwargs,
    ):
        return None

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
        chat_execution_service=None,
        tool_executor=None,
    ):

        self.chat_execution_service = chat_execution_service

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

        # Wire the active ChatExecutionService to this ChatService's
        # ExecutionHandler. The module-level ChatExecutionService singleton
        # is created before ChatService exists, so it cannot receive the
        # handler during its own construction.
        if self.chat_execution_service is not None:
            self.chat_execution_service.execution_handler = (
                self.execution_handler
            )

        if self.chat_execution_service:
            self.chat_execution_service.set_session_service(
                session_service
            )
        self.response_handler = ChatResponseHandler(self)
        self.chat_router = ChatRouter(self)
        self.planner_service = PlannerService(self)
        self.project_workspace_service = ProjectWorkspaceService()
        self.project_builder_service = ProjectBuilderService(
            self.project_workspace_service
        )
        self.intelligence_router = IntelligenceRouter(self)
        # =========================
        # UNIFIED TOOL RUNTIME
        # =========================

        self.tool_runtime = build_tool_runtime(
            session_service=session_service,
            chat_service=self,
            attachment_service=artifact_service,
        )

        self.action_router = self.tool_runtime.get(
            "action_router"
        )

        self.tool_executor = self.tool_runtime.get(
            "tool_executor"
        )

        self.tool_registry = self.tool_runtime.get(
            "tool_registry"
        )

        self.tool_bridge = self.tool_runtime.get(
            "tool_bridge"
        )

        self.nova_tool_registry = self.tool_runtime.get(
            "nova_tool_registry"
        )

        # =========================
        # NOVA ORCHESTRATOR
        # =========================

        self.orchestrator = (
            NovaOrchestrator(
                execution_state_service=execution_state_service,
                memory_service=memory_service,
                tool_executor=self.tool_executor,
            )
        )
        self.decision_service = DecisionService(
            self
        )
        self.auto_fix_service = AutoFixService(self)
        self.session_service = session_service
        self.memory_service = memory_service
        self.memory_recall_service = MemoryRecallService(
            memory_service
        )
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
        # ACTIVE EXECUTION CACHE
        # =========================

        self.active_execution_cache = {}

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

        # ======= APPROVED DEBUG COMMENT INSERTED BELOW =======
        # Debug: Initialized ChatService with tool and execution runtimes
        #

        self.agent = AgentService()
        self.memory_ranker = MemoryRankerService()
        self.tools = ToolService(base_dir=os.getcwd())

        # =====================================================
        # UNIFIED NOVA TOOL RUNTIME
        # Runtime was initialized earlier in __init__.
        # All execution services use self.tool_executor.
        # =====================================================

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

        self.execution_step_service = (
            ExecutionStepService(
                safe_str=self._safe_str,
                python_runner=self.python_runner,
                approval_service=(
                    self.execution_approval_service
                ),
                tool_executor=self.tool_executor,
            )
        )

        self.execution_engine = (
            ExecutionEngine(
                step_service=self.execution_step_service,
            )
        )

        self.execution_bridge = (
            ExecutionBridge(
                execution_engine=self.execution_engine,
                execution_state_service=(
                    self.execution_state_service
                ),
            )
        )

        self.execution_orchestrator_service = (
            ExecutionOrchestratorService(
                execution_state_service=(
                    self.execution_state_service
                ),
                working_state_service=(
                    self.working_state_service
                ),
                execution_mutation_service=(
                    self.execution_mutation_service
                ),
                safe_str=self._safe_str,
                execution_step_service=(
                    self.execution_step_service
                ),
                execution_bridge=self.execution_bridge,
            )
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
        regenerate: bool = False,
    ):

        print(
            "[CHAT HANDLE ENTER]",
            user_text,
            session_id,
            flush=True,
        )

        print(
            "[CHAT HANDLE REGENERATE]",
            regenerate,
            flush=True,
        )

        import time

        _chat_handle_t0 = time.perf_counter()

        print(
            "[CHAT HANDLE START]",
            user_text,
            flush=True,
        )
        print("[CHAT HANDLE STEP 1]", flush=True)

        guard_result = self.accidental_input_guard_service.handle(
            user_text=user_text,
            session_id=session_id,
        )

        if guard_result:
            print(
                "[CHAT HANDLE END - INPUT GUARD]",
                round(time.perf_counter() - _chat_handle_t0, 3),
                "seconds",
                flush=True,
            )
            return guard_result

        # ==================================================
        # MEMORY FACT CAPTURE
        # Extract durable user facts/preferences before the
        # normal routing pipeline continues.
        # ==================================================

        try:
            memory_recall = getattr(
                self,
                "memory_recall_service",
                None,
            )

            if memory_recall is not None:
                memory_fact = (
                    memory_recall.extract_memory_fact(
                        user_text
                    )
                )

                if isinstance(memory_fact, dict):
                    fact_text = str(
                        memory_fact.get("text") or ""
                    ).strip()

                    if (
                        fact_text
                        and not memory_recall.memory_exists_for_session(
                            session_id,
                            fact_text,
                        )
                    ):
                        item = self.memory_service.add_memory(
                            {
                                "text": fact_text,
                                "kind": memory_fact.get(
                                    "kind",
                                    "note",
                                ),
                                "tags": memory_fact.get(
                                    "tags",
                                    [],
                                ),
                                "weight": memory_fact.get(
                                    "weight",
                                    1.0,
                                ),
                                "source": "router_auto",
                                "session_id": session_id,
                            }
                        )

                        print(
                            "[MEMORY AUTO CAPTURE]",
                            {
                                "session_id": session_id,
                                "memory": item,
                            },
                            flush=True,
                        )

                        if memory_fact.get("kind") == "profile":
                            memory_recall.cleanup_competing_name_memories(
                                session_id,
                                fact_text,
                            )

        except Exception as e:
            print(
                "[MEMORY AUTO CAPTURE ERROR]",
                repr(e),
                flush=True,
            )

        target_capture_result = (
            self.execution_bridge_service
            .try_execution_target_capture(
                session_id,
                user_text,
            )
        )

        print(
            "[AFTER EXECUTION TARGET CAPTURE]",
            round(time.perf_counter() - _chat_handle_t0, 3),
            flush=True,
        )

        if target_capture_result is not None:
            return target_capture_result

        if target_capture_result is not None:
            return target_capture_result

        print(
            "[CHAT BEFORE CHAT_HANDLE IMPORT]",
            flush=True,
        )

        from nova_backend.services.chat.handle import chat_handle
        print(
            "[AFTER CHAT_HANDLE IMPORT]",
            round(time.perf_counter() - _chat_handle_t0, 3),
            flush=True,
        )
        print("[CHAT HANDLE STEP 3 IMPORTED]", flush=True)

        print(
            "[CHAT AFTER CHAT_HANDLE IMPORT]",
            flush=True,
        )

        print(
            "[BEFORE CHAT_HANDLE CALL]",
            user_text,
            session_id,
            flush=True,
        )

        attachments = attachments or []

        # ==================================================
        # PRIMARY ROUTE DECISION
        # Classify before any project/mission orchestration.
        # ==================================================

        primary_decision = self._decide_route(
            user_text=user_text,
            attachments=attachments,
            session_id=session_id,
        )

        if not isinstance(primary_decision, dict):
            primary_decision = {
                "route": "general_chat",
                "mode": "chat",
                "intent": "conversation",
            }

        primary_route = str(
            primary_decision.get("route") or "general_chat"
        ).lower()

        print(
            "[CHAT PRIMARY ROUTE]",
            {
                "route": primary_route,
                "decision": primary_decision,
            },
            flush=True,
        )

        # --------------------------------------------------
        # Explicit live market requests
        # --------------------------------------------------

        if self._looks_like_live_market_request(user_text):
            brain_state = {
                "decision": {
                    "route": "web_fetch",
                    "mode": "web_fetch",
                    "intent": "live_market",
                }
            }

            primary_decision = brain_state["decision"]
            primary_route = "web_fetch"

        # --------------------------------------------------
        # Explicit execution routes
        # --------------------------------------------------

        elif (
            primary_route == "execution"
            or self._maybe_lock_execution_flow(
                user_text=user_text,
                session_id=session_id,
            )
        ):

            print(
                "[CHAT EXECUTION GATE]",
                {
                    "primary_route": primary_route,
                    "command_trigger": self._maybe_lock_execution_flow(
                        user_text=user_text,
                        session_id=session_id,
                    ),
                    "user_text": user_text,
                },
                flush=True,
            )

            current_execution = (
                self.chat_execution_service.get_state(
                    session_id
                )
            )

            if (
                self.chat_execution_service.is_execution_trigger(
                    user_text
                )
                and current_execution.get("complete") is True
            ):
                print(
                    "[CHAT HANDLE END - COMPLETE EXECUTION]",
                    round(
                        time.perf_counter()
                        - _chat_handle_t0,
                        3,
                    ),
                    "seconds",
                    flush=True,
                )

                return {
                    "status": "complete",
                    "execution_state": current_execution,
                }

            execution_result = (
                self._handle_execution_control(
                    user_text=user_text,
                    session_id=session_id,
                    attachments=attachments,
                )
            )

            if execution_result is not None:

                if (
                    isinstance(execution_result, dict)
                    and "execution" in execution_result
                    and "execution_state"
                    not in execution_result
                ):
                    execution_result[
                        "execution_state"
                    ] = execution_result["execution"]

                print(
                    "[CHAT HANDLE END - EXECUTION CONTROL]",
                    round(
                        time.perf_counter()
                        - _chat_handle_t0,
                        3,
                    ),
                    "seconds",
                    flush=True,
                )

                return execution_result

            brain_state = {
                "decision": primary_decision,
            }

        # --------------------------------------------------
        # Project/planner routes only
        # --------------------------------------------------

        elif primary_route in {
            "project_brain",
            "planner",
        }:

            session_payload = self._get_session_payload(
                session_id
            )

            print(
                "[BEFORE ORCHESTRATOR]",
                {
                    "route": primary_route,
                    "seconds": round(
                        time.perf_counter()
                        - _chat_handle_t0,
                        3,
                    ),
                },
                flush=True,
            )

            brain_state = self.orchestrator.run(
                user_text=user_text,
                session_context=session_payload,
                session_id=session_id,
            )

            if not isinstance(brain_state, dict):
                brain_state = {}

            brain_state["decision"] = primary_decision

            print(
                "[AFTER ORCHESTRATOR]",
                round(
                    time.perf_counter()
                    - _chat_handle_t0,
                    3,
                ),
                "seconds",
                flush=True,
            )

        # --------------------------------------------------
        # Normal chat
        # Never enter project planning or execution.
        # --------------------------------------------------

        else:

            brain_state = {
                "decision": primary_decision,
            }

            print(
                "[CHAT NORMAL LANE - ORCHESTRATOR SKIPPED]",
                {
                    "route": primary_route,
                    "seconds": round(
                        time.perf_counter()
                        - _chat_handle_t0,
                        3,
                    ),
                },
                flush=True,
            )

        response = chat_handle(
            self,
            user_text,
            session_id,
            attachments,
            brain_state=brain_state,
            decision=primary_decision,
            regenerate=regenerate,
        )

        print(
            "[AFTER CHAT_HANDLE]",
            round(time.perf_counter() - _chat_handle_t0, 3),
            "seconds",
            flush=True,
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

        response["brain_state"] = brain_state

        if memory_result:
            response.setdefault(
                "debug",
                {},
            )["memory_saved"] = True

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

        print(
            "[CHAT HANDLE END]",
            round(time.perf_counter() - _chat_handle_t0, 3),
            "seconds",
            flush=True,
        )

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
            attachment_context=attachment_context,
            tool_results=tool_results or [],
            model=str(
                getattr(self, "chat_model", "")
                or getattr(self, "model", "")
                or ""
            ),
            metadata=metadata or {
                "source": "chat_service.shadow_helper",
            },
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

        text = str(
            user_text or ""
        ).strip()

        # ----------------------------------------------------------
        # PROJECT BUILDER
        # ----------------------------------------------------------
        #
        # Only treat clear project-building requests as projects.
        # Ordinary questions, debugging requests, and control commands
        # continue through the existing execution/planner path.
        #
        if self._looks_like_project_request(
            text
        ) and not self._is_control_command_value(
            text
        ):
            try:
                project_result = (
                    self.project_builder_service
                    .build_project_from_request(
                        user_text=text,
                        owner_id="default",
                    )
                )

                if project_result:
                    return {
                        "status": "ready",
                        "route": "project_builder",
                        "intent": "project",
                        "project_id": project_result.get(
                            "project_id"
                        ),
                        "project": project_result.get(
                            "project"
                        ),
                        "plan": project_result.get(
                            "plan"
                        ),
                        "tasks": project_result.get(
                            "tasks"
                        ),
                        "goal": text,
                        "steps": project_result.get(
                            "tasks"
                        ) or [],
                    }

            except Exception as exc:
                self.logger.exception(
                    "Project Builder failed: %s",
                    exc,
                )

        # ----------------------------------------------------------
        # EXISTING EXECUTION / PLANNER PATH
        # ----------------------------------------------------------

        goal = self._build_goal(
            text,
            session_id,
        )

        plan = self._build_plan(
            goal,
        )

        execution = self._build_execution(
            text,
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
                    execution.get(
                        "steps",
                        [{}],
                    )[0].get(
                        "title"
                    )
                    if execution.get(
                        "steps"
                    )
                    else ""
                )
            )

            self._save_execution_state(
                session_id,
                execution,
            )

        return execution or {}

    def _looks_like_project_request(
        self,
        text: str,
    ) -> bool:
        """
        Detect explicit project-building intent.

        Keep this deliberately conservative so normal conversation
        does not accidentally create projects.
        """

        value = str(
            text or ""
        ).strip().lower()

        if not value:
            return False

        project_phrases = (
            "build a project",
            "build the project",
            "create a project",
            "start a project",
            "new project",
            "build an app",
            "create an app",
            "build a website",
            "create a website",
            "build a web app",
            "create a web app",
            "develop an app",
            "develop a website",
            "develop a system",
            "build a system",
            "create a system",
            "implement a system",
        )

        return any(
            phrase in value
            for phrase in project_phrases
        )
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

    def _build_goal(
        self,
        user_text: str,
        session_id: str = "",
    ) -> str:
        return self.safe_str(
            user_text
        ).strip()


    def _build_plan(
        self,
        goal: str,
    ) -> list:
        return [
            "Inspect the current state and constraints",
            "Choose the safest implementation path",
            "Apply the required change",
            "Verify the result",
            "Summarize outcome and next move",
        ]


    def _build_execution(
        self,
        user_text: str,
        plan,
        decision=None,
    ) -> dict:

        execution = (
            self.execution_service.build_planning_execution(
                user_text=self.safe_str(
                    user_text
                ).strip(),
                title="Nova Execution Plan",
                max_steps=5,
            )
        )

        if isinstance(plan, list) and plan:

            execution["steps"] = [
                {
                    "id": f"step_{index + 1}",
                    "text": self.safe_str(step),
                    "status": "pending",
                }
                for index, step in enumerate(plan)
                if self.safe_str(step)
            ]

        execution["goal"] = self.safe_str(
            user_text
        ).strip()

        execution["route"] = (
            decision.get("route")
            if isinstance(decision, dict)
            else "planner"
        )

        execution["intent"] = (
            decision.get("intent")
            if isinstance(decision, dict)
            else "planning"
        )

        return self.execution_service.normalize_execution(
            execution
        )

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
                "continue_request": True,
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


        for method_name in (
            "add_memory",
        ):

            method = getattr(
                self.memory,
                method_name,
                None,
            )

            if callable(method):

                result = method(payload)

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
        service = getattr(
            self,
            "memory_service",
            None,
        )

        if not service:
            print(
                "[MEMORY LIST DEBUG] no memory_service",
                flush=True,
            )
            return []

        try:
            result = None

            if hasattr(
                service,
                "all",
            ):
                result = service.all()

            elif hasattr(
                service,
                "list_memories",
            ):
                result = service.list_memories()

            elif hasattr(
                service,
                "build_list_payload",
            ):
                result = service.build_list_payload()

            print(
                "[MEMORY LIST DEBUG]",
                {
                    "service_type": type(service).__name__,
                    "result_type": type(result).__name__,
                    "result_preview": repr(result)[:1000],
                },
                flush=True,
            )

            if isinstance(
                result,
                list,
            ):
                return result

            if isinstance(
                result,
                dict,
            ):
                for key in (
                    "items",
                    "memories",
                    "data",
                    "results",
                ):
                    value = result.get(key)

                    if isinstance(
                        value,
                        list,
                    ):
                        return value

            return []

        except Exception as e:
            print(
                "[MEMORY LIST ERROR]",
                type(e).__name__,
                repr(e),
                flush=True,
            )

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

        # ==========================================
        # EXECUTION STEP — LIVE TOOL-FIRST PIPELINE
        # ==========================================

        try:
            decision = self._safe_dict(decision)
            mission = self._safe_dict(
                decision.get("mission")
            )
            execution = mission.get("execution")

            if (
                isinstance(execution, dict)
                and self._looks_like_execution(user_text)
            ):

                exec_result = None

                status = str(
                    execution.get("status") or ""
                ).lower()

                if status not in [
                    "complete",
                    "completed",
                    "done",
                ]:

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

                    decision["mission"]["execution"] = (
                        execution
                    )

                    step_output = self.safe_str(
                        exec_result.get("step_output")
                    ).strip()

                    saved_artifact = (
                        exec_result.get("saved_artifact")
                        or {}
                    )

                    artifact_body = ""

                    if isinstance(saved_artifact, dict):

                        artifact_body = self.safe_str(
                            saved_artifact.get("body")
                        ).strip()

                    # The user should see the actual
                    # completed step result, not the stale
                    # execution state rendered before execution.
                    if step_output:

                        assistant_text = step_output

                    elif artifact_body:

                        assistant_text = artifact_body

                    else:

                        assistant_text = self._render_execution(
                            execution,
                            include_prefix=True,
                        )

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

                elif isinstance(execution, dict):

                    # Completed executions still render
                    # their latest persisted state.
                    assistant_text = self._render_execution(
                        execution,
                        include_prefix=True,
                    )

        except Exception as e:

            exec_debug(
                "EXECUTION_STEP_ERROR:",
                e,
            )
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

        decision = (
            decision
            if isinstance(decision, dict)
            else {}
        )

        intelligence = (
            intelligence
            if isinstance(intelligence, dict)
            else {}
        )

        text = self.safe_str(
            user_text
        ).lower().strip()

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
                    regenerate=regenerate,
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
                web_result
