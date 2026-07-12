"""
NOVA LAUNCH REGRESSION

Official high-level Nova launch lockdown regression owner.

Runs the highest-value existing smoke/regression owners across
the major Nova product systems.

This runner does not replace subsystem smokes.
It proves the major launch-critical systems still pass together.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


LAUNCH_REGRESSIONS = [
    (
        "CORE",
        "nova_smoke_test.py",
    ),
    (
        "LIVE CHAT + ROUTING",
        "nova_regression_smoke.py",
    ),
    (
        "MEMORY",
        "nova_memory_quality_smoke.py",
    ),
    (
        "CONTINUITY",
        "nova_conversation_continuity_smoke.py",
    ),
    (
        "PROJECT STATE",
        "nova_project_state_smoke.py",
    ),
    (
        "PROJECT BRAIN",
        "nova_project_brain_context_builder_smoke.py",
    ),
    (
        "ATTACHMENTS",
        "nova_attachment_smoke_test.py",
    ),
    (
        "ATTACHMENT CONTRACT",
        "nova_attachment_response_contract_smoke.py",
    ),
    (
        "PLANNER",
        "nova_planner_integration_smoke.py",
    ),
    (
        "AUTONOMY LIFECYCLE",
        "nova_phase_4b_live_autonomy_lifecycle_smoke.py",
    ),
    (
        "AUTONOMY COMMAND STACK",
        "nova_phase_6d_high_value_smoke_bundle.py",
    ),
    (
        "MISSION OUTCOME HOOK",
        "nova_mission_completion_outcome_hook_smoke.py",
    ),
    (
        "SELF IMPROVEMENT LIFECYCLE",
        "nova_self_improvement_full_lifecycle_smoke.py",
    ),
    (
        "SELF IMPROVEMENT LIVE SIGNAL",
        "nova_self_improvement_live_new_problem_smoke.py",
    ),
    (
        "OPENAI KEY LOG SAFETY",
        "nova_openai_key_log_safety_smoke.py",
    ),
    (
        "SECRET LOG HYGIENE",
        "nova_secret_log_hygiene_smoke.py",
    ),
    (
        "DURABLE DATA",
        "nova_durable_data_bootstrap_smoke.py",
    ),
    (
        "RAILWAY DIRECTORY GUARD",
        "nova_ensure_dir_railway_guard_smoke.py",
    ),
]


def run_regression(
    category: str,
    filename: str,
) -> dict:

    path = TOOLS / filename

    result = {
        "category": category,
        "filename": filename,
        "passed": False,
        "returncode": None,
        "output": "",
    }

    if not path.exists():

        result["output"] = (
            f"Regression file does not exist: {path}"
        )

        return result

    environment = os.environ.copy()

    environment.setdefault(
        "NOVA_SKIP_LIVE_WEB_SMOKE",
        "1",
    )

    try:

        process = subprocess.run(
            [
                sys.executable,
                str(path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env=environment,
            timeout=180,
        )

    except subprocess.TimeoutExpired as exc:

        result["returncode"] = -1

        result["output"] = (
            f"TIMEOUT after {exc.timeout} seconds"
        )

        return result

    except Exception as exc:

        result["returncode"] = -1

        result["output"] = (
            f"{type(exc).__name__}: {exc}"
        )

        return result

    output_parts = []

    if process.stdout:

        output_parts.append(
            process.stdout.rstrip()
        )

    if process.stderr:

        output_parts.append(
            process.stderr.rstrip()
        )

    result["returncode"] = (
        process.returncode
    )

    result["output"] = "\n".join(
        output_parts
    )

    result["passed"] = (
        process.returncode == 0
    )

    return result


def print_failure(
    result: dict,
) -> None:

    print("")
    print("-" * 70)

    print(
        f"FAILED CATEGORY: "
        f"{result['category']}"
    )

    print(
        f"FAILED FILE: "
        f"{result['filename']}"
    )

    print(
        f"RETURN CODE: "
        f"{result['returncode']}"
    )

    print("")
    print("OUTPUT:")
    print("")

    output = (
        result.get("output")
        or "(no output)"
    )

    print(output)

    print("-" * 70)


def main() -> int:

    print(
        "NOVA LAUNCH REGRESSION"
    )

    print(
        "=" * 70
    )

    print("")

    print(
        "Official Nova launch lockdown gate"
    )

    print(
        f"Root: {ROOT}"
    )

    print(
        "Live web smoke: skipped by default"
    )

    print("")

    results = []

    total = len(
        LAUNCH_REGRESSIONS
    )

    for index, (
        category,
        filename,
    ) in enumerate(
        LAUNCH_REGRESSIONS,
        start=1,
    ):

        print(
            f"[{index:02d}/{total:02d}] "
            f"{category:<28} "
            f"{filename}"
        )

        result = run_regression(
            category,
            filename,
        )

        results.append(
            result
        )

        if result["passed"]:

            print(
                f"           PASS {category}"
            )

        else:

            print(
                f"           FAIL {category}"
            )

    passed = [
        result
        for result in results
        if result["passed"]
    ]

    failed = [
        result
        for result in results
        if not result["passed"]
    ]

    print("")
    print(
        "=" * 70
    )

    print(
        "NOVA LAUNCH REGRESSION SUMMARY"
    )

    print(
        "=" * 70
    )

    print("")

    print(
        f"TOTAL:  {len(results)}"
    )

    print(
        f"PASSED: {len(passed)}"
    )

    print(
        f"FAILED: {len(failed)}"
    )

    for result in failed:

        print_failure(
            result
        )

    print("")

    if failed:

        print(
            "NOVA LAUNCH LOCKDOWN: BLOCKED"
        )

        print("")

        print(
            "Fix launch regression failures "
            "before product polish."
        )

        return 1

    print(
        "NOVA LAUNCH LOCKDOWN: PASS"
    )

    print("")

    print(
        "NOVA LAUNCH REGRESSION PASSED"
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )