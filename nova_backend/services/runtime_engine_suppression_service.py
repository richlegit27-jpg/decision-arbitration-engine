class RuntimeEngineSuppressionService:

    def __init__(self):

        self.failure_threshold = 3
        self.pressure_threshold = "high"

    def _safe_dict(self, value):

        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def _safe_list(self, value):

        return (
            value
            if isinstance(value, list)
            else []
        )

    def evaluate(
        self,
        engine_name,
        engine_state,
        runtime_failure_intelligence=None,
    ):

        engine_name = str(
            engine_name or ""
        ).strip()

        engine_state = self._safe_dict(
            engine_state
        )

        runtime_failure_intelligence = self._safe_dict(
            runtime_failure_intelligence
        )

        failure_count = int(
            engine_state.get("failure_count")
            or 0
        )

        system_pressure = str(
            runtime_failure_intelligence.get(
                "system_pressure"
            )
            or "normal"
        ).lower()

        high_risk_failures = self._safe_list(
            runtime_failure_intelligence.get(
                "high_risk_failures"
            )
        )

        if failure_count >= self.failure_threshold:

            return {
                "suppressed": True,
                "reason": "engine_failure_threshold_reached",
                "engine": engine_name,
            }

        if (
            system_pressure == self.pressure_threshold
            and "scheduler" in engine_name
        ):

            return {
                "suppressed": True,
                "reason": "scheduler_suppressed_under_high_pressure",
                "engine": engine_name,
            }

        if (
            system_pressure == self.pressure_threshold
            and high_risk_failures
            and "evolution" in engine_name
        ):

            return {
                "suppressed": True,
                "reason": "evolution_suppressed_during_instability",
                "engine": engine_name,
            }

        return {
            "suppressed": False,
            "reason": "",
            "engine": engine_name,
        }

