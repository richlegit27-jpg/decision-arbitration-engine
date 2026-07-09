from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

marker = "NOVA_RAILWAY_PERSISTENT_DATA_BOOTSTRAP_20260702"

if marker in text:
    print("persistent data bootstrap already installed")
    raise SystemExit(0)

patch = r'''
# ============================================================
# NOVA_RAILWAY_PERSISTENT_DATA_BOOTSTRAP_20260702
# Railway persistence fix:
# If NOVA_DATA_DIR is set, bind app runtime data/uploads to it.
# Expected Railway env:
#   NOVA_DATA_DIR=/data
# Expected Railway volume mount:
#   /data
# This preserves sessions, memory, artifacts, and generated uploads
# across Railway deploys/restarts.
# ============================================================
try:
    import os as _nova_persist_os
    import shutil as _nova_persist_shutil
    from pathlib import Path as _NovaPersistPath

    def _nova_copy_tree_contents_20260702(source, target):
        try:
            source = _NovaPersistPath(source)
            target = _NovaPersistPath(target)
            if not source.exists() or not source.is_dir():
                return

            target.mkdir(parents=True, exist_ok=True)

            for child in source.iterdir():
                dest = target / child.name

                if child.is_dir():
                    if not dest.exists():
                        _nova_persist_shutil.copytree(child, dest)
                    else:
                        _nova_copy_tree_contents_20260702(child, dest)
                else:
                    if not dest.exists():
                        _nova_persist_shutil.copy2(child, dest)
        except Exception as exc:
            try:
                print("[NOVA_RAILWAY_PERSISTENT_DATA_BOOTSTRAP_20260702] copy failed:", exc)
            except Exception:
                pass

    def _nova_bind_path_to_persistent_target_20260702(app_path, persistent_path):
        try:
            app_path = _NovaPersistPath(app_path)
            persistent_path = _NovaPersistPath(persistent_path)

            persistent_path.mkdir(parents=True, exist_ok=True)

            if app_path.exists() and not app_path.is_symlink():
                _nova_copy_tree_contents_20260702(app_path, persistent_path)

                backup_path = app_path.with_name(app_path.name + "_container_backup")
                if backup_path.exists() and backup_path.is_dir():
                    _nova_persist_shutil.rmtree(backup_path, ignore_errors=True)

                try:
                    app_path.rename(backup_path)
                except Exception:
                    _nova_persist_shutil.rmtree(app_path, ignore_errors=True)

            if app_path.is_symlink():
                try:
                    current_target = _nova_persist_os.readlink(str(app_path))
                except Exception:
                    current_target = ""

                if str(persistent_path) != str(current_target):
                    try:
                        app_path.unlink()
                    except Exception:
                        pass

            if not app_path.exists():
                try:
                    app_path.symlink_to(persistent_path, target_is_directory=True)
                except Exception:
                    # Symlink fallback: keep directory and copy data.
                    app_path.mkdir(parents=True, exist_ok=True)
                    _nova_copy_tree_contents_20260702(persistent_path, app_path)

            return True
        except Exception as exc:
            try:
                print("[NOVA_RAILWAY_PERSISTENT_DATA_BOOTSTRAP_20260702] bind failed:", app_path, persistent_path, exc)
            except Exception:
                pass
            return False

    _nova_persistent_root_20260702 = str(_nova_persist_os.environ.get("NOVA_DATA_DIR") or "").strip()

    if _nova_persistent_root_20260702:
        _nova_root_20260702 = _NovaPersistPath.cwd()
        _nova_persistent_root_path_20260702 = _NovaPersistPath(_nova_persistent_root_20260702)
        _nova_persistent_root_path_20260702.mkdir(parents=True, exist_ok=True)

        _nova_bind_path_to_persistent_target_20260702(
            _nova_root_20260702 / "data",
            _nova_persistent_root_path_20260702,
        )

        _nova_bind_path_to_persistent_target_20260702(
            _nova_root_20260702 / "uploads",
            _nova_persistent_root_path_20260702 / "uploads",
        )

        try:
            _nova_persist_os.environ["NOVA_SESSIONS_FILE"] = str(_nova_persistent_root_path_20260702 / "nova_sessions.json")
            _nova_persist_os.environ["NOVA_MEMORY_FILE"] = str(_nova_persistent_root_path_20260702 / "nova_memory.json")
            _nova_persist_os.environ["NOVA_ARTIFACTS_FILE"] = str(_nova_persistent_root_path_20260702 / "nova_artifacts.json")
            _nova_persist_os.environ["NOVA_UPLOADS_DIR"] = str(_nova_persistent_root_path_20260702 / "uploads")
        except Exception:
            pass

        try:
            print(
                "[NOVA_RAILWAY_PERSISTENT_DATA_BOOTSTRAP_20260702] active",
                "root=", str(_nova_persistent_root_path_20260702),
                "data=", str(_nova_root_20260702 / "data"),
                "uploads=", str(_nova_root_20260702 / "uploads"),
            )
        except Exception:
            pass
    else:
        try:
            print("[NOVA_RAILWAY_PERSISTENT_DATA_BOOTSTRAP_20260702] skipped; NOVA_DATA_DIR not set")
        except Exception:
            pass

except Exception as _nova_persistent_data_bootstrap_error_20260702:
    try:
        print("[NOVA_RAILWAY_PERSISTENT_DATA_BOOTSTRAP_20260702] outer failed:", _nova_persistent_data_bootstrap_error_20260702)
    except Exception:
        pass

'''

# Put this right after __future__ imports if present, otherwise before normal imports.
lines = text.splitlines()
insert_at = 0

while insert_at < len(lines) and lines[insert_at].startswith("from __future__ import "):
    insert_at += 1

lines.insert(insert_at, patch)
text = "\n".join(lines) + "\n"

path.write_text(text, encoding="utf-8")
print("patched Railway persistent data bootstrap")
