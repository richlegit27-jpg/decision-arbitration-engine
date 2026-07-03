(function () {
    "use strict";

    var VERSION = "mobile-send-stable-v1-20260703";
    window.__NOVA_MOBILE_SEND_STABLE_V1_20260703__ = VERSION;

    var inFlight = false;

    function log() {
        try {
            console.log.apply(console, ["[Nova Mobile Send Stable V1]"].concat(Array.from(arguments)));
        } catch (_) {}
    }

    function getSessionId() {
        try {
            var urlId = new URLSearchParams(window.location.search).get("session_id");
            if (urlId) return urlId;
        } catch (_) {}

        try {
            var localId = localStorage.getItem("nova_mobile_active_session_id") || localStorage.getItem("nova_active_session_id");
            if (localId) return localId;
        } catch (_) {}

        return "mobile_" + Date.now() + "_" + Math.random().toString(16).slice(2);
    }

    function findInput() {
        var selectors = [
            "#message-input",
            "#chat-input",
            "#nova-mobile-input",
            "#nova-chat-input",
            "textarea",
            "input[type='text']"
        ];

        for (var i = 0; i < selectors.length; i += 1) {
            var nodes = Array.from(document.querySelectorAll(selectors[i]));
            for (var j = 0; j < nodes.length; j += 1) {
                var el = nodes[j];
                if (!el) continue;
                if (el.offsetParent === null && el !== document.activeElement) continue;
                if (el.closest && el.closest("#nova-session-drawer-v2-panel")) continue;
                return el;
            }
        }

        return null;
    }

    function findMainChatContainer() {
        var restored = document.querySelector("[data-nova-restored-session-id]");
        if (restored) return restored;

        var selectors = [
            "#nova-session-main-restore-fallback",
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
            var nodes = Array.from(document.querySelectorAll(selectors[i]));
            for (var j = 0; j < nodes.length; j += 1) {
                var el = nodes[j];
                if (!el) continue;
                if (el.id === "nova-session-drawer-v2-panel") continue;
                if (el.closest && el.closest("#nova-session-drawer-v2-panel")) continue;
                return el;
            }
        }

        var fallback = document.createElement("div");
        fallback.id = "nova-session-main-restore-fallback";
        fallback.setAttribute("data-nova-mobile-messages", "true");
        document.body.appendChild(fallback);
        return fallback;
    }

    function installStyle() {
        var style = document.getElementById("nova-mobile-send-stable-v1-style");
        if (style) return;

        style = document.createElement("style");
        style.id = "nova-mobile-send-stable-v1-style";
        style.textContent = [
            ".nova-stable-send-message{margin:8px 10px!important;padding:10px 12px!important;border-radius:12px!important;color:#fff!important;white-space:pre-wrap!important;word-break:break-word!important;font-size:14px!important;line-height:1.38!important}",
            ".nova-stable-send-message[data-role='user']{background:rgba(139,92,246,.26)!important}",
            ".nova-stable-send-message[data-role='assistant']{background:rgba(255,255,255,.09)!important}",
            ".nova-stable-send-message[data-role='system']{background:rgba(255,255,255,.06)!important;color:rgba(255,255,255,.75)!important}"
        ].join("\\n");
        document.head.appendChild(style);
    }

    function appendMessage(role, text) {
        installStyle();

        var container = findMainChatContainer();
        if (!container) return;

        var row = document.createElement("div");
        row.className = "nova-stable-send-message";
        row.setAttribute("data-role", role || "assistant");
        row.textContent = text || "";
        container.appendChild(row);

        try {
            container.scrollTop = container.scrollHeight;
        } catch (_) {}
    }

    function extractReply(payload) {
        if (!payload) return "";

        return String(
            payload.text ||
            (payload.assistant_message && (payload.assistant_message.text || payload.assistant_message.content)) ||
            payload.content ||
            payload.message ||
            ""
        );
    }

    function sendNow(event) {
        try {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
            }
        } catch (_) {}

        if (inFlight) {
            log("ignored duplicate send");
            return;
        }

        var input = findInput();
        var text = input ? String(input.value || "").trim() : "";

        if (!text) {
            log("empty send ignored");
            return;
        }

        var sid = getSessionId();

        try {
            localStorage.setItem("nova_mobile_active_session_id", sid);
            localStorage.setItem("nova_active_session_id", sid);
        } catch (_) {}

        inFlight = true;

        appendMessage("user", text);

        if (input) {
            input.value = "";
            try {
                input.dispatchEvent(new Event("input", { bubbles: true }));
            } catch (_) {}
        }

        fetch("/api/chat", {
            method: "POST",
            credentials: "include",
            cache: "no-store",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                message: text,
                session_id: sid
            })
        }).then(function (response) {
            return response.text().then(function (raw) {
                if (!response.ok) {
                    throw new Error("HTTP " + response.status + ": " + raw.slice(0, 500));
                }

                var payload = JSON.parse(raw);
                var reply = extractReply(payload) || "[empty response]";

                appendMessage("assistant", reply);
                log("sent", sid);
            });
        }).catch(function (err) {
            appendMessage("system", "Send failed: " + (err && err.message ? err.message : String(err)));
            log("failed", err);
        }).finally(function () {
            inFlight = false;
        });
    }

    function looksLikeSendButton(el) {
        if (!el) return false;

        var text = String(el.textContent || "").trim().toLowerCase();
        var aria = String(el.getAttribute("aria-label") || "").trim().toLowerCase();
        var title = String(el.getAttribute("title") || "").trim().toLowerCase();
        var id = String(el.id || "").toLowerCase();
        var klass = String(el.className || "").toLowerCase();

        var haystack = [text, aria, title, id, klass].join(" ");

        if (haystack.indexOf("session") >= 0) return false;
        if (haystack.indexOf("stop") >= 0) return false;
        if (haystack.indexOf("voice") >= 0) return false;
        if (haystack.indexOf("attach") >= 0) return false;

        return (
            text === "send" ||
            text === "➤" ||
            text === "↑" ||
            haystack.indexOf("send") >= 0
        );
    }

    function installCapture() {
        if (window.__NOVA_MOBILE_SEND_STABLE_V1_CAPTURE_INSTALLED_20260703__) {
            return;
        }

        window.__NOVA_MOBILE_SEND_STABLE_V1_CAPTURE_INSTALLED_20260703__ = true;

        document.addEventListener("click", function (event) {
            var target = event.target;
            var button = target && target.closest && target.closest("button, a, [role='button']");
            if (!button) return;
            if (button.closest && button.closest("#nova-session-drawer-v2-panel")) return;

            if (looksLikeSendButton(button)) {
                sendNow(event);
            }
        }, true);

        document.addEventListener("keydown", function (event) {
            if (!event) return;
            if (event.key !== "Enter") return;
            if (event.shiftKey) return;

            var target = event.target;
            if (!target) return;
            if (!target.matches || !target.matches("textarea, input[type='text']")) return;
            if (target.closest && target.closest("#nova-session-drawer-v2-panel")) return;

            sendNow(event);
        }, true);
    }

    installCapture();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", installCapture);
    }

    window.NovaMobileSendStableV1 = {
        version: VERSION,
        sendNow: sendNow
    };

    log("ready", VERSION);
})();
