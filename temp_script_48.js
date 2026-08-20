
(function () {
    "use strict";

    function cleanSid(value) {
        return String(value || "")
            .trim()
            .replace(/^["']+|["']+$/g, "");
    }

    function storeActiveSessionId(sid) {
        sid = cleanSid(sid);
        if (!sid) return "";

        try {
            localStorage.setItem("nova.session_id", sid);
            localStorage.setItem("nova_session_id", sid);
            localStorage.setItem("nova_active_session_id", sid);
            localStorage.setItem("nova_desktop_session_id", sid);
            localStorage.setItem("nova_desktop_active_session_id", sid);
            localStorage.setItem("nova_current_session_id", sid);
            localStorage.setItem("active_session_id", sid);
            localStorage.setItem("session_id", sid);

            sessionStorage.setItem("nova_session_id", sid);
            sessionStorage.setItem("nova_active_session_id", sid);
            sessionStorage.setItem("active_session_id", sid);
            sessionStorage.setItem("session_id", sid);
        } catch (_) {}

        window.__NOVA_ACTIVE_SESSION_ID = sid;
        window.NovaDesktopActiveSessionId = sid;
        window.novaDesktopActiveSessionId = sid;
        window.novaCurrentSessionId = sid;
        window.currentSessionId = sid;
        window.activeSessionId = sid;

        try {
            var sidInput = document.getElementById("sid");
            if (sidInput) sidInput.value = sid;
        } catch (_) {}

        try {
            if (typeof window.setSessionId === "function") {
                window.setSessionId(sid);
            }
        } catch (_) {}

        return sid;
    }

    function messageText(message) {
        if (!message || typeof message !== "object") return "";

        return String(
            message.text ||
            message.content ||
            message.message ||
            message.reply ||
            ""
        ).trim();
    }

    function renderMessagesDirectly(session) {
        var chat = document.getElementById("chat");
        if (!chat || !session) return 0;

        var messages = Array.isArray(session.messages) ? session.messages : [];
        chat.innerHTML = "";

        if (!messages.length) {
            chat.innerHTML = [
                '<div class="nova-empty-chat">',
                '  <div>',
                '    <div class="nova-empty-chat-title">No messages in this session yet</div>',
                '    <div class="nova-empty-chat-subtitle">Session opened, but the saved message list is empty.</div>',
                '  </div>',
                '</div>'
            ].join("");
            return 0;
        }

        messages.forEach(function (message, index) {
            var role = String(message.role || message.type || "assistant").toLowerCase();
            if (role !== "user" && role !== "assistant") role = "assistant";

            var bubble = document.createElement("div");
            bubble.className = "msg " + role;
            bubble.setAttribute("data-message-id", String(message.id || index));
            bubble.setAttribute("data-session-rendered", "1");

            var body = document.createElement("div");
            body.className = "msg-body";
            body.style.whiteSpace = "pre-wrap";
            body.textContent = messageText(message);

            bubble.appendChild(body);
            chat.appendChild(bubble);
        });

        try {
            chat.scrollTop = chat.scrollHeight;
        } catch (_) {}

        return messages.length;
    }

    async function fetchSessionDetail(sid) {
        sid = cleanSid(sid);
        if (!sid) return null;

        var urls = [
            "/api/sessions/" + encodeURIComponent(sid),
            "/api/chat/" + encodeURIComponent(sid)
        ];

        for (var i = 0; i < urls.length; i++) {
            try {
                var response = await fetch(urls[i], {
                    method: "GET",
                    cache: "no-store",
                    headers: {
                        "Accept": "application/json"
                    }
                });

                if (!response.ok) continue;

                var data = await response.json();
                var session = data.session || data.item || data;
                if (session && typeof session === "object") {
                    session.id = session.id || session.session_id || sid;
                    if (!Array.isArray(session.messages) && Array.isArray(data.messages)) {
                        session.messages = data.messages;
                    }
                    return session;
                }
            } catch (error) {
                console.warn("[Nova Open Session Force Render] fetch failed", urls[i], error);
            }
        }

        return null;
    }

    async function openSessionForceRender(sid) {
        sid = storeActiveSessionId(sid);
        if (!sid) return false;

        try {
            var status = document.getElementById("status");
            if (status) status.textContent = "opening session...";
        } catch (_) {}

        var session = await fetchSessionDetail(sid);

        if (!session) {
            console.warn("[Nova Open Session Force Render] no session returned", sid);
            return false;
        }

        storeActiveSessionId(session.id || sid);

var rendered = renderMessagesDirectly(session);

if (
    Array.isArray(session.messages) &&
    session.messages.length === 0 &&
    session.meta &&
    session.meta.onboarding &&
    typeof window.renderDesktopOnboarding === "function"
) {
    window.renderDesktopOnboarding(session);
}

        try {
            if (typeof window.loadDesktopSessions === "function") {
                window.loadDesktopSessions();
            }
        } catch (_) {}

        try {
            var statusDone = document.getElementById("status");
            if (statusDone) statusDone.textContent = "session opened";
        } catch (_) {}

        console.log("[Nova Open Session Force Render] opened", {
            session_id: session.id || sid,
            rendered: rendered
        });

        return true;
    }

    window.NovaDesktopOpenSession = openSessionForceRender;
    window.openDesktopSession = openSessionForceRender;
    window.openSession = openSessionForceRender;
    window.NovaDesktopFetchSession = openSessionForceRender;

    document.addEventListener("click", function (event) {
        var item = event.target && event.target.closest
            ? event.target.closest(".desktop-session-item, .session-item, [data-sid], [data-session-id]")
            : null;

        if (!item) return;

        var sid =
            item.getAttribute("data-session-id") ||
            item.getAttribute("data-sid") ||
            item.getAttribute("data-id") ||
            "";

        sid = cleanSid(sid);

        if (!sid && item.href) {
            try {
                var url = new URL(item.href, window.location.origin);
                sid =
                    url.searchParams.get("session_id") ||
                    url.searchParams.get("sid") ||
                    url.pathname.split("/").filter(Boolean).pop() ||
                    "";
            } catch (_) {}
        }

        sid = cleanSid(sid);
        if (!sid) return;

        event.preventDefault();
        event.stopPropagation();

        openSessionForceRender(sid);
    }, true);

    document.addEventListener("DOMContentLoaded", function () {
        try {
            var url = new URL(window.location.href);
            var sid =
                url.searchParams.get("session_id") ||
                url.searchParams.get("sid") ||
                url.searchParams.get("session") ||
                "";

            sid = cleanSid(sid);
            if (sid) {
                openSessionForceRender(sid);
            }
        } catch (_) {}
    });

    console.log("[Nova Open Session Force Render] installed");
})();
