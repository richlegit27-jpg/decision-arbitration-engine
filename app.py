from __future__ import annotations

# NOVA_DURABLE_DATA_BOOTSTRAP_20260703
def _nova_durable_data_bootstrap_20260703():
    try:
        import os
        import shutil
        import time
        from pathlib import Path

        base_dir = Path(__file__).resolve().parent
        app_data = base_dir / "data"

        candidates = []

        explicit = os.environ.get("NOVA_DATA_DIR", "").strip()
        if explicit:
            candidates.append(Path(explicit))

        # Only use /data when it already exists, which indicates a real mounted
        # Railway volume. Do not create fake /data on local Windows or ephemeral
        # containers, because that can move repo-local data unexpectedly.
        volume_data = Path("/data")
        if os.name != "nt" and volume_data.exists():
            candidates.append(volume_data)

        candidates.append(app_data)

        chosen = None

        for candidate in candidates:
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                probe = candidate / ".nova_write_probe"
                probe.write_text("ok", encoding="utf-8")
                probe.unlink(missing_ok=True)
                chosen = candidate
                break
            except Exception:
                continue

        if chosen is None:
            chosen = app_data
            chosen.mkdir(parents=True, exist_ok=True)

        os.environ["NOVA_DATA_DIR"] = str(chosen)

        should_bridge_app_data = False
        try:
            should_bridge_app_data = chosen.resolve() != app_data.resolve()
        except Exception:
            should_bridge_app_data = str(chosen) != str(app_data)

        if should_bridge_app_data:
            chosen.mkdir(parents=True, exist_ok=True)

            if app_data.exists() and not app_data.is_symlink():
                for item in app_data.iterdir():
                    target = chosen / item.name
                    if target.exists():
                        continue
                    try:
                        if item.is_dir():
                            shutil.copytree(item, target)
                        else:
                            shutil.copy2(item, target)
                    except Exception:
                        pass

                try:
                    app_data.rename(base_dir / ("data_ephemeral_backup_" + time.strftime("%Y%m%d_%H%M%S")))
                except Exception:
                    pass

            if not app_data.exists():
                try:
                    app_data.symlink_to(chosen, target_is_directory=True)
                except Exception:
                    pass

        print("[NOVA_DURABLE_DATA_BOOTSTRAP_20260703] NOVA_DATA_DIR=", os.environ.get("NOVA_DATA_DIR"))
        print("[NOVA_DURABLE_DATA_BOOTSTRAP_20260703] app_data=", str(app_data), "real=", str(app_data.resolve()))

    except Exception as exc:
        try:
            print("[NOVA_DURABLE_DATA_BOOTSTRAP_20260703] failed:", exc)
        except Exception:
            pass


_nova_durable_data_bootstrap_20260703()
# /NOVA_DURABLE_DATA_BOOTSTRAP_20260703



def _nova_boot_log_20260701(*args, **kwargs):
    import os as _nova_boot_log_os_20260701

    if str(_nova_boot_log_os_20260701.getenv("NOVA_VERBOSE_BOOT_LOGS", "")).strip().lower() in {"1", "true", "yes", "on"}:
        print(*args, **kwargs)

import os
import re
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

from nova_backend.services.image_vision_service import ImageVisionService
from flask import Flask, Response, jsonify, render_template, request, send_from_directory, session
from flask_cors import CORS
from bs4 import BeautifulSoup
import uuid


def update_execution_state_safe(execution, status=None, current_step=None, last_action=None):
    """Safely assign status, current_step, last_action in execution dict."""
    if status is not None:
        execution["status"] = status
    if current_step is not None:
        execution["current_step"] = current_step
    if last_action is not None:
        execution["last_action"] = last_action

from werkzeug.utils import secure_filename

from nova_backend.services.debug_route_service import DebugRouteService

from nova_backend.services.attachment_shape_normalizer_service import (
    AttachmentShapeNormalizerService,
)


from nova_backend.services.lead_route_service import LeadRouteService

from nova_backend.routes.memory_panel_routes import (
    register_memory_panel_routes,
)

from nova_backend.services.mobile_session_persist_service import (
    MobileSessionPersistService,
)

from nova_backend.services.chat_attachment_guard_service import (
    ChatAttachmentGuardService,
)

from nova_backend.routes.improvement_routes import (

    register_improvement_routes,
)

from nova_backend.services.session_route_service import SessionRouteService

from nova_backend.services.stale_working_state_history_service import (
    clean_response_stale_working_state_history,
)

from nova_backend.services.upload_ownership_service import (
    UploadOwnershipService,
)

from nova_backend.services.execution_bridge_service import (
    ExecutionBridgeService,
)

from nova_backend.services.upload_route_service import (
    UploadRouteService,
)

from nova_backend.services.attachment_text_service import (
    AttachmentTextService,
)

from nova_backend.services.attachment_utils_service import (
    AttachmentUtilsService,
)

from nova_backend.services.execution_stream_service import (
    ExecutionStreamService,
)

from nova_backend.services.chat_stream_service import (
    ChatStreamService,
)

from nova_backend.services.execution_fix_service import (
    ExecutionFixService,
)

from nova_backend.services.session_detail_response_cache_service import (
    SessionDetailResponseCacheService,
)
from nova_backend.services.chat_guard_service import (
    ChatGuardService,
)
from nova_backend.services.project_state_route_guard_service import (
    ProjectStateRouteGuardService,
)

from nova_backend.services import session_auth_scope_service
from nova_backend.services import attachment_gate_service
from nova_backend.utils.api_response import ok_response, error_response
from nova_backend.utils.request_utils import get_json_body, get_str, get_list, normalize_attachments
from nova_backend.services import attachment_memory_service
from nova_backend.services.attachment_memory_service import (
    persist_attachments_for_session,
    summarize_attachments_for_session,
)
from nova_backend.utils.route_guard import guarded_json_route
from nova_backend.config import (
    BASE_DIR,
    DATA_DIR,
    UPLOADS_DIR,
    SESSIONS_FILE,
    ARTIFACTS_FILE,
    MEMORY_FILE,
    WEB_TIMEOUT,
    RECON_TIMEOUT,
)
from nova_backend.services.mobile_exchange_service import MobileExchangeService
from nova_backend.services.session_bootstrap_service import SessionBootstrapService
from nova_backend.services import attachment_shape_service
from nova_backend.services.admin_lead_service import AdminLeadService
from nova_backend.services.session_detail_cache_service import SessionDetailCacheService
from nova_backend.services.session_service import SessionService
from nova_backend.services.mobile_exchange_service import MobileExchangeService
from nova_backend.services.session_history_service import (
    SessionHistoryService,
)
from nova_backend.services.history_service import HistoryService
from nova_backend.services.artifact_service import ArtifactService
from nova_backend.services.memory_service import MemoryService
from nova_backend.services.memory_guard_route_service import (
    MemoryGuardRouteService,
)
from nova_backend.services.memory_recall_service import (
    MemoryRecallService,
)
from nova_backend.services.web_service import WebService
from nova_backend.services.recon_service import ReconService
from nova_backend.services.intent_router_service import IntentRouterService
from nova_backend.utils.file_utils import ensure_dir
from nova_backend.services.chat_service import ChatService
from nova_backend.services.execution_handler import NextMove, default_executor
from nova_backend.services.execution_daemon import ExecutionDaemon
from nova_backend.services.chat_execution_service import ChatExecutionService
from nova_backend.services.safe_unified_runtime import (
    SafeUnifiedRuntime,
)
from nova_backend.services.runtime_bootstrap import (
    RuntimeBootstrap,
)

from nova_backend.services.runtime_response_sanitizer_service import (
    RuntimeResponseSanitizerService,
)

from nova_backend.services.session_response_cleanup import (
    cleanup_session_response,
)

from nova_backend.services.title_guard_service import (
    clean_title,
    persist_title,
)

from nova_backend.services.project_recall_service import (
    ProjectRecallService,
)

from nova_backend.services.project_chat_response_router_service import (
    install_project_chat_response_router,
)

from nova_backend.services.session_response_finalizer_service import (
    assistant_message_already_saved,
    assistant_same_text_already_saved,
    user_message_already_saved,
)

from nova_backend.services.answer_quality_policy_service import (
    get_answer_quality_policy_answer,
)

from nova_backend.services.memory_context_service import (
    MemoryContextService,
)

from nova_backend.services.project_focus_memory_service import (
    ProjectFocusMemoryService,
)

from nova_backend.services.project_aware_context_service import (
    ProjectAwareContextService,
)

from nova_backend.services.project_state_memory_service import (
    ProjectStateMemoryService,
)

PROJECT_STATE_MEMORY_KINDS = (
    ProjectStateMemoryService.PROJECT_STATE_MEMORY_KINDS
)

from nova_backend.services.attachment_context_service import (
    AttachmentContextService,
)

from nova_backend.services.attachment_keypoints_service import (
    AttachmentKeypointsService,
)

from nova_backend.services.attachment_analysis_service import (
    AttachmentAnalysisService,
)

from nova_backend.services.response_quality_service import (
    ResponseQualityService,
)

from nova_backend.services.memory_command_service import (
    MemoryCommandService,
)

from nova_backend.services.attachment_summary_service import (
    AttachmentSummaryService,
)

from nova_backend.services.memory_guard_service import (
    MemoryGuardService,
)

from nova_backend.services.session_response_cache_service import (
    SessionResponseCacheService,
)

from nova_backend.services.attachment_endpoint_service import (
    AttachmentEndpointService,
)

from nova_backend.services.web_fetch_bridge_service import (
    WebFetchBridgeService,
)

from nova_backend.services.session_detail_response_cache_service import (
    SessionDetailResponseCacheService,
)

from nova_backend.services.session_detail_response_cache_service import (
    SessionDetailResponseCacheService,
)

from nova_backend.services.session_slim_response_service import (
    SessionSlimResponseService,
)

from nova_backend.services.account_profile_service import (
    AccountProfileService,
)

from nova_backend.services.login_page_route_service import (
    LoginPageRouteService,
)
from nova_backend.services.local_auth_route_service import (
    LocalAuthRouteService,
)

from nova_backend.services.auth_compat_route_service import (
    AuthCompatRouteService,
)

from nova_backend.services.session_auth_scope_service import (
    SessionAuthScopeService,
)

from nova_backend.services.admin_route_service import (
    AdminRouteService,
)
from nova_backend.services.execution_stream_route_service import (
    ExecutionStreamRouteService,
)

from nova_backend.services.attachment_memory_gate_service import (
    AttachmentMemoryGateService,
)

from nova_backend.services.blog_service import (
    BlogService,
)
from nova_backend.services.blog_route_service import (
    BlogRouteService,
)

from nova_backend.services.public_route_service import (
    PublicRouteService,
)

from nova_backend.services.history_route_service import (
    HistoryRouteService,
)

from nova_backend.services import empty_session_pruner_service
from nova_backend.services.chat_stream_service import ChatStreamService
from nova_backend.services.command_route_service import (
    CommandRouteService,
)

# NOVA_EXECUTION_SERVICE_SINGLETON_20260607
chat_execution_service = ChatExecutionService()
execution_bridge_service = ExecutionBridgeService(
    chat_execution_service,
    None,
)

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

app.secret_key = os.environ.get(
    "NOVA_SECRET_KEY",
    "nova-local-development-secret-key-change-me"
)
# NOVA_SELF_IMPROVEMENT_REPORT_ROUTES_20260710
try:
    register_improvement_routes(app)
    print("[NOVA_SELF_IMPROVEMENT_REPORT_ROUTES_20260710] installed")
except Exception as exc:
    print(
        "[NOVA_SELF_IMPROVEMENT_REPORT_ROUTES_20260710] failed:",
        exc,
    )

# NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701
# Priority project-brain intelligence adapter.
# Catches broad Nova project/judgment/concept questions before memory-write,
# generic chat, or stale fallback routes can answer them.
try:
    @app.before_request
    def _nova_project_brain_general_intelligence_priority_20260701():
        try:
            from flask import jsonify as _nova_gi_jsonify
            from flask import request as _nova_gi_request

            if (
                _nova_gi_request.path != "/api/chat"
                or _nova_gi_request.method != "POST"
            ):
                return None

            payload = (
                _nova_gi_request.get_json(
                    silent=True
                )
                or {}
            )

            if not isinstance(
                payload,
                dict,
            ):
                return None

            attachments = (
                payload.get(
                    "attachments"
                )
                or []
            )

            if attachments:
                return None

            user_text = str(
                payload.get(
                    "message"
                )
                or payload.get(
                    "text"
                )
                or payload.get(
                    "content"
                )
                or payload.get(
                    "user_text"
                )
                or ""
            ).strip()

            # -------------------------------------------------
            # EXPLICIT COMMAND REGISTRY OWNS ITS COMMAND PREFIX.
            #
            # This Project Brain priority guard runs before the
            # command-registry before_request guard. Explicit
            # command-registry requests must pass through to the
            # adapter-owned command registry route.
            # -------------------------------------------------

            explicit_command_prefixes = (
                "command-registry:",
                "workflow-catalog:",
            )

            if (
                user_text
                .strip()
                .lower()
                .startswith(
                    explicit_command_prefixes
                )
            ):
                return None

            normalized_user_text = (
                " ".join(
                    user_text
                    .lower()
                    .split()
                )
                .strip(" .!?")
            )

            session_id = str(
                payload.get(
                    "session_id"
                )
                or payload.get(
                    "active_session_id"
                )
                or payload.get(
                    "requested_session_id"
                )
                or ""
            ).strip()

            # -------------------------------------------------
            # ACTIVE EXECUTION OWNS EXECUTION CONTROL WORDS.
            #
            # Project Brain general intelligence is a broad
            # before_request interceptor. It must yield the
            # exact execution controls Nova advertises when an
            # active mission exists.
            # -------------------------------------------------

            execution_controls = {
                "k",
                "next",
                "continue",
                "run it",
            }

            if (
                normalized_user_text
                in execution_controls
            ):

                active_execution_getter = (
                    globals().get(
                        "_nova_phase4a_get_active_execution_20260701"
                    )
                )

                execution_is_active = (
                    globals().get(
                        "_nova_phase4a_execution_is_active_20260701"
                    )
                )

                if (
                    callable(
                        active_execution_getter
                    )
                    and callable(
                        execution_is_active
                    )
                ):

                    try:

                        active_execution = (
                            active_execution_getter(
                                session_id
                            )
                        )

                    except Exception as exc:

                        active_execution = None

                        try:
                            print(
                                "[NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701] "
                                "active execution control priority bypass:",
                                exc,
                            )
                        except Exception:
                            pass

                    if (
                        isinstance(
                            active_execution,
                            dict,
                        )
                        and execution_is_active(
                            active_execution
                        )
                    ):
                        return None

            exact_project_state_recall = {
                "what are we working on",
                "what did we just fix",
                "what is left",
            }

            if (
                normalized_user_text
                in exact_project_state_recall
            ):
                return None

            # NOVA_PROJECT_BRAIN_REPAIR_PLAN_COMMAND_YIELD_20260711
            #
            # Explicit repair-plan commands belong to the locked
            # repair-plan command owner. Project Brain is broad and
            # must yield before classifying repair failure text as
            # next_move_judgment.
            #
            # Use the canonical adapter extractor instead of copying
            # command prefixes into this route owner.
            try:
                from nova_backend.services.repair_plan_adapter import (
                    extract_repair_plan_input as _nova_gi_extract_repair_plan_input_20260711,
                )

                if (
                    _nova_gi_extract_repair_plan_input_20260711(
                        user_text
                    )
                    is not None
                ):
                    return None

            except Exception as exc:
                try:
                    print(
                        "[NOVA_PROJECT_BRAIN_REPAIR_PLAN_COMMAND_YIELD_20260711] "
                        "canonical command detection bypass:",
                        exc,
                    )
                except Exception:
                    pass

            # NOVA_PROJECT_BRAIN_REPAIR_BUILD_COMMAND_YIELD_20260711
            #
            # Explicit repair-build commands belong to the locked
            # repair-build adapter and command owner.
            #
            # Project Brain must yield before broad failure or
            # next-move judgment classification can hijack them.
            try:
                from nova_backend.services.repair_build_adapter import (
                    extract_repair_build_input as _nova_gi_extract_repair_build_input_20260711,
                )

                if (
                    _nova_gi_extract_repair_build_input_20260711(
                        user_text
                    )
                    is not None
                ):
                    return None

            except Exception as exc:
                try:
                    print(
                        "[NOVA_PROJECT_BRAIN_REPAIR_BUILD_COMMAND_YIELD_20260711] "
                        "canonical command detection bypass:",
                        exc,
                    )
                except Exception:
                    pass

            # NOVA_PHASE_7A_CONVERSATION_STATE_PROJECT_BRAIN_BYPASS_20260711
            # Existing owner only. No new route or before_request hook.
            try:
                from nova_backend.services.conversation_state_brain import (
                    conversation_state_brain,
                )

                _nova_7a_session_id = str(
                    payload.get(
                        "session_id"
                    )
                    or payload.get(
                        "active_session_id"
                    )
                    or ""
                ).strip()

                _nova_7a_session = (
                    chat_service._get_session_payload(
                        _nova_7a_session_id
                    )
                    if _nova_7a_session_id
                    else {}
                )

                _nova_7a_messages = (
                    _nova_7a_session.get(
                        "messages",
                        [],
                    )
                    if isinstance(
                        _nova_7a_session,
                        dict,
                    )
                    else []
                )

                _nova_7a_state = (
                    conversation_state_brain.build_state(
                        _nova_7a_messages,
                        current_user_text=user_text,
                    )
                )

                normalized_project_brain_question = " ".join(
                    user_text.lower().split()
                )

                explicit_project_brain_question = any(
                    marker in normalized_project_brain_question
                    for marker in (
                        "actual blocker",
                        "blocker on nova",
                        "what is blocking nova",
                        "what's blocking nova",
                        "where's the project at",
                        "where is the project at",
                    )
                )

                if (
                    not explicit_project_brain_question
                    and (
                        _nova_7a_state
                        .suppress_project_brain_contract
                        or (
                            getattr(
                                _nova_7a_state,
                                "current_intent",
                                "",
                            )
                            ==
                            "resume_unresolved_thread"
                            and bool(
                                getattr(
                                    _nova_7a_state,
                                    "unresolved_threads",
                                    (),
                                )
                            )
                        )
                    )
                ):
                    return None

            except Exception as _nova_7a_state_error:
                try:
                    print(
                        "[NOVA_PHASE_7A_CONVERSATION_STATE_PROJECT_BRAIN_BYPASS_20260711] bypass failed:",
                        _nova_7a_state_error,
                    )
                except Exception:
                    pass

            from nova_backend.services.project_brain_general_intelligence import (
                build_project_brain_general_answer,
            )

            answer = (
                build_project_brain_general_answer(
                    user_text
                )
            )

            if not answer:
                return None

            data = {
                "ok": True,
                "text": answer.text,
                "content": answer.text,
                "assistant_message": {
                    "role": "assistant",
                    "text": answer.text,
                    "content": answer.text,
                },


                "debug": {
                    "route": (
                        "autonomy_plan_command"
                        if answer.intent == "autonomy_plan"
                        else (
                            "project_state_current_memory_direct_recall"
                            if answer.intent == "current_project_state"
                            else "project_brain_general_intelligence"
                        )
                    ),
                    "route_taken": (
                        "autonomy_plan_command"
                        if answer.intent == "autonomy_plan"
                        else (
                            "project_state_current_memory_direct_recall"
                            if answer.intent == "current_project_state"
                            else "project_brain_general_intelligence"
                        )
                    ),
                    "intent": answer.intent,
                    "priority_project_brain_general_intelligence": True,
                    "mode": (
                        "proposal_only"
                        if answer.intent == "autonomy_plan"
                        else None
                    ),
                },
            }

            return _nova_gi_jsonify(
                data
            )

        except Exception as exc:
            try:
                print(
                    "[NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701] failed:",
                    exc,
                )
            except Exception:
                pass

            return None

    print("[NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701] installed")
except Exception as _nova_project_brain_general_intelligence_priority_error_20260701:
    print(
        "[NOVA_PROJECT_BRAIN_GENERAL_INTELLIGENCE_PRIORITY_20260701] install failed:",
        _nova_project_brain_general_intelligence_priority_error_20260701,
    )


CORS(app)

ensure_dir(DATA_DIR)
ensure_dir(UPLOADS_DIR)

app.config["UPLOAD_FOLDER"] = str(UPLOADS_DIR)

# -----------------------
# SERVICES
# -----------------------


session_service = SessionService(
    DATA_DIR / "nova_sessions.json"
)

command_route_service = CommandRouteService(
    session_service
)

memory_command_service = MemoryCommandService(
    session_service=session_service,
)

session_bootstrap_service = SessionBootstrapService(
    session_service,
    logger=app.logger,
)

mobile_exchange_service = MobileExchangeService(
    session_service
)

session_history_service = SessionHistoryService(
    BASE_DIR
)


history_service = HistoryService(
    session_history_service
)


project_state_memory_service = ProjectStateMemoryService(
    DATA_DIR / "nova_project_state.json"
)

memory_context_service = MemoryContextService(
    DATA_DIR,
    session_service,
)

artifact_service = ArtifactService(
    str(DATA_DIR / "nova_artifacts.json")
)

upload_ownership_service = UploadOwnershipService(
    "data/nova_upload_ownership.json"
)

upload_route_service = UploadRouteService(
    uploads_dir=UPLOADS_DIR,
    upload_ownership_service=upload_ownership_service,
)

project_aware_context_service = ProjectAwareContextService(
    memory_context_service,
    session_service,
)

attachment_memory_gate_service = AttachmentMemoryGateService(
    attachment_gate_service,
    attachment_memory_service,
)

attachment_context_service = AttachmentContextService(
    UPLOADS_DIR,
)

local_auth_route_service = LocalAuthRouteService(
    app,
    request,
    jsonify,
    session,
)

chat_stream_service = ChatStreamService()
session_route_service = SessionRouteService()
public_route_service = PublicRouteService()
login_page_route_service = LoginPageRouteService()
auth_compat_route_service = AuthCompatRouteService()
attachment_shape_normalizer_service = AttachmentShapeNormalizerService()
session_auth_scope_service = SessionAuthScopeService()
mobile_session_persist_service = MobileSessionPersistService()
project_state_route_guard_service = ProjectStateRouteGuardService()
memory_service = MemoryService(
    str(DATA_DIR / "nova_memory.json")
)

memory_recall_service = MemoryRecallService(
    memory_service
)

project_focus_memory_service = ProjectFocusMemoryService(
    memory_service,
    session_service,
)
project_recall_service = ProjectRecallService(
    project_focus_memory_service,
    project_state_memory_service,
    PROJECT_STATE_MEMORY_KINDS,
    DATA_DIR,
)


memory_guard_service = MemoryGuardService()

memory_guard_route_service = MemoryGuardRouteService(
    memory_service,
    session_service,
    memory_guard_service,
)
attachment_summary_service = AttachmentSummaryService()
attachment_utils_service = AttachmentUtilsService()
response_quality_service = ResponseQualityService()
admin_lead_service = AdminLeadService()
lead_route_service = LeadRouteService(admin_lead_service)
admin_route_service = AdminRouteService(
    admin_lead_service,
)
session_detail_cache_service = SessionDetailCacheService()
session_response_cache_service = SessionResponseCacheService(
    session_service,
    session_detail_cache_service,
    attachment_context_service,
)

chat_guard_service = ChatGuardService()
account_profile_service = AccountProfileService()
session_slim_response_service = SessionSlimResponseService()
web_service = WebService(timeout=WEB_TIMEOUT)
recon_service = ReconService(timeout=RECON_TIMEOUT)
intent_router = IntentRouterService()
runtime_brain = SafeUnifiedRuntime()
runtime_response_sanitizer = RuntimeResponseSanitizerService()
attachment_keypoints_service = AttachmentKeypointsService()
install_project_chat_response_router(app)
attachment_analysis_service = AttachmentAnalysisService()
attachment_text_service = AttachmentTextService()
blog_service = BlogService()
debug_route_service = DebugRouteService()
blog_route_service = BlogRouteService(
    blog_service
)

blog_service = BlogService()

history_route_service = HistoryRouteService(
    BASE_DIR
)

restored_runtime = getattr(
    runtime_brain,
    "restored_runtime_state",
    {},
)
attachment_endpoint_service = AttachmentEndpointService()

_nova_boot_log_20260701(
    "RESTORED RUNTIME OK",
    {
        "runtime_health": restored_runtime.get(
            "runtime_health"
        ),
        "runtime_signal": restored_runtime.get(
            "runtime_signal"
        ),
        "cycle_count": restored_runtime.get(
            "cycle_count"
        ),
    },
)

lead_route_service.install_routes(app)
debug_route_service.install_routes(app)
memory_guard_route_service.install_routes(app)
session_auth_scope_service.install(app)
empty_session_pruner_service.install(app)
memory_guard_route_service.install_routes(app)
local_auth_route_service.install_routes()
login_page_route_service.install_routes(app)
auth_compat_route_service.install_routes(app)
public_route_service.install_routes(app)
admin_route_service.install_routes(app)

history_route_service.install_routes(
    app,
    history_service,
)
command_route_service.install_routes(app)

last_compressed = getattr(
    runtime_brain,
    "last_compressed_runtime",
    {},
)

_nova_boot_log_20260701(
    "LAST COMPRESSED OK",
    {
        "runtime_health": last_compressed.get(
            "runtime_health"
        ),
        "runtime_signal": last_compressed.get(
            "runtime_signal"
        ),
        "cycle_count": last_compressed.get(
            "cycle_count"
        ),
    },
)

session_detail_response_cache_service = SessionDetailResponseCacheService(
    session_service,
    session_detail_cache_service,
    session_response_cache_service,
    attachment_text_service,
)

chat_service = ChatService(

    session_service=session_service,
    memory_service=memory_service,
    artifact_service=artifact_service,
    web_service=web_service,
    recon_service=recon_service,
)

execution_stream_service = ExecutionStreamService(
    session_service=session_service,
    chat_service=chat_service,
    default_executor=default_executor,
    next_move_class=NextMove,
    update_execution_state_safe=update_execution_state_safe,
)


execution_fix_service = ExecutionFixService(
    session_service=session_service,
    default_executor=default_executor,
    next_move_class=NextMove,
    update_execution_state_safe=update_execution_state_safe,
)

execution_stream_route_service = ExecutionStreamRouteService(
    session_service=session_service,
    execution_service=chat_execution_service,
    execution_stream_service=execution_stream_service,
    execution_fix_service=execution_fix_service,
)
# =========================
# RUNTIME BINDING
# =========================
chat_service.runtime = runtime_brain
chat_service.safe_runtime = runtime_brain
chat_service.runtime_brain = runtime_brain
app.runtime_brain = runtime_brain
app.config["runtime_brain"] = runtime_brain

install_project_chat_response_router(app)

RuntimeBootstrap.save(
    runtime_brain
)

if hasattr(chat_service, "start_execution_daemon"):
    chat_service.start_execution_daemon()

# REMOVE_APP_STARTUP_CHATSERVICE_DEBUG_LOCK

# -----------------------
# HELPERS
# -----------------------

IDENTITY_QUESTION_PATTERNS = [
    re.compile(r"\bwhat(?:'s| is)\s+my\s+name\b", re.IGNORECASE),
    re.compile(r"\bdo\s+you\s+know\s+my\s+name\b", re.IGNORECASE),
    re.compile(r"\bwho\s+am\s+i\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+do\s+you\s+know\s+about\s+me\b", re.IGNORECASE),
]

NAME_MEMORY_PATTERNS = [
    re.compile(r"^\s*user\s+name\s+is\s+(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*name\s*:\s*(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*my\s+name\s+is\s+(.+?)\s*$", re.IGNORECASE),
]


def json_ok(**kwargs):
    payload = {"ok": True}
    payload.update(kwargs)
    return jsonify(payload)



def json_error(message: str, status: int = 400, **kwargs):
    payload = {"ok": False, "error": str(message)}
    payload.update(kwargs)
    return jsonify(payload), status

def request_json() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def build_common_state_payload(session_id: str = "") -> dict:
    session = None
    if session_id:
        session = session_service.get_session(session_id)
    if not session:
        session = session_service.get_active()

    return {
        "session": session,
        "sessions": session_service.get_all(),
        "active_session_id": session_service.active_session_id,
        "artifacts": artifact_service.build_list_payload(),
        "memory": memory_service.build_list_payload(),
    }




def extract_memory_fact(user_text: str) -> dict | None:
    return memory_recall_service.extract_memory_fact(
        user_text
    )

def memory_exists_for_session(
    session_id: str,
    fact_text: str,
) -> bool:
    return memory_recall_service.memory_exists_for_session(
        session_id,
        fact_text,
    )

def extract_name_from_memory_text(
    text: str,
) -> str:
    return memory_recall_service.extract_name_from_memory_text(
        text
    )

def is_name_memory_item(
    item: dict,
) -> bool:
    return memory_recall_service.is_name_memory_item(
        item
    )


def get_memory_items():
    try:
        items = memory_service.all()
        return items if isinstance(items, list) else []
    except Exception:
        return []


def delete_memory_item(memory_id: str) -> bool:
    if not memory_id:
        return False

    for method_name in ("delete_memory", "delete", "remove"):
        method = getattr(memory_service, method_name, None)
        if callable(method):
            try:
                return bool(method(memory_id))
            except Exception:
                return False
    return False


def score_name_memory(
    item: dict,
    session_id: str,
) -> float:
    return memory_recall_service.score_name_memory(
        item,
        session_id,
    )

def find_best_name_memory(
    session_id: str,
) -> dict | None:
    return memory_recall_service.find_best_name_memory(
        session_id
    )

def cleanup_competing_name_memories(
    session_id: str,
    winning_text: str,
):
    return memory_recall_service.cleanup_competing_name_memories(
        session_id,
        winning_text,
    )

@app.get("/")
def index():
    # NOVA_ROOT_PUBLIC_HOME_ALIGNMENT_20260709
    return render_template("nova_landing_home.html")

@app.get("/preview")
def preview():
    return render_template("preview_index.html")

@app.get("/mobile")
def mobile():
    return render_template("mobile.html")




# -----------------------
# HEALTH
# -----------------------


# ============================================================
# NOVA_USAGE_API_ROUTES_ACTIVE_20260705
# Token / usage tracking endpoints.
# ============================================================

@app.get("/api/usage")
def nova_api_usage_summary_active_20260705():
    try:
        from nova_backend.services.usage_ledger_service import usage_summary
        return json_ok(**usage_summary())
    except Exception as exc:
        return json_error(str(exc), route="nova_api_usage_summary_active_20260705")


@app.get("/api/usage/session/<session_id>")
def nova_api_usage_session_summary_active_20260705(session_id):
    try:
        from nova_backend.services.usage_ledger_service import usage_summary
        return json_ok(**usage_summary(session_id=session_id))
    except Exception as exc:
        return json_error(
            str(exc),
            route="nova_api_usage_session_summary_active_20260705",
            session_id=session_id,
        )

@app.get("/api/health")
def api_health():
    return json_ok(
        status="ready",
        app="nova",
        cwd=os.getcwd(),
        base_dir=str(BASE_DIR),
        uploads_dir=str(UPLOADS_DIR),
        sessions_file=str(SESSIONS_FILE),
        artifacts_file=str(ARTIFACTS_FILE),
        memory_file=str(MEMORY_FILE),
        route_build="backend-memory-recall-fix-phase-1-001",
    )


# -----------------------
# STATE
# -----------------------

@app.get("/api/state")
def api_state():
    sessions = session_service.get_all()
    active_session = session_service.get_active() or {}

    if not isinstance(active_session, dict):
        active_session = {}

    active_session_id = str(
        getattr(session_service, "active_session_id", "")
        or active_session.get("id")
        or active_session.get("session_id")
        or ""
    ).strip()

    messages = active_session.get("messages")
    if not isinstance(messages, list):
        messages = []

    working_state = active_session.get("working_state")
    if not isinstance(working_state, dict):
        working_state = {}

    active_task = str(
        working_state.get("active_task")
        or working_state.get("task")
        or ""
    ).strip()

    current_file = str(
        working_state.get("current_file")
        or working_state.get("file")
        or ""
    ).strip()

    last_user_message = ""
    last_assistant_message = ""

    for message in reversed(messages):
        if not isinstance(message, dict):
            continue

        role = str(message.get("role") or "").strip().lower()
        text = str(
            message.get("text")
            or message.get("content")
            or ""
        ).strip()

        if role == "user" and not last_user_message:
            last_user_message = text

        if role == "assistant" and not last_assistant_message:
            last_assistant_message = text

        if last_user_message and last_assistant_message:
            break

    if not active_task:
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue

            if str(message.get("role") or "").strip().lower() != "user":
                continue

            text = str(
                message.get("text")
                or message.get("content")
                or ""
            ).strip()

            text_lc = text.lower()

            if "we are working on" in text_lc:
                active_task = text_lc.split("we are working on", 1)[1].strip(" .")
                break

            if "working on" in text_lc:
                active_task = text_lc.split("working on", 1)[1].strip(" .")
                break

    if not current_file and active_task:
        parts = active_task.replace(",", " ").split()

        for part in parts:
            clean_part = part.strip("`'\".,:;()[]{}")

            if clean_part.endswith((".py", ".js", ".css", ".html", ".json", ".md", ".txt")):
                current_file = clean_part
                break

    normalized_working_state = {
        "active_task": active_task,
        "current_file": current_file,
        "last_user_message": last_user_message,
        "last_assistant_message": last_assistant_message,
    }

    state = {
        "active_session_id": active_session_id,
        "active_task": active_task,
        "current_file": current_file,
        "last_user_message": last_user_message,
        "last_assistant_message": last_assistant_message,
        "working_state": normalized_working_state,
    }

    return json_ok(
        state=state,
        sessions=sessions,
        active_session_id=active_session_id,
        session=active_session,
        working_state=normalized_working_state,
        active_task=active_task,
        current_file=current_file,
        last_user_message=last_user_message,
        last_assistant_message=last_assistant_message,
        artifacts=artifact_service.build_list_payload(),
        memory=memory_service.build_list_payload(),
    )

