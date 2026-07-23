from pathlib import Path
from tempfile import TemporaryDirectory

from nova_backend.services.execution_approval_service import (
    ExecutionApprovalService,
)
from nova_backend.services.execution_mutation_service import (
    ExecutionMutationService,
)
from nova_backend.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
)
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


def build_state(
    target_file,
    content,
):
    return {
        "command": "run_step",
        "status": "running",
        "complete": False,
        "waiting": False,
        "current_index": 0,
        "steps": [
            {
                "title": "Protected write",
                "action": "implement",
                "target_file": str(
                    target_file
                ),
                "content": content,
                "status": "pending",
                "requires_approval": True,
            }
        ],
    }


def build_orchestrator(
    state,
    sandbox,
):
    approval_service = (
        ExecutionApprovalService()
    )

    runner = PythonRunnerService(
        sandbox_dir=sandbox,
    )

    store = FakeExecutionStateService(
        state
    )

    orchestrator = (
        ExecutionOrchestratorService(
            execution_state_service=store,
            working_state_service=None,
            execution_mutation_service=(
                ExecutionMutationService()
            ),
            safe_str=lambda value: str(
                value or ""
            ),
            execution_step_service=(
                ExecutionStepService(
                    python_runner=runner,
                    approval_service=(
                        approval_service
                    ),
                )
            ),
            approval_service=approval_service,
        )
    )

    return orchestrator, store


with TemporaryDirectory() as temporary_directory:
    sandbox = (
        Path(temporary_directory)
        / "sandbox"
    )

    approved_target = (
        sandbox / "approved.py"
    )

    approved_state = build_state(
        approved_target,
        'print("approved execution")\n',
    )

    (
        approved_orchestrator,
        approved_store,
    ) = build_orchestrator(
        approved_state,
        sandbox,
    )

    waiting_result = (
        approved_orchestrator.process_execution(
            session_id="approval-control",
            state=approved_state,
            command="run_step",
        )
    )

    assert_true(
        "protected_step_waits",
        (
            waiting_result.get("execution")
            or {}
        ).get("status")
        == "waiting_approval",
        waiting_result,
    )

    assert_true(
        "protected_step_not_run_early",
        not approved_target.exists(),
    )

    approve_result = (
        approved_orchestrator.process_execution(
            session_id="approval-control",
            state=approved_store.state,
            command="approve",
        )
    )

    assert_true(
        "approve_command_executes",
        approve_result.get("ok") is True,
        approve_result,
    )

    assert_true(
        "approved_file_created",
        approved_target.exists(),
    )

    assert_true(
        "approved_content_preserved",
        approved_target.read_text(
            encoding="utf-8"
        )
        == 'print("approved execution")\n',
    )

    assert_true(
        "approved_execution_completes",
        (
            approve_result.get("execution")
            or {}
        ).get("complete")
        is True,
        approve_result,
    )

    assert_true(
        "approval_audit_preserved",
        (
            approve_result.get("execution")
            or {}
        ).get("approval_status")
        == "approved",
        approve_result,
    )

    denied_target = (
        sandbox / "denied.py"
    )

    denied_state = build_state(
        denied_target,
        'print("must not execute")\n',
    )

    (
        denied_orchestrator,
        denied_store,
    ) = build_orchestrator(
        denied_state,
        sandbox,
    )

    denied_waiting_result = (
        denied_orchestrator.process_execution(
            session_id="denial-control",
            state=denied_state,
            command="run_step",
        )
    )

    assert_true(
        "denied_step_first_waits",
        (
            denied_waiting_result.get(
                "execution"
            )
            or {}
        ).get("status")
        == "waiting_approval",
        denied_waiting_result,
    )

    deny_result = (
        denied_orchestrator.process_execution(
            session_id="denial-control",
            state=denied_store.state,
            command="deny",
        )
    )

    assert_true(
        "deny_command_returns",
        deny_result.get("ok") is True,
        deny_result,
    )

    assert_true(
        "denied_execution_cancelled",
        (
            deny_result.get("execution")
            or {}
        ).get("status")
        == "cancelled",
        deny_result,
    )

    assert_true(
        "denied_file_not_created",
        not denied_target.exists(),
    )

    assert_true(
        "denial_audit_preserved",
        (
            deny_result.get("execution")
            or {}
        ).get("approval_status")
        == "denied",
        deny_result,
    )


print(
    "\nNOVA EXECUTION APPROVAL CONTROL "
    "SMOKE PASSED"
)