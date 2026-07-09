from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "tools" / "nova_master_quality_gate.py"

if not TARGET.exists():
    raise SystemExit("Missing target gate: tools/nova_master_quality_gate.py")

runpy.run_path(str(TARGET), run_name="__main__")
