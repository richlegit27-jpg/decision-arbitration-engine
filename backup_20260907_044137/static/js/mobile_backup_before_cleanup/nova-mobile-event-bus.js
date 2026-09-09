/**
 * NOVA MOBILE EVENT BUS (CLICK SYSTEM)
 * ------------------------------------
 * Single global click dispatcher.
 *
 * RULE:
 * - DO NOT use document.addEventListener("click", ...)
 *   anywhere else in the app.
 *
 * - All click handling must go through:
 *   window.NovaEventBus.onClick(fn)
 */

(function () {
    "use strict";

    // Prevent double initialization
    if (window.__NOVA_EVENT_BUS_V1__) {
        console.warn("[NOVA EVENT BUS] already initialized");
        return;
    }
    window.__NOVA_EVENT_BUS_V1__ = true;

    // -----------------------------
    // INTERNAL STATE
    // -----------------------------
    const handlers = new Set();

    function onClick(fn) {
        if (typeof fn !== "function") return;
        handlers.add(fn);
    }

    function offClick(fn) {
        handlers.delete(fn);
    }

    function clear() {
        handlers.clear();
    }

    function count() {
        return handlers.size;
    }

    // -----------------------------
    // SINGLE GLOBAL LISTENER
    // -----------------------------
    document.addEventListener(
        "click",
        function globalClickHandler(event) {
            const list = Array.from(handlers);

            for (let i = 0; i < list.length; i++) {
                try {
                    list[i](event);
                } catch (err) {
                    console.error("[NovaEventBus] handler error:", err);
                }
            }
        },
        true
    );

    // -----------------------------
    // PUBLIC API
    // -----------------------------
    window.NovaEventBus = {
        onClick,
        offClick,
        clear,
        count
    };

    // -----------------------------
    // DEBUG TOOLING
    // -----------------------------
    window.__novaEventBusDebug = function () {
        console.log("[NovaEventBus] handlers:", handlers.size);
        console.log(Array.from(handlers));
    };

    console.log("[NovaEventBus] initialized");
})();