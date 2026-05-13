class RuntimeGovernorService:

    def __init__(self):

        self.high_pressure_modes = {
            "high",
            "critical",
            "danger",
        }

    def _safe_dict(self, value):

        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def govern(
        self,
        runtime_failure_intelligence=None,
        selected_engines=None,
        runtime_brain=None,
    ):

        runtime_failure_intelligence = (
            self._safe_dict(
                runtime_failure_intelligence
            )
        )

        runtime_brain = self._safe_dict(
            runtime_brain
        )

        selected_engines = (
            selected_engines
            if isinstance(
                selected_engines,
                list,
            )
            else []
        )

        system_pressure = str(
            runtime_failure_intelligence.get(
                "system_pressure"
            )
            or "normal"
        ).lower()

        governor = {
            "mode": "normal",
            "allow_execution": True,
            "force_repair": False,
            "force_debug": False,
            "risk_level": "normal",
            "reason": "",
            "selected_count": len(
                selected_engines
            ),
        }

        if (
            system_pressure
            in self.high_pressure_modes
        ):

            governor["mode"] = (
                "stabilization"
            )

            governor["risk_level"] = (
                "high"
            )

            governor["force_repair"] = True

            governor["force_debug"] = True

            governor["reason"] = (
                "High runtime pressure detected."
            )

        if not selected_engines:

            governor["mode"] = (
                "blocked"
            )

            governor[
                "allow_execution"
            ] = False

            governor["risk_level"] = (
                "high"
            )

            governor["reason"] = (
                "No engines available after suppression."
            )

        return governor