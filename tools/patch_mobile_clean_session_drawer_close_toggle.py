from pathlib import Path

path = Path("static/js/mobile/nova-mobile-simple-session-drawer-v1.js")
text = path.read_text(encoding="utf-8")

old_close = '''    function closePanel() {
        panelOpen = false;

        const panel = document.getElementById(PANEL_ID);

        if (panel) {
            panel.style.setProperty("display", "none", "important");
        }
    }
'''

new_close = '''    function closePanel() {
        panelOpen = false;

        const panel = document.getElementById(PANEL_ID);

        if (panel) {
            panel.style.setProperty("display", "none", "important");
            panel.style.setProperty("pointer-events", "none", "important");
            panel.style.setProperty("visibility", "hidden", "important");
            panel.style.setProperty("opacity", "0", "important");
        }
    }

    function isPanelOpenVisible() {
        const panel = document.getElementById(PANEL_ID);

        if (!panel || !panelOpen) {
            return false;
        }

        const style = getComputedStyle(panel);

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            style.opacity !== "0"
        );
    }
'''

if old_close not in text:
    raise SystemExit("Could not find closePanel block.")

text = text.replace(old_close, new_close, 1)

old_click = '''        btn.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            renderDrawer();
        });
'''

new_click = '''        btn.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            if (isPanelOpenVisible()) {
                closePanel();
                return;
            }

            renderDrawer();
        });
'''

if old_click not in text:
    raise SystemExit("Could not find launcher click block.")

text = text.replace(old_click, new_click, 1)

text = text.replace(
    'const MARK = "NOVA_MOBILE_CLEAN_SESSION_DRAWER_V3_FAST_ENDPOINTS_20260704";',
    'const MARK = "NOVA_MOBILE_CLEAN_SESSION_DRAWER_V3_CLOSE_TOGGLE_20260704";',
    1
)

text = text.replace(
    'version: "clean-v3-fast-endpoints"',
    'version: "clean-v3-close-toggle"',
    1
)

text = text.replace(
    'console.error("[Nova Clean Sessions V3 Fast Endpoints] installed");',
    'console.error("[Nova Clean Sessions V3 Close Toggle] installed");',
    1
)

path.write_text(text, encoding="utf-8")
print("Patched clean session drawer close/toggle behavior.")
