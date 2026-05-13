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

    mutated = result.get(
        "mutated_execution_state",
        {},
    )

    graph_memory = mutated.get(
        "graph_memory",
        {},
    )

    print("\n=== ADAPTATION CYCLE", index, scenario["label"], "===\n")

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
            "healing_mode": mutated.get(
                "healing_mode"
            ),
            "healing_action_cooldown": mutated.get(
                "healing_action_cooldown"
            ),
            "runtime_signal": mutated.get(
                "runtime_signal"
            ),
            "runtime_route": mutated.get(
                "runtime_route"
            ),
            "runtime_stabilization_mode": mutated.get(
                "runtime_stabilization_mode"
            ),
            "runtime_cooldown_count": mutated.get(
                "runtime_cooldown_count"
            ),
            "runtime_cooldown_active": mutated.get(
                "runtime_cooldown_active"
            ),
            "runtime_action_rewritten": mutated.get(
                "runtime_action_rewritten"
            ),
            "runtime_policy_enforcement": result.get(
                "runtime_policy_enforcement"
            ),
            "runtime_route": mutated.get(
                "runtime_route"
            ),
            "runtime_stabilization_mode": mutated.get(
                "runtime_stabilization_mode"
            ),
            "runtime_cooldown_count": mutated.get(
                "runtime_cooldown_count"
            ),
            "runtime_cooldown_active": mutated.get(
                "runtime_cooldown_active"
            ),
            "runtime_action_rewritten": mutated.get(
                "runtime_action_rewritten"
            ),
            "graph_scores": graph_memory.get(
                "graph_scores"
            ),
            "graph_usage": graph_memory.get(
                "graph_usage"
            ),
            "runtime_graph_query": result.get(
                "runtime_graph_query"
            ),
            "runtime_graph_patterns": result.get(
                "runtime_graph_patterns"
            ),

            "runtime_trend_analysis": result.get(
                "runtime_trend_analysis"
            ),
            "runtime_adaptive_policy": result.get(
                "runtime_adaptive_policy"
            ),
            "runtime_adaptive_policy": result.get(
                "runtime_adaptive_policy"
            ),

            "runtime_governor": result.get(
                "runtime_governor"
            ),

            "memory_event_count": (
                result.get(
                    "runtime_graph_memory",
                    {},
                ).get(
                    "event_count"
                )
            ),
            "memory_event_count": (
                result.get(
                    "runtime_graph_memory",
                    {},
                ).get(
                    "event_count"
                )
            ),
        }
    )