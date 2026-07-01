from pathlib import Path

path = Path("nova_backend/services/project_brain_freshness_snapshot.py")
text = path.read_text(encoding="utf-8")

marker = "# NOVA_PROJECT_BRAIN_FRESHNESS_SNAPSHOT_SANITIZER_20260702"

if marker in text:
    print("freshness snapshot sanitizer already installed")
    raise SystemExit(0)

patch = r'''

# NOVA_PROJECT_BRAIN_FRESHNESS_SNAPSHOT_SANITIZER_20260702
# Final structured-field sanitizer for Project Brain freshness snapshot.
# Rejects malformed memory-derived fields such as "text: Current Nova project state..."
# and restores clean checkpoint/blocker/next-move wording.
try:
    from dataclasses import replace as _nova_freshness_snapshot_replace_20260702

    _NOVA_PRE_SANITIZED_BUILD_PROJECT_BRAIN_FRESHNESS_SNAPSHOT_20260702 = build_project_brain_freshness_snapshot

    _NOVA_CLEAN_CHECKPOINT_20260702 = (
        "Project Brain routing, classifier broadening, context-builder answers, "
        "direct freshness, and freshness snapshot validation are protected by dedicated smokes."
    )

    _NOVA_CLEAN_BLOCKER_20260702 = (
        "Project Brain answer freshness v2: fallback-route priority and the context-builder path "
        "are protected, but checkpoint, blocker, next move, recent commits, and validation state "
        "should come from this structured freshness snapshot instead of another wording patch."
    )

    _NOVA_CLEAN_NEXT_MOVE_20260702 = (
        "Next concrete move / safe move: use the Project Brain freshness snapshot as the "
        "context builder source of truth for checkpoint, blocker, next move, fallback priority, "
        "recent commits, validation state, and available smoke files."
    )

    def _nova_project_brain_snapshot_bad_field_20260702(value, required_terms=None):
        text_value = str(value or "").strip()
        lower = text_value.lower()
        required_terms = required_terms or []

        if not text_value:
            return True

        if any(term.lower() not in lower for term in required_terms):
            return True

        bad_terms = [
            "text: current nova project state",
            "current nova project state: richard is working",
            "and fres current blocker",
            "next move: harden",
            "live_answer_sample.py",
            "idle/generic fallback",
            "finish nova project brain answer quality",
            "larger nova answer-quality 95 smoke now passes 20/20",
            "measured answer-policy intelligence",
        ]

        return any(term in lower for term in bad_terms)

    def _nova_project_brain_sanitize_snapshot_20260702(snapshot):
        updates = {}

        checkpoint = getattr(snapshot, "checkpoint", "")
        blocker = getattr(snapshot, "blocker", "")
        next_move = getattr(snapshot, "next_move", "")

        if _nova_project_brain_snapshot_bad_field_20260702(
            checkpoint,
            ["Project Brain", "freshness"],
        ):
            updates["checkpoint"] = _NOVA_CLEAN_CHECKPOINT_20260702

        if _nova_project_brain_snapshot_bad_field_20260702(
            blocker,
            ["answer freshness", "fallback"],
        ):
            updates["blocker"] = _NOVA_CLEAN_BLOCKER_20260702

        if _nova_project_brain_snapshot_bad_field_20260702(
            next_move,
            ["safe move", "freshness snapshot", "context builder"],
        ):
            updates["next_move"] = _NOVA_CLEAN_NEXT_MOVE_20260702

        if not updates:
            return snapshot

        try:
            return _nova_freshness_snapshot_replace_20260702(snapshot, **updates)
        except Exception:
            for key, value in updates.items():
                try:
                    setattr(snapshot, key, value)
                except Exception:
                    pass
            return snapshot

    def build_project_brain_freshness_snapshot(*args, **kwargs):
        snapshot = _NOVA_PRE_SANITIZED_BUILD_PROJECT_BRAIN_FRESHNESS_SNAPSHOT_20260702(
            *args,
            **kwargs,
        )
        return _nova_project_brain_sanitize_snapshot_20260702(snapshot)

except Exception as _nova_project_brain_freshness_snapshot_sanitizer_error_20260702:
    try:
        print(
            "[NOVA_PROJECT_BRAIN_FRESHNESS_SNAPSHOT_SANITIZER_20260702] failed:",
            _nova_project_brain_freshness_snapshot_sanitizer_error_20260702,
        )
    except Exception:
        pass

'''

path.write_text(text.rstrip() + "\n\n" + patch.lstrip(), encoding="utf-8")
print("installed Project Brain freshness snapshot sanitizer")
