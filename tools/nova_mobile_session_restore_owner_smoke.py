from pathlib import Path


path = Path("static/js/mobile/nova-mobile-sessions.js")
text = path.read_text(encoding="utf-8", errors="ignore")


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA MOBILE SESSION RESTORE OWNER SMOKE")
    print(f"File: {path}")
    print("")

    assert_true("sessions file exists", path.exists())
    assert_true("main controller present", "window.__NOVA_SESSION_CONTROLLER_V2__" in text)
    assert_true("main open owner present", "async open(sessionId)" in text)
    assert_true("main render owner present", "render(sessionId, data)" in text)
    assert_true("main session fetch present", "/api/sessions/${encodeURIComponent(clean)}" in text)

    marker = "// NOVA_MOBILE_SESSION_MESSAGE_RESTORE_20260630"
    disabled = "[NOVA_MOBILE_SESSION_MESSAGE_RESTORE_20260630] disabled - owned by main Controller.open render"

    assert_true("duplicate restore marker still visible", marker in text)
    assert_true("duplicate restore layer disabled", disabled in text)

    marker_index = text.index(marker)
    disabled_index = text.index(disabled)
    assert_true(
        "disable happens inside duplicate restore layer",
        marker_index < disabled_index,
        f"marker={marker_index} disabled={disabled_index}",
    )

    print("")
    print("NOVA MOBILE SESSION RESTORE OWNER SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
