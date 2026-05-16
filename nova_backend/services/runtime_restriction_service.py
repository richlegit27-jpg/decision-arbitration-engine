class RuntimeRestrictionService:
    def enforce(
        self,
        execution_state=None,
        escalation_report=None,
        mutation_report=None,
        autonomy_report=None,
    ):
        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        escalation_report = (
            escalation_report
            if isinstance(escalation_report, dict)
            else {}
        )

        restrictions = escalation_report.get(
            "restrictions",
            [],
        )

        blocked = []

        if "block_mutation" in restrictions:
            execution_state["mutation_blocked"] = True
            blocked.append("mutation")

        if "throttle_execution" in restrictions:
            execution_state["execution_throttled"] = True
            blocked.append("execution_speed")

        if "suppress_exploration" in restrictions:
            execution_state["exploration_blocked"] = True
            blocked.append("exploration")

        if "force_checkpoint_only" in restrictions:
            execution_state["checkpoint_only_mode"] = True
            blocked.append("non_checkpoint_execution")

        return {
            "ok": True,
            "blocked_systems": blocked,
            "execution_state": execution_state,
        }