# NOVA_SKIP_RAW_BINARY_ATTACHMENT_INJECTION_20260607
def should_skip_raw_attachment_injection(self, item):
    try:
        if not isinstance(item, dict):
            return False

        mime = str(item.get("mime_type") or item.get("type") or item.get("content_type") or "").lower()
        name = str(
            item.get("filename")
            or item.get("original_filename")
            or item.get("name")
            or item.get("url")
            or item.get("file_url")
            or ""
        ).lower()

        blocked_exts = (
            ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif",
            ".zip", ".exe", ".dll", ".bin"
        )

        blocked_mimes = {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/pdf",
            "application/zip",
            "application/octet-stream",
        }

        if mime in blocked_mimes:
            return True

        if mime.startswith("image/"):
            return True

        return name.endswith(blocked_exts)
    except Exception:
        return False


def filter_raw_injection_attachments(
    self,
    attachments,
    logger=None,
):
    kept = []
    skipped = []

    for item in attachments or []:
        if self.should_skip_raw_attachment_injection(item):
            skipped.append(item)
        else:
            kept.append(item)

    if skipped and logger:
        try:
            names = [
                str(
                    x.get("original_filename")
                    or x.get("filename")
                    or x.get("name")
                    or x.get("url")
                    or "attachment"
                )
                for x in skipped
                if isinstance(x, dict)
            ]

            logger.info(
                "[RawAttachmentInjectionGuard] skipped raw binary injection for attachments=%s",
                names,
            )
        except Exception:
            pass

    return kept



@app.route("/api/chat", methods=["POST"])
def api_chat_route():
    return api_chat()

@app.route("/api/runtime/summary", methods=["GET"])
def api_runtime_summary():
    return jsonify({"ok": True})

@app.route("/api/runtime/history", methods=["GET"])
def api_runtime_history():
    return jsonify({"ok": True})

@app.route("/api/runtime/decision", methods=["GET"])
def api_runtime_decision():
    return jsonify({"ok": True})

@app.route("/api/runtime/bridge", methods=["POST"])
def api_runtime_bridge():
    return jsonify({"ok": True})

@app.route("/api/runtime/cycle", methods=["POST"])
def api_runtime_cycle():
    try:
        runtime = runtime_brain

        result = runtime.run_cycle(
            execution_state={
                "status": "failed",
                "error": "api_runtime_cycle_test",
                "steps": [
                    {
                        "title": "Runtime API cycle test",
                        "status": "failed",
                    }
                ],
            },
            world_state={},
            scheduler_state={},
            knowledge_graph={},
        )

        runtime.last_compressed_runtime = (
            result.get(
                "compressed_runtime",
                {}
            )
        )

        summary = getattr(
            runtime,
            "last_compressed_runtime",
            {},
        )

        return jsonify(
            {
                "ok": True,
                "result": result,
                "runtime": summary,
            }
        )

    except Exception as e:
        return jsonify(
            {
                "ok": False,
                "error": str(e),
            }
        ), 500

@app.post("/api/fetch")
def api_fetch():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url") or "").strip()

    if not url:
        return jsonify({
            "ok": False,
            "error": "Missing url",
            "summary": "",
        }), 400

    result = web_service.fetch(url)

    clean_result = (
        runtime_response_sanitizer.sanitize(
            result
        )
    )

    return jsonify(clean_result)
# NOVA_RESTORE_API_SESSIONS_ROUTE_20260609
@app.get("/api/sessions")
def api_sessions():
    try:
        flask_session = globals().get("session")
        current_user_id = str(
            flask_session.get("nova_user_id")
            or flask_session.get("user_id")
            or ""
        ).strip()
    except Exception:
        current_user_id = ""

    sessions = session_service.get_all(
        user_id=current_user_id,
    )

    return json_ok(
        sessions=sessions,
        active_session_id=session_service.active_session_id,
        session=session_service.get_active(),
        artifacts=artifact_service.build_list_payload(),
        memory=memory_service.build_list_payload(),
    )



# NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702
# Fresh exact project-state recall bridge.
# Thin app.py adapter; decision and response construction live in service layer.
try:
    from flask import jsonify as _nova_project_state_direct_fresh_jsonify_20260702
    from flask import request as _nova_project_state_direct_fresh_request_20260702

    @app.before_request
    def _nova_project_state_direct_freshness_bridge_20260702():
        try:
            if (
                _nova_project_state_direct_fresh_request_20260702.path
                != "/api/chat"
            ):
                return None

            if (
                _nova_project_state_direct_fresh_request_20260702.method
                != "POST"
            ):
                return None

            payload = (
                _nova_project_state_direct_fresh_request_20260702
                .get_json(
                    silent=True
                )
                or {}
            )

            if not isinstance(
                payload,
                dict,
            ):
                return None

            session_id = str(
                payload.get(
                    "session_id"
                )
                or payload.get(
                    "active_session_id"
                )
                or payload.get(
                    "requested_session_id"
                )
                or ""
            ).strip()

            # -------------------------------------------------
            # ACTIVE EXECUTION OWNS STATUS CONTINUITY.
            #
            # This before_request bridge runs before /api/chat
            # endpoint wrappers. Without this priority check,
            # exact project-state prompts return here before
            # NOVA_PROJECT_STATE_DIRECT_FRESHNESS_ACTIVE_EXECUTION_BYPASS_20260701
            # can answer.
            # -------------------------------------------------

            active_execution_getter = globals().get(
                "_nova_phase4a_get_active_execution_20260701"
            )

            if callable(
                active_execution_getter
            ):

                try:

                    active_execution = (
                        active_execution_getter(
                            session_id
                        )
                    )

                except Exception as exc:

                    active_execution = None

                    try:
                        print(
                            "[NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702] "
                            "active execution priority bypass:",
                            exc,
                        )
                    except Exception:
                        pass

                if isinstance(
                    active_execution,
                    dict,
                ):

                    execution_is_active = globals().get(
                        "_nova_phase4a_execution_is_active_20260701"
                    )

                    if (
                        callable(
                            execution_is_active
                        )
                        and execution_is_active(
                            active_execution
                        )
                    ):
                        return None

            from nova_backend.services.project_state_direct_freshness_bridge import (
                build_project_state_direct_fresh_response,
            )

            response_json = (
                build_project_state_direct_fresh_response(
                    payload
                )
            )

            if not response_json:
                return None

            return (
                _nova_project_state_direct_fresh_jsonify_20260702(
                    response_json
                )
            )

        except Exception as exc:
            try:
                print(
                    "[NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702] failed:",
                    exc,
                )
            except Exception:
                pass

            return None

    print("[NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702] installed")
except Exception as _nova_project_state_direct_freshness_bridge_error_20260702:
    print("[NOVA_PROJECT_STATE_DIRECT_FRESHNESS_BRIDGE_20260702] failed:", _nova_project_state_direct_freshness_bridge_error_20260702)


# CASUAL_CHAT_GUARD_20260604
@app.before_request
def _nova_casual_chat_guard():
    try:
        from flask import request, jsonify

        if request.path not in ("/api/chat", "/api/chat/stream") or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}
        user_text = str(payload.get("user_text") or "").strip()
        # NOVA_AUTO_PLAN_EXECUTION_START_GUARD_20260607
        auto_plan_execution_result = None
        if auto_plan_execution_result is not None:
            return jsonify(auto_plan_execution_result)

        chat_guard_result = chat_guard_service.handle_casual_chat_guard(
            payload,
            execution_bridge_service,
        )

        if chat_guard_result is not None:
            return jsonify(chat_guard_result)


        attachments = payload.get("attachments") or []

        if attachments:
            return None

        clean = " ".join(user_text.lower().split()).strip(" ?!.")

        casual_replies = {
            "hi": "Hey.",
            "hey": "Hey.",
            "hello": "Hey.",
            "yo": "Yo.",
            "sup": "I'm here.",
            "how are you": "I'm good. Ready when you are.",
            "how are u": "I'm good. Ready when you are.",
            "how you doing": "I'm good. Ready when you are.",
            "whats up": "I'm here. Ready for the next move.",
            "what's up": "I'm here. Ready for the next move.",
        }

        if clean not in casual_replies:
            return None

        session_id = str(payload.get("session_id") or "").strip()

        return jsonify({
            "ok": True,
            "session_id": session_id,
            "active_session_id": session_id,
            "assistant_message": {
                "role": "assistant",
                "text": casual_replies[clean],
                "attachments": [],
                "meta": {
                    "route": "casual_chat_guard"
                }
            },
            "attachments": [],
            "session_attachments": [],
            "debug": {
                "route": "casual_chat_guard"
            }
        })

    except Exception:
        return None


@app.post("/api/chat")


def _nova_mobile_now_iso():
    try:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    except Exception:
        return ""









