class RuntimeCollectiveIntelligence:

    name = "runtime_collective_intelligence"

    tags = [
        "runtime",
        "collective",
        "intelligence",
    ]

    def synthesize(
        self,
        mesh_report=None,
        runtime_signal=None,
    ):

        mesh_report = (
            mesh_report
            if isinstance(mesh_report, dict)
            else {}
        )

        runtime_signal = str(
            runtime_signal
            or ""
        ).lower()

        agents = (
            mesh_report.get(
                "agents",
                []
            )
            if isinstance(
                mesh_report.get(
                    "agents"
                ),
                list,
            )
            else []
        )

        consensus = []

        for agent in agents:

            consensus.append(
                {
                    "agent_id": (
                        agent.get(
                            "agent_id"
                        )
                    ),
                    "decision": (
                        "maintain_alignment"
                    ),
                    "status": (
                        "agreed"
                    ),
                }
            )

        intelligence_mode = (
            "consensus_alignment"
        )

        if runtime_signal in {
            "runtime_integrity_block",
            "runtime_escalation_required",
        }:

            intelligence_mode = (
                "recovery_consensus"
            )

        return {
            "ok": True,
            "intelligence_mode": (
                intelligence_mode
            ),
            "consensus_count": len(
                consensus
            ),
            "consensus": consensus,
        }

