class RuntimeEscalationService:
    def evaluate(
        self,
        execution_state=None,
        runtime_history=None,
        prediction_report=None,
        integrity_report=None,
    ):
        execution_state = execution_state if isinstance(execution_state, dict) else {}
        runtime_history = runtime_history if isinstance(runtime_history, list) else []
        prediction_report = prediction_report if isinstance(prediction_report, dict) else {}
        integrity_report = integrity_report if isinstance(integrity_report, dict) else {}

        failed_cycles = 0

        for item in runtime_history[-10:]:
            if not isinstance(item, dict):
                continue

            signal = str(
                item.get("runtime_signal") or ""
            ).lower()

            if (
                "repair" in signal
                or "rollback" in signal
                or "integrity" in signal
            ):
                failed_cycles += 1

        risk = prediction_report.get(
            "risk_forecast",
            "low",
        )

        escalation_level = "normal"
        restrictions = []

        if integrity_report.get("blocked"):
            escalation_level = "lockdown"

        elif failed_cycles >= 6:
            escalation_level = "survival"

        elif failed_cycles >= 4:
            escalation_level = "defensive"

        elif failed_cycles >= 2:
            escalation_level = "cautious"

        if risk == "high":
            restrictions.extend(
                [
                    "block_mutation",
                    "throttle_execution",
                ]
            )

        if escalation_level in {
            "defensive",
            "survival",
            "lockdown",
        }:
            restrictions.append(
                "suppress_exploration"
            )

        if escalation_level == "lockdown":
            restrictions.append(
                "force_checkpoint_only"
            )

        execution_state[
            "runtime_escalation_level"
        ] = escalation_level

        execution_state[
            "runtime_restrictions"
        ] = restrictions

        return {
            "ok": True,
            "escalation_level": escalation_level,
            "restrictions": restrictions,
            "failed_cycles": failed_cycles,
            "execution_state": execution_state,
        }

