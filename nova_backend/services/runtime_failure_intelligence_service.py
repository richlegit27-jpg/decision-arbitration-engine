class RuntimeFailureIntelligenceService:

    def __init__(self):

        self.failure_threshold = 3

    # =========================================
    # SAFE
    # =========================================

    def _safe_dict(self, value):

        return (
            value
            if isinstance(value, dict)
            else {}
        )

    # =========================================
    # ANALYZE
    # =========================================

    def analyze(
        self,
        runtime_brain,
    ):

        runtime_brain = self._safe_dict(
            runtime_brain
        )

        failures = self._safe_dict(
            runtime_brain.get(
                "recurring_failures"
            )
        )

        intelligence = {
            "high_risk_failures": [],
            "preventive_actions": [],
            "system_pressure": "normal",
        }

        for (
            failure_name,
            failure_data,
        ) in failures.items():

            if not isinstance(
                failure_data,
                dict,
            ):
                continue

            count = int(
                failure_data.get("count")
                or 0
            )

            if count < self.failure_threshold:
                continue

            intelligence[
                "high_risk_failures"
            ].append(
                failure_name
            )

            intelligence[
                "system_pressure"
            ] = "high"

            if "loop" in failure_name:

                intelligence[
                    "preventive_actions"
                ].append(
                    "increase_repair_bias"
                )

                intelligence[
                    "preventive_actions"
                ].append(
                    "increase_debug_bias"
                )

            if "timeout" in failure_name:

                intelligence[
                    "preventive_actions"
                ].append(
                    "reduce_parallelism"
                )

            if "memory" in failure_name:

                intelligence[
                    "preventive_actions"
                ].append(
                    "stabilize_context"
                )

        return intelligence

