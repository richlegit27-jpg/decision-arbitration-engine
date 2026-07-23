from pathlib import Path
from tempfile import TemporaryDirectory

from nova_backend.services.execution_step_service import (
    ExecutionStepService,
)
from nova_backend.services.python_runner_service import (
    PythonRunnerService,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(
            f"{name} FAILED {detail}"
        )

    print(f"PASS {name}")


with TemporaryDirectory() as temporary_directory:
    root = Path(temporary_directory)
    sandbox = root / "sandbox"
    outside = root / "outside.py"

    runner = PythonRunnerService(
        sandbox_dir=sandbox,
    )

    inside_result = runner.run_code(
        'print("sandbox execution works")',
        filename="inside.py",
    )

    assert_true(
        "sandbox_python_executes",
        inside_result.get("ok") is True,
        inside_result,
    )

    traversal_result = runner.run_code(
        'print("should not be written")',
        filename="../escaped.py",
    )

    assert_true(
        "path_traversal_blocked",
        traversal_result.get("ok") is False,
        traversal_result,
    )

    assert_true(
        "escaped_file_not_created",
        not (root / "escaped.py").exists(),
    )

    outside.write_text(
        'print("outside")\n',
        encoding="utf-8",
    )

    outside_result = runner.run_file(
        outside
    )

    assert_true(
        "outside_python_execution_blocked",
        outside_result.get("ok") is False,
        outside_result,
    )

    text_file = sandbox / "notes.txt"
    text_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    text_file.write_text(
        "not python",
        encoding="utf-8",
    )

    non_python_result = runner.run_file(
        text_file
    )

    assert_true(
        "non_python_execution_blocked",
        non_python_result.get("ok") is False,
        non_python_result,
    )

    step_service = ExecutionStepService(
        python_runner=runner,
    )

    blocked_step = {
        "action": "implement",
        "target_file": str(
            root / "blocked_write.py"
        ),
    }

    step_service.execute_step_logic(
        session_id="safety-smoke",
        step=blocked_step,
    )

    assert_true(
        "outside_write_step_blocked",
        blocked_step.get("status") == "failed",
        blocked_step,
    )

    assert_true(
        "outside_write_not_created",
        not (root / "blocked_write.py").exists(),
    )

    allowed_target = sandbox / "generated.py"
    allowed_step = {
        "action": "implement",
        "target_file": str(allowed_target),
    }

    step_service.execute_step_logic(
        session_id="safety-smoke",
        step=allowed_step,
    )

    assert_true(
        "sandbox_write_step_allowed",
        allowed_step.get("status") == "completed",
        allowed_step,
    )

    assert_true(
        "sandbox_file_created",
        allowed_target.exists(),
    )


from nova_backend.services.execution_mutation_service import (
    ExecutionMutationService,
)
from nova_backend.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)


class FakeExecutionStateService:

    def __init__(self, state):
        self.state = state

    def get_execution_state(self, session_id):
        return self.state

    def save_execution_state(
        self,
        session_id,
        execution_state,
    ):
        self.state = execution_state
        return execution_state

    def save_active_execution(
        self,
        session_id,
        execution_state,
    ):
        self.state = execution_state
        return execution_state


class FailingStepService:

    def execute_step_logic(
        self,
        session_id,
        step,
    ):
        step["status"] = "failed"
        step["error"] = (
            "Execution blocked by safety policy."
        )
        return ""


def failed_execution_state(command):
    return {
        "command": command,
        "status": "running",
        "complete": False,
        "waiting": False,
        "current_index": 0,
        "steps": [
            {
                "title": "Unsafe step",
                "action": "implement",
                "status": "pending",
            }
        ],
    }


run_step_state = failed_execution_state(
    "run_step"
)
run_step_store = FakeExecutionStateService(
    run_step_state
)

run_step_orchestrator = ExecutionOrchestratorService(
    execution_state_service=run_step_store,
    working_state_service=None,
    execution_mutation_service=(
        ExecutionMutationService()
    ),
    safe_str=lambda value: str(value or ""),
    execution_step_service=FailingStepService(),
)

run_step_result = (
    run_step_orchestrator.process_execution(
        session_id="failed-run-step",
        state=run_step_state,
    )
)

assert_true(
    "orchestrator_failed_step_stays_failed",
    run_step_result.get("ok") is False,
    run_step_result,
)

assert_true(
    "orchestrator_failure_not_completed",
    (
        run_step_result.get("execution")
        or {}
    ).get("status") == "failed",
    run_step_result,
)

assert_true(
    "orchestrator_failure_does_not_advance",
    (
        run_step_result.get("execution")
        or {}
    ).get("current_index") == 0,
    run_step_result,
)

run_all_state = failed_execution_state(
    "run_all"
)
run_all_store = FakeExecutionStateService(
    run_all_state
)

run_all_orchestrator = ExecutionOrchestratorService(
    execution_state_service=run_all_store,
    working_state_service=None,
    execution_mutation_service=(
        ExecutionMutationService()
    ),
    safe_str=lambda value: str(value or ""),
    execution_step_service=FailingStepService(),
)

run_all_result = (
    run_all_orchestrator.process_execution(
        session_id="failed-run-all",
        state=run_all_state,
    )
)

assert_true(
    "run_all_stops_on_failed_step",
    run_all_result.get("ok") is False,
    run_all_result,
)

assert_true(
    "run_all_failure_not_completed",
    (
        run_all_result.get("execution")
        or {}
    ).get("status") == "failed",
    run_all_result,
)

class SuccessfulStepService:

    def execute_step_logic(
        self,
        session_id,
        step,
    ):
        step["status"] = "completed"
        step["result"] = (
            f"Finished {step.get('title')}"
        )
        step["error"] = None
        return step["result"]


successful_state = {
    "command": "run_all",
    "status": "running",
    "complete": False,
    "waiting": False,
    "current_index": 0,
    "steps": [
        {
            "title": "Safe step one",
            "action": "respond",
            "status": "pending",
        },
        {
            "title": "Safe step two",
            "action": "respond",
            "status": "pending",
        },
    ],
}

successful_store = FakeExecutionStateService(
    successful_state
)

successful_orchestrator = ExecutionOrchestratorService(
    execution_state_service=successful_store,
    working_state_service=None,
    execution_mutation_service=(
        ExecutionMutationService()
    ),
    safe_str=lambda value: str(value or ""),
    execution_step_service=SuccessfulStepService(),
)

successful_result = (
    successful_orchestrator.process_execution(
        session_id="successful-run-all",
        state=successful_state,
    )
)

assert_true(
    "run_all_success_completes",
    successful_result.get("ok") is True,
    successful_result,
)

assert_true(
    "run_all_success_marks_complete",
    (
        successful_result.get("execution")
        or {}
    ).get("complete") is True,
    successful_result,
)

assert_true(
    "run_all_success_advances_all_steps",
    (
        successful_result.get("execution")
        or {}
    ).get("current_index") == 2,
    successful_result,
)

print(
    "\nNOVA EXECUTION SANDBOX SMOKE PASSED"
)
