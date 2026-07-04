from pathlib import Path

path = Path("static/js/mobile/nova-mobile-simple-session-drawer-v1.js")
text = path.read_text(encoding="utf-8")

if "function forceVisibleRows()" not in text:
    anchor = '''    function rescueOpenPanelSoon() {
        forceVisiblePanel();
        setTimeout(forceVisiblePanel, 25);
        setTimeout(forceVisiblePanel, 100);
        setTimeout(forceVisiblePanel, 300);
        setTimeout(forceVisiblePanel, 700);
        setTimeout(forceVisiblePanel, 1200);
    }
'''

    insert = '''    function forceVisibleRows() {
        const panel = document.getElementById("nova-simple-sessions-panel-v1");

        if (!panel) {
            return;
        }

        panel.querySelectorAll("[role='button']").forEach(function (row) {
            row.removeAttribute("hidden");
            row.removeAttribute("data-nova-hidden-by-session-owner");
            row.removeAttribute("data-nova-hidden-by-sessions-final");
            row.disabled = false;

            row.style.setProperty("display", "block", "important");
            row.style.setProperty("pointer-events", "auto", "important");
            row.style.setProperty("visibility", "visible", "important");
            row.style.setProperty("opacity", "1", "important");
            row.style.setProperty("position", "relative", "important");
            row.style.setProperty("z-index", "2147483647", "important");
        });
    }

''' + anchor.replace(
        "forceVisiblePanel();",
        "forceVisiblePanel();\n        forceVisibleRows();"
    ).replace(
        "setTimeout(forceVisiblePanel, 25);",
        "setTimeout(function () { forceVisiblePanel(); forceVisibleRows(); }, 25);"
    ).replace(
        "setTimeout(forceVisiblePanel, 100);",
        "setTimeout(function () { forceVisiblePanel(); forceVisibleRows(); }, 100);"
    ).replace(
        "setTimeout(forceVisiblePanel, 300);",
        "setTimeout(function () { forceVisiblePanel(); forceVisibleRows(); }, 300);"
    ).replace(
        "setTimeout(forceVisiblePanel, 700);",
        "setTimeout(function () { forceVisiblePanel(); forceVisibleRows(); }, 700);"
    ).replace(
        "setTimeout(forceVisiblePanel, 1200);",
        "setTimeout(function () { forceVisiblePanel(); forceVisibleRows(); }, 1200);"
    )

    if anchor not in text:
        raise SystemExit("Could not find rescueOpenPanelSoon anchor.")

    text = text.replace(anchor, insert, 1)

text = text.replace(
'''        window.setInterval(function () {
            forceVisibleButton();
            forceVisiblePanel();
        }, 1000);
''',
'''        window.setInterval(function () {
            forceVisibleButton();
            forceVisiblePanel();
            forceVisibleRows();
        }, 1000);
''',
1
)

text = text.replace(
'''            panel.appendChild(list);
''',
'''            panel.appendChild(list);
            forceVisibleRows();
''',
1
)

path.write_text(text, encoding="utf-8")
print("Patched simple session drawer row visibility rescue.")
