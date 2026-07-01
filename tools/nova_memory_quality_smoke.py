from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


REQUIRED_SMOKES = [
    "nova_project_state_smoke.py",
    "nova_project_context_smoke.py",
    "nova_project_compact_context_api_smoke.py",
    "nova_autonomy_task_brain_smoke.py",
    "nova_autonomy_command_api_smoke.py",
    "nova_phase_3i_static_backup_review_smoke.py",
    "nova_phase_3j_backup_guard_smoke.py",
    "nova_phase_3k_frontend_stability_smoke.py",
]


def run_smoke(filename):
    path = TOOLS / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing required smoke: {path}")

    subprocess.run([sys.executable, str(path)], cwd=ROOT, check=True)
    print(f"PASS {path.stem}")


def main():
    for filename in REQUIRED_SMOKES:
        run_smoke(filename)

    print("NOVA MEMORY QUALITY SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
