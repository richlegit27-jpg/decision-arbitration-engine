from nova_backend.services.runtime_engine_base import (
    RuntimeEngineBase,
)


class RuntimePolicyEngine(RuntimeEngineBase):
    def __init__(self):
        super().__init__(
            name="runtime_policy_engine",
            tags=[
                "policy",
                "governor",
                "safety",
                "runtime",
            ],
        )

    def execute(self, context=None):
        context = self._safe_dict(context)

        failed_count = context.get("failed_count", 0)
        debug_issues = self._safe_list(
            context.get("debug_issues")
        )
        execution_status = self._safe_str(
            context.get("execution_status")
        ).lower()

        policy_updates = []

        if failed_count > 0:
            policy_updates.append(
                {
                    "policy": "increase_repair_priority",
                    "reason": "Runtime detected failed execution steps.",
                }
            )

        if debug_issues:
            policy_updates.append(
                {
                    "policy": "increase_debug_priority",
                    "reason": "Runtime debug issues detected.",
                    "issues": debug_issues,
                }
            )

        if execution_status in {"complete", "completed"}:
            policy_updates.append(
                {
                    "policy": "allow_next_goal_planning",
                    "reason": "Execution completed successfully.",
                }
            )

        if not policy_updates:
            policy_updates.append(
                {
                    "policy": "maintain_current_policy",
                    "reason": "No policy change required.",
                }
            )

        return {
            "ok": True,
            "action": "runtime_policy_review_completed",
            "policy_updates": policy_updates,
            "policy_update_count": len(policy_updates),
        }