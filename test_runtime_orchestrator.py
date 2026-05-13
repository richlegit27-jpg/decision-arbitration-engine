from nova_backend.services.runtime_orchestrator_service import (
    RuntimeOrchestratorService,
)


def main():
    orchestrator = RuntimeOrchestratorService()

    result_1 = orchestrator.orchestrate(
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

    result_2 = orchestrator.orchestrate(
        runtime_result={
            "ok": True,
            "cycle": 2,
            "final_action": "follow_fusion",
            "trace_id": "test-trace-002",
            "replay_id": "test-replay-002",
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

    print("OK =", result_2.get("ok"))
    print(
        "ENGINES =",
        list(
            orchestrator.get_engine_registry().keys()
        ),
    )
    print(
        "PLAN STEPS =",
        len(
            result_2.get("plan", {}).get(
                "steps",
                [],
            )
        ),
    )
    print(
        "REPORT RESULTS =",
        len(
            result_2.get("report", {}).get(
                "results",
                [],
            )
        ),
    )
    print(
        "HAS FUSION =",
        bool(
            result_2.get("fusion")
        ),
    )
    print(
        "LAST FUSION =",
        bool(
            orchestrator.get_last_fusion()
        ),
    )

    first_top = (
        result_1.get("plan", {})
        .get("selected_engines", [{}])[0]
        .get("name")
    )

    second_top = (
        result_2.get("plan", {})
        .get("selected_engines", [{}])[0]
        .get("name")
    )

    print(
        "FIRST TOP ENGINE =",
        first_top,
    )
    print(
        "SECOND TOP ENGINE =",
        second_top,
    )


if __name__ == "__main__":
    main()