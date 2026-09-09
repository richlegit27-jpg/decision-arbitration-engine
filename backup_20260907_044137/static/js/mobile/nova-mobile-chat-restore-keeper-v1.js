(function () {
    "use strict";

    if (window.__NOVA_MOBILE_CHAT_RESTORE_KEEPER_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_CHAT_RESTORE_KEEPER_V1_20260703__ = true;

    var VERSION = "chat-restore-keeper-v1-20260703";
    var lastPayload = null;
    var lastSessionId = null;
    var restoring = false;
    var observerReady = false;

    function isValidSessionId(value) {
        var text;

        if (!value) {
            return false;
        }

        text = String(value).trim();

        if (
            !text ||
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

    function getActiveSessionId() {
        var id;

        id =
            window.NovaMobileActiveSessionId ||
            getUrlSessionId() ||
            getStoredSessionId();

        if (isValidSessionId(id)) {
            return String(id).trim();
        }

        return null;
    }

    function getChat() {
        return document.getElementById("mobileChatMessages");
    }

    function getVisibleCount() {
        var chat = getChat();

        if (!chat) {
            return 0;
        }

        return chat.children ? chat.children.length : 0;
    }

    function getPayloadMessageCount(payload) {
        if (
            payload &&
            payload.session &&
            Array.isArray(payload.session.messages)
        ) {
            return payload.session.messages.length;
        }

        return 0;
    }

    function sleep(ms) {
        return new Promise(function (resolve) {
            setTimeout(resolve, ms);
        });
    }

    async function fetchJson(url) {
        var response;
        var text;
        var data;

        response = await fetch(url, {
            method: "GET",
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        });

        text = await response.text();

        try {
            data = text ? JSON.parse(text) : {};
        } catch (err) {
            data = {
                ok: false,
                error: text || response.statusText
            };
        }

        if (!response.ok || data.ok === false) {
            throw new Error(data.error || response.statusText || ("HTTP " + response.status));
        }

        return data;
    }

    async function waitForRenderer() {
        var i;

        for (i = 0; i < 80; i += 1) {
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

    async function renderPayload(payload, reason) {
        var renderer;
        var count;

        if (restoring) {
            return false;
        }

        count = getPayloadMessageCount(payload);

        if (!count) {
            return false;
        }

        restoring = true;

        try {
            renderer = await waitForRenderer();

            if (!renderer) {
                console.warn("[Nova Chat Restore Keeper] renderer missing");
                return false;
            }

            renderer.renderPayload(payload);

            console.log(
                "[Nova Chat Restore Keeper] rendered",
                reason || "restore",
                "messages:",
                count,
                "children:",
                getVisibleCount()
            );

            return true;
        } catch (err) {
            console.error("[Nova Chat Restore Keeper] render failed", err);
            return false;
        } finally {
            restoring = false;
        }
    }

    async function loadAndRender(reason) {
        var sessionId;
        var payload;
        var messageCount;

        sessionId = getActiveSessionId();

        if (!isValidSessionId(sessionId)) {
            return;
        }

        payload = await fetchJson(
            "/api/sessions/" +
                encodeURIComponent(sessionId) +
                "?cache_bust=" +
                Date.now()
        );

        messageCount = getPayloadMessageCount(payload);

        lastSessionId = sessionId;

        if (!messageCount) {
            lastPayload = null;
            console.log("[Nova Chat Restore Keeper] active session empty", sessionId);
            return;
        }

        lastPayload = payload;

        await renderPayload(payload, reason || "load");
    }

    function shouldRestoreLastPayload() {
        var sessionId;

        sessionId = getActiveSessionId();

        return (
            lastPayload &&
            isValidSessionId(lastSessionId) &&
            sessionId === lastSessionId &&
            getPayloadMessageCount(lastPayload) > 0 &&
            getVisibleCount() === 0
        );
    }

    function scheduleRestore(reason, delay) {
        setTimeout(function () {
            if (shouldRestoreLastPayload()) {
                renderPayload(lastPayload, reason || "watchdog");
            }
        }, delay || 120);
    }

    function watchChatClears() {
        var chat;

        if (observerReady) {
            return;
        }

        chat = getChat();

        if (!chat) {
            setTimeout(watchChatClears, 250);
            return;
        }

        observerReady = true;

        try {
            new MutationObserver(function () {
                if (shouldRestoreLastPayload()) {
                    scheduleRestore("chat-was-cleared", 160);
                }
            }).observe(chat, {
                childList: true,
                subtree: false
            });
        } catch (err) {
            setInterval(function () {
                if (shouldRestoreLastPayload()) {
                    renderPayload(lastPayload, "interval-watchdog");
                }
            }, 1000);
        }
    }

    function boot() {
        var delays;

        watchChatClears();

        delays = [0, 250, 750, 1500, 3000, 5000];

        delays.forEach(function (delay) {
            setTimeout(function () {
                loadAndRender("boot-" + delay).catch(function (err) {
                    console.warn("[Nova Chat Restore Keeper] boot load failed", err);
                });
            }, delay);
        });

        window.addEventListener("nova-mobile-active-session-resolved", function () {
            loadAndRender("active-session-resolved").catch(function (err) {
                console.warn("[Nova Chat Restore Keeper] active resolve failed", err);
            });
        });

        window.addEventListener("nova-mobile-session-opened", function () {
            loadAndRender("session-opened").catch(function (err) {
                console.warn("[Nova Chat Restore Keeper] session opened failed", err);
            });

            scheduleRestore("session-opened-watchdog", 800);
            scheduleRestore("session-opened-watchdog-late", 1800);
        });

        window.addEventListener("popstate", function () {
            loadAndRender("popstate").catch(function (err) {
                console.warn("[Nova Chat Restore Keeper] popstate failed", err);
            });
        });

        console.log("[Nova Chat Restore Keeper] ready", VERSION);
    }

    window.NovaMobileChatRestoreKeeperV1 = {
        version: VERSION,
        loadAndRender: loadAndRender,
        renderLast: function () {
            return renderPayload(lastPayload, "manual");
        },
        getLastSessionId: function () {
            return lastSessionId;
        },
        getVisibleCount: getVisibleCount
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
}());
