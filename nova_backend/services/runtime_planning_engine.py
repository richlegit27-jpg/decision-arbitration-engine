from nova_backend.services.runtime_engine_base import RuntimeEngineBase


class RuntimePlanningEngine(RuntimeEngineBase):
    def __init__(self):
        super().__init__(
            name="runtime_planning_engine",
            tags=[
                "planning",
                "execution",
                "runtime",
            ],
        )

    def execute(
        self,
        context=None,
    ):
        context = self._safe_dict(context)

        execution_status = self._safe_str(
            context.get("execution_status")
        ).lower()

        final_action = self._safe_str(
            context.get("final_action")
        )

        if execution_status not in {
            "",
            "idle",
            "complete",
            "completed",
        }:
            return {
                "ok": True,
                "action": "planning_skipped",
                "message": "Execution is already active.",
                "execution_status": execution_status,
            }

        return {
            "ok": True,
            "action": "runtime_plan_recommended",
            "message": "Planning engine recommends preparing the next execution plan.",
            "execution_status": execution_status,
            "final_action": final_action,
            "recommended_next": "build_execution_plan",
        }