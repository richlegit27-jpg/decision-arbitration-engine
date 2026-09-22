class DecisionService:

    def __init__(self, chat_service):
        self.chat_service = chat_service

    def safe_str(self, value):
        return str(value or "").strip()

    def _execution_decision(
        self,
        user_text: str,
        intent: str,
        reason: str,
        command: str = "",
        mode: str = "execution",
    ) -> dict:
        decision = {
            "route": "execution",
            "mode": mode,
            "intent": intent,
            "confidence": 1.0,
            "reasons": [
                reason,
            ],
            "save_artifact": False,
            "save_memory": False,
            "use_memory": False,
            "prompt": user_text,
        }

        if command:
            decision["command"] = command

        return decision

    def _extract_explicit_command(self, user_text: str) -> str:
        text = self.safe_str(user_text).strip()

        if not text:
            return ""

        lower_text = text.lower()

        command_markers = (
            "terminal command now:",
            "terminal command:",
            "execute this terminal command now:",
            "execute this terminal command:",
            "execute this command now:",
            "execute this command:",
            "run this terminal command now:",
            "run this terminal command:",
            "run this command now:",
            "run this command:",
            "that runs:",
            "which runs:",
            "to run:",
            "execute:",
            "run:",
        )

        for marker in command_markers:
            marker_index = lower_text.find(marker)

            if marker_index >= 0:
                command = text[
                    marker_index + len(marker):
                ].strip()

                if command:
                    return command

        # Standalone commands are already complete commands.
        command_prefixes = (
            "write-output ",
            "write-host ",
            "get-childitem ",
            "get-content ",
            "set-content ",
            "add-content ",
            "remove-item ",
            "copy-item ",
            "move-item ",
            "new-item ",
            "invoke-restmethod ",
            "invoke-webrequest ",
            "python ",
            "py ",
            "python3 ",
            "node ",
            "npm ",
            "npx ",
            "git ",
            "curl ",
            "curl.exe ",
            "powershell ",
            "pwsh ",
            "bash ",
            "sh ",
            "cmd ",
            "echo ",
        )

        if lower_text.startswith(command_prefixes):
            return text

        if (
            lower_text.endswith(".ps1")
            or " -file " in lower_text
            or lower_text.startswith(".\\")
            or lower_text.startswith("./")
        ):
            return text

        return ""

    def _has_explicit_execution_intent(self, lower_text: str) -> bool:
        lower_text = self.safe_str(lower_text).strip().lower()

        explicit_phrases = (
            "execute this terminal command",
            "execute this command",
            "run this terminal command",
            "run this command",
            "execute the terminal command",
            "execute the command",
            "run the terminal command",
            "run the command",
            "create a project execution step",
            "create an execution step",
            "create a terminal execution step",
            "make a project execution step",
            "make an execution step",
            "terminal command now",
            "execute now",
            "run now",
        )

        if any(
            phrase in lower_text
            for phrase in explicit_phrases
        ):
            return True

        command_prefixes = (
            "write-output ",
            "write-host ",
            "get-childitem ",
            "get-content ",
            "set-content ",
            "add-content ",
            "remove-item ",
            "copy-item ",
            "move-item ",
            "new-item ",
            "invoke-restmethod ",
            "invoke-webrequest ",
            "python ",
            "py ",
            "python3 ",
            "node ",
            "npm ",
            "npx ",
            "git ",
            "curl ",
            "curl.exe ",
            "powershell ",
            "pwsh ",
            "bash ",
            "sh ",
            "cmd ",
            "echo ",
        )

        if lower_text.startswith(command_prefixes):
            return True

        if (
            lower_text.endswith(".ps1")
            or " -file " in lower_text
            or lower_text.startswith(".\\")
            or lower_text.startswith("./")
        ):
            return True

        return False

    def _decide_route(
        self,
        user_text: str,
        attachments=None,
        session_id: str = "",
    ) -> dict:

        user_text = self.safe_str(user_text)
        lower_text = user_text.lower()

        # Resume an existing unfinished execution before normal route
        # classification can send the continuation to general_chat or
        # project_brain.
        pending_execution = False

        try:
            execution_state = self.chat_service._load_execution_state(
                session_id
            )

            if isinstance(execution_state, dict):
                steps = execution_state.get("steps") or []
                current_index = execution_state.get(
                    "current_index",
                    0,
                )
                execution_status = self.safe_str(
                    execution_state.get("status")
                ).lower()

                try:
                    current_index = int(current_index or 0)
                except (TypeError, ValueError):
                    current_index = 0

                pending_execution = (
                    isinstance(steps, list)
                    and bool(steps)
                                        and execution_status in {
                        "pending",
                        "running",
                        "in_progress",
                        "paused",
                        "waiting",
                        "waiting_approval",
                    }
                    and current_index < len(steps)
                )

        except Exception as exc:
            print(
                "[DECISION PENDING EXECUTION CHECK FAILED]",
                repr(exc),
            )

        project_execution_request = (
            (
                "create a project" in lower_text
                or "create a tiny test project" in lower_text
                or "build a project" in lower_text
                or "make a project" in lower_text
            )
            and (
                "execute" in lower_text
                or "run" in lower_text
                or "start" in lower_text
            )
        )

        if project_execution_request:
            return self._execution_decision(
                user_text=user_text,
                intent="project_execution",
                reason="project_creation_with_execution_request",
            )

        if pending_execution:
            return self._execution_decision(
                user_text=user_text,
                intent="execution_continuation",
                reason="pending_execution_priority",
            )

        # Explicit terminal-command execution must be evaluated before
        # general action classification and before the default chat route.
        explicit_command = self._extract_explicit_command(
            user_text
        )

        if (
            explicit_command
            and self._has_explicit_execution_intent(
                lower_text
            )
        ):
            return self._execution_decision(
                user_text=user_text,
                intent="terminal_command_execution",
                reason="explicit_terminal_command",
                command=explicit_command,
            )

        # Explicit project-execution-step creation.
        if (
            "create a project execution step" in lower_text
            or "create an execution step" in lower_text
            or "create a terminal execution step" in lower_text
            or "make a project execution step" in lower_text
            or "make an execution step" in lower_text
        ):
            return self._execution_decision(
                user_text=user_text,
                intent="execution_step_creation",
                reason="explicit_execution_step_request",
                command=explicit_command,
            )

        # Explicitly execute the currently selected project step.
        if (
            "execute the next step" in lower_text
            or "run the next step" in lower_text
            or "proceed with the next step" in lower_text
            or "continue with the next step" in lower_text
        ):
            return self._execution_decision(
                user_text=user_text,
                intent="execution_continuation",
                reason="explicit_next_project_step_execution",
                mode="execution",
            )

        if (
            "what should i do next" in lower_text
            or "best next step" in lower_text
        ):
            return {
                "route": "project_brain",
                "mode": "project_state",
                "intent": "mission_control",
                "confidence": 1.0,
                "reasons": [
                    "next_step_request",
                ],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": True,
                "prompt": user_text,
            }

        if any(
            phrase in lower_text
            for phrase in [
                "what are we working on",
                "what are we working on right now",
                "current blocker",
                "what should we do next",
                "next move",
                "where are we",
            ]
        ):

            return {
                "route": "project_brain",
                "mode": "project_state",
                "intent": "mission_control",
                "confidence": 1.0,
                "reasons": [
                    "project_state_priority",
                ],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": True,
                "prompt": user_text,
            }

        short_chat = (
            "hello",
            "hi",
            "hey",
            "yo",
            "thanks",
            "thank you",
        )

        if lower_text.strip() in short_chat:
            return {
                "route": "general_chat",
                "mode": "chat",
                "intent": "conversation",
                "confidence": 0.95,
                "reasons": [
                    "short_chat",
                ],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": False,
                "prompt": user_text,
            }

        if lower_text.startswith(
            (
                "auto-plan ",
                "autoplan ",
                "auto plan ",
            )
        ):
            return {
                "route": "execution",
                "mode": "auto_plan",
                "intent": "mission_creation",
                "confidence": 1.0,
                "reasons": [
                    "auto_plan_command",
                ],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": False,
                "prompt": user_text,
            }

        project_state_triggers = (
            "status",
            "what's next",
            "whats next",
            "what should i do next",
            "next move",
            "current blocker",
            "where are we",
            "where are we at",
            "what are we doing",
            "what is left",
            "what are we working on",
            "what are we working on now",
            "what are we working on right now",
        )

        if any(
            trigger in lower_text
            for trigger in project_state_triggers
        ):
            return {
                "route": "project_brain",
                "mode": "project_state",
                "intent": "mission_control",
                "confidence": 0.95,
                "reasons": [
                    "project_state_question",
                ],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": True,
                "prompt": user_text,
            }

        execution_triggers = (
            "next",
            "continue",
            "keep going",
            "run step",
            "run all",
            "execute",
            "advance",
            "stop",
            "cancel",
        )

        if lower_text.strip() in execution_triggers:
            return self._execution_decision(
                user_text=user_text,
                intent="execution_control",
                reason="execution_command",
            )

        execution_action_prefixes = (
            "create ",
            "make ",
            "write ",
                        "fix ",
            "edit ",
            "modify ",
            "update ",
            "delete ",
            "remove ",
            "rename ",
            "move ",
            "copy ",
            "run ",
            "start ",
            "stop ",
            "restart ",
            "install ",
            "uninstall ",
            "execute ",
        )

        execution_action_terms = (
            " file",
            " folder",
            " directory",
            ".py",
            ".js",
            ".json",
            ".txt",
            ".md",
            ".html",
            ".css",
            ".ps1",
            "command",
            "script",
            "process",
            "function",
            "class",
            "endpoint",
            "service",
            "terminal",
            "execution step",
        )

        project_execution_request = (
            (
                "create a project" in lower_text
                or "create a tiny test project" in lower_text
                or "build a project" in lower_text
                or "make a project" in lower_text
            )
            and (
                "execute" in lower_text
                or "run" in lower_text
                or "start" in lower_text
            )
        )

        if project_execution_request:
            return self._execution_decision(
                user_text=user_text,
                intent="project_execution",
                reason="project_creation_with_execution_request",
            )

        project_creation_execution = (
            (
                "project" in lower_text
                or "workspace" in lower_text
            )
            and (
                "execute" in lower_text
                or "run" in lower_text
                or "start" in lower_text
            )
        )

        is_execution_action = (
            lower_text.startswith(
                execution_action_prefixes
            )
            and any(
                term in lower_text
                for term in execution_action_terms
            )
        )

        task_creation_triggers = (
            "create a task",
            "create task",
            "make a task",
            "create a test task",
            "make a test task",
            "create steps",
            "make steps",
            "create a checklist",
            "make a checklist",
        )

        if any(
            trigger in lower_text
            for trigger in task_creation_triggers
        ):
            return self._execution_decision(
                user_text=user_text,
                intent="task_creation",
                reason="task_creation_request",
            )

        if is_execution_action:
            return self._execution_decision(
                user_text=user_text,
                intent="task_execution",
                reason="explicit_execution_action",
                command=explicit_command,
            )

        task_creation_triggers = (
            "create a task",
            "create task",
            "make a task",
            "make a test task",
            "create a test task",
            "create a simple test task",
            "build a task",
        )

        if any(
            trigger in lower_text
            for trigger in task_creation_triggers
        ):
            return self._execution_decision(
                user_text=user_text,
                intent="task_creation",
                reason="task_creation_request",
            )

        planning_triggers = (
            "plan",
            "planning",
            "roadmap",
            "strategy",
            "launch plan",
            "project plan",
            "create a plan",
            "make a plan",
            "build a plan",
            "implementation plan",
            "development plan",
            "technical plan",
            "architecture plan",
        )

        if any(
            trigger in lower_text
            for trigger in planning_triggers
        ):
            return {
                "route": "planner",
                "mode": "planning",
                "intent": "planning",
                "confidence": 0.95,
                "reasons": [
                    "explicit_planning_request",
                ],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": True,
                "prompt": user_text,
            }

        return {
            "route": "general_chat",
            "mode": "chat",
            "confidence": 0.6,
            "reasons": [
                "default_chat",
            ],
            "save_artifact": True,
            "save_memory": True,
            "use_memory": True,
            "prompt": user_text,
        }








