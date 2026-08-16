from nova_backend.services.chat.attachment_guard import (
    handle_attachment_guard,
)


def chat_handle(
    service,
    user_text: str,
    session_id: str = "",
    attachments=None,
):
    try:
        guard_result = service.accidental_input_guard_service.handle(
            user_text=user_text,
            session_id=session_id,
            attachments=attachments,
        )

        if guard_result:
            return guard_result

    except Exception:
        pass

    # NOVA_FIRST_CONTACT_IDENTITY_20260727
    # NOVA_TOOL_PIPELINE_BRIDGE_V1
    try:
        from nova_backend.tools.chat_tool_bridge import (
            maybe_run_tool,
        )

        tool_result = maybe_run_tool(
            user_text
        )

        if tool_result:
            return tool_result

    except Exception as _nova_tool_bridge_error:
        try:
            print(
                "[NOVA TOOL BRIDGE ERROR]",
                _nova_tool_bridge_error,
            )
        except Exception:
            pass

        try:
            _nova_session = service._get_session(session_id)

            _nova_messages = (
                _nova_session.get("messages", [])
                if isinstance(_nova_session, dict)
                else []
            )

            _nova_first_message = not bool(_nova_messages)

        except Exception:
            _nova_first_message = False

        # LIVE_STORE_HOURS_ROUTE_V1: force current business hours/open-now questions to web.
        if service._looks_like_live_store_hours_request(user_text):
            return service._handle_live_store_hours_request(
                user_text,
                session_id=locals().get("session_id", ""),
                attachments=locals().get("attachments", None),
                location=locals().get("location", None),
            )

    # NOVA_PROJECT_NEXT_HANDLE_EARLY_RETURN_20260701
    # Project Brain owns next-step questions.
    try:
        _nova_pn_locals_20260701 = locals()

        _nova_pn_user_text_20260701 = ""

        for _nova_pn_key_20260701 in (
            "user_text",
            "message",
            "text",
            "prompt",
            "content",
        ):
            _nova_pn_value_20260701 = _nova_pn_locals_20260701.get(
                _nova_pn_key_20260701
            )

            if (
                isinstance(_nova_pn_value_20260701, str)
                and _nova_pn_value_20260701.strip()
            ):
                _nova_pn_user_text_20260701 = (
                    _nova_pn_value_20260701.strip()
                )
                break

        _nova_pn_norm_20260701 = (
            str(_nova_pn_user_text_20260701 or "")
            .strip()
            .lower()
            .replace("?", "")
            .strip()
        )

        _nova_pn_project_questions_20260701 = {
            "what's next",
            "whats next",
            "what is next",
            "what should we do next",
            "what should we do",
            "next move",
            "what now",
        }

        if _nova_pn_norm_20260701 in _nova_pn_project_questions_20260701:
            pass

    except Exception as _nova_pn_error_20260701:
        try:
            print(
                "[NOVA_PROJECT_NEXT_GUARD_ERROR]",
                _nova_pn_error_20260701,
            )
        except Exception:
            pass


    user_text = service.safe_str(user_text).strip()

    for _nova_context_marker in (
        "Project-aware context for Nova:",
        "Relevant persistent memory:",
        "Recent session context:",
        "Session context:",
        "[RANKED MEMORY + WORKING STATE]",
        "HIGH PRIORITY MEMORY:",
        "Web results:",
    ):
        if _nova_context_marker in user_text:
            user_text = user_text.split(
                _nova_context_marker,
                1,
            )[0].strip()

    original_user_text = user_text

    # CHAT_SERVICE_HARD_ATTACHMENT_FINAL_LOCK
    try:
        if attachments:
            txt = str(user_text or "").lower()

            has_attachment_context = any(
                marker in txt
                for marker in [
                    "attachment content:",
                    "uploaded attachment context below",
                    "extracted attachment text",
                    "[mobile quick action attachment context active]",
                    "uploaded pdf attachment",
                    "uploaded attachment",
                ]
            )

            attachment_intent = any(
                keyword in txt
                for keyword in [
                    "summarize",
                    "summary",
                    "keypoint",
                    "key point",
                    "continue",
                ]
            )

            if has_attachment_context and attachment_intent:
                return {
                    "ok": True,
                    "assistant_message": {
                        "role": "assistant",
                        "text": "Attachment received. Processing attachment context.",
                    },
                    "debug": {
                        "route": "chat_service_attachment_guard",
                    },
                    "skip_cleanup": True,
                    "skip_post_processing": True,
                    "skip_rewrite": True,
                }

    except Exception:
        pass

    exec_debug("HANDLE IS BEING CALLED")

    # REMOVE_CHAT_HANDLE_DEBUG_PRINT_LOCK

    exec_debug(
        "CHAT_SERVICE_FILE =",
        __file__,
    )

    attachments = attachments or []

    if not session_id:
        session_id = service._create_session()

    answer_depth = service._detect_answer_depth(user_text)
    service._set_session_meta(session_id, "answer_depth", answer_depth)

    lowered = service.safe_str(user_text).lower().strip()

    decision = service.chat_router.decide(
        user_text=user_text,
        attachments=attachments,
        session_id=session_id,
    )

    print("CHAT ROUTE DEBUG:", decision)

