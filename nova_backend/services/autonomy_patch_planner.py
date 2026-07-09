from __future__ import annotations

from typing import Dict, List


def _clean_goal(goal: str) -> str:
    return " ".join(str(goal or "").strip().split())


def _contains_any(text: str, needles: List[str]) -> bool:
    low = text.lower()
    return any(needle in low for needle in needles)


def _unique(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []

    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)

    return out


def _likely_files(goal: str) -> List[str]:
    low = goal.lower()
    files: List[str] = []

    if _contains_any(low, ["image", "images", "description", "caption", "generated image"]):
        files.extend(
            [
                "nova_backend/services/chat_service.py",
                "static/js/mobile/nova-mobile-images.js",
                "tools/nova_regression_smoke.py",
            ]
        )

    if _contains_any(low, ["memory", "recall", "project", "checkpoint", "context"]):
        files.extend(
            [
                "nova_backend/services/project_state_service.py",
                "tools/nova_memory_quality_smoke.py",
                "tools/nova_project_state_smoke.py",
                "tools/nova_project_context_smoke.py",
            ]
        )

    if _contains_any(low, ["session", "sessions", "switch", "rename"]):
        files.extend(
            [
                "static/js/mobile/nova-mobile-sessions.js",
                "tools/nova_regression_smoke.py",
            ]
        )

    if _contains_any(low, ["mobile", "button", "composer", "phone", "ui"]):
        files.extend(
            [
                "templates/mobile.html",
                "static/css/nova-mobile.css",
                "static/js/mobile/nova-mobile-ui-utils.js",
            ]
        )

    if _contains_any(low, ["attachment", "upload", "file summary", "summarize file"]):
        files.extend(
            [
                "static/js/mobile/nova-mobile-upload.js",
                "nova_backend/services/chat_service.py",
                "tools/nova_regression_smoke.py",
            ]
        )

    if _contains_any(low, ["autonomy", "planner", "plan", "task"]):
        files.extend(
            [
                "nova_backend/services/autonomy_task_brain.py",
                "nova_backend/services/autonomy_patch_planner.py",
                "tools/nova_autonomy_task_brain_smoke.py",
            ]
        )

    if not files:
        files.extend(
            [
                "nova_backend/services/chat_service.py",
                "tools/nova_regression_smoke.py",
            ]
        )

    return _unique(files)


def _patch_strategy(goal: str) -> List[str]:
    low = goal.lower()

    if _contains_any(low, ["image", "images", "description", "caption"]):
        return [
            "Do not change image generation routing first.",
            "Add or improve a response-polish helper only after confirming the existing image route still returns generated-image output.",
            "Cover the change with a smoke that proves image prompts do not fall into normal chat or web routing.",
        ]

    if _contains_any(low, ["memory", "recall", "project", "checkpoint", "context"]):
        return [
            "Do not rewrite memory ranking directly.",
            "Add a narrow formatter or guard first.",
            "Cover stale-checkpoint and project-context behavior with memory quality smoke.",
        ]

    if _contains_any(low, ["session", "sessions"]):
        return [
            "Do not replace the session controller wholesale.",
            "Patch one session behavior at a time: open, switch, rename, or restore.",
            "Run JS syntax checks and manually verify mobile switching after the patch.",
        ]

    if _contains_any(low, ["mobile", "button", "composer", "ui"]):
        return [
            "Avoid broad layout rewrites.",
            "Patch only the smallest CSS or one mobile JS owner file.",
            "Verify touch behavior on phone after compile checks.",
        ]

    if _contains_any(low, ["attachment", "upload", "file"]):
        return [
            "Do not touch image generation and upload routing in the same patch.",
            "Patch upload/summary behavior behind existing attachment guards.",
            "Verify upload, preview, and normal chat are not hijacked.",
        ]

    if _contains_any(low, ["autonomy", "planner", "task"]):
        return [
            "Keep autonomy proposal-only.",
            "Add planner capability as a separate service first.",
            "Wire chat command only after service smoke is green.",
        ]

    return [
        "Start with a tooling-only or route-level guarded patch.",
        "Avoid changing multiple subsystems at once.",
        "Add a smoke test before committing.",
    ]


