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

from nova_backend.services.execution_orchestrator_service import (
    ExecutionOrchestratorService,
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


def safe_str(
    value,
):

    if value is None:

        return ""

    return str(
        value
    )


def main():

    project_path = str(
        BASE_DIR
    )

    print_section(
        "NOVA ORCHESTRATOR UNIFIED BRIDGE TEST"
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
                safe_str=safe_str,
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

        orchestrator = (
            ExecutionOrchestratorService(
                safe_str=safe_str,
                execution_step_service=step_service,
                execution_bridge=execution_bridge,
            )
        )

        execution_state = {
            "goal": (
                "Inspect the Nova project using "
                "the orchestrator unified execution bridge."
            ),
            "steps": [
                {
                    "id": 1,
                    "title": (
                        "Determine working directory"
                    ),
                    "action": "working_directory",
                    "tool_name": "working_directory",
                    "status": "pending",
                    "payload": {},
                },
                {
                    "id": 2,
                    "title": (
                        "Inspect project tree"
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
                        "Check git status"
                    ),
                    "action": "git_status",
                    "tool_name": "git_status",
                    "status": "pending",
                    "payload": {
                        "path": project_path,
                    },
                },
            ],
            "status": "pending",
            "current_index": 0,
        }

        print_section(
            "INITIAL EXECUTION STATE"
        )

        print(
            execution_state
        )

        print_section(
            "RUNNING ORCHESTRATOR COMMAND"
        )

        result = (
            orchestrator._process_execution_command(
                command="run_all",
                session_id=(
                    "orchestrator_unified_bridge_test"
                ),
                execution_state=execution_state,
            )
        )

        print(
            result
        )

        print_section(
            "RESULT SUMMARY"
        )

        print(
            "OK:",
            result.get("ok"),
        )

        assistant_message = (
            result.get(
                "assistant_message"
            )
            or {}
        )

        print(
            "MESSAGE:",
            assistant_message.get(
                "text"
            ),
        )

        final_execution = (
            result.get(
                "execution"
            )
            or {}
        )

        print(
            "STATUS:",
            final_execution.get(
                "status"
            ),
        )

        print()

        steps = (
            final_execution.get(
                "steps"
            )
            or []
        )

        passed = 0

        for step in steps:

            status = safe_str(
                step.get(
                    "status"
                )
            ).lower()

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

        final_status = safe_str(
            final_execution.get(
                "status"
            )
        ).lower()

        if (
            result.get("ok")
            and passed == len(steps)
            and final_status in {
                "complete",
                "completed",
            }
        ):

            print(
                "ORCHESTRATOR UNIFIED BRIDGE TEST PASSED"
            )

        else:

            print(
                "ORCHESTRATOR UNIFIED BRIDGE TEST FAILED"
            )

    except Exception as exc:

        print()

        print(
            "ORCHESTRATOR UNIFIED BRIDGE TEST FAILED"
        )

        print(
            "ERROR:",
            str(exc),
        )

        traceback.print_exc()


if __name__ == "__main__":

    main()