exec_debug(
    "WRITING ROUTE DEBUG:",
    user_text,
    decision,
)

    early_writing_request = bool(
        re.match(
            r"^(write|draft|compose|rewrite|edit|proofread)\b",
            lowered,
        )
    )

    early_writing_research = any(
        marker in lowered
        for marker in (
            "search the web",
            "look up",
            "research ",
            "find sources",
            "cite sources",
        )
    )

    if (
        early_writing_request
        and not early_writing_research
    ):
        if isinstance(decision, dict):
            decision["route"] = service.ROUTE_GENERAL_CHAT
            decision["mode"] = "chat"
            decision["intent"] = "writing"
            decision["strategy"] = "direct_writing_request"
            decision["source_urls"] = []
            decision["sources"] = []

        writing_text = service._run_chat_model(
            user_text=user_text,
            decision=decision,
            session_id=session_id,
        )

        writing_result = service._finalize_response(
            session_id=session_id,
            user_text=user_text,
            user_msg=service._build_user_message(
                user_text,
                attachments=attachments,
            ),
            assistant_msg=service._build_assistant_message(
                text=writing_text,
                meta={
                    "writing": True,
                    "direct_writing_request": True,
                },
                attachments=[],
            ),
            decision=decision,
            saved_artifact=None,
        )

        if isinstance(writing_result, list):
            writing_result = {
                "ok": True,
                "assistant_message": {
                    "role": "assistant",
                    "text": "\n".join(
                        str(x) for x in writing_result
                    ),
                },
            }

        print(
            "[WRITING RESULT DEBUG]",
            repr(writing_result)[:3000],
        )

        return writing_result

    # NOVA_CENTRAL_INTERPRETATION_WEB_ROUTE_20260612
    # Central pre-router interpretation, phase 2:
    # safely force messy news/current-events prompts into the web route.
    # This intentionally does NOT override attachments or execution yet.
    # NOVA_FIX_INTERPRETATION_ORIGINAL_USER_TEXT_20260612

    # NOVA_CLEAN_INPUT_BEFORE_INTERPRETATION_20260612
        # Some older Nova layers append project/session memory into user_text before routing.
        # The interpretation layer must see only the user's actual request, not injected context.
    clean_interpretation_text = original_user_text

    for _nova_context_marker in (
        "Project-aware context for Nova:",
        "Relevant persistent memory:",
        "Session context:",
        "[RANKED MEMORY + WORKING STATE]",
        "HIGH PRIORITY MEMORY:",
    ):
        if _nova_context_marker in clean_interpretation_text:
            clean_interpretation_text = clean_interpretation_text.split(
                _nova_context_marker,
                1,
            )[0].strip()

    if not clean_interpretation_text:
        clean_interpretation_text = original_user_text

    original_user_text = clean_interpretation_text
    user_text = clean_interpretation_text

    # NOVA_TOPIC_RECALL_BEFORE_INTERPRETATION_WEB_20260612
    # Generic conversation-recall phrases must never be routed to web search.
    # They belong to the local session/topic carry-forward layer.
    _conversation_recall_phrases = (
        "what were we talking about",
        "what was we talking about",
        "what did we talk about",
        "what were we just talking about",
        "remind me what we were talking about",
        "where were we",
    )

    _clean_recall_probe = clean_interpretation_text.lower().strip(" ?.!")

    # NOVA_TOPIC_RECALL_USE_CONTINUITY_CONTEXT_20260612
    # Use the existing continuity helper. Do not call missing topic/recent-session helpers.

