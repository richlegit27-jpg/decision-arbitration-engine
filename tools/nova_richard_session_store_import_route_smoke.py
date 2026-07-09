from pathlib import Path

text = Path("app.py").read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

check("import route marker present", "NOVA_RICHARD_SESSION_STORE_IMPORT_ROUTE_20260703" in text)
check("import endpoint present", "/api/admin/session-store/import" in text)
check("richard auth guard present", '!= "richard"' in text)
check("confirmation guard present", "I_UNDERSTAND_IMPORT_LOCAL_NOVA_SESSIONS" in text)
check("previous owner preserved", "previous_owner_username" in text)
check("owner import source present", "session_store_import_20260703" in text)

print("")
print("NOVA RICHARD SESSION STORE IMPORT ROUTE SMOKE PASSED")
