class RuntimeTaskSynthesisService:
    def __init__(
        self,
    ):
        pass

    def _safe_dict(
        self,
        value,
    ):
        return value if isinstance(value, dict) else {}

    def _safe_list(
        self,
        value,
    ):
        return value if isinstance(value, list) else []

    def synthesize_tasks(
        self,
        execution_state=None,
        working_state=None,
        user_intent=None,
        failures=None,
        memory=None,
    ):
        execution_state = self._safe_dict(execution_state)
        working_state = self._safe_dict(working_state)
        failures = self._safe_list(failures)
        memory = self._safe_list(memory)

        goal = (
            execution_state.get("current_goal")
            or working_state.get("active_task")
            or working_state.get("next_move")
            or user_intent
            or "maintain_runtime_stability"
        )

        actions = []

        if goal and goal != "maintain_runtime_stability":
            actions.append(
                {
                    "action_type": "runtime_plan_goal",
                    "title": "Create executable plan from active goal",
                    "goal": goal,
                    "priority": "high",
                    "status": "queued",
                }
            )

        if failures:
            actions.append(
                {
                    "action_type": "runtime_repair_failure",
                    "title": "Analyze and repair active runtime failure",
                    "failure_count": len(failures),
                    "priority": "high",
                    "status": "queued",
                }
            )

        if working_state.get("current_file"):
            actions.append(
                {
                    "action_type": "runtime_inspect_file",
                    "title": "Inspect current working file",
                    "target_file": working_state.get("current_file"),
                    "priority": "medium",
                    "status": "queued",
                }
            )

        if not actions:
            actions.append(
                {
                    "action_type": "runtime_observe",
                    "title": "Observe runtime state and wait for stronger objective",
                    "goal": goal,
                    "priority": "low",
                    "status": "queued",
                }
            )

        return {
            "ok": True,
            "goal": goal,
            "runtime_execution_queue": actions,
            "active_plan": actions,
            "task_synthesis": {
                "generated": True,
                "action_count": len(actions),
                "source": "RuntimeTaskSynthesisService",
            },
        }