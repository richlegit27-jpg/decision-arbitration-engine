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

/* NOVA_MOBILE_FINAL_SCROLL_GEOMETRY_FORCE_20260624 */
(function () {
    "use strict";

    function imp(el, prop, value) {
        if (!el) return;
        el.style.setProperty(prop, value, "important");
    }

    function forceFinalScrollGeometry() {
        var chat = document.getElementById("mobileChatMessages");
        var comp = document.getElementById("nova-mobile-composer");
        var input = document.getElementById("nova-mobile-input");

        if (!chat || !comp) return;

        imp(comp, "position", "fixed");
        imp(comp, "left", "0px");
        imp(comp, "right", "0px");
        imp(comp, "bottom", "0px");
        imp(comp, "top", "auto");
        imp(comp, "max-height", "108px");
        imp(comp, "height", "auto");
        imp(comp, "overflow", "hidden");
        imp(comp, "z-index", "90");

        if (input) {
            imp(input, "min-height", "38px");
            imp(input, "max-height", "46px");
        }

        imp(chat, "position", "fixed");
        imp(chat, "top", "118px");
        imp(chat, "left", "0px");
        imp(chat, "right", "0px");
        imp(chat, "bottom", "118px");
        imp(chat, "height", "auto");
        imp(chat, "max-height", "none");
        imp(chat, "overflow-y", "auto");
        imp(chat, "overflow-x", "hidden");
        imp(chat, "padding-bottom", "24px");
        imp(chat, "z-index", "10");
    }

    window.NovaMobileFinalScrollGeometryForce = forceFinalScrollGeometry;
    window.NovaMobileMicroScrollTune = forceFinalScrollGeometry;

    window.addEventListener("load", function () {
        forceFinalScrollGeometry();
        setTimeout(forceFinalScrollGeometry, 250);
        setTimeout(forceFinalScrollGeometry, 900);
        setTimeout(forceFinalScrollGeometry, 1800);
    });

    window.addEventListener("pageshow", function () {
        setTimeout(forceFinalScrollGeometry, 120);
    });

    window.addEventListener("resize", forceFinalScrollGeometry);
    window.addEventListener("orientationchange", forceFinalScrollGeometry);

    document.addEventListener("click", function () {
        setTimeout(forceFinalScrollGeometry, 80);
    }, true);

    document.addEventListener("input", function () {
        setTimeout(forceFinalScrollGeometry, 80);
    }, true);

    setTimeout(forceFinalScrollGeometry, 100);
    setTimeout(forceFinalScrollGeometry, 700);
    setTimeout(forceFinalScrollGeometry, 1600);

    console.log("[NOVA_MOBILE_FINAL_SCROLL_GEOMETRY_FORCE_20260624] ready");
})();

