from pathlib import Path

JS_PATH = Path("static/js/nova-chat-width-stability.js")
TEMPLATES = list(Path("templates").glob("*.html"))

JS_CODE = r'''// NOVA_CHAT_WIDTH_STABILITY_GUARD_20260702
// Prevent the desktop/mobile chat column from collapsing inward as long threads grow.
// Runtime guard because later message renders can overwrite static CSS/layout state.

(function () {
    if (window.__NOVA_CHAT_WIDTH_STABILITY_GUARD_20260702__) {
        return;
    }
    window.__NOVA_CHAT_WIDTH_STABILITY_GUARD_20260702__ = true;

    const MARK = "nova-width-stability-active";

    const TARGET_SELECTORS = [
        "main",
        "#app",
        "#root",
        "#chat",
        "#messages",
        "#chatMessages",
        "#chatWindow",
        "#conversation",
        "#conversationMessages",
        ".app",
        ".nova-app",
        ".nova-shell",
        ".app-shell",
        ".desktop-shell",
        ".mobile-shell",
        ".main-shell",
        ".page-shell",
        ".layout",
        ".app-layout",
        ".main-layout",
        ".main",
        ".nova-main",
        ".main-panel",
        ".content",
        ".content-panel",
        ".chat-main",
        ".chat-page",
        ".chat-layout",
        ".chat-shell",
        ".chat-panel",
        ".chat-column",
        ".chat-container",
        ".conversation",
        ".conversation-panel",
        ".conversation-container",
        ".messages",
        ".message-list",
        ".messages-list",
        ".chat-messages"
    ];

    const MESSAGE_SELECTORS = [
        ".message",
        ".message-row",
        ".chat-message",
        ".assistant-message",
        ".user-message",
        ".bubble",
        ".message-bubble",
        "pre",
        "code"
    ];

    function installStyle() {
        if (document.getElementById("nova-chat-width-stability-style-20260702")) {
            return;
        }

        const style = document.createElement("style");
        style.id = "nova-chat-width-stability-style-20260702";
        style.textContent = `
            html.${MARK},
            body.${MARK} {
                width: 100% !important;
                max-width: none !important;
                overflow-x: hidden !important;
            }

            body.${MARK} main,
            body.${MARK} #app,
            body.${MARK} #root,
            body.${MARK} #chat,
            body.${MARK} #messages,
            body.${MARK} #chatMessages,
            body.${MARK} #chatWindow,
            body.${MARK} #conversation,
            body.${MARK} #conversationMessages,
            body.${MARK} .app,
            body.${MARK} .nova-app,
            body.${MARK} .nova-shell,
            body.${MARK} .app-shell,
            body.${MARK} .desktop-shell,
            body.${MARK} .mobile-shell,
            body.${MARK} .main-shell,
            body.${MARK} .page-shell,
            body.${MARK} .layout,
            body.${MARK} .app-layout,
            body.${MARK} .main-layout,
            body.${MARK} .main,
            body.${MARK} .nova-main,
            body.${MARK} .main-panel,
            body.${MARK} .content,
            body.${MARK} .content-panel,
            body.${MARK} .chat-main,
            body.${MARK} .chat-page,
            body.${MARK} .chat-layout,
            body.${MARK} .chat-shell,
            body.${MARK} .chat-panel,
            body.${MARK} .chat-column,
            body.${MARK} .chat-container,
            body.${MARK} .conversation,
            body.${MARK} .conversation-panel,
            body.${MARK} .conversation-container,
            body.${MARK} .messages,
            body.${MARK} .message-list,
            body.${MARK} .messages-list,
            body.${MARK} .chat-messages {
                box-sizing: border-box !important;
                min-width: 0 !important;
                max-width: none !important;
            }

            body.${MARK} .message,
            body.${MARK} .message-row,
            body.${MARK} .chat-message,
            body.${MARK} .assistant-message,
            body.${MARK} .user-message,
            body.${MARK} .bubble,
            body.${MARK} .message-bubble,
            body.${MARK} pre,
            body.${MARK} code {
                min-width: 0 !important;
                overflow-wrap: anywhere !important;
                word-break: break-word !important;
                max-width: 100% !important;
            }
        `;
        document.head.appendChild(style);
    }

    function isVisible(el) {
        if (!el || !(el instanceof HTMLElement)) {
            return false;
        }
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }

    function forceStableBox(el) {
        if (!el || !(el instanceof HTMLElement) || !isVisible(el)) {
            return;
        }

        el.style.boxSizing = "border-box";
        el.style.minWidth = "0";
        el.style.maxWidth = "none";

        const parent = el.parentElement;
        if (!parent || !isVisible(parent)) {
            return;
        }

        const rect = el.getBoundingClientRect();
        const parentRect = parent.getBoundingClientRect();
        const viewportWidth = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);

        const parentIsWide = parentRect.width >= viewportWidth * 0.55;
        const childCollapsed = rect.width > 0 && rect.width < parentRect.width * 0.62;

        if (parentIsWide && childCollapsed) {
            el.style.width = "100%";
            el.style.flex = "1 1 auto";
            el.style.alignSelf = "stretch";
        }

        if (parentIsWide && rect.right < parentRect.right - 160) {
            el.style.width = "100%";
            el.style.maxWidth = "none";
            el.style.flex = "1 1 auto";
            el.style.alignSelf = "stretch";
        }
    }

    function forceMessageStability(el) {
        if (!el || !(el instanceof HTMLElement)) {
            return;
        }
        el.style.minWidth = "0";
        el.style.maxWidth = "100%";
        el.style.overflowWrap = "anywhere";
        el.style.wordBreak = "break-word";
    }

    let scheduled = false;

    function stabilize() {
        scheduled = false;

        document.documentElement.classList.add(MARK);
        document.body.classList.add(MARK);

        document.documentElement.style.width = "100%";
        document.documentElement.style.maxWidth = "none";
        document.body.style.width = "100%";
        document.body.style.maxWidth = "none";

        const targets = document.querySelectorAll(TARGET_SELECTORS.join(","));
        targets.forEach(forceStableBox);

        const messages = document.querySelectorAll(MESSAGE_SELECTORS.join(","));
        messages.forEach(forceMessageStability);
    }

    function schedule() {
        if (scheduled) {
            return;
        }
        scheduled = true;
        window.requestAnimationFrame(stabilize);
    }

    function start() {
        installStyle();
        schedule();

        const observer = new MutationObserver(schedule);
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["class", "style"]
        });

        window.addEventListener("resize", schedule, { passive: true });
        window.addEventListener("load", schedule, { once: false });

        // Some Nova render paths update after async response finalization.
        setInterval(schedule, 750);

        console.log("[NOVA_CHAT_WIDTH_STABILITY_GUARD_20260702] active");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start, { once: true });
    } else {
        start();
    }
})();
'''

JS_PATH.parent.mkdir(parents=True, exist_ok=True)
JS_PATH.write_text(JS_CODE, encoding="utf-8")

SCRIPT_TAG = '<script src="{{ url_for(\'static\', filename=\'js/nova-chat-width-stability.js\') }}?v=20260702"></script>'

patched = []
for path in TEMPLATES:
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    if "nova-chat-width-stability.js" in text:
        continue

    lower = text.lower()
    idx = lower.rfind("</body>")
    if idx != -1:
        text = text[:idx] + "    " + SCRIPT_TAG + "\n" + text[idx:]
    else:
        text = text.rstrip() + "\n" + SCRIPT_TAG + "\n"

    path.write_text(text, encoding="utf-8")
    patched.append(str(path))

print("created", JS_PATH)
print("patched templates:")
for item in patched:
    print("-", item)