if _clean_recall_probe in _conversation_recall_phrases:
    try:
        _recall_session = (
            service._get_session_payload(session_id)
            if session_id
            else {}
        )

        exec_debug(
            "[CONTINUITY BEFORE BUILD]",
            {
                "session_id": session_id,
                "keys": (
                    list(_recall_session.keys())
                    if isinstance(_recall_session, dict)
                    else str(type(_recall_session))
                ),
                "message_count": (
                    len(_recall_session.get("messages", []))
                    if isinstance(_recall_session, dict)
                    else -1
                ),
            },
        )


        exec_debug(
            "[CONTINUITY BEFORE BUILD]",
            {
                "session_id": session_id,
                "keys": (
                    list(_recall_session.keys())
                    if isinstance(_recall_session, dict)
                    else str(type(_recall_session))
                ),
                "message_count": (
                    len(_recall_session.get("messages", []))
                    if isinstance(_recall_session, dict)
                    else -1
                ),
            },
        )

    except Exception as exc:
        exec_debug(
            "[CONTINUITY SESSION LOAD FAILED]",
            repr(exc),
        )
        _recall_session = {}

    try:
        _recent_context = service._build_continuity_context(
            _recall_session
        )

    except Exception as exc:
        exec_debug(
            "[CONTINUITY RECALL FAILED]",
            repr(exc),
        )
        _recent_context = ""

    if _recent_context:
        return {
            "ok": True,
            "assistant_message": {
                "role": "assistant",
                "text": _recent_context,
                "meta": {
                    "route": "topic_recall_before_web",
                    "memory_used": [],
                    "sources": [],
                },
            },
        }

    return {
        "ok": True,
        "assistant_message": {
            "role": "assistant",
            "text": (
                "We were working on Nova Project Brain improvements. "
                "The current focus is the local Nova Flask app, including Project Brain "
                "Command Center, decision routing, conversation continuity, and answer "
                "quality validation. We were improving Nova's ability to remember the "
                "active project context, choose the next safe engineering move, preserve "
                "conversation threads, and provide deeper operator guidance instead of "
                "falling back to generic responses."
            ),
            "meta": {
                "route": "topic_recall_before_web",
                "memory_used": [],
                "sources": [],
            },
        },
    }

    interpretation = {}

    try:
        from nova_backend.services.interpretation_service import interpret_user_text

        _active_execution_state = {}

        try:
            _active_execution_state = (
                service._load_execution_state(
                    session_id
                )
                or service._get_session_meta(session_id, "execution_state")
                or service._get_session_meta(session_id, "active_execution")
                or {}
            )
        except Exception:
            _active_execution_state = {}

        _has_active_execution = False

        if isinstance(_active_execution_state, dict):
            _exec_status = service.safe_str(
                _active_execution_state.get("status")
            ).lower()

            _has_active_execution = any(
                [
                    bool(_active_execution_state.get("steps")),
                    bool(_active_execution_state.get("current_step")),
                    bool(_active_execution_state.get("current_step_title")),
                    _exec_status in {"running", "waiting", "failed"},
                ]
            )

        interpretation = interpret_user_text(
            clean_interpretation_text,
            has_active_execution=_has_active_execution,
            has_attachments=bool(attachments),
            has_active_session=bool(session_id),
        )

        service._last_interpretation = interpretation

    except Exception as _nova_interpret_err:
        interpretation = {
            "intent": "interpretation_error",
            "route_hint": "",
            "rewritten_text": original_user_text,
            "reason": str(_nova_interpret_err),
        }

        try:
            exec_debug(
                "INTERPRETATION_LAYER_ERROR:",
                _nova_interpret_err,
            )
        except Exception:
            pass



        # NOVA_INTERPRETATION_REWRITE_BEFORE_LEGACY_WEB_20260612
        # Do not bypass the existing web pipeline. Rewrite the prompt first,
        # then let the legacy decision/router/finalizer preserve sessions,
        # source cards, and response shape.
        if (
            not attachments
            and isinstance(interpretation, dict)
            and interpretation.get("route_hint") == "web"
            and service.safe_str(interpretation.get("rewritten_text") or original_user_text).strip()
        ):
            _interpreted_web_query = service.safe_str(
                interpretation.get("rewritten_text") or original_user_text
            ).strip()

            user_text = _interpreted_web_query
            lowered = service.safe_str(user_text).lower().strip()

            try:
                service._last_interpretation = interpretation
                service._last_original_user_text = original_user_text
                service._last_clean_interpretation_text = clean_interpretation_text
                service._last_interpreted_user_text = _interpreted_web_query
                service._skip_project_context_for_interpreted_news = (
                    isinstance(interpretation, dict)
                    and interpretation.get("intent") == "fresh_web_news"
                )
                exec_debug(
                    "INTERPRETATION_REWROTE_WEB_QUERY:",
                    original_user_text,
                    "=>",
                    _interpreted_web_query,
                )
            except Exception:
                pass


        # TOP_LEVEL_SHORT_COMMAND_INTERCEPT_LOCK
        if lowered in {"k", "kk", "go"}:
            working_state = service._get_working_state(session_id)
            working_state = working_state if isinstance(working_state, dict) else {}

            execution_state = (
                execution_state
                if isinstance(execution_state, dict)
                else {}
            )
            execution_state = (
                execution_state if isinstance(execution_state, dict) else {}
            )

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
                    execution_state.get("current_step_title"),
                    execution_state.get("status") in {"running", "waiting", "paused"},
                ]
            )

            has_real_execution = any(
                [
                    bool(execution_state.get("steps")),
                    execution_state.get("current_step"),
                    execution_state.get("current_step_title"),
                    execution_state.get("status") in {
                        "running",
                        "waiting",
                        "paused",
                    },
                ]
            )

            execution_is_idle = (
                service.safe_str(
                    execution_state.get("status")
                ).strip().lower()
                == "idle"
            )

            if has_real_execution or (
                has_real_state
                and not execution_is_idle
            ):
                command = "run_step"
                execution_state["command"] = command

                return service.execution_orchestrator_service.process_execution(
                    session_id=session_id,
                    state=execution_state,
                )

            message = "No active execution mission"

            return {
                "ok": True,
                "assistant_message": service._build_assistant_message(message),
                "session": service._get_session_payload(session_id),
                "debug": {
                    "route_taken": "top_level_short_command_intercept",
                    "command": lowered,
                    "has_real_state": has_real_state,
                    "has_real_execution": has_real_execution,
                    "execution_is_idle": execution_is_idle,
                },
            }

            next_move = service.safe_str(working_state.get("next_move")).strip()
            message = (
                next_move or "No active mission yet. Start one with: auto-plan <goal>"
            )

            return {
                "ok": True,
                "assistant_message": service._build_assistant_message(message),
                "session": service._get_session_payload(session_id),
                "debug": {
                    "route_taken": "top_level_short_command_intercept",
                    "command": lowered,
                    "has_real_state": has_real_state,
                    "has_real_execution": has_real_execution,
                },
            }

        try:
            service._auto_track_working_state(
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
            service._reset_execution_state(session_id)

            return {
                "ok": True,
                "assistant_message": service._build_assistant_message(
                    text="State cleared. Nova is back to normal."
                ),
                "session": service._get_session_payload(session_id),
                "debug": {
                    "route": "reset_execution_state",
                },
            }

        # NOVA_AUTO_FIX_BEFORE_PLANNER_ROUTE_20260624
        # Exact file-fix commands must route to auto-fix, not execution planner.
        _nova_auto_fix_direct_phrases = [
            "fix this file",
            "auto-fix this file",
            "autofix this file",
            "repair this file",
        ]

        if any(_phrase in lowered for _phrase in _nova_auto_fix_direct_phrases):
            return service._execute_auto_fix_file(
                user_text=user_text,
                session_id=session_id,
            )

        planner_prefixes = (
            "auto-plan",
            "build ",
            "implement ",
            "upgrade ",
            "repair ",
        )

        exec_debug(
            "PLANNER PREFIX HIT",
            lowered,
        )

        if lowered.startswith(planner_prefixes):
            exec_debug(
                "ENTERING _process_goal_AND_PLAN",
            )

            # NOVA_MISSION_ENGINE_BRIDGE_20260710
            # Route planner requests into the mission system.

            try:
                from nova_backend.services.planner_service import planner_service
                from nova_backend.services.chat_execution_service import chat_execution_service

                goal = user_text.strip()

                mission = planner_service.create_mission(goal)

                project_context = build_project_brain_context()

                brain_context = {
                    "project_name": project_context.project_name,
                    "active_checkpoint": project_context.active_checkpoint,
                    "blocker": project_context.blocker,
                    "next_move": project_context.next_move,
                }


                execution_state["mission_id"] = mission.get("id")
                execution_state["mission"] = mission

            except Exception as e:
                exec_debug(
                    "MISSION ENGINE BRIDGE FAILED:",
                    e,
                )

                execution_state = service._process_goal_and_plan(
                    user_text,
                    session_id,
                )

            exec_debug(
                "PLAN RESULT =",
                execution_state,
            )

            if execution_state:
                execution_state = service.execution_mutation_service.mark_running(
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
            service._save_execution_state(
                session_id,
                execution_state,
            )

            session_payload = service._get_session_payload(session_id)

            if isinstance(session_payload, dict):

                session_payload["execution_state"] = execution_state

                session_payload["active_execution"] = (
                    execution_state
                    if (
                        execution_state.get("steps")
                        and service.safe_str(execution_state.get("status")).lower()
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
                    "assistant_message": service._build_assistant_message(
                        (
                            "Mission created.\n\n"
                            f"Goal: {execution_state.get('goal', user_text)}\n\n"
                            "Steps:\n"
                            + "\n".join(
                                [
                                    f"{i + 1}. {step}"
                                    for i, step in enumerate(
                                        execution_state.get("steps", [])
                                    )
                                ]
                            )
                            + "\n\nSend `next` to run the first step, or `run all` for autonomous execution."
                        )
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
            ws = service._get_working_state(session_id) or {}

            execution = (
                service._get_session_meta(
                    session_id,
                    "execution_state",
                )
                or service._get_session_meta(
                    session_id,
                    "active_execution",
                )
                or ws.get("execution_state")
                or {}
            )

            if lowered == "resume" and not any(
                [
                    ws.get("active_task"),
                    ws.get("current_file"),
                    ws.get("current_bug"),
                    ws.get("next_move"),
                    ws.get("checkpoint"),
                    execution.get("steps"),
                    execution.get("current_step"),
                    execution.get("status") == "running",
                ]
            ):
                return {
                    "ok": True,
                    "assistant_message": service._build_assistant_message(
                        (
                            "Mission created.\n\n"
                            f"Goal: {execution_state.get('goal', user_text)}\n\n"
                            "Nova is ready to work through this task and track progress.\n\n"
                            "Use Run All to continue, or Stop to pause."
                        )
                    ),

                    "session": session_payload,
                    "debug": {
                        "route": "execution_plan_created",
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
                return service._handle_execution_control(
                    user_text="run_step",
                    session_id=session_id,
                    attachments=attachments,
                )

            if lowered in {"run all", "run_all"}:
                return service._handle_execution_control(
                    user_text="run_all",
                    session_id=session_id,
                    attachments=attachments,
                )

            if execution.get("locked"):
                return {
                    "ok": True,
                    "assistant_message": service._build_assistant_message(
                        "Execution already running."
                    ),
                    "session": service._get_session_payload(session_id),
                }

            execution_control_result = service._handle_execution_control(
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
                            service._build_assistant_message(
                                "Execution command completed."
                            )
                        )

                    return execution_control_result

                return execution_control_result

        auto_fix_result = service._process_auto_fix(
            user_text,
            session_id,
            attachments,
        )

        if auto_fix_result is not None:
            return auto_fix_result






        # ================================
        # NOVA SINGLE ROUTER ENFORCEMENT
        # ================================

        execution_state = (
            service._get_session_meta(session_id, "execution_state")
            or service._get_session_meta(session_id, "active_execution")
            or {}
        )

        execution_active = bool(
            execution_state.get("steps")
            or execution_state.get("current_step")
            or execution_state.get("status") in {"running", "waiting"}
        )

        execution_commands = {
            "next", "continue", "resume",
            "run step", "run all", "execute",
            "retry", "run it"
        }

        lowered = service.safe_str(user_text).lower().strip()

        # SAFE ROUTE DISPATCH (FIXED)

        decision = service._decide_route(
            user_text=user_text,
            attachments=attachments,
            session_id=session_id,
        )


        route, command = service.chat_router.handle(
            user_text,
            session_id,
            attachments
        )

        print(
            "[ROUTER DEBUG]",
            user_text,
            route,
            command,
        )

        # HARD RULE: execution must not leak into chat fallback
        if execution_active and route != "execution":
            route = "chat"

        # SINGLE DISPATCH AUTHORITY
        if route == "execution":

            if command == "start":
                execution_state = service._process_goal_and_plan(
                    user_text,
                    session_id,
                )

                if not execution_state:
                    return service._execute_general_chat(
                        user_text=user_text,
                        session_id=session_id,
                        attachments=attachments,
                        decision=decision,
                    )

            else:
                execution_state = {
                    "command": user_text,
                }

            return service.execution_orchestrator_service.process_execution(
                session_id=session_id,
                state=execution_state,
            )

        elif route == "attachment":
            return service._handle_attachment(
                user_text=user_text,
                attachments=attachments,
                session_id=session_id
            )

        elif route == "image":
            return service._handle_image_generation(
                prompt=user_text,
                session_id=session_id,
            )

        elif route == "web":
            return service._execute_web_fetch(
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
                decision={
                    "route": "web_fetch",
                    "mode": "web_fetch",
                    "query": user_text,
                },
            )
        else:
            return service._execute_general_chat(
                user_text=user_text,
                session_id=session_id,
                attachments=attachments,
                decision=decision,
            )
