from pathlib import Path

p = Path(r"C:\Users\Owner\nova\nova_backend\services\chat_service.py")
lines = p.read_text(encoding="utf-8-sig").splitlines()

start = None
end = None

for i, line in enumerate(lines):
    if line == "def _start_execution_worker(self, session_id: str):":
        start = i
        break

if start is None:
    raise SystemExit("START NOT FOUND")

for i in range(start + 1, len(lines)):
    if lines[i].startswith("    def _compose_model_messages"):
        end = i
        break

if end is None:
    raise SystemExit("END NOT FOUND")

for i in range(start, end):
    if lines[i].strip():
        lines[i] = "    " + lines[i]

p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("INDENTED_WORKER_BLOCK")
print("start", start + 1, "end", end + 1)


