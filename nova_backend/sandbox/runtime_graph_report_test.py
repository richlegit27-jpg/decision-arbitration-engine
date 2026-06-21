from pprint import pprint

from nova_backend.services.safe_unified_runtime import (
    SafeUnifiedRuntime,
)


runtime = SafeUnifiedRuntime()

result = runtime.run_cycle(
    execution_state={
        "status": "running",
        "steps": [
            {
                "id": "1",
                "status": "completed",
            },
            {
                "id": "2",
                "status": "failed",
            },
        ],
    }
)

print("\n=== RUNTIME GRAPH REPORT ===\n")

pprint(
    result.get(
        "runtime_graph_report",
        {},
    )
)

