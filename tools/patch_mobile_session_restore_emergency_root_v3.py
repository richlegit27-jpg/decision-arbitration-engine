from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-session-restore-lock.js")
text = js_path.read_text(encoding="utf-8")

text = re.sub(
    r'const VERSION = "session-restore-lock[^"]*";',
    'const VERSION = "session-restore-lock-dom-root-v3";',
    text,
)

if "__NOVA_MOBILE_SESSION_RESTORE_EMERGENCY_ROOT_V3__" not in text:
    text = text.replace(
        "window.__NOVA_MOBILE_SESSION_RESTORE_LOCK_20260702__ = true;",
        "window.__NOVA_MOBILE_SESSION_RESTORE_LOCK_20260702__ = true;\n"
        "    window.__NOVA_MOBILE_SESSION_RESTORE_DOM_ROOT_V2__ = true;\n"
        "    window.__NOVA_MOBILE_SESSION_RESTORE_EMERGENCY_ROOT_V3__ = true;",
    )

emergency = r'''
    function createEmergencyChatRoot() {
        let root = document.getElementById("nova-mobile-restored-session-messages");

        if (root) {
            return root;
        }

        root = document.createElement("div");
        root.id = "nova-mobile-restored-session-messages";
        root.className = "nova-mobile-restored-session-messages nova-mobile-messages chat-messages";
        root.setAttribute("data-nova-chat-messages", "true");
        root.setAttribute("data-session-restore-emergency-root", "true");
        root.style.cssText = [
            "box-sizing:border-box",
            "width:100%",
            "min-height:45vh",
            "max-height:calc(100vh - 170px)",
            "overflow-y:auto",
            "-webkit-overflow-scrolling:touch",
            "padding:12px",
            "display:flex",
            "flex-direction:column",
            "gap:10px"
        ].join(";");

        const composer = document.querySelector(
            "#composer, #mobile-composer, #nova-composer, #nova-mobile-composer, .composer, .mobile-composer, .nova-composer, .nova-mobile-composer, form textarea, textarea"
        );

        const anchor = composer && composer.closest
            ? composer.closest("form, footer, .composer, .mobile-composer, .nova-composer, .nova-mobile-composer")
            : null;

        if (anchor && anchor.parentNode) {
            anchor.parentNode.insertBefore(root, anchor);
        } else {
            const main = document.querySelector("main") || document.body;
            main.appendChild(root);
        }

        log("created emergency chat root", root);
        return root;
    }

'''

if "function createEmergencyChatRoot()" not in text:
    text = text.replace(
        "    function clearAndRenderMessages(messages) {",
        emergency + "    function clearAndRenderMessages(messages) {",
    )

text = text.replace(
    "        const root = findChatRoot();\n\n        if (!root) {",
    "        let root = findChatRoot();\n\n"
    "        if (!root) {\n"
    "            root = createEmergencyChatRoot();\n"
    "        }\n\n"
    "        if (!root) {",
)

text = text.replace(
    "        let root = findChatRoot();\n\n        if (!root) {\n            warn(\"chat root not found; cannot render restored messages\");",
    "        let root = findChatRoot();\n\n"
    "        if (!root) {\n"
    "            root = createEmergencyChatRoot();\n"
    "        }\n\n"
    "        if (!root) {\n"
    "            warn(\"chat root not found after emergency root; cannot render restored messages\");",
)

js_path.write_text(text, encoding="utf-8")
print("patched", js_path)

for html_path in Path("templates").glob("*.html"):
    html = html_path.read_text(encoding="utf-8")

    if "nova-mobile-session-restore-lock.js" not in html:
        continue

    html = html.replace("?v=session-restore-lock-20260702b", "?v=session-restore-dom-root-v3")
    html = html.replace("?v=session-restore-lock-20260702", "?v=session-restore-dom-root-v3")
    html = html.replace("?v=dom-root-v2", "?v=session-restore-dom-root-v3")
    html = html.replace("?v=session-restore-lock-dom-root-v3", "?v=session-restore-dom-root-v3")

    html_path.write_text(html, encoding="utf-8")
    print("cache-busted", html_path)
