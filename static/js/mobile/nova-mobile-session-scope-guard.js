/*
NOVA_MOBILE_SESSION_SCOPE_GUARD_20260623
Clears stale mobile active session ids when /api/sessions says they are not visible.
*/

(function () {
    "use strict";

    const FIX_ID = "NOVA_MOBILE_SESSION_SCOPE_GUARD_20260623";

    const SESSION_KEYS = [
        "nova_mobile_active_session_id",
        "nova_active_session_id",
        "active_session_id",
        "session_id",
        "nova_session_id",
        "novaMobileSessionId",
        "NovaMobileActiveSessionId",
        "NOVA_ACTIVE_SESSION_ID"
    ];

    function getLocalActiveId() {
        for (const key of SESSION_KEYS) {
            try {
                const value = String(localStorage.getItem(key) || sessionStorage.getItem(key) || "").trim();

                if (value) return value;
            } catch (_) {}
        }

        return String(
            window.NOVA_ACTIVE_SESSION_ID ||
            window.NovaActiveSessionId ||
            window.NovaMobileActiveSessionId ||
            window.novaMobileActiveSessionId ||
            window.NovaCurrentSessionId ||
            window.currentSessionId ||
            window.activeSessionId ||
            ""
        ).trim();
    }

    function clearLocalActiveId(reason) {
        SESSION_KEYS.forEach(function (key) {
            try {
                localStorage.removeItem(key);
            } catch (_) {}

            try {
                sessionStorage.removeItem(key);
            } catch (_) {}
        });

        window.NOVA_ACTIVE_SESSION_ID = "";
        window.NovaActiveSessionId = "";
        window.NovaMobileActiveSessionId = "";
        window.novaMobileActiveSessionId = "";
        window.NovaCurrentSessionId = "";
        window.currentSessionId = "";
        window.activeSessionId = "";
        window.NOVA_FORCE_NEW_SESSION_ON_NEXT_SEND = true;
        window.NOVA_PENDING_NEW_SESSION_ID = "";

        console.log("[" + FIX_ID + "] cleared stale active session", reason || "");
    }

    function collectVisibleIds(payload) {
        const ids = new Set();

        ["items", "sessions"].forEach(function (key) {
            const list = payload && Array.isArray(payload[key]) ? payload[key] : [];

            list.forEach(function (item) {
                if (!item || typeof item !== "object") return;

                const id = String(item.id || item.session_id || "").trim();

                if (id) ids.add(id);
            });
        });

        return ids;
    }

    function scrubFromPayload(payload) {
        if (!payload || typeof payload !== "object") return;

        const ids = collectVisibleIds(payload);
        const localId = getLocalActiveId();
        const responseActive = String(payload.active_session_id || "").trim();

        if (responseActive && !ids.has(responseActive)) {
            payload.active_session_id = "";
        }

        if (localId && !ids.has(localId)) {
            clearLocalActiveId("not visible in /api/sessions: " + localId);
        }

        if (!ids.size && localId) {
            clearLocalActiveId("empty scoped session list");
        }
    }

    async function checkNow() {
        try {
            const response = await fetch("/api/sessions", {
                credentials: "include",
                headers: {
                    "Accept": "application/json"
                }
            });

            const payload = await response.json();

            scrubFromPayload(payload);

            return payload;
        } catch (error) {
            console.warn("[" + FIX_ID + "] check failed", error);
            return null;
        }
    }

    function installFetchHook() {
        if (window.__novaMobileSessionScopeGuardFetchHook) return;

        window.__novaMobileSessionScopeGuardFetchHook = true;

        const originalFetch = window.fetch;

        if (typeof originalFetch !== "function") return;

        window.fetch = function () {
            const args = arguments;
            const url = String(args[0] && args[0].url || args[0] || "");

            return originalFetch.apply(this, args).then(function (response) {
                try {
                    if (url.includes("/api/sessions")) {
                        response.clone().json().then(scrubFromPayload).catch(function () {});
                    }
                } catch (_) {}

                return response;
            });
        };
    }

    function boot() {
        installFetchHook();

        [80, 500, 1200, 2400].forEach(function (delay) {
            window.setTimeout(checkNow, delay);
        });

        console.log("[" + FIX_ID + "] ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    window.NovaMobileSessionScopeGuard = {
        check: checkNow,
        clear: clearLocalActiveId
    };
})();