def _risks(goal: str) -> List[str]:
    low = goal.lower()

    risks = [
        "A broad patch can break a previously locked route.",
        "A missing smoke can let regressions slip into mobile, memory, image, or execution behavior.",
    ]

    if _contains_any(low, ["image", "images"]):
        risks.append("Image prompts may be accidentally routed into normal chat, web fetch, or attachment handling.")

    if _contains_any(low, ["memory", "project", "checkpoint"]):
        risks.append("Project memory may show stale checkpoint text or noisy recall.")

    if _contains_any(low, ["session", "mobile", "ui"]):
        risks.append("Mobile behavior may pass backend smoke but still fail on phone touch flows.")

    if _contains_any(low, ["autonomy"]):
        risks.append("Autonomy features can become unsafe if they execute edits or commands before approval.")

    return risks


def _tests(goal: str) -> List[str]:
    low = goal.lower()

    tests = [
        "python .\\tools\\nova_regression_smoke.py",
        "python .\\tools\\nova_memory_quality_smoke.py",
    ]

    if _contains_any(low, ["image", "images"]):
        tests.extend(
            [
                "python .\\tools\\nova_project_compact_context_api_smoke.py",
            ]
        )

    if _contains_any(low, ["memory", "project", "checkpoint", "context"]):
        tests.extend(
            [
                "python .\\tools\\nova_project_state_smoke.py",
                "python .\\tools\\nova_project_context_smoke.py",
            ]
        )

    if _contains_any(low, ["mobile", "session", "sessions", "ui", "button"]):
        tests.extend(
            [
                "node --check .\\static\\js\\mobile\\nova-mobile-sessions.js",
                "node --check .\\static\\js\\mobile\\nova-mobile-ui-utils.js",
                "node --check .\\static\\js\\mobile\\nova-mobile-images.js",
            ]
        )

    if _contains_any(low, ["autonomy", "planner", "task"]):
        tests.extend(
            [
                "python .\\tools\\nova_autonomy_task_brain_smoke.py",
                "python .\\tools\\nova_autonomy_patch_planner_smoke.py",
            ]
        )

    return _unique(tests)


def create_autonomy_patch_plan(goal: str) -> Dict[str, object]:
    clean_goal = _clean_goal(goal) or "Improve Nova safely."

    return {
        "goal": clean_goal,
        "mode": "proposal_only",
        "likely_files": _likely_files(clean_goal),
        "risks": _risks(clean_goal),
        "patch_strategy": _patch_strategy(clean_goal),
        "tests": _tests(clean_goal),
        "commit_plan": [
            "Run compile checks for every changed Python or JS file.",
            "Run the smallest relevant smoke first.",
            "Run regression and memory quality smokes before commit.",
            "Commit with a narrow message describing exactly one subsystem.",
            "Sync data/nova_project_state.json only after the feature commit is locked.",
        ],
        "rollback_plan": [
            "Before commit: git restore <changed-file>",
            "After commit: git revert <commit>",
            "Emergency recovery: git reset --hard <stable-tag>",
        ],
        "next_step": "Create the smallest patch only after this plan is reviewed.",
    }


def format_autonomy_patch_plan(goal: str) -> str:
    plan = create_autonomy_patch_plan(goal)

    lines = [
        "Nova supervised patch proposal",
        "",
        f"Goal: {plan['goal']}",
        f"Mode: {plan['mode']}",
        "",
        "Likely files:",
    ]

    lines.extend(f"- {item}" for item in plan["likely_files"])

    lines.extend(["", "Risks:"])
    lines.extend(f"- {item}" for item in plan["risks"])

    lines.extend(["", "Smallest safe patch strategy:"])
    lines.extend(f"- {item}" for item in plan["patch_strategy"])

    lines.extend(["", "Tests:"])
    lines.extend(f"- {item}" for item in plan["tests"])

    lines.extend(["", "Commit plan:"])
    lines.extend(f"- {item}" for item in plan["commit_plan"])

    lines.extend(["", "Rollback plan:"])
    lines.extend(f"- {item}" for item in plan["rollback_plan"])

    lines.extend(["", f"Next step: {plan['next_step']}"])

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create a Nova supervised patch proposal.")
    parser.add_argument("goal", nargs="*", help="Goal to plan.")
    args = parser.parse_args()

    print(format_autonomy_patch_plan(" ".join(args.goal)))
