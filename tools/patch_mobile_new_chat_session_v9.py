from pathlib import Path
import re

panel_path = Path("static/js/mobile/nova-mobile-session-panel-v6.js")
loader_path = Path("static/js/mobile/nova-mobile-session-restore-override-v4.js")
smoke_path = Path("tools/nova_mobile_new_chat_session_v8_smoke.py")

panel = panel_path.read_text(encoding="utf-8")

extra = r'''
/* NOVA_MOBILE_NEW_CHAT_URL_BOOT_V9_20260703 */
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_NEW_CHAT_URL_BOOT_V9_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_NEW_CHAT_URL_BOOT_V9_20260703__ = true;

    const KEYS = [
        "nova_mobile_active_session_id",
        "nova_active_session_id",
        "active_session_id",
        "session_id"
    ];

    function log() {
        try { console.log("[NOVA MOBILE NEW CHAT URL BOOT V9]", ...arguments); } catch (_) {}
    }

    function makeSessionId() {
        return "mobile_session_" + Date.now() + "_" + Math.random().toString(16).slice(2, 8);
    }

    function setActiveSessionId(id) {
        const sessionId = String(id || "").trim();
        if (!sessionId) return "";

        for (const key of KEYS) {
            try { localStorage.setItem(key, sessionId); } catch (_) {}
        }

        window.novaMobileActiveSessionId = sessionId;
        window.activeSessionId = sessionId;
        window.currentSessionId = sessionId;
        window.NOVA_ACTIVE_SESSION_ID = sessionId;

        try {
            if (
                window.NovaMobileSessionPanelV6 &&
                typeof window.NovaMobileSessionPanelV6.setActiveSessionId === "function"
            ) {
                window.NovaMobileSessionPanelV6.setActiveSessionId(sessionId);
            }
        } catch (_) {}

        return sessionId;
    }

    function clearVisibleChatSoon() {
        setTimeout(function () {
            const roots = [
                document.getElementById("mobileChatMessages"),
                document.querySelector("[data-nova-chat-messages='true']"),
                document.querySelector(".mobile-chat-container"),
                document.querySelector(".chat-messages"),
                document.querySelector("#chatMessages")
            ].filter(Boolean);

            const seen = new Set();

            for (const root of roots) {
                if (seen.has(root)) continue;
                seen.add(root);

                if (
                    root.id === "nova-mobile-session-panel-v6" ||
                    root.closest("#nova-mobile-session-panel-v6")
                ) {
                    continue;
                }

                root.innerHTML = "";
                root.setAttribute("data-nova-new-chat-url-cleared", "true");
            }

            try { window.messages = []; } catch (_) {}
            try { window.currentMessages = []; } catch (_) {}
        }, 0);
    }

    function rotateSessionFromNewUrl() {
        let url;

        try {
            url = new URL(window.location.href);
        } catch (_) {
            return;
        }

        if (!url.searchParams.has("new")) {
            return;
        }

        const newToken = String(url.searchParams.get("new") || Date.now());
        const seenKey = "nova_mobile_new_chat_url_seen_" + newToken;

        try {
            if (sessionStorage.getItem(seenKey)) {
                return;
            }

            sessionStorage.setItem(seenKey, "1");
        } catch (_) {}

        const sessionId = makeSessionId();
        setActiveSessionId(sessionId);
        clearVisibleChatSoon();

        try {
            url.searchParams.delete("new");
            const cleanUrl = url.pathname + (url.search ? url.search : "") + (url.hash || "");
            window.history.replaceState(null, "", cleanUrl);
        } catch (_) {}

        log("rotated session from ?new=", sessionId);
    }

    rotateSessionFromNewUrl();

    window.NovaMobileNewChatUrlBootV9 = {
        makeSessionId,
        setActiveSessionId,
        rotateSessionFromNewUrl
    };

    log("active");
})();
/* /NOVA_MOBILE_NEW_CHAT_URL_BOOT_V9_20260703 */
'''

if "NOVA_MOBILE_NEW_CHAT_URL_BOOT_V9_20260703" not in panel:
    panel = panel.rstrip() + "\n\n" + extra.strip() + "\n"
    panel_path.write_text(panel, encoding="utf-8")
    print("appended new chat url boot v9")
else:
    print("new chat url boot v9 already present")

loader = loader_path.read_text(encoding="utf-8")

updated = re.sub(
    r"nova-mobile-session-panel-v6\.js\?v=[^\"'\\s<>]+",
    "nova-mobile-session-panel-v6.js?v=new-chat-session-v9",
    loader,
)

if updated == loader:
    updated = loader.replace(
        "nova-mobile-session-panel-v6.js",
        "nova-mobile-session-panel-v6.js?v=new-chat-session-v9"
    )

loader_path.write_text(updated, encoding="utf-8")
print("patched v4 loader to new-chat-session-v9")

if smoke_path.exists():
    smoke = smoke_path.read_text(encoding="utf-8")
    smoke = smoke.replace("new-chat-session-v8", "new-chat-session-v9")

    if "NOVA_MOBILE_NEW_CHAT_URL_BOOT_V9_20260703" not in smoke:
        smoke = smoke.replace(
            'check("v4 loader cache bumped", "new-chat-session-v9" in loader_text)',
            'check("v4 loader cache bumped", "new-chat-session-v9" in loader_text)\n'
            'check("new chat url boot v9 marker present", "NOVA_MOBILE_NEW_CHAT_URL_BOOT_V9_20260703" in panel_text)\n'
            'check("new chat url uses URLSearchParams", "searchParams.has(\\"new\\")" in panel_text)\n'
            'check("new chat url cleans address", "history.replaceState" in panel_text)'
        )

    smoke_path.write_text(smoke, encoding="utf-8")
    print("updated smoke")
