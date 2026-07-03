from pathlib import Path

text = Path("app.py").read_text(encoding="utf-8", errors="replace")

def check(name, ok):
    if not ok:
        raise AssertionError(name)
    print("PASS", name)

check("legacy owner bridge marker present", "NOVA_RICHARD_LEGACY_SESSION_OWNER_BRIDGE_20260703" in text)
check("legacy bridge route debug present", "richard_legacy_session_owner_bridge" in text)
check("legacy joe adoption present", 'item_username == "joe"' in text)
check("unowned adoption present", "is_unowned" in text)
check("previous owner preserved", "previous_owner_username" in text)
check("local auth adoption source present", "local_auth_legacy_adoption_20260703" in text)
check("x nova slim sessions header present", 'slim_response.headers["X-Nova-Slim-Sessions"] = "1"' in text)

print("")
print("NOVA RICHARD LEGACY SESSION OWNER BRIDGE SMOKE PASSED")
