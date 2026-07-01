from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
MEMORY_PATH = ROOT / "data" / "nova_memory.json"
PROJECT_STATE_PATH = ROOT / "data" / "nova_project_state.json"


NOISE_PATTERNS = [
    ("placeholder_next_move", r"\bnext task here\b"),
    ("old_idle_fallback", r"\bno active task is currently tracked yet\b"),
    ("old_execution_idle_fallback", r"\bno active execution mission\b"),
    ("failed_phase3_patch", r"NOVA_PROJECT_STATE_CONTEXT_RECALL_PHASE3_20260701"),
    ("phase3_import_error", r"name ['\"]?_question_kind['\"]? is not defined"),
    ("generic_alignment_reply", r"\byes\s*-\s*i['’]?m aligned and ready\b"),
    ("debug_noise", r"\bDEBUG GOAL:\b|\bDEBUG CLEAN:\b|\bDEBUG LOWER:\b"),
    ("server_log_noise", r"\bGET /api/backend/readiness\b|\bPOST /api/chat\b"),
]


def load_json(path: Path) -> Any:
    try:
        if not path.exists():
            return None

        raw = path.read_text(encoding="utf-8-sig").strip()
        if not raw:
            return None

        return json.loads(raw)
    except Exception as exc:
        return {
            "_load_error": str(exc),
            "_path": str(path),
        }


def compact_text(value: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text

    return text[: limit - 3] + "..."


def iter_text_nodes(value: Any, path: str = "$") -> Iterable[Tuple[str, str]]:
    if isinstance(value, dict):
        for key, nested in value.items():
            child_path = f"{path}.{key}"
            yield from iter_text_nodes(nested, child_path)
        return

    if isinstance(value, list):
        for index, nested in enumerate(value):
            child_path = f"{path}[{index}]"
            yield from iter_text_nodes(nested, child_path)
        return

    if isinstance(value, str):
        yield path, value


def detect_reasons(text: str) -> List[str]:
    reasons: List[str] = []

    for name, pattern in NOISE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            reasons.append(name)

    return reasons


def audit_memory(memory: Any) -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []
    total_text_nodes = 0

    for path, text in iter_text_nodes(memory):
        total_text_nodes += 1
        reasons = detect_reasons(text)

        if reasons:
            candidates.append(
                {
                    "path": path,
                    "reasons": reasons,
                    "text": compact_text(text),
                }
            )

    return {
        "memory_path": str(MEMORY_PATH),
        "total_text_nodes": total_text_nodes,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def project_state_summary(project_state: Any) -> Dict[str, Any]:
    if not isinstance(project_state, dict):
        return {
            "project_state_path": str(PROJECT_STATE_PATH),
            "loaded": False,
        }

    return {
        "project_state_path": str(PROJECT_STATE_PATH),
        "loaded": True,
        "checkpoint": project_state.get("checkpoint", ""),
        "current_focus": project_state.get("current_focus", ""),
        "next_move": project_state.get("next_move", ""),
        "locked_count": len(project_state.get("locked", []) or []),
        "remaining_count": len(project_state.get("remaining", []) or []),
    }


def render_text_report(result: Dict[str, Any]) -> str:
    lines: List[str] = []

    project = result.get("project_state", {})
    audit = result.get("memory_audit", {})

    lines.append("Nova memory hygiene audit")
    lines.append("")
    lines.append("Project state:")
    lines.append(f"- checkpoint: {project.get('checkpoint') or 'unknown'}")
    lines.append(f"- current_focus: {project.get('current_focus') or 'unknown'}")
    lines.append(f"- next_move: {project.get('next_move') or 'unknown'}")
    lines.append("")
    lines.append("Memory scan:")
    lines.append(f"- text nodes scanned: {audit.get('total_text_nodes', 0)}")
    lines.append(f"- noisy/stale candidates: {audit.get('candidate_count', 0)}")

    candidates = audit.get("candidates", []) or []
    if candidates:
        lines.append("")
        lines.append("Candidates:")
        for index, item in enumerate(candidates[:50], start=1):
            reasons = ", ".join(item.get("reasons", []))
            lines.append(f"{index}. {item.get('path')} [{reasons}]")
            lines.append(f"   {item.get('text')}")

    if len(candidates) > 50:
        lines.append("")
        lines.append(f"... {len(candidates) - 50} more candidates omitted from text report.")

    if not candidates:
        lines.append("")
        lines.append("No obvious noisy project-memory candidates found.")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Nova memory for stale/noisy project-memory entries.")
    parser.add_argument("--json", action="store_true", help="Print JSON output instead of text.")
    parser.add_argument(
        "--fail-on-candidates",
        action="store_true",
        help="Exit non-zero when noisy/stale candidates are found.",
    )

    args = parser.parse_args()

    memory = load_json(MEMORY_PATH)
    project_state = load_json(PROJECT_STATE_PATH)

    result = {
        "project_state": project_state_summary(project_state),
        "memory_audit": audit_memory(memory),
    }

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render_text_report(result))

    candidate_count = int(result["memory_audit"].get("candidate_count") or 0)

    if args.fail_on_candidates and candidate_count:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
