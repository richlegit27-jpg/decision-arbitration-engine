from __future__ import annotations

from nova_backend.services.runtime_bootstrap import RuntimeBootstrap


def test_safe_unified_runtime_boots() -> None:
    RuntimeBootstrap._runtime_instance = None

    runtime = RuntimeBootstrap.build()

    assert runtime is not None
    assert hasattr(runtime, "run_cycle")


def test_safe_unified_runtime_run_cycle_smoke() -> None:
    RuntimeBootstrap._runtime_instance = None

    runtime = RuntimeBootstrap.build()

    result = runtime.run_cycle(
        execution_state={
            "session_id": "pytest_runtime_smoke",
            "user_text": "smoke test runtime cycle",
        },
        world_state={},
        scheduler_state={},
        knowledge_graph={},
    )

    assert isinstance(result, dict)
    assert result


