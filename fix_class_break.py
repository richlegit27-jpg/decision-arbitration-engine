from pathlib import Path

p = Path(r"C:\Users\Owner\nova\nova_backend\services\chat_service.py")
s = p.read_text(encoding="utf-8-sig")

bad = """

import threading
import time

def _start_execution_worker(self, session_id: str):
"""

good = """

    def _start_execution_worker(self, session_id: str):
"""

if bad not in s:
    raise SystemExit("BAD BLOCK NOT FOUND")

s = s.replace(bad, good, 1)

p.write_text(s, encoding="utf-8")
print("FIXED_CLASS_BREAK")
