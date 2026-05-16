class RuntimeConsensusService:
    def resolve(
        self,
        execution_state=None,
        runtime_result=None,
        integrity_report=None,
        rollback_report=None,
        prediction_report=None,
        runtime_governor=None,
        autonomy_report=None,
        mutation_report=None,
    ):
        execution_state = execution_state if isinstance(execution_state, dict) else {}
        integrity_report = integrity_report if isinstance(integrity_report, dict) else {}
        rollback_report = rollback_report if isinstance(rollback_report, dict) else {}
        prediction_report = prediction_report if isinstance(prediction_report, dict) else {}
        runtime_governor = runtime_governor if isinstance(runtime_governor, dict) else {}
        autonomy_report = autonomy_report if isinstance(autonomy_report, dict) else {}
        mutation_report = mutation_report if isinstance(mutation_report, dict) else {}

        signal = execution_state.get("runtime_signal") or "runtime_idle"

        authority = "normal_runtime"
        action = "continue"
        blocked = False
        reason = "Runtime consensus allowed normal continuation."

        if integrity_report.get("blocked"):
            authority = "runtime_integrity"
            action = "block_and_recover"
            blocked = True
            signal = "runtime_integrity_block"
            reason = "Integrity validation has highest authority and blocked unsafe runtime state."

        elif rollback_report.get("should_rollback"):
            authority = "runtime_rollback"
            action = "restore_checkpoint"
            blocked = True
            signal = "runtime_rollback_required"
            reason = "Rollback engine requested checkpoint restoration."

        elif prediction_report.get("risk_forecast") == "high":
            authority = "runtime_prediction"
            action = "throttle_execution"
            blocked = False
            signal = "runtime_high_risk_throttle"
            reason = "Prediction engine detected high runtime risk."

        elif runtime_governor.get("selected_action"):
            authority = "runtime_governor"
            action = runtime_governor.get("selected_action")
            blocked = False
            reason = "Governor selected the runtime action."

        elif autonomy_report.get("action"):
            authority = "runtime_autonomy"
            action = autonomy_report.get("action")
            blocked = False
            reason = "Autonomy loop selected the runtime action."

        execution_state["runtime_signal"] = signal
        execution_state["runtime_consensus_authority"] = authority
        execution_state["runtime_consensus_action"] = action
        execution_state["runtime_consensus_blocked"] = blocked
        execution_state["runtime_consensus_reason"] = reason

        return {
            "ok": True,
            "authority": authority,
            "action": action,
            "blocked": blocked,
            "runtime_signal": signal,
            "reason": reason,
            "execution_state": execution_state,
        }