from pathlib import Path

TEMPLATE = Path("templates/app.html")
MARKER = "NOVA_DESKTOP_EXECUTION_NATIVE_BOTTOM_TOOLS_20260702"

style = r'''

<style id="nova-desktop-execution-native-bottom-tools-20260702">
/* NOVA_DESKTOP_EXECUTION_NATIVE_BOTTOM_TOOLS_20260702
   Keep Execution native inside the tools rail, but place it at the bottom.
*/
aside.panel.tools {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
}

aside.panel.tools > #nova-desktop-execution-native,
#nova-desktop-execution-native {
    order: 9999 !important;
    margin-top: auto !important;
    margin-bottom: 0 !important;
    flex: 0 0 auto !important;
    align-self: stretch !important;
    position: static !important;
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
}
</style>
'''

if not TEMPLATE.exists():
    raise SystemExit(f"missing {TEMPLATE}")

text = TEMPLATE.read_text(encoding="utf-8-sig", errors="ignore")

if "nova-desktop-execution-native" not in text:
    raise SystemExit("native execution panel missing; not patching")

if MARKER in text:
    print("already patched", TEMPLATE)
else:
    idx = text.lower().rfind("</body>")
    if idx < 0:
        raise SystemExit("could not find </body>; not patching")
    text = text[:idx] + style + "\n" + text[idx:]
    TEMPLATE.write_text(text, encoding="utf-8")
    print("patched", TEMPLATE)
