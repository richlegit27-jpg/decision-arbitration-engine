class RuntimeOutputCompressionService:

    def _safe_dict(self, value):

        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def compress_cycle_result(
        self,
        result=None,
    ):

        result = self._safe_dict(result)

        policy_enforcement = self._safe_dict(
            result.get("runtime_policy_enforcement")
        )

        execution_state = self._safe_dict(
            policy_enforcement.get("execution_state")
        )

        world_model = self._safe_dict(
            execution_state.get("runtime_world_model")
        )

        trend = self._safe_dict(
            result.get("runtime_trend_analysis")
        )

        return {
            "ok": result.get("ok", True),
            "cycle_count": result.get("cycle_count"),
            "final_action": result.get("final_action"),
            "runtime_route": result.get("runtime_route"),
            "runtime_signal": result.get("runtime_signal"),
            "healing_mode": result.get("healing_mode"),
            "runtime_health": trend.get("runtime_health"),
            "stability_ratio": trend.get("stability_ratio"),
            "runtime_world_prediction": world_model.get("prediction"),
        }