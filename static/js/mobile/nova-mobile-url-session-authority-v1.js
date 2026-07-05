(function () {
    "use strict";

    const MARK = "NOVA_MOBILE_URL_SESSION_AUTHORITY_V2_20260704";

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

    function getMessages(payload) {
        if (!payload || !payload.session || !Array.isArray(payload.session.messages)) {
            return [];
        }

        return payload.session.messages;
    }

    function makeBubble(message) {
        const role = String(message.role || "assistant").toLowerCase();
        const div = document.createElement("div");

        div.className = [
            "nova-mobile-visible-message-v1",
            "nova-mobile-polished-bubble",
            role === "user" ? "nova-mobile-polished-user" : "nova-mobile-polished-assistant"
        ].join(" ");

        div.dataset.novaUrlSessionAuthorityRendered = "1";
        div.dataset.role = role;
        div.textContent = message.text || message.content || "";

        return div;
    }

    function directRenderMessages(payload) {
        const chat = document.getElementById("mobileChatMessages");
        const messages = getMessages(payload);

        if (!chat || !messages.length) {
            return {
                ok: false,
                reason: !chat ? "missing chat node" : "no messages",
                count: 0
            };
        }

        chat.innerHTML = "";

        messages.forEach(function (message) {
            chat.appendChild(makeBubble(message));
        });

        try {
            chat.scrollTop = chat.scrollHeight;
        } catch (_) {}

        return {
            ok: true,
            count: messages.length
        };
    }

    function renderPayload(payload) {
        let recoveryRendered = false;

        const renderer = window.NovaMobileChatVisibleRecoveryV1;

        if (renderer && typeof renderer.renderPayload === "function") {
            try {
                renderer.renderPayload(payload);
                recoveryRendered = true;
            } catch (err) {
                console.error("[Nova URL Session Authority V2] recovery renderer failed", err);
            }
        }

        const direct = directRenderMessages(payload);

        return {
            recoveryRendered: recoveryRendered,
            direct: direct
        };
    }

    async function forceUrlSession() {
        const sessionId = getUrlSessionId();

        if (!sessionId) {
            return;
        }

        storeSessionId(sessionId);

        try {
            const res = await fetch("/api/sessions/" + encodeURIComponent(sessionId) + "?url_session_authority_v2=" + Date.now(), {
                credentials: "include",
                cache: "no-store"
            });

            if (!res.ok) {
                console.error("[Nova URL Session Authority V2] fetch failed", res.status);
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

            const result = renderPayload(payload);

            setTimeout(function () {
                const lateResult = renderPayload(payload);
                console.error("[Nova URL Session Authority V2] late render", {
                    sessionId: sessionId,
                    result: lateResult,
                    messageCount: getMessages(payload).length
                });
            }, 700);

            console.error("[Nova URL Session Authority V2] forced url session", {
                sessionId: sessionId,
                result: result,
                messageCount: getMessages(payload).length
            });
        } catch (err) {
            console.error("[Nova URL Session Authority V2] error", err);
        }
    }

    window.NovaMobileUrlSessionAuthorityV2 = {
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

/* NOVA_URL_AUTHORITY_TOP_LAYOUT_BRIDGE_V1_START */
(function () {
    "use strict";

    if (window.__NOVA_URL_AUTHORITY_TOP_LAYOUT_BRIDGE_V1_20260704__) {
        return;
    }

    window.__NOVA_URL_AUTHORITY_TOP_LAYOUT_BRIDGE_V1_20260704__ = true;

    let scheduled = false;

    function applyTopLayout(reason) {
        if (scheduled) {
            return;
        }

        scheduled = true;

        requestAnimationFrame(function () {
            scheduled = false;

            try {
                if (
                    window.NovaMobileTopButtonLayoutV3 &&
                    typeof window.NovaMobileTopButtonLayoutV3.apply === "function"
                ) {
                    window.NovaMobileTopButtonLayoutV3.apply();

                    setTimeout(function () {
                        try {
                            window.NovaMobileTopButtonLayoutV3.apply();
                        } catch (_) {}
                    }, 80);

                    console.log("[Nova URL Authority Top Layout Bridge V1] applied", reason);
                }
            } catch (err) {
                console.warn("[Nova URL Authority Top Layout Bridge V1] failed", err);
            }
        });
    }

    window.NovaUrlAuthorityApplyTopLayoutV1 = applyTopLayout;

    function startObserver() {
        if (!document.body) {
            setTimeout(startObserver, 50);
            return;
        }

        const observer = new MutationObserver(function () {
            applyTopLayout("mutation");
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        applyTopLayout("boot");

        setTimeout(function () { applyTopLayout("late-250"); }, 250);
        setTimeout(function () { applyTopLayout("late-750"); }, 750);
        setTimeout(function () { applyTopLayout("late-1500"); }, 1500);
        setTimeout(function () { applyTopLayout("late-3000"); }, 3000);

        console.log("[Nova URL Authority Top Layout Bridge V1] installed");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", startObserver, { once: true });
    } else {
        startObserver();
    }
})();
/* NOVA_URL_AUTHORITY_TOP_LAYOUT_BRIDGE_V1_END */

