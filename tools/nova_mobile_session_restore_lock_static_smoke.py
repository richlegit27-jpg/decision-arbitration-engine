from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")

def main():
    js_path = ROOT / "static" / "js" / "mobile" / "nova-mobile-session-restore-lock.js"
    assert_true("session restore lock js exists", js_path.exists(), js_path)

    js = js_path.read_text(encoding="utf-8")
    assert_true("restore marker present", "__NOVA_MOBILE_SESSION_RESTORE_LOCK_20260702__" in js)
    assert_true("session detail endpoint used", "/api/sessions/" in js)
    assert_true("credentials include used", 'credentials: "include"' in js or "credentials = \"include\"" in js)
    assert_true("messages rendered from session detail", "normalizeMessages" in js and "clearAndRenderMessages" in js)
    assert_true("active session state updated", "nova_mobile_active_session_id" in js)
    assert_true("new chat debounce present", "blocked duplicate New Chat click" in js)

    wired = False
    for rel in ("templates/mobile.html", "templates/index-mobile.html"):
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "nova-mobile-session-restore-lock.js" in text:
            wired = True
            print(f"PASS wired in {rel}")

    assert_true("restore lock wired into a mobile template", wired)

    print("")
    print("NOVA MOBILE SESSION RESTORE LOCK STATIC SMOKE PASSED")

if __name__ == "__main__":
    main()
