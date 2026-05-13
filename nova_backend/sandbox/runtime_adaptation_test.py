from pprint import pprint

from nova_backend.services.safe_unified_runtime import (
    SafeUnifiedRuntime,
)


runtime = SafeUnifiedRuntime()


scenarios = [
    {
        "label": "failure_cycle_1",
        "execution_state": {
            "status": "running",
            "steps": [
                {
                    "id": 1,
                    "title": "Repair runtime",
                    "status": "failed",
                }
            ],
        },
    },
    {
        "label": "failure_cycle_2",
        "execution_state": {
            "status": "running",
            "steps": [
                {
                    "id": 1,
                    "title": "Repair runtime",
                    "status": "failed",
                }
            ],
        },
    },
    {
        "label": "partial_recovery",
        "execution_state": {
            "status": "running",
            "steps": [
                {
                    "id": 1,
                    "title": "Repair runtime",
                    "status": "completed",
                },
                {
                    "id": 2,
                    "title": "Verify runtime",
                    "status": "failed",
                },
            ],
        },
    },
    {
        "label": "stabilized_success",
        "execution_state": {
            "status": "completed",
            "complete": True,
            "steps": [
                {
                    "id": 1,
                    "title": "Repair runtime",
                    "status": "completed",
                },
                {
                    "id": 2,
                    "title": "Verify runtime",
                    "status": "completed",
                },
            ],
        },
    },
]


for index, scenario in enumerate(scenarios, start=1):

    result = runtime.run_cycle(
        execution_state=scenario["execution_state"],
        world_state={
            "scenario": scenario["label"],
            "iteration": index,
        },
        scheduler_state={
            "active": True,
        },
    )

    print(
        "\n=== ADAPTATION CYCLE",
        index,
        scenario["label"],
        "===\n",
    )

    pprint(
        result.get(
            "compressed_runtime",
            result,
        )
    )