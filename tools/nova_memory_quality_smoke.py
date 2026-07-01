import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SMOKES = [
    "nova_project_state_smoke.py",
    "nova_project_context_smoke.py",
    "nova_project_compact_context_api_smoke.py",
    "nova_autonomy_task_brain_smoke.py",
    "nova_autonomy_command_api_smoke.py",
    "nova_phase_3i_static_backup_review_smoke.py",
    "nova_phase_3j_backup_guard_smoke.py",
    "nova_phase_3k_frontend_stability_smoke.py",
    "nova_phase_4b_live_autonomy_lifecycle_smoke.py",
    "nova_phase_4e_live_completion_cleanup_smoke.py",
    "nova_phase_4f_normal_chat_isolation_smoke.py",
]


def run_smoke(filename):
    smoke_path = ROOT / "tools" / filename
    subprocess.run([sys.executable, str(smoke_path)], cwd=ROOT, check=True)
    print(f"PASS {smoke_path.stem}")


def main():
    for filename in SMOKES:
        run_smoke(filename)

    print("NOVA MEMORY QUALITY SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