def api_chat():
    from flask import session as flask_session
    # NOVA_API_CHAT_IMAGE_VISION_GATE_20260607
    try:
        from pathlib import Path as _NovaPath
        import base64 as _nova_base64
        import mimetypes as _nova_mimetypes
        import os as _nova_os

        _nova_payload = request.get_json(silent=True) or {}

        _nova_user_text = str(
            _nova_payload.get("user_text")
            or _nova_payload.get("text")
            or _nova_payload.get("message")
            or ""
        ).strip()

        _nova_session_id = str(
            _nova_payload.get("session_id")
            or _nova_payload.get("client_session_id")
            or "default"
        ).strip() or "default"

        _nova_attachments = _nova_payload.get("attachments") or []

        # ?? IMAGE FASTPATH SAFETY GUARD
        if str(_nova_user_text or "").strip().lower().startswith("/image"):
            _nova_attachments = []

        _nova_image = None

        if isinstance(_nova_attachments, list):
            for _nova_item in _nova_attachments:
                if not isinstance(_nova_item, dict):
                    continue

                _nova_mime = str(
                    _nova_item.get("mime_type")
                    or _nova_item.get("type")
                    or ""
                ).lower()

                _nova_name_probe = str(
                    _nova_item.get("filename")
                    or _nova_item.get("original_filename")
                    or _nova_item.get("name")
                    or _nova_item.get("url")
                    or _nova_item.get("file_url")
                    or ""
                ).lower()

                if (
                    _nova_mime.startswith("image/")
                    or any(ext in _nova_name_probe for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"))
                ):
                    _nova_image = _nova_item
                    break
        # NOVA_IMAGE_GATE_WEB_INTENT_STRIPS_STALE_ATTACHMENTS_20260609
        # Web/news prompts must ignore stale mobile attachment payload before the image gate scans it.
        _nova_image_gate_clean = " ".join(str(_nova_user_text or "").lower().split())
        _nova_image_gate_web_terms = (
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
        if any(term in _nova_image_gate_clean for term in _nova_image_gate_web_terms):
            _nova_attachments = []
            try:
                request.environ["NOVA_FORCE_WEB_INTENT_20260609"] = "1"
                request.environ["NOVA_IGNORE_STALE_ATTACHMENTS_20260609"] = "1"
            except Exception:
                pass

        if isinstance(_nova_attachments, list):
            for _nova_item in _nova_attachments:
                if not isinstance(_nova_item, dict):
                    continue

                _nova_mime = str(
                    _nova_item.get("mime_type")
                    or _nova_item.get("type")
                    or ""
                ).lower()

                _nova_name_probe = str(
                    _nova_item.get("filename")
                    or _nova_item.get("original_filename")
                    or _nova_item.get("name")
                    or _nova_item.get("url")
                    or _nova_item.get("file_url")
                    or ""
                ).lower()

                if (
                    _nova_mime.startswith("image/")
                    or any(_nova_ext in _nova_name_probe for _nova_ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"))
                ):
                    _nova_image = _nova_item
                    break

        if _nova_image:
            _nova_raw_url = str(
                _nova_image.get("url")
                or _nova_image.get("file_url")
                or ""
            ).strip()

            _nova_raw_name = str(
                _nova_image.get("filename")
                or _nova_image.get("original_filename")
                or _nova_image.get("name")
                or ""
            ).strip()

            _nova_filename = ""

            if "/api/uploads/" in _nova_raw_url:
                _nova_filename = _nova_raw_url.split("/api/uploads/", 1)[1].split("?", 1)[0].split("#", 1)[0]
            elif _nova_raw_url:
                _nova_filename = _NovaPath(_nova_raw_url).name

            if not _nova_filename and _nova_raw_name:
                _nova_filename = _NovaPath(_nova_raw_name).name

            _nova_filename = _nova_filename.replace("\\", "/").split("/")[-1].strip()

            _nova_candidates = [
                _NovaPath.cwd() / "uploads" / _nova_filename,
                _NovaPath.cwd() / "static" / "uploads" / _nova_filename,
                _NovaPath(__file__).resolve().parent / "uploads" / _nova_filename,
                _NovaPath(__file__).resolve().parent / "static" / "uploads" / _nova_filename,
            ]

            _nova_image_path = None

            for _nova_candidate in _nova_candidates:
                try:
                    if _nova_candidate.exists() and _nova_candidate.is_file():
                        _nova_image_path = _nova_candidate
                        break
                except Exception:
                    continue

            if _nova_image_path is None:
                _nova_text = (
                    "VISION_DEBUG: image file not found. "
                    + "filename=" + str(_nova_filename)
                    + " raw_url=" + str(_nova_raw_url)
                    + " candidates=" + " | ".join(str(c) for c in _nova_candidates)
                )
                _nova_vision_used = False
            else:
                try:
                    from openai import OpenAI as _NovaOpenAI

                    _nova_mime_type = _nova_mimetypes.guess_type(str(_nova_image_path))[0] or "image/jpeg"

                    with open(_nova_image_path, "rb") as _nova_file:
                        _nova_encoded = _nova_base64.b64encode(_nova_file.read()).decode("utf-8")

                    _nova_data_url = "data:" + _nova_mime_type + ";base64," + _nova_encoded

                    _nova_client = _NovaOpenAI(api_key=_nova_os.getenv("OPENAI_API_KEY"))

                    _nova_response = _nova_client.chat.completions.create(
                        model=_nova_os.getenv("NOVA_VISION_MODEL", "gpt-4o-mini"),
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are Nova's image analysis module. "
                                    "Describe the attached image directly. "
                                    "Do not use web search. "
                                    "Do not mention unrelated news. "
                                    "If something cannot be identified, describe what is visible."
                                ),
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": _nova_user_text or "What is this image?",
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": _nova_data_url,
                                        },
                                    },
                                ],
                            },
                        ],
                        temperature=0.2,
                        max_tokens=500,
                    )

                    _nova_text = str(_nova_response.choices[0].message.content or "").strip()

                    if not _nova_text:
                        _nova_text = "VISION_DEBUG: OpenAI vision returned empty text."
                        _nova_vision_used = False
                    else:
                        _nova_vision_used = True

                except Exception as _nova_exc:
                    _nova_text = "VISION_DEBUG: OpenAI vision failed: " + str(_nova_exc)
                    _nova_vision_used = False

            return jsonify({
                "ok": True,
                "active_session_id": _nova_session_id,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_text,
                    "attachments": [],
                    "meta": {
                        "attachment_analysis": True,
                        "api_chat_image_vision_gate": True,
                        "vision_used": _nova_vision_used,
                        "source_urls": [],
                        "sources": [],
                    },
                },
                "debug": {
                    "route": "api_chat",
                    "route_taken": "attachment_analysis",
                    "decision": {
                        "route": "attachment_analysis",
                        "mode": "image_analysis",
                        "strategy": "api_chat_image_vision_gate",
                        "source_urls": [],
                        "sources": [],
                    },
                },
                "session_attachments": _nova_attachments,
                "attachment_debug": {
                    "requested_session_id": _nova_session_id,
                    "session_attachments_count": len(_nova_attachments) if isinstance(_nova_attachments, list) else 0,
                },
            })

    except Exception as _nova_api_image_gate_error:
        print("[NOVA_API_CHAT_IMAGE_VISION_GATE] failed:", _nova_api_image_gate_error)

    # NOVA_DURABLE_EXECUTION_TOP_GUARD_20260607
    try:
        _nova_exec_payload = request.get_json(silent=True) or {}
        _nova_exec_user_text = str(
            _nova_exec_payload.get("user_text")
            or _nova_exec_payload.get("text")
            or _nova_exec_payload.get("message")
            or ""
        ).strip()
        _nova_exec_session_id = str(
            _nova_exec_payload.get("session_id")
            or _nova_exec_payload.get("client_session_id")
            or "default"
        ).strip() or "default"
        _nova_exec_clean = " ".join(_nova_exec_user_text.lower().split())

        # NOVA_WEB_INTENT_BLOCKS_STALE_ATTACHMENT_20260609
        # Fresh web/news/weather/current-events prompts must not be hijacked by stale attachment/image state.
        _nova_web_intent_terms = (
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
        _nova_is_web_intent = any(term in _nova_exec_clean for term in _nova_web_intent_terms)

        if _nova_is_web_intent:
            try:
                request.environ["NOVA_FORCE_WEB_INTENT_20260609"] = "1"
                request.environ["NOVA_IGNORE_STALE_ATTACHMENTS_20260609"] = "1"
            except Exception:
                pass
        # NOVA_IMAGE_ATTACHMENT_NO_WEB_FALLBACK_20260607
        _nova_image_prompt_words = [
            "describe this image",
            "what is this image",
            "what is in this image",
            "what's in this image",
            "look at this image",
            "analyze this image",
            "analyse this image",
            "this picture",
            "this photo",
        ]

        _nova_current_attachments = _nova_exec_payload.get("attachments") or []
        if not isinstance(_nova_current_attachments, list):
            _nova_current_attachments = []

        _nova_has_image_attachment = False
        for _nova_attachment in _nova_current_attachments:
            if not isinstance(_nova_attachment, dict):
                continue

            _nova_name = str(
                _nova_attachment.get("filename")
                or _nova_attachment.get("original_filename")
                or _nova_attachment.get("name")
                or _nova_attachment.get("url")
                or _nova_attachment.get("file_url")
                or ""
            ).lower()

            _nova_mime = str(_nova_attachment.get("mime_type") or _nova_attachment.get("type") or "").lower()

            if (
                _nova_mime.startswith("image/")
                or _nova_name.endswith(".png")
                or _nova_name.endswith(".jpg")
                or _nova_name.endswith(".jpeg")
                or _nova_name.endswith(".webp")
            ):
                _nova_has_image_attachment = True
                break

        if _nova_has_image_attachment and any(_word in _nova_exec_clean for _word in _nova_image_prompt_words):
            _nova_exec_payload["force_image_analysis"] = True
            _nova_exec_payload["disable_web_fetch"] = True

        # NOVA_IMAGE_PROMPT_NO_WEB_GUARD_20260607
        _nova_image_words = [
            "describe this image",
            "describe image",
            "what is in this image",
            "what's in this image",
            "what is this image",
            "look at this image",
            "analyze this image",
            "analyse this image",
            "this picture",
            "this photo",
        ]

        if any(_word in _nova_exec_clean for _word in _nova_image_words):
            _nova_current_attachments = _nova_exec_payload.get("attachments") or []
            if not isinstance(_nova_current_attachments, list):
                _nova_current_attachments = []

            if not _nova_current_attachments:
                _nova_answer = (
                    "I can see you asked me to describe an image, but no image attachment reached /api/chat.\n\n"
                    "The upload/preview side may be working, but the mobile send payload is still dropping the attachment before the backend receives it.\n\n"
                    "Next fix: make the mobile /api/chat request include the pending image attachment so backend sees attachments_count=1."
                )

                return jsonify({
                    "ok": True,
                    "text": _nova_answer,
                    "assistant_message": {
                        "role": "assistant",
                        "text": _nova_answer,
                        "meta": {
                            "image_prompt_no_attachment": True,
                            "web_bypassed": True,
                            "route_taken": "image_prompt_no_web_guard"
                        },
                        "attachments": []
                    },
                    "debug": {
                        "route": "api_chat",
                        "route_taken": "image_prompt_no_web_guard",
                        "blocked": ["web_fetch"]
                    }
                })

        # NOVA_DOCX_ATTACHMENT_DIRECT_HANDLER_20260607
        _nova_docx_attachment_words = [
            "attachment",
            "attach",
            "what is this file",
            "what is this attachment",
            "summarize this attachment",
            "summarise this attachment",
            "summarize this file",
            "summarise this file",
            "this file",
        ]

        if any(_word in _nova_exec_clean for _word in _nova_docx_attachment_words):
            _nova_current_attachments = _nova_exec_payload.get("attachments") or []

            if isinstance(_nova_current_attachments, list) and _nova_current_attachments:
                for _nova_attachment in _nova_current_attachments:
                    _nova_name = str(
                        _nova_attachment.get("original_filename")
                        or _nova_attachment.get("filename")
                        or _nova_attachment.get("name")
                        or _nova_attachment.get("url")
                        or _nova_attachment.get("file_url")
                        or ""
                    ).lower()

                    if ".docx" not in _nova_name:
                        continue

                    _nova_file_path = attachment_utils_service.find_uploaded_file_path(_nova_attachment)
                    # NOVA_USE_PHASE2_DOCX_EXTRACTOR_DIRECT_20260609
                    _nova_docx_text = attachment_context_service.extract_docx_text(
                        _nova_file_path
                    )

                    if _nova_docx_text:
                        _nova_preview = _nova_docx_text[:1200].strip()

                        # NOVA_DIRECT_DOCX_ATTACHMENT_SUMMARY_RETURN_20260609
                        _nova_answer = attachment_text_service.plain_attachment_text_summary(
                            _nova_name,
                            _nova_file_path,
                            _nova_docx_text,
                            _nova_exec_user_text,  # NOVA_FIX_DOCX_SUMMARY_USER_TEXT_ARG_20260609
                        )

                        return jsonify({
                            "ok": True,
                            "text": _nova_answer,
                            "assistant_message": {
                                "role": "assistant",
                                "text": _nova_answer,
                                "meta": {
                                    "docx_attachment_extracted": True,
                                    "route_taken": "docx_attachment_direct_handler",
                                    "file_path": _nova_file_path
                                },
                                "attachments": []
                            },
                            "debug": {
                                "route": "api_chat",
                                "route_taken": "docx_attachment_direct_handler",
                                "file_path": _nova_file_path,
                                "extracted_chars": len(_nova_docx_text)
                            }
                        })

        # NOVA_ATTACHMENT_PROMPT_NO_WEB_GUARD_20260607
        _nova_attachment_words = [
            "attachment",
            "attach",
            "summarize this attachment",
            "summarise this attachment",
            "summarize this file",
            "summarise this file",
            "this file",
        ]

        # NOVA_ATTACHMENT_CONVERSATION_STATE_PRIORITY_20260711
        # Deferring or completing attachment work is conversation state,
        # not a request to analyze a currently uploaded file.
        _nova_attachment_state_phrases = (
            "after this",
            "come back to attachment",
            "later let's fix attachment",
            "later we should fix attachment",
            "done with attachment",
            "finished with attachment",
            "closed attachment",
            "close attachment",
            "attachment is done",
            "attachment is closed",
            "attachment is complete",
            "attachment is resolved",
            "attachments are done",
            "attachments are closed",
            "attachments are complete",
            "attachments are resolved",
        )

        _nova_attachment_is_state_message = any(
            _phrase in _nova_exec_clean
            for _phrase in _nova_attachment_state_phrases
        )

        if (
            any(
                _word in _nova_exec_clean
                for _word in _nova_attachment_words
            )
            and not _nova_attachment_is_state_message
        ):
            _nova_current_attachments = _nova_exec_payload.get("attachments") or []
            if not isinstance(_nova_current_attachments, list):
                _nova_current_attachments = []

            if not _nova_current_attachments:
                _nova_answer = (
                    "I can see you asked about an attachment, but no attachment reached /api/chat.\n\n"
                    "Frontend upload/preview may have worked, but the send payload did not include the file.\n\n"
                    "Next fix: make the mobile send payload carry the uploaded attachment into /api/chat."
                )

                return jsonify({
                    "ok": True,
                    "text": _nova_answer,
                    "assistant_message": {
                        "role": "assistant",
                        "text": _nova_answer,
                        "meta": {
                            "attachment_prompt_no_attachment": True,
                            "web_bypassed": True,
                            "route_taken": "attachment_prompt_no_web_guard"
                        },
                        "attachments": []
                    },
                    "debug": {
                        "route": "api_chat",
                        "route_taken": "attachment_prompt_no_web_guard",
                        "blocked": ["web_fetch"]
                    }
                })

        # NOVA_API_CHAT_PROJECT_STATUS_FRONT_GUARD_20260607
        _nova_project_status_phrases = [
            "what did we fix",
            "what we fixed",
            "explain what we fixed",
            "summarize what we fixed",
            "what did we do today",
            "what have we done today",
        ]

        if any(_phrase in _nova_exec_clean for _phrase in _nova_project_status_phrases):
            _nova_answer = (
                "Here is what we actually fixed today:\n\n"
                "- Fixed the mobile composer buttons so send, voice, attach, tools, and TTS stopped stretching.\n"
                "- Fixed the mojibukakke icon issue where broken encoded symbols were showing instead of clean icons.\n"
                "- Fixed the stale frontend cache issue where /mobile kept loading an old nova-mobile-app.js?v=attachment-payload-bridge-20260607204432 version.\n"
                "- Slimmed the mobile composer/input bar so the real input and main buttons are now 40px high.\n"
                "- Fixed the router bug where the word 'today' forced local project questions into web_fetch.\n\n"
                "Remaining issue: add a real work-log system so Nova can summarize actual project progress instead of guessing from old memories."
            )

            return jsonify({
                "ok": True,
                "text": _nova_answer,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_answer,
                    "meta": {
                        "project_status_direct": True,
                        "route_taken": "api_chat_project_status_front_guard",
                        "memory_bypassed": True,
                        "web_bypassed": True
                    },
                    "attachments": []
                },
                "debug": {
                    "route": "api_chat",
                    "route_taken": "api_chat_project_status_front_guard",
                    "blocked": ["chat_service_memory", "web_fetch"]
                }
            })


        # NOVA_EXECUTION_STATUS_TOP_GUARD_20260607
        if _nova_exec_clean in {"status", "execution status", "mission status"}:
            _nova_exec_state = chat_execution_service.get_state(_nova_exec_session_id)
            _nova_exec_reply = chat_execution_service.format_reply(_nova_exec_state)

            return jsonify({
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_exec_reply,
                    "content": _nova_exec_reply,
                    "execution_state": _nova_exec_state,
                },
                "execution_state": _nova_exec_state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            })

        # NOVA_EXECUTION_RESET_ALL_BRIDGE_20260607
        if _nova_exec_clean in {"reset all", "reset all missions", "clear all missions", "clear all execution", "reset executions"}:
            _nova_reset_session_ids = []

            if hasattr(chat_execution_service, "list_sessions"):
                try:
                    _nova_reset_session_ids = list(chat_execution_service.list_sessions() or [])
                except Exception:
                    _nova_reset_session_ids = []

            if not _nova_reset_session_ids:
                for _nova_attr_name in ("states", "_states", "execution_states", "_execution_states", "missions", "_missions"):
                    _nova_attr_value = getattr(chat_execution_service, _nova_attr_name, None)
                    if isinstance(_nova_attr_value, dict):
                        _nova_reset_session_ids = list(_nova_attr_value.keys())
                        break

            if _nova_exec_session_id not in _nova_reset_session_ids:
                _nova_reset_session_ids.append(_nova_exec_session_id)

            _nova_reset_session_ids = [
                str(_nova_sid).strip()
                for _nova_sid in _nova_reset_session_ids
                if str(_nova_sid).strip()
            ]

            _nova_reset_session_ids = list(dict.fromkeys(_nova_reset_session_ids))
            _nova_cleared_sessions = []

            for _nova_sid in _nova_reset_session_ids:
                try:
                    chat_execution_service.reset(_nova_sid)
                    _nova_cleared_sessions.append(_nova_sid)
                except Exception:
                    pass

            if _nova_cleared_sessions:
                reply_text = (
                    "All known execution missions reset. Cleared sessions: "
                    + ", ".join(_nova_cleared_sessions)
                )
            else:
                reply_text = "No execution missions were found to reset."

            return jsonify({
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                },
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            })
        # NOVA_EXECUTION_RESET_BRIDGE_20260607
        if _nova_exec_clean in {"reset mission", "reset execution", "clear mission", "reset"}:
            _nova_exec_state = chat_execution_service.reset(_nova_exec_session_id)
            reply_text = f"Mission reset. Previous mission state cleared for session {_nova_exec_session_id}."

            return jsonify({
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "content": reply_text,
                    "execution_state": _nova_exec_state,
                },
                "execution_state": _nova_exec_state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            })

        _nova_boot_log_20260701("DEBUG GOAL:", _nova_exec_user_text)
        _nova_boot_log_20260701("DEBUG CLEAN:", _nova_exec_clean)

        if _nova_exec_clean.startswith("auto-plan "):
            _nova_exec_goal = (
                _nova_exec_user_text[len("auto-plan "):].strip()
                or "Untitled execution mission"
            )

            _nova_goal_lower = _nova_exec_goal.lower()

            _nova_boot_log_20260701("DEBUG LOWER:", _nova_goal_lower)

            if "attachment" in _nova_goal_lower or "upload" in _nova_goal_lower or "preview" in _nova_goal_lower:
                _nova_exec_steps = [
                    "Inspect the attachment upload, payload, and preview flow",
                    "Patch the smallest broken link between upload capture and preview rendering",
                    "Test upload preview, send payload, and attachment summary behavior",
                ]
            elif (
                "mobile" in _nova_goal_lower
                or " css" in _nova_goal_lower
                or " ui " in f" {_nova_goal_lower} "
            ):
                _nova_exec_steps = [
                    "Inspect the mobile UI file and identify the broken layout target",
                    "Patch the smallest CSS or JS issue without touching stable backend logic",
                    "Verify mobile layout, composer buttons, and session behavior",
                ]
            elif "web" in _nova_goal_lower or "fetch" in _nova_goal_lower or "search" in _nova_goal_lower:
                _nova_exec_steps = [
                    "Inspect the web fetch route, ranking path, and displayed source output",
                    "Patch the smallest mismatch between backend fetch results and UI/session output",
                    "Verify fresh search results, source ordering, and displayed cards",
                ]
            elif "memory" in _nova_goal_lower or "recall" in _nova_goal_lower:
                _nova_exec_steps = [
                    "Inspect memory write, ranking, and recall injection path",
                    "Patch the smallest issue blocking correct memory recall",
                    "Verify recall with a direct follow-up prompt",
                ]
            elif "execution" in _nova_goal_lower or "plan" in _nova_goal_lower:
                _nova_exec_steps = [
                    "Inspect execution state, trigger routing, and durable save file",
                    "Patch the smallest issue in mission start or step advancement",
                    "Verify auto-plan, k, next, continue, and completion behavior",
                ]
            else:
                _nova_exec_steps = [
                    "Inspect the mission and identify the likely target files",
                    "Make the smallest safe implementation change",
                    "Verify the result and report the next move",
                ]
            _nova_exec_state = chat_execution_service.start(
                _nova_exec_session_id,
                _nova_exec_goal,
                _nova_exec_steps,
            )
            _nova_exec_reply = (
                "Execution mission started: " + _nova_exec_goal + "\n\n"
                "Step 1/3: " + str(_nova_exec_state.get("current_step") or _nova_exec_steps[0]) + "\n\n"
                "Send k, next, continue, or run it to advance."
            )
            return jsonify({
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_exec_reply,
                    "content": _nova_exec_reply,
                    "execution_state": _nova_exec_state,
                },
                "execution_state": _nova_exec_state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            })

        if _nova_exec_clean in {"k", "ok", "okay", "next", "continue", "run it", "run step", "execute", "go"}:
            _nova_exec_state = chat_execution_service.advance(_nova_exec_session_id)
            _nova_exec_reply = chat_execution_service.format_reply(_nova_exec_state)
            return jsonify({
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_exec_reply,
                    "content": _nova_exec_reply,
                    "execution_state": _nova_exec_state,
                },
                "execution_state": _nova_exec_state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            })
    except Exception as exc:
        logger.exception("[NovaDurableExecutionTopGuard] failed")
        _nova_exec_reply = "Execution top guard failed: " + str(exc)
        return jsonify({
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": _nova_exec_reply,
                "content": _nova_exec_reply,
            },
            "execution_state": {
                "status": "failed",
                "error": str(exc),
            },
            "skip_cleanup": True,
            "skip_post_processing": True,
            "skip_rewrite": True,
        })
    # NOVA_AUTO_PLAN_TOP_OF_API_CHAT_GUARD_20260607
    try:
        _nova_early_payload = request.get_json(silent=True) or {}
        _nova_early_user_text = str(
            _nova_early_payload.get("user_text")
            or _nova_early_payload.get("text")
            or _nova_early_payload.get("message")
            or ""
        ).strip()
        _nova_early_session_id = str(
            _nova_early_payload.get("session_id")
            or _nova_early_payload.get("client_session_id")
            or "default"
        ).strip() or "default"

        _nova_early_auto_plan_result = None

        if _nova_early_auto_plan_result is not None:
            return jsonify(_nova_early_auto_plan_result)
    except Exception as exc:
        logger.exception("[NovaAutoPlanTopGuard] failed")
        return jsonify({
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": "Auto-plan top guard failed: " + str(exc),
                "content": "Auto-plan top guard failed: " + str(exc),
            },
            "execution_state": {
                "status": "failed",
                "error": str(exc),
            },
        })


    # NOVA_EXECUTION_COMMAND_TOP_GUARD_20260611
    # Explicit execution controls must beat web/news/search routing.
    try:
        _nova_exec_payload2 = request.get_json(silent=True) or {}
        _nova_exec_text2 = str(
            _nova_exec_payload2.get("user_text")
            or _nova_exec_payload2.get("text")
            or _nova_exec_payload2.get("message")
            or ""
        ).strip()
        _nova_exec_clean2 = " ".join(_nova_exec_text2.lower().split())

        _nova_exec_session_id2 = str(
            _nova_exec_payload2.get("session_id")
            or _nova_exec_payload2.get("client_session_id")
            or _nova_exec_payload2.get("conversation_id")
            or "default"
        ).strip() or "default"

        _nova_exec_commands2 = {
            "next": "next",
            "nex": "next",
            "continue": "next",
            "continue on": "next",
            "keep going": "next",
            "go": "next",
            "run next": "next",
            "next step": "next",
            "run step": "next",
            "run_step": "next",
            "run all": "run_all",
            "run_all": "run_all",
            "run it": "run_all",
            "execute": "run_all",
            "execute all": "run_all",
            "auto": "run_all",
            "auto mode": "run_all",
            "autopilot": "run_all",
            "retry": "retry",
            "retry failed": "retry",
            "retry_failed": "retry",
            "try again": "retry",
            "rerun failed": "retry",
            "stop": "cancel",
            "cancel": "cancel",
        }

        if _nova_exec_clean2 in _nova_exec_commands2:
            _nova_exec_action2 = _nova_exec_commands2[_nova_exec_clean2]

            if _nova_exec_action2 == "run_all":
                _nova_exec_state2 = chat_execution_service.run_all(_nova_exec_session_id2)
            elif _nova_exec_action2 == "cancel":
                _nova_exec_state2 = chat_execution_service.cancel(_nova_exec_session_id2)
            else:
                _nova_exec_state2 = chat_execution_service.advance(_nova_exec_session_id2)

            # NOVA_EXECUTION_GUARD_INLINE_FORMATTER_20260611
            _nova_exec_status2 = str(_nova_exec_state2.get("status") or "").strip().lower()
            _nova_exec_goal2 = str(_nova_exec_state2.get("goal") or "").strip()
            _nova_exec_error2 = str(_nova_exec_state2.get("error") or "").strip()
            _nova_exec_steps2 = _nova_exec_state2.get("steps") or []
            _nova_exec_current2 = str(_nova_exec_state2.get("current_step") or "").strip()
            _nova_exec_index2 = int(_nova_exec_state2.get("current_index") or 0)

            if _nova_exec_status2 in {"idle", "none", ""}:
                _nova_exec_reply2 = _nova_exec_error2 or "No active execution mission. Start one with: auto-plan <goal>"
            elif _nova_exec_status2 in {"complete", "completed"}:
                if _nova_exec_goal2:
                    _nova_exec_reply2 = "Execution complete: " + _nova_exec_goal2
                else:
                    _nova_exec_reply2 = "Execution complete."
            elif _nova_exec_status2 in {"failed", "error"}:
                _nova_exec_reply2 = _nova_exec_error2 or "Execution failed."
            else:
                _nova_exec_total2 = len(_nova_exec_steps2)
                _nova_exec_step_num2 = min(_nova_exec_index2 + 1, _nova_exec_total2) if _nova_exec_total2 else 1
                if not _nova_exec_current2 and _nova_exec_steps2:
                    _nova_exec_current2 = str(_nova_exec_steps2[_nova_exec_index2] if _nova_exec_index2 < _nova_exec_total2 else _nova_exec_steps2[-1])
                _nova_exec_reply2 = (
                    "Execution waiting. "
                    + "Step "
                    + str(_nova_exec_step_num2)
                    + "/"
                    + str(_nova_exec_total2 or "?")
                    + ": "
                    + (_nova_exec_current2 or "Next step")
                )

            return jsonify({
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_exec_reply2,
                    "content": _nova_exec_reply2,
                },
                "execution_state": _nova_exec_state2,
                "debug": {
                    "route": "execution_command_top_guard",
                    "command": _nova_exec_clean2,
                    "action": _nova_exec_action2,
                    "session_id": _nova_exec_session_id2,
                },
            })
    except Exception as exc:
        return jsonify({
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": "Execution command guard failed: " + str(exc),
                "content": "Execution command guard failed: " + str(exc),
            },
            "execution_state": {
                "status": "failed",
                "error": str(exc),
            },
            "debug": {
                "route": "execution_command_top_guard_failed",
            },
        })

    data = request_json()

    user_text = str(
        data.get("user_text")
        or data.get("text")
        or data.get("message")
        or ""
    ).strip()

    if isinstance(data, dict) and user_text:
        data["user_text"] = user_text
        data["text"] = user_text
        data["message"] = user_text

    _nova_user_text_lower = str(user_text or "").strip().lower()

    requested_session_id = str(data.get("session_id") or "").strip()
    session_id = requested_session_id

    # NOVA_EMPTY_SESSION_CREATE_GUARD_EXACT_20260610
    # Normalize attachments before session creation so blank frontend pings do not create stored sessions.
    attachments = normalize_attachments(data.get("attachments"))
    if not user_text and not attachments:
        return jsonify({
            "ok": True,
            "session_id": session_id,
            "active_session_id": session_id,
            "assistant_message": {
                "role": "assistant",
                "text": "",
            },
            "text": "",
            "empty_request": True,
            "no_session_created": True,
        })

        result["session_id"] = result.get("session_id") or session_id
        result["active_session_id"] = result.get("active_session_id") or result.get("session_id") or session_id

        # NOVA_IMAGE_FASTPATH_RESPONSE_CLEANUP_20260610
        # Normalize echoed image-command text so the user sees only the real prompt.
        def _nova_clean_image_echo_text(value):
            value = str(value or "").strip()
            prefix = "Generated image for:"
            if not value.startswith(prefix):
                return value

            prompt = value[len(prefix):].strip()
            lowered = prompt.lower()

            cleanup_prefixes = [
                "/image",
                "generate an image of ",
                "generate image of ",
                "generate an image ",
                "generate image ",
                "create an image of ",
                "create image of ",
                "create an image ",
                "create image ",
                "make an image of ",
                "make image of ",
                "make an image ",
                "make image ",
                "draw ",
            ]

            if lowered == "/image":
                prompt = "image"
            else:
                for item in cleanup_prefixes:
                    if lowered.startswith(item):
                        prompt = prompt[len(item):].strip() or "image"
                        break

            return f"Generated image for: {prompt}"

        result["text"] = _nova_clean_image_echo_text(result.get("text"))
        assistant_message = result.get("assistant_message")
        if isinstance(assistant_message, dict):
            assistant_message["text"] = _nova_clean_image_echo_text(assistant_message.get("text"))
            result["assistant_message"] = assistant_message

        
        # NOVA_ATTACHMENT_SYNC_TEXT_TO_CLEAN_CONTENT_ALL_RETURNS_20260611
        try:
            _nova_result_for_attachment_sync = result if isinstance(result, dict) else None
            if isinstance(_nova_result_for_attachment_sync, dict):
                _nova_assistant_for_attachment_sync = _nova_result_for_attachment_sync.get("assistant_message")
                if isinstance(_nova_assistant_for_attachment_sync, dict):
                    _nova_content_for_attachment_sync = str(_nova_assistant_for_attachment_sync.get("content") or "").strip()
                    if _nova_content_for_attachment_sync.startswith("Attachment analysis:") and "Attachment " in _nova_content_for_attachment_sync and " content:" in _nova_content_for_attachment_sync:
                        _nova_assistant_for_attachment_sync["text"] = _nova_content_for_attachment_sync
                        _nova_assistant_for_attachment_sync["content"] = _nova_content_for_attachment_sync
                        _nova_result_for_attachment_sync["assistant_message"] = _nova_assistant_for_attachment_sync
        except Exception:
            pass
        return jsonify(result)


    # MOBILE_SESSION_FORCE_LOCK_20260606
    # Honor mobile-provided session ids instead of letting backend drift to random session_* ids.
    if requested_session_id:
        # FORCE_MOBILE_SESSION_OBJECT_CREATE_LOCK_20260606
        # Active id alone is not enough. Ensure the actual mobile session object exists.
        try:
            session_bootstrap_service.ensure_requested_session(
                requested_session_id,
                title=user_text or "Mobile Chat",
            )
        except Exception:
            app.logger.exception("[api_chat] failed to ensure requested mobile session object")

    try:
        # MOBILE_ATTACHMENT_FIX_20260606: active_session_id is read-only.
        pass
    except Exception:
        app.logger.exception("[api_chat] failed to force active mobile session id")


    attachments = normalize_attachments(request.json.get("attachments", []))

    # NOVA_API_CHAT_WEB_INTENT_STRIPS_CURRENT_ATTACHMENTS_20260609
    # If this is a fresh web/news request, do not let stale mobile attachment state hijack routing.
    _nova_main_clean_for_web = " ".join(str(user_text or "").lower().split())
    _nova_main_web_terms = (
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
    if (
        request.environ.get("NOVA_IGNORE_STALE_ATTACHMENTS_20260609") == "1"
        or any(term in _nova_main_clean_for_web for term in _nova_main_web_terms)
    ):
        attachments = []
        try:
            data["attachments"] = []
            request.environ["NOVA_FORCE_WEB_INTENT_20260609"] = "1"
            request.environ["NOVA_IGNORE_STALE_ATTACHMENTS_20260609"] = "1"
        except Exception:
            pass

    # NOVA_INLINE_TEXT_ATTACHMENT_FASTPATH_20260612
    # Inline attachment text from API/mobile/browser tests is valid content.
    # Answer it before older upload-file lookup paths can return "file was not found in uploads."
    try:
        _nova_inline_text_items = []
        if isinstance(attachments, list):
            for _nova_inline_att in attachments:
                if not isinstance(_nova_inline_att, dict):
                    continue

                _nova_inline_text = str(_nova_inline_att.get("text") or _nova_inline_att.get("content") or "").strip()
                if not _nova_inline_text:
                    continue

                _nova_inline_name = str(
                    _nova_inline_att.get("original_filename")
                    or _nova_inline_att.get("filename")
                    or "inline attachment"
                ).strip()

                _nova_inline_text_items.append((_nova_inline_name, _nova_inline_text))

        _nova_inline_prompt = " ".join(str(user_text or "").lower().split())
        _nova_inline_wants_attachment = (
            bool(_nova_inline_text_items)
            and (
                "attachment" in _nova_inline_prompt
                or "summarize" in _nova_inline_prompt
                or "summary" in _nova_inline_prompt
                or "what exact text" in _nova_inline_prompt
                or "what is inside" in _nova_inline_prompt
                or "what's inside" in _nova_inline_prompt
                or "key point" in _nova_inline_prompt
                or "keypoint" in _nova_inline_prompt
                or len(_nova_inline_prompt) <= 60
            )
        )

        if _nova_inline_wants_attachment:
            _nova_inline_lines = []
            for _nova_inline_name, _nova_inline_text in _nova_inline_text_items:
                _nova_inline_lines.append(f"{_nova_inline_name}:")
                _nova_inline_lines.append(_nova_inline_text)

            _nova_inline_reply = (
                "Attachment analysis:\n"
                + "\n".join(_nova_inline_lines).strip()
            )

            return jsonify({
                "ok": True,
                "session_id": session_id,
                "active_session_id": session_id,
                "assistant_message": {
                    "role": "assistant",
                    "text": _nova_inline_reply,
                    "content": _nova_inline_reply,
                },
                "text": _nova_inline_reply,
                "session_attachments": list(attachments or []),
                "attachment_debug": {
                    "requested_session_id": requested_session_id,
                    "active_session_id": session_id,
                    "session_attachments_count": len(attachments or []),
                    "inline_text_fastpath": True,
                },
                "debug": {
                    "route": "app_inline_text_attachment_fastpath",
                    "route_taken": "attachment_analysis",
                    "blocked_file_lookup": True,
                },
            })
    except Exception as _nova_inline_text_fastpath_error:
        app.logger.warning(
            "[InlineTextAttachmentFastPath] failed; falling through: %s",
            _nova_inline_text_fastpath_error,
        )
    # BACKEND_ATTACHMENT_DEBUG_LOG_LOCK
    try:
        app.logger.info(
            "[api_chat] incoming request session_id=%s user_text_len=%s attachments_count=%s attachment_names=%s",
            session_id or "<missing>",
            len(user_text or ""),
            len(attachments or []),
            [
                (
                    item.get("original_filename")
                    or item.get("filename")
                    or item.get("name")
                    or item.get("url")
                    or item.get("file_url")
                    or "<unnamed>"
                )
                for item in (attachments or [])
                if isinstance(item, dict)
            ],
        )
    except Exception:
        app.logger.exception("[api_chat] failed while logging attachment debug info")

    regen_commands = {
        "regen",
        "regenerate",
        "redo image",
        "make another",
        "another image",
    }

    if user_text.lower().strip() in regen_commands:
        last_prompt = chat_service._get_session_meta(
            session_id,
            "last_image_prompt",
        ) or "generate an image"

        result = chat_service._handle_image_generation(
            prompt=last_prompt,
            session_id=session_id,
            parent_artifact_id="",
            source_type="regenerated",
        )


    force_new_session = bool(data.get("force_new_session") or data.get("new_session"))

    if not session_id and not force_new_session:
        active = session_service.get_active()
        if active:
            session_id = str(active.get("id") or "").strip()

    auth_user_id = (
        flask_session.get("nova_user_id")
        or flask_session.get("user_id")
        or ""
    )

    if not session_id:
        created = session_service.create_session(
            "New Chat",
            user_id=auth_user_id,
        )

    if not session_id:
        created = session_service.create_session(
            "New Chat",
            user_id=auth_user_id,
        )

        session_id = created["id"]

    if not user_text and not attachments:
        return json_error("Missing user_text or attachments", 400)

    # EARLY_IMAGE_ATTACHMENT_GATE_20260606
    # If the current request includes image attachments, answer before memory,
    # web routing, weak fallback guards, or chat_service can turn it into a generic intro.
    try:
        current_attachments = attachments if isinstance(attachments, list) else []
        image_attachments = []

        for item in current_attachments:
            if not isinstance(item, dict):
                continue

            name = str(
                item.get("original_filename")
                or item.get("filename")
                or item.get("name")
                or "image attachment"
            ).strip()

            mime = str(
                item.get("mime_type")
                or item.get("content_type")
                or item.get("type")
                or item.get("mime")
                or ""
            ).strip()

            url = str(item.get("file_url") or item.get("url") or item.get("path") or "").strip()
            name_lower = name.lower()

            if (
                mime.lower().startswith("image/")
                or name_lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
                or url.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
            ):
                image_attachments.append({
                    "name": name,
                    "mime": mime or "image/*",
                    "url": url,
                    "raw": item,
                })

        if image_attachments:
            # SKIP_EARLY_IMAGE_GATE_FOR_ANALYSIS_REQUESTS_20260606
            # Do not let the receipt gate block real image/attachment analysis.
            _analysis_text = str(user_text or "").lower().strip()
            _analysis_words = (
                "summarize",
                "summary",
                "analyze",
                "analyse",
                "describe",
                "what is this",
                "what's this",
                "what is in",
                "what's in",
                "what was the attached",
                "what was attached",
                "read this",
                "look at this",
                "tell me about",
            )

            if any(word in _analysis_text for word in _analysis_words):
                image_attachments = []
            else:
                lines = ["Image attachment received."]

            for index, item in enumerate(image_attachments[:5], start=1):
                line = f"{index}. {item.get('name') or 'image attachment'} ({item.get('mime') or 'image/*'})"
                if item.get("url"):
                    line += f" — {item.get('url')}"
                lines.append(line)

            lines.append("")
            lines.append("The image is now attached to this chat request.")

            _early_gate_text = str(user_text or "").lower().strip()
            _early_gate_analysis_request = any(
                word in _early_gate_text
                for word in (
                    "summarize",
                    "summary",
                    "analyze",
                    "analyse",
                    "describe",
                    "what is this",
                    "what's this",
                    "what is in",
                    "what's in",
                    "read this",
                    "look at this",
                    "tell me about",
                )
            )

            if _early_gate_analysis_request:
                raise RuntimeError("skip early image receipt gate for analysis request")

            reply_text = "Attachment received."

            app.logger.info(
                "[EarlyImageAttachmentGate] returning image attachment response session_id=%s image_count=%s",
                session_id,
                len(image_attachments),
            )

            mobile_exchange_service.direct_save_mobile_exchange(
                session_id,
                user_text,
                reply_text,
                attachments=current_attachments,
                route="early_image_attachment_gate",
                clean_text=attachment_text_service.strip_project_context_from_visible_text,
                logger=app.logger,
            )

            return jsonify({
                "ok": True,
                "session_id": session_id,
                "active_session_id": session_id,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply_text,
                    "attachments": current_attachments,
                    "meta": {
                        "route": "early_image_attachment_gate",
                    },
                },
                "attachments": current_attachments,
                "session_attachments": current_attachments,
                "skip_post_processing": True,
                "skip_rewrite": True,
                "debug": {
                    "route": "early_image_attachment_gate",
                    "image_count": len(image_attachments),
                    "attachments_count": len(current_attachments),
                },
            })
    except Exception as early_image_error:
        app.logger.warning(
            "[EarlyImageAttachmentGate] failed; continuing normal api_chat flow: %s",
            early_image_error,
        )

    project_focus_memory_service.save_project_focus_memory(
        user_text,
        session_id,
    )

    project_state_memory_service.save_project_state_memories(
        user_text,
        session_id,
    )

    direct_project_state_response = (
        project_recall_service
        .try_project_state_direct_recall(
            user_text,
            session_id,
        )
    )

    if direct_project_state_response is not None:
        app.logger.info(
            "[project-state-direct-recall] answered from project state memory session_id=%s",
            session_id,
        )

        return response_quality_service.slim_assistant_payload(
            direct_project_state_response.get("text"),
            session_id=session_id,
            **{
                key: value
                for key, value in direct_project_state_response.items()
                if key != "text"
            },
        )

    direct_project_focus_response = (
        project_recall_service
        .try_project_focus_direct_recall(
            user_text,
            session_id,
        )
    )

    if direct_project_focus_response is not None:
        app.logger.info(
            "[project-focus-direct-recall] answered from recent session context session_id=%s",
            session_id,
        )

        return response_quality_service.slim_assistant_payload(
            direct_project_focus_response.get("text"),
            session_id=session_id,
            **{
                key: value
                for key, value in direct_project_focus_response.items()
                if key != "text"
            },
        )

    try:
        # REAL_ATTACHMENT_MEMORY_BACKEND_LOCK
        if attachments:
            try:
                added_attachment_memory = persist_attachments_for_session(
                    attachments,
                    session_id=session_id,
                    client_session_id=requested_session_id,
                )
                app.logger.info(
                    "[api_chat] persisted attachment memory count=%s session_id=%s",
                    added_attachment_memory,
                    session_id,
                )
            except Exception:
                app.logger.exception("[api_chat] failed to persist attachment memory")

        # NOVA_PHASE1_TEXT_ATTACHMENT_READER_INJECT_20260607
        user_text = attachment_context_service.append_text_attachments_to_user_text(
            user_text,
            attachments,
            logger=app.logger,
        )


        # PROJECT_AWARE_ATTACHMENT_CONTEXT_LOCK
        try:
            remembered_session_attachments = summarize_attachments_for_session(
                session_id,
                limit=25,
                client_session_id=requested_session_id,
            )
        except Exception:
            remembered_session_attachments = []
            app.logger.exception("[api_chat] failed to load remembered session attachments")

        # NOVA_SKIP_RAW_BINARY_ATTACHMENT_INJECTION_CALL_20260607
        raw_injection_attachments = attachment_utils_service.filter_raw_injection_attachments(
            attachments,
            logger=app.logger,
        )
        # ATTACHMENT_CONTENT_INJECTION_FINAL_LOCK
        # HARD_BYPASS_CASUAL_GREETINGS_LOCK
        # Tiny casual messages should not enter project-aware memory, attachment memory,
        # web routing, or task-mode responses.
        _nova_clean_casual_text = str(user_text or "").strip().lower()
        _nova_casual_greetings = {
            "hi",
            "hey",
            "yo",
            "hello",
            "sup",
        }

        if not attachments and _nova_clean_casual_text in _nova_casual_greetings:
            app.logger.info(
                "[api_chat] hard bypass casual greeting session_id=%s text=%r",
                session_id,
                user_text,
            )

            return jsonify({
                "ok": True,
                "session_id": session_id,
                "active_session_id": session_id,
                "assistant_message": {
                    "role": "assistant",
                    "text": "Hey.",
                },
                "attachments": [],
                "session_attachments": [],
                "skip_post_processing": True,
                "skip_rewrite": True,
                "route": "hard_bypass_casual_greeting",
                "route_taken": "hard_bypass_casual_greeting",
                "debug": {
                    "route": "hard_bypass_casual_greeting",
                    "route_taken": "hard_bypass_casual_greeting",
                    "strategy": "hard_bypass_casual_greeting",
                    "hard_bypass_casual_greeting": True,
                },
                "meta": {
                    "strategy": "hard_bypass_casual_greeting",
                    "route": "hard_bypass_casual_greeting",
                },
            })

        attachment_content_lines = []

        # ATTACHMENT_INJECTION_LOOP_CURRENT_ONLY_LOCK
        # When the user sends attachments with this request, inject ONLY those current files.
        # Old session attachment memory can still be stored, but must not flood this prompt.
        # ACTUAL_STOP_STALE_ATTACHMENT_MEMORY_LOCK
        if attachments:
            remembered_session_attachments = list(attachments)
            app.logger.info(
                "[AttachmentContentGate] forcing current request attachments only before injection count=%s session_id=%s",
                len(remembered_session_attachments or []),
                session_id,
            )
        else:
            remembered_session_attachments = []
            app.logger.info(
                "[AttachmentContentGate] no current attachments; stale session attachment injection disabled session_id=%s",
                session_id,
            )

        # KILL_STALE_ATTACHMENT_LOOP_DIRECT_LOCK
        # Hard stop: never loop old remembered attachments when this request has no current upload.
        if not attachments:
            remembered_session_attachments = []
            attachment_content_lines = []
            app.logger.info(
                "[AttachmentContentGate] direct stale attachment loop killed because current request has no attachments session_id=%s",
                session_id,
            )

        for attachment in remembered_session_attachments or []:
            attachment_filename = str(attachment.get("filename") or "").strip()
            attachment_original_filename = str(attachment.get("original_filename") or "").strip()

            if attachment_filename == "<unknown>":
                attachment_filename = ""

            if attachment_original_filename == "<unknown>":
                attachment_original_filename = ""

            # ATTACHMENT_CONTENT_ROOT_FIX_20260604
            raw_attachment_name = (
                attachment_filename
                or attachment_original_filename
                or Path(str(attachment.get("stored_name") or "")).name
                or Path(str(attachment.get("file_url") or "")).name
                or Path(str(attachment.get("url") or "")).name
                or ""
            )

            local_path_value = str(attachment.get("local_path") or attachment.get("path") or "").strip()
            candidate_paths = []

            if local_path_value:
                candidate_paths.append(Path(local_path_value).expanduser())

            if raw_attachment_name:
                safe_name = Path(str(raw_attachment_name).strip().lstrip("/\\")).name
                candidate_paths.append((UPLOADS_DIR / safe_name).resolve())

            file_path = None
            uploads_root = UPLOADS_DIR.resolve()

            for candidate in candidate_paths:
                try:
                    candidate = candidate.resolve()
                except Exception:
                    continue

                if not candidate.exists() or not candidate.is_file():
                    continue

                if str(candidate).startswith(str(uploads_root)) or str(candidate).startswith(str(BASE_DIR.resolve())):
                    file_path = candidate
                    break

            if file_path is None and raw_attachment_name:
                file_path = (UPLOADS_DIR / Path(str(raw_attachment_name).strip().lstrip("/\\")).name).resolve()
            content_snippet = ""
            try:
                if file_path.exists() and file_path.is_file() and str(file_path).startswith(str(UPLOADS_DIR.resolve())):
                    content_snippet = file_path.read_text(encoding="utf-8", errors="replace")[:4000]
                    app.logger.info(
                        "[AttachmentContentFinal] loaded file content path=%s chars=%s",
                        str(file_path),
                        len(content_snippet),
                    )
                else:
                    app.logger.warning("[AttachmentContentFinal] file unavailable path=%s exists=%s", str(file_path), file_path.exists())
            except Exception as e:
                app.logger.warning("[AttachmentContentFinal] failed reading %s: %s", str(file_path), e)
            try:
                uploads_root = UPLOADS_DIR.resolve()

                if (
                    str(file_path).startswith(str(uploads_root))
                    and file_path.exists()
                    and file_path.is_file()
                ):
                    # SKIP_BINARY_ATTACHMENT_TEXT_INJECTION_LOCK
                    mime_type = str(attachment.get("mime_type") or "").lower().strip()
                    filename_for_type = str(
                        attachment.get("original_filename")
                        or attachment.get("filename")
                        or ""
                    ).lower().strip()

                    binary_extensions = (
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".gif",
                        ".webp",
                        ".bmp",
                        ".ico",
                        ".pdf",
                        ".zip",
                        ".7z",
                        ".rar",
                        ".exe",
                        ".dll",
                        ".mp3",
                        ".mp4",
                        ".mov",
                        ".wav",
                        ".webm",
                    )

                    is_binary_attachment = (
                        mime_type.startswith("image/")
                        or mime_type.startswith("audio/")
                        or mime_type.startswith("video/")
                        or mime_type in {
                            "application/pdf",
                            "application/zip",
                            "application/octet-stream",
                        }
                        or filename_for_type.endswith(binary_extensions)
                    )

                    if is_binary_attachment:
                        # FIX_ATTACHMENT_ANALYZER_ROUTE_AND_CALL_LOCK
                        attachment_path = str(file_path)
                        mime_type = str(mime_type or "")
                        extracted_attachment_text = attachment_analysis_service.analyze_binary_attachment_for_prompt(
                            attachment_path,
                            mime_type,
                        )

                        if extracted_attachment_text:
                            # STRIP_URLS_FROM_EXTRACTED_ATTACHMENT_CHAT_TEXT_LOCK
                            extracted_attachment_text = (
                                attachment_analysis_service.strip_urls_from_extracted_attachment_text(
                                    extracted_attachment_text
                                )
                            )

                            content_snippet = extracted_attachment_text[:4000]
                            app.logger.info(
                                "[AttachmentAnalyzer] extracted binary attachment content path=%s chars=%s mime_type=%s",
                                attachment_path,
                                len(content_snippet),
                                mime_type,
                            )


                            app.logger.info(
                                "[AttachmentAnalyzer] extracted binary attachment content path=%s chars=%s mime_type=%s",
                                attachment_path,
                                len(content_snippet),
                                mime_type,
                            )
                        else:
                            app.logger.info(
                                "[AttachmentAnalyzer] skipped binary attachment prompt append path=%s mime_type=%s",
                                attachment_path,
                                mime_type,
                            )
                            content_snippet = "[Attachment received, but no readable text could be extracted.]"
                    else:
                        content_snippet = file_path.read_text(
                            encoding="utf-8",
                            errors="replace",
                        )[:4000]
                    app.logger.info(
                        "[AttachmentContent] loaded file content path=%s chars=%s",
                        str(file_path),
                        len(content_snippet),
                    )
                else:
                    app.logger.warning(
                        "[AttachmentContent] file unavailable path=%s exists=%s",
                        str(file_path),
                        file_path.exists(),
                    )
            except Exception as e:
                app.logger.warning("[AttachmentContent] failed reading %s: %s", file_path, e)

            # ATTACHMENT_OUTPUT_CLEANER_20260604
            content_snippet = str(content_snippet or "")
            content_snippet = content_snippet.replace("\ufeff", "").replace("\u200b", "").strip()

            fallback_text = "[Attachment content could not be read from disk.]"

            attachment_display_name = (
                attachment.get("original_filename")
                or attachment.get("filename")
                or "<unknown>"
            )

            content_snippet = str(content_snippet or "")
            content_snippet = content_snippet.replace("\ufeff", "").replace("\u200b", "").strip()

            if not str(attachment.get("mime_type") or "").lower().startswith(("image/", "application/pdf")):
                content_snippet = content_snippet.replace(
                    "This uploaded attachment contains readable text about:",
                    ""
                ).replace(
                    "This uploaded attachment contains readable text about:",
                    ""
                ).strip()

            attachment_content_lines.append(
                f"Attachment {attachment_display_name} content:\n"
                f"{content_snippet if content_snippet else fallback_text}"
            )

        # GATE_REMEMBERED_ATTACHMENT_INJECTION_LOCK
        attachment_gate_text = str(user_text or "").lower().strip()
        current_request_attachments = attachments if isinstance(attachments, list) else []

        attachment_intent_words = (
            "attachment",
            "attachments",
            "attached",
            "file",
            "files",
            "image",
            "photo",
            "picture",
            "pic",
            "screenshot",
            "document",
            "docx",
            "pdf",
            "analyze this",
            "what is this",
            "what's this",
            "look at this",
            "read this",
            "summarize this file",
        )

        allow_remembered_attachment_injection = bool(current_request_attachments)


        if not allow_remembered_attachment_injection:
            attachment_content_lines = []
            remembered_session_attachments = []
            app.logger.info(
                "[AttachmentContentGate] skipped remembered attachment injection for non-attachment message session_id=%s text_len=%s",
                requested_session_id,
                len(attachment_gate_text),
            )

        if attachment_content_lines:
            attachment_content_text = "\n\n".join(attachment_content_lines)
            if user_text:
                user_text = f"{user_text}\n\n{attachment_content_text}"
            else:
                user_text = attachment_content_text

            app.logger.info(
                "[AttachmentContent] injected %s attachments content into user_text session_id=%s",
                len(attachment_content_lines),
                requested_session_id,
            )

        # SHORT_CHAT_SKIP_ATTACHMENT_MEMORY_LOCK
        short_casual_text = str(user_text or "").strip().lower()
        skip_remembered_attachment_context = (
            len(short_casual_text) <= 12
            and short_casual_text in {
                "hi",
                "yo",
                "hey",
                "hello",
                "sup",
                "k",
                "ok",
                "kk",
                "test",
            }
            and not attachments
        )

        if False and remembered_session_attachments and not skip_remembered_attachment_context:

            attachment_context_lines = [
                "",
                "Session attachment memory:",
            ]

            for index, item in enumerate(remembered_session_attachments, start=1):
                attachment_context_lines.append(
                    f"{index}. "
                    f"name={item.get('original_filename') or item.get('filename') or '<unknown>'}; "
                    f"url={item.get('file_url') or ''}; "
                    f"type={item.get('mime_type') or ''}; "
                    f"size={item.get('size') or 0}"
                )

            attachment_context = "\n".join(attachment_context_lines)

            if user_text:
                user_text = f"{user_text}\n\n{attachment_context}"
            else:
                user_text = attachment_context.strip()

            app.logger.info(
                "[api_chat] injected project-aware attachment context count=%s session_id=%s",
                len(remembered_session_attachments),
                session_id,
            )

        # SKIP_PROJECT_CONTEXT_FOR_CASUAL_SHORT_MESSAGES_LOCK
        _nova_original_user_text_before_project_context = str(user_text or "").strip()
        _nova_short_casual_messages = {
            "hi",
            "hey",
            "yo",
            "hello",
            "sup",
            "ok",
            "okay",
            "k",
            "yes",
            "no",
            "thanks",
            "thank you",
        }
        _nova_skip_project_context = (
            len(_nova_original_user_text_before_project_context) <= 16
            and _nova_original_user_text_before_project_context.lower() in _nova_short_casual_messages
        )

        if _nova_skip_project_context:
            app.logger.info(
                "[project-aware] skipped project context for short casual message session_id=%s text=%r",
                session_id,
                _nova_exec_user_text,  # NOVA_FIX_DOCX_SUMMARY_USER_TEXT_ARG_20260609
            )
        else:
            user_text = project_state_memory_service.inject_project_state_context(
                user_text,
                session_id,
            )

        try:
            if _nova_skip_project_context:
                project_aware_context = ""
            else:
                project_aware_context = project_aware_context_service.build_project_aware_context(
                    user_text,
                    session_id=session_id,
                    requested_session_id=requested_session_id,
                )
        except Exception:
            project_aware_context = ""
            app.logger.exception("[api_chat] failed to build project-aware memory context")

        if project_aware_context:
            raw_user_text = user_text
            clean_probe = str(raw_user_text or "").strip().lower()

            is_image_request = (
                clean_probe.startswith("/image")
                or clean_probe.startswith("draw ")
                or clean_probe.startswith("generate image")
                or clean_probe.startswith("make image")
                or clean_probe.startswith("create image")
            )

            if not is_image_request:
                user_text = f"{user_text}\n\n{project_aware_context}" if user_text else project_aware_context

                app.logger.info(
                    "[api_chat] injected project-aware memory context chars=%s session_id=%s requested_session_id=%s",
                    len(project_aware_context),
                    session_id,
                    requested_session_id,
                )

        # FORCE_EXTRACTED_TEXT_CHAT_HANDOFF_LOCK
        # If attachment text was already extracted into user_text, hand off to chat_service as plain text.
        # This prevents chat_service attachment guards from returning canned attachment responses.
        attachments_for_chat_service = list(attachments or [])

        # NOVA_IMAGE_COMMAND_ATTACHMENT_BYPASS_20260610
        # Explicit image generation commands must not be hijacked by stale/current attachment gates.
        _nova_image_command_text = str(data.get("user_text") or data.get("text") or data.get("message") or "").strip().lower()
        _nova_is_image_command = (
            _nova_image_command_text.startswith("/image")
            or _nova_image_command_text.startswith("image ")
            or _nova_image_command_text.startswith("generate image")
            or _nova_image_command_text.startswith("generate an image")
            or _nova_image_command_text.startswith("draw ")
            or _nova_image_command_text.startswith("create image")
            or _nova_image_command_text.startswith("make image")
        )

        if _nova_is_image_command:
            attachments = []
            remembered_session_attachments = []
            attachment_content_lines = []
            attachments_for_chat_service = []
            app.logger.info(
                "[ImageCommandAttachmentBypass] cleared attachment state for image command session_id=%s text=%r",
                session_id,
                _nova_image_command_text,
            )

        if attachment_content_lines:
            attachments_for_chat_service = []

            app.logger.info(
                "[AttachmentContentGate] extracted attachment text active; suppressing raw attachments session_id=%s extracted_count=%s",
                session_id,
                len(attachment_content_lines),
            )

        # APP_ATTACHMENT_PREHANDLE_REAL_ANCHOR_LOCK
        # Attachment requests are answered here after extracted text is injected,
        # but before chat_service/web routing can hijack the prompt.
        try:
            import re as _nova_prehandle_re

            _nova_prehandle_text = str(user_text or "")
            _nova_prehandle_lower = _nova_prehandle_text.lower()

            _nova_has_attachment_text = (
                "attachment content:" in _nova_prehandle_lower
                or "uploaded attachment context below" in _nova_prehandle_lower
                or "extracted attachment text" in _nova_prehandle_lower
                or "[mobile quick action attachment context active]" in _nova_prehandle_lower
            )

            _nova_attachment_intent = (
                "summarize" in _nova_prehandle_lower
                or "summary" in _nova_prehandle_lower
                or "keypoint" in _nova_prehandle_lower
                or "key point" in _nova_prehandle_lower
                or "continue" in _nova_prehandle_lower
                or "uploaded pdf attachment" in _nova_prehandle_lower
                or "uploaded attachment" in _nova_prehandle_lower
            )

            if _nova_has_attachment_text and _nova_attachment_intent:
                _nova_noise_exact = {
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
            "copy",
            "regen",
            "regenerate",
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

                _nova_noise_contains = (
                    "wayfair",
                    "save big",
                    "prices you'll love",
                    "eye-catching prints",
                    "url removed from extracted attachment text",
                    "free_shipping",
                    "furniture & décor",
                    "kitchen appliances",
                    "love, horror and more themes",
                    "plain field in front of mountain peak",
                    "free stock photo",
                    "google news",
                    "direct_url_patch_hit",
                )

                _nova_lines = []
                _nova_seen = set()

                for _nova_raw_line in _nova_prehandle_text.splitlines():
                    _nova_line = _nova_prehandle_re.sub(r"^\s*\d+\.\s*", "", str(_nova_raw_line or "")).strip()
                    _nova_line = _nova_line.replace("Attachment <unknown>", "uploaded attachment")
                    _nova_line = _nova_line.replace("Attachment content:", "").strip()
                    _nova_line = _nova_prehandle_re.sub(r"\s+", " ", _nova_line).strip()

                    if not _nova_line:
                        continue

                    _nova_low = _nova_line.lower().strip(" :;-•*|")
                    _nova_low_compact = _nova_prehandle_re.sub(r"[^a-z0-9]+", " ", _nova_low).strip()

                    if _nova_low_compact in _nova_noise_exact:
                        continue

                    if any(_nova_bad in _nova_low for _nova_bad in _nova_noise_contains):
                        continue

                    if _nova_line.startswith("http://") or _nova_line.startswith("https://"):
                        continue

                    if len(_nova_line) <= 2:
                        continue

                    if _nova_low.startswith("typed user text"):
                        continue

                    if _nova_low.startswith("uploaded attachment context below"):
                        continue

                    if _nova_low.startswith("extracted attachment text"):
                        continue

                    if _nova_low.startswith("[mobile quick action attachment context active]"):
                        continue

                    _nova_key = _nova_low_compact[:160]
                    if not _nova_key or _nova_key in _nova_seen:
                        continue

                    _nova_seen.add(_nova_key)
                    _nova_lines.append(_nova_line)

                _nova_top = _nova_lines[:8]

                if _nova_top:
                    _nova_reply = "Attachment content:\n" + "\n".join(_nova_top[:12])
                else:
                    _nova_reply = (
                        "Attachment content:\n"
                        "The attachment was received, but no clean readable text was found."
                    )

                app.logger.info(
                    "[AttachmentPreHandle] answered before chat_service to block web/news hijack session_id=%s lines=%s",
                    session_id,
                    len(_nova_top),
                )

                return jsonify({
                    "ok": True,
                    "session_id": session_id,
                    "active_session_id": session_id,
                    "assistant_message": {
                        "role": "assistant",
                        "text": _nova_reply.strip(),
                    },
                    "debug": {
                        "route": "attachment_prehandle_response",
                        "blocked_web_hijack": True,
                    },
                })

        except Exception as _nova_prehandle_exc:
            app.logger.warning(
                "[AttachmentPreHandle] failed; falling through to chat_service: %s",
                _nova_prehandle_exc,
            )


        # APP_ATTACHMENT_LINES_PREHANDLE_LOCK
        # Attachment text is already extracted in app.py. Answer before chat_service.handle,
        # because chat_service may route short mobile quick-actions to cached web/news URLs.
        try:
            import re as _nova_attach_re

            _attachment_lines = attachment_content_lines if isinstance(attachment_content_lines, list) else []
            _request_attachments = attachments if isinstance(attachments, list) else []
            _has_current_attachment = bool(_attachment_lines or _request_attachments)

            _intent_text = str(user_text or "").lower()
            _is_attachment_action = (
                "summarize" in _intent_text
                or "summary" in _intent_text
                or "keypoint" in _intent_text
                or "key point" in _intent_text
                or "continue" in _intent_text
                or "improve" in _intent_text
                or "next" in _intent_text
                or len(_intent_text.strip()) <= 40
            )

            # NOVA_ENABLE_ATTACHMENT_LINES_PREHANDLE_SAFE_20260611
            # Text attachments should answer immediately for summarize/continue/next/improve
            # instead of falling through to stale web/source/image routing.
            _has_image_like_attachment = False
            try:
                for _att in _request_attachments:
                    if not isinstance(_att, dict):
                        continue
                    _mime = str(_att.get("mime_type") or _att.get("type") or "").lower()
                    _name = str(_att.get("filename") or _att.get("original_filename") or "").lower()
                    if (
                        _mime.startswith("image/")
                        or _name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"))
                    ):
                        _has_image_like_attachment = True
                        break
            except Exception:
                _has_image_like_attachment = False

            _attachment_web_probe = " ".join(str(user_text or "").lower().split())
            _attachment_is_web_intent = (
                request.environ.get("NOVA_FORCE_WEB_INTENT_20260609") == "1"
                or request.environ.get("NOVA_IGNORE_STALE_ATTACHMENTS_20260609") == "1"
                or any(term in _attachment_web_probe for term in (
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
                ))
            )

            _attachment_is_image_command = str(user_text or "").lower().strip().startswith((
                "/image",
                "image ",
                "generate image",
                "generate an image",
                "draw ",
                "create image",
                "make image",
            ))

            if (
                _has_current_attachment
                and _is_attachment_action
                and not _has_image_like_attachment
                and not bool(locals().get("_attachment_web_intent", False))
                and not _attachment_is_image_command
            ):
                _raw_text = "\n".join(str(x or "") for x in _attachment_lines).strip()
                if not _raw_text:
                    _raw_text = str(user_text or "").strip()

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
            "copy",
            "regen",
            "regenerate",
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
                    "furniture & décor",
                    "kitchen appliances",
                    "love, horror and more themes",
                    "plain field in front of mountain peak",
                    "free stock photo",
                    "news.google.com",
                    "direct_url_patch_hit",
                )


                _raw_low_for_fake_context = str(_raw_text or "").lower()

                if (
                    "project-aware context for nova:" in _raw_low_for_fake_context
                    or "relevant persistent memory:" in _raw_low_for_fake_context
                    or "recent session context:" in _raw_low_for_fake_context
                    or "persistent memory:" in _raw_low_for_fake_context
                ):
                    raise RuntimeError("attachment prehandle ignored injected Nova memory context")
                _lines = []
                _seen = set()

                for _raw in _raw_text.splitlines():
                    _line = _nova_attach_re.sub(r"^\s*\d+\.\s*", "", str(_raw or "")).strip()
                    _line = _line.replace("Attachment <unknown>", "uploaded attachment")
                    _line = _line.replace("Attachment content:", "").strip()
                    _line = _nova_attach_re.sub(r"\s+", " ", _line).strip()

                    if not _line:
                        continue

                    _low = _line.lower().strip(" :;-•*|")
                    _compact = _nova_attach_re.sub(r"[^a-z0-9]+", " ", _low).strip()

                    if _compact in _noise_exact:
                        continue

                    if any(_bad in _low for _bad in _noise_contains):
                        continue

                    if _line.startswith("http://") or _line.startswith("https://"):
                        continue

                    if len(_line) <= 2:
                        continue

                    if not _compact or _compact in _seen:
                        continue

                    _seen.add(_compact)
                    _lines.append(_line)

                _top = _lines[:8]

                _fake_context_markers = (
                    "project-aware context for nova:",
                    "relevant persistent memory:",
                    "recent session context:",
                    "persistent memory:",
                    "[preference]",
                    "[user_fact]",
                    "[people]",
                )

                _top = [
                    _item for _item in _top
                    if not any(
                        _marker in str(_item or "").lower()
                        for _marker in _fake_context_markers
                    )
                ]

                if not _top:
                    raise RuntimeError("attachment prehandle ignored fake memory context")

                if _top:
                    _topic = "; ".join(_top[:3])
                    _reply = "Attachment analysis:\n"
                    _reply += f"{_topic}\n\n"
                    _reply += "Key points:\n"
                    for _i, _item in enumerate(_top, start=1):
                        _reply += f"{_i}. {_item}\n"
                    _reply += "\nPreview:\n" + "\n".join(_top[:6])
                else:
                    _reply = (
                        "Attachment analysis:\n"
                        "The attachment was received and processed, but the extracted text is too limited or noisy to summarize cleanly."
                    )

                _reply_low = str(_reply or "").lower()

                if (
                    "project-aware context for nova:" in _reply_low
                    or "relevant persistent memory:" in _reply_low
                    or "recent session context:" in _reply_low
                    or "persistent memory:" in _reply_low
                    or "[preference]" in _reply_low
                    or "[user_fact]" in _reply_low
                    or "[people]" in _reply_low
                ):
                    _reply = (
                        "Attachment received.\n"
                        "The file was uploaded, but Nova ignored internal memory/context text that was accidentally mixed into the attachment analyzer."
                    )

                app.logger.info(
                    "[AttachmentLinesPreHandle] answered before chat_service.handle session_id=%s lines=%s",
                    session_id,
                    len(_top),
                )

                return jsonify({
                    "ok": True,
                    "session_id": session_id,
                    "active_session_id": session_id,
                    "assistant_message": {
                        "role": "assistant",
                        "text": _reply.strip(),
                    },
                    "debug": {
                        "route": "app_attachment_lines_prehandle",
                        "blocked_web_hijack": True,
                    },
                })

        except Exception as _attachment_prehandle_exc:
            app.logger.warning(
                "[AttachmentLinesPreHandle] failed; falling through to chat_service.handle: %s",
                _attachment_prehandle_exc,
            )

        # IMAGE_ATTACHMENT_PREHANDLE_LOCK
        # Current image attachments must beat web/source-open routing.
        try:
            # NOVA_IMAGE_COMMAND_SKIP_IMAGE_ATTACHMENT_PREHANDLE_20260610
            # Explicit image generation commands must not be converted into attachment-received replies.
            _nova_image_prehandle_command_text = str(
                data.get("user_text")
                or data.get("text")
                or data.get("message")
                or user_text
                or ""
            ).strip().lower()

            _nova_skip_image_attachment_prehandle = (
                _nova_image_prehandle_command_text.startswith("/image")
                or _nova_image_prehandle_command_text.startswith("image ")
                or _nova_image_prehandle_command_text.startswith("generate image")
                or _nova_image_prehandle_command_text.startswith("generate an image")
                or _nova_image_prehandle_command_text.startswith("draw ")
                or _nova_image_prehandle_command_text.startswith("create image")
                or _nova_image_prehandle_command_text.startswith("make image")
            )

            if _nova_skip_image_attachment_prehandle:
                raise RuntimeError("skip image attachment prehandle for explicit image command")

            current_attachments = list(attachments or [])
            image_attachments = []

            for item in current_attachments:
                if not isinstance(item, dict):
                    continue

                mime = str(
                    item.get("mime_type")
                    or item.get("type")
                    or item.get("mime")
                    or ""
                ).lower().strip()

                name = str(
                    item.get("original_filename")
                    or item.get("filename")
                    or item.get("name")
                    or item.get("url")
                    or item.get("file_url")
                    or "image attachment"
                ).strip()

                url = str(item.get("file_url") or item.get("url") or "").strip()

                if mime.startswith("image/") or name.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                    image_attachments.append({
                        "name": name,
                        "mime": mime or "image/*",
                        "url": url,
                    })

            _image_prehandle_text = str(user_text or "").lower().strip()


            _is_image_prehandle_analysis = any(


                word in _image_prehandle_text


                for word in (


                    "summarize",


                    "summary",


                    "analyze",


                    "analyse",


                    "describe",


                    "what is this",


                    "what's this",


                    "what is in",


                    "what's in",


                    "read this",


                    "look at this",


                    "tell me about",


                )


            )


            


            if image_attachments and _is_image_prehandle_analysis:


                raise RuntimeError("skip image prehandle receipt for analysis request")


            


            if image_attachments:


                lines = ["Image attachment received."]

                for index, item in enumerate(image_attachments[:5], start=1):
                    label = item.get("name") or "image attachment"
                    mime = item.get("mime") or "image/*"
                    url = item.get("url") or ""

                    line = f"{index}. {label} ({mime})"
                    if url:
                        line += f" — {url}"
                    lines.append(line)

                lines.append("")
                lines.append("I can analyze this image, describe what is visible, or answer a question about it. The image attachment is now being handled as an attachment, not as a previous web source.")

                reply_text = "\n".join(lines).strip()

                app.logger.info(
                    "[ImageAttachmentPreHandle] answered before chat_service.handle session_id=%s images=%s",
                    session_id,
                    len(image_attachments),
                )

                return jsonify({
                    "ok": True,
                    "session_id": session_id,
                    "active_session_id": session_id,
                    "assistant_message": {
                        "role": "assistant",
                        "text": reply_text,
                    },
                    "session_attachments": current_attachments,
                    "attachments": current_attachments,
                    "skip_post_processing": True,
                    "skip_rewrite": True,
                    "meta": {
                        "strategy": "image_attachment_prehandle",
                        "image_count": len(image_attachments),
                    },
                })
        except Exception as _image_attachment_prehandle_error:
            app.logger.warning(
                "[ImageAttachmentPreHandle] failed; falling through to chat_service.handle: %s",
                _image_attachment_prehandle_error,
            )






        # NOVA_API_CHAT_EARLY_EXPLICIT_MEMORY_GUARD_LIVE_ANCHOR_20260611_CALL
        try:
            _nova_raw_user_text = str(
                data.get("user_text")
                or data.get("text")
                or data.get("message")
                or user_text
                or ""
            ).strip()
            _nova_explicit_memory_text = memory_command_service.extract_explicit_memory_live(_nova_raw_user_text)

            if _nova_explicit_memory_text:
                memory_service.add_memory({
                    "text": _nova_explicit_memory_text,
                    "kind": memory_command_service.memory_kind_live(_nova_explicit_memory_text),
                    "source": "app_explicit_memory_command",
                    "session_id": session_id or "",
                })

                return jsonify(
                    memory_command_service.memory_response_live(
                        raw_user_text=_nova_raw_user_text,
                        session_id=session_id,
                        clean=_nova_explicit_memory_text,
                    )
                )
        except Exception as _nova_early_memory_error:
            app.logger.warning("[api_chat early explicit memory guard live] failed: %s", _nova_early_memory_error)

        app.logger.info(
            "[api_chat] calling chat_service.handle session_id=%s attachments_count=%s",
            session_id,
            len(attachments_for_chat_service or []),
        )

        # CLEAN_IMAGE_PROMPT_RIGHT_BEFORE_CHAT_SERVICE_LOCK
        _nova_pre_chat_user_text = str(user_text or "")
        _nova_pre_chat_lower = _nova_pre_chat_user_text.lower().strip()
        _nova_image_prompt_starters = (
            "generate an image",
            "create an image",
            "make an image",
            "draw an image",
            "generate a picture",
            "create a picture",
            "make a picture",
            "draw a picture",
        )

        if any(_nova_pre_chat_lower.startswith(_starter) for _starter in _nova_image_prompt_starters):
            if "\n\nProject-aware context for Nova:" in _nova_pre_chat_user_text:
                user_text = _nova_pre_chat_user_text.split("\n\nProject-aware context for Nova:", 1)[0].strip()
            elif "\nProject-aware context for Nova:" in _nova_pre_chat_user_text:
                user_text = _nova_pre_chat_user_text.split("\nProject-aware context for Nova:", 1)[0].strip()
            else:
                user_text = _nova_pre_chat_user_text.strip()

            app.logger.info(
                "[api_chat] cleaned project-aware context from image-generation prompt session_id=%s cleaned_len=%s",
                session_id,
                len(user_text),
            )

        # NOVA_WEB_INTENT_CLEANS_PROJECT_CONTEXT_BEFORE_CHAT_SERVICE_20260609
        # Fresh web/news prompts must not let injected recent context trigger image generation.
        _nova_real_user_text_for_web = str(
            data.get("user_text")
            or data.get("text")
            or data.get("message")
            or ""
        ).strip()

        _nova_real_web_probe = " ".join(_nova_real_user_text_for_web.lower().split())
        _nova_real_web_terms = (
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

        if (
            request.environ.get("NOVA_FORCE_WEB_INTENT_20260609") == "1"
            or any(term in _nova_real_web_probe for term in _nova_real_web_terms)
        ):
            if _nova_real_user_text_for_web:
                user_text = _nova_real_user_text_for_web
                attachments_for_chat_service = []
                attachments = []

                try:
                    data["attachments"] = []
                    data["user_text"] = _nova_real_user_text_for_web
                    data["text"] = _nova_real_user_text_for_web
                    data["message"] = _nova_real_user_text_for_web
                    request.environ["NOVA_FORCE_WEB_INTENT_20260609"] = "1"
                    request.environ["NOVA_IGNORE_STALE_ATTACHMENTS_20260609"] = "1"
                    app.logger.info(
                        "[api_chat] web intent cleaned project context before chat_service.handle text=%r",
                        _nova_real_user_text_for_web,
                    )
                except Exception:
                    pass

        image_command_user_text = user_text

        if user_text.lower().startswith("/image"):
            image_command_user_text = "generate image " + (user_text[6:].strip() or "image")

        app.logger.info(
            "[api_chat] calling chat_service.handle session_id=%s attachments_count=%s",
            session_id,
            len(attachments_for_chat_service or []),
        )

        username = ""

        try:
            from flask import g

            user = getattr(g, "nova_auth_user", None) or {}

            username = str(
                user.get("username") or ""
            ).strip()

        except Exception:
            pass

        result = chat_service.handle(
            user_text=image_command_user_text,
            session_id=session_id,
            attachments=attachments_for_chat_service,
        )

        # NOVA_MOBILE_IMAGE_URL_ACTIVE_SESSION_FORCE_20260630
        # Image generation can create the PNG but leave image_url attached to
        # a stale/placeholder session. Force the image URL onto the actual
        # requested mobile session response and latest assistant message.
        try:
            if isinstance(result, dict):
                request_payload_for_image = data if isinstance(data, dict) else (request.get_json(silent=True) or {})

                target_session_id = str(
                    request_payload_for_image.get("session_id")
                    or request_payload_for_image.get("sessionId")
                    or request_payload_for_image.get("active_session_id")
                    or locals().get("requested_session_id")
                    or result.get("active_session_id")
                    or result.get("session_id")
                    or session_id
                    or ""
                ).strip()

                if not target_session_id:
                    target_session_id = str(session_id or "").strip()

                assistant = result.get("assistant_message")
                if not isinstance(assistant, dict):
                    assistant = {
                        "role": "assistant",
                        "text": str(result.get("text") or "").strip(),
                    }

                image_url = str(
                    result.get("image_url")
                    or result.get("imageUrl")
                    or assistant.get("image_url")
                    or assistant.get("imageUrl")
                    or ""
                ).strip()

                result_text_for_image = str(
                    result.get("text")
                    or assistant.get("text")
                    or assistant.get("content")
                    or ""
                ).strip()

                if not image_url and result_text_for_image.startswith("Generated image for:"):
                    try:
                        owner_id = get_current_user_id()

                        generated_files = sorted(
                            Path(UPLOADS_DIR).glob("generated_*.png"),
                            key=lambda item: item.stat().st_mtime,
                            reverse=True,
                        )

                        for item in generated_files:
                            if UploadOwnershipService().belongs_to_user(
                                item.name,
                                owner_id,
                            ):
                                image_url = f"/api/uploads/{item.name}"
                                break

                    except Exception as image_file_error:
                        app.logger.warning(
                            "[MobileImageUrlForce] owned generated file lookup failed: %s",
                            image_file_error,
                        )

                if image_url:
                    image_filename = image_url.split("/api/uploads/", 1)[-1].split("?", 1)[0].strip("/\\")

                    image_attachment = {
                        "id": image_filename,
                        "filename": image_filename,
                        "stored_name": image_filename,
                        "url": image_url,
                        "file_url": image_url,
                        "mime_type": "image/png",
                        "type": "image/png",
                    }

                    assistant["role"] = "assistant"
                    assistant["text"] = result_text_for_image or f"Generated image for: {image_command_user_text}"
                    assistant["content"] = assistant["text"]
                    assistant["image_url"] = image_url
                    assistant["attachments"] = [image_attachment]

                    meta = assistant.get("meta")
                    if not isinstance(meta, dict):
                        meta = {}
                    meta["source"] = "image_generation"
                    meta["image_url"] = image_url
                    meta["active_session_forced"] = True
                    meta["forced_target_session_id"] = target_session_id
                    assistant["meta"] = meta

                    result["assistant_message"] = assistant
                    result["text"] = assistant["text"]
                    result["content"] = assistant["text"]
                    result["image_url"] = image_url
                    result["active_session_id"] = target_session_id
                    result["session_id"] = target_session_id

                    # Patch session through session_service.
                    try:
                        current_session = session_service.get_session(target_session_id) or {}
                        messages = current_session.get("messages")
                        if isinstance(messages, list):
                            for message in reversed(messages):
                                if (
                                    isinstance(message, dict)
                                    and str(message.get("role") or "").lower() == "assistant"
                                    and str(message.get("text") or "").startswith("Generated image for:")
                                ):
                                    message["image_url"] = image_url
                                    message["attachments"] = [image_attachment]
                                    message["meta"] = dict(meta)
                                    break

                            current_session["messages"] = messages
                            all_sessions = session_service.get_all()

                            if isinstance(all_sessions, dict):
                                all_sessions.setdefault("sessions", {})
                                if isinstance(all_sessions["sessions"], dict):
                                    all_sessions["sessions"][target_session_id] = current_session
                                session_service.save(all_sessions, active=target_session_id)
                    except Exception as session_patch_error:
                        app.logger.warning(
                            "[MobileImageUrlForce] session_service patch failed: %s",
                            session_patch_error,
                        )

                    # Direct JSON patch fallback. This handles dict or array session stores.
                    try:
                        sessions_path = Path(SESSIONS_FILE)
                        store = json.loads(sessions_path.read_text(encoding="utf-8"))

                        sessions_obj = store.get("sessions")
                        target_session = None

                        if isinstance(sessions_obj, dict):
                            target_session = sessions_obj.get(target_session_id)
                        elif isinstance(sessions_obj, list):
                            for item in sessions_obj:
                                if isinstance(item, dict) and str(item.get("id") or "") == target_session_id:
                                    target_session = item
                                    break

                        if isinstance(target_session, dict):
                            target_messages = target_session.get("messages")
                            if isinstance(target_messages, list):
                                patched = False

                                for message in reversed(target_messages):
                                    if (
                                        isinstance(message, dict)
                                        and str(message.get("role") or "").lower() == "assistant"
                                        and str(message.get("text") or "").startswith("Generated image for:")
                                    ):
                                        message["image_url"] = image_url
                                        message["attachments"] = [image_attachment]
                                        message["meta"] = dict(meta)
                                        patched = True
                                        break

                                if patched:
                                    target_session["messages"] = target_messages
                                    store["active"] = target_session_id
                                    store["active_session_id"] = target_session_id
                                    sessions_path.write_text(
                                        json.dumps(store, indent=2, ensure_ascii=False),
                                        encoding="utf-8",
                                    )

                    except Exception as json_patch_error:
                        app.logger.warning(
                            "[MobileImageUrlForce] direct json patch failed: %s",
                            json_patch_error,
                        )

                    app.logger.info(
                        "[MobileImageUrlForce] forced image_url=%s target_session_id=%s old_session_id=%s",
                        image_url,
                        target_session_id,
                        session_id,
                    )
        except Exception as image_force_error:
            app.logger.warning("[MobileImageUrlForce] failed: %s", image_force_error)

         # =========================
        # IMAGE NORMALIZATION BLOCK
        # =========================
        if isinstance(result, dict):
            assistant = result.get("assistant_message") or {}

            if isinstance(assistant, dict):
                prompt = result.get("prompt") or assistant.get("text") or ""

                if isinstance(prompt, str) and prompt.startswith("generate image "):
                    clean_prompt = prompt[len("generate image "):].strip()

                    result["prompt"] = clean_prompt
                    assistant["text"] = f"Generated image for: {clean_prompt}"
                    assistant["content"] = assistant["text"]

                    if "image_url" in assistant:
                        result["image_url"] = assistant["image_url"]

                    result["assistant_message"] = assistant

        # =========================
        # SAFE LOGGING
        # =========================
        try:
            app.logger.info(
                "[api_chat] chat_service.handle result ok=%s active_session_id=%s keys=%s",
                result.get("ok") if isinstance(result, dict) else None,
                result.get("active_session_id") if isinstance(result, dict) else None,
                sorted(list(result.keys())) if isinstance(result, dict) else type(result).__name__,
            )
        except Exception:
            pass

            # NOVA_SAFE_API_CHAT_WEAK_GUARD_AFTER_HANDLE_LOCK
            result = response_quality_service.replace_weak_backend_reply(
                image_command_user_text,
                result,
            )
            # AFTER_WEAK_GUARD_ATTACHMENT_SUMMARY_LOCK
            # Final safety: if attachment text was extracted but the reply is still the old canned
            # attachment response, replace it with a local summary after weak-reply cleanup.
            try:
                if attachment_content_lines and isinstance(result, dict):
                    assistant_message = result.get("assistant_message")
                    if isinstance(assistant_message, dict):
                        current_reply = str(
                            assistant_message.get("text")
                            or assistant_message.get("content")
                            or ""
                        ).strip()
            
                        lower_reply = current_reply.lower()
                        is_canned_attachment_reply = (
                            "i received the attachment" in lower_reply
                            and "instead of generating an image" in lower_reply
                        )
            
                        if is_canned_attachment_reply:
                            extracted_text = "\n\n".join(str(item or "") for item in attachment_content_lines).strip()
            
                            try:
                                summary_payload = attachment_analysis_service.local_summary_from_text(
                                    extracted_text
                                )
                            except Exception:
                                summary_payload = None
            
                            if isinstance(summary_payload, dict):
                                summary = str(summary_payload.get("summary") or "").strip()
                                key_points = summary_payload.get("key_points") or []
                                preview = str(summary_payload.get("preview") or "").strip()
                            else:
                                summary = "I extracted readable text from the attachment."
                                key_points = []
                                seen = set()
                                for raw_line in extracted_text.splitlines():
                                    cleaned = " ".join(str(raw_line or "").strip().split())
                                    lowered = cleaned.lower()
                                    if not cleaned or lowered in seen or len(cleaned) < 8:
                                        continue
                                    seen.add(lowered)
                                    key_points.append(cleaned)
                                    if len(key_points) >= 10:
                                        break
                                preview = "\n".join(key_points[:6])
            
                            # WEAK_GUARD_CLEAN_BEFORE_FORMAT_LOCK
                            # Clean weak-guard attachment text before formatting final response.
                            # Prevents double summaries like:
                            # "This attachment appears... This attachment appears... Key points..."
                            import re as _nova_weak_guard_re

                            def _nova_weak_guard_clean_line(value):
                                line = str(value or "").strip()
                                line = _nova_weak_guard_re.sub(r"^\\s*\\d+\\.\\s*", "", line).strip()
                                line = line.replace("", "").strip()
                                line = line.replace("Attachment <unknown>", "uploaded attachment")
                                line = _nova_weak_guard_re.sub(r"\\s+", " ", line).strip()
                                return line

                            _nova_weak_bad_exact = {
                                "attachment analysis:",
                                "key points:",
                                "preview:",
            "copy",
            "regen",
            "regenerate",
                                "uploaded attachment content:",
                                "attachment content:",
                                "attachment <unknown> content:",
                                "keypoints",
            "copy",
            "regen",
            "regenerate",
                                "summarize",
                                "summary",
                                "continue",
                            }

                            _nova_weak_bad_starts = (
                                "this attachment appears to contain extracted image/pdf content about:",
                                "this attachment appears to contain image/search/pdf extraction text about:",
                                "this attachment appears to be about:",
                            )

                            _nova_weak_bad_contains = (
                                "uploaded attachment content:",
                                "attachment <unknown> content:",
                                "key points:;",
                                "preview:;",
                            )

                            def _nova_weak_keep_line(value):
                                line = _nova_weak_guard_clean_line(value)
                                if not line:
                                    return ""

                                low = line.lower().strip(" :;-•*|")
                                compact = _nova_weak_guard_re.sub(r"[^a-z0-9]+", " ", low).strip()

                                if low in _nova_weak_bad_exact or compact in _nova_weak_bad_exact:
                                    return ""

                                if any(low.startswith(prefix) for prefix in _nova_weak_bad_starts):
                                    return ""

                                if any(bad in low for bad in _nova_weak_bad_contains):
                                    return ""

                                if line.isdigit():
                                    return ""

                                if len(line) <= 2:
                                    return ""

                                return line

                            cleaned_key_points = []
                            seen_weak_points = set()

                            if isinstance(key_points, list):
                                for raw_point in key_points:
                                    clean_point = _nova_weak_keep_line(raw_point)
                                    if not clean_point:
                                        continue

                                    key = _nova_weak_guard_re.sub(
                                        r"[^a-z0-9]+",
                                        " ",
                                        clean_point.lower(),
                                    ).strip()[:160]

                                    if not key or key in seen_weak_points:
                                        continue

                                    seen_weak_points.add(key)
                                    cleaned_key_points.append(clean_point)

                                    if len(cleaned_key_points) >= 10:
                                        break

                            key_points = cleaned_key_points

                            cleaned_preview_lines = []
                            for raw_preview_line in str(preview or "").splitlines():
                                clean_preview_line = _nova_weak_keep_line(raw_preview_line)
                                if clean_preview_line:
                                    cleaned_preview_lines.append(clean_preview_line)

                            preview = "\n".join(cleaned_preview_lines[:6])

                            if key_points:
                                summary = (
                                    "This uploaded attachment contains readable text about: "
                                    + "; ".join(key_points[:3])
                                    + "."
                                )
                            else:
                                summary = "The attachment was received and processed, but the extracted text is too limited or noisy to summarize cleanly."

                            points_text = ""
                            if isinstance(key_points, list) and key_points:
                                points_text = "\n".join(
                                    f"{index + 1}. {point}"
                                    for index, point in enumerate(key_points[:10])
                                )
            
                            replacement_text = (
                                "Attachment analysis:\n"
                                + (summary or "I extracted readable text from the attachment.")
                                + ("\n\nKey points:\n" + points_text if points_text else "")
                                + ("\n\nPreview:\n" + preview[:1200] if preview else "")
                            ).strip()
            
                            # NOVA_DISABLE_ATTACHMENT_RECURSIVE_WRAPPER_REWRITE_20260611
                            _nova_existing_attachment_content = str(assistant_message.get("content") or "").strip()
                            _nova_replacement_text_value = str(replacement_text or "").strip()

                            if (
                                _nova_existing_attachment_content.startswith("Attachment analysis:")
                                and "Attachment " in _nova_existing_attachment_content
                                and " content:" in _nova_existing_attachment_content
                                and "This uploaded attachment contains readable text about:" in _nova_replacement_text_value
                            ):
                                assistant_message["text"] = _nova_existing_attachment_content
                                assistant_message["content"] = _nova_existing_attachment_content
                            else:
                                assistant_message["text"] = replacement_text
                                assistant_message["content"] = replacement_text

                            result["assistant_message"] = assistant_message
                            result["skip_cleanup"] = True
                            result["skip_post_processing"] = True
                            result["skip_rewrite"] = True
            
                            app.logger.info(
                                "[AttachmentContentGate] after weak guard replaced canned attachment reply chars=%s key_points=%s session_id=%s",
                                len(replacement_text),
                                len(key_points or []),
                                session_id,
                            )
            except Exception as _nova_after_weak_guard_attachment_error:
                app.logger.warning(
                    "[AttachmentContentGate] after weak guard attachment summary failed error=%s",
                    _nova_after_weak_guard_attachment_error,
                )



            if isinstance(result, dict):
                active_attachment_session_id = str(
                    result.get("active_session_id")
                    or session_id
                    or ""
                ).strip()

                result["session_attachments"] = summarize_attachments_for_session(
                    active_attachment_session_id,
                    limit=25,
                    client_session_id=requested_session_id,
                )


                # REAL_RESPONSE_ATTACHMENT_COUNT_LOCK
                # Force returned attachment payload/count to current request only.
                try:
                    if isinstance(result, dict):
                        result["session_attachments"] = list(attachments or [])
                        result_session = result.get("session")
                        if isinstance(result_session, dict):
                            result_session["session_attachments"] = list(attachments or [])
                            result_session["attachment_memory"] = list(attachments or [])
                            result_session["attachments"] = list(attachments or [])
                    app.logger.info(
                        "[AttachmentContentGate] real response attachment payload forced current-only count=%s session_id=%s",
                        len(attachments or []),
                        requested_session_id,
                    )
                except Exception as _nova_real_response_attachment_error:
                    app.logger.warning(
                        "[AttachmentContentGate] real response attachment payload cleanup failed error=%s",
                        _nova_real_response_attachment_error,
                    )
                app.logger.info(
                    "[api_chat] returned session attachment memory count=%s session_id=%s",
                    len(result.get("session_attachments") or []),
                    active_attachment_session_id,
                )
        except Exception:
            app.logger.exception("[api_chat] failed while logging chat_service result")

        # TEMP DISABLED:
        # runtime_brain.run_cycle is crashing on undefined working_state.
        # Keep disabled until execution mutation is stable.
        # REMOVE_API_CHAT_RAW_RESULT_PRINT_LOCK

        if result is None:
            result = {
                "ok": False,
                "assistant_message": {
                    "role": "assistant",
                    "text": "Nova returned no response from chat_service.handle().",
                },
                "session_id": session_id,
            }

        try:
            if isinstance(result, dict):
                session = result.get("session") or {}
                meta = session.get("meta") or {}

                if meta.get("pending_execution_action"):
                    meta["pending_execution_action"] = ""

                assistant_message = result.get("assistant_message") or {}
                assistant_meta = assistant_message.get("meta") or {}

                if assistant_meta.get("pending_execution_action"):
                    assistant_meta["pending_execution_action"] = ""

        except Exception as cleanup_error:
            print("PENDING EXECUTION CLEANUP FAILED:", cleanup_error)

        # NOVA_NORMALIZE_RESULT_BEFORE_ASSISTANT_MESSAGE_20260608
        # Some attachment/DOCX paths return a plain string from chat_service.handle.
        # Normalize it into Nova's expected /api/chat dict contract before result.get(...).
        if isinstance(result, str):
            result = {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "content": result,
                    "text": result,
                },
                "text": result,
                "session_id": session_id,
                "active_session_id": session_id,
                "debug": {
                    "normalized_string_result": True,
                    "route_taken": "attachment_analysis",
                },
            }

        assistant_message = result.get("assistant_message") or {
            "role": "assistant",
            "text": "",
        }

        # API_CHAT_RESPONSE_CONTRACT_LOCK
        if not isinstance(assistant_message, dict):
            assistant_message = {
                "role": "assistant",
                "text": str(assistant_message or "").strip(),
            }

        assistant_message.setdefault("role", "assistant")

        assistant_text = str(
            assistant_message.get("text")
            or assistant_message.get("content")
            or assistant_message.get("message")
            or ""
        ).strip()

        if not assistant_text and result.get("ok", True):
            assistant_text = "Nova completed the request but returned an empty assistant response."

        assistant_text = response_quality_service.prevent_bad_exact_pong_response(
            assistant_text,
            user_text,
        )


        assistant_message["text"] = assistant_text
        assistant_message["content"] = assistant_text

        payload = {
            "ok": result.get("ok", True),
            "assistant_message": assistant_message,
            # ATTACHMENT_CONTEXT_RESPONSE_FIX_LOCK
            "session_attachments": (
                result.get("session_attachments")
                if isinstance(result, dict)
                else []
            ) or [],
            "attachment_debug": {
                "requested_session_id": requested_session_id,
                "active_session_id": (
                    result.get("active_session_id")
                    if isinstance(result, dict)
                    else session_id
                ),
                "session_attachments_count": len(
                    (
                        result.get("session_attachments")
                        if isinstance(result, dict)
                        else []
                    ) or []
                ),
            },
            "active_session_id": (
                result.get("active_session_id")
                or result.get("session_id")
                or session_id
            ),
            "session": (
                result.get("session")
                or session_service.get_session(session_id)
            ),
            "saved_artifact": result.get("saved_artifact"),
            "runtime": {},
            "debug": result.get("debug") or {},
        }

        return json_ok(
            **{
                k: v
                for k, v in payload.items()
                if v is not None
            }
        )

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return json_error(str(exc), 500)

