from pathlib import Path


MARKER = "NOVA_PROJECT_BRAIN_DECISION_LOG_ROUTE_KEYWORDS_20260701"

CANDIDATES = [
    Path("app.py"),
    Path("nova_backend/services/project_brain_decision_engine.py"),
    Path("nova_backend/services/project_brain_general_intelligence.py"),
    Path("nova_backend/services/project_brain_context_builder.py"),
    Path("nova_backend/services/chat_service.py"),
]

KEYWORDS = [
    "what changed recently",
    "what changed lately",
    "recent changes",
    "recent decisions",
    "decision log",
    "recent commits",
    "last commits",
    "latest commits",
    "what did we commit",
    "what did we lock recently",
    "what got locked recently",
    "locked upgrades",
    "operator timeline",
]

existing = [path for path in CANDIDATES if path.exists()]
if not existing:
    raise SystemExit("no candidate files found")

patched = False

for path in existing:
    text = path.read_text(encoding="utf-8-sig")
    lowered = text.lower()

    if MARKER in text:
        print(f"already patched: {path}")
        patched = True
        continue

    # Prefer the existing Project Brain top-priority/Decision Engine layer.
    is_best_target = (
        "NOVA_PROJECT_BRAIN_QUESTION_TOP_PRIORITY_20260701" in text
        or "project_brain_general_intelligence" in lowered
        or "mission control" in lowered
    )

    if not is_best_target:
        continue

    insert = (
        f"\n# {MARKER}\n"
        "NOVA_PROJECT_BRAIN_DECISION_LOG_ROUTE_KEYWORDS_20260701 = (\n"
        + "".join(f'    "{keyword}",\n' for keyword in KEYWORDS)
        + ")\n\n"
        "def _nova_project_brain_decision_log_route_question_20260701(user_text):\n"
        "    text = str(user_text or '').strip().lower()\n"
        "    return any(keyword in text for keyword in NOVA_PROJECT_BRAIN_DECISION_LOG_ROUTE_KEYWORDS_20260701)\n"
    )

    # If this file has a general Project Brain question classifier, patch it by adding a
    # fallback helper that later route wrappers can use.
    path.write_text(text + insert, encoding="utf-8")
    print(f"installed decision-log route keywords in {path}")
    patched = True
    break

if not patched:
    raise SystemExit("could not find a Project Brain route/classifier target to patch")

print("decision-log route keyword helper installed")
