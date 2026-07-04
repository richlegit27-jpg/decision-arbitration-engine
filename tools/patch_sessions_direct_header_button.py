from pathlib import Path

path = Path("static/js/mobile/nova-mobile-sessions-final-v2.js")
js = path.read_text(encoding="utf-8")

direct_function = r'''
    function installDirectHeaderButton() {
        var old = byId(HEADER_BUTTON_ID);

        if (!old) {
            return false;
        }

        if (old.dataset.novaMobileSessionsFinalV2Direct === "1") {
            return true;
        }

        var fresh = old.cloneNode(true);

        fresh.id = HEADER_BUTTON_ID;
        fresh.textContent = "Sessions";
        fresh.setAttribute("aria-label", "Sessions");
        fresh.dataset.novaMobileSessionsFinalV2Direct = "1";
        fresh.dataset.novaMobileSessionsFinalV2Bound = "1";

        fresh.style.pointerEvents = "auto";
        fresh.style.position = fresh.style.position || "relative";
        fresh.style.zIndex = "2147483645";

        fresh.onclick = function (event) {
            event.preventDefault();
            event.stopPropagation();

            openSessions("direct-cloned-header-button");

            return false;
        };

        fresh.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            openSessions("direct-cloned-header-button-capture");
        }, true);

        old.replaceWith(fresh);

        console.log("[Nova Mobile Sessions Final V2] direct cloned header button installed");

        return true;
    }

'''

if "function installDirectHeaderButton()" not in js:
    anchor = "    function bindHeader() {"
    js = js.replace(anchor, direct_function + anchor)

if "installDirectHeaderButton();" not in js:
    js = js.replace(
        '    bindHeader();\n    installDelegatedHeaderClick();',
        '    bindHeader();\n    installDelegatedHeaderClick();\n    installDirectHeaderButton();'
    )

if 'setTimeout(installDirectHeaderButton, 250);' not in js:
    js = js.replace(
        '    setTimeout(bindHeader, 250);\n    setTimeout(bindHeader, 1000);\n    setTimeout(bindHeader, 2500);',
        '    setTimeout(bindHeader, 250);\n    setTimeout(installDirectHeaderButton, 250);\n    setTimeout(bindHeader, 1000);\n    setTimeout(installDirectHeaderButton, 1000);\n    setTimeout(bindHeader, 2500);\n    setTimeout(installDirectHeaderButton, 2500);'
    )

path.write_text(js, encoding="utf-8")
