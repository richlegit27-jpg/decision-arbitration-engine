class RuntimeSelfRepairPlannerService:
    def __init__(
        self,
    ):
        pass

    def _safe_dict(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def build_repair_plan(
        self,
        execution_state=None,
    ):
        execution_state = self._safe_dict(
            execution_state
        )

        runtime_signal = str(
            execution_state.get(
                "runtime_signal",
                ""
            )
            or ""
        ).lower()

        persistent_risk_score = int(
            execution_state.get(
                "persistent_risk_score",
                0,
            )
            or 0
        )

        retry_count = int(
            execution_state.get(
                "runtime_retry_count",
                0,
            )
            or 0
        )

        suppressed_strategy = str(
            execution_state.get(
                "runtime_suppressed_strategy",
                ""
            )
            or ""
        )

        repair_candidates = []

        if retry_count >= 2:
            repair_candidates.append(
                {
                    "action": "inspect_failed_step",
                    "priority": "high",
                    "reason": "Retry ceiling pressure detected.",
                    "safety_score": 9,
                }
            )

        if persistent_risk_score >= 100:
            repair_candidates.append(
                {
                    "action": "cooldown_repair",
                    "priority": "critical",
                    "reason": "Persistent runtime instability detected.",
                    "safety_score": 10,
                }
            )

        if "failure" in runtime_signal:
            repair_candidates.append(
                {
                    "action": "isolate_failure",
                    "priority": "high",
                    "reason": "Failure signal detected.",
                    "safety_score": 8,
                }
            )

        if (
            execution_state.get(
                "runtime_bridge_authorized"
            )
            and execution_state.get(
                "runtime_execute_now"
            )
        ):

            repair_candidates.append(
                {
                    "action": (
                        "reroute_execution"
                    ),
                    "priority": "high",
                    "reason": (
                        "Bridge override bypassed "
                        "repair suppression."
                    ),
                    "safety_score": 10,
                }
            )

        elif suppressed_strategy:

            repair_candidates.append(
                {
                    "action": "avoid_strategy",
                    "target": suppressed_strategy,
                    "priority": "medium",
                    "reason": (
                        "Suppressed strategy "
                        "should be avoided."
                    ),
                    "safety_score": 7,
                }
            )

        if not repair_candidates:
            repair_candidates.append(
                {
                    "action": "observe_runtime",
                    "priority": "low",
                    "reason": "No immediate repair pressure.",
                    "safety_score": 5,
                }
            )

        ranked_repairs = sorted(
            repair_candidates,
            key=lambda item: item.get(
                "safety_score",
                0,
            ),
            reverse=True,
        )

        selected_repair = ranked_repairs[0]

        execution_state[
            "runtime_repair_candidates"
        ] = ranked_repairs

        execution_state[
            "runtime_selected_repair"
        ] = selected_repair

        execution_state[
            "runtime_repair_mode"
        ] = (
            selected_repair.get(
                "action"
            )
        )

        return {
            "ok": True,
            "execution_state": execution_state,
            "repair_candidates": ranked_repairs,
            "selected_repair": selected_repair,
        }