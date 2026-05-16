class RuntimeWorldModelService:
    def __init__(self):
        self.world_state = {
            "prediction_history": [],
            "world_temperament": "neutral",
            "risk_forecast": "unknown",
        }

    def simulate(
        self,
        runtime_goal=None,
        runtime_identity=None,
        runtime_plan=None,
        trend=None,
    ):
        runtime_goal = self._safe_dict(
            runtime_goal
        )

        runtime_identity = self._safe_dict(
            runtime_identity
        )

        runtime_plan = self._safe_dict(
            runtime_plan
        )

        trend = self._safe_dict(trend)

        goal_state = self._safe_dict(
            runtime_goal.get("goal_state")
        )

        identity_state = self._safe_dict(
            runtime_identity.get(
                "identity_state"
            )
        )

        plan_state = self._safe_dict(
            runtime_plan.get("plan_state")
        )

        instability_ratio = (
            self._safe_float(
                trend.get(
                    "instability_ratio"
                ),
                0.0,
            )
        )

        runtime_identity_name = str(
            identity_state.get(
                "runtime_identity",
                ""
            )
        ).lower()

        active_plan = list(
            plan_state.get(
                "active_plan",
                []
            )
        )

        current_goal = str(
            goal_state.get(
                "current_goal",
                ""
            )
        ).lower()

        predicted_state = (
            "stable_execution"
        )

        risk_forecast = "low"

        prediction_reason = (
            "Runtime appears stable."
        )

        if instability_ratio >= 0.70:
            predicted_state = (
                "continued_instability"
            )

            risk_forecast = "high"

            prediction_reason = (
                "High instability ratio "
                "suggests continued runtime pressure."
            )

        if (
            "suppress_mutation"
            in active_plan
        ):
            prediction_reason += (
                " Mutation suppression "
                "may reduce volatility."
            )

        if (
            runtime_identity_name
            == "cooldown_runtime"
        ):
            predicted_state = (
                "controlled_repair_cycle"
            )

            risk_forecast = "medium"

        if (
            current_goal
            == "restore_safe_execution"
        ):
            predicted_state = (
                "gradual_stabilization"
            )

        prediction = {
            "predicted_state": (
                predicted_state
            ),
            "risk_forecast": (
                risk_forecast
            ),
            "prediction_reason": (
                prediction_reason
            ),
            "active_goal": (
                current_goal
            ),
        }

        self.world_state[
            "prediction_history"
        ].append(
            prediction
        )

        self.world_state[
            "prediction_history"
        ] = (
            self.world_state[
                "prediction_history"
            ][-25:]
        )

        self.world_state[
            "risk_forecast"
        ] = risk_forecast

        self.world_state[
            "world_temperament"
        ] = predicted_state

        return {
            "ok": True,
            "world_state": (
                self.world_state
            ),
            "prediction": prediction,
        }

    def get_world_state(
        self,
    ):
        return self.world_state

    def _safe_dict(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def _safe_float(
        self,
        value,
        default=0.0,
    ):
        try:
            return float(value)
        except Exception:
            return default