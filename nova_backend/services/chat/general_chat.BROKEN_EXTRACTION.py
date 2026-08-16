
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

    original_user_text = self.safe_str(user_text)

    text_lc = original_user_text.lower().strip()

    # NOVA_PROJECT_STATUS_DIRECT_ROUTE_20260607
    project_status_query = any(
        phrase in text_lc
        for phrase in [
            "what did we fix",
            "what we fixed",
            "explain what we fixed",
            "summarize what we fixed",
            "what did we do today",
            "what have we done today",
        ]
    )

    if project_status_query:
        assistant_text = (
            "Here is what we actually fixed today:\n\n"
            "- Fixed the mobile composer buttons so send, voice, attach, tools, and TTS stopped stretching.\n"
            "- Fixed the mojibukakke icon issue where broken encoded symbols were showing instead of clean icons.\n"
            "- Fixed the stale frontend cache issue where /mobile kept loading an old nova-mobile-app.js?v=attachment-payload-bridge-20260607204432 version.\n"
            "- Slimmed the mobile composer/input bar so the real input and main buttons are now 40px high.\n"
            "- Fixed the router bug where the word 'today' forced local project questions into web_fetch.\n\n"
            "Remaining issue: project status answers still need a real work-log system so Nova does not guess from old memories."
        )



        return self._finalize_response(
            session_id=session_id,
            user_text=original_user_text,
            user_msg=self._build_user_message(
                original_user_text,
                attachments=attachments,
            ),
            assistant_msg=assistant_msg,
            decision={
                "route": "project_status_direct",
                "mode": "project_status",
                "confidence": 1.0,
                "reasons": ["project_status_memory_bypass"],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": False,
            },
            saved_artifact=None,
        )


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

        if any(pattern in text_lc for pattern in identity_patterns):

            self._reinforce_memory(
                session_id=session_id,
                memory_text=(f"User identity/context: " f"{original_user_text}"),
                category="profile",
                amount=3,
            )

        if any(pattern in text_lc for pattern in preference_patterns):

            self._reinforce_memory(
                session_id=session_id,
                memory_text=(
                    f"User preference/correction: " f"{original_user_text}"
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

                detected_file = match.group(0).strip()

                break

        traceback_match = re.search(
            r'File "([^"]+)"',
            original_user_text,
            re.IGNORECASE,
        )

        if traceback_match:

            detected_file = str(traceback_match.group(1)).strip()

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

        if any(marker in text_lc for marker in bug_markers):

            detected_bug = original_user_text[:1200].strip()

        if detected_file:

            ws = self._get_working_state(session_id) or {}

            self._update_working_state(
                session_id,
                {
                    "current_file": detected_file,
                    "active_task": (ws.get("active_task") or "active debugging"),
                    "current_bug": detected_bug,
                    "checkpoint": (
                        "auto_bug_detected"
                        if detected_bug
                        else "auto_file_detected"
                    ),
                },
            )

            self._reinforce_memory(
                session_id=session_id,
                memory_text=(f"Current file: " f"{detected_file}"),
                category="operational",
                amount=2,
            )

            if detected_bug:

                self._reinforce_memory(
                    session_id=session_id,
                    memory_text=(f"Current bug: " f"{detected_bug[:500]}"),
                    category="correction",
                    amount=2,
                )

    except Exception as e:

        exec_debug(
            "AUTO_FILE_DETECTION_FAILED:",
            e,
        )

    if text_lc in {
        "what file are we in",
        "what fiel are we in",
        "which file",
        "current file",
        "what file",
        "what fiel",
        "what file we are in",
        "what file are we working in",
    }:

        effective_session_id = (
            str(locals().get("target_session_id") or "").strip()
            or str(session_id or "").strip()
            or str(getattr(self.session_service, "active_session_id", "") or "").strip()
        )

        ws = self._get_working_state(effective_session_id) or {}

        if not isinstance(ws, dict):
            ws = {}

        current_file = str(ws.get("current_file") or "").strip()

        if not current_file:
            current_file = "No active file is currently tracked."

        assistant_msg = self._build_assistant_message(
            text=(f"Current file:\n" f"{current_file}")
        )

        return self._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg={
                "role": "user",
                "text": user_text,
                "content": user_text,
                "attachments": attachments or [],
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
        effective_session_id = (
            str(locals().get("target_session_id") or "").strip()
            or str(session_id or "").strip()
            or str(getattr(self.session_service, "active_session_id", "") or "").strip()
        )

        ws = self._get_working_state(effective_session_id) or {}

        if not isinstance(ws, dict):
            ws = {}

        active_task = str(ws.get("active_task") or "").strip()

        if not active_task:
            active_task = "No active task is currently tracked."

        assistant_msg = self._build_assistant_message(
            text=(f"Active task:\n" f"{active_task}")
        )

        return self._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg={
                "role": "user",
                "text": user_text,
                "content": user_text,
                "attachments": attachments or [],
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
            if isinstance(s, dict) and str(s.get("id")) == str(session_id):
                session_messages = s.get("messages", [])
                break

        previous_user = ""

        user_messages = [
            m
            for m in session_messages
            if isinstance(m, dict) and m.get("role") == "user"
        ]

        if len(user_messages) >= 2:
            previous_user = str(user_messages[-2].get("text", "")).strip()

        if not previous_user:
            previous_user = "I could not find a previous message."

        assistant_msg = self._build_assistant_message(
            text=(f"Your previous message was: " f'"{previous_user}"')
        )

        return self._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg={
                "role": "user",
                "text": user_text,
                "content": user_text,
                "attachments": attachments or [],
                "meta": {},
            },
            assistant_msg=assistant_msg,
            saved_artifact=None,
        )

    assistant_text = ""
    assistant_msg = None

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
                memory_brain.append(f"{label}: {value}")

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
            x in text_lc for x in execution_keywords
        )

        # NOVA_SKIP_PROJECT_CONTEXT_FOR_INTERPRETED_NEWS_20260612
        # Clean public news/web queries must not be polluted with Nova project memory.
        # Example bad query before this guard:
        # "latest tucker carlson project aware context for nova ... news today"
        _skip_project_context_for_news = bool(
            getattr(self, "_skip_project_context_for_interpreted_news", False)
        )

        if memory_brain and should_attach_operational_context and not _skip_project_context_for_news:
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
        last_prompt = (
            self._get_session_meta(
                session_id,
                "last_image_prompt",
            )
            or "generate an image"
        )

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
        last_prompt = (
            self._get_session_meta(
                session_id,
                "last_image_prompt",
            )
            or ""
        )

        last_prompt = self.safe_str(last_prompt).strip()

        if not last_prompt or last_prompt in regen_commands:
            last_prompt = "generate an image"

        return self._handle_image_generation(
            prompt=last_prompt,
            session_id=session_id,
            parent_artifact_id=parent_artifact_id,
            source_type="regenerated",
        )

    if self._is_image_generation_request(user_text) and not self._nova_is_web_news_intent_20260609(user_text):
        return self._handle_image_generation(
            prompt=user_text,
            session_id=session_id,
            parent_artifact_id=(
                parent_artifact_id if "parent_artifact_id" in locals() else ""
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

    lowered = str(user_text or "").strip().lower()

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

if is_execution:
    decision = (
        decision
        if isinstance(decision, dict)
        else {}
    )

    decision["intent"] = "planning"

    if not decision.get("route"):
        decision["route"] = "execution"

    exec_debug(
        "FORCED EXECUTION PLANNING ROUTE",
        decision,
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
        "stop",
        "cancel",
    }:
        exec_debug(
            "EXECUTION INTERCEPT HIT",
            lowered,
        )

    execution_state = {}

    if decision and decision.get("intent") == "planning":
        execution_state = self.execution_handler.handle(
            user_text,
            session_id,
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
                session_obj = self.sessions.get_session(session_id) or {}

                session_obj["execution_state"] = execution_state

                session_obj["active_execution"] = (
                    execution_state
                    if (
                        isinstance(execution_state, dict)
                        and execution_state.get("steps")
                        and self.safe_str(execution_state.get("status")).lower()
                        != "complete"
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

        working_state = self._get_working_state(session_id) or {}

        execution_state = (
            execution_state if isinstance(execution_state, dict) else {}
        )

        mission_state = self._build_mission_state(
            working_state=working_state,
            execution_state=execution_state,
        )

        if execution_state.get("steps") and self.safe_str(
            execution_state.get("status")
        ).lower() in {
            "running",
            "adapting",
            "waiting",
        }:

            self._update_working_state(
                session_id,
                {
                    "mission": mission_state,
                    "active_task": user_text,
                    "next_move": "run_step",
                    "checkpoint": ("execution_plan_created"),
                    "execution_status": "running",
                },
            )

        if decision and decision.get("intent") == "planning":

            print(
                "EXECUTION PLAN RETURNING",
                execution_state,
            )

            return {
                "execution_state": execution_state,
                "route": "planner",
                "ok": True,
            }

        is_continue = text_lc.strip() in {
            "continue",
            "next",
            "run it",
            "go",
        }

    # SINGLE SOURCE OF TRUTH
    state = self._get_working_state(session_id) or {}
    session = self._get_session_payload(session_id)

    mission_mode = self.safe_str(state.get("mission_mode"))

    active_task = self.safe_str(state.get("active_task"))
    next_step = self.safe_str(state.get("next_move"))

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

    for item in dominant_memory:

        if not isinstance(item, dict):
            continue

        text = self.safe_str(
            item.get("text") or item.get("content")
        ).strip()

            if not text:
                continue

            text_lower = text.lower()

            if any(phrase in text_lower for phrase in blocked_internal_phrases):
                continue

            normalized = text_lower.strip()

            if normalized in seen_memory:
                continue

            seen_memory.add(normalized)

            memory_lines.append(f"- {text}")

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

        line_str = self.safe_str(line).strip()

        if not line_str:
            continue

        if "Recovered operational context" in line_str:
            continue

        clean_fallback.append(line_str)

    if _nova_has_image_attachment:
            text = (
                "\n".join(clean_fallback)
                or "No active working state is currently tracked."
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

        working_state = self._get_working_state(session_id) or {}

        persisted_execution_state = (
            self._load_execution_state(
                session_id
            )
        )

        if isinstance(
            persisted_execution_state, dict
        ) and persisted_execution_state.get("steps"):
            execution_state = persisted_execution_state
        else:
            execution_state = {}

        reconciled = self._reconcile_execution_state(
            session_id=session_id,
            working_state=working_state,
            execution_state=execution_state,
        )

        working_state = reconciled.get("working_state") or {}

        execution_state = reconciled.get("execution_state") or {}

        mission_state = self._build_mission_state(
            working_state=working_state,
            execution_state=execution_state,
        )

        assistant_text = self._format_mission_state(mission_state)

        return {
            "ok": True,
            "assistant_message": (
                self._build_assistant_message(
                    "No active working state is currently tracked."
                )
            ),
            "session": self._get_session_payload(session_id),
            "saved_artifact": None,
            "artifacts": [],
            "debug": {
                "route_taken": ("mission_state_continuity_suppressed"),
            },
        }

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

    isolated_routes = {
        self.ROUTE_WEB_FETCH,
        self.ROUTE_IMAGE_GENERATION,
    }

    # =========================
    # RUNTIME ROUTE
    # =========================

    if route == "runtime":

        runtime_command = (
            self.safe_str(decision.get("runtime_command")).strip().lower()
        )

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

                return self._build_assistant_message(text=str(runtime_result))

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

                if not runtime or not hasattr(
                    runtime,
                    "get_recent_replays",
                ):
                    return self._build_assistant_message(
                        text=str(
                            {
                                "ok": False,
                                "error": ("runtime_replay_unavailable"),
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

            elif text_lc.startswith("/runtime replay explain"):

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

                if not runtime or not hasattr(
                    runtime,
                    "explain_replay",
                ):
                    return self._build_assistant_message(
                        text=str(
                            {
                                "ok": False,
                                "error": ("runtime_replay_unavailable"),
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

                runtime_result = self.runtime.run_cycle(
                    execution_state=execution_state,
                    world_state={},
                    scheduler_state={},
                    knowledge_graph=None,
                )

        except Exception as e:

            runtime_result = {
                "ok": False,
                "runtime_error": type(e).__name__,
                "message": str(e),
            }

        assistant_msg = self._build_assistant_message(text=str(runtime_result))

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

    if route == self.ROUTE_ATTACHMENT_ANALYSIS:
        # NOVA_DISPATCH_ATTACHMENT_ANALYSIS_ROUTE_20260607
        return self.attachment_analysis_service.execute_attachment_analysis(
            attachments=attachments,
            decision=decision,
            user_text=user_text,
            session_id=session_id,
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
    # NOVA_PROJECT_STATUS_MEMORY_FILTER_20260607
    project_status_query = any(
        phrase in original_user_text.lower()
        for phrase in [
            "what did we fix",
            "what we fixed",
            "explain what we fixed",
            "summarize what we fixed",
            "what did we do today",
            "what have we done today",
        ]
    )





    if project_status_query:
        memory_context = ""
        working_context_block = ""

    # NOVA_MEMORY_RECALL_PRIORITY_20260726
    memory_recall_query = any(
        phrase in original_user_text.lower()
        for phrase in [
            "what did i ask you to remember",
            "what did i tell you to remember",
            "what do you remember about me",
            "show my memories",
            "what memories do you have",
        ]
    )

    if memory_recall_query:
        assistant_msg = self._build_assistant_message(
            text=self._build_memory_recall_text(
                session_id=session_id,
                user_text=user_text,
                limit=5,
            )
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

    working_state = self._get_working_state(session_id) or {}

    execution_state = (
        self._get_session_meta(
            session_id,
            "execution_state",
        )
        or {}
    )

    try:

        has_real_state = any(
            [
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
                    and working_state.get("checkpoint") != "execution_plan_created"
                ),
            ]
        )

        has_real_execution = any(
            [
                execution_state.get("steps"),
                execution_state.get("current_step"),
                execution_state.get("status") == "running",
            ]
        )

        if not has_real_state and not has_real_execution:
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
                    mem.get("content") or mem.get("text") or mem.get("memory") or ""
                ).strip()

            else:
                text = str(mem).strip()

            if text:

                dominant_memory.append(f"- {text}")

                memory_dominance_debug.append(text[:300])

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

    should_apply_dominance = any(q in text_lc for q in continuity_queries)

    if dominant_memory:
        dominance_block = (
            "\n\n"
            "SAVED MEMORY:\n"
            "Lower priority than the current user message and recent conversation. "
            "Use only when relevant and never when contradicted by the active session context.\n\n"
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
        memory_context = (
            f"{memory_context}\n\nAnswer depth instruction:\n{depth_instruction}"
        )
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
            session.get("messages", []) if isinstance(session, dict) else []
        )

        previous_user = ""

        for msg in reversed(session_messages):

            if not isinstance(msg, dict):
                continue

            role = self.safe_str(msg.get("role"))
            text = self.safe_str(msg.get("text")).strip()

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
            m
            for m in session_messages
            if isinstance(m, dict) and m.get("role") == "user"
        ]

        if len(user_messages) >= 2:
            previous_user = str(user_messages[-2].get("text", "")).strip()

        if not previous_user:
            previous_user = "I could not find a previous user message."

        assistant_text = f'Your previous message was: "{previous_user}"'

        assistant_msg = self._build_assistant_message(text=assistant_text)

        return self._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            saved_artifact=None,
        )

    is_memory_request = (
        original_user_text.lower()
        .strip()
        .startswith(
            (
                "remember ",
                "remember:",
                "save this",
                "store this",
                "note that",
            )
        )
    )

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
        and execution_state.get("status")
        not in {
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

    # NOVA ANSWER QUALITY DIRECTIVE 20260630
    # Normal chat only. Do not touch web, image, or execution routes here.
    quality_directive = {
        "role": "system",
        "content": (
            "Nova answer quality rules: "
            "Answer the user's latest message first. "
            "Give the most concrete next action early, especially for Nova project work. "
            "Avoid abstract labels like continuity, action shaping, workspace anchoring, or response selection unless the user asks for theory. "
            "For coding/debugging, name the exact file path and exact command or patch before giving explanation. "
            "Match the user's practical, get-to-the-point style. "
            "Do not claim background work, future monitoring, or hidden async progress. "
            "Do not say 'if you want', 'let me know', or add generic follow-up offers. "
            "Do not repeat the same answer, paragraph, list, or conclusion twice. "
            "Do not invent certainty; say when something is uncertain. "
            "For attachments, describe only the provided file or image. "
            "For current facts/news/prices/schedules, use the web route instead of guessing. "
            "Keep replies concise unless the user asks for detail."
        ),
    }

    if isinstance(model_messages, list):
        insert_at = 1 if (
            model_messages
            and isinstance(model_messages[0], dict)
            and model_messages[0].get("role") == "system"
        ) else 0

        model_messages.insert(insert_at, quality_directive)

    def dedupe_repeated_answer_20260630(value: str) -> str:
        import re

        clean = self.safe_str(value).strip()

        if not clean:
            return ""

        compact = " ".join(clean.split())

        # Exact duplicated paragraph/list halves.
        paragraphs = [p.strip() for p in clean.split("\n\n") if p.strip()]
        if len(paragraphs) >= 2 and len(paragraphs) % 2 == 0:
            half = len(paragraphs) // 2
            if paragraphs[:half] == paragraphs[half:]:
                return "\n\n".join(paragraphs[:half]).strip()

        # Exact duplicated text with only spaces between copies.
        if len(compact) >= 80:
            midpoint = len(compact) // 2

            for cut in range(
                max(1, midpoint - 160),
                min(len(compact), midpoint + 160),
            ):
                left = compact[:cut].strip()
                right = compact[cut:].strip()

                if len(left) >= 40 and left == right:
                    return left

                if len(left) >= 40 and right.startswith(left):
                    return left

        # Sentence-level duplicate cleaner.
        sentence_parts = re.split(r"(?<=[.!?])\s+", clean)
        sentence_parts = [part.strip() for part in sentence_parts if part.strip()]

        if len(sentence_parts) >= 2 and len(sentence_parts) % 2 == 0:
            half = len(sentence_parts) // 2
            left = " ".join(sentence_parts[:half]).strip()
            right = " ".join(sentence_parts[half:]).strip()

            if left and left == right:
                return left

        # Remove repeated individual sentences while preserving order.
        if len(sentence_parts) >= 4:
            seen = set()
            output = []

            for sentence in sentence_parts:
                key = " ".join(sentence.lower().split())

                if key in seen:
                    continue

                seen.add(key)
                output.append(sentence)

            cleaned = " ".join(output).strip()

            if cleaned and len(cleaned) < len(clean):
                return cleaned

        return clean

    print(
        "DEBUG BEFORE MODEL CALL REACHED",
        user_text,
    )

    try:
        print(
            "DEBUG GENERAL MODEL MESSAGES =",
            repr(model_messages)[:2000],
        )

        response = responses_create(

            nova_username=(
                getattr(self, "username", None)
                or os.getenv("NOVA_DEFAULT_USERNAME")
                or "richard"
            ),
            nova_session_id=session_id,
            model=self.chat_model,
            input=model_messages,
        )

        print(
            "DEBUG GENERAL RESPONSE RAW =",
            repr(response)[:1000],
        )

        print(
            "DEBUG EXTRACT TEST RESPONSE =",
            repr(response)[:3000],
        )

        assistant_text = dedupe_repeated_answer_20260630(
            self.response_handler.extract_response_text(response)
        )


        print(
            "DEBUG AFTER EXTRACTION =",
            repr(assistant_text),
        )
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
        if any(
            phrase in text_lc
            for phrase in [
                "my package",
                "my order",
                "my shipment",
                "my delivery",
                "where is my package",
                "where is my order",
                "track my package",
            ]
        ):
            assistant_text = (
                "I can help with that, but I need some details first. "
                "Please provide the tracking number, carrier, or order "
                "information you have."
            )

        elif "name" in text_lc:
            assistant_text = (
                "I do not have your name in this session yet. "
                "Tell me your name once and I ll use it for this chat."
            )

        else:
            assistant_text = "I m here. Send the next instruction."

    print(
        "[DECISION DEBUG BEFORE INTELLIGENCE]",
        repr(decision),
    )

    intelligence_result = self._apply_response_intelligence(


        user_text=user_text,
        assistant_text=assistant_text,
        decision=decision,
        session_id=session_id,
        attachments=attachments,
    )

    print(
        "DEBUG AFTER INTELLIGENCE =",
        {
            "assistant_text": repr(assistant_text),
            "intelligence_result": repr(intelligence_result)[:2000],
        },
    )

    intelligence_result = (
        intelligence_result if isinstance(intelligence_result, dict) else {}
    )

    # lock tool outputs (prevent conversational overwrite)
    if decision.get("route") in {
        self.ROUTE_WEB_FETCH,
        self.ROUTE_IMAGE_GENERATION,
        self.ROUTE_ATTACHMENT_ANALYSIS,
    }:
        assistant_text = assistant_text
    else:
        rewritten_text = self.safe_str(
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

        current_text_lc = assistant_text.lower().strip()

        rewritten_text_lc = rewritten_text.lower().strip()

        if current_text_lc in protected_memory_answers:
            pass

        elif rewritten_text and len(rewritten_text.split()) >= 3:
            assistant_text = rewritten_text

    assistant_text = dedupe_repeated_answer_20260630(assistant_text)

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

    memory_text = " ".join(
        [
            self.safe_str(m.get("text"))
            for m in used_memory_items
            if isinstance(m, dict)
        ]
    ).lower()

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

        working_state = self._get_working_state(session_id) or {}

        if working_state.get("checkpoint") == "runtime_error_detected":
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

            value = self.safe_str(working_state.get(key)).strip()

            if self._is_control_command_value(value):
                working_state[key] = ""

        if self._is_control_command_value(working_state.get("active_task")):
            working_state["active_task"] = ""

        if self._is_control_command_value(working_state.get("next_move")):
            working_state["next_move"] = ""

        self._update_working_state(
            session_id,
            working_state,
        )

    used_memory_full = [
        {
            "id": self.safe_str(m.get("id")),
            "text": self.safe_str(m.get("text")),
            "kind": self.safe_str(m.get("kind")),
            "pinned": bool(m.get("pinned")),
            "weight": m.get("weight", 1),
        }
        for m in used_memory_items
        if isinstance(m, dict) and self.safe_str(m.get("text"))
    ]

    decision_mission = (
        decision.get("mission", {}) if isinstance(decision, dict) else {}
    )

    if isinstance(decision_mission, dict):

        sanitized_mission = {}

        for k, v in decision_mission.items():

            key = self.safe_str(k)
            value = self.safe_str(v).strip()

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
            if not self._is_control_command_value(decision_mission.get("mission"))
            else {}
        ),
        "strategy": (
            decision.get("strategy", "") if isinstance(decision, dict) else ""
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

    assistant_text = dedupe_repeated_answer_20260630(assistant_text)

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
