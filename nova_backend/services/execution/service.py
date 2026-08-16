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


    def _build_goal(
        self,
        user_text,
        session_id=None
    ):
        """
        Converts raw input into a structured goal.
        """

        text = (
            user_text
            or ""
        ).lower()

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
        Turns a goal into structured execution phases.
        """

        goal_type = str(
            goal_obj.get("type") or ""
        ).strip().lower()

        if goal_type == "debug":

            return [
                {
                    "action": "analyze",
                    "input": "inspect issue and identify root cause",
                },
                {
                    "action": "diagnose",
                    "input": "determine affected components",
                },
                {
                    "action": "fix",
                    "input": "apply correction",
                },
                {
                    "action": "validate",
                    "input": "test result and confirm resolution",
                },
            ]

        if goal_type == "analysis":

            return [
                {
                    "action": "analyze",
                    "input": "inspect provided information",
                },
                {
                    "action": "organize",
                    "input": "extract important patterns",
                },
                {
                    "action": "summarize",
                    "input": "generate useful insights",
                },
            ]

        if goal_type == "build":

            return [
                {
                    "action": "planning",
                    "input": "understand requirements and define scope",
                },
                {
                    "action": "architecture",
                    "input": "design system structure and components",
                },
                {
                    "action": "design",
                    "input": "create detailed implementation plan",
                },
                {
                    "action": "implementation",
                    "input": "build core functionality",
                    "target_file": (
                        r"C:\Users\Owner\nova\nova_backend\sandbox\agent_target.py"
                    ),
                    "target_function": "placeholder_function",
                },
                {
                    "action": "integration",
                    "input": "connect components and services",
                },
                {
                    "action": "testing",
                    "input": "validate functionality and detect issues",
                    "target_file": (
                        r"C:\Users\Owner\nova\nova_backend\sandbox\agent_target.py"
                    ),
                },
                {
                    "action": "optimization",
                    "input": "improve quality, reliability, and performance",
                },
                {
                    "action": "delivery",
                    "input": "prepare final result and summarize work",
                },
            ]

        return [
            {
                "action": "respond",
                "input": "direct reply",
            },
        ]


    def _execute_tool(
        self,
        step: dict,
    ):

        action = step.get("action")
        input_data = step.get("input")

        if action == "analyze":
            return f"analyzed: {input_data}"

        if action == "diagnose":
            return f"diagnosed: {input_data}"

        if action == "fix":
            return f"fixed: {input_data}"

        if action == "validate":
            return f"validated: {input_data}"

        if action == "planning":
            return f"planned: {input_data}"

        if action == "architecture":
            return f"architected: {input_data}"

        if action == "design":
            return f"designed: {input_data}"

        if action == "implementation":
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

        goal = self._build_goal(user_text)

        if (
            isinstance(goal, dict)
            and str(goal.get("type") or "").strip().lower() == "general"
            and str(goal.get("goal") or "").strip().lower() == "respond normally"
        ):
            exec_debug(
                "BLOCKED GENERAL CHAT EXECUTION PLAN"
            )

            self._save_execution_state(
                session_id,
                {},
            )

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

                normalized_steps.append(
                    {
                        "id": f"step_{index}",
                        "title": title,
                        "action": action,
                        "input": input_value,
                        "target_file": step.get("target_file") or "",
                        "target_function": step.get("target_function") or "",
                        "content": step.get("content") or "",
                        "file_content": (
                            step.get("file_content")
                            or step.get("code")
                            or ""
                        ),
                        "code": step.get("code") or "",
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

        try:
            if hasattr(
                self,
                "chat_execution_service",
            ) and self.chat_execution_service:

                execution_state = (
                    self.chat_execution_service
                    .advance(
                        session_id
                    )
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
                        self.sessions.get_session(
                            session_id
                        )
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
                        "ADVANCED EXECUTION SAVE FAILED:",
                        e,
                    )

        except Exception as e:
            exec_debug(
                "EXECUTION AUTO ADVANCE FAILED:",
                e,
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