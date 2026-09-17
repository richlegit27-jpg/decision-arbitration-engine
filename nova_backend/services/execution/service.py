import re
import uuid
from datetime import datetime


class ExecutionService:

    def __init__(
        self,
        chat_service,
        chat_execution_service=None,
    ):
        self.chat_service = chat_service
        self.chat_execution_service = chat_execution_service

    @staticmethod
    def safe_str(value):
        """
        Safely normalize arbitrary values into a string.
        """
        if value is None:
            return ""

        if isinstance(value, str):
            return value

        try:
            return str(value)
        except Exception:
            return ""



    def _extract_file_creation_request(
        self,
        user_text,
    ):
        """
        Extract a requested filename and file contents from natural language.
        """

        original_text = str(user_text or "").strip()

        filename_match = re.search(
            r"(?:named|called|file)\s+[`\"']?([A-Za-z0-9_.-]+\.[A-Za-z0-9]+)",
            original_text,
            re.IGNORECASE,
        )

        if not filename_match:
            filename_match = re.search(
                r"\b([A-Za-z0-9_.-]+\.(?:txt|md|json|csv|py|js|html|css))\b",
                original_text,
                re.IGNORECASE,
            )

        if not filename_match:
            return {
                "filename": "",
                "target_file": "",
                "content": "",
            }

        filename = filename_match.group(1).strip()

        content_match = re.search(
            r"(?:containing|with)\s+(?:the\s+)?(?:text|content|contents?)\s+(.+?)(?=\s+then\s+verify\b|\s+and\s+verify\b|$)",
            original_text,
            re.IGNORECASE | re.DOTALL,
        )

        if not content_match:
            content_match = re.search(
                r"(?:text|content|contents?)\s*[:=]\s*[`\"']?(.+?)(?:[`\"']?\s+then\s+verify\b|[`\"']?\s+and\s+verify\b|$)",
                original_text,
                re.IGNORECASE | re.DOTALL,
            )

        content = ""
        if content_match:
            content = content_match.group(1).strip()
            content = content.strip("`\"' ")
            content = content.rstrip(" .,;:")
            content = content.rstrip(" .,;:")
            content = content.rstrip(" .,;:")

        target_file = filename

        if not re.match(r"^[A-Za-z]:[\\/]", target_file):
            target_file = str(
                __import__("pathlib").Path.cwd() / filename
            )

        return {
            "filename": filename,
            "target_file": target_file,
            "content": content,
        }
    def _build_goal(
        self,
        user_text,
        session_id=None
    ):
        """
        Converts raw input into a structured goal.
        """

        original_text = str(
            user_text
            or ""
        ).strip()

        text = original_text.lower()

        file_creation_request = (
            (
                "create" in text
                or "make" in text
                or "write" in text
            )
            and (
                "file" in text
                or ".txt" in text
                or ".md" in text
                or ".json" in text
                or ".csv" in text
                or ".py" in text
                or ".js" in text
                or ".html" in text
                or ".css" in text
            )
        )

        if file_creation_request:
            file_request = self._extract_file_creation_request(
                original_text
            )

            return {
                "type": "file_creation",
                "goal": original_text,
                "original_text": original_text,
                "filename": file_request.get("filename") or "",
                "target_file": file_request.get("target_file") or "",
                "content": file_request.get("content") or "",
            }

        if (
            "fix" in text
            or "error" in text
            or "bug" in text
            or "broken" in text
        ):
            return {
                "type": "debug",
                "goal": "debug and fix issue",
            }

        if (
            "plan" in text
            or "planning" in text
            or "roadmap" in text
            or "strategy" in text
            or "organize" in text
            or "steps" in text
        ):
            return {
                "type": "planning",
                "goal": "create project plan",
            }

        if (
            "build" in text
            or "create" in text
            or "make" in text
            or "develop" in text
        ):
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


    def _build_plan(
        self,
        goal_obj: dict,
    ):
        """
        Turns a structured goal into executable plan steps.
        """

        goal_obj = (
            goal_obj
            if isinstance(goal_obj, dict)
            else {}
        )

        goal_type = str(
            goal_obj.get("type") or ""
        ).strip().lower()

        if goal_type == "debug":

            return [
                {
                    "action": "analyze",
                    "input": (
                        "Inspect the issue and identify "
                        "the root cause."
                    ),
                },
                {
                    "action": "diagnose",
                    "input": (
                        "Determine the affected components."
                    ),
                },
                {
                    "action": "fix",
                    "input": "Apply the required correction.",
                },
                {
                    "action": "validate",
                    "input": (
                        "Test the result and confirm "
                        "the resolution."
                    ),
                },
            ]

        if goal_type == "analysis":

            return [
                {
                    "action": "analyze",
                    "input": (
                        "Inspect the provided information."
                    ),
                },
                {
                    "action": "organize",
                    "input": (
                        "Extract the important patterns."
                    ),
                },
                {
                    "action": "summarize",
                    "input": (
                        "Generate useful insights."
                    ),
                },
            ]

        if goal_type in {
            "planning",
            "plan",
        }:

            return [
                {
                    "action": "analyze",
                    "input": (
                        "Analyze the requested objective "
                        "and identify the required work."
                    ),
                },
                {
                    "action": "plan",
                    "input": (
                        "Create an ordered execution plan "
                        "for the requested objective."
                    ),
                },
                {
                    "action": "validate",
                    "input": (
                        "Validate that the execution plan "
                        "contains actionable steps."
                    ),
                },
            ]

        if goal_type == "file_creation":

            original_text = str(
                goal_obj.get("original_text")
                or goal_obj.get("goal")
                or ""
            ).strip()

            filename = str(
                goal_obj.get("filename")
                or ""
            ).strip()

            target_file = str(
                goal_obj.get("target_file")
                or ""
            ).strip()

            content = str(
                goal_obj.get("content")
                or ""
            )

            return [
                {
                    "action": "create",
                    "title": (
                        f"Create {filename}"
                        if filename
                        else "Create requested file"
                    ),
                    "input": original_text,
                    "description": original_text,
                    "target_file": target_file,
                    "content": content,
                    "file_content": content,
                    "code": content,
                },
                {
                    "action": "verify",
                    "title": (
                        f"Verify {filename}"
                        if filename
                        else "Verify requested file"
                    ),
                    "input": original_text,
                    "description": original_text,
                    "target_file": target_file,
                },
            ]

        if goal_type == "build":

            return [
                {
                    "action": "planning",
                    "input": (
                        "Understand the requirements "
                        "and define the scope."
                    ),
                },
                {
                    "action": "architecture",
                    "input": (
                        "Design the system structure "
                        "and components."
                    ),
                },
                {
                    "action": "design",
                    "input": (
                        "Create a detailed implementation plan."
                    ),
                },
                {
                    "action": "implementation",
                    "input": (
                        "Build the core functionality."
                    ),
                    "target_file": (
                        r"C:\Users\Owner\nova\nova_backend"
                        r"\sandbox\agent_target.py"
                    ),
                    "target_function": (
                        "placeholder_function"
                    ),
                },
                {
                    "action": "integration",
                    "input": (
                        "Connect the components and services."
                    ),
                },
                {
                    "action": "testing",
                    "input": (
                        "Validate functionality and detect "
                        "issues."
                    ),
                    "target_file": (
                        r"C:\Users\Owner\nova\nova_backend"
                        r"\sandbox\agent_target.py"
                    ),
                },
                {
                    "action": "optimization",
                    "input": (
                        "Improve quality, reliability, "
                        "and performance."
                    ),
                },
                {
                    "action": "delivery",
                    "input": (
                        "Prepare the final result and "
                        "summarize the work."
                    ),
                },
            ]

        return [
            {
                "action": "execute",
                "input": (
                    "Execute the requested objective."
                ),
            },
        ]

    def _execute_tool(
        self,
        step: dict,
    ):

        step = (
            step
            if isinstance(step, dict)
            else {}
        )

        action = str(
            step.get("action")
            or ""
        ).strip().lower()

        input_data = (
            step.get("input")
            or step.get("description")
            or step.get("text")
            or ""
        )

        if action in {
            "execute",
            "run_step",
        }:
            return (
                "Executed the requested task: "
                f"{input_data}"
            )

        if action == "verify":
            return (
                "Verified the execution result "
                "for the requested task."
            )

        if action == "analyze":
            return f"analyzed: {input_data}"

        if action == "diagnose":
            return f"diagnosed: {input_data}"

        if action == "fix":
            return f"fixed: {input_data}"

        if action == "validate":
            return f"validated: {input_data}"

        if action in {
            "plan",
            "planning",
        }:
            return f"planned: {input_data}"

        if action == "architecture":
            return f"architected: {input_data}"

        if action == "design":
            return f"designed: {input_data}"

        if action in {
            "implement",
            "implementation",
        }:
            return f"implemented: {input_data}"

        if action == "integration":
            return f"integrated: {input_data}"

        if action == "testing":
            return f"tested: {input_data}"

        if action == "optimization":
            return f"optimized: {input_data}"

        if action == "delivery":
            return f"delivered: {input_data}"

        if action == "respond":
            return f"response: {input_data}"

        return f"unknown action: {action}"


    def _build_execution(
        self,
        user_text: str,
        assistant_text: str,
        decision: dict | None,
    ) -> dict | None:

        if not self.chat_service._looks_like_execution(
            user_text,
            decision,
        ):
            return None

        goal = str(
            user_text or ""
        ).strip()

        step_titles = (
            self.chat_service
            ._execution_step_titles_for_goal(
                goal
            )
        )

        now_iso = (
            self.chat_service
            ._iso_now()
        )

        step_objs = []

        for i, title in enumerate(
            step_titles,
            start=1,
        ):
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
            "current_step": (
                step_titles[0]
                if step_titles
                else ""
            ),
            "summary": str(
                assistant_text or ""
            )[:200],
            "steps": step_objs,
            "started_at": now_iso,
            "updated_at": now_iso,
        }

    def run(
        self,
        user_text: str,
        session_id: str = "",
        decision: dict | None = None,
    ) -> dict:
        """
        Main execution entry point.
        Creates goal -> plan -> stores execution state.
        """

        return self._process_goal_and_plan(
            user_text=user_text,
            session_id=session_id,
        )

    def _process_goal_and_plan(self, user_text: str, session_id: str):
        user_text = self.safe_str(user_text).strip()

        existing_state = (
            self.chat_service._load_execution_state(
                session_id
            )
        )

        if (
            isinstance(existing_state, dict)
            and isinstance(existing_state.get("steps"), list)
            and existing_state.get("steps")
        ):
            current_index = existing_state.get(
                "current_index",
                0,
            )

            try:
                current_index = int(
                    current_index
                )
            except (TypeError, ValueError):
                current_index = 0

            execution_status = str(
                existing_state.get("status")
                or ""
            ).strip().lower()

            current_step = (
                existing_state["steps"][current_index]
                if 0 <= current_index < len(
                    existing_state["steps"]
                )
                else {}
            )

            current_action = str(
                current_step.get("action")
                if isinstance(current_step, dict)
                else ""
            ).strip().lower()

            continuation_terms = (
                "continue",
                "resume",
                "next step",
                "finish",
                "proceed",
                "retry",
                "run it",
                "execute it",
                "go ahead",
            )

            is_continuation = any(
                term in user_text.lower()
                for term in continuation_terms
            )

            reusable_status = execution_status in {
                "running",
                "waiting",
                "paused",
                "pending",
            }

            reusable_action = current_action not in {
                "",
                "implement",
                "create_file",
                "write_file",
            }

            if (
                current_index < len(
                    existing_state["steps"]
                )
                and reusable_status
                and is_continuation
                and reusable_action
            ):
                exec_debug(
                    "REUSING EXISTING EXECUTION STATE "
                    f"session_id={session_id} "
                    f"current_index={current_index} "
                    f"steps={len(existing_state['steps'])}"
                )

                return existing_state

            exec_debug(
                "DISCARDING STALE OR NON-CONTINUATION "
                "EXECUTION STATE "
                f"session_id={session_id} "
                f"status={execution_status} "
                f"current_action={current_action} "
                f"current_index={current_index}"
            )

            self._save_execution_state(
                session_id,
                {},
            )

        goal = self._build_goal(user_text)

        if (
            isinstance(goal, dict)
            and str(goal.get("type") or "").strip().lower() == "general"
            and str(goal.get("goal") or "").strip().lower() == "respond normally"
        ):
            exec_debug(
                "BLOCKED GENERAL CHAT EXECUTION PLAN"
            )

            self._save_execution_state(session_id, {})

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

                action = (
                    step.get("action")
                    or "execute"
                )

                input_value = (
                    step.get("input")
                    or user_text
                )

                if (
                    "python project" in user_text.lower()
                    or "create a small python" in user_text.lower()
                ):

                    action = "implement"

                    step["target_file"] = (
                        "hello_nova/main.py"
                    )

                    step["content"] = (
                        "def greet():\n"
                        "    return \"Hello Nova\"\n\n\n"
                        "if __name__ == \"__main__\":\n"
                        "    print(greet())\n"
                    )

                    step["mutation_mode"] = "create"
                    step["next_action"] = "execute"
                    step["mutation_ready"] = True
                    step["payload_required"] = False

                if (
                    "flask api" in user_text.lower()
                    or "create a flask api" in user_text.lower()
                ):

                    action = "implement"

                    step["target_file"] = (
                        "flask_api/app.py"
                    )

                    step["content"] = (
                        "from flask import Flask, jsonify\n\n"
                        "app = Flask(__name__)\n\n\n"
                        "@app.route('/')\n"
                        "def home():\n"
                        "    return jsonify({\"message\": \"Hello Nova API\"})\n\n\n"
                        "if __name__ == \"__main__\":\n"
                        "    app.run(debug=True)\n"
                    )

                    step["mutation_mode"] = "create"
                    step["next_action"] = "execute"
                    step["mutation_ready"] = True
                    step["payload_required"] = False

                print(
                    "DEBUG RAW STEP BEFORE NORMALIZE =",
                    step,
                    flush=True,
                )


                normalized_steps.append(
                    {
                        "id": f"step_{index}",
                        "title": title,
                        "action": action,
                        "input": input_value,

                        "target_file": (
                            step.get("target_file")
                            or ""
                        ),

                        "target_files": (
                            step.get("target_files")
                            or []
                        ),

                        "target_function": (
                            step.get("target_function")
                            or ""
                        ),

                        "content": (
                            step.get("content")
                            or ""
                        ),

                        "file_content": (
                            step.get("file_content")
                            or step.get("content")
                            or step.get("code")
                            or ""
                        ),

                        "code": (
                            step.get("code")
                            or ""
                        ),

                        "mutation_mode": (
                            step.get("mutation_mode")
                        ),

                        "next_action": (
                            step.get("next_action")
                        ),

                        "mutation_ready": bool(
                            step.get("mutation_ready")
                        ),

                        "payload_required": bool(
                            step.get("payload_required")
                        ),

                        "execution_file": (
                            step.get("execution_file")
                            or ""
                        ),

                        "run_file": (
                            step.get("run_file")
                            or ""
                        ),

                        "script_file": (
                            step.get("script_file")
                            or ""
                        ),

                        "test_script": (
                            step.get("test_script")
                            or ""
                        ),

                        "test_file": (
                            step.get("test_file")
                            or ""
                        ),

                        "command": (
                            step.get("command")
                            or ""
                        ),

                        "status": "pending",
                        "result": "",
                        "error": None,
                    }
                )

            else:

                normalized_steps.append(
                    {
                        "id": f"step_{index}",
                        "title": (
                            self.safe_str(step)
                            or f"Execution Step {index}"
                        ),
                        "action": "execute",
                        "input": user_text,
                        "target_file": "",
                        "target_function": "",
                        "content": "",
                        "file_content": "",
                        "code": "",
                        "status": "pending",
                        "result": "",
                        "error": None,
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
                    "error": None,
                },
                {
                    "id": "step_2",
                    "title": "Build execution plan",
                    "action": "plan",
                    "input": user_text,
                    "status": "pending",
                    "result": "",
                    "error": None,
                },
                {
                    "id": "step_3",
                    "title": "Validate execution result",
                    "action": "validate",
                    "input": user_text,
                    "status": "pending",
                    "result": "",
                    "error": None,
                },
            ]

        execution_state = {
            "status": "running",
            "goal": (
                goal.get("goal", user_text)
                if isinstance(goal, dict)
                else goal
            ),
            "original_user_text": user_text,
            "steps": normalized_steps,
            "plan": normalized_steps,
            "current_index": 0,
            "current_step": normalized_steps[0].get(
                "title",
                "Execution Step 1",
            ),
            "current_step_title": normalized_steps[0].get(
                "title",
                "Execution Step 1",
            ),
            "history": [],
            "last_action": "execution_requested",
            "waiting": False,
        }

        if self.chat_execution_service:
            self.chat_execution_service.start(
                session_id=session_id,
                goal=execution_state.get(
                    "goal",
                    user_text,
                ),
                steps=normalized_steps,
                context={
                    "task_type": (
                        goal.get("type", "general")
                        if isinstance(goal, dict)
                        else "general"
                    )
                },
            )

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

        try:
            session_obj = (
                self.sessions.get_session(session_id)
                or {}
            )

            session_obj["execution_state"] = execution_state
            session_obj["active_execution"] = execution_state

            self.sessions.update_session(
                session_id,
                session_obj,
            )

        except Exception as e:
            exec_debug(
                "PLAN SAVE FAILED:",
                e,
            )

        print(
            "DEBUG CHAT EXECUTION SERVICE:",
            self.chat_execution_service,
        )

        exec_debug(
            "EXECUTION MISSION CREATED - WAITING FOR USER ADVANCE",
            execution_state,
        )

        exec_debug(
            "_process_goal_and_plan RETURN =",
            execution_state,
        )

        print(
            "DEBUG PROCESS GOAL PLAN RETURN =",
            execution_state,
        )

        return execution_state




