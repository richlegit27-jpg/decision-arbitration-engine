class RuntimePolicyArbitrationService:

    def __init__(self):

        self.blocked_modes = {
            "blocked",
        }

        self.restricted_risk_levels = {
            "high",
            "critical",
        }

    def _safe_dict(self, value):

        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def arbitrate(
        self,
        runtime_governor=None,
        runtime_failure_intelligence=None,
        runtime_brain=None,
    ):

        runtime_governor = self._safe_dict(
            runtime_governor
        )

        runtime_failure_intelligence = self._safe_dict(
            runtime_failure_intelligence
        )

        runtime_brain = self._safe_dict(
            runtime_brain
        )

        mode = str(
            runtime_governor.get("mode")
            or "normal"
        ).lower()

        risk_level = str(
            runtime_governor.get("risk_level")
            or "normal"
        ).lower()

        policy = {
            "decision": "allow",
            "allow_execution": True,
            "restrict_execution": False,
            "reason": "",
            "mode": mode,
            "risk_level": risk_level,
        }

        if mode in self.blocked_modes:

            policy["decision"] = "block"
            policy["allow_execution"] = False
            policy["reason"] = (
                "Runtime governor blocked execution."
            )

            return policy

        if risk_level in self.restricted_risk_levels:

            policy["decision"] = "restrict"
            policy["restrict_execution"] = True
            policy["reason"] = (
                "Runtime risk level requires restricted execution."
            )

            return policy

        return policy