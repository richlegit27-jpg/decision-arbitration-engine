from pathlib import Path

TEMPLATE = Path("templates/app.html")
MARKER = "NOVA_DESKTOP_EXECUTION_DOCK_TOP_VISIBLE_20260702"

if not TEMPLATE.exists():
    raise SystemExit(f"missing {TEMPLATE}")

text = TEMPLATE.read_text(encoding="utf-8-sig", errors="ignore")

# Change dock insertion from append bottom to insert at top.
text = text.replace(
    'host.appendChild(dockHost);',
    'host.insertBefore(dockHost, host.firstChild);'
)

style = r'''

<style id="nova-desktop-execution-dock-top-visible-20260702">
/* NOVA_DESKTOP_EXECUTION_DOCK_TOP_VISIBLE_20260702
   Put Execution at the top of the right tools panel and make it obvious.
*/
#nova-desktop-execution-dock-host {
    order: -9999 !important;
    margin: 0 0 12px 0 !important;
    padding: 0 !important;
}

#nova-desktop-execution-rail {
    border: 2px solid rgba(250, 204, 21, 0.92) !important;
    background: linear-gradient(180deg, rgba(30, 41, 59, 0.98), rgba(15, 23, 42, 0.98)) !important;
    box-shadow:
        0 0 0 3px rgba(250, 204, 21, 0.14),
        0 12px 30px rgba(0,0,0,0.32) !important;
}

#nova-desktop-execution-rail .nova-desktop-exec-head {
    background: linear-gradient(135deg, #facc15, #7c3aed) !important;
    color: #ffffff !important;
}

#nova-desktop-execution-rail .nova-desktop-exec-title::before {
    content: "⚙ " !important;
}

#nova-desktop-execution-rail .nova-desktop-exec-title {
    color: #ffffff !important;
    text-shadow: 0 1px 2px rgba(0,0,0,0.4) !important;
}

#nova-desktop-execution-rail .nova-desktop-exec-toggle {
    background: rgba(0,0,0,0.24) !important;
    color: #fff !important;
    border-color: rgba(255,255,255,0.45) !important;
}
</style>
'''

if MARKER not in text:
    idx = text.lower().rfind("</body>")
    if idx < 0:
        raise SystemExit("could not find </body>; not patching")
    text = text[:idx] + style + "\n" + text[idx:]

TEMPLATE.write_text(text, encoding="utf-8")
print("patched", TEMPLATE)
