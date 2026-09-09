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


BASE_DIR = Path(
    r"C:\Users\Owner\nova"
)

SESSIONS_FILE = (
    BASE_DIR
    / "data"
    / "nova_sessions.json"
)


def print_header(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def run_test(
    step_service,
    name,
    step,
):
    print_header(
        f"TEST: {name}"
    )

    try:
        result = (
            step_service.execute_step_logic(
                session_id="tool_matrix",
                step=step,
            )
        )

        status = result.get(
            "status"
        )

        error = result.get(
            "error"
        )

        tool_result = result.get(
            "result"
        )

        success = (
            status == "completed"
            and not error
        )

        print(
            "STATUS:",
            status,
        )

        print(
            "SUCCESS:",
            success,
        )

        if error:
            print(
                "ERROR:",
                error,
            )

        print(
            "RESULT:",
            tool_result,
        )

        return {
            "name": name,
            "success": success,
            "status": status,
            "error": error,
        }

    except Exception as exc:
        print(
            "EXCEPTION:",
            str(exc),
        )

        traceback.print_exc()

        return {
            "name": name,
            "success": False,
            "status": "exception",
            "error": str(exc),
        }


def main():

    print_header(
        "NOVA TOOL EXECUTION MATRIX"
    )

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

    tests = [

        (
            "working_directory",
            {
                "action": "working_directory",
                "tool_name": "working_directory",
                "status": "pending",
            },
        ),

        (
            "file_exists",
            {
                "action": "file_exists",
                "tool_name": "file_exists",
                "status": "pending",
                "payload": {
                    "path": str(
                        BASE_DIR
                    ),
                },
            },
        ),

        (
            "file_list",
            {
                "action": "file_list",
                "tool_name": "file_list",
                "status": "pending",
                "payload": {
                    "path": str(
                        BASE_DIR
                    ),
                },
            },
        ),

        (
            "directory_list",
            {
                "action": "directory_list",
                "tool_name": "directory_list",
                "status": "pending",
                "payload": {
                    "path": str(
                        BASE_DIR
                    ),
                },
            },
        ),

        (
            "project_tree",
            {
                "action": "project_tree",
                "tool_name": "project_tree",
                "status": "pending",
                "payload": {},
            },
        ),

        (
            "git_status",
            {
                "action": "git_status",
                "tool_name": "git_status",
                "status": "pending",
                "payload": {},
            },
        ),

        (
            "git_log",
            {
                "action": "git_log",
                "tool_name": "git_log",
                "status": "pending",
                "payload": {},
            },
        ),

        (
            "python_compile",
            {
                "action": "python_compile",
                "tool_name": "python_compile",
                "status": "pending",
                "payload": {
                    "path": (
                        "nova_backend/core/"
                        "execution_engine.py"
                    ),
                },
            },
        ),

        (
            "process_list",
            {
                "action": "process_list",
                "tool_name": "process_list",
                "status": "pending",
                "payload": {},
            },
        ),

        (
            "port_check",
            {
                "action": "port_check",
                "tool_name": "port_check",
                "status": "pending",
                "payload": {
                    "port": 8000,
                },
            },
        ),

        (
            "environment_get",
            {
                "action": "environment_get",
                "tool_name": "environment_get",
                "status": "pending",
                "payload": {},
            },
        ),

        (
            "disk_usage",
            {
                "action": "disk_usage",
                "tool_name": "disk_usage",
                "status": "pending",
                "payload": {
                    "path": str(
                        BASE_DIR
                    ),
                },
            },
        ),
    ]

    results = []

    for (
        name,
        step,
    ) in tests:

        result = run_test(
            step_service,
            name,
            step,
        )

        results.append(
            result
        )

    print_header(
        "FINAL MATRIX RESULTS"
    )

    passed = 0

    for result in results:

        marker = (
            "PASS"
            if result["success"]
            else "FAIL"
        )

        print(
            f"{marker:5} | "
            f"{result['name']}"
        )

        if result["success"]:
            passed += 1

    print()

    print(
        f"PASSED: {passed}/{len(results)}"
    )

    failed = (
        len(results)
        - passed
    )

    print(
        f"FAILED: {failed}/{len(results)}"
    )


if __name__ == "__main__":
    main()