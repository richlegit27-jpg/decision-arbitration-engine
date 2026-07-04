(function () {
    "use strict";

    const MARK = "NOVA_MOBILE_SEND_SESSION_AUTHORITY_V1_20260704";

    if (window[MARK]) {
        return;
    }

    window[MARK] = true;

    const originalFetch = window.fetch.bind(window);

    function getSessionId() {
        try {
            const fromUrl = new URLSearchParams(location.search).get("session_id");
            if (fromUrl) {
                return fromUrl;
            }
        } catch (_) {}

        try {
            return (
                localStorage.getItem("nova_mobile_active_session_id") ||
                localStorage.getItem("nova_active_session_id") ||
                localStorage.getItem("active_session_id") ||
                ""
            );
        } catch (_) {
            return "";
        }
    }

    function isChatUrl(input) {
        try {
            const raw = typeof input === "string" ? input : input && input.url;
            if (!raw) {
                return false;
            }

            const url = new URL(raw, location.origin);
            return url.pathname === "/api/chat" || url.pathname === "/api/chat/stream";
        } catch (_) {
            return false;
        }
    }

    function forceBody(body, sessionId) {
        if (body instanceof FormData) {
            body.set("session_id", sessionId);
            body.set("active_session_id", sessionId);
            body.set("sessionId", sessionId);
            return body;
        }

        if (typeof body === "string") {
            try {
                const payload = JSON.parse(body);
                if (payload && typeof payload === "object" && !Array.isArray(payload)) {
                    payload.session_id = sessionId;
                    payload.active_session_id = sessionId;
                    payload.sessionId = sessionId;
                    return JSON.stringify(payload);
                }
            } catch (_) {}
        }

        return body;
    }

    window.fetch = function novaMobileSendSessionAuthorityFetch(input, init) {
        const sessionId = getSessionId();

        if (!sessionId || !isChatUrl(input)) {
            return originalFetch(input, init);
        }

        const nextInit = Object.assign({}, init || {});
        const headers = new Headers(nextInit.headers || {});

        headers.set("X-Nova-Session-Id", sessionId);
        headers.set("X-Nova-Active-Session-Id", sessionId);

        nextInit.headers = headers;
        nextInit.body = forceBody(nextInit.body, sessionId);

        console.error("[Nova Send Session Authority] forced chat session", {
            sessionId: sessionId,
            url: typeof input === "string" ? input : input && input.url
        });

        return originalFetch(input, nextInit);
    };

    window.NovaMobileSendSessionAuthorityV1 = {
        getSessionId: getSessionId
    };

    console.error("[Nova Send Session Authority] installed");
})();
