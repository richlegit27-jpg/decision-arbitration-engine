class RuntimeCognitiveInjectionService:
    """
    Compresses runtime state into small cognition signals
    that chat/intelligence routing can safely consume.
    """

    def __init__(self):
        pass

    def build(
        self,
        runtime_summary=None,
        runtime_decision=None,
    ):

        runtime_summary = self._safe_dict(runtime_summary)
        runtime_decision = self._safe_dict(runtime_decision)

        compressed_runtime = self.compress_runtime_summary(
            runtime_summary
        )

        cycle_count = self._first_present(
            runtime_summary,
            [
                "cycle_count",
                "cycles",
                "cycle",
            ],
            0,
        )

        active_goal = self._first_present(
            compressed_runtime,
            [
                "runtime_goal",
            ],
            "",
        )

        predicted_state = self._first_present(
            compressed_runtime,
            [
                "runtime_prediction",
            ],
            "",
        )

        risk_forecast = self._first_present(
            compressed_runtime,
            [
                "runtime_risk",
            ],
            "",
        )

        last_action = self._first_present(
            compressed_runtime,
            [
                "runtime_action",
            ],
            "",
        )

        if not last_action:

            last_action = self._first_present(
                runtime_decision,
                [
                    "final_action",
                    "action",
                    "selected_action",
                ],
                "",
            )

        runtime_pressure = self._build_pressure(
            risk_forecast=risk_forecast,
            predicted_state=predicted_state,
        )

        recommendation = self._build_recommendation(
            risk_forecast=risk_forecast,
            predicted_state=predicted_state,
            last_action=last_action,
        )

        return {
            "runtime_active_goal": active_goal,
            "runtime_predicted_state": predicted_state,
            "runtime_risk": risk_forecast,
            "runtime_last_action": last_action,
            "runtime_cycle_count": cycle_count,
            "runtime_pressure": runtime_pressure,
            "runtime_recommendation": recommendation,
            "compressed_runtime": compressed_runtime,
            "has_runtime_cognition": bool(
                active_goal
                or predicted_state
                or risk_forecast
                or last_action
                or cycle_count
                or compressed_runtime.get("has_runtime_compression")
            ),
        }

    def compress_runtime_summary(
        self,
        runtime_summary=None,
    ):

        runtime_summary = self._safe_dict(runtime_summary)

        runtime_world_prediction = self._safe_dict(
            runtime_summary.get(
                "runtime_world_prediction"
            )
        )

        runtime_execution_router = self._safe_dict(
            runtime_summary.get(
                "runtime_execution_router"
            )
        )

        runtime_health = runtime_summary.get(
            "runtime_health",
            "",
        )

        runtime_route = runtime_summary.get(
            "runtime_route",
            "",
        )

        runtime_signal = runtime_summary.get(
            "runtime_signal",
            "",
        )

        stability_ratio = runtime_summary.get(
            "stability_ratio",
            0.0,
        )

        runtime_goal = runtime_world_prediction.get(
            "active_goal",
            "",
        )

        runtime_prediction = runtime_world_prediction.get(
            "predicted_state",
            "",
        )

        runtime_risk = runtime_world_prediction.get(
            "risk_forecast",
            "",
        )

        runtime_reason = runtime_world_prediction.get(
            "prediction_reason",
            "",
        )

        runtime_mode = runtime_execution_router.get(
            "autonomy_mode",
            "",
        )

        runtime_priority = runtime_execution_router.get(
            "priority",
            "",
        )

        runtime_execute_now = runtime_execution_router.get(
            "execute_now",
            False,
        )

        runtime_action = runtime_summary.get(
            "final_action",
            "",
        )

        if not runtime_action:

            runtime_action = runtime_summary.get(
                "runtime_final_action",
                "",
            )

        return {
            "runtime_health": runtime_health,
            "runtime_route": runtime_route,
            "runtime_signal": runtime_signal,
            "runtime_goal": runtime_goal,
            "runtime_prediction": runtime_prediction,
            "runtime_risk": runtime_risk,
            "runtime_reason": runtime_reason,
            "runtime_mode": runtime_mode,
            "runtime_priority": runtime_priority,
            "runtime_execute_now": runtime_execute_now,
            "runtime_action": runtime_action,
            "stability_ratio": stability_ratio,
            "has_runtime_compression": bool(
                runtime_health
                or runtime_route
                or runtime_signal
                or runtime_goal
                or runtime_prediction
                or runtime_risk
                or runtime_action
            ),
        }

    def _safe_dict(
        self,
        value,
    ):

        if isinstance(value, dict):
            return value

        return {}

    def _first_present(
        self,
        data,
        keys,
        default=None,
    ):

        data = self._safe_dict(data)

        for key in keys:

            value = data.get(key)

            if value not in (None, "", [], {}):
                return value

        return default

    def _build_pressure(
        self,
        risk_forecast="",
        predicted_state="",
    ):

        risk = str(risk_forecast or "").lower()
        predicted = str(predicted_state or "").lower()

        if risk in {"high", "critical"}:
            return "execution instability detected"

        if "unstable" in predicted:
            return "runtime instability detected"

        if "stabil" in predicted:
            return "runtime stabilization in progress"

        if risk == "low":
            return "minimal runtime pressure"

        if risk:
            return "runtime risk signal detected"

        return ""

    def _build_recommendation(
        self,
        risk_forecast="",
        predicted_state="",
        last_action="",
    ):

        risk = str(risk_forecast or "").lower()
        predicted = str(predicted_state or "").lower()
        action = str(last_action or "").lower()

        if risk in {"high", "critical"}:
            return "reduce concurrent execution load"

        if "pause" in action:
            return "hold execution until runtime stabilizes"

        if "stabil" in predicted:
            return "continue observing runtime state"

        if risk == "low":
            return "runtime is safe to observe"

        return ""