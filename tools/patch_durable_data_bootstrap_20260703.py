from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

BOOT = "NOVA_DURABLE_DATA_BOOTSTRAP_20260703"
ROUTE = "NOVA_DURABLE_DATA_HEALTH_ROUTE_20260703"

bootstrap = r'''
# NOVA_DURABLE_DATA_BOOTSTRAP_20260703
def _nova_durable_data_bootstrap_20260703():
    try:
        import os
        import shutil
        import time
        from pathlib import Path

        base_dir = Path(__file__).resolve().parent
        app_data = base_dir / "data"

        candidates = []

        explicit = os.environ.get("NOVA_DATA_DIR", "").strip()
        if explicit:
            candidates.append(Path(explicit))

        candidates.append(Path("/data"))
        candidates.append(app_data)

        chosen = None

        for candidate in candidates:
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                probe = candidate / ".nova_write_probe"
                probe.write_text("ok", encoding="utf-8")
                probe.unlink(missing_ok=True)
                chosen = candidate
                break
            except Exception:
                continue

        if chosen is None:
            chosen = app_data
            chosen.mkdir(parents=True, exist_ok=True)

        os.environ["NOVA_DATA_DIR"] = str(chosen)

        if chosen.resolve() != app_data.resolve():
            chosen.mkdir(parents=True, exist_ok=True)

            if app_data.exists() and not app_data.is_symlink():
                for item in app_data.iterdir():
                    target = chosen / item.name
                    if target.exists():
                        continue
                    try:
                        if item.is_dir():
                            shutil.copytree(item, target)
                        else:
                            shutil.copy2(item, target)
                    except Exception:
                        pass

                try:
                    app_data.rename(base_dir / ("data_ephemeral_backup_" + time.strftime("%Y%m%d_%H%M%S")))
                except Exception:
                    pass

            if not app_data.exists():
                try:
                    app_data.symlink_to(chosen, target_is_directory=True)
                except Exception:
                    pass

        print("[NOVA_DURABLE_DATA_BOOTSTRAP_20260703] NOVA_DATA_DIR=", os.environ.get("NOVA_DATA_DIR"))
        print("[NOVA_DURABLE_DATA_BOOTSTRAP_20260703] app_data=", str(app_data), "real=", str(app_data.resolve()))

    except Exception as exc:
        try:
            print("[NOVA_DURABLE_DATA_BOOTSTRAP_20260703] failed:", exc)
        except Exception:
            pass


_nova_durable_data_bootstrap_20260703()
# /NOVA_DURABLE_DATA_BOOTSTRAP_20260703

'''

route = r'''
# NOVA_DURABLE_DATA_HEALTH_ROUTE_20260703
try:
    @app.get("/api/storage/health")
    def _nova_storage_health_20260703():
        import os
        from pathlib import Path

        base_dir = Path(__file__).resolve().parent
        app_data = base_dir / "data"
        env_data = Path(os.environ.get("NOVA_DATA_DIR", str(app_data)))

        names = [
            "nova_auth_users.json",
            "nova_sessions.json",
            "nova_memory.json",
            "nova_artifacts.json",
            "nova_flask_secret.key",
        ]

        def info(path):
            try:
                return {
                    "path": str(path),
                    "exists": path.exists(),
                    "is_file": path.is_file(),
                    "is_dir": path.is_dir(),
                    "is_symlink": path.is_symlink(),
                    "realpath": str(path.resolve()) if path.exists() or path.is_symlink() else None,
                }
            except Exception as exc:
                return {"path": str(path), "error": str(exc)}

        return {
            "ok": True,
            "marker": "NOVA_DURABLE_DATA_HEALTH_ROUTE_20260703",
            "cwd": os.getcwd(),
            "base_dir": str(base_dir),
            "nova_data_dir_env": os.environ.get("NOVA_DATA_DIR"),
            "app_data": info(app_data),
            "env_data": info(env_data),
            "files": {
                name: {
                    "app_data": info(app_data / name),
                    "env_data": info(env_data / name),
                }
                for name in names
            },
        }
except Exception as exc:
    try:
        print("[NOVA_DURABLE_DATA_HEALTH_ROUTE_20260703] failed:", exc)
    except Exception:
        pass
# /NOVA_DURABLE_DATA_HEALTH_ROUTE_20260703

'''

if BOOT not in text:
    if text.startswith("from __future__ import annotations\n"):
        text = text.replace(
            "from __future__ import annotations\n",
            "from __future__ import annotations\n\n" + bootstrap,
            1,
        )
    else:
        text = bootstrap + text

if ROUTE not in text:
    guard = 'if __name__ == "__main__":'
    if guard in text:
        text = text.replace(guard, route + "\n" + guard, 1)
    else:
        text = text.rstrip() + "\n\n" + route + "\n"

path.write_text(text, encoding="utf-8")
print("patched app.py")
