from pathlib import Path
import re

js_path = Path("static/js/mobile/nova-mobile-session-drawer-v2.js")

js = js_path.read_text(encoding="utf-8")

marker = "NOVA_SESSION_DRAWER_V2_MAIN_CHAT_RESTORE_20260703"

if marker not in js:
    anchor = "    function renderMessages(id, title, messages) {"
    if anchor not in js:
        raise SystemExit("missing renderMessages anchor")

    helper = r'''
    // NOVA_SESSION_DRAWER_V2_MAIN_CHAT_RESTORE_20260703
    function installMainChatRestoreStyle() {
        try {
            var style = document.getElementById("nova-session-drawer-v2-main-chat-restore-style");
            if (!style) {
                style = document.createElement("style");
                style.id = "nova-session-drawer-v2-main-chat-restore-style";
                document.head.appendChild(style);
            }

            style.textContent = [
                ".nova-session-main-restore-header{margin:58px 10px 10px 10px!important;padding:10px 12px!important;border-radius:12px!important;background:rgba(139,92,246,.16)!important;color:#fff!important;border:1px solid rgba(139,92,246,.28)!important;font-size:13px!important}",
                ".nova-session-main-restore-message{margin:8px 10px!important;padding:10px 12px!important;border-radius:12px!important;color:#fff!important;white-space:pre-wrap!important;word-break:break-word!important;font-size:14px!important;line-height:1.38!important}",
                ".nova-session-main-restore-message[data-role='user']{background:rgba(139,92,246,.26)!important}",
                ".nova-session-main-restore-message[data-role='assistant']{background:rgba(255,255,255,.09)!important}",
                ".nova-session-main-restore-message[data-role='system']{background:rgba(255,255,255,.06)!important;color:rgba(255,255,255,.75)!important}"
            ].join("\\n");
        } catch (_) {}
    }

    function findMainChatContainer() {
        var selectors = [
            "#nova-mobile-chat-messages",
            "#nova-mobile-messages",
            "#nova-chat-messages",
            "#chat-messages",
            "#messages",
            "[data-nova-mobile-messages]",
            ".nova-mobile-chat-messages",
            ".nova-mobile-messages",
            ".chat-messages",
            ".messages"
        ];

        for (var i = 0; i < selectors.length; i += 1) {
            try {
                var nodes = Array.from(document.querySelectorAll(selectors[i]));
                for (var j = 0; j < nodes.length; j += 1) {
                    var el = nodes[j];
                    if (!el) continue;
                    if (el.id === "nova-session-drawer-v2-panel") continue;
                    if (el.closest && el.closest("#nova-session-drawer-v2-panel")) continue;
                    if (el.tagName && ["INPUT", "TEXTAREA", "BUTTON"].indexOf(el.tagName.toUpperCase()) >= 0) continue;

                    var rect = el.getBoundingClientRect();
                    if (rect.width > 80 && rect.height >= 0) {
                        return el;
                    }
                }
            } catch (_) {}
        }

        var fallback = document.getElementById("nova-session-main-restore-fallback");
        if (!fallback) {
            fallback = document.createElement("div");
            fallback.id = "nova-session-main-restore-fallback";
            fallback.setAttribute("data-nova-mobile-messages", "true");

            var drawer = document.getElementById("nova-session-drawer-v2-panel");
            if (drawer && drawer.parentNode) {
                drawer.parentNode.insertBefore(fallback, drawer);
            } else {
                document.body.appendChild(fallback);
            }
        }

        return fallback;
    }

    function renderSessionToMainChat(id, title, messages) {
        try {
            installMainChatRestoreStyle();

            var container = findMainChatContainer();
            if (!container) return false;

            container.innerHTML = "";
            container.setAttribute("data-nova-restored-session-id", id);

            var header = document.createElement("div");
            header.className = "nova-session-main-restore-header";
            header.textContent = "Session: " + (title || id) + " · " + messages.length + " messages";
            container.appendChild(header);

            if (!messages.length) {
                var empty = document.createElement("div");
                empty.className = "nova-session-main-restore-message";
                empty.setAttribute("data-role", "system");
                empty.textContent = "No messages in this session.";
                container.appendChild(empty);
            }

            messages.forEach(function (message) {
                var row = document.createElement("div");
                row.className = "nova-session-main-restore-message";
                row.setAttribute("data-role", roleOf(message));
                row.textContent = textOf(message) || "[empty message]";
                container.appendChild(row);
            });

            try {
                container.scrollTop = container.scrollHeight;
            } catch (_) {}

            try {
                window.scrollTo({ top: 0, behavior: "smooth" });
            } catch (_) {
                window.scrollTo(0, 0);
            }

            return true;
        } catch (err) {
            log("main chat restore failed", err);
            return false;
        }
    }

'''
    js = js.replace(anchor, helper + anchor, 1)

old = 'renderMessages(id, session.title || title, messagesFrom(detail));'
new = '''var restoredMessages = messagesFrom(detail);
            renderMessages(id, session.title || title, restoredMessages);
            renderSessionToMainChat(id, session.title || title, restoredMessages);'''

if old in js:
    js = js.replace(old, new, 1)
else:
    raise SystemExit("missing openSession renderMessages call")

# Cache-bust served references.
targets = [
    Path("app.py"),
    Path("templates/index.html"),
    Path("templates/mobile.html"),
]

for path in targets:
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")
    new_text = re.sub(
        r'nova-mobile-session-drawer-v2\.js\?v=[^"\']+',
        "nova-mobile-session-drawer-v2.js?v=20260703-stable-no-jitter-4-main-chat-restore",
        text,
    )

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        print("updated", path)

js = js.rstrip() + "\n"
js_path.write_text(js, encoding="utf-8")

print("patched main chat restore from drawer")
