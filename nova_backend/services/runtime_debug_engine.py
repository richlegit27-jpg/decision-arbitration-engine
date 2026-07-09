from nova_backend.services.runtime_engine_base import RuntimeEngineBase


class RuntimeDebugEngine(RuntimeEngineBase):
    def __init__(self):
        super().__init__(
            name="runtime_debug_engine",
            tags=[
                "debug",
                "inspection",
                "runtime",
            ],
        )

    def execute(
        self,
        context=None,
    ):
        context = self._safe_dict(context)

        issues = self._safe_list(
            context.get("debug_issues")
        )

        if not issues:
            return {
                "ok": True,
                "action": "no_debug_action_required",
                "message": "No runtime debug issues detected.",
                "issues": [],
            }

        return {
            "ok": True,
            "action": "runtime_debug_review",
            "message": "Runtime debug issues detected.",
            "issues": issues,
            "issue_count": len(issues),
            "recommended_next": "route_to_repair_engine",
        }

