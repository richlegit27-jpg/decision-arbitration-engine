(function () {
    "use strict";

    if (window.__NOVA_MOBILE_ACTIVE_SESSION_SANITIZER_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_ACTIVE_SESSION_SANITIZER_V1_20260703__ = true;

    var VERSION = "active-session-sanitizer-v1-20260703";

    function isValidSessionId(value) {
        if (!value) {
            return false;
        }

        var text = String(value).trim();

        if (!text) {
            return false;
        }

        if (
            text === "null" ||
            text === "undefined" ||
            text.indexOf("=") === 0 ||
            text.indexOf(" ") >= 0
        ) {
            return false;
        }

        return (
            text.indexOf("session_") === 0 ||
            text.indexOf("mobile_") === 0 ||
            text.indexOf("debug_") === 0 ||
            text.indexOf("regression_") === 0
        );
    }

    function getUrlSessionId() {
        try {
            return new URL(window.location.href).searchParams.get("session_id");
        } catch (err) {
            return null;
        }
    }

    function setUrlSessionId(sessionId) {
        try {
            var url = new URL(window.location.href);
            url.searchParams.set("session_id", sessionId);
            window.history.replaceState(null, "", url.pathname + url.search + url.hash);
        } catch (err) {
            console.warn("[Nova Mobile Active Session Sanitizer] URL replace failed", err);
        }
    }

    function saveSessionId(sessionId) {
        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.removeItem("active_session_id");
        } catch (err) {
            console.warn("[Nova Mobile Active Session Sanitizer] localStorage save failed", err);
        }
    }

    function getStoredSessionId() {
        try {
            return (
                localStorage.getItem("nova_mobile_active_session_id") ||
                localStorage.getItem("nova_active_session_id") ||
                localStorage.getItem("active_session_id")
            );
        } catch (err) {
            return null;
        }
    }

    function extractSessionId(session) {
        if (!session) {
            return null;
        }

        return session.session_id || session.id || null;
    }

    function sleep(ms) {
        return new Promise(function (resolve) {
            setTimeout(resolve, ms);
        });
    }

    async function fetchJson(url) {
        var response = await fetch(url, {
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        });

        return await response.json();
    }

    async function waitForRecoveryRenderer() {
        var i;

        for (i = 0; i < 40; i += 1) {
            if (
                window.NovaMobileChatVisibleRecoveryV1 &&
                typeof window.NovaMobileChatVisibleRecoveryV1.renderPayload === "function"
            ) {
                return window.NovaMobileChatVisibleRecoveryV1;
            }

            await sleep(50);
        }

        return null;
    }

    async function renderSession(sessionId) {
        var payload;
        var renderer;

        if (!isValidSessionId(sessionId)) {
            return;
        }

        payload = await fetchJson(
            "/api/sessions/" +
                encodeURIComponent(sessionId) +
                "?cache_bust=" +
                Date.now()
        );

        if (!payload || payload.ok === false || !payload.session) {
            console.warn("[Nova Mobile Active Session Sanitizer] session payload failed", payload);
            return;
        }

        renderer = await waitForRecoveryRenderer();

        if (!renderer) {
            console.warn("[Nova Mobile Active Session Sanitizer] recovery renderer not available");
            return;
        }

        renderer.renderPayload(payload);

        console.log(
            "[Nova Mobile Active Session Sanitizer] rendered",
            sessionId,
            "messages:",
            payload.session.messages ? payload.session.messages.length : 0
        );
    }

    async function resolveActiveSession() {
        var list;
        var urlSessionId;
        var storedSessionId;
        var candidate;
        var sessions;
        var validIds;
        var i;
        var id;
        var activeSessionId;

        urlSessionId = getUrlSessionId();
        storedSessionId = getStoredSessionId();

        candidate = null;

        if (isValidSessionId(urlSessionId)) {
            candidate = String(urlSessionId).trim();
        } else if (isValidSessionId(storedSessionId)) {
            candidate = String(storedSessionId).trim();
        }

        list = await fetchJson("/api/sessions?cache_bust=" + Date.now());

        if (!list || list.ok === false) {
            console.warn("[Nova Mobile Active Session Sanitizer] session list failed", list);
            return candidate;
        }

        sessions = Array.isArray(list.sessions) ? list.sessions : [];
        validIds = {};

        for (i = 0; i < sessions.length; i += 1) {
            id = extractSessionId(sessions[i]);

            if (isValidSessionId(id)) {
                validIds[String(id).trim()] = true;
            }
        }

        activeSessionId = list.active_session_id;

        if (!isValidSessionId(candidate) || !validIds[candidate]) {
            if (isValidSessionId(activeSessionId) && validIds[String(activeSessionId).trim()]) {
                candidate = String(activeSessionId).trim();
            } else {
                candidate = null;

                for (id in validIds) {
                    if (Object.prototype.hasOwnProperty.call(validIds, id)) {
                        candidate = id;
                        break;
                    }
                }
            }
        }

        if (isValidSessionId(candidate)) {
            saveSessionId(candidate);
            setUrlSessionId(candidate);

            window.NovaMobileActiveSessionId = candidate;

            window.dispatchEvent(
                new CustomEvent("nova-mobile-active-session-resolved", {
                    detail: {
                        session_id: candidate,
                        version: VERSION
                    }
                })
            );

            console.log("[Nova Mobile Active Session Sanitizer] active:", candidate);

            await renderSession(candidate);

            return candidate;
        }

        console.warn("[Nova Mobile Active Session Sanitizer] no valid session found");
        return null;
    }

    window.NovaMobileActiveSessionSanitizerV1 = {
        version: VERSION,
        isValidSessionId: isValidSessionId,
        resolveActiveSession: resolveActiveSession
    };

    resolveActiveSession().catch(function (err) {
        console.error("[Nova Mobile Active Session Sanitizer] failed", err);
    });
}());
