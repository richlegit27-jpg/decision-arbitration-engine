from nova_backend.services.runtime_engine_base import RuntimeEngineBase


class RuntimeRepairEngine(RuntimeEngineBase):
    def __init__(self):
        super().__init__(
            name="runtime_repair_engine",
            tags=[
                "repair",
                "healing",
                "runtime",
            ],
        )

    def execute(
        self,
        context=None,
    ):
        context = self._safe_dict(context)

        failed_count = context.get(
            "failed_count",
            0,
        )

        debug_issues = self._safe_list(
            context.get("debug_issues")
        )

        repairs = []

        if failed_count > 0:
            repairs.append(
                {
                    "type": "execution_failure_repair",
                    "action": "inspect_failed_steps",
                    "reason": "Execution failure count detected.",
                }
            )

        if debug_issues:
            repairs.append(
                {
                    "type": "debug_issue_repair",
                    "action": "apply_runtime_debug_repair",
                    "reason": "Runtime debug issues detected.",
                    "issues": debug_issues,
                }
            )

        if not repairs:
            return {
                "ok": True,
                "action": "no_repair_required",
                "message": "Runtime repair engine found nothing to repair.",
                "repairs": [],
            }

        return {
            "ok": True,
            "action": "runtime_repair_plan_created",
            "message": "Runtime repair actions prepared.",
            "repairs": repairs,
            "repair_count": len(repairs),
        }

