from __future__ import annotations

from pathlib import Path
from typing import Dict, List


EXPECTED_LOCKED_ROUTES = [
    "autonomy_command",
    "autonomy_plan_command",
    "patch_build_command",
    "repair_plan_command",
    "repair_build_command",
    "workflow_catalog_command",
    "autonomy_index_command",
    "command_registry_command",
]


EXPECTED_LOCKED_MODES = [
    "task_brief",
    "patch_proposal_only",
    "instructions_only",
    "repair_proposal_only",
    "repair_instructions_only",
    "manual_workflow_catalog_only",
    "autonomy_ladder_index_only",
    "read_only_command_registry",
]


EXPECTED_GUARD_MARKERS = [
    "NOVA_AUTONOMY_PLAN_COMMAND",
    "NOVA_PATCH_BUILD_COMMAND",
    "NOVA_REPAIR_PLAN_COMMAND",
    "NOVA_REPAIR_BUILD_COMMAND",
    "NOVA_WORKFLOW_CATALOG_COMMAND",
    "NOVA_AUTONOMY_INDEX_COMMAND",
    "NOVA_COMMAND_REGISTRY_COMMAND",
]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return ""
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _count_contains(text: str, needles: List[str]) -> Dict[str, bool]:
    low = text.lower()

    return {
        needle: needle.lower() in low
        for needle in needles
    }


def _find_command_guard_markers(text: str) -> List[str]:
    markers = []

    for line in text.splitlines():
        clean = line.strip()

        if clean.startswith("# NOVA_") and "COMMAND" in clean and "GUARD" in clean:
            markers.append(clean.lstrip("#").strip())

    return markers


def _find_before_request_guards(text: str) -> List[str]:
    lines = text.splitlines()
    names = []

    for index, line in enumerate(lines):
        if "@app.before_request" not in line:
            continue

        for next_line in lines[index + 1:index + 6]:
            clean = next_line.strip()

            if clean.startswith("def ") and "(" in clean:
                names.append(clean.split("def ", 1)[1].split("(", 1)[0].strip())
                break

    return names


def create_autonomy_guard_cleanup_review(app_path: str = "app.py") -> Dict[str, object]:
    path = Path(app_path)
    text = _read_text(path)

    guard_markers = _find_command_guard_markers(text)
    before_request_guards = _find_before_request_guards(text)

    route_presence = _count_contains(text, EXPECTED_LOCKED_ROUTES)
    mode_presence = _count_contains(text, EXPECTED_LOCKED_MODES)
    marker_presence = _count_contains(text, EXPECTED_GUARD_MARKERS)

    missing_routes = [name for name, found in route_presence.items() if not found]
    missing_modes = [name for name, found in mode_presence.items() if not found]
    missing_markers = [name for name, found in marker_presence.items() if not found]

    return {
        "mode": "guard_cleanup_review_only",
        "status": "no_behavior_change_review",
        "target_file": str(path),
        "guard_marker_count": len(guard_markers),
        "before_request_guard_count": len(before_request_guards),
        "guard_markers": guard_markers,
        "before_request_guards": before_request_guards,
        "route_presence": route_presence,
        "mode_presence": mode_presence,
        "marker_presence": marker_presence,
        "missing_routes": missing_routes,
        "missing_modes": missing_modes,
        "missing_markers": missing_markers,
        "review_summary": [
            "app.py contains multiple locked command guards that now have registry metadata.",
            "This review is read-only and must not modify app.py.",
            "The safest next migration is one command at a time, not a broad centralization.",
            "The command-registry service is the read-only source of truth before any adapter work.",
        ],
        "safe_migration_plan": [
            "Keep every existing app.py guard in place for now.",
            "Create a tiny adapter for exactly one low-risk read-only command first.",
            "Start with command-registry because it is read-only and already registry-backed.",
            "Prove the adapter with the command-registry API smoke and memory quality smoke.",
            "Do not remove any old guard until the replacement route returns identical mode and route debug fields.",
            "Repeat one command at a time only after clean git status.",
        ],
        "required_smokes_before_any_refactor": [
            "python -m py_compile .\\app.py",
            "python .\\tools\\nova_command_registry_command_api_smoke.py",
            "python .\\tools\\nova_autonomy_command_registry_smoke.py",
            "python .\\tools\\nova_memory_quality_smoke.py",
        ],
        "forbidden_actions": [
            "Do not centralize all guards in one commit.",
            "Do not remove locked app.py guards during review.",
            "Do not rename routes, modes, commands, or prefixes.",
            "Do not weaken API smokes.",
            "Do not touch mobile, image, web, upload, or attachment code.",
            "Do not execute commands automatically.",
            "Do not edit files automatically.",
        ],
        "next_step": "Lock this cleanup review first, then create a one-command registry adapter for command-registry only.",
    }


def format_autonomy_guard_cleanup_review(app_path: str = "app.py") -> str:
    review = create_autonomy_guard_cleanup_review(app_path)

    lines = [
        "Nova autonomy guard cleanup review",
        "",
        f"Mode: {review['mode']}",
        f"Status: {review['status']}",
        f"Target file: {review['target_file']}",
        "",
        f"Command guard markers found: {review['guard_marker_count']}",
        f"Before-request guards found: {review['before_request_guard_count']}",
        "",
        "Guard markers:",
    ]

    if review["guard_markers"]:
        lines.extend(f"- {item}" for item in review["guard_markers"])
    else:
        lines.append("- none found")

    lines.extend(["", "Before-request guards:"])

    if review["before_request_guards"]:
        lines.extend(f"- {item}" for item in review["before_request_guards"])
    else:
        lines.append("- none found")

    lines.extend(["", "Missing locked routes:"])
    if review["missing_routes"]:
        lines.extend(f"- {item}" for item in review["missing_routes"])
    else:
        lines.append("- none")

    lines.extend(["", "Missing locked modes:"])
    if review["missing_modes"]:
        lines.extend(f"- {item}" for item in review["missing_modes"])
    else:
        lines.append("- none")

    lines.extend(["", "Missing guard markers:"])
    if review["missing_markers"]:
        lines.extend(f"- {item}" for item in review["missing_markers"])
    else:
        lines.append("- none")

    lines.extend(["", "Review summary:"])
    lines.extend(f"- {item}" for item in review["review_summary"])

    lines.extend(["", "Safe migration plan:"])
    for index, item in enumerate(review["safe_migration_plan"], start=1):
        lines.append(f"{index}. {item}")

    lines.extend(["", "Required smokes before any refactor:"])
    lines.extend(f"- {item}" for item in review["required_smokes_before_any_refactor"])

    lines.extend(["", "Forbidden actions:"])
    lines.extend(f"- {item}" for item in review["forbidden_actions"])

    lines.extend(["", f"Next step: {review['next_step']}"])

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    input_path = " ".join(sys.argv[1:]).strip() or "app.py"
    print(format_autonomy_guard_cleanup_review(input_path))
