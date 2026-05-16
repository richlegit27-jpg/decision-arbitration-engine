class RuntimeAuthorityService:

    def resolve(
        self,
        execution_state=None,
        current_action=None,
        current_signal=None,
        constitution_report=None,
        escalation_report=None,
        integrity_report=None,
    ):
        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        supreme_authority = (
            constitution_report.get(
                "supreme_authority",
                "normal_runtime",
            )
            if isinstance(
                constitution_report,
                dict,
            )
            else "normal_runtime"
        )

        veto_action = (
            constitution_report.get(
                "veto_action"
            )
            if isinstance(
                constitution_report,
                dict,
            )
            else None
        )

        final_action = current_action
        final_signal = current_signal

        if veto_action == "block_execution":
            final_action = (
                "runtime_integrity_recovery"
            )

            final_signal = (
                "runtime_integrity_block"
            )

        elif veto_action == "restore_checkpoint":
            final_action = (
                "runtime_restore_checkpoint"
            )

            final_signal = (
                "runtime_rollback_executed"
            )

        elif veto_action == "enter_lockdown":
            final_action = (
                "runtime_lockdown"
            )

            final_signal = (
                "runtime_escalation_required"
            )

        execution_state[
            "runtime_signal"
        ] = final_signal

        execution_state[
            "runtime_final_action"
        ] = final_action

        execution_state[
            "runtime_supreme_authority"
        ] = supreme_authority

        return {
            "ok": True,
            "final_action": final_action,
            "final_signal": final_signal,
            "supreme_authority": supreme_authority,
            "execution_state": execution_state,
        }