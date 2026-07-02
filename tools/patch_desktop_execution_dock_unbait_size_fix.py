from pathlib import Path

TEMPLATE = Path("templates/app.html")
MARKER = "NOVA_DESKTOP_EXECUTION_DOCK_UNBAIT_SIZE_FIX_20260702"

if not TEMPLATE.exists():
    raise SystemExit(f"missing {TEMPLATE}")

text = TEMPLATE.read_text(encoding="utf-8-sig", errors="ignore")

# Remove old desktop selector bait from the restored rail.
text = text.replace(
    'class="nova-desktop-execution-rail desktop-execution execution-section"',
    'class="nova-desktop-execution-card"'
)

text = text.replace(
    'class="nova-desktop-execution-rail desktop-execution execution-section nova-exec-docked-right"',
    'class="nova-desktop-execution-card nova-exec-docked-right"'
)

# Keep the panel content marker, but stop using old rail data selector bait.
text = text.replace(
    'data-rail-panel="execution"\n    aria-label="Execution Panel"',
    'data-nova-execution-rail="desktop"\n    aria-label="Execution Panel"'
)

style = r'''

<style id="nova-desktop-execution-dock-unbait-size-fix-20260702">
/* NOVA_DESKTOP_EXECUTION_DOCK_UNBAIT_SIZE_FIX_20260702
   Make the restored desktop execution card fit inside ASIDE.panel.tools.
   Avoid old .execution-panel / [data-rail-panel="execution"] kill rules.
*/
#nova-desktop-execution-dock-host {
    display: block !important;
    width: 100% !important;
    min-width: 260px !important;
    min-height: 198px !important;
    box-sizing: border-box !important;
    flex: 0 0 auto !important;
    align-self: stretch !important;
    overflow: visible !important;
}

#nova-desktop-execution-rail,
#nova-desktop-execution-rail.nova-desktop-execution-card,
#nova-desktop-execution-rail.nova-exec-docked-right {
    display: block !important;
    position: relative !important;
    left: auto !important;
    right: auto !important;
    top: auto !important;
    bottom: auto !important;
    width: 100% !important;
    min-width: 260px !important;
    max-width: 100% !important;
    height: auto !important;
    min-height: 198px !important;
    max-height: none !important;
    margin: 10px 0 !important;
    padding: 0 !important;
    box-sizing: border-box !important;
    visibility: visible !important;
    opacity: 1 !important;
    overflow: visible !important;
    contain: none !important;
    transform: none !important;
    pointer-events: auto !important;
}

#nova-desktop-execution-rail .nova-desktop-exec-head,
#nova-desktop-execution-rail .nova-desktop-exec-body,
#nova-desktop-execution-rail [data-execution-panel],
#nova-desktop-execution-rail .nova-desktop-exec-actions {
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
    visibility: visible !important;
    opacity: 1 !important;
}

#nova-desktop-execution-rail .nova-desktop-exec-head {
    display: flex !important;
    min-height: 46px !important;
}

#nova-desktop-execution-rail .nova-desktop-exec-body {
    display: block !important;
    min-height: 130px !important;
}

#nova-desktop-execution-rail [data-execution-panel] {
    display: block !important;
    min-height: 64px !important;
}

#nova-desktop-execution-rail .nova-desktop-exec-actions {
    display: grid !important;
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
    min-height: 42px !important;
}

#nova-desktop-execution-rail button,
#nova-desktop-execution-rail .nova-panel-muted,
#nova-desktop-execution-rail strong {
    visibility: visible !important;
    opacity: 1 !important;
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