/* NOVA_MOBILE_FINAL_SCROLL_GEOMETRY_FORCE_V2_20260624 */
(function () {
    "use strict";

    function imp(el, prop, value) {
        if (!el) return;
        el.style.setProperty(prop, value, "important");
    }

    function finalScrollGeometryForceV2() {
        var chat = document.getElementById("mobileChatMessages");
        var comp = document.getElementById("nova-mobile-composer");
        var input = document.getElementById("nova-mobile-input");

        if (!chat || !comp) return;

        chat.style.removeProperty("inset");
        chat.style.removeProperty("transform");

        imp(comp, "position", "fixed");
        imp(comp, "left", "0px");
        imp(comp, "right", "0px");
        imp(comp, "bottom", "0px");
        imp(comp, "top", "auto");
        imp(comp, "max-height", "108px");
        imp(comp, "height", "auto");
        imp(comp, "overflow", "hidden");
        imp(comp, "z-index", "90");

        if (input) {
            imp(input, "min-height", "38px");
            imp(input, "max-height", "46px");
        }

        imp(chat, "position", "fixed");
        imp(chat, "top", "68px");
        imp(chat, "left", "0px");
        imp(chat, "right", "0px");
        imp(chat, "bottom", "118px");
        imp(chat, "height", "auto");
        imp(chat, "max-height", "none");
        imp(chat, "overflow-y", "auto");
        imp(chat, "overflow-x", "hidden");
        imp(chat, "padding-bottom", "24px");
        imp(chat, "z-index", "10");
    }

    window.NovaMobileFinalScrollGeometryForce = finalScrollGeometryForceV2;
    window.NovaMobileMicroScrollTune = finalScrollGeometryForceV2;

    window.addEventListener("load", function () {
        setTimeout(finalScrollGeometryForceV2, 600);
        setTimeout(finalScrollGeometryForceV2, 1600);
        setTimeout(finalScrollGeometryForceV2, 3200);
        setTimeout(finalScrollGeometryForceV2, 5200);
    });

    window.addEventListener("pageshow", function () {
        setTimeout(finalScrollGeometryForceV2, 600);
        setTimeout(finalScrollGeometryForceV2, 1600);
    });

    document.addEventListener("click", function () {
        setTimeout(finalScrollGeometryForceV2, 100);
    }, true);

    document.addEventListener("input", function () {
        setTimeout(finalScrollGeometryForceV2, 100);
    }, true);

    setTimeout(finalScrollGeometryForceV2, 900);
    setTimeout(finalScrollGeometryForceV2, 2500);
    setTimeout(finalScrollGeometryForceV2, 5000);

    console.log("[NOVA_MOBILE_FINAL_SCROLL_GEOMETRY_FORCE_V2_20260624] ready");
})();

/* NOVA_MOBILE_TOP_BUTTON_POLISH_20260624 */
(function () {
    "use strict";

    function imp(el, prop, value) {
        if (!el) return;
        el.style.setProperty(prop, value, "important");
    }

    function polishTopButtons() {
        var newBtn = document.getElementById("mobileMenuButton");
        var sessionsBtn = document.getElementById("mobileMemoryButton");

        var visibleTopButtons = [newBtn, sessionsBtn].filter(Boolean);

        visibleTopButtons.forEach(function (btn) {
            imp(btn, "display", "inline-flex");
            imp(btn, "align-items", "center");
            imp(btn, "justify-content", "center");
            imp(btn, "height", "36px");
            imp(btn, "min-height", "36px");
            imp(btn, "max-height", "36px");
            imp(btn, "padding", "0 14px");
            imp(btn, "border-radius", "999px");
            imp(btn, "font-size", "13px");
            imp(btn, "font-weight", "800");
            imp(btn, "line-height", "1");
            imp(btn, "letter-spacing", "0.01em");
            imp(btn, "color", "#f7f2ff");
            imp(btn, "background", "linear-gradient(135deg, rgba(168, 85, 247, 0.32), rgba(124, 58, 237, 0.18))");
            imp(btn, "border", "1px solid rgba(196, 181, 253, 0.38)");
            imp(btn, "box-shadow", "0 10px 28px rgba(88, 28, 135, 0.22)");
            imp(btn, "white-space", "nowrap");
            imp(btn, "box-sizing", "border-box");
        });

        if (newBtn) {
            imp(newBtn, "width", "72px");
        }

        if (sessionsBtn) {
            imp(sessionsBtn, "width", "92px");
        }

        // Keep legacy duplicate controls hidden but clickable handlers intact.
        ["nova-mobile-new-chat", "nova-mobile-sessions-toggle"].forEach(function (id) {
            var el = document.getElementById(id);
            if (!el) return;
            imp(el, "position", "fixed");
            imp(el, "left", "-9998px");
            imp(el, "top", "-9998px");
            imp(el, "width", "1px");
            imp(el, "height", "1px");
            imp(el, "opacity", "0");
            imp(el, "pointer-events", "none");
        });
    }

    window.NovaMobileTopButtonPolish = polishTopButtons;

    window.addEventListener("load", function () {
        polishTopButtons();
        setTimeout(polishTopButtons, 500);
        setTimeout(polishTopButtons, 1500);
        setTimeout(polishTopButtons, 3000);
    });

    window.addEventListener("pageshow", function () {
        setTimeout(polishTopButtons, 400);
    });

    setTimeout(polishTopButtons, 800);
    setTimeout(polishTopButtons, 2200);

    console.log("[NOVA_MOBILE_TOP_BUTTON_POLISH_20260624] ready");
})();

