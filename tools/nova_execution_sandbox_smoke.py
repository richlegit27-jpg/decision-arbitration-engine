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


print(
    "\nNOVA EXECUTION SANDBOX SMOKE PASSED"
)
