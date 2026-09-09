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

from nova_backend.core.execution_plan_normalizer import (
    ExecutionPlanNormalizer,
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

    print_section(
        "NOVA ENDGAME EXECUTION PIPELINE TEST"
    )

    try:

        session_id = (
            "endgame_execution_pipeline_test"
        )

        goal = (
            "Inspect the Nova project working directory, "
            "inspect the project tree, check git status, "
            "and inspect recent git history."
        )


        print_section(
            "BUILDING REAL NOVA RUNTIME"
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


        normalizer = (
            ExecutionPlanNormalizer()
        )


        print(
            "Runtime:",
            type(runtime).__name__,
        )

        print(
            "Executor:",
            type(executor).__name__,
        )

        print(
            "Step Service:",
            type(step_service).__name__,
        )

        print(
            "Execution Engine:",
            type(execution_engine).__name__,
        )

        print(
            "Execution Bridge:",
            type(execution_bridge).__name__,
        )

        print(
            "Plan Normalizer:",
            type(normalizer).__name__,
        )


        print_section(
            "RAW GOAL"
        )


        print(goal)


        project_path = str(
            BASE_DIR
        )


        raw_plan = {
            "goal": goal,
            "steps": [
                {
                    "title": (
                        "Determine the Nova working directory"
                    ),
                    "action": (
                        "working_directory"
                    ),
                    "tool_name": (
                        "working_directory"
                    ),
                },
                {
                    "title": (
                        "Inspect the Nova project tree"
                    ),
                    "action": (
                        "project_tree"
                    ),
                    "tool_name": (
                        "project_tree"
                    ),
                    "payload": {
                        "path": project_path,
                    },
                },
                {
                    "title": (
                        "Check the Nova git repository status"
                    ),
                    "action": (
                        "git_status"
                    ),
                    "tool_name": (
                        "git_status"
                    ),
                    "payload": {
                        "path": project_path,
                    },
                },
                {
                    "title": (
                        "Inspect recent Nova git history"
                    ),
                    "action": (
                        "git_log"
                    ),
                    "tool_name": (
                        "git_log"
                    ),
                    "payload": {
                        "path": project_path,
                    },
                },
            ],
        }


        print_section(
            "RAW PLAN"
        )


        print(raw_plan)


        print_section(
            "NORMALIZING PLAN"
        )


        plan = normalizer.normalize(
            raw_plan
        )


        print(plan)


        if not isinstance(
            plan,
            dict,
        ):

            raise RuntimeError(
                "Plan normalizer did not return a dict."
            )


        steps = (
            plan.get("steps")
            or []
        )


        if not steps:

            raise RuntimeError(
                "Normalized plan contains no steps."
            )


        print_section(
            "EXECUTING NORMALIZED PLAN"
        )


        result = (
            execution_bridge.execute(
                plan,
                session_id=session_id,
            )
        )


        print(result)


        print_section(
            "ENDGAME STEP RESULTS"
        )


        output = (
            result.get("output")
            or {}
        )


        execution_steps = (
            output.get("steps")
            or []
        )


        passed = 0


        for step in execution_steps:

            status = (
                step.get("status")
                or ""
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
            f"PASSED: "
            f"{passed}/{len(execution_steps)}"
        )


        print_section(
            "FINAL ENDGAME STATUS"
        )


        bridge_status = (
            result.get("status")
        )


        execution_status = (
            output.get("status")
        )


        error = (
            result.get("error")
            or output.get("error")
        )


        print(
            "BRIDGE STATUS:",
            bridge_status,
        )

        print(
            "EXECUTION STATUS:",
            execution_status,
        )

        print(
            "ERROR:",
            error,
        )


        all_steps_passed = (
            len(execution_steps) > 0
            and passed == len(execution_steps)
        )


        execution_passed = (
            execution_status
            in {
                "complete",
                "completed",
            }
        )


        if (
            all_steps_passed
            and execution_passed
            and not error
        ):

            print()

            print(
                "NOVA ENDGAME EXECUTION PIPELINE PASSED"
            )

        else:

            print()

            print(
                "NOVA ENDGAME EXECUTION PIPELINE FAILED"
            )


    except Exception as exc:

        print()

        print_section(
            "NOVA ENDGAME EXECUTION PIPELINE FAILED"
        )

        print(
            "ERROR:",
            str(exc),
        )

        traceback.print_exc()


if __name__ == "__main__":
    main()