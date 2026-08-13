class IntelligenceRouter:

    def __init__(self, chat_service):
        self.chat_service = chat_service

    def build_state(
        self,
        user_text: str = "",
        session_id: str = "",
        attachments=None,
    ) -> dict:
        attachments = attachments or []
        text = self.chat_service.safe_str(user_text).strip()
        text_lc = text.lower()

        working_state = self.chat_service._get_working_state(session_id) or {}

        execution_state = (
            self.chat_service._get_session_meta(session_id, "execution_state")
            or self.chat_service._get_session_meta(session_id, "active_execution")
            or {}
        )

        failed_steps = []
        if isinstance(execution_state, dict):
            for step in execution_state.get("steps") or []:
                if (
                    isinstance(step, dict)
                    and self.chat_service.safe_str(step.get("status")).lower() == "failed"
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
            and self.chat_service.safe_str(execution_state.get("status")).lower()
            not in {"complete", "completed", "done", "cancelled", "canceled"}
        )

        intent = "chat"
        route = self.chat_service.ROUTE_GENERAL_CHAT
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
            "approve",
            "approved",
            "approve step",
            "approve execution",
            "deny",
            "denied",
            "deny step",
            "deny execution",
            "reject",
        }

        if text_lc in execution_commands:

            if text_lc in {
                "approve",
                "approved",
                "approve step",
                "approve execution",
            }:
                intent = "approve_execution"

            elif text_lc in {
                "deny",
                "denied",
                "deny step",
                "deny execution",
                "reject",
            }:
                intent = "deny_execution"

            elif "retry" in text_lc:
                intent = "retry_failed_step"

            elif (
                "run all" in text_lc
                or text_lc in {
                    "run_all",
                    "execute all",
                }
            ):
                intent = "run_all_steps"

            elif text_lc in {
                "stop",
                "cancel",
            }:
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

        elif any(
            x in text_lc
            for x in [
                "traceback",
                "syntaxerror",
                "indentationerror",
                "nameerror",
                "typeerror",
            ]
        ):
            intent = "debugging"
            route = "auto_fix_or_debug"
            strategy = "diagnose_fix"
            priority = "high"
            confidence = 0.9
            reasons.append("error_signal")

        # SOURCE_FOLLOWUP_BEFORE_FULL_FILE_INTENT_LOCK
        elif any(
            verb in text_lc for verb in ("open", "show", "view", "click", "read")
        ) and any(
            marker in text_lc
            for marker in (
                "first",
                "second",
                "third",
                "fourth",
                "fifth",
                "1",
                "2",
                "3",
                "4",
                "5",
                "one",
                "two",
                "three",
                "four",
                "five",
            )
        ):
            intent = "web_fetch"
            route = self.chat_service.ROUTE_WEB_FETCH
            strategy = "open_web_source_followup"
            priority = "high"
            confidence = 1.0
            reasons.append("source_followup_forced_before_full_file")

        # LOCAL_NOVA_PROJECT_CONTEXT_BEATS_WEB_FRESHNESS
        elif (
            "nova project" in text_lc
            or "our nova project" in text_lc
            or "the nova project" in text_lc
            or "in the nova project" in text_lc
            or (
                "what changed" in text_lc
                and "nova" in text_lc
            )
            or (
                "what changed recently" in text_lc
                and "nova" in text_lc
            )

        ):
            intent = "current_project_state"
            route = "project_brain_general_intelligence"
            strategy = "project_brain_general_intelligence"
            priority = "high"
            confidence = 0.95
            reasons.append("local_nova_project_context_priority")

        # PROJECT_BRAIN_BLOCKER_PRIORITY_LOCK_20260803
        elif any(
            phrase in text_lc
            for phrase in (
                "what is the current blocker",
                "what's the current blocker",
                "current blocker",
                "what is the blocker",
                "what blocker do we have",
                "what are we blocked on",
                "what is blocking nova",
            )
        ):
            intent = "actual_blocker"
            route = "project_brain_general_intelligence"
            strategy = "project_brain_general_intelligence"
            priority = "high"
            confidence = 0.95
            reasons.append("project_brain_actual_blocker_priority")

        # LATEST_NEWS_BEFORE_FULL_FILE_INTENT_LOCK

        elif any(
            marker in text_lc.split()
            for marker in (
                "latest",
                "fresh",
                "breaking",
                "news",
                "current",
                "right now",
                "recent",
                "update",
                "updates",
                "source",
                "sources",
                "top sources",
                "look up",
                "search",
            )
        ):
            intent = "web_fetch"
            route = self.chat_service.ROUTE_WEB_FETCH
            strategy = "fetch_current_sources"
            priority = "high"
            confidence = 1.0
            reasons.append("latest_news_forced_before_full_file")

        # SOURCE_FOLLOWUP_HARD_INSERT_LOCK
        elif any(
            verb in text_lc for verb in ("open", "show", "view", "click", "read")
        ) and any(
            marker in text_lc
            for marker in (
                "first",
                "second",
                "third",
                "fourth",
                "fifth",
                "1",
                "2",
                "3",
                "4",
                "5",
                "one",
                "two",
                "three",
                "four",
                "five",
            )
        ):
            intent = "web_fetch"
            route = self.chat_service.ROUTE_WEB_FETCH
            strategy = "open_web_source_followup"
            priority = "high"
            confidence = 1.0
            reasons.append("source_followup_forced_before_full_file")

        elif "smff" in text_lc or "full file" in text_lc or "full code" in text_lc:
            intent = "full_file_code"
            route = "code_full_file"
            strategy = "provide_full_file"
            priority = "high"
            confidence = 0.9
            reasons.append("full_file_request")

        elif (
            "current checkpoint" in text_lc
            or "checkpoint" == text_lc
            or "what is the checkpoint" in text_lc
            or "what's the checkpoint" in text_lc
        ):
            intent = "current_project_state"
            route = "project_brain_general_intelligence"
            strategy = "fresh_project_state"
            priority = "high"
            confidence = 0.95
            reasons.append("checkpoint_project_state_query")

        elif (
            "where are we at with nova" in text_lc
            or "what are we working on" in text_lc
            or "nova status" in text_lc
            or "give me the nova status" in text_lc
            or "status without hype" in text_lc
        ):
            intent = "current_project_state"
            route = "project_brain_general_intelligence"
            strategy = "project_brain_general_intelligence"
            priority = "high"
            confidence = 0.95
            reasons.append("project_brain_general_intelligence_query")

            self.chat_service._update_working_state(
                session_id,
                {
                    "active_task": "",
                    "next_move": "",
                },
            )

        print(
            "[NOVA INTENT DEBUG]",
            text_lc,
            "intent=",
            intent,
            "route=",
            route,
        )

        mission_state = self.chat_service._build_mission_state(
            working_state=working_state,
            execution_state=execution_state,
        )

        autonomous_direction = ""

        if has_failed_steps:
            autonomous_direction = retry_strategy

        elif has_active_execution:
            autonomous_direction = "continue_execution"

        elif mission_state.get("recommended_next_move"):
            autonomous_direction = mission_state.get("recommended_next_move")

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
