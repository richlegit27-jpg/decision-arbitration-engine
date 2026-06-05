import importlib.util
from pathlib import Path

app_path = Path(r"C:\Users\Owner\nova\app.py")

spec = importlib.util.spec_from_file_location("nova_root_app", app_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

app = getattr(mod, "app", None)
if app is None:
    raise SystemExit("FAILED: app object not found in app.py")

client = app.test_client()
rv = client.get("/mobile")

html = rv.data.decode("utf-8", errors="ignore")
print("STATUS:", rv.status_code)
print(html[:2000])
