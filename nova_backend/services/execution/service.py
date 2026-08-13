class ExecutionService:

    def __init__(self, chat_service):
        self.chat_service = chat_service


    def _build_goal(self, user_text: str):
        """
        Converts raw input into a structured goal.
        """

        text = (user_text or "").lower()

        if "fix" in text or "error" in text or "bug" in text:
            return {
                "type": "debug",
                "goal": "debug and fix issue",
            }

        if "build" in text or "create" in text:
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

    def _build_plan(self, goal_obj: dict):
        """
        Turns a goal into structured execution steps.
        """

        goal_type = str(goal_obj.get("type") or "").strip().lower()

        if goal_type == "debug":
            return [
                {"action": "analyze", "input": "find issue"},
                {"action": "fix", "input": "apply correction"},
                {"action": "validate", "input": "check result"},
            ]

        if goal_type == "analysis":
            return [
                {"action": "analyze", "input": "inspect input"},
                {"action": "summarize", "input": "generate insights"},
            ]

        if goal_type == "build":
            return [
                {
                    "action": "design",
                    "input": "create structure",
                },
                {
                    "action": "implement",
                    "input": "build core logic",
                    "target_file": r"C:\Users\Owner\nova\nova_backend\sandbox\agent_target.py",
                    "target_function": "placeholder_function",
                },
                {
                    "action": "test",
                    "input": "validate output",
                    "target_file": r"C:\Users\Owner\nova\nova_backend\sandbox\agent_target.py",
                },
            ]

        return [
            {"action": "respond", "input": "direct reply"},
        ]

    def _execute_tool(self, step: dict):
        action = step.get("action")
        input_data = step.get("input")

        if action == "analyze":
            return f"analyzed: {input_data}"

        if action == "fix":
            return f"fixed: {input_data}"

        if action == "validate":
            return f"validated: {input_data}"

        if action == "web_search":
            return f"web result for: {input_data}"

        if action == "design":
            return f"designed: {input_data}"

        if action == "implement":
            return f"implemented: {input_data}"

        if action == "test":
            return f"tested: {input_data}"

        if action == "respond":
            return f"response: {input_data}"

        return f"unknown action: {action}"

    def _build_execution(
        self,
        user_text: str,
        assistant_text: str,
        decision: dict | None,
    ) -> dict | None:
        if not self.chat_service._looks_like_execution(user_text, decision):
            return None

        goal = str(user_text or "").strip()
        step_titles = self.chat_service._execution_step_titles_for_goal(goal)
        now_iso = self.chat_service._iso_now()

        step_objs = []
        for i, title in enumerate(step_titles, start=1):
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
            "current_step": step_titles[0] if step_titles else "",
            "summary": str(assistant_text or "")[:200],
            "steps": step_objs,
            "started_at": locals().get("now_iso") or datetime.utcnow().isoformat(),
            "updated_at": now_iso,
        }

    def _execution_mark_running(
        self,
        execution: dict | None,
        step_index: int = 0,
    ) -> dict | None:
        if not isinstance(execution, dict):
            return execution

        steps = execution.get("steps")
        if not isinstance(steps, list) or not steps:
            execution["status"] = "running"
            execution["updated_at"] = self.chat_service._iso_now()
            return execution

        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            if idx < step_index and step.get("status") != "failed":
                step["status"] = "completed"
            elif idx == step_index:
                step["status"] = "running"
                execution["current_step"] = str(step.get("title") or "").strip()
            elif step.get("status") != "failed":
                step["status"] = "planned"

        execution["status"] = "running"
        execution["updated_at"] = self.chat_service._iso_now()
        return execution

    def _execution_mark_completed(
        self,
        execution: dict | None,
        assistant_text: str = "",
    ) -> dict | None:
        if not isinstance(execution, dict):
            return execution

        steps = execution.get("steps")

        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict) and step.get("status") != "failed":
                    step["status"] = "completed"

        execution["status"] = "completed"
        execution["current_step"] = ""
        execution["summary"] = str(assistant_text or execution.get("summary") or "")[
            :200
        ]
        execution["updated_at"] = self.chat_service._iso_now()

        return execution

    def _execution_mark_failed(
        self,
        execution: dict | None,
        error_text: str = "",
    ) -> dict | None:
        if not isinstance(execution, dict):
            return execution

        steps = execution.get("steps")

        failed_index = 0

        if isinstance(steps, list):
            for index, step in enumerate(steps):
                if isinstance(step, dict) and step.get("status") == "running":
                    failed_index = index
                    break

        execution = self.chat_service._mark_execution_failed(
            execution,
            step_index=failed_index,
            error=str(error_text or "Execution failed."),
        )

        execution["summary"] = str(error_text or execution.get("summary") or "")[:200]
        execution["updated_at"] = self.chat_service._iso_now()
        return execution
