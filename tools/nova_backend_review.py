from pathlib import Path
import ast
import re
import subprocess

ROOT = Path(".")
APP = ROOT / "app.py"
SERVICES = ROOT / "nova_backend" / "services"
TOOLS = ROOT / "tools"

def line_count(path):
    try:
        return len(path.read_text(encoding="utf-8-sig").splitlines())
    except Exception:
        return 0

def read(path):
    try:
        return path.read_text(encoding="utf-8-sig")
    except Exception:
        return ""

def count_pattern(text, pattern):
    return len(re.findall(pattern, text))

def py_files(folder):
    if not folder.exists():
        return []
    return sorted(folder.rglob("*.py"))

def ast_functions(path):
    text = read(path)
    try:
        tree = ast.parse(text)
    except Exception:
        return []
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

def top_files_by_lines(files, limit=20):
    return sorted(
        [(line_count(path), path) for path in files],
        reverse=True,
    )[:limit]

def main():
    print("NOVA BACKEND REVIEW")
    print("===================")

    service_files = py_files(SERVICES)
    tool_files = py_files(TOOLS)
    app_text = read(APP)

    print("")
    print("1. SIZE / SURFACE AREA")
    print("----------------------")
    print(f"app.py lines: {line_count(APP)}")
    print(f"service files: {len(service_files)}")
    print(f"tool/smoke files: {len(tool_files)}")

    print("")
    print("Largest backend/service files:")
    for lines, path in top_files_by_lines([APP] + service_files, limit=15):
        print(f"- {lines:5d} lines  {path}")

    print("")
    print("2. APP.PY ROUTE + HOOK PRESSURE")
    print("-------------------------------")
    print(f"@app.route count: {count_pattern(app_text, r'@app\\.route')}")
    print(f"@app.after_request count: {count_pattern(app_text, r'@app\\.after_request')}")
    print(f"@app.before_request count: {count_pattern(app_text, r'@app\\.before_request')}")
    print(f"NOVA marker count: {count_pattern(app_text, r'NOVA_[A-Z0-9_]+')}")
    print(f"try blocks in app.py: {count_pattern(app_text, r'\\btry:')}")
    print(f"except blocks in app.py: {count_pattern(app_text, r'\\bexcept\\b')}")

    print("")
    print("3. KNOWN BACKEND RISK MARKERS")
    print("-----------------------------")
    risk_terms = [
        "after_request",
        "route_taken",
        "project_state_current_memory_direct_recall",
        "project_brain_general_intelligence",
        "attachment",
        "session_id",
        "active_session_id",
        "stale",
        "fallback",
        "guard",
        "wrapper",
    ]

    for term in risk_terms:
        print(f"- {term}: {app_text.lower().count(term.lower())}")

    print("")
    print("4. PROJECT BRAIN SERVICES")
    print("-------------------------")
    project_brain_files = [
        path for path in service_files
        if "project_brain" in path.name
    ]
    for path in sorted(project_brain_files):
        funcs = ast_functions(path)
        print(f"- {path} | {line_count(path)} lines | {len(funcs)} funcs")

    print("")
    print("5. AUTONOMY / MEMORY / CHAT SERVICES")
    print("------------------------------------")
    focus_names = [
        "chat_service.py",
        "memory_service.py",
        "planner_service.py",
        "chat_execution_service.py",
        "model_gateway_service.py",
    ]
    for name in focus_names:
        path = SERVICES / name
        if path.exists():
            funcs = ast_functions(path)
            print(f"- {path} | {line_count(path)} lines | {len(funcs)} funcs")
        else:
            print(f"- MISSING: {path}")

    print("")
    print("6. SMOKE COVERAGE SIGNALS")
    print("-------------------------")
    smoke_files = sorted(TOOLS.glob("*smoke*.py"))
    print(f"smoke files: {len(smoke_files)}")
    for path in smoke_files[-40:]:
        print(f"- {path}")

    print("")
    print("7. GIT STATUS")
    print("-------------")
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout.strip()
        print(output if output else "clean")
    except Exception as exc:
        print(f"git status failed: {exc}")

    print("")
    print("8. REVIEW RECOMMENDATION")
    print("------------------------")
    print("Recommended review order:")
    print("1. app.py after_request / route guard stack")
    print("2. Project Brain service boundaries")
    print("3. direct recall vs Command Center ownership")
    print("4. session + attachment backend paths")
    print("5. smoke suite consolidation")
    print("")
    print("NOVA BACKEND REVIEW COMPLETE")

if __name__ == '__main__':
    main()
