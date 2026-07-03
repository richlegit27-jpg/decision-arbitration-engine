from pathlib import Path

js_path = Path("static/js/mobile/nova-mobile-sessions-rescue-final-v1.js")
template_path = Path("templates/mobile.html")

js = js_path.read_text(encoding="utf-8", errors="replace")
template = template_path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V3_BODY_UNHIDE_20260703"

if marker in js and "sessions-rescue-final-v3-body-unhide-20260703" in template:
    print("sessions rescue body unhide v3 already installed")
    raise SystemExit(0)

if marker not in js:
    helper = '''
    function restoreBodyVisibility(reason) {
        /* NOVA_MOBILE_SESSIONS_RESCUE_FINAL_V3_BODY_UNHIDE_20260703 */
        var body = document.body;
        if (!body) return;

        body.removeAttribute("hidden");

        if (body.getAttribute("aria-hidden") === "true") {
            body.removeAttribute("aria-hidden");
        }

        body.style.removeProperty("display");
        body.style.removeProperty("visibility");
        body.style.removeProperty("opacity");
        body.style.removeProperty("pointer-events");

        if (getComputedStyle(body).display === "none") {
            body.style.setProperty("display", "block", "important");
        }

        if (getComputedStyle(body).visibility === "hidden") {
            body.style.setProperty("visibility", "visible", "important");
        }

        if (getComputedStyle(body).opacity === "0") {
            body.style.setProperty("opacity", "1", "important");
        }

        body.style.setProperty("pointer-events", "auto", "important");
        body.dataset.novaSessionsBodyRestored = reason || "unknown";
    }

'''

    needle = "    function showMainLayout() {\n"
    if needle not in js:
        raise SystemExit("could not find showMainLayout anchor")
    js = js.replace(needle, helper + needle, 1)

    old = '''        var panel = getPanel();

        panel.classList.add("hidden");
'''
    new = '''        var panel = getPanel();

        restoreBodyVisibility("close-before");

        if (document.activeElement && panel.contains(document.activeElement)) {
            try {
                document.activeElement.blur();
            } catch (e) {}
        }

        panel.removeAttribute("hidden");
        panel.classList.add("hidden");
'''
    if old not in js:
        raise SystemExit("could not patch closePanel body guard")
    js = js.replace(old, new, 1)

    old = '''    function openPanel() {
        addStyle();

        var panel = getPanel();

        panel.classList.remove("hidden");
'''
    new = '''    function openPanel() {
        addStyle();
        restoreBodyVisibility("open-before");

        var panel = getPanel();
        ensurePanelMarkup(panel);

        panel.removeAttribute("hidden");
        panel.classList.remove("hidden");
'''
    if old not in js:
        raise SystemExit("could not patch openPanel body guard")
    js = js.replace(old, new, 1)

    old = '''        if (document.body) {
            document.body.classList.add("nova-mobile-sessions-open");
        }

        loadSessions();
    }
'''
    new = '''        if (document.body) {
            document.body.classList.add("nova-mobile-sessions-open");
        }

        restoreBodyVisibility("open-after");
        loadSessions();
    }
'''
    if old not in js:
        raise SystemExit("could not patch openPanel restore after")
    js = js.replace(old, new, 1)

    old = '''    function ensureButton() {
        addStyle();

        var button = findExistingButton();
'''
    new = '''    function ensureButton() {
        addStyle();
        restoreBodyVisibility("ensure-button");

        var button = findExistingButton();
'''
    if old not in js:
        raise SystemExit("could not patch ensureButton body guard")
    js = js.replace(old, new, 1)

    old = '''    function boot() {
        ensureButton();
        closePanel();
    }
'''
    new = '''    function boot() {
        restoreBodyVisibility("boot-start");
        ensureButton();
        closePanel();
        restoreBodyVisibility("boot-end");
    }
'''
    if old not in js:
        raise SystemExit("could not patch boot body guard")
    js = js.replace(old, new, 1)

    old = "    setInterval(ensureButton, 1500);"
    new = '''    setInterval(function () {
        restoreBodyVisibility("interval");
        ensureButton();
    }, 1500);'''
    if old not in js:
        raise SystemExit("could not patch interval body guard")
    js = js.replace(old, new, 1)

    js_path.write_text(js.rstrip() + "\n", encoding="utf-8")
    print("patched body unhide guard:", js_path)

old_url = "/static/js/mobile/nova-mobile-sessions-rescue-final-v1.js?v=sessions-rescue-final-v2-panel-markup-20260703"
new_url = "/static/js/mobile/nova-mobile-sessions-rescue-final-v1.js?v=sessions-rescue-final-v3-body-unhide-20260703"

if new_url not in template:
    if old_url not in template:
        raise SystemExit("old v2 rescue script URL not found in template")
    template = template.replace(old_url, new_url, 1)
    template_path.write_text(template.rstrip() + "\n", encoding="utf-8")
    print("patched template cache bust to v3:", template_path)
