from pathlib import Path
import tempfile
import shutil

from nova_backend.utils.file_utils import ensure_dir

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

tmp = Path(tempfile.mkdtemp(prefix="nova_ensure_dir_guard_"))

try:
    normal = tmp / "normal"
    ensure_dir(normal)
    check("creates missing directory", normal.exists() and normal.is_dir())

    ensure_dir(normal)
    check("existing directory stays valid", normal.exists() and normal.is_dir())

    blocker = tmp / "data"
    blocker.write_text("not a directory", encoding="utf-8")
    ensure_dir(blocker)
    check("file blocker replaced with directory", blocker.exists() and blocker.is_dir())

    backups = list(tmp.glob("data.file_blocker_*"))
    check("file blocker backed up", len(backups) >= 1)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("")
print("NOVA ENSURE DIR RAILWAY GUARD SMOKE PASSED")