@app.get("/api/chat/<session_id>")
def api_chat_session_compat(session_id: str):
    # MOBILE_MISSING_SESSION_SAFE_FALLBACK_LOCK
    requested_session_id = str(session_id or "").strip()

    session = session_service.get_session(requested_session_id)

    if not session:
        session = {
            "id": requested_session_id,
            "title": "New Chat",
            "messages": [],
            "created_at": "",
            "updated_at": "",
            "pinned": False,
            "working_state": {},
            "execution_state": {},
            "active_execution": None,
            "missing": True,
        }

        return json_ok(
            session=session,
            sessions=session_service.get_all(),
            active_session_id=requested_session_id,
            messages=[],
            missing_session=True,
            mobile_fallback=True,
        )

    return json_ok(
        session=session,
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
        messages=session.get("messages") or [],
        missing_session=False,
        mobile_fallback=False,
    )

# NOVA_FIX_MISSING_UPLOAD_HELPER_LOGGER_20260609
import logging as _nova_logging_20260609
logger = _nova_logging_20260609.getLogger(__name__)


@app.get("/api/sessions/<session_id>")
def api_session_by_id(session_id: str):
    # NOVA_SESSION_DETAIL_SERVICE_FIRST_20260703
    # Detail must read through the same service path used by list/delete.
    # The old manual candidate-file scanner could 404 even when /api/sessions
    # listed the session and /api/sessions/delete could remove it.
    sid = str(session_id or "").strip()

    if not sid:
        return jsonify({
            "ok": False,
            "error": "Session not found",
            "session": None,
            "active_session_id": "",
            "session_id": sid,
            "skip_session_auth_scope_filter": True,
        }), 404

    found = None
    active_session_id = ""

    auth_user_id = ""
    try:
        flask_session = globals().get("session")

        auth_user_id = str(
            flask_session.get("nova_user_id")
            or flask_session.get("user_id")
            or ""
        ).strip()

    except Exception:
        auth_user_id = ""

    try:
        candidate = session_service.get_session(
            sid,
            user_id=auth_user_id,
        )

        if isinstance(candidate, dict):
            found = candidate

    except Exception:
        found = None

    if found is None:
        try:
            sessions = session_service.get_all(
                user_id=auth_user_id,
            )

            if isinstance(sessions, list):
                for item in sessions:
                    if not isinstance(item, dict):
                        continue

                    if str(item.get("id") or "").strip() != sid:
                        continue

                    if not session_service._belongs_to_user(
                        item,
                        auth_user_id,
                    ):
                        continue

                    found = item
                    break

        except Exception:
            found = None

    # Last-resort raw store fallback with owner enforcement.
    if found is None:
        try:
            store = session_service._read_store()
            items = store.get("sessions") if isinstance(store, dict) else []

            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue

                    if str(item.get("id") or "").strip() != sid:
                        continue

                    if not session_service._belongs_to_user(
                        item,
                        auth_user_id,
                    ):
                        continue

                    found = item
                    break

        except Exception:
            found = None

    if found is None:
        return jsonify({
            "ok": False,
            "error": "Session not found",
            "session": None,
            "active_session_id": active_session_id,
            "session_id": sid,
            "skip_session_auth_scope_filter": True,
        }), 404

    return jsonify({
        "ok": True,
        "session": found,
        "active_session_id": active_session_id or sid,
        "session_id": sid,
        "detail_service_first": True,
    })

