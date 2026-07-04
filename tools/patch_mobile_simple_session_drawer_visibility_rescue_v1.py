from pathlib import Path

path = Path("static/js/mobile/nova-mobile-simple-session-drawer-v1.js")
text = path.read_text(encoding="utf-8")

if "function forceVisibleButton()" not in text:
    anchor = '''    function closePanel() {
        const panel = document.getElementById("nova-simple-sessions-panel-v1");
        if (panel) {
            panel.style.display = "none";
        }
    }
'''

    insert = anchor + '''
    function forceVisibleButton() {
        const btn = document.getElementById("nova-simple-sessions-button-v1");

        if (!btn) {
            return;
        }

        btn.removeAttribute("data-nova-hidden-by-session-owner");
        btn.removeAttribute("data-nova-hidden-by-sessions-final");
        btn.removeAttribute("hidden");
        btn.disabled = false;

        btn.style.setProperty("display", "inline-flex", "important");
        btn.style.setProperty("pointer-events", "auto", "important");
        btn.style.setProperty("visibility", "visible", "important");
        btn.style.setProperty("opacity", "1", "important");
        btn.style.setProperty("align-items", "center", "important");
        btn.style.setProperty("justify-content", "center", "important");
        btn.style.setProperty("position", "fixed", "important");
        btn.style.setProperty("left", "10px", "important");
        btn.style.setProperty("top", "10px", "important");
        btn.style.setProperty("z-index", "2147483647", "important");
    }

    function installVisibilityRescue() {
        forceVisibleButton();

        setTimeout(forceVisibleButton, 50);
        setTimeout(forceVisibleButton, 250);
        setTimeout(forceVisibleButton, 750);
        setTimeout(forceVisibleButton, 1500);

        window.setInterval(forceVisibleButton, 1000);

        try {
            const observer = new MutationObserver(function () {
                forceVisibleButton();
            });

            observer.observe(document.documentElement, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ["style", "hidden", "data-nova-hidden-by-session-owner", "data-nova-hidden-by-sessions-final"]
            });
        } catch (_) {}
    }
'''

    if anchor not in text:
        raise SystemExit("Could not find closePanel anchor.")

    text = text.replace(anchor, insert, 1)

text = text.replace(
'''        document.body.appendChild(btn);
        return btn;
''',
'''        document.body.appendChild(btn);
        forceVisibleButton();
        return btn;
''',
1
)

text = text.replace(
'''    function boot() {
        makeButton();
        console.error("[Nova Simple Sessions] installed");
    }
''',
'''    function boot() {
        makeButton();
        installVisibilityRescue();
        console.error("[Nova Simple Sessions] installed");
    }
''',
1
)

path.write_text(text, encoding="utf-8")
print("Patched simple session drawer visibility rescue.")
