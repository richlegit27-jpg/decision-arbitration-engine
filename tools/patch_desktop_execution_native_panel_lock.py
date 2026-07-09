from pathlib import Path

TEMPLATE = Path("templates/app.html")
MARKER = "NOVA_DESKTOP_EXECUTION_NATIVE_PANEL_LOCK_20260702"

style = r'''

<style id="nova-desktop-execution-native-panel-lock-20260702">
/* NOVA_DESKTOP_EXECUTION_NATIVE_PANEL_LOCK_20260702
   Make native Execution behave like a real card inside the right tools panel.
*/
aside.panel.tools {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 12px !important;
    box-sizing: border-box !important;
}

aside.panel.tools > #nova-desktop-execution-native,
#nova-desktop-execution-native {
    position: static !important;
    inset: auto !important;
    transform: none !important;
    float: none !important;
    clear: both !important;
    flex: 0 0 auto !important;
    align-self: stretch !important;
    order: -100 !important;

    display: block !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    height: auto !important;
    min-height: 160px !important;
    box-sizing: border-box !important;

    margin: 0 0 12px 0 !important;
    padding: 12px !important;

    border: 1px solid rgba(148, 163, 184, 0.22) !important;
    border-radius: 16px !important;
    background: rgba(15, 23, 42, 0.88) !important;
    box-shadow: none !important;
    outline: none !important;

    overflow: hidden !important;
    color: #e5e7eb !important;
    z-index: auto !important;
}

#nova-desktop-execution-native .panel-section-title {
    display: flex !important;
    align-items: center !important;
    min-height: 24px !important;
    margin: 0 0 10px 0 !important;
    padding: 0 !important;
    color: #facc15 !important;
    font-size: 13px !important;
    font-weight: 900 !important;
}

#nova-desktop-execution-native [data-execution-panel] {
    display: block !important;
    width: 100% !important;
    min-height: 64px !important;
    box-sizing: border-box !important;
    margin: 0 !important;
    padding: 10px !important;
    border-radius: 12px !important;
    background: rgba(255, 255, 255, 0.055) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    color: #dbeafe !important;
    overflow: hidden !important;
}

#nova-desktop-execution-native .nova-desktop-execution-native-actions {
    display: grid !important;
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
    gap: 8px !important;
    width: 100% !important;
    margin-top: 10px !important;
    box-sizing: border-box !important;
}

#nova-desktop-execution-native button {
    width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
}
</style>
'''

if not TEMPLATE.exists():
    raise SystemExit(f"missing {TEMPLATE}")

text = TEMPLATE.read_text(encoding="utf-8-sig", errors="ignore")

if "nova-desktop-execution-native" not in text:
    raise SystemExit("native execution panel is missing; run native tools panel patch first")

if MARKER in text:
    print("already patched", TEMPLATE)
else:
    idx = text.lower().rfind("</body>")
    if idx < 0:
        raise SystemExit("could not find </body>; not patching")

    text = text[:idx] + style + "\n" + text[idx:]
    TEMPLATE.write_text(text, encoding="utf-8")
    print("patched", TEMPLATE)
