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

    function isChatRequest(input) {
        try {
            const raw = typeof input === "string" ? input : input && input.url;
            if (!raw) {
                return false;
            }

            const url = new URL(raw, location.origin);

            return (
                url.pathname === "/api/chat" ||
                url.pathname === "/api/chat/stream"
            );
        } catch (_) {
            return false;
        }
    }

    function forceHeaders(headers, sessionId) {
        const next = new Headers(headers || {});
        next.set("X-Nova-Session-Id", sessionId);
        next.set("X-Nova-Active-Session-Id", sessionId);
        return next;
    }

    function forceJsonBody(body, sessionId) {
        if (typeof body !== "string") {
            return {
                changed: false,
                body: body
            };
        }

        try {
            const payload = JSON.parse(body);

            if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
                return {
                    changed: false,
                    body: body
                };
            }

            payload.session_id = sessionId;
            payload.active_session_id = sessionId;
            payload.sessionId = sessionId;

            return {
                changed: true,
                body: JSON.stringify(payload)
            };
        } catch (_) {
            return {
                changed: false,
                body: body
            };
        }
    }

    function forceFormBody(body, sessionId) {
        if (!(body instanceof FormData)) {
            return false;
        }

        try {
            body.set("session_id", sessionId);
            body.set("active_session_id", sessionId);
            body.set("sessionId", sessionId);
            return true;
        } catch (_) {
            return false;
        }
    }

    window.fetch = function novaMobileSendSessionAuthorityFetch(input, init) {
        const sessionId = getSessionId();

        if (!sessionId || !isChatRequest(input)) {
            return originalFetch(input, init);
        }

        const nextInit = Object.assign({}, init || {});

        if (!nextInit.method) {
            nextInit.method = "POST";
        }

        nextInit.headers = forceHeaders(nextInit.headers, sessionId);

        if (nextInit.body instanceof FormData) {
            forceFormBody(nextInit.body, sessionId);
        } else {
            const forced = forceJsonBody(nextInit.body, sessionId);

            if (forced.changed) {
                nextInit.body = forced.body;
                nextInit.headers.set("Content-Type", "application/json");
            }
        }

        console.error("[Nova Send Session Authority] forced chat session", {
            sessionId: sessionId,
            url: typeof input === "string" ? input : input && input.url,
            method: nextInit.method,
            hasBody: !!nextInit.body
        });

        return originalFetch(input, nextInit);
    };

    window.NovaMobileSendSessionAuthorityV1 = {
        getSessionId: getSessionId
    };

    console.error("[Nova Send Session Authority] installed");
})();
