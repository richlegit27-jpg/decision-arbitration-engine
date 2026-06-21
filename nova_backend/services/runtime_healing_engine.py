from nova_backend.services.runtime_engine_base import RuntimeEngineBase


class RuntimeHealingEngine(RuntimeEngineBase):
    def __init__(self):
        super().__init__(
            name="runtime_healing_engine",
            tags=[
                "healing",
                "stability",
                "runtime",
            ],
        )

    def execute(
        self,
        context=None,
    ):
        context = self._safe_dict(context)

        debug_issues = self._safe_list(
            context.get("debug_issues")
        )

        healing_applied = self._safe_list(
            context.get("healing_applied")
        )

        if not debug_issues and not healing_applied:
            return {
                "ok": True,
                "action": "no_healing_required",
                "message": "Runtime healing engine found no instability.",
                "healing_required": False,
            }

        return {
            "ok": True,
            "action": "runtime_healing_review",
            "message": "Runtime healing review completed.",
            "healing_required": bool(debug_issues),
            "debug_issues": debug_issues,
            "healing_applied": healing_applied,
            "recommended_next": "verify_runtime_stability",
        }

