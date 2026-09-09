from pathlib import Path
import traceback


BASE_DIR = Path(
    r"C:\Users\Owner\nova"
)


def print_section(
    title,
):

    print()

    print("=" * 70)

    print(title)

    print("=" * 70)


def check(
    name,
    value,
):

    status = (
        "PASS"
        if value
        else "FAIL"
    )

    print(
        f"{status:5} | {name}"
    )

    return bool(
        value
    )


def safe_str(
    value,
):

    if value is None:

        return ""

    return str(
        value
    )


def main():

    print_section(
        "NOVA REAL PRODUCTION EXECUTION STACK TEST"
    )

    try:

        print(
            "IMPORTING REAL APP..."
        )

        import app as nova_app

        chat_service = getattr(
            nova_app,
            "chat_service",
            None,
        )

        results = []

        print_section(
            "PHASE 1 - PRODUCTION STACK IDENTITY"
        )

        results.append(
            check(
                "chat_service exists",
                chat_service is not None,
            )
        )

        if chat_service is None:

            raise RuntimeError(
                "Production app has no chat_service"
            )

        orchestrator = getattr(
            chat_service,
            "execution_orchestrator_service",
            None,
        )

        bridge = getattr(
            chat_service,
            "execution_bridge",
            None,
        )

        engine = getattr(
            chat_service,
            "execution_engine",
            None,
        )

        step_service = getattr(
            chat_service,
            "execution_step_service",
            None,
        )

        tool_executor = getattr(
            chat_service,
            "tool_executor",
            None,
        )

        results.append(
            check(
                "orchestrator exists",
                orchestrator is not None,
            )
        )

        results.append(
            check(
                "bridge exists",
                bridge is not None,
            )
        )

        results.append(
            check(
                "engine exists",
                engine is not None,
            )
        )

        results.append(
            check(
                "step service exists",
                step_service is not None,
            )
        )

        results.append(
            check(
                "tool executor exists",
                tool_executor is not None,
            )
        )

        results.append(
            check(
                "orchestrator uses production bridge",
                getattr(
                    orchestrator,
                    "execution_bridge",
                    None,
                )
                is bridge,
            )
        )

        results.append(
            check(
                "bridge uses production engine",
                getattr(
                    bridge,
                    "execution_engine",
                    None,
                )
                is engine,
            )
        )

        results.append(
            check(
                "engine uses production step service",
                getattr(
                    engine,
                    "step_service",
                    None,
                )
                is step_service,
            )
        )

        results.append(
            check(
                "step service uses authoritative executor",
                getattr(
                    step_service,
                    "tool_executor",
                    None,
                )
                is tool_executor,
            )
        )

        results.append(
            check(
                "orchestrator uses production step service",
                getattr(
                    orchestrator,
                    "execution_step_service",
                    None,
                )
                is step_service,
            )
        )

        print_section(
            "PHASE 2 - REAL ORCHESTRATOR EXECUTION"
        )

        project_path = str(
            BASE_DIR
        )

        execution_state = {
            "goal": (
                "Inspect the Nova project using the "
                "real production execution pipeline."
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

        print(
            "EXECUTING REAL run_all..."
        )

        result = (
            orchestrator._process_execution_command(
                command="run_all",
                session_id=(
                    "real_production_execution_test"
                ),
                execution_state=execution_state,
            )
        )

        print_section(
            "EXECUTION RESULT"
        )

        print(
            "RESULT TYPE:",
            type(result).__name__,
        )

        if not isinstance(
            result,
            dict,
        ):

            raise RuntimeError(
                "Orchestrator returned non-dict result: "
                f"{type(result).__name__}"
            )

        print(
            "OK:",
            result.get("ok"),
        )

        final_execution = (
            result.get("execution")
            or {}
        )

        print(
            "EXECUTION STATUS:",
            final_execution.get("status"),
        )

        final_steps = (
            final_execution.get("steps")
            or []
        )

        print()

        passed_steps = 0

        for step in final_steps:

            if not isinstance(
                step,
                dict,
            ):

                continue

            status = safe_str(
                step.get("status")
            ).strip().lower()

            passed = status in {
                "complete",
                "completed",
                "done",
            }

            marker = (
                "PASS"
                if passed
                else "FAIL"
            )

            print(
                f"{marker:5} | "
                f"STEP {step.get('id')} | "
                f"{step.get('tool_name')} | "
                f"{status}"
            )

            if passed:

                passed_steps += 1

        total_steps = len(
            final_steps
        )

        results.append(
            check(
                "execution result ok",
                bool(
                    result.get("ok")
                ),
            )
        )

        results.append(
            check(
                "all execution steps returned",
                total_steps == 3,
            )
        )

        results.append(
            check(
                "all tools completed",
                passed_steps == 3,
            )
        )

        final_status = safe_str(
            final_execution.get("status")
        ).strip().lower()

        results.append(
            check(
                "execution reached terminal completion",
                final_status in {
                    "complete",
                    "completed",
                },
            )
        )

        print_section(
            "FINAL RESULT"
        )

        passed = sum(
            1
            for value in results
            if value
        )

        total = len(
            results
        )

        print(
            f"PASSED: {passed}/{total}"
        )

        if all(results):

            print()

            print(
                "REAL PRODUCTION EXECUTION "
                "PIPELINE PASSED"
            )

        else:

            print()

            print(
                "REAL PRODUCTION EXECUTION "
                "PIPELINE FAILED"
            )

    except Exception as exc:

        print_section(
            "TEST FAILED"
        )

        print(
            "ERROR:",
            str(exc),
        )

        traceback.print_exc()


if __name__ == "__main__":

    main()