import subprocess
import sys
import urllib.request
from pathlib import Path


ROOT = Path.cwd()
BASE_URL = "http://127.0.0.1:5001"


SMOKES = [
    {
        "name": "project state recall",
        "path": "tools/nova_project_state_smoke.py",
        "required": True,
    },
    {
        "name": "project compact context API",
        "path": "tools/nova_project_compact_context_api_smoke.py",
        "required": True,
    },
    {
        "name": "autonomy task brain",
        "path": "tools/nova_autonomy_task_brain_smoke.py",
        "required": True,
    },
    {
        "name": "autonomy command API",
        "path": "tools/nova_autonomy_command_api_smoke.py",
        "required": True,
    },
    {
        "name": "phase 6D high value backend bundle",
        "path": "tools/nova_phase_6d_high_value_smoke_bundle.py",
        "required": True,
    },
    {
        "name": "image web block cleanup validation",
        "path": "tools/nova_phase_6e_image_web_block_cleanup_plan_smoke.py",
        "required": True,
    },
    {
        "name": "image attachment live route",
        "path": "tools/nova_phase_6f_image_attachment_route_live_smoke.py",
        "required": True,
    },
    {
        "name": "session double-save live behavior",
        "path": "tools/nova_phase_6g_session_double_save_live_smoke.py",
        "required": True,
    },
]


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def server_is_up():
    try:
        with urllib.request.urlopen(BASE_URL + "/api/health", timeout=5) as response:
            return response.status < 500
    except Exception:
        return False


def run_smoke(item):
    path = ROOT / item["path"]

    print("")
    print(f"=== {item['name']} ===")
    print(path)

    if not path.exists():
        print(f"FAIL missing smoke: {path}")
        return False

    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    output = completed.stdout.strip()
    if output:
        print(output)

    if completed.returncode != 0:
        print(f"FAIL {item['name']} exit={completed.returncode}")
        return False

    print(f"PASS {item['name']}")
    return True


def main():
    print("NOVA INTELLIGENCE BEHAVIOR SMOKE")
    print(f"Root: {ROOT}")
    print("")

    assert_true("app.py exists", (ROOT / "app.py").exists())
    assert_true("tools directory exists", (ROOT / "tools").exists())

    if not server_is_up():
        print("")
        print("NOVA INTELLIGENCE BEHAVIOR SMOKE FAILED")
        print("Server is not reachable at http://127.0.0.1:5001")
        print("Start Nova in another PowerShell with: python .\\app.py")
        return 1

    print("PASS local Nova server reachable")

    failures = []

    for item in SMOKES:
        ok = run_smoke(item)
        if not ok and item.get("required", True):
            failures.append(item["name"])

    print("")
    if failures:
        print("NOVA INTELLIGENCE BEHAVIOR SMOKE FAILED")
        print("Failed checks:")
        for name in failures:
            print(f"- {name}")
        return 1

    print("NOVA INTELLIGENCE BEHAVIOR SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
