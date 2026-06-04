(function () {
    "use strict";

    function installBridge(options) {
        options = options || {};

        window.NovaMobileBridge = {
            renderMarkdown: window.NovaMobileCore.renderMarkdown,
            enhanceCodeBlocks: window.NovaMobileCodeUI.enhanceCodeBlocks,
            scrollBottom: window.NovaMobileCore.scrollBottom,
            saveCurrentMessages: window.NovaMobileCore.saveCurrentMessages,
            syncSessionFromResponse: options.syncSessionFromResponse
        };

        console.log("[Nova Mobile] bridge installed");
    }

    window.NovaMobileBridgeModule = {
        installBridge
    };

    console.log("[Nova Mobile] bridge module ready");
})();

/* NOVA MOBILE SESSION BRIDGE START */
(function () {
    "use strict";

    function clean(value) {
        return String(value || "").trim();
    }

    function rememberSessionId(sessionId) {
        sessionId = clean(sessionId);

        if (!sessionId) {
            return "";
        }

        window.__novaActiveSessionId = sessionId;
        window.activeSessionId = sessionId;
        window.sessionId = sessionId;

        try {
            localStorage.setItem("nova_active_session_id", sessionId);
        } catch (_) {}

        try {
            if (document.body) {
                document.body.setAttribute("data-session-id", sessionId);
            }
        } catch (_) {}

        return sessionId;
    }

    function extractSessionId(payload) {
        if (!payload || typeof payload !== "object") {
            return "";
        }

        return clean(
            payload.active_session_id ||
            payload.session_id ||
            payload.chat_id ||
            (
                payload.session &&
                (
                    payload.session.id ||
                    payload.session.session_id ||
                    payload.session.chat_id
                )
            ) ||
            (
                payload.data &&
                (
                    payload.data.active_session_id ||
                    payload.data.session_id ||
                    (
                        payload.data.session &&
                        (
                            payload.data.session.id ||
                            payload.data.session.session_id ||
                            payload.data.session.chat_id
                        )
                    )
                )
            ) ||
            ""
        );
    }

    window.getSessionId = function () {
        return clean(
            window.__novaActiveSessionId ||
            window.activeSessionId ||
            window.sessionId ||
            localStorage.getItem("nova_active_session_id") ||
            (
                document.body &&
                document.body.getAttribute("data-session-id")
            ) ||
            ""
        );
    };

    window.NovaRememberMobileSessionId = rememberSessionId;
    window.NovaMobileSessionBridgeInstalled = true;

    if (!window.__NovaMobileSessionFetchWrapped) {
        window.__NovaMobileSessionFetchWrapped = true;

        const originalFetch = window.fetch;

        window.fetch = async function () {
            const response = await originalFetch.apply(this, arguments);

            try {
                const cloned = response.clone();
                const contentType = cloned.headers.get("content-type") || "";

                if (contentType.includes("application/json")) {
                    cloned.json().then(function (payload) {
                        const sessionId = extractSessionId(payload);

                        if (sessionId) {
                            rememberSessionId(sessionId);
                            console.log("[Nova Mobile] session remembered", sessionId);
                        }
                    }).catch(function () {});
                }
            } catch (_) {}

            return response;
        };
    }

    const existing = window.getSessionId();

    if (existing) {
        rememberSessionId(existing);
    }

    console.log("[Nova Mobile] session bridge active from module");
})();
/* NOVA MOBILE SESSION BRIDGE END */

