from pprint import pprint

from nova_backend.services.safe_unified_runtime import (
    SafeUnifiedRuntime,
)

runtime = SafeUnifiedRuntime()

execution_state = {
    "status": "running",
    "steps": [
        {
            "id": 1,
            "title": "Repair runtime",
            "status": "failed",
        }
    ],
}

for i in range(5):

    result = runtime.run_cycle(
        execution_state=execution_state,
        world_state={
            "iteration": i,
        },
        scheduler_state={
            "active": True,
        },
    )

    print("\n=== CYCLE", i + 1, "===\n")

    pprint(
        {
            "cycle_count": result.get(
                "cycle_count"
            ),
            "final_action": result.get(
                "final_action"
            ),
            "reflection": result.get(
                "reflection"
            ),
            "graph_report": result.get(
                "runtime_graph_report"
            ),
            "memory_events": (
                result.get(
                    "runtime_graph_memory",
                    {},
                )
            ),
        }
    )