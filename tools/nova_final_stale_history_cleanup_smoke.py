from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def require(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)
    print("PASS", message)


print("=" * 80)
print("NOVA FINAL STALE HISTORY CLEANUP SMOKE")
print("=" * 80)


from nova_backend.services.project_brain_state_bridge import (
    build_state_bridge_record,
)


record = build_state_bridge_record(
    next_move="continue cleanup validation",
)


payload = json.dumps(
    record.__dict__,
    default=str,
    indent=2,
).lower()


require(
    "project brain" in payload,
    "project brain context survives cleanup path",
)

require(
    "decision engine" in payload,
    "decision engine context survives cleanup path",
)

require(
    "stale history" not in payload,
    "stale history marker not injected into fresh state",
)

print()
print("=" * 80)
print("NOVA FINAL STALE HISTORY CLEANUP SMOKE PASSED")
print("=" * 80)