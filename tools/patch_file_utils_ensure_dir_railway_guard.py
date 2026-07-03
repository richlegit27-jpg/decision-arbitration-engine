from pathlib import Path

path = Path("nova_backend/utils/file_utils.py")
text = path.read_text(encoding="utf-8")

lines = text.splitlines(keepends=True)

start = None
for i, line in enumerate(lines):
    if line.startswith("def ensure_dir"):
        start = i
        break

if start is None:
    raise SystemExit("Could not find a top-level ensure_dir function")

end = len(lines)
for j in range(start + 1, len(lines)):
    line = lines[j]

    if line.strip() == "":
        continue

    if not line.startswith((" ", "\t")) and (
        line.startswith("def ") or
        line.startswith("class ") or
        line.startswith("@")
    ):
        end = j
        break

replacement = '''def ensure_dir(path):
    """
    Ensure a path is a usable directory.

    If Railway presents an existing file or broken symlink at a directory path,
    repair it instead of crashing app boot with FileExistsError.
    """
    from pathlib import Path
    import time

    p = Path(path)

    try:
        if p.is_dir():
            return p

        if p.exists() or p.is_symlink():
            backup = p.with_name(f"{p.name}.file_blocker_{int(time.time())}")
            try:
                p.rename(backup)
            except Exception:
                try:
                    p.unlink()
                except FileNotFoundError:
                    pass

        p.mkdir(parents=True, exist_ok=True)
        return p

    except FileExistsError:
        if p.is_dir():
            return p

        if p.exists() or p.is_symlink():
            backup = p.with_name(f"{p.name}.file_blocker_{int(time.time())}")
            try:
                p.rename(backup)
            except Exception:
                try:
                    p.unlink()
                except FileNotFoundError:
                    pass

        p.mkdir(parents=True, exist_ok=True)
        return p
'''

new_text = "".join(lines[:start]) + replacement + "\n\n" + "".join(lines[end:])
path.write_text(new_text, encoding="utf-8")
print(f"patched {path} lines {start + 1}-{end}")
