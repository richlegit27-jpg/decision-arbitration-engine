class RuntimePolicyAdaptationService:
    def __init__(
        self,
        trend_analyzer=None,
    ):
        self.trend_analyzer = trend_analyzer

    def _safe_dict(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def adapt_policy(
        self,
    ):
        trend = {}

        if self.trend_analyzer and hasattr(
            self.trend_analyzer,
            "analyze",
        ):
            trend = self._safe_dict(
                self.trend_analyzer.analyze()
            )

        runtime_health = trend.get(
            "runtime_health",
            "unknown",
        )

        retry_actions = int(
            trend.get(
                "retry_actions",
                0,
            )
            or 0
        )

        throttled_cycles = int(
            trend.get(
                "throttled_cycles",
                0,
            )
            or 0
        )

        average_graph_score = float(
            trend.get(
                "average_graph_score",
                0.0,
            )
            or 0.0
        )

        policy = {
            "ok": True,
            "runtime_health": runtime_health,
            "allow_mutation": True,
            "allow_retry": True,
            "allow_evolution": True,
            "healing_aggressiveness": "normal",
            "retry_ceiling": 3,
            "mutation_threshold": 0.45,
            "reason": "default_policy",
        }

        if runtime_health == "unstable":
            policy.update(
                {
                    "allow_mutation": False,
                    "allow_retry": True,
                    "allow_evolution": False,
                    "healing_aggressiveness": "high",
                    "retry_ceiling": 2,
                    "mutation_threshold": 0.6,
                    "reason": "unstable_runtime_detected",
                }
            )

        elif runtime_health == "recovering":
            policy.update(
                {
                    "allow_mutation": True,
                    "allow_retry": True,
                    "allow_evolution": False,
                    "healing_aggressiveness": "moderate",
                    "retry_ceiling": 3,
                    "mutation_threshold": 0.5,
                    "reason": "runtime_recovering",
                }
            )

        elif runtime_health == "stable":
            policy.update(
                {
                    "allow_mutation": True,
                    "allow_retry": True,
                    "allow_evolution": True,
                    "healing_aggressiveness": "low",
                    "retry_ceiling": 5,
                    "mutation_threshold": 0.35,
                    "reason": "stable_runtime_detected",
                }
            )

        if retry_actions >= 8:
            policy["retry_ceiling"] = min(
                policy.get(
                    "retry_ceiling",
                    3,
                ),
                2,
            )
            policy["reason"] = (
                policy.get("reason")
                + "_retry_pressure"
            )

        if throttled_cycles >= 5:
            policy["allow_mutation"] = False
            policy["reason"] = (
                policy.get("reason")
                + "_throttle_pressure"
            )

        if average_graph_score < 0.4:
            policy["allow_evolution"] = False
            policy["healing_aggressiveness"] = "high"
            policy["reason"] = (
                policy.get("reason")
                + "_low_graph_confidence"
            )

        return {
            "ok": True,
            "trend": trend,
            "adaptive_policy": policy,
        }