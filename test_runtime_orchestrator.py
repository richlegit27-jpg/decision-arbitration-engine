from nova_backend.services.runtime_orchestrator_service import RuntimeOrchestratorService


def main():
    orchestrator = RuntimeOrchestratorService()

    result = orchestrator.orchestrate(
        runtime_result={
            "ok": True,
            "cycle": 1,
            "final_action": "inspect_runtime",
            "trace_id": "test-trace-001",
            "replay_id": "test-replay-001",
            "execution": {
                "status": "failed",
                "failed_count": 1,
            },
        },
        execution_state={
            "status": "failed",
        },
        debug_report={
            "ok": False,
            "issues": [
                "test_runtime_issue",
            ],
        },
        healing_report={
            "applied": [
                "test_healing_action",
            ],
        },
    )

    print("OK =", result.get("ok"))
    print("ENGINES =", list(orchestrator.get_engine_registry().keys()))
    print("PLAN STEPS =", len(result.get("plan", {}).get("steps", [])))
    print("REPORT RESULTS =", len(result.get("report", {}).get("results", [])))


if __name__ == "__main__":
    main()