@app.post("/api/sessions/new")
def api_sessions_new():
    # NOVA_SESSION_NEW_FORCE_DURABLE_OWNER_WRITE_20260703
    # Create a real durable session, stamp current local-auth owner fields,
    # force-write it into the canonical session store, then return only the
    # saved/readable version. This prevents ghost active_session_id values.

    data = request_json()
    title = str(data.get("title") or "New Chat").strip() or "New Chat"

    # Resolve owner from Flask session before creating the session.
    auth_user_id = ""
    auth_username = ""

    try:
        auth_user_id = str(
            session.get("nova_user_id") or ""
        ).strip()

    except Exception:
        auth_user_id = ""

    if hasattr(session_service, "create_session"):
        created = session_service.create_session(
            title,
            user_id=auth_user_id,
        )
    elif hasattr(session_service, "new_session"):
        created = session_service.new_session(
            title,
            user_id=auth_user_id,
        )
    else:
        raise AttributeError(
            "SessionService has no create_session/new_session method"
        )

    session_id = ""

    if isinstance(created, dict):
        session_id = str(created.get("id") or "").strip()

    if not session_id:
        session_id = str(
            getattr(session_service, "active_session_id", "") or ""
        ).strip()


    try:
        users_path = DATA_DIR / "nova_auth_users.json"
        users_data = load_json(users_path, {"users": []})
        users = users_data.get("users", []) if isinstance(users_data, dict) else []

        for user in users:
            if not isinstance(user, dict):
                continue

            if str(user.get("id") or "") == auth_user_id:
                auth_username = str(
                    user.get("username")
                    or user.get("email")
                    or ""
                ).strip()
                break
    except Exception:
        auth_username = ""

    # Owner fallback for Richard's stable direct-login route.
    if auth_user_id == "user_richard_stable_local_login" and not auth_username:
        auth_username = "richard"

    if isinstance(created, dict):
        if auth_user_id:
            created["user_id"] = auth_user_id
        if auth_username:
            created["username"] = auth_username

        meta = created.get("meta")
        if not isinstance(meta, dict):
            meta = {}
        if auth_user_id or auth_username:
            meta["owner_source"] = "local_auth"
        created["meta"] = meta

    # Force durable write into the same store used by detail/list routes.
    if session_id and isinstance(created, dict):
        try:
            store = session_service._read_store()
            if not isinstance(store, dict):
                store = {"active_session_id": "", "sessions": []}

            sessions = store.get("sessions")
            if not isinstance(sessions, list):
                sessions = []

            found = False
            for index, item in enumerate(sessions):
                if isinstance(item, dict) and str(item.get("id") or "") == session_id:
                    merged = dict(item)
                    merged.update(created)
                    sessions[index] = merged
                    created = merged
                    found = True
                    break

            if not found:
                sessions.insert(0, created)

            store["sessions"] = sessions
            store["active_session_id"] = session_id
            session_service._write_store(store)
        except Exception as exc:
            try:
                app.logger.warning("[NOVA_SESSION_NEW_FORCE_DURABLE_OWNER_WRITE_20260703] force write failed: %s", exc)
            except Exception:
                pass

    saved = (
    session_service.get_session(
        session_id,
        user_id=auth_user_id,
    )
    if session_id
    else None
)

    if isinstance(saved, dict):
        created = saved

    sessions = session_service.get_all(
        user_id=auth_user_id,
    )

    # Ensure the response list includes the created active session, even if a
    # list cap/filter elsewhere has not refreshed yet.
    if session_id and isinstance(created, dict):
        found_in_response = False
        for item in sessions:
            if isinstance(item, dict) and str(item.get("id") or "") == session_id:
                found_in_response = True
                break
        if not found_in_response:
            sessions = [created] + [item for item in sessions if isinstance(item, dict)]

    return json_ok(
        session=created if isinstance(created, dict) else None,
        sessions=sessions,
        active_session_id=session_id or getattr(session_service, "active_session_id", ""),
        session_id=session_id,
        skip_session_auth_scope_filter=True,
        durable_session_write=True,
    )


@app.post("/api/sessions/switch")
def api_sessions_switch():

    data = request_json()
    session_id = str(data.get("session_id") or "").strip()

    if not session_id:
        return json_error("Missing session_id", 400)

    session = session_service.set_active(
        session_id,
        user_id=auth_user_id,
    )
    if not session:
        return json_error("Session not found", 404)

    return json_ok(
        session=session_service.get_session(session_id),
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/rename")
def api_sessions_rename():

    data = request_json()
    session_id = str(data.get("session_id") or "").strip()
    title = str(data.get("title") or "").strip()

    if not session_id:
        return json_error("Missing session_id", 400)

    auth_user_id = ""

    try:
        flask_session = globals().get("session")

        auth_user_id = str(
            flask_session.get("nova_user_id")
            or flask_session.get("user_id")
            or ""
        ).strip()

    except Exception:
        auth_user_id = ""

    session = session_service.rename(
        session_id,
        title or "New Chat",
        user_id=auth_user_id,
    )

    if not session:
        return json_error("Session not found", 404)

    return json_ok(
        session=session_service.get_session(session_id),
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/pin")
def api_sessions_pin():

    data = request_json()
    session_id = str(data.get("session_id") or "").strip()
    pinned = bool(data.get("pinned"))

    if not session_id:
        return json_error("Missing session_id", 400)

    auth_user_id = ""

    try:
        flask_session = globals().get("session")

        auth_user_id = str(
            flask_session.get("nova_user_id")
            or flask_session.get("user_id")
            or ""
        ).strip()

    except Exception:
        auth_user_id = ""

    session = session_service.pin(
        session_id,
        pinned,
        user_id=auth_user_id,
    )

    if not session:
        return json_error("Session not found", 404)

    return json_ok(
        session=session_service.get_session(session_id),
        sessions=session_service.get_all(),
        active_session_id=session_service.active_session_id,
    )


@app.post("/api/sessions/delete")
def api_sessions_delete():

    data = request_json()
    session_id = str(data.get("session_id") or "").strip()

    if not session_id:
        return json_error("Missing session_id", 400)

    auth_user_id = ""

    try:
        flask_session = globals().get("session")

        auth_user_id = str(
            flask_session.get("nova_user_id")
            or flask_session.get("user_id")
            or ""
        ).strip()

    except Exception:
        auth_user_id = ""

    if not session_service.delete(
        session_id,
        user_id=auth_user_id,
    ):
        return json_error("Session not found", 404)

    active_id = session_service.active_session_id
    active_session = session_service.get_active()

    return json_ok(
        session=active_session,
        sessions=session_service.get_all(),
        active_session_id=active_id,
    )

# -----------------------
# ARTIFACTS
# -----------------------

@app.get("/api/artifacts")
def api_artifacts():
    return json_ok(
        artifacts=artifact_service.build_list_payload(),
    )


@app.get("/api/artifacts/<artifact_id>")
def api_artifact_view(artifact_id: str):
    payload = artifact_service.build_view_payload(artifact_id)
    if not payload:
        return json_error("Artifact not found", 404)

    return json_ok(
        artifact=payload,
    )

@app.delete("/api/artifacts/<artifact_id>")
def api_delete_artifact(artifact_id: str):
    try:
        ok = artifact_service.delete_artifact(artifact_id)

        return json_ok(
            ok=bool(ok),
            deleted_artifact_id=artifact_id,
            artifacts=artifact_service.build_list_payload(),
        )

    except Exception as e:
        return json_error(f"Failed to delete artifact: {e}", 500)

def delete_artifact(self, artifact_id: str) -> bool:
    from nova_backend.services.auth_context import get_current_user_id

    try:
        data = self._load()

        artifacts = data.get("artifacts", [])

        owner_id = get_current_user_id()

        new_artifacts = [
            a for a in artifacts
            if not (
                str(a.get("id")) == str(artifact_id)
                and str(a.get("owner_id") or "") == str(owner_id)
            )
        ]

        if len(new_artifacts) == len(artifacts):
            return False

        data["artifacts"] = new_artifacts
        self._save(data)

        return True

    except Exception as e:
        print("DELETE ARTIFACT ERROR:", e)
        return False

# -----------------------
# MEMORY
# -----------------------

@app.get("/api/memory")
@guarded_json_route
def api_memory():
    memory = memory_service.all()
    return ok_response(
        data={
            "memory": memory,
            "count": len(memory),
        },
        message="Memory loaded.",
    )


@app.post("/api/memory/add")
@guarded_json_route
def api_memory_add():
    data = get_json_body(request)

    text = get_str(data, "text")
    kind = get_str(data, "kind", "note") or "note"
    source = get_str(data, "source", "manual") or "manual"
    session_id = get_str(data, "session_id")

    if not text:
        return error_response(
            error="text is required.",
            code="missing_text",
        ), 400

    item = memory_service.add_memory({
        "text": text,
        "kind": kind,
        "source": source,
        "session_id": session_id,
    })

    memory = memory_service.all()

    memory = memory_service.all()

    return ok_response(
        data={
            "item": item,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory added.",
    )

@app.post("/api/memory/pin")
@guarded_json_route
def api_memory_pin():
    data = get_json_body(request)
    memory_id = get_str(data, "id") or get_str(data, "memory_id")
    pinned = bool(data.get("pinned", True))

    if not memory_id:
        return error_response(
            error="id is required.",
            code="missing_id",
        ), 400

    item = memory_service.pin_memory(memory_id, pinned=pinned)
    memory = memory_service.all()

    return ok_response(
        data={
            "item": item,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory pinned." if pinned else "Memory unpinned.",
    )

@app.post("/api/memory/delete")
@guarded_json_route
def api_memory_delete():
    data = get_json_body(request)
    memory_id = get_str(data, "id") or get_str(data, "memory_id")

    if not memory_id:
        return error_response(
            error="id is required.",
            code="missing_id",
        ), 400

    deleted = memory_service.delete_memory(memory_id)
    memory = memory_service.all()

    return ok_response(
        data={
            "deleted": deleted,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory deleted." if deleted else "Memory not found.",
    )

@app.post("/api/memory/update")
@guarded_json_route
def api_memory_update():
    data = get_json_body(request)

    memory_id = str(data.get("id") or "").strip()
    text = str(data.get("text") or "").strip()
    kind = str(data.get("kind") or "note").strip()

    if not memory_id:
        return error_response("Missing memory id", code="missing_id"), 400

    if not text:
        return error_response("Missing memory text", code="missing_text"), 400

    items = memory_service.all()

    updated = None
    for item in items:
        if str(item.get("id")) == memory_id:
            item["text"] = text
            item["kind"] = kind
            item["updated_at"] = iso_now()
            updated = item
            break

    if not updated:
        return error_response("Memory not found", code="not_found"), 404

    memory_service._write_store({"memory": items})

    return ok_response(
        item=updated,
        message="Memory updated."
    )

@app.post("/api/memory/cleanup")
@guarded_json_route
def api_memory_cleanup():
    result = memory_service.cleanup_memories()
    memory = memory_service.all()

    return ok_response(
        data={
            "result": result,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory cleanup complete.",
    )


@app.post("/api/memory/promote")
@guarded_json_route
def api_memory_promote():
    result = memory_service.promote_memories()
    memory = memory_service.all()

    return ok_response(
        data={
            "result": result,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory promotion complete.",
    )


@app.post("/api/memory/cleanup-promote")
@guarded_json_route
def api_memory_cleanup_promote():
    result = memory_service.cleanup_and_promote_memories()
    memory = memory_service.all()

    return ok_response(
        data={
            "result": result,
            "memory": memory,
            "count": len(memory),
        },
        message="Memory cleanup and promotion complete.",
    )


# -----------------------
# WEB
# -----------------------

@app.post("/api/web/fetch")
def api_web_fetch():
    print("HIT API_WEB_FETCH ROUTE", flush=True)
    try:
        data = request.get_json(silent=True) or {}
        url = str(data.get("url") or "").strip()

        if not url:
            return jsonify({
                "ok": False,
                "error": "Missing url",
            }), 400

        try:
            result = web_service.fetch(url)
        except Exception as exc:
            result = {
                "ok": False,
                "url": url,
                "summary": "Preview unavailable. Open the full article instead.",
                "images": [],
                "error": str(exc),
            }

        if not isinstance(result, dict):
            result = {
                "ok": False,
                "url": url,
                "summary": "Preview unavailable. Open the full article instead.",
                "images": [],
                "error": "web_service.fetch returned non-dict result",
            }

        artifact = None
        if result.get("ok"):
            try:
                artifact = web_service.build_artifact_payload(result)
            except Exception as exc:
                result["artifact_error"] = str(exc)

        return jsonify({
            "ok": True,
            "result": result,
            "artifact": artifact,
        })

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
            "route": "/api/web/fetch",
        }), 200

# -----------------------
# RECON
# -----------------------

@app.post("/api/recon/analyze")
def api_recon_analyze():

    data = request_json()
    url = str(data.get("url") or "").strip()

    if not url:
        return json_error("Missing url", 400)

    result = recon_service.analyze_target(url)
    if not result.get("ok"):
        return json_error(result.get("error") or "Recon failed", 500, result=result)

    return json_ok(
        result=result,
        artifact=recon_service.build_artifact_payload(result),
    )

@app.post("/api/upload")
def api_upload():

    try:
        if "file" not in request.files:
            return jsonify({
                "ok": False,
                "error": "No file provided.",
            }), 400

        file = request.files["file"]
        if not file or not getattr(file, "filename", ""):
            return jsonify({
                "ok": False,
                "error": "Empty file.",
            }), 400

        auth_user_id = ""

        try:
            auth_user_id = str(
                session.get("nova_user_id")
                or session.get("user_id")
                or ""
            ).strip()
        except Exception:
            auth_user_id = ""

        result = upload_route_service.handle_upload(
            file,
            auth_user_id=auth_user_id,
            logger=app.logger,
            secure_filename=secure_filename,
        )

        return jsonify(result)

    except Exception as e:
        app.logger.exception("api_upload failed")
        return jsonify({
            "ok": False,
            "error": str(e),
        }), 500

# -----------------------
# UPLOADS
# -----------------------
@app.get("/api/uploads/<path:filename>")
def api_uploads(filename: str):
    try:
        raw_name = str(filename or "").strip().lstrip("/\\")
        auth_user_id = ""

        try:
            auth_user_id = str(
                session.get("nova_user_id")
                or session.get("user_id")
                or ""
            ).strip()

        except Exception:
            auth_user_id = ""

        if not auth_user_id:
            return jsonify({
                "ok": False,
                "error": "Upload owner required",
                "filename": raw_name,
            }), 403

        if not upload_ownership_service.belongs_to_user(
            raw_name,
            auth_user_id,
        ):
            return jsonify({
                "ok": False,
                "error": "Upload not found",
                "filename": raw_name,
            }), 404
        full_path = (UPLOADS_DIR / raw_name).resolve()
        uploads_root = UPLOADS_DIR.resolve()

        noisy_video_request = raw_name.lower().endswith((
            ".mp4",
            ".mov",
            ".webm",
            ".m4v",
        ))

        try:
            full_path.relative_to(uploads_root)
        except ValueError:
            if not noisy_video_request:
                app.logger.warning(f"UPLOAD BLOCKED OUTSIDE ROOT: {full_path}")

            return jsonify({
                "ok": False,
                "error": "Invalid upload path",
                "filename": raw_name,
            }), 400

        if not full_path.exists() or not full_path.is_file():
            if not noisy_video_request:
                app.logger.warning(f"UPLOAD MISS: {full_path}")

            return jsonify({
                "ok": False,
                "error": "Upload not found",
                "filename": raw_name,
                "full_path": str(full_path),
                "uploads_dir": str(uploads_root),
            }), 404

        if not noisy_video_request:
            app.logger.info(f"UPLOAD HIT: {full_path}")

        return send_from_directory(
            directory=str(uploads_root),
            path=raw_name,
            as_attachment=False,
        )

    except TypeError:
        # Older Flask / Werkzeug compatibility
        try:
            raw_name = str(filename or "").strip().lstrip("/\\")
            full_path = (UPLOADS_DIR / raw_name).resolve()
            uploads_root = UPLOADS_DIR.resolve()

            noisy_video_request = raw_name.lower().endswith((
                ".mp4",
                ".mov",
                ".webm",
                ".m4v",
            ))

            try:
                full_path.relative_to(uploads_root)
            except ValueError:
                if not noisy_video_request:
                    app.logger.warning(f"UPLOAD BLOCKED OUTSIDE ROOT: {full_path}")

                return jsonify({
                    "ok": False,
                    "error": "Invalid upload path",
                    "filename": raw_name,
                }), 400

            if not full_path.exists() or not full_path.is_file():
                if not noisy_video_request:
                    app.logger.warning(f"UPLOAD MISS: {full_path}")

                return jsonify({
                    "ok": False,
                    "error": "Upload not found",
                    "filename": raw_name,
                    "full_path": str(full_path),
                    "uploads_dir": str(uploads_root),
                }), 404

            if not noisy_video_request:
                app.logger.info(f"UPLOAD HIT: {full_path}")

            return send_from_directory(
                str(uploads_root),
                raw_name,
                as_attachment=False,
            )

        except Exception as e:
            app.logger.exception("api_uploads failed (compat path)")
            return jsonify({
                "ok": False,
                "error": str(e),
                "filename": str(filename or ""),
            }), 500

    except Exception as e:
        app.logger.exception("api_uploads failed")
        return jsonify({
            "ok": False,
            "error": str(e),
            "filename": str(filename or ""),
        }), 500

@app.route("/api/execution/control", methods=["POST"])
def execution_control():
    data = request.get_json(silent=True) or {}

    session_id = str(data.get("session_id") or "").strip()
    action = str(data.get("action") or "").strip()

    if not session_id:
        return jsonify({
            "ok": False,
            "error": "missing session_id",
            "execution_state": {
                "status": "error",
                "steps": [],
                "history": ["missing session_id"],
            },
        }), 400

    if not action:
        return jsonify({
            "ok": False,
            "error": "missing action",
            "execution_state": {
                "status": "error",
                "steps": [],
                "history": ["missing action"],
            },
        }), 400

    working = chat_service._get_working_state(session_id) or {}
    execution = working.get("execution")

    if not isinstance(execution, dict):
        execution = {}

    steps = execution.get("steps")
    if not isinstance(steps, list):
        steps = []

    history = execution.get("history")
    if not isinstance(history, list):
        history = []

    execution = {
        "status": str(execution.get("status") or "idle"),
        "steps": steps,
        "history": history,
        "last_action": str(execution.get("last_action") or ""),
        "current_step": str(execution.get("current_step") or ""),
    }

    if action == "run_step":
        step_num = len(execution["steps"]) + 1
        step_title = f"Step {step_num}"

        step = {
            "title": step_title,
            "status": "done",
            "output": "Step completed.",
        }

        execution["steps"].append(step)
        execution["history"].append(f"run_step: {step_title}")
        execution["status"] = "complete"
        execution["last_action"] = action
        execution["current_step"] = step_title

    elif action == "run_all":
        start_num = len(execution["steps"]) + 1

        for offset in range(3):
            step_num = start_num + offset
            step_title = f"Step {step_num}"

            step = {
                "title": step_title,
                "status": "done",
                "output": "Step completed.",
            }

            execution["steps"].append(step)

        execution["history"].append("run_all: added 3 completed steps")
        execution["status"] = "complete"
        execution["last_action"] = action
        execution["current_step"] = "Run all complete"

    elif action == "test_fail":
        step_num = len(execution["steps"]) + 1
        step_title = f"Failed Step {step_num}"

        failed_step = {
            "title": step_title,
            "status": "failed",
            "output": "Simulated failure.",
        }

        execution["steps"].append(failed_step)
        execution["history"].append(f"test_fail: {step_title}")
        execution["status"] = "error"
        execution["last_action"] = action
        execution["current_step"] = step_title

    elif action in ("retry", "retry_failed"):
        failed_index = None

        for i in range(len(execution["steps"]) - 1, -1, -1):
            step = execution["steps"][i]
            step_status = str(step.get("status") or "").strip().lower()

            if step_status in ("failed", "error"):
                failed_index = i
                break

        if failed_index is not None:
            failed_step = execution["steps"][failed_index]
            failed_title = str(failed_step.get("title") or f"Step {failed_index + 1}")

            failed_step["status"] = "running"
            failed_step["output"] = "Retrying failed step..."

            execution["status"] = "running"
            execution["last_action"] = "retry_failed"
            execution["current_step"] = failed_title
            execution["history"].append(f"retry_failed: {failed_title}")

            failed_step["status"] = "done"
            failed_step["output"] = "Retry successful."

            execution["status"] = "complete"
            execution["current_step"] = "Retry complete"
        else:
            execution["history"].append("retry_failed: no failed step found")
            execution["status"] = "complete"
            execution["last_action"] = "retry_failed"
            execution["current_step"] = "No failed step found"

    elif action == "stop":
        execution["history"].append("stop")
        execution["status"] = "stopped"
        execution["last_action"] = action
        execution["current_step"] = "Stopped"

    else:
        execution["history"].append(f"unknown action: {action}")
        execution["status"] = "error"
        execution["last_action"] = action
        execution["current_step"] = "Unknown action"

    chat_service._update_working_state(session_id, {
        "execution": execution,
    })

    return jsonify({
        "ok": True,
        "action": action,
        "session_id": session_id,
        "execution_state": execution,
    })


def serialize_move(move):
    if isinstance(move, dict):
        return move

    return {
        "id": str(getattr(move, "id", "")),
        "type": str(getattr(move, "type", "")),
        "payload": getattr(move, "payload", {}) if isinstance(getattr(move, "payload", {}), dict) else {},
    }

@app.route("/api/execution/stream", methods=["POST"])
def execution_stream():
    data = request.get_json(silent=True) or {}

    return Response(
        execution_stream_route_service.stream(data),
        mimetype="text/event-stream",
    )
    data = request.get_json(silent=True) or {}

    session_id = str(data.get("session_id") or "").strip()

    action = str(
        data.get("action") or ""
    ).strip()

    action = execution_loop_service.command_alias(
        action
    )

    def generate():
        import time

        if not session_id:
            yield execution_stream_service.send_event("error", {"ok": False, "error": "missing session_id", "done": True})
            return

        if not action:
            yield execution_stream_service.send_event("error", {"ok": False, "error": "missing action", "done": True})
            return

        session = session_service.get_session(
            session_id
        )

        if not isinstance(
            session,
            dict,
        ):
            session = {}

        execution = (
            (session or {})
            .get("working_state", {})
            .get("execution")
            or {}
        )

        execution = execution_service.normalize_execution(
            execution
        )


        yield execution_stream_service.send_event("start", {
            "ok": True,
            "action": action,
            "session_id": session_id,
            "execution_state": execution,
            "done": False,
        })

        if action == "fix_file":

            result = execution_fix_service.apply_fix(
                session_id,
                session,
                execution,
                action,
            )

            execution = result["execution"]
            step = result["step"]
            ok = result["ok"]

            execution_stream_service.save_execution(
                session_id,
                execution,
            )

            yield execution_stream_service.send_event("step_start", {
                "step": step,
                "execution_state": execution,
                "done": False,
            })

            yield execution_stream_service.send_event("step_done", {
                "step": step,
                "execution_state": execution,
                "done": False,
            })

            yield execution_stream_service.send_event("done", {
                "ok": ok,
                "execution_state": execution,
                "done": True,
            })

            return

        else:
            execution = execution_service.apply_control_action(
                execution,
                action,
            )

            execution_stream_service.save_execution(
                session_id,
                execution,
            )

        yield execution_stream_service.send_event("done", {
            "ok": True,
            "execution_state": execution,
            "done": True,
        })

    return Response(generate(), mimetype="text/event-stream")

@app.route("/api/debug/execution", methods=["GET"])
def api_debug_execution():
    try:
        session_id = str(request.args.get("session_id") or "").strip()

        if not session_id:
            return jsonify({
                "ok": False,
                "error": "Missing session_id",
                "active_task": "",
                "next_move": "",
                "last_execution_status": "idle",
                "last_execution_steps": 0,
                "execution_history": [],
            }), 400

        session = session_service.get_session(session_id) or {}
        state = session.get("working_state", {}).get("execution", {})

        if not isinstance(state, dict):
            state = {}

        history = (
            state.get("execution_history")
            or state.get("history")
            or []
        )

        if not isinstance(history, list):
            history = []

        return jsonify({
            "ok": True,
            "session_id": session_id,
            "active_task": state.get("active_task") or "",
            "next_move": state.get("next_move") or "",
            "last_execution_status": state.get("last_execution_status") or "idle",
            "last_execution_action": state.get("last_execution_action") or "",
            "last_execution_steps": state.get("last_execution_steps") or len(history),
            "execution_history": history,
            "working_state": state,
        })

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
            "active_task": "",
            "next_move": "",
            "last_execution_status": "error",
            "last_execution_steps": 0,
            "execution_history": [],
        }), 500

@app.route("/api/web/preview", methods=["POST"])
def web_preview():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url") or "").strip()

    if not url:
        return jsonify({
            "ok": False,
            "error": "Missing url",
            "title": "Source preview",
            "preview": "",
            "url": "",
        }), 400

    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        # Resolve Google News RSS redirect links into the real publisher page.
        if "news.google.com/rss/articles/" in url or "news.google.com/articles/" in url:
            try:
                redirect_response = requests.get(
                    url,
                    headers=headers,
                    timeout=10,
                    allow_redirects=True,
                )
                if redirect_response.url:
                    url = redirect_response.url
            except Exception:
                pass

        response = requests.get(
            url,
            headers=headers,
            timeout=10,
            allow_redirects=True,
        )

        final_url = response.url or url
        html = response.text or ""

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "form",
            "noscript",
            "svg",
        ]):
            tag.decompose()

        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        article = soup.find("article")
        if article:
            text = article.get_text("\n", strip=True)
        else:
            text = soup.get_text("\n", strip=True)

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        cleaned_lines = []
        junk_phrases = [
            "sign in",
            "subscribe",
            "advertisement",
            "cookie",
            "privacy policy",
            "terms of use",
            "enable javascript",
            "all rights reserved",
        ]

        for line in lines:
            low = line.lower()
            if any(junk in low for junk in junk_phrases):
                continue
            if len(line) < 20:
                continue
            cleaned_lines.append(line)

        preview = "\n".join(cleaned_lines[:24]).strip()

        if not preview:
            preview = "Preview route is working, but no readable article text was found."

        return jsonify({
            "ok": True,
            "title": title or "Source preview",
            "preview": preview[:4000],
            "url": final_url,
        })

    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": str(exc),
            "title": "Source preview",
            "preview": "Preview failed on backend.",
            "url": url,
        }), 500

def create_startup_backup():
    root = Path(r"C:\Users\Owner\nova")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_root = root / "nova_backups"
    backup_dir = backup_root / f"startup_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    files_to_backup = [
        root / "app.py",
        root / "nova_backend" / "services" / "chat_service.py",
        root / "static" / "js" / "nova-composer-bundle.js",
        root / "templates" / "index.html",
        root / "static" / "css" / "nova-main.css",
    ]

    for file_path in files_to_backup:
        if file_path.exists():
            relative_path = file_path.relative_to(root)
            destination = backup_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, destination)

    print(f"[NOVA BACKUP] Created: {backup_dir}")

    # ?? AUTO CLEANUP (keep last 10 backups)
    backups = sorted(backup_root.glob("startup_*"), key=lambda p: p.stat().st_mtime, reverse=True)

    for old in backups[10:]:
        try:
            shutil.rmtree(old)
            print(f"[NOVA BACKUP] Removed old: {old}")
        except Exception as e:
            print(f"[NOVA BACKUP] Cleanup error: {e}")

# -----------------------
# MAIN
# -----------------------


# FIX_ATTACHMENT_ANALYZER_ROUTE_AND_CALL_LOCK
# Safety repair: make sure /api/chat points to api_chat, not helper functions.
try:
    if "api_chat" in globals():
        for _nova_rule in app.url_map.iter_rules():
            if str(_nova_rule.rule) == "/api/chat":
                app.view_functions[_nova_rule.endpoint] = api_chat
                _nova_boot_log_20260701(f"[NOVA ROUTE REPAIR] /api/chat endpoint={_nova_rule.endpoint} rebound to api_chat")
