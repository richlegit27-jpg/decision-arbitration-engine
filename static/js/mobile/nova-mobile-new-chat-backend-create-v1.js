(function () {
    "use strict";

    const MARKER = "NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_V1_20260703";

    if (window.__NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_V1_20260703__ = true;

    function log() {
        try {
            console.log("[Nova Mobile New Chat Backend Create V1]", ...arguments);
        } catch (_) {}
    }

    function isNewChatTarget(target) {
        if (!target) {
            return false;
        }

        const el = target.closest && target.closest("button, a, [role='button'], [data-action], [id], [class]");
        if (!el) {
            return false;
        }

        const text = String(el.textContent || "").trim().toLowerCase();
        const aria = String(el.getAttribute("aria-label") || "").trim().toLowerCase();
        const title = String(el.getAttribute("title") || "").trim().toLowerCase();
        const id = String(el.id || "").trim().toLowerCase();
        const cls = String(el.className || "").trim().toLowerCase();
        const href = String(el.getAttribute("href") || "").trim().toLowerCase();
        const action = String(el.getAttribute("data-action") || "").trim().toLowerCase();

        return (
            text === "new chat" ||
            text.includes("new chat") ||
            aria.includes("new chat") ||
            title.includes("new chat") ||
            id.includes("new-chat") ||
            id.includes("new_chat") ||
            cls.includes("new-chat") ||
            cls.includes("new_chat") ||
            action.includes("new-chat") ||
            href.includes("?new=") ||
            href.includes("&new=")
        );
    }

    function extractSessionId(data) {
        return (
            data?.session_id ||
            data?.id ||
            data?.session?.session_id ||
            data?.session?.id ||
            data?.data?.session_id ||
            data?.data?.id ||
            null
        );
    }

    async function createBackendSession() {
        const stamp = Date.now();

        const res = await fetch("/api/sessions/new?v=" + stamp, {
            method: "POST",
            credentials: "include",
            cache: "no-store",
            headers: {
                "Content-Type": "application/json",
                "Cache-Control": "no-cache"
            },
            body: JSON.stringify({
                title: "New Chat"
            })
        });

        const text = await res.text();
        let data = {};

        try {
            data = JSON.parse(text);
        } catch (_) {
            data = { raw: text };
        }

        if (!res.ok) {
            throw new Error("Session create failed: HTTP " + res.status + " " + text.slice(0, 300));
        }

        const sessionId = extractSessionId(data);

        if (!sessionId) {
            throw new Error("Session create returned no session id: " + text.slice(0, 300));
        }

        return {
            sessionId,
            data
        };
    }

    function saveActiveSession(sessionId) {
        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("nova_current_session_id", sessionId);
            sessionStorage.setItem("nova_mobile_active_session_id", sessionId);
            sessionStorage.setItem("nova_active_session_id", sessionId);
        } catch (exc) {
            log("storage save failed", exc);
        }

        window.__NOVA_MOBILE_ACTIVE_SESSION_ID__ = sessionId;
    }

    function openSession(sessionId) {
        const url = "/mobile?session_id=" + encodeURIComponent(sessionId) + "&new=" + Date.now();
        log("opening new backend session", sessionId, url);
        window.location.assign(url);
    }

    async function runNewChatFlow(event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();

            if (event.stopImmediatePropagation) {
                event.stopImmediatePropagation();
            }
        }

        try {
            const created = await createBackendSession();
            saveActiveSession(created.sessionId);
            openSession(created.sessionId);
        } catch (exc) {
            console.error("[Nova Mobile New Chat Backend Create V1] failed", exc);
            alert("New Chat failed: " + (exc && exc.message ? exc.message : exc));
        }
    }

    document.addEventListener("click", function (event) {
        if (!isNewChatTarget(event.target)) {
            return;
        }

        runNewChatFlow(event);
    }, true);

    window.NovaMobileNewChatBackendCreateV1 = {
        marker: MARKER,
        createBackendSession,
        saveActiveSession,
        openSession,
        runNewChatFlow,
        isNewChatTarget
    };

    log("installed");
})();
