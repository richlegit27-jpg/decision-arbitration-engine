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

    def _is_explicit_project_creation_request(self, user_text: str) -> bool:
        """Recognize direct project-building requests, not how-to questions."""
        text = " ".join(self.safe_str(user_text).lower().split()).rstrip("?!. ")

        informational_prefixes = (
            "how do i ",
            "how can i ",
            "how would i ",
            "how do you ",
            "how can you ",
            "tell me how ",
            "explain how ",
            "what is the best way to ",
            "what would it take to ",
        )
        if text.startswith(informational_prefixes):
            return False

        # Strip polite/request lead-ins, then require an explicit
        # creation/build verb at the start of the remaining request.
        for _ in range(2):
            matched_prefix = False
            for prefix in (
                "please ",
                "can you ",
                "could you ",
                "would you ",
                "i want you to ",
                "i need you to ",
                "i'd like you to ",
                "i would like you to ",
                "let's ",
                "i want to ",
            ):
                if text.startswith(prefix):
                    text = text[len(prefix):].lstrip()
                    matched_prefix = True
                    break
            if not matched_prefix:
                break

        # A request for a project plan is not necessarily a request to create
        # a persistent Nova project. The explicit "project to ..." form is.
        if text.startswith((
            "create a project plan",
            "make a project plan",
            "build a project plan",
        )):
            return False

        action_prefixes = (
            "create a project",
            "create a new project",
            "create project",
            "create new project",
            "make a project",
            "make a new project",
            "build a project",
            "build a new project",
            "start a project",
            "start a new project",
            "new project",
            "build me ",
            "create me ",
            "make me ",
            "develop me ",
            "design me ",
            "build a ",
            "build an ",
            "create a ",
            "create an ",
            "make a ",
            "make an ",
            "develop a ",
            "develop an ",
            "implement a ",
            "implement an ",
            "design a website",
            "design an app",
            "i need a project ",
        )
        return text.startswith(action_prefixes)

    def _decide_route(
        self,
        user_text: str,
        attachments=None,
        session_id: str = "",
    ) -> dict:

        user_text = self.safe_str(user_text)
        lower_text = user_text.lower()

        # Repository questions and Git mutation requests must be claimed
        # before pending execution or generic command routing. The dedicated
        # Code Workspace only exposes configured-root read operations.
        code_workspace = getattr(
            self.chat_service,
            "code_workspace_service",
            None,
        )
        if code_workspace is not None and not attachments:
            code_workspace_intent = code_workspace.classify_request(user_text)
            if code_workspace_intent:
                return {
                    "route": "code_workspace",
                    "mode": "read_only_repository_inspection",
                    "intent": code_workspace_intent,
                    "confidence": 1.0,
                    "reasons": ["configured_repository_git_intent"],
                    "save_artifact": False,
                    "save_memory": False,
                    "use_memory": False,
                    "prompt": user_text,
                }

        # Resume an existing unfinished execution before normal route
        # classification can send the continuation to general_chat or
        # project_brain.
        pending_execution = False

        try:
            execution_state = self.chat_service._load_execution_state(
                session_id
            )

            print(
                "[DECISION APPROVAL STATE]",
                {
                    "session_id": session_id,
                    "status": (
                        execution_state.get("status")
                        if isinstance(execution_state, dict)
                        else None
                    ),
                    "current_index": (
                        execution_state.get("current_index")
                        if isinstance(execution_state, dict)
                        else None
                    ),
                    "step_count": (
                        len(execution_state.get("steps") or [])
                        if isinstance(execution_state, dict)
                        else 0
                    ),
                    "waiting": (
                        execution_state.get("waiting")
                        if isinstance(execution_state, dict)
                        else None
                    ),
                    "approval_required": (
                        execution_state.get("approval_required")
                        if isinstance(execution_state, dict)
                        else None
                    ),
                },
                flush=True,
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

                current_step = (
                    steps[current_index]
                    if (
                        isinstance(steps, list)
                        and 0 <= current_index < len(steps)
                        and isinstance(steps[current_index], dict)
                    )
                    else {}
                )

                approval_waiting = (
                    isinstance(current_step, dict)
                    and (
                        current_step.get("approval_required") is True
                        or current_step.get("requires_approval") is True
                        or self.safe_str(
                            current_step.get("status")
                        ).lower()
                        in {
                            "waiting_approval",
                            "awaiting_approval",
                            "approval_required",
                        }
                    )
                )

                if (
                    approval_waiting
                    and lower_text.strip()
                    in {
                        "yes",
                        "y",
                        "yeah",
                        "yep",
                        "sure",
                        "okay",
                        "ok",
                        "go ahead",
                        "do it",
                        "approve",
                        "approved",
                        "approve step",
                        "approve execution",
                    }
                ):
                    return self._execution_decision(
                        user_text=user_text,
                        intent="execution_control",
                        reason="approval_confirmation",
                        command="approve",
                    )

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

        project_execution_request = self._is_explicit_project_creation_request(
            user_text
        )

        if project_execution_request:
            explicit_execution = any(
                marker in lower_text
                for marker in (
                    "run it",
                    "run the project",
                    "execute it",
                    "execute the project",
                    "start execution",
                    "run all tasks",
                )
            )
            if explicit_execution:
                return self._execution_decision(
                    user_text=user_text,
                    intent="project_execution",
                    reason="project_creation_with_explicit_execution_request",
                )

            return {
                "route": "project_builder",
                "mode": "project_creation",
                "intent": "project_creation",
                "confidence": 1.0,
                "reasons": ["explicit_conversational_project_creation"],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": True,
                "prompt": user_text,
            }

        print(
            "[NOVA_IMAGE_ROUTE_DIAGNOSTIC]",
            {
                "attachments_type": type(attachments).__name__,
                "attachments_is_list": isinstance(attachments, list),
                "attachment_count": (
                    len(attachments)
                    if isinstance(attachments, list)
                    else None
                ),
                "attachment_items": [
                    {
                        "type": type(item).__name__,
                        "mime_type": (
                            item.get("mime_type") or item.get("type")
                            if isinstance(item, dict)
                            else None
                        ),
                        "filename": (
                            item.get("filename")
                            or item.get("original_filename")
                            or item.get("name")
                            if isinstance(item, dict)
                            else None
                        ),
                    }
                    for item in attachments
                ] if isinstance(attachments, list) else [],
                "detector_result": (
                    self.chat_service._nova_has_image_attachment_20260607(
                        attachments
                    )
                ),
            },
            flush=True,
        )

        # NOVA_IMAGE_ATTACHMENT_ROUTE_20260929
        # Route uploaded images through the existing vision handler.
        if (
            isinstance(attachments, list)
            and any(
                isinstance(item, dict)
                and (
                    item.get("mime_type")
                    or item.get("type")
                    or item.get("filename")
                    or item.get("url")
                    or item.get("file_url")
                )
                for item in attachments
            )
        ):
            return {
                "route": self.chat_service.ROUTE_ATTACHMENT_ANALYSIS,
                "mode": "image_analysis",
                "intent": "image_analysis",
                "confidence": 1.0,
                "reasons": [
                    "image_attachment_requires_vision",
                ],
                "save_artifact": False,
                "save_memory": False,
                "use_memory": False,
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

        if (
            pending_execution
            and not approval_waiting
            and lower_text.strip()
            not in short_chat
        ):
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
            lower_text.strip() == "next"
            or lower_text.strip() == "next step"
            or "execute the next step" in lower_text
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

        if (
            pending_execution
            and not approval_waiting
            and lower_text.strip()
            not in short_chat
        ):
            return self._execution_decision(
                user_text=user_text,
                intent="execution_continuation",
                reason="pending_execution_priority",
            )
        # Explicit terminal-command execution must be evaluated before
        # existing ChatService image-generation pipeline.
        if lower_text.startswith(
            (
                "/image ",
                "/image",
                "generate an image ",
                "generate image ",
                "create an image ",
                "create image ",
                "make an image ",
                "make image ",
                "draw ",
                "draw me ",
            )
        ):
            return {
                "route": "image_generation",
                "mode": "image_generation",
                "intent": "image_generation",
                "confidence": 0.95,
                "reasons": [
                    "explicit_image_request",
                ],
                "save_artifact": True,
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
            "what are we going to do first",
            "what should we do first",
            "what is the first task",
            "what's the first task",
            "whats the first task",
            "first saved task",
            "exact first task in the project",
            "what is left",
            "what's left",
            "whats left",
            "what did we finish",
            "what have we finished",
            "what have we completed",
            "what's blocking us",
            "what is blocking us",
            "explain the current task",
            "explain current task",
            "describe the current task",
            "continue planning it",
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
            "approve",
            "approved",
            "approve step",
            "approve execution",
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

        project_execution_request = self._is_explicit_project_creation_request(
            user_text
        ) and any(word in lower_text for word in ("execute", "run", "start"))

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
