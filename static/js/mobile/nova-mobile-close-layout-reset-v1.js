(function () {
    "use strict";

    const MARKER = "NOVA_MOBILE_CLOSE_LAYOUT_RESET_V1_20260703";

    if (window.__NOVA_MOBILE_CLOSE_LAYOUT_RESET_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_CLOSE_LAYOUT_RESET_V1_20260703__ = true;

    const OPEN_CLASSES = [
        "drawer-open",
        "sidebar-open",
        "sessions-open",
        "session-panel-open",
        "nova-session-panel-open",
        "nova-mobile-session-panel-open",
        "nova-mobile-drawer-open",
        "mobile-drawer-open"
    ];

    const ROOT_SELECTORS = [
        "html",
        "body",
        "#app",
        "#root",
        "main",
        ".nova-mobile-shell",
        ".mobile-shell",
        ".nova-mobile-app",
        ".nova-mobile-root"
    ];

    function isCloseTarget(target) {
        if (!target) {
            return false;
        }

        const el = target.closest && target.closest("button, [role='button'], [aria-label], [title], [id], [class], [data-action]");
        if (!el) {
            return false;
        }

        const text = String(el.textContent || "").trim().toLowerCase();
        const aria = String(el.getAttribute("aria-label") || "").trim().toLowerCase();
        const title = String(el.getAttribute("title") || "").trim().toLowerCase();
        const id = String(el.id || "").trim().toLowerCase();
        const cls = String(el.className || "").trim().toLowerCase();
        const action = String(el.getAttribute("data-action") || "").trim().toLowerCase();

        const looksClose =
            text === "close" ||
            text === "×" ||
            text === "x" ||
            aria.includes("close") ||
            title.includes("close") ||
            id.includes("close") ||
            cls.includes("close") ||
            action.includes("close");

        const looksSession =
            id.includes("session") ||
            cls.includes("session") ||
            action.includes("session") ||
            Boolean(el.closest && el.closest("[id*='session'], [class*='session']"));

        return looksClose && looksSession;
    }

    function resetLayout(reason) {
        try {
            for (const cls of OPEN_CLASSES) {
                document.documentElement.classList.remove(cls);
                document.body.classList.remove(cls);
            }

            for (const selector of ROOT_SELECTORS) {
                for (const el of document.querySelectorAll(selector)) {
                    el.style.transform = "";
                    el.style.translate = "";
                    el.style.left = "";
                    el.style.right = "";
                    el.style.marginLeft = "";
                    el.style.marginRight = "";
                    el.style.width = "";
                    el.style.maxWidth = "";
                    el.style.minWidth = "";
                }
            }

            document.documentElement.style.width = "100%";
            document.documentElement.style.maxWidth = "100%";
            document.documentElement.style.overflowX = "hidden";

            document.body.style.width = "100%";
            document.body.style.maxWidth = "100%";
            document.body.style.overflowX = "hidden";
            document.body.style.position = "relative";
            document.body.style.left = "0";
            document.body.style.transform = "none";

            for (const el of document.querySelectorAll("*")) {
                const r = el.getBoundingClientRect();

                if (r.left < -5 || r.width > window.innerWidth + 20) {
                    el.style.left = "0";
                    el.style.right = "";
                    el.style.transform = "none";
                    el.style.translate = "";
                    el.style.maxWidth = "100vw";
                    el.style.overflowX = "hidden";
                }
            }

            console.log("[Nova Mobile Close Layout Reset V1] reset", reason, window.innerWidth);
        } catch (exc) {
            console.warn("[Nova Mobile Close Layout Reset V1] failed", exc);
        }
    }

    document.addEventListener("click", function (event) {
        if (!isCloseTarget(event.target)) {
            return;
        }

        window.setTimeout(function () {
            resetLayout("close-click");
        }, 0);

        window.setTimeout(function () {
            resetLayout("close-click-late");
        }, 150);
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") {
            return;
        }

        window.setTimeout(function () {
            resetLayout("escape");
        }, 0);
    }, true);

    window.NovaMobileCloseLayoutResetV1 = {
        marker: MARKER,
        resetLayout,
        isCloseTarget
    };

    console.log("[Nova Mobile Close Layout Reset V1] installed");
})();

