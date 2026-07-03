from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

start_marker = "# NOVA_DURABLE_DATA_BOOTSTRAP_20260703"
end_marker = "# /NOVA_DURABLE_DATA_BOOTSTRAP_20260703"

start = text.index(start_marker)
end = text.index(end_marker, start) + len(end_marker)

new_bootstrap = r'''# NOVA_DURABLE_DATA_BOOTSTRAP_20260703
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

        # Only use /data when it already exists, which indicates a real mounted
        # Railway volume. Do not create fake /data on local Windows or ephemeral
        # containers, because that can move repo-local data unexpectedly.
        volume_data = Path("/data")
        if os.name != "nt" and volume_data.exists():
            candidates.append(volume_data)

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

        should_bridge_app_data = False
        try:
            should_bridge_app_data = chosen.resolve() != app_data.resolve()
        except Exception:
            should_bridge_app_data = str(chosen) != str(app_data)

        if should_bridge_app_data:
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
# /NOVA_DURABLE_DATA_BOOTSTRAP_20260703'''

text = text[:start] + new_bootstrap + text[end:]
path.write_text(text, encoding="utf-8")
print("patched safer durable bootstrap")
