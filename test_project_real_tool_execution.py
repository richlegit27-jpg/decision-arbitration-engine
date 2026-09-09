from pathlib import Path
import traceback

from nova_backend.services.session_service import (
    SessionService,
)

from nova_backend.services.tool_runtime_factory import (
    build_tool_runtime,
)

from nova_backend.services.execution_step_service import (
    ExecutionStepService,
)

from nova_backend.core.execution_engine import (
    ExecutionEngine,
)

from nova_backend.core.execution_bridge import (
    ExecutionBridge,
)


BASE_DIR = Path(
    r"C:\Users\Owner\nova"
)

SESSIONS_FILE = (
    BASE_DIR
    / "data"
    / "nova_sessions.json"
)


def print_section(
    title,
):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def main():

    project_path = str(
        BASE_DIR
    )

    print_section(
        "NOVA REAL PROJECT TOOL EXECUTION TEST"
    )

    try:

        session_service = (
            SessionService(
                SESSIONS_FILE
            )
        )

        runtime = (
            build_tool_runtime(
                session_service=session_service,
            )
        )

        executor = (
            runtime["tool_executor"]
        )

        step_service = (
            ExecutionStepService(
                tool_executor=executor,
            )
        )

        execution_engine = (
            ExecutionEngine(
                step_service=step_service,
            )
        )

        execution_bridge = (
            ExecutionBridge(
                execution_engine=execution_engine,
            )
        )

        plan = {
            "goal": (
                "Inspect the Nova project using "
                "real Nova tools."
            ),
            "steps": [
                {
                    "id": 1,
                    "title": (
                        "Determine the Nova working directory"
                    ),
                    "action": "working_directory",
                    "tool_name": "working_directory",
                    "status": "pending",
                    "payload": {},
                },
                {
                    "id": 2,
                    "title": (
                        "Inspect the Nova project tree"
                    ),
                    "action": "project_tree",
                    "tool_name": "project_tree",
                    "status": "pending",
                    "payload": {
                        "path": project_path,
                    },
                },
                {
                    "id": 3,
                    "title": (
                        "Check the Nova git repository status"
                    ),
                    "action": "git_status",
                    "tool_name": "git_status",
                    "status": "pending",
                    "payload": {
                        "path": project_path,
                    },
                },
                {
                    "id": 4,
                    "title": (
                        "Inspect recent Nova git history"
                    ),
                    "action": "git_log",
                    "tool_name": "git_log",
                    "status": "pending",
                    "payload": {
                        "path": project_path,
                    },
                },
            ],
            "status": "pending",
        }

        print_section(
            "PROJECT PLAN"
        )

        print(plan)

        print_section(
            "EXECUTING PROJECT"
        )

        result = (
            execution_bridge.execute(
                plan,
                "real_project_tool_test",
            )
        )

        print(result)

        print_section(
            "STEP RESULTS"
        )

        output = result.get(
            "output",
            {}
        )

        steps = output.get(
            "steps",
            []
        )

        passed = 0

        for step in steps:

            status = step.get(
                "status"
            )

            marker = (
                "PASS"
                if status in {
                    "complete",
                    "completed",
                }
                else "FAIL"
            )

            print(
                f"{marker:5} | "
                f"{step.get('id')} | "
                f"{step.get('tool_name')} | "
                f"{status}"
            )

            if marker == "PASS":
                passed += 1

        print()

        print(
            f"PASSED: {passed}/{len(steps)}"
        )

        print_section(
            "FINAL STATUS"
        )

        output_status = output.get(
            "status"
        )

        output_error = output.get(
            "error"
        )

        print(
            "BRIDGE STATUS:",
            result.get("status"),
        )

        print(
            "EXECUTION STATUS:",
            output_status,
        )

        print(
            "ERROR:",
            output_error,
        )

        print()

        if (
            passed == len(steps)
            and output_status == "complete"
        ):
            print(
                "REAL PROJECT TOOL EXECUTION TEST PASSED"
            )
        else:
            print(
                "REAL PROJECT TOOL EXECUTION TEST FAILED"
            )

    except Exception as exc:

        print()

        print(
            "REAL PROJECT TOOL EXECUTION TEST FAILED"
        )

        print(
            "ERROR:",
            str(exc),
        )

        traceback.print_exc()


if __name__ == "__main__":
    main()