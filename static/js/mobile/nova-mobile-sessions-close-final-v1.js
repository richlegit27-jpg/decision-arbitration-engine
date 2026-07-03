/* NOVA_MOBILE_SESSIONS_CLOSE_FINAL_V1_20260703 */
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSIONS_CLOSE_FINAL_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_SESSIONS_CLOSE_FINAL_V1_20260703__ = true;

    function $(id) {
        return document.getElementById(id);
    }

    function showMainLayout() {
        var shell = document.querySelector(".mobile-shell");
        var messages = $("mobileChatMessages");
        var composer = $("nova-mobile-composer");

        [shell, messages, composer].forEach(function (el) {
            if (!el) return;
            el.style.removeProperty("height");
            el.style.removeProperty("max-height");
            el.style.removeProperty("min-height");
            el.style.removeProperty("overflow");
            el.style.removeProperty("transform");
        });

        if (messages) {
            messages.style.setProperty("display", "block", "important");
            messages.style.setProperty("visibility", "visible", "important");
            messages.style.setProperty("opacity", "1", "important");
            messages.style.setProperty("pointer-events", "auto", "important");
        }

        if (composer) {
            composer.style.setProperty("display", "flex", "important");
            composer.style.setProperty("visibility", "visible", "important");
            composer.style.setProperty("opacity", "1", "important");
            composer.style.setProperty("pointer-events", "auto", "important");
        }

        document.documentElement.classList.remove(
            "nova-mobile-sessions-open",
            "nova-sessions-open",
            "sessions-open"
        );

        if (document.body) {
            document.body.classList.remove(
                "nova-mobile-sessions-open",
                "nova-sessions-open",
                "sessions-open"
            );
        }
    }

    function hardCloseSessions(reason) {
        var panel = $("nova-mobile-sessions-panel");

        if (!panel) {
            showMainLayout();
            return false;
        }

        panel.classList.add("hidden");
        panel.setAttribute("aria-hidden", "true");
        panel.setAttribute("data-nova-sessions-open", "false");
        panel.dataset.novaSessionsOpen = "false";

        panel.style.setProperty("display", "none", "important");
        panel.style.setProperty("visibility", "hidden", "important");
        panel.style.setProperty("opacity", "0", "important");
        panel.style.setProperty("pointer-events", "none", "important");
        panel.style.removeProperty("height");
        panel.style.removeProperty("max-height");
        panel.style.removeProperty("min-height");
        panel.style.removeProperty("overflow");
        panel.style.removeProperty("transform");

        showMainLayout();

        window.__NOVA_MOBILE_LAST_SESSIONS_CLOSE_FINAL__ = {
            reason: reason || "unknown",
            at: new Date().toISOString()
        };

        return true;
    }

    function looksLikeCloseSessions(el) {
        if (!el) return false;

        var text = String(el.textContent || el.value || "").replace(/\s+/g, " ").trim().toLowerCase();
        var id = String(el.id || "").toLowerCase();
        var action = String(el.getAttribute && (
            el.getAttribute("data-action") ||
            el.getAttribute("data-mobile-action") ||
            el.getAttribute("aria-label") ||
            el.getAttribute("title") ||
            ""
        )).toLowerCase();

        if (text === "close sessions") return true;
        if (text === "close" && el.closest && el.closest("#nova-mobile-sessions-panel")) return true;
        if (id.includes("sessions") && id.includes("close")) return true;
        if (action.includes("close") && action.includes("session")) return true;

        return false;
    }

    function wireExistingCloseButtons() {
        document.querySelectorAll(
            "#nova-mobile-sessions-panel button, " +
            "#nova-mobile-sessions-panel a, " +
            "#nova-mobile-sessions-panel [role='button'], " +
            "button, a, [role='button']"
        ).forEach(function (el) {
            if (!looksLikeCloseSessions(el)) return;
            if (el.dataset.novaSessionsCloseFinalWired === "1") return;

            el.dataset.novaSessionsCloseFinalWired = "1";
            el.removeAttribute("onclick");

            el.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                if (event.stopImmediatePropagation) {
                    event.stopImmediatePropagation();
                }
                hardCloseSessions("wired-button");
                return false;
            }, true);
        });
    }

    document.addEventListener("click", function (event) {
        var target = event.target && event.target.closest
            ? event.target.closest("button, a, [role='button'], [data-action], [aria-label]")
            : null;

        if (!looksLikeCloseSessions(target)) return;

        event.preventDefault();
        event.stopPropagation();

        if (event.stopImmediatePropagation) {
            event.stopImmediatePropagation();
        }

        hardCloseSessions("captured-click");
        return false;
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            hardCloseSessions("escape");
        }
    }, true);

    window.NovaMobileCloseSessionsFinal = hardCloseSessions;
    window.NovaMobileCloseSessions = hardCloseSessions;
    window.NovaCloseMobileSessions = hardCloseSessions;

    function boot() {
        wireExistingCloseButtons();

        var panel = $("nova-mobile-sessions-panel");
        if (panel && panel.classList.contains("hidden")) {
            hardCloseSessions("boot-hidden");
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    var observer = new MutationObserver(function () {
        wireExistingCloseButtons();
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true
    });

    console.log("[NOVA_MOBILE_SESSIONS_CLOSE_FINAL_V1_20260703] ready");
})();
