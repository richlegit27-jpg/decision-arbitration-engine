class RuntimeConstitutionService:

    def evaluate(
        self,
        execution_state=None,
        integrity_report=None,
        rollback_report=None,
        escalation_report=None,
        consensus_report=None,
    ):
        execution_state = (
            execution_state
            if isinstance(execution_state, dict)
            else {}
        )

        integrity_report = (
            integrity_report
            if isinstance(integrity_report, dict)
            else {}
        )

        rollback_report = (
            rollback_report
            if isinstance(rollback_report, dict)
            else {}
        )

        escalation_report = (
            escalation_report
            if isinstance(escalation_report, dict)
            else {}
        )

        consensus_report = (
            consensus_report
            if isinstance(consensus_report, dict)
            else {}
        )

        authority_order = [
            "integrity",
            "rollback",
            "constitution",
            "consensus",
            "governor",
            "autonomy",
            "mutation",
        ]

        supreme_authority = "normal_runtime"
        veto_action = None

        if integrity_report.get("blocked"):
            supreme_authority = "integrity"
            veto_action = "block_execution"

        elif rollback_report.get("should_rollback"):
            supreme_authority = "rollback"
            veto_action = "restore_checkpoint"

        elif escalation_report.get(
            "escalation_level"
        ) == "lockdown":
            supreme_authority = "constitution"
            veto_action = "enter_lockdown"

        execution_state[
            "runtime_constitution"
        ] = {
            "authority_order": authority_order,
            "supreme_authority": supreme_authority,
            "veto_action": veto_action,
        }

        return {
            "ok": True,
            "authority_order": authority_order,
            "supreme_authority": supreme_authority,
            "veto_action": veto_action,
            "execution_state": execution_state,
        }

