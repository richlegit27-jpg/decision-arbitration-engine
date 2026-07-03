from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_DATA_PATH_HEALTH_DIAGNOSTIC_20260703"
if marker in text:
    print("data path health diagnostic already installed")
    raise SystemExit(0)

needle = 'payload["auth_users_file_exists"] = bool(users_file.exists())'
if needle not in text:
    raise SystemExit("could not find auth health insertion point")

insert = '''
            # NOVA_DATA_PATH_HEALTH_DIAGNOSTIC_20260703
            try:
                import os as _nova_data_health_os_20260703
                payload["nova_data_dir_env"] = _nova_data_health_os_20260703.environ.get("NOVA_DATA_DIR")
                payload["nova_sessions_file_env"] = _nova_data_health_os_20260703.environ.get("NOVA_SESSIONS_FILE")
                payload["data_dir_resolved"] = str(data_dir.resolve())
                payload["data_dir_exists"] = bool(data_dir.exists())
                payload["sessions_file_exists"] = bool((data_dir / "nova_sessions.json").exists())
                payload["sessions_file_size"] = (
                    (data_dir / "nova_sessions.json").stat().st_size
                    if (data_dir / "nova_sessions.json").exists()
                    else 0
                )
            except Exception as _nova_data_health_error_20260703:
                payload["data_path_health_error"] = str(_nova_data_health_error_20260703)
'''

text = text.replace(needle, needle + "\n" + insert, 1)
path.write_text(text.rstrip() + "\n", encoding="utf-8")
print("installed data path health diagnostic")
