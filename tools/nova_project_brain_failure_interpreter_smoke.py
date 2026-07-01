from nova_backend.services.project_brain_failure_interpreter import (
    build_project_brain_failure_interpreter_answer,
    interpret_project_brain_failure,
)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def run_case(name, pasted_output, expected_type, expected_terms):
    print("")
    print(f"CASE: {name}")

    result = interpret_project_brain_failure(
        user_text="diagnose this failure",
        pasted_output=pasted_output,
    )
    answer = build_project_brain_failure_interpreter_answer(
        user_text="diagnose this failure",
        pasted_output=pasted_output,
    )
    lower = answer.lower()

    print(answer)

    assert_true(f"{name} type", result.failure_type == expected_type, result)
    assert_true(f"{name} severity", bool(result.severity), result)
    assert_true(f"{name} likely source", bool(result.likely_source), result)
    assert_true(f"{name} patch target", bool(result.patch_target), result)
    assert_true(f"{name} next command", bool(result.next_command), result)
    assert_true(f"{name} avoid rules", bool(result.do_not_touch), result)
    assert_true(f"{name} formatted title", "project brain failure interpreter" in lower, answer)
    assert_true(f"{name} formatted type", "failure type:" in lower, answer)
    assert_true(f"{name} formatted next", "next command:" in lower, answer)

    for term in expected_terms:
        assert_true(
            f"{name} includes {term}",
            term.lower() in lower,
            answer,
        )


def main():
    print("NOVA PROJECT BRAIN FAILURE INTERPRETER SMOKE")
    print("============================================")

    run_case(
        name="server refused",
        pasted_output="NOVA REGRESSION SMOKE FAILED: Request failed for 'what should we work on next': <urlopen error [WinError 10061] No connection could be made because the target machine actively refused it>",
        expected_type="server_not_running",
        expected_terms=[
            "server_not_running",
            "python app.py",
            "runtime",
        ],
    )

    run_case(
        name="indentation error",
        pasted_output="Sorry: IndentationError: unexpected indent (nova_project_brain_freshness_snapshot_smoke.py, line 106)",
        expected_type="python_compile_error",
        expected_terms=[
            "python_compile_error",
            "py_compile",
            "nova_project_brain_freshness_snapshot_smoke.py",
        ],
    )

    run_case(
        name="answer quality missing signal",
        pasted_output="NOVA ANSWER QUALITY SMOKE FAILED\nnext move judgment freshness includes expected signals FAILED missing=['Mission Control v1.1']",
        expected_type="smoke_contract_mismatch",
        expected_terms=[
            "smoke_contract_mismatch",
            "Mission Control v1.1",
            "product answer",
            "smoke contract",
        ],
    )

    run_case(
        name="route mismatch",
        pasted_output="project_direct_recall_route FAILED expected project_state_current_memory_direct_recall got project_brain_general_intelligence",
        expected_type="route_contract_mismatch",
        expected_terms=[
            "route_contract_mismatch",
            "selector service",
            "app.py only if locator proves",
        ],
    )

    run_case(
        name="clean output",
        pasted_output="NOVA REGRESSION SMOKE PASSED\ngit status --short",
        expected_type="no_failure_detected",
        expected_terms=[
            "no_failure_detected",
            "git status --short",
        ],
    )

    print("")
    print("NOVA PROJECT BRAIN FAILURE INTERPRETER SMOKE PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
