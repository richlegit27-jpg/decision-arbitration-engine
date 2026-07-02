from pathlib import Path

TEMPLATE = Path("templates/app.html")
MARKER = "NOVA_DESKTOP_EXECUTION_RAIL_HEIGHT_FIX_20260702"

if not TEMPLATE.exists():
    raise SystemExit(f"missing {TEMPLATE}")

text = TEMPLATE.read_text(encoding="utf-8-sig", errors="ignore")

# Remove broad class that old CSS may target.
text = text.replace(
    'class="execution-panel desktop-execution execution-section"',
    'class="nova-desktop-execution-rail desktop-execution execution-section"'
)

style = r'''

<style id="nova-desktop-execution-rail-height-fix-20260702">
/* NOVA_DESKTOP_EXECUTION_RAIL_HEIGHT_FIX_20260702
   Prevent old desktop execution-panel kill rules from collapsing the restored rail.
*/
#nova-desktop-execution-rail {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    height: auto !important;
    min-height: 178px !important;
    max-height: 70vh !important;
    overflow: visible !important;
}

#nova-desktop-execution-rail .nova-desktop-exec-head {
    display: flex !important;
    min-height: 46px !important;
    visibility: visible !important;
    opacity: 1 !important;
}

#nova-desktop-execution-rail .nova-desktop-exec-body {
    display: block !important;
    min-height: 112px !important;
    visibility: visible !important;
    opacity: 1 !important;
}

#nova-desktop-execution-rail [data-execution-panel] {
    display: block !important;
    min-height: 62px !important;
    visibility: visible !important;
    opacity: 1 !important;
}

#nova-desktop-execution-rail .nova-desktop-exec-actions {
    display: grid !important;
    min-height: 42px !important;
    visibility: visible !important;
    opacity: 1 !important;
}

#nova-desktop-execution-rail button,
#nova-desktop-execution-rail .nova-panel-muted,
#nova-desktop-execution-rail strong {
    display: revert !important;
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
