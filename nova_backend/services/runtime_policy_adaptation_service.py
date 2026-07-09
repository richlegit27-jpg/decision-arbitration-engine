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

    def _safe_list(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, list)
            else []
        )

    def _summarize_governance_memory(
        self,
        governance_memory=None,
    ):
        governance_memory = self._safe_dict(
            governance_memory
        )

        top_memory = self._safe_list(
            governance_memory.get("top_memory")
        )

        total_importance = 0
        high_risk_count = 0

        for item in top_memory:

            if not isinstance(item, dict):
                continue

            importance_score = int(
                item.get(
                    "importance_score",
                    0,
                )
                or 0
            )

            total_importance += importance_score

            if importance_score >= 10:
                high_risk_count += 1

        return {
            "summary_count": int(
                governance_memory.get(
                    "summary_count",
                    0,
                )
                or 0
            ),
            "has_high_importance_memory": bool(
                governance_memory.get(
                    "has_high_importance_memory",
                    False,
                )
            ),
            "high_risk_count": high_risk_count,
            "total_importance": total_importance,
        }

    def _build_runtime_risk_pressure(
        self,
        execution_state=None,
    ):
        execution_state = self._safe_dict(
            execution_state
        )

        risk_memory_state = self._safe_dict(
            execution_state.get(
                "risk_memory_state"
            )
        )

        persistent_risk_score = int(
            execution_state.get(
                "persistent_risk_score",
                0,
            )
            or 0
        )

        persistent_recovery_pressure = int(
            execution_state.get(
                "persistent_recovery_pressure",
                0,
            )
            or 0
        )

        risk_level = str(
            risk_memory_state.get(
                "risk_level",
                "low",
            )
            or "low"
        ).lower()

        return {
            "persistent_risk_score": (
                persistent_risk_score
            ),
            "persistent_recovery_pressure": (
                persistent_recovery_pressure
            ),
            "risk_level": risk_level,
            "summary_count": int(
                risk_memory_state.get(
                    "summary_count",
                    0,
                )
                or 0
            ),
        }

    def adapt_policy(
        self,
        governance_memory=None,
        execution_state=None,
    ):
        trend = {}

        if self.trend_analyzer and hasattr(
            self.trend_analyzer,
            "analyze",
        ):
            trend = self._safe_dict(
                self.trend_analyzer.analyze()
            )

        governance_summary = (
            self._summarize_governance_memory(
                governance_memory=governance_memory,
            )
        )

        runtime_risk_pressure = (
            self._build_runtime_risk_pressure(
                execution_state=execution_state,
            )
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
            "governance_memory": governance_summary,
            "runtime_risk_pressure": (
                runtime_risk_pressure
            ),
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

        if governance_summary.get(
            "has_high_importance_memory"
        ):
            policy["allow_evolution"] = False

            policy["mutation_threshold"] = max(
                float(
                    policy.get(
                        "mutation_threshold",
                        0.45,
                    )
                    or 0.45
                ),
                0.6,
            )

            policy["retry_ceiling"] = min(
                int(
                    policy.get(
                        "retry_ceiling",
                        3,
                    )
                    or 3
                ),
                2,
            )

            policy["healing_aggressiveness"] = "high"

            policy["reason"] = (
                policy.get("reason")
                + "_governance_memory_pressure"
            )

        if governance_summary.get(
            "high_risk_count",
            0,
        ) >= 2:
            policy["allow_mutation"] = False
            policy["allow_evolution"] = False

            policy["reason"] = (
                policy.get("reason")
                + "_repeated_high_risk_memory"
            )

        persistent_risk_score = int(
            runtime_risk_pressure.get(
                "persistent_risk_score",
                0,
            )
            or 0
        )

        persistent_recovery_pressure = int(
            runtime_risk_pressure.get(
                "persistent_recovery_pressure",
                0,
            )
            or 0
        )

        risk_level = str(
            runtime_risk_pressure.get(
                "risk_level",
                "low",
            )
            or "low"
        ).lower()

        if persistent_risk_score >= 40:
            policy["allow_evolution"] = False
            policy["mutation_threshold"] = max(
                policy.get(
                    "mutation_threshold",
                    0.45,
                ),
                0.65,
            )

            policy["healing_aggressiveness"] = "high"

            policy["reason"] = (
                policy.get("reason")
                + "_persistent_risk_pressure"
            )

        if persistent_risk_score >= 80:
            policy["allow_mutation"] = False
            policy["retry_ceiling"] = 1

            policy["reason"] = (
                policy.get("reason")
                + "_critical_risk_memory"
            )

        if persistent_recovery_pressure >= 5:
            policy["allow_evolution"] = False

            policy["reason"] = (
                policy.get("reason")
                + "_recovery_pressure"
            )

        if risk_level == "high":
            policy["healing_aggressiveness"] = "maximum"
            policy["allow_mutation"] = False
            policy["allow_evolution"] = False

            policy["reason"] = (
                policy.get("reason")
                + "_high_risk_lockdown"
            )

        return {
            "ok": True,
            "trend": trend,
            "governance_summary": governance_summary,
            "runtime_risk_pressure": (
                runtime_risk_pressure
            ),
            "adaptive_policy": policy,
        }

