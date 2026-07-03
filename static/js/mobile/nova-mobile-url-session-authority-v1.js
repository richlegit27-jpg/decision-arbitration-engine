(function () {
    "use strict";

    const MARKER = "NOVA_MOBILE_URL_SESSION_AUTHORITY_V1_20260703";

    if (window.__NOVA_MOBILE_URL_SESSION_AUTHORITY_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_URL_SESSION_AUTHORITY_V1_20260703__ = true;

    function getUrlSessionId() {
        try {
            const params = new URLSearchParams(window.location.search);
            return params.get("session_id") || "";
        } catch (_) {
            return "";
        }
    }

    function saveUrlSession(sessionId) {
        if (!sessionId) {
            return;
        }

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.setItem("nova_current_session_id", sessionId);
            sessionStorage.setItem("nova_mobile_active_session_id", sessionId);
            sessionStorage.setItem("nova_active_session_id", sessionId);
        } catch (_) {}

        window.__NOVA_MOBILE_ACTIVE_SESSION_ID__ = sessionId;
        window.__NOVA_ACTIVE_SESSION_ID__ = sessionId;
    }

    function stripNewParamWhenSessionExists() {
        try {
            const url = new URL(window.location.href);

            if (!url.searchParams.get("session_id") || !url.searchParams.has("new")) {
                return;
            }

            url.searchParams.delete("new");
            window.history.replaceState({}, "", url.pathname + url.search + url.hash);
        } catch (_) {}
    }

    function enforceUrlSession(reason) {
        const sessionId = getUrlSessionId();

        if (!sessionId) {
            return "";
        }

        saveUrlSession(sessionId);
        stripNewParamWhenSessionExists();

        try {
            console.log("[Nova Mobile URL Session Authority V1] enforced", reason, sessionId);
        } catch (_) {}

        return sessionId;
    }

    function installFetchGuard() {
        if (window.__NOVA_MOBILE_URL_SESSION_AUTHORITY_FETCH_PATCHED__) {
            return;
        }

        window.__NOVA_MOBILE_URL_SESSION_AUTHORITY_FETCH_PATCHED__ = true;

        const originalFetch = window.fetch;

        if (typeof originalFetch !== "function") {
            return;
        }

        window.fetch = function (input, init) {
            const sessionId = enforceUrlSession("fetch");

            try {
                const url = typeof input === "string" ? input : String(input && input.url || "");

                if (sessionId && url.includes("/api/chat")) {
                    const nextInit = Object.assign({}, init || {});

                    if (typeof nextInit.body === "string") {
                        try {
                            const data = JSON.parse(nextInit.body);
                            data.session_id = sessionId;
                            data.session = sessionId;
                            nextInit.body = JSON.stringify(data);
                            return originalFetch.call(this, input, nextInit);
                        } catch (_) {}
                    }
                }
            } catch (_) {}

            return originalFetch.apply(this, arguments);
        };
    }

    enforceUrlSession("boot");
    installFetchGuard();

    let ticks = 0;
    const timer = window.setInterval(function () {
        ticks += 1;
        enforceUrlSession("timer");

        if (ticks >= 40) {
            window.clearInterval(timer);
        }
    }, 250);

    document.addEventListener("visibilitychange", function () {
        enforceUrlSession("visibilitychange");
    }, true);

    window.NovaMobileUrlSessionAuthorityV1 = {
        marker: MARKER,
        getUrlSessionId,
        saveUrlSession,
        enforceUrlSession,
        stripNewParamWhenSessionExists
    };
})();
