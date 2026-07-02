from pathlib import Path

TEMPLATE = Path("templates/app.html")
MARKER = "NOVA_DESKTOP_EXECUTION_RAIL_FORCE_VISIBLE_20260702"

style = r'''

<style id="nova-desktop-execution-rail-force-visible-20260702">
/* NOVA_DESKTOP_EXECUTION_RAIL_FORCE_VISIBLE_20260702
   Beat old desktop CSS that hides .execution-panel / [data-execution-panel].
*/
#nova-desktop-execution-rail,
section#nova-desktop-execution-rail,
body #nova-desktop-execution-rail[data-rail-panel="execution"] {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
}

#nova-desktop-execution-rail [data-execution-panel],
body #nova-desktop-execution-rail [data-execution-panel] {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
}
</style>
'''

if not TEMPLATE.exists():
    raise SystemExit(f"missing {TEMPLATE}")

text = TEMPLATE.read_text(encoding="utf-8-sig", errors="ignore")

if MARKER in text:
    print("already patched", TEMPLATE)
else:
    idx = text.lower().rfind("</body>")
    if idx < 0:
        raise SystemExit("could not find </body>; not patching")

    text = text[:idx] + style + "\n" + text[idx:]
    TEMPLATE.write_text(text, encoding="utf-8")
    print("patched", TEMPLATE)
