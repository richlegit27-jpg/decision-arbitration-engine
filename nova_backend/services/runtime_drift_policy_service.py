class RuntimeDriftPolicyService:

    def __init__(self):

        pass

    def _safe_dict(self, value):

        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def build_policy(
        self,
        drift_report=None,
    ):

        drift_report = self._safe_dict(
            drift_report
        )

        drift_state = str(
            drift_report.get(
                "drift_state",
                "",
            )
        ).lower()

        policy = {
            "ok": True,
            "drift_state": drift_state,
            "mode": "normal",
            "allow_autonomy": True,
            "force_stabilization": False,
            "repair_bias": 0,
            "debug_bias": 0,
            "planning_bias": 0,
        }

        if drift_state == "destabilizing":

            policy.update(
                {
                    "mode": "stabilization",
                    "allow_autonomy": False,
                    "force_stabilization": True,
                    "repair_bias": 25,
                    "debug_bias": 20,
                    "planning_bias": -10,
                }
            )

        elif drift_state == "transitioning":

            policy.update(
                {
                    "mode": "adaptive",
                    "allow_autonomy": True,
                    "force_stabilization": False,
                    "repair_bias": 10,
                    "debug_bias": 8,
                    "planning_bias": 5,
                }
            )

        return policy

