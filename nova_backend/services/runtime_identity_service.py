class RuntimeIdentityService:
    def __init__(self):
        self.identity_state = {
            "runtime_identity": "adaptive_runtime",
            "runtime_role": "general_execution",
            "risk_tolerance": "medium",
            "mutation_policy": "adaptive",
            "execution_temperament": "balanced",
            "identity_history": [],
        }

    def evolve_identity(
        self,
        trend=None,
        runtime_policy=None,
        runtime_governor=None,
    ):
        trend = self._safe_dict(trend)
        runtime_policy = self._safe_dict(
            runtime_policy
        )
        runtime_governor = self._safe_dict(
            runtime_governor
        )

        runtime_health = str(
            runtime_policy.get(
                "runtime_health",
                "",
            )
        ).lower()

        instability_ratio = self._safe_float(
            trend.get(
                "instability_ratio",
            ),
            0.0,
        )

        retry_actions = self._safe_int(
            trend.get(
                "retry_actions",
            ),
            0,
        )

        selected_engine = str(
            runtime_governor.get(
                "selected_engine",
                "",
            )
        ).lower()

        selected_action = str(
            runtime_governor.get(
                "selected_action",
                "",
            )
        ).lower()

        identity = "adaptive_runtime"
        role = "general_execution"
        risk = "medium"
        mutation_policy = "adaptive"
        temperament = "balanced"

        if (
            runtime_health == "unstable"
            or instability_ratio >= 0.70
        ):
            identity = "stabilization_runtime"
            role = "repair_oriented"
            risk = "low"
            mutation_policy = "restricted"
            temperament = "cautious"

        if selected_action == "cooldown_repair":
            identity = "cooldown_runtime"
            role = "stability_enforcement"
            risk = "minimal"
            mutation_policy = "blocked"
            temperament = "defensive"

        if (
            selected_engine == "strategy"
            and instability_ratio < 0.30
        ):
            identity = "exploration_runtime"
            role = "optimization_oriented"
            risk = "high"
            mutation_policy = "adaptive"
            temperament = "aggressive"

        if retry_actions >= 10:
            temperament = "fatigued"

        self.identity_state.update(
            {
                "runtime_identity": identity,
                "runtime_role": role,
                "risk_tolerance": risk,
                "mutation_policy": mutation_policy,
                "execution_temperament": temperament,
            }
        )

        self.identity_state[
            "identity_history"
        ].append(
            {
                "identity": identity,
                "role": role,
                "temperament": temperament,
            }
        )

        self.identity_state[
            "identity_history"
        ] = (
            self.identity_state[
                "identity_history"
            ][-25:]
        )

        return {
            "ok": True,
            "identity_state": (
                self.identity_state
            ),
        }

    def get_identity(
        self,
    ):
        return self.identity_state

    def _safe_dict(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def _safe_int(
        self,
        value,
        default=0,
    ):
        try:
            return int(value)
        except Exception:
            return default

    def _safe_float(
        self,
        value,
        default=0.0,
    ):
        try:
            return float(value)
        except Exception:
            return default

