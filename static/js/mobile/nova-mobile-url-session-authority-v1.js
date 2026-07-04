(function () {
    "use strict";

    const MARK = "NOVA_MOBILE_URL_SESSION_AUTHORITY_V1_20260704";

    if (window[MARK]) {
        return;
    }

    window[MARK] = true;

    function getUrlSessionId() {
        try {
            return new URLSearchParams(location.search).get("session_id") || "";
        } catch (_) {
            return "";
        }
    }

    function storeSessionId(sessionId) {
        if (!sessionId) {
            return;
        }

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("active_session_id", sessionId);
        } catch (_) {}
    }

    function renderPayload(payload) {
        if (!payload || !payload.session) {
            return false;
        }

        const renderer = window.NovaMobileChatVisibleRecoveryV1;

        if (renderer && typeof renderer.renderPayload === "function") {
            renderer.renderPayload(payload);
            return true;
        }

        return false;
    }

    async function forceUrlSession() {
        const sessionId = getUrlSessionId();

        if (!sessionId) {
            return;
        }

        storeSessionId(sessionId);

        try {
            const res = await fetch("/api/sessions/" + encodeURIComponent(sessionId) + "?url_session_authority=" + Date.now(), {
                credentials: "include",
                cache: "no-store"
            });

            if (!res.ok) {
                console.error("[Nova URL Session Authority] fetch failed", res.status);
                return;
            }

            const payload = await res.json();

            payload.active_session_id = sessionId;
            payload.session_id = sessionId;

            if (payload.session) {
                payload.session.active_session_id = sessionId;
                payload.session.id = payload.session.id || sessionId;
            }

            storeSessionId(sessionId);

            let rendered = renderPayload(payload);

            if (!rendered) {
                setTimeout(function () {
                    rendered = renderPayload(payload);
                    console.error("[Nova URL Session Authority] delayed render", {
                        sessionId: sessionId,
                        rendered: rendered
                    });
                }, 500);
            }

            console.error("[Nova URL Session Authority] forced url session", {
                sessionId: sessionId,
                rendered: rendered,
                messageCount: payload.session && payload.session.messages ? payload.session.messages.length : null
            });
        } catch (err) {
            console.error("[Nova URL Session Authority] error", err);
        }
    }

    window.NovaMobileUrlSessionAuthorityV1 = {
        forceUrlSession: forceUrlSession
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", forceUrlSession);
    } else {
        forceUrlSession();
    }

    setTimeout(forceUrlSession, 800);
    setTimeout(forceUrlSession, 1800);
})();
