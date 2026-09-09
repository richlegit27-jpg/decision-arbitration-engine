(function () {
    "use strict";

    const MARKER = "NOVA_MOBILE_SEND_DEDUPE_GUARD_V1_20260703";

    if (window.__NOVA_MOBILE_SEND_DEDUPE_GUARD_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_SEND_DEDUPE_GUARD_V1_20260703__ = true;

    const SEND_LOCK_MS = 1400;

    function now() {
        return Date.now();
    }

    function getTextFromPage() {
        const candidates = [
            "#message-input",
            "#nova-mobile-input",
            "textarea[name='message']",
            "textarea",
            "input[type='text']"
        ];

        for (const selector of candidates) {
            const el = document.querySelector(selector);
            if (el && typeof el.value === "string" && el.value.trim()) {
                return el.value.trim();
            }
        }

        return "";
    }

    function isSendTarget(target) {
        if (!target) {
            return false;
        }

        const el = target.closest && target.closest("button, [role='button'], [data-action], [id], [class]");
        if (!el) {
            return false;
        }

        const text = String(el.textContent || "").trim().toLowerCase();
        const aria = String(el.getAttribute("aria-label") || "").trim().toLowerCase();
        const title = String(el.getAttribute("title") || "").trim().toLowerCase();
        const id = String(el.id || "").trim().toLowerCase();
        const cls = String(el.className || "").trim().toLowerCase();
        const action = String(el.getAttribute("data-action") || "").trim().toLowerCase();

        return (
            text === "send" ||
            aria.includes("send") ||
            title.includes("send") ||
            id.includes("send") ||
            cls.includes("send") ||
            action.includes("send")
        );
    }

    function shouldBlockSend(reason) {
        const text = getTextFromPage();
        const t = now();

        const last = window.__NOVA_MOBILE_LAST_SEND_GUARD__ || {
            time: 0,
            text: "",
            reason: ""
        };

        const sameText = text && last.text && text === last.text;
        const tooSoon = (t - Number(last.time || 0)) < SEND_LOCK_MS;

        if (sameText && tooSoon) {
            try {
                console.warn("[Nova Mobile Send Dedupe Guard V1] blocked duplicate send", {
                    reason,
                    text,
                    elapsed: t - Number(last.time || 0),
                    lastReason: last.reason
                });
            } catch (_) {}

            return true;
        }

        window.__NOVA_MOBILE_LAST_SEND_GUARD__ = {
            time: t,
            text,
            reason
        };

        return false;
    }

    document.addEventListener("click", function (event) {
        if (!isSendTarget(event.target)) {
            return;
        }

        if (shouldBlockSend("click")) {
            event.preventDefault();
            event.stopPropagation();

            if (event.stopImmediatePropagation) {
                event.stopImmediatePropagation();
            }
        }
    }, true);

    document.addEventListener("submit", function (event) {
        if (shouldBlockSend("submit")) {
            event.preventDefault();
            event.stopPropagation();

            if (event.stopImmediatePropagation) {
                event.stopImmediatePropagation();
            }
        }
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" || event.shiftKey) {
            return;
        }

        const target = event.target;
        const tag = String(target && target.tagName || "").toLowerCase();

        if (tag !== "textarea" && tag !== "input") {
            return;
        }

        if (shouldBlockSend("enter")) {
            event.preventDefault();
            event.stopPropagation();

            if (event.stopImmediatePropagation) {
                event.stopImmediatePropagation();
            }
        }
    }, true);

    window.NovaMobileSendDedupeGuardV1 = {
        marker: MARKER,
        shouldBlockSend,
        isSendTarget
    };

    try {
        console.log("[Nova Mobile Send Dedupe Guard V1] installed");
    } catch (_) {}
})();
