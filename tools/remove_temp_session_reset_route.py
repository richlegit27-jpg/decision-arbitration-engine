from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "# NOVA_TEMP_SESSION_RESET_ROUTE_20260704"
function_name = "def nova_temp_reset_sessions_clean_start_20260704():"

lines = text.splitlines(keepends=True)

marker_index = None
for i, line in enumerate(lines):
    if marker in line:
        marker_index = i
        break

if marker_index is None:
    raise SystemExit("Reset route marker not found. It may already be removed.")

def_index = None
for i in range(marker_index, len(lines)):
    if function_name in lines[i]:
        def_index = i
        break

if def_index is None:
    raise SystemExit("Reset route function not found after marker.")

end_index = len(lines)

for i in range(def_index + 1, len(lines)):
    line = lines[i]
    stripped = line.strip()

    if not stripped:
        continue

    if not line.startswith((" ", "\t")):
        end_index = i
        break

start_index = marker_index

while start_index > 0 and not lines[start_index - 1].strip():
    start_index -= 1

removed = "".join(lines[start_index:end_index])
new_text = "".join(lines[:start_index] + lines[end_index:])

path.write_text(new_text, encoding="utf-8")

print("Removed temporary reset route.")
print("Removed lines:", len(removed.splitlines()))
