def install_project_brain_patch(ChatService):

    # NOVA_PROJECT_BRAIN_QUESTION_TOP_PRIORITY_20260701

    # Final top-priority guard for project-brain questions.

    # Prevents stale project brain fallback answers.

    # "No active task is currently tracked yet."

    _NOVA_PRE_PROJECT_BRAIN_QUESTION_TOP_PRIORITY_HANDLE_20260701 = (
        ChatService.handle
    )

    def _nova_project_brain_question_text_20260701(args, kwargs):
        for key in (
            "user_text",
            "message",
            "text",
            "prompt",
            "content",
        ):
            value = kwargs.get(key)

            if isinstance(value, str) and value.strip():
                return value

        for arg in args:
            if isinstance(arg, str) and arg.strip():
                return arg

            if isinstance(arg, dict):
                for key in (
                    "user_text",
                    "message",
                    "text",
                    "prompt",
                    "content",
                ):
                    value = arg.get(key)

                    if isinstance(value, str) and value.strip():
                        return value

        return ""

    def _nova_project_brain_question_session_20260701(args, kwargs):
        for key in ("session_id", "active_session_id", "requested_session_id"):
            value = kwargs.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        for arg in args:
            if isinstance(arg, dict):
                for key in ("session_id", "active_session_id", "requested_session_id"):
                    value = arg.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()

        return ""

    def _nova_project_brain_has_active_execution_20260711(
        self,
        session_id,
    ):
        try:
            session_obj = (
                self._get_session_payload(session_id)
                or self._get_session(session_id)
                or {}
            )

            if not isinstance(session_obj, dict):
                return False

            working_state = (
                session_obj.get("working_state")
                or {}
            )

            if not isinstance(
                working_state,
                dict,
            ):
                working_state = {}

            execution_candidates = [
                session_obj.get(
                    "active_execution"
                ),
                session_obj.get(
                    "execution_state"
                ),
                working_state.get(
                    "active_execution"
                ),
                working_state.get(
                    "execution_state"
                ),
            ]

            terminal_statuses = {
                "",
                "idle",
                "complete",
                "completed",
                "cancelled",
                "canceled",
                "stopped",
                "failed",
            }

            for execution_state in execution_candidates:

                if not isinstance(
                    execution_state,
                    dict,
                ):
                    continue

                if bool(
                    execution_state.get(
                        "complete"
                    )
                ):
                    continue

                status = str(
                    execution_state.get(
                        "status"
                    )
                    or ""
                ).strip().lower()

                if status in terminal_statuses:
                    continue

                goal = str(
                    execution_state.get(
                        "goal"
                    )
                    or ""
                ).strip()

                current_step = str(
                    execution_state.get(
                        "current_step"
                    )
                    or ""
                ).strip()

                steps = (
                    execution_state.get(
                        "steps"
                    )
                    or []
                )

                if (
                    goal
                    or current_step
                    or steps
                ):
                    return True

        except Exception as exc:
            try:
                print(
                    "[NOVA_ACTIVE_EXECUTION_PROJECT_BRAIN_PRIORITY_20260711] "
                    "detection bypass:",
                    exc,
                )
            except Exception:
                pass

        return False

    def _nova_project_brain_question_kind_20260701(user_text):
        text = str(user_text or "").strip().lower()
        text = text.replace("?", "'").replace("`", "")
        text = " ".join(text.split())
        bare = text.rstrip("?!.")
        
        if (
            "nova status" in bare
            or "give me the nova status" in bare
            or "status without hype" in bare
            or "where are we at with nova" in bare
            or "where are we at" in bare
            or "current project state" in bare
            or "current project state of nova" in bare
        ):
            return "current_project_state"

        if (
            "what does this failure mean" in bare
            or "failure" in bare
            and (
                "error" in bare
                or "traceback" in bare
                or "failed" in bare
                or "smoke" in bare
            )
        ):
            return "failure_interpreter"

        if (
            (
                "mission control" in bare
                or "mission-control" in bare
                or "show mission" in bare
                or "mission card" in bare
                or "show mission card" in bare
                or "project mission" in bare
            )
            and not (
                "indentationerror" in bare
                or "syntaxerror" in bare
                or "unexpected indent" in bare
                or "traceback" in bare
                or "assertionerror" in bare
                or "failed smoke" in bare
                or "smoke failed" in bare
            )
        ):
            return "mission_control"

        if (
            "current blocker" in bare
            or "what is the current blocker" in bare
            or "what's the current blocker" in bare
            or bare == "blocker"
        ):
            return "actual_blocker"

        if (
            bare in {
                "what are we working on",
                "what are we working on now",
                "what are we working on right now",
                "what are we doing",
                "what am i working on",
                "what is the current task",
                "current task",
            }
            or "where are we at with nova" in bare
            or bare == "where are we at"
            or bare == "where is nova at"
            or "nova status" in bare
            or "give me the nova status" in bare
            or "status without hype" in bare
            or (
                "what changed" in bare
                and "nova" in bare
            )
        ):
            return "working"

        if bare in {
            "what's next",
            "whats next",
            "what is next",
            "what should we work on next",
            "what should we do next",
            "next move",
        }:
            return "next"

        if bare in {
            "what's next",
            "whats next",
            "what is next",
            "what should we work on next",
            "what should we do next",
            "next move",
        }:
            return "next"

        if (
            "indentationerror" in bare
            or "syntaxerror" in bare
            or "unexpected indent" in bare
            or "traceback" in bare
            or "assertionerror" in bare
            or "failed smoke" in bare
            or "smoke failed" in bare
            or (
                "failure" in bare
                and (
                    "error" in bare
                    or "failed" in bare
                    or "smoke" in bare
                )
            )
            or "what does this failure mean" in bare
        ):
            return "failure_interpreter"

        return ""

    def _nova_project_brain_bad_answer_20260701(answer):
        text = str(answer or "").strip()
        low = text.lower()

        if not text:
            return True

        bad_exact = {
            "no active task is currently tracked yet.",
            "no active task is currently tracked.",
            "nothing active is tracked right now.",
            "active task:\nno active task is currently tracked yet.",
            "active task:\nno active task is currently tracked.",
        }

        if low in bad_exact:
            return True

        bad_starts = (
            "next: tell me",
            "reply with the task",
            "paste the current file path",
            "start with the highest-impact unblocker",
            "no active execution mission",
        )

        return low.startswith(bad_starts)

    def _nova_project_brain_answer_20260701(
        kind,
        session_id,
        user_text="",
    ):
        print(
            "[ANSWER BUILDER DEBUG]",
            repr(kind),
        )

        question = (
            "give me mission control"
            if kind == "mission_control"
            else "what are we working on?"
            if kind == "working"
            else user_text
            if kind == "failure_interpreter"
            else "give me the Nova status without hype"
            if kind == "current_project_state"
            else "what's next?"
        )

        answer = ""

        try:
            print(
                "[ANSWER KIND BEFORE BRANCH]",
                repr(kind),
                repr(user_text),
            )

            if kind == "failure_interpreter":
                from nova_backend.services.project_brain_failure_interpreter import (
                    build_project_brain_failure_interpreter_answer,
                )

                answer = build_project_brain_failure_interpreter_answer(
                    user_text=user_text,
                    pasted_output=user_text,
                )

            elif kind == "mission_control":
                from nova_backend.services.project_brain_general_intelligence import (
                    build_project_brain_general_answer,
                )

                fresh_answer = build_project_brain_general_answer(
                    question,
                )

                answer = str(
                    getattr(
                        fresh_answer,
                        "text",
                        fresh_answer,
                    )
                    or ""

                ).strip()

            elif kind == "actual_blocker":
                from nova_backend.services.project_brain_general_intelligence import (
                    build_project_brain_general_answer,
                )

                fresh_answer = build_project_brain_general_answer(
                    question,
                )

                answer = str(
                    getattr(
                        fresh_answer,
                        "text",
                        fresh_answer,
                    )
                    or ""
                ).strip()

            elif kind == "current_project_state":
                from nova_backend.services.project_brain_general_intelligence import (
                    build_project_brain_general_answer,
                )

                print(
                    "[CHAT SERVICE CALLING PBGI]",
                    repr(user_text),
                    "kind=",
                    repr(kind),
                )

                fresh_answer = build_project_brain_general_answer(
                    question,
                )

                answer = str(
                    getattr(
                        fresh_answer,
                        "text",
                        fresh_answer,
                    )
                    or ""
                ).strip()

                print(
                    "[CURRENT PROJECT ANSWER DEBUG]",
                    repr(answer[:300]),
                )
            elif kind == "working":
                from nova_backend.services.project_state_service import (
                    answer_project_state_question,
                )

                if callable(answer_project_state_question):
                    answer = str(
                        answer_project_state_question(
                            question,
                            session_id=session_id,
                        )
                        or ""
                    ).strip()

            elif kind == "next":
                from nova_backend.services.project_brain_general_intelligence import (
                    build_project_brain_general_answer,
                )

                general_answer = build_project_brain_general_answer(
                    question,
                )

                if isinstance(general_answer, dict):
                    answer = str(
                        general_answer.get("content")
                        or general_answer.get("text")
                        or general_answer.get("answer")
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

        except Exception as exc:
            import traceback

            traceback.print_exc()

            print(
                "[NOVA_PROJECT_BRAIN_QUESTION_TOP_PRIORITY_20260701] fresh answer bypass:",
                exc,
            )

        print(
            "[FINAL PROJECT BRAIN ANSWER DEBUG]",
            repr(answer),
        )

        print(
            "[BLOCKER FINAL ANSWER DEBUG]",
            repr(kind),
            repr(answer),
        )

        if kind in {
            "mission_control",
            "failure_interpreter",
            "actual_blocker",
            "current_project_state",
        }:
            return answer

        if not _nova_project_brain_bad_answer_20260701(answer):
            return answer

        if kind == "next":
            return (
                "Current Nova project context:\n"
                "Current task: fix Nova project brain answer quality.\n"
                "Next move: continue improving project brain routing and verify the regression smoke."
            )

        return (
            "Current Nova project context:\n"
            "Current task: fix Nova project brain answer quality."
        )
    def _nova_project_brain_response_20260701(
        text,
        session_id,
        first_message=False,
    ):
        meta = {
            "route": "project_brain_general_intelligence",
            "strategy": "project_brain_general_intelligence",
            "session_id": session_id,
            "source_urls": [],
            "sources": [],
        }

        assistant_message = {
            "role": "assistant",
            "content": text,
            "text": text,
            "attachments": [],
            "meta": meta,
        }

        if first_message:
            onboarding_payload = {
                "onboarding": True,
                "welcome_message": (
                    "Welcome to your AI workspace.\n\n"
                    "I can help you answer questions, plan projects, "
                    "analyze files, work with documents, and create "
                    "new things.\n\n"
                    "For more information, check out Help in the menu."
                ),
                "actions": [
                    {
                        "label": "Start a project",
                        "prompt": "Help me start a project",
                        "intent": "project",
                    },
                    {
                        "label": "Learn Nova",
                        "prompt": "Show me how Nova works",
                        "intent": "help",
                    },
                ],
            }
        else:
            onboarding_payload = {}

        return {
            "ok": True,
            "assistant_message": assistant_message,
            "saved_artifact": None,
            "session": {
                "id": session_id,
                "session_id": session_id,
                "messages": [assistant_message],
                "attachments": [],
                "meta": meta,
            },
            "route": "project_brain_general_intelligence",
            "route_taken": "project_brain_general_intelligence",
            "debug": {
                "route": "project_brain_general_intelligence",
                "route_taken": "project_brain_general_intelligence",
            },
            "meta": meta,
            "session_id": session_id,
            "active_session_id": session_id,
        }

    def _nova_project_brain_question_top_priority_handle_20260701(
        self,
        *args,
        **kwargs,
    ):
        user_text = (
            _nova_project_brain_question_text_20260701(
                args,
                kwargs,
            )
        )

        _nova_first_message = user_text

        print(
            "[QUESTION TEXT DEBUG]",
            repr(user_text),
        )

        kind = (
            _nova_project_brain_question_kind_20260701(
                user_text
            )
        )

        print(
            "[KIND CHECK BEFORE ANSWER]",
            repr(user_text),
            repr(kind),
        )

        print(
            "[PROJECT BRAIN DEBUG]",
            repr(user_text),
            repr(kind),
        )

        if kind:
            session_id = (
                _nova_project_brain_question_session_20260701(
                    args,
                    kwargs,
                )
            )

            answer = ""

            print(
                "[EXECUTION CHECK DEBUG]",
                repr(session_id),
                _nova_project_brain_has_active_execution_20260711(
                    self,
                    session_id,
                ),
            )

        if kind == "current_project_state":
            from nova_backend.services.project_brain_context_builder import (
                build_current_project_answer,
            )

            fresh_answer = build_current_project_answer()

            return _nova_project_brain_response_20260701(
                fresh_answer,
                session_id,
                first_message=False,
            )

            if (
                _nova_project_brain_has_active_execution_20260711(
                    self,
                    session_id,
                )
            ):
                pre_project_state_handle = globals().get(
                    "_NOVA_PRE_PROJECT_STATE_FRESH_PRIORITY_HANDLE_20260701"
                )

                return (
                    _NOVA_PRE_PROJECT_BRAIN_QUESTION_TOP_PRIORITY_HANDLE_20260701(
                        self,
                        *args,
                        **kwargs,
                    )
                )

        return (
            _NOVA_PRE_PROJECT_BRAIN_QUESTION_TOP_PRIORITY_HANDLE_20260701(
                self,
                *args,
                **kwargs,
            )
        )


    if hasattr(ChatService, "handle"):
        ChatService.handle = _nova_project_brain_question_top_priority_handle_20260701

        ChatService._NOVA_PROJECT_BRAIN_QUESTION_TOP_PRIORITY_20260701 = True

        print(
            "[NOVA_PROJECT_BRAIN_QUESTION_TOP_PRIORITY_20260701] installed"
        )