/* NOVA_MOBILE_SESSIONS_PANEL_POLISH_V2_20260624 */
(function () {
    "use strict";

    function imp(el, prop, value) {
        if (!el) return;
        el.style.setProperty(prop, value, "important");
    }

    function polishSessionsPanelV2() {
        var panel = document.getElementById("nova-mobile-sessions-panel");
        if (!panel) return;

        imp(panel, "position", "fixed");
        imp(panel, "left", "50%");
        imp(panel, "right", "auto");
        imp(panel, "top", "62px");
        imp(panel, "bottom", "118px");
        imp(panel, "transform", "translateX(-50%)");
        imp(panel, "width", "min(500px, calc(100vw - 20px))");
        imp(panel, "max-width", "min(500px, calc(100vw - 20px))");
        imp(panel, "height", "auto");
        imp(panel, "max-height", "none");
        imp(panel, "padding", "14px");
        imp(panel, "box-sizing", "border-box");
        imp(panel, "overflow-y", "auto");
        imp(panel, "overflow-x", "hidden");
        imp(panel, "border-radius", "22px");
        imp(panel, "background", "linear-gradient(180deg, rgba(24, 18, 38, 0.98), rgba(13, 10, 22, 0.98))");
        imp(panel, "border", "1px solid rgba(196, 181, 253, 0.22)");
        imp(panel, "box-shadow", "0 18px 48px rgba(0, 0, 0, 0.42)");
        imp(panel, "z-index", "140");

        Array.from(panel.querySelectorAll("button")).forEach(function (btn) {
            var label = (btn.textContent || "").trim().toLowerCase();

            imp(btn, "height", "32px");
            imp(btn, "min-height", "32px");
            imp(btn, "border-radius", "999px");
            imp(btn, "font-size", "12px");
            imp(btn, "font-weight", "800");
            imp(btn, "line-height", "1");
            imp(btn, "box-sizing", "border-box");
            imp(btn, "white-space", "nowrap");
            imp(btn, "color", "#f7f2ff");
            imp(btn, "border", "1px solid rgba(196, 181, 253, 0.24)");

            if (label === "delete") {
                imp(btn, "background", "rgba(255, 70, 70, 0.24)");
                imp(btn, "border-color", "rgba(255, 130, 130, 0.30)");
            } else if (label.indexOf("close") >= 0) {
                imp(btn, "background", "rgba(168, 85, 247, 0.24)");
                imp(btn, "border-color", "rgba(196, 181, 253, 0.34)");
            } else {
                imp(btn, "background", "rgba(255, 255, 255, 0.08)");
            }
        });
    }

    window.NovaMobileSessionsPanelPolish = polishSessionsPanelV2;
    window.NovaMobileSessionsPanelPolishV2 = polishSessionsPanelV2;

    document.addEventListener("click", function () {
        setTimeout(polishSessionsPanelV2, 80);
        setTimeout(polishSessionsPanelV2, 350);
        setTimeout(polishSessionsPanelV2, 900);
    }, true);

    window.addEventListener("load", function () {
        setTimeout(polishSessionsPanelV2, 800);
        setTimeout(polishSessionsPanelV2, 2200);
    });

    window.addEventListener("pageshow", function () {
        setTimeout(polishSessionsPanelV2, 700);
    });

    console.log("[NOVA_MOBILE_SESSIONS_PANEL_POLISH_V2_20260624] ready");
})();

