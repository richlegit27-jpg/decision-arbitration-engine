from pathlib import Path

path = Path("static/js/mobile/nova-mobile-sessions-rescue-final-v1.js")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V2_PANEL_MARKUP_20260703"

if marker in text:
    print("sessions rescue panel markup patch already installed")
    raise SystemExit(0)

helper = '''
    function ensurePanelMarkup(panel) {
        /* NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V2_PANEL_MARKUP_20260703 */
        if (!panel) return;

        var existingList = panel.querySelector("#nova-mobile-sessions-rescue-list");
        var existingClose = panel.querySelector(".nova-sessions-rescue-close");

        if (existingList && existingClose) {
            return;
        }

        panel.innerHTML = `
            <div class="nova-sessions-rescue-header">
                <div class="nova-sessions-rescue-title">Sessions</div>
                <button type="button" class="nova-sessions-rescue-close" data-action="close-sessions">Close</button>
            </div>
            <div id="nova-mobile-sessions-rescue-list">Loading sessions...</div>
        `;
    }

'''

needle = "    function getPanel() {\n"

if needle not in text:
    raise SystemExit("could not find getPanel function")

text = text.replace(needle, helper + needle, 1)

old_existing = '''        if (panel) {
            if (!panel.id) panel.id = "nova-mobile-sessions-panel";
            return panel;
        }
'''

new_existing = '''        if (panel) {
            if (!panel.id) panel.id = "nova-mobile-sessions-panel";
            ensurePanelMarkup(panel);
            return panel;
        }
'''

if old_existing not in text:
    raise SystemExit("could not find existing panel return block")

text = text.replace(old_existing, new_existing, 1)

old_new_panel = '''        document.body.appendChild(panel);
        return panel;
'''

new_new_panel = '''        document.body.appendChild(panel);
        ensurePanelMarkup(panel);
        return panel;
'''

if old_new_panel not in text:
    raise SystemExit("could not find new panel append return block")

text = text.replace(old_new_panel, new_new_panel, 1)

path.write_text(text.rstrip() + "\n", encoding="utf-8")
print("patched:", path)
