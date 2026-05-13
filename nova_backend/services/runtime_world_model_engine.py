from nova_backend.services.runtime_engine_base import (
    RuntimeEngineBase,
)


class RuntimeWorldModelEngine(
    RuntimeEngineBase
):
    def __init__(
        self,
    ):
        super().__init__(
            name="runtime_world_model_engine",
            tags=[
                "world_model",
                "state",
                "prediction",
                "runtime",
            ],
        )

    def execute(
        self,
        context=None,
    ):
        context = self._safe_dict(
            context
        )

        execution_status = self._safe_str(
            context.get(
                "execution_status"
            )
        ).lower()

        failed_count = context.get(
            "failed_count",
            0,
        )

        debug_issues = self._safe_list(
            context.get(
                "debug_issues"
            )
        )

        world_state = {
            "runtime_health": (
                "unstable"
                if failed_count > 0 or debug_issues
                else "stable"
            ),
            "execution_status": execution_status,
            "failure_pressure": failed_count,
            "debug_pressure": len(
                debug_issues
            ),
        }

        predictions = []

        if failed_count > 0:
            predictions.append(
                {
                    "prediction": (
                        "repair_required_before_autonomy"
                    ),
                    "confidence": 0.9,
                    "reason": (
                        "Failed execution steps indicate "
                        "runtime instability."
                    ),
                }
            )

        if debug_issues:
            predictions.append(
                {
                    "prediction": (
                        "debug_loop_likely"
                    ),
                    "confidence": 0.8,
                    "reason": (
                        "Debug issues are still present."
                    ),
                }
            )

        if execution_status in {
            "complete",
            "completed",
        }:
            predictions.append(
                {
                    "prediction": (
                        "next_goal_ready"
                    ),
                    "confidence": 0.75,
                    "reason": (
                        "Execution completed and runtime "
                        "can plan the next move."
                    ),
                }
            )

        if not predictions:
            predictions.append(
                {
                    "prediction": (
                        "runtime_idle_or_stable"
                    ),
                    "confidence": 0.6,
                    "reason": (
                        "No major instability detected."
                    ),
                }
            )

        return {
            "ok": True,
            "action": (
                "runtime_world_model_updated"
            ),
            "world_state": world_state,
            "predictions": predictions,
            "prediction_count": len(
                predictions
            ),
        }