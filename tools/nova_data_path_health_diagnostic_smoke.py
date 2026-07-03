from pathlib import Path

text = Path("app.py").read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

check("data path diagnostic marker present", "NOVA_DATA_PATH_HEALTH_DIAGNOSTIC_20260703" in text)
check("health exposes NOVA_DATA_DIR", "nova_data_dir_env" in text)
check("health exposes NOVA_SESSIONS_FILE", "nova_sessions_file_env" in text)
check("health exposes sessions file size", "sessions_file_size" in text)

print("")
print("NOVA DATA PATH HEALTH DIAGNOSTIC SMOKE PASSED")
