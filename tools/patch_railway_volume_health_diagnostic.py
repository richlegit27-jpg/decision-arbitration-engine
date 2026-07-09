from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_RAILWAY_VOLUME_HEALTH_DIAGNOSTIC_20260703"
if marker in text:
    print("volume health diagnostic already installed")
    raise SystemExit(0)

needle = 'payload["nova_sessions_file_env"] = _nova_data_health_os_20260703.environ.get("NOVA_SESSIONS_FILE")'
if needle not in text:
    raise SystemExit("could not find data health insertion point")

insert = '''
                # NOVA_RAILWAY_VOLUME_HEALTH_DIAGNOSTIC_20260703
                payload["railway_volume_name"] = _nova_data_health_os_20260703.environ.get("RAILWAY_VOLUME_NAME")
                payload["railway_volume_mount_path"] = _nova_data_health_os_20260703.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
'''

text = text.replace(needle, needle + "\n" + insert, 1)
path.write_text(text.rstrip() + "\n", encoding="utf-8")
print("installed railway volume health diagnostic")
