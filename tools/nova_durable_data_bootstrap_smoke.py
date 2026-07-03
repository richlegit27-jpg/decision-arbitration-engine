from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app = ROOT / "app.py"

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

text = app.read_text(encoding="utf-8")

check("durable bootstrap marker present", "NOVA_DURABLE_DATA_BOOTSTRAP_20260703" in text)
check("storage health route marker present", "NOVA_DURABLE_DATA_HEALTH_ROUTE_20260703" in text)
check("NOVA_DATA_DIR configured", 'os.environ["NOVA_DATA_DIR"]' in text)
check("Railway /data candidate present", 'Path("/data")' in text)
check("/app/data symlink bridge present", "symlink_to(chosen" in text)
check("storage health endpoint present", '@app.get("/api/storage/health")' in text)
check("auth users checked", "nova_auth_users.json" in text)
check("sessions checked", "nova_sessions.json" in text)
check("secret checked", "nova_flask_secret.key" in text)

print("")
print("NOVA DURABLE DATA BOOTSTRAP SMOKE PASSED")
