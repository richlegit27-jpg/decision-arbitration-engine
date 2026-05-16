class RuntimePredictionService:

    def __init__(
        self,
        graph_evolution=None,
    ):

        self.graph_evolution = (
            graph_evolution
        )

    def _safe_dict(self, value):

        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def predict_runtime_state(self):

        evolution = (
            self.graph_evolution.recommend_evolution()
            if self.graph_evolution
            else {}
        )

        evolution = self._safe_dict(
            evolution
        )

        success_rate = float(
            self._safe_dict(
                evolution.get("report")
            ).get(
                "success_rate",
                0,
            )
        )

        predicted_state = (
            "stable"
        )

        risk_forecast = (
            "low"
        )

        prediction_reason = (
            "Runtime graph indicates stable orchestration."
        )

        if success_rate < 0.40:

            predicted_state = (
                "unstable"
            )

            risk_forecast = (
                "high"
            )

            prediction_reason = (
                "Low runtime success rate detected."
            )

        elif success_rate < 0.70:

            predicted_state = (
                "adaptive"
            )

            risk_forecast = (
                "medium"
            )

            prediction_reason = (
                "Runtime entering adaptive stabilization phase."
            )

        return {
            "ok": True,
            "predicted_state": predicted_state,
            "risk_forecast": risk_forecast,
            "prediction_reason": prediction_reason,
            "success_rate": success_rate,
        }