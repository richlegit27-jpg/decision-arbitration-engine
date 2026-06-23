/*
NOVA_MOBILE_FINAL_POLISH_GUARD_20260623
Final guard:
- keeps Summary + 4 Horsemen panel docked and visible
- strips menu-panel classes from Summary
- fixes aria-hidden focus warning when panels close
- hides stray attachment ? markers
*/

(function () {
    "use strict";

    const FIX_ID = "NOVA_MOBILE_FINAL_POLISH_GUARD_20260623";

    const BAD_SUMMARY_CLASSES = [
        "nova-mobile-tools-menu-fixed",
        "nova-mobile-menu-panel-fixed",
        "nova-mobile-panel-fixed",
        "mobile-menu-panel-fixed",
        "hidden",
        "is-hidden",
        "nova-hidden",
        "d-none"
    ];

    function $(id) {
        return document.getElementById(id);
    }

    function composer() {
        return (
            $("nova-mobile-composer") ||
            document.querySelector(".nova-mobile-composer") ||
            document.querySelector(".mobile-composer") ||
            document.querySelector("footer")
        );
    }

    function summaryPanel() {
        return $("nova-mobile-summary-horsemen");
    }

    function cleanSummaryPanel() {
        const panel = summaryPanel();

        if (!panel) {
            if (window.NovaMobileSummaryHorsemen && typeof window.NovaMobileSummaryHorsemen.boot === "function") {
                try {
                    window.NovaMobileSummaryHorsemen.boot();
                } catch (_) {}
            }
            return;
        }

        BAD_SUMMARY_CLASSES.forEach(function (name) {
            panel.classList.remove(name);
        });

        panel.hidden = false;
        panel.removeAttribute("aria-hidden");
        panel.setAttribute("data-nova-summary-panel", "true");

        panel.style.display = "block";
        panel.style.visibility = "visible";
        panel.style.opacity = "1";
        panel.style.pointerEvents = "auto";
        panel.style.position = "relative";
        panel.style.inset = "auto";
        panel.style.left = "auto";
        panel.style.right = "auto";
        panel.style.top = "auto";
        panel.style.bottom = "auto";
        panel.style.transform = "none";
        panel.style.maxHeight = "none";
        panel.style.overflow = "visible";
        panel.style.zIndex = "20";

        const c = composer();

        if (c && c.parentNode && panel.nextElementSibling !== c) {
            c.parentNode.insertBefore(panel, c);
        }
    }

    function activeInside(node) {
        return !!(node && document.activeElement && node.contains(document.activeElement));
    }

    function panelIsHidden(panel) {
        if (!panel) return false;

        return (
            panel.hidden ||
            panel.getAttribute("aria-hidden") === "true" ||
            panel.classList.contains("hidden") ||
            panel.classList.contains("is-hidden") ||
            panel.style.display === "none"
        );
    }

    function blurIfHiddenPanelHasFocus() {
        const panels = Array.from(document.querySelectorAll([
            ".mobile-panel",
            ".nova-mobile-menu-panel-fixed",
            ".nova-mobile-tools-menu-fixed",
            "#nova-mobile-artifacts-panel",
            "#nova-mobile-memory-panel",
            "#nova-mobile-sessions-panel",
            "#nova-mobile-tools-panel"
        ].join(",")));

        panels.forEach(function (panel) {
            if (panelIsHidden(panel) && activeInside(panel)) {
                try {
                    document.activeElement.blur();
                } catch (_) {}
            }
        });
    }

    function closeButtonBlurGuard(event) {
        const target = event.target && event.target.closest && event.target.closest([
            "#nova-mobile-artifacts-close",
            "#nova-mobile-memory-close",
            "#nova-mobile-sessions-close",
            "#nova-mobile-tools-close",
            "[id$='-close']",
            "[aria-label*='close' i]",
            "[data-action='close']"
        ].join(","));

        if (!target) return;

        try {
            target.blur();
        } catch (_) {}

        if (document.activeElement && document.activeElement !== document.body) {
            try {
                document.activeElement.blur();
            } catch (_) {}
        }
    }

    function hideStrayQuestionMarks() {
        const chips = Array.from(document.querySelectorAll([
            ".nova-mobile-attachment-chip",
            ".mobile-attachment-chip",
            ".attachment-chip",
            ".nova-attachment-chip",
            "[data-mobile-attachment-chip]",
            "[class*='attachment'][class*='chip']"
        ].join(",")));

        chips.forEach(function (chip) {
            Array.from(chip.querySelectorAll("span, small, em, i, b, div")).forEach(function (node) {
                const value = String(node.textContent || "").trim();

                if (value === "?") {
                    node.style.display = "none";
                    node.setAttribute("aria-hidden", "true");
                }
            });
        });
    }

    function polish() {
        cleanSummaryPanel();
        blurIfHiddenPanelHasFocus();
        hideStrayQuestionMarks();
    }

    function installObserver() {
        if (window.__novaMobileFinalPolishGuardObserver) {
            window.__novaMobileFinalPolishGuardObserver.disconnect();
        }

        let queued = false;

        window.__novaMobileFinalPolishGuardObserver = new MutationObserver(function () {
            if (queued) return;

            queued = true;

            requestAnimationFrame(function () {
                queued = false;
                polish();
            });
        });

        window.__novaMobileFinalPolishGuardObserver.observe(document.body, {
            subtree: true,
            childList: true,
            attributes: true,
            attributeFilter: ["class", "style", "hidden", "aria-hidden"]
        });
    }

    function boot() {
        document.addEventListener("pointerdown", closeButtonBlurGuard, true);
        document.addEventListener("click", closeButtonBlurGuard, true);

        polish();
        installObserver();

        window.clearInterval(window.__novaMobileFinalPolishGuardTimer);
        window.__novaMobileFinalPolishGuardTimer = window.setInterval(polish, 1500);

        console.log("[" + FIX_ID + "] ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    window.NovaMobileFinalPolishGuard = {
        polish: polish,
        cleanSummaryPanel: cleanSummaryPanel
    };

    window.NovaMobileSummaryHorsemenPolish = {
        polish: polish
    };
})();
