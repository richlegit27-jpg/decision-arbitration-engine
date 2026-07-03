from pathlib import Path

text = Path("app.py").read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

check("railway volume diagnostic marker present", "NOVA_RAILWAY_VOLUME_HEALTH_DIAGNOSTIC_20260703" in text)
check("health exposes railway volume name", "railway_volume_name" in text)
check("health exposes railway volume mount path", "railway_volume_mount_path" in text)

print("")
print("NOVA RAILWAY VOLUME HEALTH DIAGNOSTIC SMOKE PASSED")