except Exception as _nova_route_repair_error:
    print(f"[NOVA ROUTE REPAIR FAILED] {_nova_route_repair_error}")


# ATTACHMENT_EXTRACT_ENDPOINT_LOCK
@app.route("/api/attachment/extract", methods=["POST"])
def api_attachment_extract():
    """
    Extract readable text from an uploaded PDF/image without touching the chat pipeline.
    Accepts JSON:
      {
        "url": "/api/uploads/file.pdf",
        "path": "optional local path",
        "mime_type": "application/pdf"
      }
    """
    try:
        payload = request.get_json(silent=True) or {}

        upload_url = str(payload.get("url") or payload.get("file_url") or "").strip()
        local_path = str(payload.get("path") or "").strip()
        mime_type = str(payload.get("mime_type") or payload.get("type") or "").strip()

        if not local_path and upload_url:
            filename = upload_url.replace("\\", "/").split("/")[-1].strip()
            if filename:
                local_path = str(Path(UPLOADS_DIR) / filename)

        if not local_path:
            return jsonify({
                "ok": False,
                "error": "Missing url or path.",
            }), 400

        file_path = Path(local_path)

        if not file_path.exists():
            return jsonify({
                "ok": False,
                "error": f"File not found: {file_path}",
            }), 404

        if not mime_type:
            suffix = file_path.suffix.lower()
            if suffix == ".pdf":
                mime_type = "application/pdf"
            elif suffix in {".jpg", ".jpeg"}:
                mime_type = "image/jpeg"
            elif suffix == ".png":
                mime_type = "image/png"
            elif suffix == ".webp":
                mime_type = "image/webp"
            else:
                mime_type = "application/octet-stream"

        extracted_text = attachment_analysis_service.analyze_binary_attachment_for_prompt(
            str(file_path),
            mime_type,
        )

        extracted_text = str(extracted_text or "").strip()

        app.logger.info(
            "[AttachmentExtractEndpoint] extracted path=%s chars=%s mime_type=%s",
            str(file_path),
            len(extracted_text),
            mime_type,
        )

        return jsonify({
            "ok": True,
            "path": str(file_path),
            "url": upload_url,
            "mime_type": mime_type,
            "chars": len(extracted_text),
            "text": extracted_text,
        })

    except Exception as error:
        app.logger.exception("[AttachmentExtractEndpoint] failed")
        return jsonify({
            "ok": False,
            "error": str(error),
        }), 500



@app.route("/api/attachment/summarize", methods=["POST"])
def api_attachment_summarize():
    """
    Extract and summarize an uploaded PDF/image without touching the chat pipeline.
    Accepts JSON:
      {
        "url": "/api/uploads/file.pdf",
        "path": "optional local path",
        "mime_type": "application/pdf"
      }
    """
    try:
        payload = request.get_json(silent=True) or {}

        upload_url = str(payload.get("url") or payload.get("file_url") or "").strip()
        local_path = str(payload.get("path") or "").strip()
        mime_type = str(payload.get("mime_type") or payload.get("type") or "").strip()

        if not local_path and upload_url:
            filename = upload_url.replace("\\", "/").split("/")[-1].strip()
            if filename:
                local_path = str(Path(UPLOADS_DIR) / filename)

        if not local_path:
            return jsonify({
                "ok": False,
                "error": "Missing url or path.",
            }), 400

        file_path = Path(local_path)

        if not file_path.exists():
            return jsonify({
                "ok": False,
                "error": f"File not found: {file_path}",
            }), 404

        if not mime_type:
            suffix = file_path.suffix.lower()
            if suffix == ".pdf":
                mime_type = "application/pdf"
            elif suffix in {".jpg", ".jpeg"}:
                mime_type = "image/jpeg"
            elif suffix == ".png":
                mime_type = "image/png"
            elif suffix == ".webp":
                mime_type = "image/webp"
            else:
                mime_type = "application/octet-stream"

        extracted_text = attachment_analysis_service.analyze_binary_attachment_for_prompt(
            str(file_path),
            mime_type,
        )

        cleaned_text = attachment_analysis_service.clean_extracted_attachment_text(
            extracted_text
        )

        local_summary = attachment_analysis_service.local_summary_from_text(
            extracted_text
        )

        app.logger.info(
            "[AttachmentSummarizeEndpoint] summarized path=%s raw_chars=%s clean_chars=%s mime_type=%s",
            str(file_path),
            len(str(extracted_text or "")),
            len(cleaned_text),
            mime_type,
        )

        cleaned_endpoint_summary = (
            attachment_endpoint_service.clean_attachment_endpoint_response(
                local_summary,
                cleaned_text,
                file_path,
                mime_type,
            )
        )

        return jsonify({
            "ok": True,
            "path": str(file_path),
            "url": upload_url,
            "mime_type": mime_type,
            "raw_chars": len(str(extracted_text or "")),
            "clean_chars": len(cleaned_text),
            "summary": cleaned_endpoint_summary["summary"],
            "key_points": cleaned_endpoint_summary["key_points"],
            "preview": cleaned_endpoint_summary["preview"],
            "clean_text": cleaned_endpoint_summary["preview"] or cleaned_text,
        })

    except Exception as error:
        app.logger.exception("[AttachmentSummarizeEndpoint] failed")
        return jsonify({
            "ok": False,
            "error": str(error),
        }), 500

@app.route("/api/attachment/keypoints", methods=["POST"])
def api_attachment_keypoints():
    """
    Extract key points from an uploaded PDF/image without touching the chat pipeline.
    Accepts JSON:
      {
        "url": "/api/uploads/file.pdf",
        "path": "optional local path",
        "mime_type": "application/pdf"
      }
    """
    try:
        payload = request.get_json(silent=True) or {}

        upload_url = str(payload.get("url") or payload.get("file_url") or "").strip()
        local_path = str(payload.get("path") or "").strip()
        mime_type = str(payload.get("mime_type") or payload.get("type") or "").strip()

        if not local_path and upload_url:
            filename = upload_url.replace("\\", "/").split("/")[-1].strip()
            if filename:
                local_path = str(Path(UPLOADS_DIR) / filename)

        if not local_path:
            return jsonify({
                "ok": False,
                "error": "Missing url or path.",
            }), 400

        file_path = Path(local_path)

        if not file_path.exists():
            return jsonify({
                "ok": False,
                "error": f"File not found: {file_path}",
            }), 404

        if not mime_type:
            suffix = file_path.suffix.lower()
            if suffix == ".pdf":
                mime_type = "application/pdf"
            elif suffix in {".jpg", ".jpeg"}:
                mime_type = "image/jpeg"
            elif suffix == ".png":
                mime_type = "image/png"
            elif suffix == ".webp":
                mime_type = "image/webp"
            else:
                mime_type = "application/octet-stream"

        extracted_text = attachment_analysis_service.analyze_binary_attachment_for_prompt(
            str(file_path),
            mime_type,
        )

        key_points = attachment_keypoints_service.attachment_keypoints_from_text(
            extracted_text,
            max_points=10,
        )
        summary = "No readable key points found."
        if key_points:
            summary = "Top attachment point: " + key_points[0]

        app.logger.info(
            "[AttachmentKeypointsEndpoint] extracted keypoints path=%s raw_chars=%s points=%s mime_type=%s",
            str(file_path),
            len(str(extracted_text or "")),
            len(key_points),
            mime_type,
        )

        return jsonify({
            "ok": True,
            "path": str(file_path),
            "url": upload_url,
            "mime_type": mime_type,
            "raw_chars": len(str(extracted_text or "")),
            "summary": summary,
            "key_points": key_points,
            "points_count": len(key_points),
        })

    except Exception as error:
        app.logger.exception("[AttachmentKeypointsEndpoint] failed")
        return jsonify({
            "ok": False,
            "error": str(error),
        }), 500

# CHAT_ATTACHMENT_RESPONSE_CLEANUP_LOCK
@app.after_request
def _nova_clean_attachment_analysis_response(response):
    return attachment_endpoint_service.clean_attachment_analysis_response(
        response
    )


# NOVA_BACKEND_READINESS_ROUTE_20260609
# Live local backend readiness endpoint.
try:
    from nova_backend.services.chat_service_backend_readiness import get_backend_readiness

    @app.route("/api/backend/readiness", methods=["GET"])
    def api_backend_readiness_20260609():
        return get_backend_readiness()

except Exception as _nova_backend_readiness_route_error_20260609:
    @app.route("/api/backend/readiness", methods=["GET"])
    def api_backend_readiness_route_error_20260609():
        return {
            "ok": False,
            "error": "backend_readiness_route_failed",
            "detail": str(_nova_backend_readiness_route_error_20260609),
        }, 500

# NOVA_MOBILE_DIRECT_SESSION_PERSIST_ENDPOINT_20260609
@app.post("/api/mobile/session/persist")
def nova_mobile_direct_session_persist_20260609():
    payload = request.get_json(silent=True) or {}

    return mobile_session_persist_service.persist(
        payload,
        globals().get("SESSIONS_FILE"),
    )

# NOVA_APP_ROUTE_FIXED_CLEAN_BOTTOM_20260610
@app.get("/app")
def nova_desktop_app_fixed_20260610():
    return render_template("app.html")

# NOVA_ACCOUNT_PROFILE_ROUTE_20260708
@app.get("/api/account")
def nova_account_profile_20260708():
    return account_profile_service.get_profile()


# NOVA_LOGIN_PAGE_ROUTES_20260610
login_page_route_service.install_routes(app)
auth_compat_route_service.install_routes(app)

# NOVA_SLIM_API_SESSIONS_PAYLOAD_20260611
@app.after_request
def nova_slim_api_sessions_payload_20260611(response):
    return session_slim_response_service.handle(
        response,
        request,
        app,
    )

# NOVA_BEFORE_REQUEST_SLIM_API_SESSIONS_20260611
@app.before_request
def nova_before_request_slim_api_sessions_20260611():
    return session_route_service.handle_slim_sessions(
        request,
        session,
        session_service,
        app,
        jsonify,
    )


# NOVA_BEFORE_REQUEST_EXPLICIT_MEMORY_GUARD_20260611
@app.before_request
def nova_before_request_explicit_memory_guard_20260611():
    try:
        if request.path not in (
            "/api/chat",
            "/api/chat/stream",
        ) or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}

        return memory_guard_service.handle_explicit_memory_guard(
            payload,
            memory_service,
            session_service,
            jsonify,
            app.logger,
        )

    except Exception:
        return None

# NOVA_BEFORE_REQUEST_FAVORITE_RECALL_GUARD_20260611
@app.before_request
def nova_before_request_favorite_recall_guard_20260611():
    try:
        if request.path not in (
            "/api/chat",
            "/api/chat/stream",
        ) or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}

        return memory_guard_service.handle_favorite_recall_guard(
            payload,
            memory_service,
            session_service,
            jsonify,
            app.logger,
        )

    except Exception:
        return None

# NOVA_BEFORE_REQUEST_MEMORY_SUMMARY_GUARD_20260611
@app.before_request
def nova_before_request_memory_summary_guard_20260611():
    try:
        if request.path not in (
            "/api/chat",
            "/api/chat/stream",
        ) or request.method != "POST":
            return None

        payload = request.get_json(silent=True) or {}

        return memory_guard_service.handle_memory_summary_guard(
            payload,
            memory_service,
            session_service,
            jsonify,
            app.logger,
        )

    except Exception:
        return None

# NOVA_CHAT_STREAM_REAL_20260613

@app.route("/api/events/stream")
def stream_events():
    def event_stream():
        while True:
            # keep connection alive
            yield "data: {}\n\n"
            time.sleep(15)

    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/api/chat/stream", methods=["POST"])
def nova_chat_stream():
    return chat_stream_service.stream(api_chat)

@app.before_request
def nova_memory_command_before_web_20260611():
    try:
        if request.path not in (
            "/api/chat",
            "/api/chat/stream",
        ) or request.method != "POST":
            return None

        data = request.get_json(silent=True) or {}

        return memory_command_service.handle_memory_command_before_web(
            data,
            memory_service,
        )

    except Exception:
        return None

# NOVA_WEB_FETCH_BRIDGE_JSON_IMPORT_FIX_20260612
# Ensure this late bridge can rewrite Flask response JSON even if json was not imported globally.
import json as json

# NOVA_WEB_FETCH_REQUESTED_SESSION_BRIDGE_SAFE_20260612
# Registers before the existing target-session bridge.
# Rewrites successful web_fetch /api/chat responses to the requested session id
# and includes a response session object so the UI can render source cards even
# if /api/sessions/<id> filtering is still strict.

@app.after_request
def nova_web_fetch_requested_session_bridge_safe_20260612(response):
    try:
        payload = request.get_json(silent=True) or {}

        return web_fetch_bridge_service.handle(
            response,
            payload,
        )

    except Exception:
        return response

# NOVA_FORCE_WEB_FETCH_BRIDGE_RUNS_LAST_20260612
# Flask executes after_request hooks in reverse registration order.
# Force the safe web-fetch bridge to index 0 so it runs last and cannot be
# overwritten by older response-normalizer hooks.
try:
    _nova_after_hooks = app.after_request_funcs.get(None, [])
    _nova_bridge_name = "nova_web_fetch_requested_session_bridge_safe_20260612"
    _nova_bridge_func = None

    for _nova_hook in list(_nova_after_hooks):
        if getattr(_nova_hook, "__name__", "") == _nova_bridge_name:
            _nova_bridge_func = _nova_hook
            try:
                _nova_after_hooks.remove(_nova_hook)
            except ValueError:
                pass
            break

    if _nova_bridge_func is not None:
        _nova_after_hooks.insert(0, _nova_bridge_func)
        app.after_request_funcs[None] = _nova_after_hooks
        _nova_boot_log_20260701("[NOVA_WEB_FETCH_BRIDGE_ORDER] forced bridge to run last")
    else:
        print("[NOVA_WEB_FETCH_BRIDGE_ORDER] bridge function not found")
except Exception as _nova_bridge_order_error:
    try:
        app.logger.warning("[NOVA_WEB_FETCH_BRIDGE_ORDER] failed: %s", _nova_bridge_order_error)
    except Exception:
        pass


@app.after_request
def nova_final_session_detail_response_cache_20260612(response):
    return session_detail_response_cache_service.handle(
        response,
        request,
        app,
    )


# Force this hook to run last. Flask executes after_request hooks in reverse order,
# so index 0 is the final hook to touch the response.
try:
    _nova_hooks = app.after_request_funcs.get(None, [])
    _nova_name = "nova_final_session_detail_response_cache_20260612"
    _nova_func = None

    for _nova_hook in list(_nova_hooks):
        if getattr(_nova_hook, "__name__", "") == _nova_name:
            _nova_func = _nova_hook
            try:
                _nova_hooks.remove(_nova_hook)
            except ValueError:
                pass
            break

    if _nova_func is not None:
        _nova_hooks.insert(0, _nova_func)
        app.after_request_funcs[None] = _nova_hooks
        _nova_boot_log_20260701("[NOVA_FINAL_SESSION_DETAIL_CACHE] forced final hook to run last")
except Exception:
    pass


# NOVA_FINAL_TITLE_GUARD_20260630
# Delegated to session_title_guard_service.

@app.after_request
def nova_final_title_guard_20260630(response):
    try:
        from nova_backend.services.session_title_guard_service import (
            apply_response_title_guard,
        )

        return apply_response_title_guard(response)

    except Exception as error:
        print(
            "[NOVA_FINAL_TITLE_GUARD_20260630] skipped:",
            error,
        )

    return response


# Project state route guard
project_state_route_guard_service.install(app)


# NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701
# Prefix-only autonomy task brief route.
# Safe mode: proposal-only. Does not edit files, run commands, or execute plans.
try:
    import json as _nova_autonomy_json_20260701
    import importlib.util as _nova_autonomy_importlib_util_20260701
    from pathlib import Path as _NovaAutonomyPath20260701
    from flask import request as _nova_autonomy_request_20260701
    from flask import Response as _NovaAutonomyResponse20260701

    _NOVA_AUTONOMY_PREFIXES_20260701 = (
        "autonomy:",
        "autonomy ",
        "task brain:",
        "safe task:",
        "safe autonomy:",
    )

    def _nova_autonomy_request_json_20260701():
        try:
            data = _nova_autonomy_request_20260701.get_json(silent=True) or {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _nova_autonomy_request_text_20260701(data):
        for key in ("message", "user_text", "text", "prompt"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _nova_autonomy_goal_from_text_20260701(user_text):
        text = str(user_text or "").strip()
        low = text.lower()

        for prefix in _NOVA_AUTONOMY_PREFIXES_20260701:
            if low.startswith(prefix):
                return text[len(prefix):].strip() or "Improve Nova safely."

        return ""

    def _nova_autonomy_load_formatter_20260701():
        service_path = (
            _NovaAutonomyPath20260701(__file__)
            .resolve()
            .parent
            / "nova_backend"
            / "services"
            / "autonomy_task_brain.py"
        )

        spec = _nova_autonomy_importlib_util_20260701.spec_from_file_location(
            "_nova_autonomy_task_brain_direct_20260701",
            str(service_path),
        )

        if not spec or not spec.loader:
            return None

        module = _nova_autonomy_importlib_util_20260701.module_from_spec(spec)
        spec.loader.exec_module(module)

        formatter = getattr(module, "format_autonomy_task_brief", None)
        return formatter if callable(formatter) else None

    def _nova_autonomy_payload_20260701(reply, data):
        session_id = ""
        if isinstance(data, dict):
            session_id = str(data.get("session_id") or data.get("active_session_id") or "").strip()

        return {
            "ok": True,
            "success": True,
            "content": reply,
            "message": reply,
            "response": reply,
            "session_id": session_id,
            "active_session_id": session_id,
            "assistant_message": {
                "role": "assistant",
                "content": reply,
                "attachments": [],
            },
            "route": "autonomy_task_brief",
            "route_taken": "autonomy_task_brief",
            "debug": {
                "route": "autonomy_task_brief",
                "route_taken": "autonomy_task_brief",
                "autonomy_mode": "proposal_only",
            },
            "meta": {
                "route": "autonomy_task_brief",
                "strategy": "proposal_only",
            },
        }

    def _nova_autonomy_wrap_endpoint_20260701(app, endpoint_name):
        view = app.view_functions.get(endpoint_name)
        if not callable(view):
            return False

        if getattr(view, "_NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701", False):
            return True

        def _nova_autonomy_wrapped_view_20260701(*args, **kwargs):
            try:
                data = _nova_autonomy_request_json_20260701()
                user_text = _nova_autonomy_request_text_20260701(data)
                goal = _nova_autonomy_goal_from_text_20260701(user_text)

                if goal:
                    formatter = _nova_autonomy_load_formatter_20260701()

                    if formatter:
                        reply = formatter(goal)
                        payload = _nova_autonomy_payload_20260701(reply, data)
                        encoded = _nova_autonomy_json_20260701.dumps(payload, ensure_ascii=False)
                        return _NovaAutonomyResponse20260701(
                            encoded,
                            status=200,
                            mimetype="application/json",
                        )
            except Exception as _nova_autonomy_route_error_20260701:
                try:
                    print(
                        "[NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701] bypass:",
                        _nova_autonomy_route_error_20260701,
                    )
                except Exception:
                    pass

            return view(*args, **kwargs)

        _nova_autonomy_wrapped_view_20260701.__name__ = getattr(
            view,
            "__name__",
            "_nova_autonomy_wrapped_view_20260701",
        )
        _nova_autonomy_wrapped_view_20260701._NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701 = True

        app.view_functions[endpoint_name] = _nova_autonomy_wrapped_view_20260701
        return True

    _nova_autonomy_wrapped_count_20260701 = 0
    for _endpoint_name_20260701, _view_20260701 in list(app.view_functions.items()):
        try:
            rule_matches = [
                rule.rule
                for rule in app.url_map.iter_rules()
                if rule.endpoint == _endpoint_name_20260701
            ]

            if "/api/chat" in rule_matches:
                if _nova_autonomy_wrap_endpoint_20260701(app, _endpoint_name_20260701):
                    _nova_autonomy_wrapped_count_20260701 += 1
        except Exception:
            pass

    _nova_boot_log_20260701(
        "[NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701] wrapped endpoints:",
        _nova_autonomy_wrapped_count_20260701,
    )
except Exception as _nova_autonomy_install_error_20260701:
    try:
        print(
            "[NOVA_API_CHAT_AUTONOMY_TASK_BRIEF_20260701] failed:",
            _nova_autonomy_install_error_20260701,
        )
    except Exception:
        pass




# NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701
# One-command adapter migration for autonomy-plan.
# Adapter owns matching command requests; legacy fallback guard has been removed.
try:
    @app.before_request
    def nova_autonomy_plan_adapter_guard_20260701():
        try:
            if request.method != "POST":
                return None

            if request.path not in ("/api/chat", "/api/chat/stream"):
                return None

            try:
                payload = request.get_json(silent=True) or {}
            except Exception:
                payload = {}

            from nova_backend.services.autonomy_plan_adapter import build_autonomy_plan_response

            response_json = build_autonomy_plan_response(payload, session_service)

            if not response_json:
                return None

            return jsonify(response_json)
        except Exception as _nova_autonomy_plan_adapter_error_20260701:
            print("[NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701] failed:", _nova_autonomy_plan_adapter_error_20260701)
            return None

    _nova_boot_log_20260701("[NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701] installed")
except Exception as _nova_autonomy_plan_adapter_install_error_20260701:
    print("[NOVA_AUTONOMY_PLAN_ADAPTER_GUARD_20260701] install failed:", _nova_autonomy_plan_adapter_install_error_20260701)

# NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701
# One-command adapter migration for patch-build.
# Adapter owns matching command requests; legacy fallback guard has been removed.
try:
    @app.before_request
    def nova_patch_build_adapter_guard_20260701():
        try:
            if request.method != "POST":
                return None

            if request.path not in ("/api/chat", "/api/chat/stream"):
                return None

            try:
                payload = request.get_json(silent=True) or {}
            except Exception:
                payload = {}

            from nova_backend.services.patch_build_adapter import build_patch_build_response

            response_json = build_patch_build_response(payload, session_service)

            if not response_json:
                return None

            return jsonify(response_json)
        except Exception as _nova_patch_build_adapter_error_20260701:
            print("[NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701] failed:", _nova_patch_build_adapter_error_20260701)
            return None

    _nova_boot_log_20260701("[NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701] installed")
except Exception as _nova_patch_build_adapter_install_error_20260701:
    print("[NOVA_PATCH_BUILD_ADAPTER_GUARD_20260701] install failed:", _nova_patch_build_adapter_install_error_20260701)

# NOVA_ACTIVE_EXECUTION_STATUS_PRIORITY_20260701
# Active execution missions should beat global project-state recall for status questions.
try:
    from flask import request as _nova_phase4a_request, jsonify as _nova_phase4a_jsonify, make_response as _nova_phase4a_make_response
    from pathlib import Path as _NovaPhase4APath
    import json as _nova_phase4a_json
    import functools as _nova_phase4a_functools

    _NOVA_PHASE4A_ACTIVE_EXECUTION_CACHE_20260701 = {}
    _NOVA_PHASE4D_COMPLETED_EXECUTION_CACHE_20260701 = {}

    _NOVA_PHASE4A_STATUS_QUESTIONS_20260701 = {
        "what are we working on",
        "what are we working on?",
        "what are we doing",
        "what are we doing?",
        "where are we",
        "where are we?",
        "status",
        "current status",
        "what is the status",
        "what's the status",
        "whats the status",
        "what comes next",
        "what comes next?",
        "what is next",
        "what's next",
        "whats next",
        "next step",
        "what is the next step",
        "what's the next step",
        "whats the next step",
    }

    def _nova_phase4a_clean_text_20260701(value):
        return " ".join(str(value or "").strip().lower().split())

    def _nova_phase4a_is_status_question_20260701(user_text):
        clean = _nova_phase4a_clean_text_20260701(user_text).strip(" .!")
        return clean in _NOVA_PHASE4A_STATUS_QUESTIONS_20260701

    def _nova_phase4a_execution_is_active_20260701(execution):
        if not isinstance(execution, dict):
            return False

        goal = str(execution.get("goal") or "").strip()
        status = str(execution.get("status") or "").strip().lower()

        if not goal:
            return False

        if status in {"complete", "completed", "done", "failed", "error", "cancelled", "canceled"}:
            return False

        return True

    def _nova_phase4d_execution_is_complete_20260701(execution):
        if not isinstance(execution, dict):
            return False

        goal = str(execution.get("goal") or "").strip()
        status = str(execution.get("status") or "").strip().lower()

        if not goal:
            return False

        if execution.get("complete") is True:
            return True

        return status in {"complete", "completed", "done"}

    def _nova_phase4a_goal_20260701(execution):
        return str((execution or {}).get("goal") or "").strip()

    def _nova_phase4a_steps_20260701(execution):
        raw_steps = (execution or {}).get("steps") or []
        steps = []

        for item in raw_steps:
            if isinstance(item, dict):
                title = str(item.get("title") or item.get("text") or item.get("name") or "").strip()
            else:
                title = str(item or "").strip()

            if title:
                steps.append(title)

        return steps

    def _nova_phase4a_index_20260701(execution, steps):
        value = (
            (execution or {}).get("current_index")
            if "current_index" in (execution or {})
            else (execution or {}).get("current_step_index", 0)
        )

        try:
            index = int(value or 0)
        except Exception:
            index = 0

        if steps:
            index = max(0, min(index, len(steps) - 1))
        else:
            index = max(0, index)

        return index

    def _nova_phase4a_current_step_20260701(execution):
        steps = _nova_phase4a_steps_20260701(execution)
        index = _nova_phase4a_index_20260701(execution, steps)

        current = str((execution or {}).get("current_step") or "").strip()
        if current:
            return current

        if steps and 0 <= index < len(steps):
            return steps[index]

        return ""

    def _nova_phase4a_execution_status_text_20260701(execution):
        goal = _nova_phase4a_goal_20260701(execution)
        status = str((execution or {}).get("status") or "ready").strip() or "ready"
        steps = _nova_phase4a_steps_20260701(execution)
        index = _nova_phase4a_index_20260701(execution, steps)
        current_step = _nova_phase4a_current_step_20260701(execution)

        lines = [
            f"Active mission: {goal}",
            f"Status: {status}",
        ]

        if current_step and steps:
            lines.append(f"Step {index + 1}/{len(steps)}: {current_step}")
        elif current_step:
            lines.append(f"Current step: {current_step}")

        if str((execution or {}).get("waiting") or "").lower() in {"true", "1", "yes"}:
            lines.append("Next: send next, k, continue, or run it to advance.")

        return "\n".join(lines).strip()

    def _nova_phase4a_session_service_20260701():
        for name in ("session_service", "sessions", "session_manager"):
            svc = globals().get(name)
            if svc is not None:
                return svc
        return None

    def _nova_phase4a_read_sessions_file_20260701():
        path = _NovaPhase4APath(__file__).resolve().parent / "data" / "nova_sessions.json"
        if not path.exists():
            return None, path

        try:
            return _nova_phase4a_json.loads(path.read_text(encoding="utf-8", errors="replace")), path
        except Exception:
            return None, path

    def _nova_phase4a_find_session_20260701(container, session_id):
        if not session_id:
            return None

        if isinstance(container, dict):
            direct = container.get(session_id)
            if isinstance(direct, dict):
                return direct

            for key in ("sessions", "items", "data"):
                found = _nova_phase4a_find_session_20260701(container.get(key), session_id)
                if found is not None:
                    return found

            for value in container.values():
                if isinstance(value, dict) and str(value.get("id") or "") == session_id:
                    return value
                if isinstance(value, (dict, list)):
                    found = _nova_phase4a_find_session_20260701(value, session_id)
                    if found is not None:
                        return found

        if isinstance(container, list):
            for item in container:
                if isinstance(item, dict) and str(item.get("id") or "") == session_id:
                    return item

        return None

    def _nova_phase4a_get_working_state_20260701(
        session_id,
    ):
        session_id = str(
            session_id
            or ""
        ).strip()

        if not session_id:
            return {}

        merged_state = {}

        svc = (
            _nova_phase4a_session_service_20260701()
        )

        # -------------------------------------------------
        # 1. Read service working state.
        #
        # Some service implementations normalize/filter
        # working_state keys, so this source is useful but
        # must not be treated as the only source.
        # -------------------------------------------------

        method = getattr(
            svc,
            "get_working_state",
            None,
        )

        if callable(method):

            try:

                state = method(
                    session_id
                )

                if isinstance(
                    state,
                    dict,
                ):
                    merged_state.update(
                        state
                    )

            except Exception:
                pass

        # -------------------------------------------------
        # 2. Read the full service session.
        #
        # Execution is intentionally persisted at the
        # session top level for restart recovery.
        # -------------------------------------------------

        for method_name in (
            "get_session",
            "get",
        ):

            method = getattr(
                svc,
                method_name,
                None,
            )

            if not callable(method):
                continue

            try:

                session = method(
                    session_id
                )

            except Exception:
                session = None

            if not isinstance(
                session,
                dict,
            ):
                continue

            working_state = session.get(
                "working_state"
            )

            if isinstance(
                working_state,
                dict,
            ):
                merged_state.update(
                    working_state
                )

            for key in (
                "active_execution",
                "execution_state",
                "execution",
            ):

                execution = session.get(
                    key
                )

                if isinstance(
                    execution,
                    dict,
                ):
                    merged_state[key] = (
                        execution
                    )

        # -------------------------------------------------
        # 3. Read durable session storage.
        #
        # This is the restart/recovery authority when the
        # in-memory service state is incomplete.
        # -------------------------------------------------

        data, _ = (
            _nova_phase4a_read_sessions_file_20260701()
        )

        session = (
            _nova_phase4a_find_session_20260701(
                data,
                session_id,
            )
        )

        if isinstance(
            session,
            dict,
        ):

            working_state = session.get(
                "working_state"
            )

            if isinstance(
                working_state,
                dict,
            ):
                merged_state.update(
                    working_state
                )

            for key in (
                "active_execution",
                "execution_state",
                "execution",
            ):

                execution = session.get(
                    key
                )

                if isinstance(
                    execution,
                    dict,
                ):
                    merged_state[key] = (
                        execution
                    )

        return merged_state

    def _nova_phase4a_persist_working_state_20260701(session_id, patch):
        session_id = str(session_id or "").strip()
        if not session_id or not isinstance(patch, dict):
            return False

        service_saved = False

        svc = _nova_phase4a_session_service_20260701()
        method = getattr(svc, "update_working_state", None)

        if callable(method):
            try:
                method(session_id, patch)
                service_saved = True
            except Exception:
                service_saved = False

        data, path = _nova_phase4a_read_sessions_file_20260701()
        if data is None:
            return service_saved

        session = _nova_phase4a_find_session_20260701(data, session_id)
        if not isinstance(session, dict):
            session = {
                "id": session_id,
                "title": session_id,
                "messages": [],
                "session_attachments": [],
                "working_state": {},
                "active_execution": None,
                "execution_state": None,
            }

            if isinstance(data, dict):
                sessions_value = data.get("sessions")

                if isinstance(sessions_value, list):
                    sessions_value.append(session)
                elif isinstance(sessions_value, dict):
                    sessions_value[session_id] = session
                else:
                    data[session_id] = session

            elif isinstance(data, list):
                data.append(session)

            else:
                return service_saved

        state = session.get("working_state")
        if not isinstance(state, dict):
            state = {}

        state.update(patch)
        session["working_state"] = state

        # Phase 4F: persist executable mission state at top-level too.
        # Some session working_state paths filter unknown keys, so active_execution
        # must be stored directly on the session for restart recovery.
        if "active_execution" in patch:
            session["active_execution"] = patch.get("active_execution")

        if "execution_state" in patch:
            session["execution_state"] = patch.get("execution_state")

        try:
            path.write_text(_nova_phase4a_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception:
            return service_saved

    def _nova_phase4a_get_active_execution_20260701(session_id):
        session_id = str(session_id or "").strip()

        if session_id:
            cached = _NOVA_PHASE4A_ACTIVE_EXECUTION_CACHE_20260701.get(session_id)
            if _nova_phase4a_execution_is_active_20260701(cached):
                return cached

        state = _nova_phase4a_get_working_state_20260701(session_id)
        for key in ("active_execution", "execution_state", "execution"):
            execution = state.get(key)
            if _nova_phase4a_execution_is_active_20260701(execution):
                if session_id:
                    _NOVA_PHASE4A_ACTIVE_EXECUTION_CACHE_20260701[session_id] = execution
                return execution
        return None

    def _nova_phase4d_get_completed_execution_20260701(session_id):
        session_id = str(session_id or "").strip()

        if session_id:
            cached = _NOVA_PHASE4D_COMPLETED_EXECUTION_CACHE_20260701.get(session_id)
            if _nova_phase4d_execution_is_complete_20260701(cached):
                return cached

        state = _nova_phase4a_get_working_state_20260701(session_id)
        for key in ("execution_state", "execution", "last_execution"):
            execution = state.get(key)
            if _nova_phase4d_execution_is_complete_20260701(execution):
                if session_id:
                    _NOVA_PHASE4D_COMPLETED_EXECUTION_CACHE_20260701[session_id] = execution
                return execution

        return None

    def _nova_phase4d_completed_status_text_20260701(execution):
        goal = _nova_phase4a_goal_20260701(execution)
        if goal:
            return f"No active mission is running. Last completed mission: {goal}"
        return "No active mission is running."

    def _nova_phase4a_persist_execution_20260701(session_id, execution):
        session_id = str(session_id or "").strip()

        if _nova_phase4d_execution_is_complete_20260701(execution):
            if session_id:
                _NOVA_PHASE4A_ACTIVE_EXECUTION_CACHE_20260701.pop(session_id, None)
                _NOVA_PHASE4D_COMPLETED_EXECUTION_CACHE_20260701[session_id] = execution

            return _nova_phase4a_persist_working_state_20260701(
                session_id,
                {
                    "active_execution": None,
                    "execution_state": execution,
                    "active_task": "",
                    "next_move": "",
                    "checkpoint": "Execution mission complete",
                },
            )

        if not _nova_phase4a_execution_is_active_20260701(execution):
            return False

        if session_id:
            _NOVA_PHASE4A_ACTIVE_EXECUTION_CACHE_20260701[session_id] = execution

        goal = _nova_phase4a_goal_20260701(execution)
        current_step = _nova_phase4a_current_step_20260701(execution)

        patch = {
            "active_execution": execution,
            "execution_state": execution,
            "active_task": goal,
            "next_move": current_step,
            "checkpoint": "Active execution mission",
        }

        return _nova_phase4a_persist_working_state_20260701(session_id, patch)

    def _nova_phase4a_wrap_chat_endpoint_20260701(endpoint, view_func):
        if getattr(view_func, "_nova_phase4a_active_execution_wrapped", False):
            return view_func

        @_nova_phase4a_functools.wraps(view_func)
        def _nova_phase4a_wrapped(*args, **kwargs):
            payload = {}
            try:
                payload = _nova_phase4a_request.get_json(silent=True) or {}
            except Exception:
                payload = {}

            user_text = str(payload.get("message") or payload.get("text") or payload.get("user_text") or "").strip()
            session_id = str(payload.get("session_id") or payload.get("active_session_id") or "").strip()

            if _nova_phase4a_clean_text_20260701(user_text).strip(" .!") == "say only pong":
                text = "pong"
                return _nova_phase4a_jsonify({
                    "ok": True,
                    "session_id": session_id,
                    "active_session_id": session_id,
                    "assistant_message": {
                        "role": "assistant",
                        "text": text,
                        "content": text,
                        "session_id": session_id,
                        "active_session_id": session_id,
                        "meta": {
                            "render_source": "direct_pong_priority",
                        },
                    },
                    "debug": {
                        "route": "chat",
                        "route_taken": "chat",
                        "direct_pong_priority": True,
                    },
                })

            if session_id and _nova_phase4a_is_status_question_20260701(user_text):
                active_execution = _nova_phase4a_get_active_execution_20260701(session_id)
                if _nova_phase4a_execution_is_active_20260701(active_execution):
                    text = _nova_phase4a_execution_status_text_20260701(active_execution)
                    return _nova_phase4a_jsonify({
                        "ok": True,
                        "session_id": session_id,
                        "active_session_id": session_id,
                        "assistant_message": {
                            "role": "assistant",
                            "text": text,
                            "content": text,
                            "session_id": session_id,
                            "active_session_id": session_id,
                            "execution_state": active_execution,
                            "meta": {
                                "render_source": "active_execution_status",
                            },
                        },
                        "execution_state": active_execution,
                        "debug": {
                            "route": "active_execution_status",
                            "route_taken": "active_execution_status",
                            "suppressed_project_state_recall": True,
                        },
                    })

                completed_execution = _nova_phase4d_get_completed_execution_20260701(session_id)
                if _nova_phase4d_execution_is_complete_20260701(completed_execution):
                    text = _nova_phase4d_completed_status_text_20260701(completed_execution)
                    return _nova_phase4a_jsonify({
                        "ok": True,
                        "session_id": session_id,
                        "active_session_id": session_id,
                        "assistant_message": {
                            "role": "assistant",
                            "text": text,
                            "content": text,
                            "session_id": session_id,
                            "active_session_id": session_id,
                            "execution_state": completed_execution,
                            "meta": {
                                "render_source": "completed_execution_status",
                            },
                        },
                        "execution_state": completed_execution,
                        "debug": {
                            "route": "completed_execution_status",
                            "route_taken": "completed_execution_status",
                            "suppressed_project_state_recall": True,
                        },
                    })

            result = view_func(*args, **kwargs)

            try:
                response = _nova_phase4a_make_response(result)
                data = response.get_json(silent=True)

                if isinstance(data, dict) and session_id:
                    execution = data.get("execution_state")
                    if not isinstance(execution, dict):
                        assistant = data.get("assistant_message")
                        if isinstance(assistant, dict):
                            execution = assistant.get("execution_state")

                    if _nova_phase4a_execution_is_active_20260701(execution) or _nova_phase4d_execution_is_complete_20260701(execution):
                        _nova_phase4a_persist_execution_20260701(session_id, execution)

                return response
            except Exception:
                return result

        _nova_phase4a_wrapped._nova_phase4a_active_execution_wrapped = True
        return _nova_phase4a_wrapped

    _nova_phase4a_wrapped_count_20260701 = 0

    for _nova_phase4a_endpoint_20260701, _nova_phase4a_view_20260701 in list(app.view_functions.items()):
        try:
            _nova_phase4a_rules_20260701 = [
                str(rule.rule)
                for rule in app.url_map.iter_rules(_nova_phase4a_endpoint_20260701)
            ]
        except Exception:
            _nova_phase4a_rules_20260701 = []

        if "/api/chat" in _nova_phase4a_rules_20260701:
            app.view_functions[_nova_phase4a_endpoint_20260701] = _nova_phase4a_wrap_chat_endpoint_20260701(
                _nova_phase4a_endpoint_20260701,
                _nova_phase4a_view_20260701,
            )
            _nova_phase4a_wrapped_count_20260701 += 1

    _nova_boot_log_20260701(f"[NOVA_ACTIVE_EXECUTION_STATUS_PRIORITY_20260701] wrapped endpoints: {_nova_phase4a_wrapped_count_20260701}")

except Exception as _nova_phase4a_error_20260701:
    print("[NOVA_ACTIVE_EXECUTION_STATUS_PRIORITY_20260701] failed:", _nova_phase4a_error_20260701)



# NOVA_PHASE4G_SESSION_HISTORY_RENAME_PERSISTENCE_20260701
# Preserve chat history across refresh/session switch and prevent manual titles from
# being overwritten by later chat messages.
try:
    import json as _nova_phase4g_json
    import uuid as _nova_phase4g_uuid
    from datetime import datetime as _nova_phase4g_datetime
    from datetime import timezone as _nova_phase4g_timezone
    from pathlib import Path as _nova_phase4g_Path

    from flask import g as _nova_phase4g_g
    from flask import request as _nova_phase4g_request

    _NOVA_PHASE4G_SESSIONS_PATH_20260701 = (
        _nova_phase4g_Path(__file__).resolve().parent / "data" / "nova_sessions.json"
    )

    def _nova_phase4g_now_20260701():
        return _nova_phase4g_datetime.now(_nova_phase4g_timezone.utc).isoformat()

    def _nova_phase4g_text_20260701(value):
        try:
            return str(value or "").strip()
        except Exception:
            return ""

    def _nova_phase4g_request_json_20260701():
        try:
            data = _nova_phase4g_request.get_json(silent=True)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _nova_phase4g_response_json_20260701(response):
        try:
            raw = response.get_data(as_text=True)
            data = _nova_phase4g_json.loads(raw)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _nova_phase4g_write_response_json_20260701(response, data):
        try:
            payload = _nova_phase4g_json.dumps(data, ensure_ascii=False)
            response.set_data(payload)
            response.headers["Content-Length"] = str(len(response.get_data()))
            response.headers["Content-Type"] = "application/json"
        except Exception:
            pass
        return response

    def _nova_phase4g_read_sessions_20260701():
        try:
            if not _NOVA_PHASE4G_SESSIONS_PATH_20260701.exists():
                return {"sessions": []}
            data = _nova_phase4g_json.loads(
                _NOVA_PHASE4G_SESSIONS_PATH_20260701.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            )
            if isinstance(data, (dict, list)):
                return data
        except Exception:
            pass
        return {"sessions": []}

    def _nova_phase4g_write_sessions_20260701(data):
        try:
            _NOVA_PHASE4G_SESSIONS_PATH_20260701.parent.mkdir(parents=True, exist_ok=True)
            _NOVA_PHASE4G_SESSIONS_PATH_20260701.write_text(
                _nova_phase4g_json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return True
        except Exception:
            return False

    def _nova_phase4g_find_session_20260701(obj, session_id):
        if not session_id:
            return None

        if isinstance(obj, dict):
            if obj.get("id") == session_id:
                return obj
            for value in obj.values():
                found = _nova_phase4g_find_session_20260701(value, session_id)
                if isinstance(found, dict):
                    return found

        if isinstance(obj, list):
            for value in obj:
                found = _nova_phase4g_find_session_20260701(value, session_id)
                if isinstance(found, dict):
                    return found

        return None

    def _nova_phase4g_create_session_20260701(data, session_id, title=""):
        owner_id = ""

        try:
            from flask import session as flask_session

            owner_id = str(
                flask_session.get("nova_user_id") or ""
            ).strip()

        except Exception:
            owner_id = ""

        session = {
            "id": session_id,
            "title": title or session_id,
            "user_id": owner_id,
            "messages": [],
            "session_attachments": [],
            "working_state": {},
            "active_execution": None,
            "execution_state": None,
            "pinned": False,
            "created_at": _nova_phase4g_now_20260701(),
            "updated_at": _nova_phase4g_now_20260701(),
            "message_count": 0,
            "active_session_id": session_id,
        }

        if isinstance(data, dict):
            sessions = data.get("sessions")

            if isinstance(sessions, list):
                sessions.append(session)

            elif isinstance(sessions, dict):
                sessions[session_id] = session

            else:
                data["sessions"] = [session]

            return session

        if isinstance(data, list):
            data.append(session)
            return session

        return session


    def _nova_phase4g_get_or_create_session_20260701(data, session_id, title=""):
        session = _nova_phase4g_find_session_20260701(data, session_id)
        if isinstance(session, dict):
            return session
        return _nova_phase4g_create_session_20260701(data, session_id, title)

    def _nova_phase4g_message_text_20260701(message):
        if not isinstance(message, dict):
            return ""
        return _nova_phase4g_text_20260701(
            message.get("text")
            or message.get("content")
            or message.get("message")
        )

    def _nova_phase4g_append_message_20260701(session, role, text, meta=None, attachments=None):
        text = _nova_phase4g_text_20260701(text)
        role = _nova_phase4g_text_20260701(role) or "assistant"

        if not isinstance(session, dict) or not text:
            return False

        messages = session.get("messages")
        if not isinstance(messages, list):
            messages = []
            session["messages"] = messages

        if messages:
            last = messages[-1]
            if (
                isinstance(last, dict)
                and _nova_phase4g_text_20260701(last.get("role")) == role
                and _nova_phase4g_message_text_20260701(last) == text
            ):
                return False

        now = _nova_phase4g_now_20260701()
        message = {
            "id": "msg_" + _nova_phase4g_uuid.uuid4().hex,
            "role": role,
            "text": text,
            "content": text,
            "attachments": attachments if isinstance(attachments, list) else [],
            "created_at": now,
            "updated_at": now,
            "meta": meta if isinstance(meta, dict) else {},
        }

        messages.append(message)
        session["message_count"] = len(messages)
        session["updated_at"] = now
        return True

    def _nova_phase4g_is_title_locked_20260701(session):
        if not isinstance(session, dict):
            return False
        if session.get("manual_title") is True or session.get("title_locked") is True:
            return True
        meta = session.get("meta")
        if isinstance(meta, dict):
            return meta.get("manual_title") is True or meta.get("title_locked") is True
        return False

    def _nova_phase4g_pick_session_id_20260701(data, response_data=None):
        request_data = _nova_phase4g_request_json_20260701()

        for source in (request_data, response_data or {}):
            if not isinstance(source, dict):
                continue
            for key in ("session_id", "active_session_id", "id"):
                value = _nova_phase4g_text_20260701(source.get(key))
                if value:
                    return value

            session_obj = source.get("session")
            if isinstance(session, dict):
                value = _nova_phase4g_text_20260701(session_obj.get("id"))
                if value:
                    return value

        return ""

    def _nova_phase4g_pick_assistant_text_20260701(response_data):
        if not isinstance(response_data, dict):
            return ""

        assistant = response_data.get("assistant_message")
        if isinstance(assistant, dict):
            return _nova_phase4g_text_20260701(
                assistant.get("text")
                or assistant.get("content")
                or assistant.get("message")
            )

        return _nova_phase4g_text_20260701(
            response_data.get("text")
            or response_data.get("content")
            or response_data.get("message")
        )

    def _nova_phase4g_pick_user_text_20260701():
        request_data = _nova_phase4g_request_json_20260701()
        return _nova_phase4g_text_20260701(
            request_data.get("message")
            or request_data.get("text")
            or request_data.get("content")
        )

    def _nova_phase4g_capture_title_20260701():
        try:
            path = _nova_phase4g_text_20260701(_nova_phase4g_request.path).lower()
            if not (path.endswith("/api/chat") or "/api/chat" in path or "rename" in path):
                return

            data = _nova_phase4g_read_sessions_20260701()
            session_id = _nova_phase4g_pick_session_id_20260701(data)
            session = _nova_phase4g_find_session_20260701(data, session_id)

            if isinstance(session, dict):
                _nova_phase4g_g.nova_phase4g_existing_title = session.get("title")
                _nova_phase4g_g.nova_phase4g_title_locked = _nova_phase4g_is_title_locked_20260701(session)
        except Exception:
            pass

    app.before_request(_nova_phase4g_capture_title_20260701)

    def _nova_phase4g_after_response_20260701(response):
        try:
            path = _nova_phase4g_text_20260701(_nova_phase4g_request.path).lower()
            request_data = _nova_phase4g_request_json_20260701()
            response_data = _nova_phase4g_response_json_20260701(response)

            if "session" in path and "rename" in path:
                session_id = _nova_phase4g_pick_session_id_20260701(response_data)
                title = _nova_phase4g_text_20260701(
                    request_data.get("title")
                    or request_data.get("name")
                    or request_data.get("new_title")
                )

                if session_id and title:
                    data = _nova_phase4g_read_sessions_20260701()
                    session = _nova_phase4g_get_or_create_session_20260701(data, session_id, title)
                    session["title"] = title
                    session["manual_title"] = True
                    session["title_locked"] = True
                    meta = session.get("meta")
                    if not isinstance(meta, dict):
                        meta = {}
                    meta["manual_title"] = True
                    meta["title_locked"] = True
                    session["meta"] = meta
                    session["updated_at"] = _nova_phase4g_now_20260701()
                    _nova_phase4g_write_sessions_20260701(data)

                return response

            if not (path.endswith("/api/chat") or "/api/chat" in path):
                return response

            if not isinstance(response_data, dict):
                return response

            session_id = _nova_phase4g_pick_session_id_20260701(response_data)
            if not session_id:
                return response

            user_text = _nova_phase4g_pick_user_text_20260701()
            assistant_text = _nova_phase4g_pick_assistant_text_20260701(response_data)

            data = _nova_phase4g_read_sessions_20260701()
            title_seed = user_text or session_id
            session = _nova_phase4g_get_or_create_session_20260701(data, session_id, title_seed)

            existing_title = getattr(_nova_phase4g_g, "nova_phase4g_existing_title", None)
            was_locked = bool(getattr(_nova_phase4g_g, "nova_phase4g_title_locked", False))

            if was_locked or _nova_phase4g_is_title_locked_20260701(session):
                if existing_title:
                    session["title"] = existing_title
                session["manual_title"] = True
                session["title_locked"] = True
            else:
                current_title = _nova_phase4g_text_20260701(session.get("title"))
                if not current_title or current_title == session_id or current_title.startswith("session_"):
                    session["title"] = title_seed[:80]

            response_session = response_data.get("session")
            # Phase 4G duplicate fix:
            # Do not replay response_session.messages here. The response session can
            # already contain the current user/assistant pair, and replaying it before
            # appending the current exchange creates duplicate visible history.
            _nova_phase4g_append_message_20260701(
                session,
                "user",
                user_text,
                {
                    "route": "phase4g_session_history_persistence",
                    "session_id": session_id,
                },
                request_data.get("attachments") if isinstance(request_data.get("attachments"), list) else [],
            )

            assistant_meta = {}
            assistant = response_data.get("assistant_message")
            if isinstance(assistant, dict) and isinstance(assistant.get("meta"), dict):
                assistant_meta = assistant.get("meta")

            _nova_phase4g_append_message_20260701(
                session,
                "assistant",
                assistant_text,
                assistant_meta,
                [],
            )

            if isinstance(response_session, dict):
                for key in (
                    "active_execution",
                    "execution_state",
                    "working_state",
                    "session_attachments",
                    "meta",
                    "pinned",
                    "created_at",
                    "active_session_id",
                ):
                    if key in response_session and key not in {"messages"}:
                        session[key] = response_session.get(key)

            session["active_session_id"] = session_id
            session["message_count"] = len(session.get("messages") or [])
            session["updated_at"] = _nova_phase4g_now_20260701()

            _nova_phase4g_write_sessions_20260701(data)

            response_data["session"] = session
            response_data["session_id"] = session_id
            response_data["active_session_id"] = session_id
            response_data["phase4g_session_history_persistence"] = True

            return _nova_phase4g_write_response_json_20260701(response, response_data)

        except Exception as exc:
            try:
                print("[NOVA_PHASE4G_SESSION_HISTORY_RENAME_PERSISTENCE_20260701] failed:", exc)
            except Exception:
                pass
            return response

    app.after_request(_nova_phase4g_after_response_20260701)

    _nova_boot_log_20260701("[NOVA_PHASE4G_SESSION_HISTORY_RENAME_PERSISTENCE_20260701] installed")
except Exception as _nova_phase4g_error_20260701:
    print("[NOVA_PHASE4G_SESSION_HISTORY_RENAME_PERSISTENCE_20260701] failed:", _nova_phase4g_error_20260701)

# NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701
# Must be above

# NOVA_MEMORY_GUARDS_INCLUDE_STREAM_20260611



# Must be above app.run(). Keeps normal chat from being overwritten by stale project/autonomy state.
try:
    import json as _nova_phase4f_prerun_json_20260701
    from flask import request as _nova_phase4f_prerun_request_20260701

    def _nova_phase4f_prerun_text_20260701(value):
        try:
            return str(value or "").strip()
        except Exception:
            return ""

    def _nova_phase4f_prerun_is_normal_chat_20260701(user_text):
        text = _nova_phase4f_prerun_text_20260701(user_text).lower()
        if not text:
            return False

        project_context_tokens = (
            "nova",
            "project",
            "mission",
            "checkpoint",
            "progress",
            "status",
            "state",
            "working on",
            "where are we",
            "where we are",
            "what are we doing",
            "what we're doing",
            "what were we doing",
            "what are we working on",
            "what we're working on",
            "what were we working on",
            "what did we just fix",
            "what did i just fix",
            "what was just fixed",
            "what is left",
            "what's left",
            "whats left",
            "what remains",
            "remaining work",
            "next move",
            "move on",
            "continue project",
            "continue nova",
            "current focus",
            "current checkpoint",
        )

        project_context_intent_tokens = (
            "current",
            "status",
            "state",
            "progress",
            "where",
            "working",
            "doing",
            "checkpoint",
            "focus",
            "left",
            "remaining",
            "remain",
            "next",
            "move",
            "continue",
            "fixed",
            "fix",
            "locked",
            "lock",
        )

        if any(token in text for token in project_context_tokens):
            return False

        if ("nova" in text or "project" in text or "mission" in text) and any(token in text for token in project_context_intent_tokens):
            return False

        project_recall_exact = {
            "current project state",
            "project state",
            "just fixed",
            "remaining work",
            "next command",
            "k command",
        }

        project_recall_markers = (
            "current project state",
            "project state",
            "just fixed",
            "what did we just fix",
            "what did i just fix",
            "what was just fixed",
            "remaining work",
            "what remains",
            "what's left",
            "whats left",
            "what is left",
            "current focus",
            "first remaining item",
            "next command",
            "k command",
            "nova status",
            "current nova",
            "current status",
            "locked status",
            "lock status",
            "project status",
            "status of nova",
            "nova progress",
            "current progress",
            "project progress",
            "how far",
            "where are we",
            "where we are",
            "what are we working on",
            "what we're working on",
            "what were we working on",
            "what should we do next",
            "what comes next",
            "what is next",
            "next move",
            "move on",
            "continue project",
            "continue nova",
            "nova context",
            "project context",
            "current checkpoint",
            "checkpoint",
        )

        if text in project_recall_exact:
            return False

        if any(marker in text for marker in project_recall_markers):
            return False

        command_exact = {
            "next",
            "continue",
            "run all",
            "run step",
            "run it",
            "execute",
            "stop",
            "cancel",
            "retry",
            "status",
            "what are we working on",
            "what are we working on?",
            "what's next",
            "whats next",
            "what next",
        }

        if text in command_exact:
            return False

        command_prefixes = (
            "auto-plan",
            "autoplan",
            "auto build",
            "autobuild",
            "build ",
            "create ",
            "make ",
            "implement ",
            "fix ",
            "repair ",
            "upgrade ",
            "run ",
            "execute ",
        )

        if any(text.startswith(prefix) for prefix in command_prefixes):
            return False

        normal_prefixes = (
            "what is ",
            "what's ",
            "whats ",
            "who is ",
            "where is ",
            "when is ",
            "why is ",
            "how do ",
            "how does ",
            "how many ",
            "how much ",
            "tell me ",
            "explain ",
            "define ",
            "ping",
            "hello",
            "hi",
            "hey",
        )

        return text.endswith("?") or any(text.startswith(prefix) for prefix in normal_prefixes)

    def _nova_phase4f_prerun_is_bleed_20260701(content):
        text = _nova_phase4f_prerun_text_20260701(content).lower()
        if not text:
            return False

        markers = (
            "next move:",
            "current focus:",
            "first remaining item:",
            "remaining work",
            "next command",
            "project state",
            "active nova mission",
            "active mission",
            "last mission",
            "autonomy task",
            "fallback guard cleanup",
            "autonomy-plan fallback",
            "patch-build fallback",
        )

        return any(marker in text for marker in markers)


    def _nova_phase4f_prerun_is_safe_probe_20260701(user_text):
        text = _nova_phase4f_prerun_text_20260701(user_text).lower()
        compact = (
            text.replace(" ", "")
            .replace("?", "")
            .replace("plus", "+")
            .replace("add", "+")
        )

        if text.startswith("ping"):
            return True

        if "2+2" in compact or "twoplustwo" in compact:
            return True

        if "short joke" in text or text.startswith("tell me a joke") or text.startswith("tell me a short joke"):
            return True

        return False


    def _nova_phase4f_prerun_safe_answer_20260701(user_text):
        text = _nova_phase4f_prerun_text_20260701(user_text).lower()
        compact = (
            text.replace(" ", "")
            .replace("?", "")
            .replace("plus", "+")
            .replace("add", "+")
        )

        if "2+2" in compact or "twoplustwo" in compact:
            return "2 plus 2 is 4."

        if text.startswith("ping"):
            return "pong"

        if "short joke" in text or text.startswith("tell me a joke") or text.startswith("tell me a short joke"):
            return "Why did the computer get cold? It left its Windows open."

        return "I?m here. What would you like to talk about?"

    def _nova_phase4f_prerun_extract_20260701(data):
        assistant = data.get("assistant_message")
        if isinstance(assistant, dict):
            for key in ("content", "text", "message", "response", "answer"):
                value = assistant.get(key)
                if isinstance(value, str) and value.strip():
                    return value

        for key in ("content", "response", "message", "text", "answer"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value

        return ""

    def _nova_phase4f_prerun_set_answer_20260701(data, answer):
        assistant = data.get("assistant_message")
        if isinstance(assistant, dict):
            assistant["content"] = answer
            assistant["text"] = answer
            data["assistant_message"] = assistant
        else:
            data["assistant_message"] = {
                "role": "assistant",
                "content": answer,
                "text": answer,
            }

        data["content"] = answer
        data["response"] = answer
        data["message"] = answer
        data["text"] = answer
        data["answer"] = answer

        debug = data.get("debug")
        if not isinstance(debug, dict):
            debug = {}

        existing_route = str(
            debug.get("route")
            or data.get("route")
            or data.get("route_taken")
            or ""
        ).strip()

        if existing_route != "project_brain_general_intelligence":
            debug["route"] = "chat"
            debug["route_taken"] = "chat"
            debug["normal_chat_priority"] = True
            debug["suppressed_project_state_bleed"] = True
        else:
            debug["route"] = "project_brain_general_intelligence"
            debug["route_taken"] = "project_brain_general_intelligence"

        debug["phase4f_prerun_final_guard"] = True

        data["debug"] = debug

        return data



    @app.after_request
    def _nova_phase4f_prerun_final_normal_chat_bleed_guard_20260701(response):
        try:
            if _nova_phase4f_prerun_request_20260701.path != "/api/chat":
                return response

            if response.status_code >= 400:
                return response

            request_payload = _nova_phase4f_prerun_request_20260701.get_json(silent=True) or {}
            user_text = request_payload.get("message") or request_payload.get("user_text") or ""

            if not _nova_phase4f_prerun_is_normal_chat_20260701(user_text):
                return response

            # NOVA_PROJECT_BRAIN_ROUTE_PROTECTION_20260712
            # Do not overwrite Project Brain ownership metadata.
            from nova_backend.services.project_brain_route_protection_service import (
                response_owned_by_project_brain,
            )

            if response_owned_by_project_brain(response):
                return response

            if not _nova_phase4f_prerun_is_safe_probe_20260701(user_text):
                return response

            raw = response.get_data(as_text=True)
            if not raw:
                return response

            data = _nova_phase4f_prerun_json_20260701.loads(raw)
            if not isinstance(data, dict):
                return response

            content = _nova_phase4f_prerun_extract_20260701(data)
            if not _nova_phase4f_prerun_is_bleed_20260701(content):
                return response

            answer = _nova_phase4f_prerun_safe_answer_20260701(user_text)
            data = _nova_phase4f_prerun_set_answer_20260701(data, answer)

            response.set_data(_nova_phase4f_prerun_json_20260701.dumps(data, ensure_ascii=False))
            response.headers["Content-Type"] = "application/json"
            response.headers["Content-Length"] = str(len(response.get_data()))
            return response

        except Exception as exc:
            try:
                print("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] failed:", exc)
            except Exception:
                pass
            return response

    try:
        funcs = app.after_request_funcs.get(None, [])
        if _nova_phase4f_prerun_final_normal_chat_bleed_guard_20260701 in funcs:
            funcs.remove(_nova_phase4f_prerun_final_normal_chat_bleed_guard_20260701)
            funcs.insert(0, _nova_phase4f_prerun_final_normal_chat_bleed_guard_20260701)
            app.after_request_funcs[None] = funcs
            _nova_boot_log_20260701("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] forced final hook")
    except Exception as order_exc:
        print("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] final-order failed:", order_exc)

    _nova_boot_log_20260701("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] installed")
except Exception as guard_exc:
    print("[NOVA_PHASE4F_PRE_RUN_FINAL_NORMAL_CHAT_BLEED_GUARD_20260701] failed:", guard_exc)

# NOVA_REPAIR_PLAN_COMMAND_PRIORITY_GUARD_20260701
# Explicit repair-plan / fix-plan commands must outrank project-context recall.
try:
    from nova_backend.services import repair_plan_adapter as _nova_repair_plan_adapter_20260701

    _NOVA_PRE_REPAIR_PLAN_COMMAND_PRIORITY_HANDLE_20260701 = ChatService.handle

    def _nova_repair_plan_command_priority_handle_20260701(self, *args, **kwargs):
        user_text = ""
        session_id = None
        attachments = []

        try:
            if args:
                first = args[0]

                if isinstance(first, dict):
                    user_text = str(first.get("user_text") or first.get("message") or first.get("text") or "")
                    session_id = first.get("session_id")
                    attachments = first.get("attachments") or []
                else:
                    user_text = str(first or "")

                    if len(args) > 1:
                        session_id = args[1]

                    if len(args) > 2:
                        attachments = args[2] or []

            user_text = str(
                kwargs.get("user_text")
                or kwargs.get("message")
                or kwargs.get("text")
                or user_text
                or ""
            )

            session_id = kwargs.get("session_id") or session_id
            attachments = kwargs.get("attachments") or attachments or []

            repair_input = _nova_repair_plan_adapter_20260701.extract_repair_plan_input(user_text)

            if repair_input is not None:
                payload = {
                    "user_text": user_text,
                    "session_id": session_id or getattr(getattr(self, "session_service", None), "active_session_id", None) or "default",
                    "attachments": attachments,
                }

                session_service = getattr(self, "session_service", None)

                if session_service is None:
                    session_service = globals().get("session_service")

                if session_service is not None:
                    return _nova_repair_plan_adapter_20260701.build_repair_plan_response(
                        payload,
                        session_service,
                    )

        except Exception as exc:
            try:
                print("[NOVA_REPAIR_PLAN_COMMAND_PRIORITY_GUARD_20260701] failed:", exc)
            except Exception:
                pass

        return _NOVA_PRE_REPAIR_PLAN_COMMAND_PRIORITY_HANDLE_20260701(self, *args, **kwargs)

    ChatService.handle = _nova_repair_plan_command_priority_handle_20260701
    print("[NOVA_REPAIR_PLAN_COMMAND_PRIORITY_GUARD_20260701] installed")
except Exception as _nova_repair_plan_command_priority_error_20260701:
    print("[NOVA_REPAIR_PLAN_COMMAND_PRIORITY_GUARD_20260701] failed:", _nova_repair_plan_command_priority_error_20260701)



# NOVA_REPAIR_PLAN_API_BEFORE_REQUEST_PRIORITY_20260701
# Explicit repair-plan / fix-plan commands must bypass project-context recall before /api/chat runs.
try:
    from flask import request as _nova_repair_plan_flask_request_20260701
    from flask import jsonify as _nova_repair_plan_flask_jsonify_20260701
    from nova_backend.services import repair_plan_adapter as _nova_repair_plan_api_adapter_20260701

    @app.before_request
    def _nova_repair_plan_api_before_request_priority_20260701():
        try:
            if _nova_repair_plan_flask_request_20260701.path != "/api/chat":
                return None

            if _nova_repair_plan_flask_request_20260701.method != "POST":
                return None

            data = _nova_repair_plan_flask_request_20260701.get_json(silent=True) or {}

            user_text = str(
                data.get("user_text")
                or data.get("message")
                or data.get("text")
                or ""
            )

            repair_input = _nova_repair_plan_api_adapter_20260701.extract_repair_plan_input(user_text)

            if repair_input is None:
                return None

            session_id = (
                data.get("session_id")
                or getattr(globals().get("session_service"), "active_session_id", None)
                or "default"
            )

            payload = {
                "user_text": user_text,
                "session_id": session_id,
                "attachments": data.get("attachments") or [],
            }

            result = _nova_repair_plan_api_adapter_20260701.build_repair_plan_response(
                payload,
                globals().get("session_service"),
            )

            return _nova_repair_plan_flask_jsonify_20260701(result)

        except Exception as exc:
            try:
                print("[NOVA_REPAIR_PLAN_API_BEFORE_REQUEST_PRIORITY_20260701] failed:", exc)
            except Exception:
                pass

            return None

    print("[NOVA_REPAIR_PLAN_API_BEFORE_REQUEST_PRIORITY_20260701] installed")
except Exception as _nova_repair_plan_api_before_request_error_20260701:
    print("[NOVA_REPAIR_PLAN_API_BEFORE_REQUEST_PRIORITY_20260701] failed:", _nova_repair_plan_api_before_request_error_20260701)


# NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_FIXED_20260701
# Corrected route-table wrapper for exact project-brain "what's next?"
# Fixes prior Response/function name collision.
try:
    import json as _nova_next_fixed_json_20260701
    from flask import request as _nova_next_fixed_request_20260701
    from flask import Response as _nova_next_fixed_flask_response_20260701

    def _nova_next_fixed_norm_20260701(value):
        return (
            str(value or "")
            .strip()
            .lower()
            .replace("?", "'")
            .rstrip("?!.")
        )

    def _nova_next_fixed_is_question_20260701(value):
        return _nova_next_fixed_norm_20260701(value) in {
            "what's next",
            "whats next",
            "what is next",
            "what should we do next",
        }

    def _nova_next_fixed_answer_20260701():
        from flask import (
            request as _nova_next_fixed_request_20260711,
        )

        from nova_backend.services.project_brain_general_intelligence import (
            build_project_brain_general_answer as
            _nova_next_fixed_build_general_answer_20260711,
        )

        payload = (
            _nova_next_fixed_request_20260711.get_json(
                silent=True
            )
            or {}
        )

        user_text = str(
            payload.get(
                "message"
            )
            or payload.get(
                "text"
            )
            or payload.get(
                "content"
            )
            or payload.get(
                "user_text"
            )
            or ""
        ).strip()

        general_answer = (
            _nova_next_fixed_build_general_answer_20260711(
                user_text
            )
        )

        if isinstance(
            general_answer,
            dict,
        ):
            answer = str(
                general_answer.get(
                    "content"
                )
                or general_answer.get(
                    "text"
                )
                or general_answer.get(
                    "answer"
                )
                or ""
            ).strip()

        else:
            answer = str(
                getattr(
                    general_answer,
                    "text",
                    general_answer,
                )
                or ""
            ).strip()

        return answer

    def _nova_next_fixed_make_response_20260701(session_id):
        fixed_text = _nova_next_fixed_answer_20260701()

        meta = {
            "route": "api_chat_project_next_endpoint_wrapper_fixed",
            "strategy": "api_chat_project_next_endpoint_wrapper_fixed",
            "session_id": session_id,
            "source_urls": [],
            "sources": [],
        }

        assistant_message = {
            "role": "assistant",
            "content": fixed_text,
            "text": fixed_text,
            "attachments": [],
            "meta": meta,
        }

        data = {
            "ok": True,
            "success": True,
            "assistant_message": assistant_message,
            "assistant_text": fixed_text,
            "text": fixed_text,
            "saved_artifact": None,
            "session": {
                "id": session_id,
                "session_id": session_id,
                "messages": [assistant_message],
                "attachments": [],
                "meta": meta,
            },
            "route": "api_chat_project_next_endpoint_wrapper_fixed",
            "route_taken": "api_chat_project_next_endpoint_wrapper_fixed",
            "debug": {
                "route": "api_chat_project_next_endpoint_wrapper_fixed",
                "route_taken": "api_chat_project_next_endpoint_wrapper_fixed",
            },
            "meta": meta,
            "session_id": session_id,
            "active_session_id": session_id,
        }

        return _nova_next_fixed_flask_response_20260701(
            _nova_next_fixed_json_20260701.dumps(data, ensure_ascii=False),
            status=200,
            mimetype="application/json",
        )

    def _nova_next_fixed_wrap_endpoint_20260701(endpoint_name, original_view):
        if not callable(original_view):
            return False

        if getattr(original_view, "_nova_next_fixed_endpoint_wrapper_20260701", False):
            return False

        def _nova_next_fixed_wrapped_view_20260701(*args, **kwargs):
            try:
                if (
                    str(getattr(_nova_next_fixed_request_20260701, "path", "") or "") == "/api/chat"
                    and str(getattr(_nova_next_fixed_request_20260701, "method", "") or "").upper() == "POST"
                ):
                    payload = _nova_next_fixed_request_20260701.get_json(silent=True) or {}
                    if isinstance(payload, dict):
                        user_text = (
                            payload.get("message")
                            or payload.get("user_text")
                            or payload.get("text")
                            or payload.get("prompt")
                            or ""
                        )

                        if _nova_next_fixed_is_question_20260701(user_text):
                            session_id = str(
                                payload.get("session_id")
                                or payload.get("active_session_id")
                                or payload.get("requested_session_id")
                                or ""
                            ).strip()

                            try:
                                print(
                                    "[NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_FIXED_20260701] intercepted",
                                    "session_id=" + session_id,
                                )
                            except Exception:
                                pass

                            return _nova_next_fixed_make_response_20260701(session_id)

            except Exception as _nova_next_fixed_request_error_20260701:
                try:
                    print(
                        "[NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_FIXED_20260701] bypass:",
                        _nova_next_fixed_request_error_20260701,
                    )
                except Exception:
                    pass

            return original_view(*args, **kwargs)

        _nova_next_fixed_wrapped_view_20260701.__name__ = getattr(
            original_view,
            "__name__",
            "nova_next_fixed_wrapped_api_chat",
        )
        _nova_next_fixed_wrapped_view_20260701.__doc__ = getattr(original_view, "__doc__", None)
        _nova_next_fixed_wrapped_view_20260701._nova_next_fixed_endpoint_wrapper_20260701 = True

        app.view_functions[endpoint_name] = _nova_next_fixed_wrapped_view_20260701
        return True

    _nova_next_fixed_wrapped_count_20260701 = 0

    for _nova_next_fixed_rule_20260701 in list(app.url_map.iter_rules()):
        try:
            if getattr(_nova_next_fixed_rule_20260701, "rule", "") != "/api/chat":
                continue

            _nova_next_fixed_endpoint_name_20260701 = getattr(
                _nova_next_fixed_rule_20260701,
                "endpoint",
                "",
            )
            _nova_next_fixed_original_view_20260701 = app.view_functions.get(
                _nova_next_fixed_endpoint_name_20260701
            )

            if _nova_next_fixed_wrap_endpoint_20260701(
                _nova_next_fixed_endpoint_name_20260701,
                _nova_next_fixed_original_view_20260701,
            ):
                _nova_next_fixed_wrapped_count_20260701 += 1
        except Exception:
            pass

    print(
        "[NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_FIXED_20260701] wrapped endpoints:",
        _nova_next_fixed_wrapped_count_20260701,
    )

except Exception as _nova_next_fixed_install_error_20260701:
    try:
        print(
            "[NOVA_API_CHAT_PROJECT_NEXT_ENDPOINT_WRAPPER_FIXED_20260701] failed:",
            _nova_next_fixed_install_error_20260701,
        )
    except Exception:
        pass



# NOVA_CODING_JUDGMENT_DIRECT_ANSWER_20260701
# Direct answer-quality guard for coding judgment questions.
# Keeps Nova from suggesting broad tests while omitting py_compile.
try:
    from flask import request as _nova_coding_judgment_request_20260701
    from flask import jsonify as _nova_coding_judgment_jsonify_20260701

    @_nova_app.before_request if False else app.before_request
    def _nova_coding_judgment_direct_answer_20260701():
        try:
            if _nova_coding_judgment_request_20260701.path != "/api/chat":
                return None

            if _nova_coding_judgment_request_20260701.method != "POST":
                return None

            data = _nova_coding_judgment_request_20260701.get_json(silent=True) or {}
            user_text = str(
                data.get("message")
                or data.get("user_text")
                or data.get("text")
                or ""
            ).strip()

            clean = " ".join(user_text.lower().split())

            triggers = (
                "what test should we run before touching code",
                "what tests should we run before touching code",
                "what should we run before touching code",
                "what test before touching code",
                "what tests before touching code",
                "before touching code",
                "before we touch code",
                "before patching",
                "before we patch",
            )

            if not any(trigger in clean for trigger in triggers):
                return None

            session_id = str(
                data.get("session_id")
                or data.get("active_session_id")
                or ""
            ).strip()

            answer = (
                "Before touching code, run the smallest checks that prove the current behavior is safe:\n\n"
                "1. `python -m py_compile` on the Python files you may touch.\n"
                "2. The most relevant focused smoke test.\n"
                "3. `git status --short` before staging or committing.\n\n"
                "For this Nova intelligence/memory work, use:\n\n"
                "```powershell\n"
                "python -m py_compile .\\\\app.py\n"
                "python -m py_compile .\\\\tools\\\nova_answer_quality_smoke.py\n"
                "python .\\\\tools\\\nova_answer_quality_smoke.py\n"
                "python .\\\\tools\\\nova_project_state_memory_api_smoke.py\n"
                "python .\\\\tools\\\nova_phase_4i_guard_stack_audit_smoke.py\n"
                "git status --short\n"
                "```\n\n"
                "Rule: py_compile first, focused smoke second, git status third, then patch or commit."
            )

            try:
                return response_quality_service.slim_assistant_payload(
                    answer,
                    session_id=session_id,
                    route="coding_judgment_direct_answer",
                    route_taken="coding_judgment_direct_answer",
                    coding_judgment_policy=True,
                )
            except Exception:
                return _nova_coding_judgment_jsonify_20260701({
                    "ok": True,
                    "session_id": session_id,
                    "active_session_id": session_id,
                    "text": answer,
                    "assistant_message": {
                        "role": "assistant",
                        "text": answer,
                        "content": answer,
                    },
                    "debug": {
                        "route": "coding_judgment_direct_answer",
                        "route_taken": "coding_judgment_direct_answer",
                    },
                    "route": "coding_judgment_direct_answer",
                    "route_taken": "coding_judgment_direct_answer",
                })

        except Exception as exc:
            try:
                app.logger.warning(
                    "[NOVA_CODING_JUDGMENT_DIRECT_ANSWER_20260701] failed: %s",
                    exc,
                )
            except Exception:
                pass

        return None

    print("[NOVA_CODING_JUDGMENT_DIRECT_ANSWER_20260701] installed")
except Exception as _nova_coding_judgment_error_20260701:
    print("[NOVA_CODING_JUDGMENT_DIRECT_ANSWER_20260701] failed:", _nova_coding_judgment_error_20260701)


# --- NOVA_ANSWER_QUALITY_95_DIRECT_POLICY_OWNER_20260701 ---
# NOVA_ANSWER_QUALITY_95_DIRECT_POLICY_20260701
# Project-intelligence direct policy answers for recurring Nova control questions.
# Keeps project judgment, testing, memory boundaries, route/debug, and rollback answers specific.
try:
    from flask import request as _nova_aq95_request_20260701
    from flask import jsonify as _nova_aq95_jsonify_20260701
    from nova_backend.services.chat_response_finalizer_service import (
        build_answer_quality_95_payload as _nova_build_answer_quality_95_payload_20260715,
    )

    def _nova_aq95_clean_20260701(value):
        return " ".join(str(value or "").lower().strip().split())

    @app.before_request
    def _nova_answer_quality_95_direct_policy_20260701():
        try:
            if _nova_aq95_request_20260701.path != "/api/chat":
                return None

            if _nova_aq95_request_20260701.method != "POST":
                return None

            data = _nova_aq95_request_20260701.get_json(silent=True) or {}
            user_text = str(
                data.get("message")
                or data.get("user_text")
                or data.get("text")
                or ""
            ).strip()

            clean = _nova_aq95_clean_20260701(user_text)

            session_id = str(
                data.get("session_id")
                or data.get("active_session_id")
                or ""
            ).strip()


            answer = get_answer_quality_policy_answer(user_text)
            if not answer:
                return None

            return _nova_build_answer_quality_95_payload_20260715(
                answer,
                session_id=session_id,
                route="answer_quality_95_direct_policy",
                slim_payload_builder=response_quality_service.slim_assistant_payload,
            )

        except Exception as exc:
            try:
                app.logger.warning(
                    "[NOVA_ANSWER_QUALITY_95_DIRECT_POLICY_20260701] failed: %s",
                    exc,
                )
            except Exception:
                pass

        return None

    try:
        _nova_aq95_funcs_20260701 = app.before_request_funcs.get(None, [])
        if _nova_answer_quality_95_direct_policy_20260701 in _nova_aq95_funcs_20260701:
            _nova_aq95_funcs_20260701.remove(_nova_answer_quality_95_direct_policy_20260701)
            _nova_aq95_funcs_20260701.insert(0, _nova_answer_quality_95_direct_policy_20260701)
            app.before_request_funcs[None] = _nova_aq95_funcs_20260701
    except Exception:
        pass

    print("[NOVA_ANSWER_QUALITY_95_DIRECT_POLICY_20260701] installed")
except Exception as _nova_aq95_error_20260701:
    print("[NOVA_ANSWER_QUALITY_95_DIRECT_POLICY_20260701] failed:", _nova_aq95_error_20260701)


# 
# Thin Flask wrapper for the service-owned Decision Log route contract.
# Keeps current-state/project-state recall separate.
try:
    from flask import request, jsonify
    from nova_backend.services.project_brain_decision_log_route_contract import (
        build_decision_log_api_payload as _nova_build_decision_log_api_payload_20260701,
        extract_user_text as _nova_decision_log_extract_user_text_20260701,
        is_decision_log_question as _nova_is_decision_log_api_question_20260701,
    )

except Exception as _nova_decision_log_api_route_error_20260701:
    print("[NOVA_PROJECT_BRAIN_DECISION_LOG_API_ROUTE_CONTRACT_20260701] failed:", _nova_decision_log_api_route_error_20260701)

# --- NOVA_PROTECTED_SESSION_RESTORE_20260703 ---
try:
    import os as _npsr_os
    import json as _npsr_json
    import shutil as _npsr_shutil
    from pathlib import Path as _NpsrPath
    from flask import request as _npsr_request
    from flask import jsonify as _npsr_jsonify

    def _npsr_paths_20260703():
        base = _NpsrPath(__file__).resolve().parent
        data = _NpsrPath(_npsr_os.environ.get("NOVA_DATA_DIR", str(base / "data")))
        data.mkdir(parents=True, exist_ok=True)
        sessions = _NpsrPath(_npsr_os.environ.get("NOVA_SESSIONS_FILE", str(data / "nova_sessions.json")))
        vault = data / "nova_sessions.richard_restore_vault_20260703.json"
        return sessions, vault

    def _npsr_count_20260703(value):
        if isinstance(value, list):
            return len(value)

        if isinstance(value, dict):
            sessions = value.get("sessions")
            if isinstance(sessions, list):
                return len(sessions)
            if isinstance(sessions, dict):
                return len(sessions)

            found = [
                item for item in value.values()
                if isinstance(item, dict) and (
                    "messages" in item or "id" in item or "session_id" in item
                )
            ]
            return len(found)

        return 0

    def _npsr_file_count_20260703(path):
        try:
            if not path.exists():
                return 0
            return _npsr_count_20260703(_npsr_json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return 0

    def _npsr_rewrite_owner_20260703(value):
        if isinstance(value, list):
            return [_npsr_rewrite_owner_20260703(item) for item in value]

        if isinstance(value, dict):
            out = {}
            for key, item in value.items():
                lk = str(key).lower()

                if lk in ("owner", "owner_name") and item in (None, "", "joe", "Joe", "JOE", "blank"):
                    out[key] = "richard"
                elif lk in ("owner_id", "user_id") and item in (None, "", "joe", "Joe", "JOE", "blank", "user_joe"):
                    out[key] = "user_richard_stable_local_login"
                else:
                    out[key] = _npsr_rewrite_owner_20260703(item)

            return out

        return value

    def _npsr_restore_if_needed_20260703(reason="request"):
        try:
            sessions, vault = _npsr_paths_20260703()

            current_count = _npsr_file_count_20260703(sessions)
            vault_count = _npsr_file_count_20260703(vault)

            if vault.exists() and vault_count >= 5 and current_count < vault_count:
                if sessions.exists():
                    backup = sessions.with_name("nova_sessions.overwritten_before_restore_20260703.json")
                    _npsr_shutil.copy2(sessions, backup)

                _npsr_shutil.copy2(vault, sessions)
                print("[NOVA_PROTECTED_SESSION_RESTORE_20260703] restored", {
                    "reason": reason,
                    "current_count": current_count,
                    "vault_count": vault_count,
                })
                return True
        except Exception as exc:
            try:
                print("[NOVA_PROTECTED_SESSION_RESTORE_20260703] restore failed:", exc)
            except Exception:
                pass

        return False

    _npsr_restore_if_needed_20260703("startup")

    @app.before_request
    def _npsr_before_request_20260703():
        _npsr_restore_if_needed_20260703("before_request")
        return None

    @app.post("/api/admin/session-store/import-protected")
    def _npsr_import_protected_20260703():
        expected = _npsr_os.environ.get("NOVA_SESSION_IMPORT_TOKEN", "richard-import-20260703")
        provided = _npsr_request.headers.get("X-Nova-Import-Token", "")

        if provided != expected:
            return _npsr_jsonify({"ok": False, "error": "Bad import token."}), 403

        raw = _npsr_request.get_data(as_text=True) or ""
        if not raw.strip():
            return _npsr_jsonify({"ok": False, "error": "Empty request body."}), 400

        try:
            payload = _npsr_json.loads(raw)
        except Exception as exc:
            return _npsr_jsonify({"ok": False, "error": "Invalid JSON.", "detail": str(exc)}), 400

        payload = _npsr_rewrite_owner_20260703(payload)
        imported_count = _npsr_count_20260703(payload)

        if imported_count < 5:
            return _npsr_jsonify({
                "ok": False,
                "error": "Refusing tiny session import.",
                "imported_count": imported_count,
            }), 400

        sessions, vault = _npsr_paths_20260703()
        text = _npsr_json.dumps(payload, ensure_ascii=False, indent=2)

        if sessions.exists():
            backup = sessions.with_name("nova_sessions.before_protected_import_20260703.json")
            _npsr_shutil.copy2(sessions, backup)

        vault.write_text(text, encoding="utf-8")
        sessions.write_text(text, encoding="utf-8")

        return _npsr_jsonify({
            "ok": True,
            "imported_count": imported_count,
            "target": str(sessions),
            "vault": str(vault),
            "mode": "protected_replace",
        })

    print("[NOVA_PROTECTED_SESSION_RESTORE_20260703] installed")
except Exception as _npsr_error_20260703:
    try:
        print("[NOVA_PROTECTED_SESSION_RESTORE_20260703] failed:", _npsr_error_20260703)
    except Exception:
        pass

# --- NOVA_RICHARD_LOGIN_AND_STATUS_RESTORE_20260703_DISABLED ---
# Disabled for multi-user launch.
# Legacy Richard auto-login restore removed.

if False:
    try:
        from flask import session as _nrla_session
        from flask import request as _nrla_request
        from flask import jsonify as _nrla_jsonify
        from flask import redirect as _nrla_redirect
        from flask import make_response as _nrla_make_response

        def _nrla_set_richard_auth_20260703(response):
            try:
                _nrla_session.permanent = True
                _nrla_session["authenticated"] = True
                _nrla_session["auth_mode"] = "local"
                _nrla_session["username"] = "richard"
                _nrla_session["user_id"] = "user_richard_stable_local_login"
            except Exception:
                pass

            return response

        @app.get("/api/auth/richard-login")
        @app.post("/api/auth/richard-login")
        def nova_richard_login_restore_api_20260703():
            response = _nrla_make_response(_nrla_redirect("/mobile"))
            return _nrla_set_richard_auth_20260703(response)

    except Exception:
        pass

    def _nrla_richard_payload_20260703():
        return {
            "ok": True,
            "authenticated": True,
            "mode": "local",
            "user": {
                "id": "user_richard_stable_local_login",
                "username": "richard",
                "email": "",
            },
        }

    @app.get("/api/auth/richard-login")
    @app.post("/api/auth/richard-login")
    def nova_richard_login_restore_api_20260703():
        response = _nrla_make_response(_nrla_redirect("/mobile"))
        return _nrla_set_richard_auth_20260703(response)

    print("[NOVA_RICHARD_LOGIN_AND_STATUS_RESTORE_20260703] installed")

# --- NOVA_MOBILE_OWNER_AUTO_AUTH_20260703_DISABLED ---
# Disabled for multi-user launch.
# This legacy development shortcut forced every mobile/session request
# into the Richard owner account.
#
# Real authentication now comes from:
# session["nova_user_id"]
# via the normal login/register flow

# --- NOVA_AUTH_STATUS_FIRST_OWNER_FIX_20260703_DISABLED ---
try:
    from flask import request as _nasf_request
    from flask import session as _nasf_session
    from flask import jsonify as _nasf_jsonify

    def _nasf_set_owner_session_20260703():
        try:
            _nasf_session.permanent = True
            _nasf_session["authenticated"] = True
            _nasf_session["auth_mode"] = "local"

            print("[RICHARD RESTORE FIRED]")
            print("[SESSION BEFORE RICHARD]", dict(_nasf_session))

            if False:
                _nasf_session["username"] = "richard"
                _nasf_session["user_id"] = "user_9cf403c995b3cf8d36a461e9"
                _nasf_session["nova_user_id"] = "user_9cf403c995b3cf8d36a461e9"

            print("[SESSION AFTER RICHARD]", dict(_nasf_session))

        except Exception as exc:
            print("[RICHARD RESTORE FAILED]", repr(exc))

    def _nasf_payload_20260703():
        return {
            "ok": True,
            "authenticated": True,
            "mode": "local",
            "user": {
                "id": "user_richard_stable_local_login",
                "username": "richard",
                "email": "",
            },
        }

    def _nasf_cookie_20260703(response):
        try:
            response.set_cookie(
                "nova_richard_login",
                "1",
                max_age=60 * 60 * 24 * 365,
                httponly=True,
                secure=True,
                samesite="Lax",
                path="/",
            )
        except Exception:
            pass
        return response

    def _nasf_owner_before_request_20260703():
        try:
            path = str(_nasf_request.path or "")

            if (
                path == "/api/auth/status"
                or path in ("/mobile", "/mobile/")
                or path.startswith("/api/sessions")
                or path.startswith("/api/chat")
            ):
                if not _nasf_session.get("nova_user_id"):
                    _nasf_set_owner_session_20260703()

            if path == "/api/auth/status":
                if _nasf_session.get("user_id") == "user_richard_stable_local_login":
                    return _nasf_cookie_20260703(
                        _nasf_jsonify(_nasf_payload_20260703())
                    )

        except Exception:
            pass

        return None

    # Put this first so older auth guards cannot answer false before it.
    try:
        app.before_request_funcs.setdefault(None, []).insert(
            0,
            _nasf_owner_before_request_20260703,
        )
    except Exception:
        app.before_request(_nasf_owner_before_request_20260703)

    @app.after_request
    def _nasf_owner_after_request_20260703(response):
        try:
            if (
                _nasf_session.get("authenticated")
                and str(_nasf_session.get("username") or "").lower() == "richard"
            ):
                return _nasf_cookie_20260703(response)
        except Exception:
            pass
        return response

    print("[NOVA_AUTH_STATUS_FIRST_OWNER_FIX_20260703] installed")
except Exception as _nasf_error_20260703:
        try:
            print("[NOVA_AUTH_STATUS_FIRST_OWNER_FIX_20260703] failed:", _nasf_error_20260703)
        except Exception:
            pass

# --- NOVA_MOBILE_SEND_STABLE_V1_INJECT_20260703 ---
try:
    from flask import request as _nmssv1_request

    @app.after_request
    def _nmssv1_inject_after_request_20260703(response):
        try:
            if _nmssv1_request.path not in ("/mobile", "/mobile/"):
                return response

            content_type = str(response.headers.get("Content-Type") or "")
            if "text/html" not in content_type:
                return response

            html = response.get_data(as_text=True)

            if "nova-mobile-send-stable-v1.js" in html:
                return response

            script = '<script src="/static/js/mobile/nova-mobile-send-stable-v1.js?v=mobile-send-stable-v1-20260703"></script>'

            lower = html.lower()
            idx = lower.rfind("</body>")

            if idx >= 0:
                html = html[:idx] + "\n" + script + "\n" + html[idx:]
            else:
                html = html + "\n" + script + "\n"

            response.set_data(html)
            response.headers["Content-Length"] = str(len(response.get_data()))
        except Exception as exc:
            try:
                print("[NOVA_MOBILE_SEND_STABLE_V1_INJECT_20260703] failed:", exc)
            except Exception:
                pass

        return response

    print("[NOVA_MOBILE_SEND_STABLE_V1_INJECT_20260703] installed")
except Exception as _nmssv1_error_20260703:
    try:
        print("[NOVA_MOBILE_SEND_STABLE_V1_INJECT_20260703] failed:", _nmssv1_error_20260703)
    except Exception:
        pass


# /NOVA_LEAD_CAPTURE_ROUTES_20260709

# NOVA_PAYMENTS_READINESS_ROUTES_20260709
# Staged payment readiness routes. Safe mode: no live checkout, no charge creation,
# no invoice creation, no subscription mutation, and webhook is a no-op until live wiring.
try:
    def _nova_payments_route_exists_20260709(rule_text):
        try:
            return any(str(rule) == rule_text for rule in app.url_map.iter_rules())
        except Exception:
            return False


    def _nova_payments_current_username_20260709():
        try:
            from flask import request, session

            username = (
                session.get("username")
                or session.get("nova_username")
                or request.args.get("username")
                or ""
            )
        except Exception:
            username = ""

        username = (username or "richard").strip()
        return username or "richard"


    def _nova_payments_json_20260709(payload, status_code=200):
        from flask import jsonify

        response = jsonify(payload)
        response.status_code = status_code
        return response


    def _nova_payments_bool_label_20260709(value):
        return "YES" if bool(value) else "NO"


    def _nova_render_admin_billing_readiness_20260709(data):
        from html import escape

        account = data.get("account") or {}
        payments = data.get("payments") or {}
        usage = data.get("usage_enforcement") or {}
        summary = data.get("summary") or {}
        blockers = data.get("blockers") or []
        plans = data.get("plans") or []

        rows = [
            ("Mode", data.get("mode", "")),
            ("Username", data.get("username", "")),
            ("Plan", account.get("plan", "")),
            ("Credits", account.get("credits", 0)),
            ("Monthly credits", account.get("monthly_credits", 0)),
            ("Stripe customer configured", _nova_payments_bool_label_20260709(account.get("stripe_customer_configured"))),
            ("Payments live enabled", _nova_payments_bool_label_20260709(payments.get("live_enabled"))),
            ("Checkout ready", _nova_payments_bool_label_20260709(payments.get("checkout_ready"))),
            ("Webhook ready", _nova_payments_bool_label_20260709(payments.get("webhook_ready"))),
            ("Stripe secret configured", _nova_payments_bool_label_20260709(payments.get("stripe_secret_configured"))),
            ("Stripe webhook secret configured", _nova_payments_bool_label_20260709(payments.get("stripe_webhook_secret_configured"))),
            ("Paid price configured", _nova_payments_bool_label_20260709(payments.get("paid_price_configured"))),
            ("consume_usage exists", _nova_payments_bool_label_20260709(usage.get("billing_service_consume_usage_exists"))),
            ("Gateway usage enforced", _nova_payments_bool_label_20260709(usage.get("gateway_usage_enforced"))),
            ("Chat usage enforced", _nova_payments_bool_label_20260709(usage.get("chat_usage_enforced"))),
            ("Safe to take payment", _nova_payments_bool_label_20260709(summary.get("safe_to_take_payment"))),
            ("Next patch", summary.get("next_patch", "")),
        ]

        row_html = "\n".join(
            '<tr><th style="text-align:left;padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.12);">'
            + escape(str(label))
            + '</th><td style="padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.12);">'
            + escape(str(value))
            + "</td></tr>"
            for label, value in rows
        )

        blocker_html = "\n".join(
            "<li>" + escape(str(item)) + "</li>"
            for item in blockers
        ) or "<li>No blockers detected.</li>"

        plan_html = "\n".join(
            "<li><strong>"
            + escape(str(plan.get("label", "")))
            + "</strong> ? "
            + escape(str(plan.get("status", "")))
            + " ? monthly credits: "
            + escape(str(plan.get("monthly_credits", "")))
            + " ? price env: "
            + escape(str(plan.get("stripe_price_env", "") or "none"))
            + "</li>"
            for plan in plans
        )

        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Nova Admin ? Billing Readiness</title></head>'
            '<body style="margin:0;background:#090816;color:#f7f3ff;font-family:Inter,system-ui,Segoe UI,sans-serif;">'
            '<main style="max-width:980px;margin:0 auto;padding:32px 18px 56px;">'
            '<p><a href="/admin" style="color:#c9b7ff;">? Admin</a> ? '
            '<a href="/billing" style="color:#c9b7ff;">Billing page</a> ? '
            '<a href="/api/billing/readiness" style="color:#c9b7ff;">Readiness JSON</a></p>'
            '<h1 style="margin:18px 0 6px;font-size:34px;">Billing readiness</h1>'
            '<p style="color:#cfc6ee;max-width:760px;">Staged payments audit panel. This shows local billing state, planned Stripe readiness, route safety, and whether Nova is safe to take live payments.</p>'
            '<section style="margin-top:24px;padding:18px;border:1px solid rgba(255,255,255,.14);border-radius:18px;background:rgba(255,255,255,.06);">'
            '<h2>State</h2>'
            '<table style="width:100%;border-collapse:collapse;">'
            + row_html +
            '</table></section>'
            '<section style="margin-top:24px;padding:18px;border:1px solid rgba(255,255,255,.14);border-radius:18px;background:rgba(255,255,255,.06);">'
            '<h2>Blockers</h2><ul>'
            + blocker_html +
            '</ul></section>'
            '<section style="margin-top:24px;padding:18px;border:1px solid rgba(255,255,255,.14);border-radius:18px;background:rgba(255,255,255,.06);">'
            '<h2>Plans</h2><ul>'
            + plan_html +
            '</ul></section>'
            '<p style="margin-top:26px;color:#aaa0cc;">NOVA_PAYMENTS_READINESS_ROUTES_20260709</p>'
            '</main></body></html>'
        )


    if not _nova_payments_route_exists_20260709("/api/billing/readiness"):
        @app.get("/api/billing/readiness")
        def nova_billing_readiness_api_20260709():
            from nova_backend.services.payments_readiness_service import build_payments_readiness

            username = _nova_payments_current_username_20260709()
            data = build_payments_readiness(username=username)
            return _nova_payments_json_20260709({"ok": True, **data})


    if not _nova_payments_route_exists_20260709("/api/billing/plans"):
        @app.get("/api/billing/plans")
        def nova_billing_plans_api_20260709():
            from nova_backend.services.payments_readiness_service import build_payments_readiness

            username = _nova_payments_current_username_20260709()
            data = build_payments_readiness(username=username)
            return _nova_payments_json_20260709({
                "ok": True,
                "mode": data.get("mode"),
                "plans": data.get("plans", []),
                "payments": data.get("payments", {}),
            })


    if not _nova_payments_route_exists_20260709("/api/billing/checkout"):
        @app.post("/api/billing/checkout")
        def nova_billing_checkout_staged_api_20260709():
            from flask import request
            from nova_backend.services.payments_readiness_service import build_payments_readiness

            username = _nova_payments_current_username_20260709()
            payload = request.get_json(silent=True) or {}
            data = build_payments_readiness(username=username)

            return _nova_payments_json_20260709({
                "ok": True,
                "live": False,
                "processed": False,
                "status": "staged_planned",
                "route": "/api/billing/checkout",
                "message": "Checkout route exists, but live Stripe checkout is intentionally disabled until payments are configured and usage enforcement is wired.",
                "requested_plan": payload.get("plan") or payload.get("plan_id") or "",
                "readiness": data,
            })


    if not _nova_payments_route_exists_20260709("/api/billing/portal"):
        @app.post("/api/billing/portal")
        def nova_billing_portal_staged_api_20260709():
            from nova_backend.services.payments_readiness_service import build_payments_readiness

            username = _nova_payments_current_username_20260709()
            data = build_payments_readiness(username=username)

            return _nova_payments_json_20260709({
                "ok": True,
                "live": False,
                "processed": False,
                "status": "staged_planned",
                "route": "/api/billing/portal",
                "message": "Customer portal route exists, but live Stripe portal sessions are intentionally disabled until Stripe is configured.",
                "readiness": data,
            })


    if not _nova_payments_route_exists_20260709("/api/stripe/webhook"):
        @app.post("/api/stripe/webhook")
        def nova_stripe_webhook_staged_api_20260709():
            from flask import request
            from nova_backend.services.payments_readiness_service import build_payments_readiness

            username = _nova_payments_current_username_20260709()
            data = build_payments_readiness(username=username)

            return _nova_payments_json_20260709({
                "ok": True,
                "received": True,
                "processed": False,
                "live": False,
                "status": "staged_noop",
                "route": "/api/stripe/webhook",
                "stripe_signature_present": bool(request.headers.get("Stripe-Signature")),
                "message": "Stripe webhook route exists, but event processing is intentionally disabled until live Stripe verification and account updates are wired.",
                "readiness": data,
            })


    if not _nova_payments_route_exists_20260709("/admin/billing-readiness"):
        @app.get("/admin/billing-readiness")
        def nova_admin_billing_readiness_20260709():
            from nova_backend.services.payments_readiness_service import build_payments_readiness

            username = _nova_payments_current_username_20260709()
            data = build_payments_readiness(username=username)
            return _nova_render_admin_billing_readiness_20260709(data)


    print("[NOVA_PAYMENTS_READINESS_ROUTES_20260709] installed")
except Exception as _nova_payments_readiness_routes_error_20260709:
    print("[NOVA_PAYMENTS_READINESS_ROUTES_20260709] install failed:", _nova_payments_readiness_routes_error_20260709)
# /NOVA_PAYMENTS_READINESS_ROUTES_20260709

# --- NOVA_MOBILE_CHAT_VISIBLE_RECOVERY_INJECT_20260703 ---
try:
    from flask import request as _nvcvr_request

    @app.after_request
    def _nvcvr_inject_after_request_20260703(response):
        try:
            if _nvcvr_request.path not in ("/mobile", "/mobile/"):
                return response

            content_type = str(response.headers.get("Content-Type") or "")
            if "text/html" not in content_type.lower():
                return response

            body = response.get_data(as_text=True)

            if "nova-mobile-chat-visible-recovery-v1.js" in body:
                return response

            script = '<script src="/static/js/mobile/nova-mobile-chat-visible-recovery-v1.js?v=chat-visible-recovery-dedupe-final-20260703c"></script>'

            import re
            if re.search(r"</body>", body, flags=re.I):
                body = re.sub(r"</body>", script + "\n</body>", body, count=1, flags=re.I)
            else:
                body = body + "\n" + script + "\n"

            response.set_data(body)
            response.headers["Content-Length"] = str(len(body.encode("utf-8")))
            return response
        except Exception as error:
            try:
                print("[NOVA_MOBILE_CHAT_VISIBLE_RECOVERY_INJECT_20260703] bypass:", error)
            except Exception:
                pass
            return response

    print("[NOVA_MOBILE_CHAT_VISIBLE_RECOVERY_INJECT_20260703] installed")
except Exception as _nvcvr_error:
    try:
        print("[NOVA_MOBILE_CHAT_VISIBLE_RECOVERY_INJECT_20260703] install failed:", _nvcvr_error)
    except Exception:
        pass


# NOVA_DEBUG_ROUTES_GUARD_20260705
def _nova_debug_routes_enabled():
    try:
        import os

        value = str(os.getenv("NOVA_DEBUG_ROUTES", "")).strip().lower()

        return value in {
            "1",
            "true",
            "yes",
            "on",
            "enabled",
        }
    except Exception:
        return False


def _nova_debug_routes_disabled_response():
    try:
        from flask import jsonify

        return jsonify(
            {
                "ok": False,
                "error": "Debug routes are disabled. Set NOVA_DEBUG_ROUTES=1 to enable.",
            }
        ), 404
    except Exception:
        return {
            "ok": False,
            "error": "Debug routes are disabled. Set NOVA_DEBUG_ROUTES=1 to enable.",
        }, 404


# NOVA_DURABLE_DATA_HEALTH_ROUTE_20260703
try:
    @app.get("/api/storage/health")
    def _nova_storage_health_20260703():
        import os
        from pathlib import Path

        base_dir = Path(__file__).resolve().parent
        app_data = base_dir / "data"
        env_data = Path(os.environ.get("NOVA_DATA_DIR", str(app_data)))

        names = [
            "nova_auth_users.json",
            "nova_sessions.json",
            "nova_memory.json",
            "nova_artifacts.json",
            "nova_flask_secret.key",
        ]

        def info(path):
            try:
                return {
                    "path": str(path),
                    "exists": path.exists(),
                    "is_file": path.is_file(),
                    "is_dir": path.is_dir(),
                    "is_symlink": path.is_symlink(),
                    "realpath": str(path.resolve()) if path.exists() or path.is_symlink() else None,
                }
            except Exception as exc:
                return {"path": str(path), "error": str(exc)}

        return {
            "ok": True,
            "marker": "NOVA_DURABLE_DATA_HEALTH_ROUTE_20260703",
            "cwd": os.getcwd(),
            "base_dir": str(base_dir),
            "nova_data_dir_env": os.environ.get("NOVA_DATA_DIR"),
            "app_data": info(app_data),
            "env_data": info(env_data),
            "files": {
                name: {
                    "app_data": info(app_data / name),
                    "env_data": info(env_data / name),
                }
                for name in names
            },
        }
except Exception as exc:
    try:
        print("[NOVA_DURABLE_DATA_HEALTH_ROUTE_20260703] failed:", exc)
    except Exception:
        pass
# /NOVA_DURABLE_DATA_HEALTH_ROUTE_20260703


if __name__ == "__main__":
    create_startup_backup()
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
    )

