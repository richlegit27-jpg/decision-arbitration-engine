from pathlib import Path

path = Path("static/js/mobile/nova-mobile-simple-session-drawer-v1.js")
text = path.read_text(encoding="utf-8")

if "let simpleSessionPanelOpen = false;" not in text:
    text = text.replace(
'''    window[MARK] = true;
''',
'''    window[MARK] = true;

    let simpleSessionPanelOpen = false;
''',
1
)

if "function forceVisiblePanel()" not in text:
    anchor = '''    function forceVisibleButton() {
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
'''

    insert = anchor + '''
    function forceVisiblePanel() {
        const panel = document.getElementById("nova-simple-sessions-panel-v1");

        if (!panel || !simpleSessionPanelOpen) {
            return;
        }

        panel.removeAttribute("hidden");
        panel.removeAttribute("data-nova-hidden-by-session-owner");
        panel.removeAttribute("data-nova-hidden-by-sessions-final");

        panel.style.setProperty("display", "block", "important");
        panel.style.setProperty("pointer-events", "auto", "important");
        panel.style.setProperty("visibility", "visible", "important");
        panel.style.setProperty("opacity", "1", "important");
        panel.style.setProperty("position", "fixed", "important");
        panel.style.setProperty("left", "10px", "important");
        panel.style.setProperty("right", "10px", "important");
        panel.style.setProperty("top", "56px", "important");
        panel.style.setProperty("z-index", "2147483647", "important");
    }

    function rescueOpenPanelSoon() {
        forceVisiblePanel();
        setTimeout(forceVisiblePanel, 25);
        setTimeout(forceVisiblePanel, 100);
        setTimeout(forceVisiblePanel, 300);
        setTimeout(forceVisiblePanel, 700);
        setTimeout(forceVisiblePanel, 1200);
    }
'''

    if anchor not in text:
        raise SystemExit("Could not find forceVisibleButton anchor.")

    text = text.replace(anchor, insert, 1)

text = text.replace(
'''    function closePanel() {
        const panel = document.getElementById("nova-simple-sessions-panel-v1");
        if (panel) {
            panel.style.display = "none";
        }
    }
''',
'''    function closePanel() {
        simpleSessionPanelOpen = false;

        const panel = document.getElementById("nova-simple-sessions-panel-v1");
        if (panel) {
            panel.style.setProperty("display", "none", "important");
        }
    }
''',
1
)

text = text.replace(
'''        panel.style.display = "block";
        panel.innerHTML = "<div style='padding:10px;'>Loading sessions...</div>";
''',
'''        simpleSessionPanelOpen = true;
        panel.style.setProperty("display", "block", "important");
        panel.innerHTML = "<div style='padding:10px;'>Loading sessions...</div>";
        rescueOpenPanelSoon();
''',
1
)

text = text.replace(
'''            console.error("[Nova Simple Sessions] rendered", {
                count: data.sessions.length,
                activeSessionId: data.activeSessionId,
                currentId: currentId
            });
''',
'''            rescueOpenPanelSoon();

            console.error("[Nova Simple Sessions] rendered", {
                count: data.sessions.length,
                activeSessionId: data.activeSessionId,
                currentId: currentId
            });
''',
1
)

text = text.replace(
'''        window.setInterval(forceVisibleButton, 1000);
''',
'''        window.setInterval(function () {
            forceVisibleButton();
            forceVisiblePanel();
        }, 1000);
''',
1
)

text = text.replace(
'''                forceVisibleButton();
''',
'''                forceVisibleButton();
                forceVisiblePanel();
''',
1
)

path.write_text(text, encoding="utf-8")
print("Patched simple session drawer panel visibility rescue.")
