/*
NOVA_MOBILE_SESSION_SCOPE_GUARD_STORAGE_LOCK_20260623
Prevents stale hidden session ids from being re-saved by old mobile bridge code.
*/

(function () {
    "use strict";

    const FIX_ID = "NOVA_MOBILE_SESSION_SCOPE_GUARD_STORAGE_LOCK_20260623";

    const ACTIVE_KEYS = [
        "nova_mobile_active_session_id",
        "nova_active_session_id",
        "active_session_id",
        "session_id",
        "nova_session_id",
        "novaMobileSessionId",
        "NovaMobileActiveSessionId",
        "NOVA_ACTIVE_SESSION_ID"
    ];

    const GLOBAL_KEYS = [
        "NOVA_ACTIVE_SESSION_ID",
        "NovaActiveSessionId",
        "NovaMobileActiveSessionId",
        "novaMobileActiveSessionId",
        "NovaCurrentSessionId",
        "currentSessionId",
        "activeSessionId"
    ];

    let visibleSessionIds = new Set();
    let hasSeenSessionsPayload = false;

    function clean(value) {
        return String(value || "").trim();
    }

    function isActiveKey(key) {
        return ACTIVE_KEYS.includes(String(key || ""));
    }

    function isBlockedSessionId(value) {
        const id = clean(value);

        if (!id) return false;

        if (id === "debug_encoding_news_003") return true;

        if (id.startsWith("debug_") && hasSeenSessionsPayload && !visibleSessionIds.has(id)) {
            return true;
        }

        if (visibleSessionIds.size && !visibleSessionIds.has(id)) {
            return true;
        }

        return false;
    }

    function removeActiveStorage(reason) {
        ACTIVE_KEYS.forEach(function (key) {
            try {
                localStorage.removeItem(key);
            } catch (_) {}

            try {
                sessionStorage.removeItem(key);
            } catch (_) {}
        });

        GLOBAL_KEYS.forEach(function (key) {
            try {
                window[key] = "";
            } catch (_) {}
        });

        window.NOVA_FORCE_NEW_SESSION_ON_NEXT_SEND = true;
        window.NOVA_PENDING_NEW_SESSION_ID = "";

        console.log("[" + FIX_ID + "] cleared active session", reason || "");
    }

    function installStorageSetItemLock() {
        if (window.__novaMobileScopeStorageSetItemLock20260623) return;

        window.__novaMobileScopeStorageSetItemLock20260623 = true;

        const originalLocalSetItem = Storage.prototype.setItem;

        Storage.prototype.setItem = function (key, value) {
            if (isActiveKey(key) && isBlockedSessionId(value)) {
                try {
                    originalLocalSetItem.call(this, key, "");
                    this.removeItem(key);
                } catch (_) {}

                console.log("[" + FIX_ID + "] blocked stale storage save", key, value);
                return;
            }

            return originalLocalSetItem.call(this, key, value);
        };
    }

    function installGlobalLocks() {
        if (window.__novaMobileScopeGlobalLocks20260623) return;

        window.__novaMobileScopeGlobalLocks20260623 = true;

        GLOBAL_KEYS.forEach(function (key) {
            let internalValue = "";

            try {
                internalValue = clean(window[key]);
            } catch (_) {}

            try {
                Object.defineProperty(window, key, {
                    configurable: true,
                    get: function () {
                        return internalValue;
                    },
                    set: function (value) {
                        const next = clean(value);

                        if (isBlockedSessionId(next)) {
                            internalValue = "";
                            console.log("[" + FIX_ID + "] blocked stale global save", key, next);
                            return;
                        }

                        internalValue = next;
                    }
                });
            } catch (_) {}
        });
    }

    function collectVisibleIds(payload) {
        const ids = new Set();

        ["items", "sessions"].forEach(function (key) {
            const list = payload && Array.isArray(payload[key]) ? payload[key] : [];

            list.forEach(function (item) {
                if (!item || typeof item !== "object") return;

                const id = clean(item.id || item.session_id);

                if (id) ids.add(id);
            });
        });

        return ids;
    }

    function scrubPayload(payload) {
        if (!payload || typeof payload !== "object") return;

        if ("items" in payload || "sessions" in payload) {
            visibleSessionIds = collectVisibleIds(payload);
            hasSeenSessionsPayload = true;
        }

        const activeId = clean(payload.active_session_id);

        if (activeId && isBlockedSessionId(activeId)) {
            payload.active_session_id = "";
            removeActiveStorage("response active id not visible: " + activeId);
        }

        if (!visibleSessionIds.size && hasSeenSessionsPayload) {
            removeActiveStorage("empty scoped session list");
        }
    }

    function installFetchHook() {
        if (window.__novaMobileScopeFetchLock20260623) return;

        window.__novaMobileScopeFetchLock20260623 = true;

        const originalFetch = window.fetch;

        if (typeof originalFetch !== "function") return;

        window.fetch = function () {
            const args = arguments;
            const url = clean(args[0] && args[0].url || args[0] || "");

            return originalFetch.apply(this, args).then(function (response) {
                try {
                    if (url.includes("/api/sessions")) {
                        response.clone().json().then(scrubPayload).catch(function () {});
                    }
                } catch (_) {}

                return response;
            });
        };
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

            scrubPayload(payload);

            return payload;
        } catch (error) {
            console.warn("[" + FIX_ID + "] check failed", error);
            return null;
        }
    }

    function boot() {
        installStorageSetItemLock();
        installGlobalLocks();
        installFetchHook();

        removeActiveStorage("boot cleanup");

        [80, 400, 1000, 1800, 3000].forEach(function (delay) {
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
        clear: removeActiveStorage,
        visibleIds: function () {
            return Array.from(visibleSessionIds);
        }
    };
})();
