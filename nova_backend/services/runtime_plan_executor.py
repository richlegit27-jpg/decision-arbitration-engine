class RuntimePlanExecutor:

    def execute(
        self,
        recursive_plan=None,
        runtime_signal=None,
    ):

        recursive_plan = (
            recursive_plan
            if isinstance(recursive_plan, dict)
            else {}
        )

        runtime_signal = str(
            runtime_signal
            or ""
        ).lower()

        steps = (
            recursive_plan.get(
                "steps",
                []
            )
            if isinstance(
                recursive_plan.get("steps"),
                list,
            )
            else []
        )

        executed_steps = []

        for step in steps:

            executed_steps.append(
                {
                    "step": step,
                    "status": "planned",
                }
            )

        action = "plan_ready"

        if runtime_signal in {
            "runtime_integrity_block",
            "runtime_rollback_executed",
            "runtime_escalation_required",
        }:

            action = "priority_execution_required"

        return {
            "ok": True,
            "action": action,
            "executed_steps": executed_steps,
            "step_count": len(executed_steps),
        }

