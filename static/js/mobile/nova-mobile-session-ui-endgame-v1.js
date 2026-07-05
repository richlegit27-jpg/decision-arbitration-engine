(function () {
    "use strict";
    window.__NOVA_FORCE_SESSIONS_OPENER_V3_DISABLED_20260704__ = true;

    function novaRemoveForceSessionsOpenerV3() {
        const bad = document.getElementById("nova-force-sessions-opener-v3");
        if (bad && bad.parentNode) {
            bad.parentNode.removeChild(bad);
        }
    }

    novaRemoveForceSessionsOpenerV3();

    const novaForceSessionsOpenerV3Observer = new MutationObserver(function () {
        novaRemoveForceSessionsOpenerV3();
    });

    if (document.documentElement) {
        novaForceSessionsOpenerV3Observer.observe(document.documentElement, {
            childList: true,
            subtree: true
        });
    }


    if (window.__NOVA_MOBILE_SESSION_UI_ENDGAME_V1_20260704__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_UI_ENDGAME_V1_20260704__ = true;

    const LOG = "[Nova Mobile Session UI Endgame V1]";
    let scheduled = false;
    let lastApplyAt = 0;

    function safeText(el) {
        if (!el) return "";
        return [
            el.id || "",
            el.className || "",
            el.getAttribute && (el.getAttribute("aria-label") || ""),
            el.getAttribute && (el.getAttribute("title") || ""),
            el.getAttribute && (el.getAttribute("data-action") || ""),
            el.textContent || ""
        ].join(" ").toLowerCase();
    }

    function isVisible(el) {
        if (!el || !el.getBoundingClientRect) return false;

        const style = getComputedStyle(el);
        if (
            style.display === "none" ||
            style.visibility === "hidden" ||
            Number(style.opacity || "1") <= 0.01
        ) {
            return false;
        }

        const rect = el.getBoundingClientRect();
        return rect.width > 2 && rect.height > 2;
    }

    function isSessionSurface(el) {
        if (!el || el === document.body || el === document.documentElement) {
            return false;
        }

        const t = safeText(el);
        const style = getComputedStyle(el);

        return (
            /session|drawer|history|chat-list|conversation/.test(t) &&
            (
                style.position === "fixed" ||
                style.position === "absolute" ||
                /drawer|panel|modal|overlay|sheet|sidebar|sessions/.test(t)
            )
        );
    }

    function findSessionSurface(start) {
        let el = start;

        while (el && el !== document.body && el !== document.documentElement) {
            if (isSessionSurface(el)) {
                return el;
            }
            el = el.parentElement;
        }

        const candidates = [
            ...document.querySelectorAll(
                "[id*='session' i], [class*='session' i], [id*='drawer' i], [class*='drawer' i], [id*='panel' i], [class*='panel' i]"
            )
        ].filter(isVisible);

        return candidates.find(isSessionSurface) || null;
    }

    function closeSessionSurface(surface) {
        if (!surface) return false;

        surface.classList.remove("open", "active", "show", "visible", "is-open");
        surface.setAttribute("aria-hidden", "true");
        surface.dataset.novaEndgameClosed = "true";

        surface.style.setProperty("display", "none", "important");
        surface.style.setProperty("visibility", "hidden", "important");
        surface.style.setProperty("pointer-events", "none", "important");
        surface.style.setProperty("opacity", "0", "important");
        surface.style.setProperty("transform", "translateX(110%)", "important");

        console.log(LOG, "closed session surface", surface);
        return true;
    }

    function looksLikeCloseButton(el) {
        if (!el) return false;

        const t = safeText(el).trim();

        return (
            t === "x" ||
            t === "×" ||
            t === "close" ||
            /(^|\s)(x|×|close|dismiss|hide)(\s|$)/.test(t) ||
            /close|dismiss/.test(t)
        );
    }

    function installCloseCapture() {
        if (window.__NOVA_MOBILE_SESSION_UI_ENDGAME_CLOSE_CAPTURE_V1__) {
            return;
        }

        window.__NOVA_MOBILE_SESSION_UI_ENDGAME_CLOSE_CAPTURE_V1__ = true;

        document.addEventListener("click", function (event) {
            const button = event.target && event.target.closest
                ? event.target.closest("button, a, [role='button'], [data-action], .close, .btn-close")
                : null;

            if (!button || !looksLikeCloseButton(button)) {
                return;
            }

            const surface = findSessionSurface(button);

            if (!surface) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();

            closeSessionSurface(surface);
        }, true);

        document.addEventListener("keydown", function (event) {
            if (event.key !== "Escape") {
                return;
            }

            const surfaces = [
                ...document.querySelectorAll(
                    "[id*='session' i], [class*='session' i], [id*='drawer' i], [class*='drawer' i], [id*='panel' i], [class*='panel' i]"
                )
            ].filter(isVisible).filter(isSessionSurface);

            surfaces.forEach(closeSessionSurface);
        }, true);
    }

    function applyTopLayout(reason) {
        const now = Date.now();

        if (now - lastApplyAt < 40) {
            return;
        }

        lastApplyAt = now;

        try {
            if (
                window.NovaMobileTopButtonLayoutV3 &&
                typeof window.NovaMobileTopButtonLayoutV3.apply === "function"
            ) {
                window.NovaMobileTopButtonLayoutV3.apply();
                console.log(LOG, "re-applied top layout", reason);
            }
        } catch (err) {
            console.warn(LOG, "top layout apply failed", err);
        }
    }

    function schedule(reason) {
        if (scheduled) {
            return;
        }

        scheduled = true;

        requestAnimationFrame(function () {
            scheduled = false;
            applyTopLayout(reason);

            setTimeout(function () {
                applyTopLayout(reason + ":late-80");
            }, 80);

            setTimeout(function () {
                applyTopLayout(reason + ":late-250");
            }, 250);
        });
    }

    function installMutationWatcher() {
        if (!document.body) {
            setTimeout(installMutationWatcher, 50);
            return;
        }

        const observer = new MutationObserver(function () {
            schedule("mutation");
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["class", "style", "aria-hidden"]
        });

        schedule("boot");
        setTimeout(function () { schedule("late-500"); }, 500);
        setTimeout(function () { schedule("late-1000"); }, 1000);
        setTimeout(function () { schedule("late-2000"); }, 2000);
        setTimeout(function () { schedule("late-4000"); }, 4000);
    }

    window.NovaMobileSessionUiEndgameV1 = {
        apply: function () {
            schedule("manual");
        },
        close: function () {
            const surface = findSessionSurface(document.activeElement || document.body);
            return closeSessionSurface(surface);
        },
        version: "20260704"
    };

    installCloseCapture();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", installMutationWatcher, { once: true });
    } else {
        installMutationWatcher();
    }

    console.log(LOG, "installed");
})();

/* NOVA_SESSION_UI_AGGRESSIVE_CLOSE_V2_START */
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSION_UI_ENDGAME_AGGRESSIVE_CLOSE_V2_20260704__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_UI_ENDGAME_AGGRESSIVE_CLOSE_V2_20260704__ = true;

    const LOG = "[Nova Mobile Session UI Aggressive Close V2]";

    function txt(el) {
        if (!el) return "";

        return [
            el.id || "",
            el.className || "",
            el.getAttribute && (el.getAttribute("aria-label") || ""),
            el.getAttribute && (el.getAttribute("title") || ""),
            el.getAttribute && (el.getAttribute("role") || ""),
            el.getAttribute && (el.getAttribute("data-action") || ""),
            el.textContent || ""
        ].join(" ").toLowerCase();
    }

    function visible(el) {
        if (!el || !el.getBoundingClientRect) return false;

        const style = getComputedStyle(el);
        if (
            style.display === "none" ||
            style.visibility === "hidden" ||
            Number(style.opacity || "1") <= 0.01
        ) {
            return false;
        }

        const rect = el.getBoundingClientRect();

        return (
            rect.width >= 80 &&
            rect.height >= 80 &&
            rect.bottom > 0 &&
            rect.right > 0 &&
            rect.top < window.innerHeight &&
            rect.left < window.innerWidth
        );
    }

    function isBadCandidate(el) {
        if (!el || el === document.body || el === document.documentElement) {
            return true;
        }

        const tag = (el.tagName || "").toLowerCase();
        if (/^(script|style|link|meta|html|body|button|input|textarea|select|option|svg|path)$/.test(tag)) {
            return true;
        }

        const t = txt(el);

        return /mobilechatmessages|chatmessages|chat-message|composer|textarea|chat-input|message-input|final-input|quick-prompt|upload|preview-bar/.test(t);
    }

    function scoreSurface(el) {
        if (isBadCandidate(el) || !visible(el)) {
            return -999;
        }

        const t = txt(el);
        const style = getComputedStyle(el);
        const rect = el.getBoundingClientRect();

        let score = 0;

        if (/session|sessions|conversation|history|drawer|panel|sidebar|sheet|modal|overlay/.test(t)) score += 8;
        if (/close|rename|pin|delete|new chat|chat history|session list/.test(t)) score += 4;
        if (style.position === "fixed" || style.position === "absolute") score += 5;
        if (Number(style.zIndex || "0") >= 10) score += 3;
        if (rect.width >= 180 && rect.height >= 180) score += 3;
        if (rect.left <= 40 || rect.right >= window.innerWidth - 40) score += 2;
        if (rect.height >= window.innerHeight * 0.4) score += 2;

        return score;
    }

    function findSurfaces() {
        const selector = [
            "[id*='session' i]",
            "[class*='session' i]",
            "[id*='drawer' i]",
            "[class*='drawer' i]",
            "[id*='panel' i]",
            "[class*='panel' i]",
            "[id*='sidebar' i]",
            "[class*='sidebar' i]",
            "[id*='sheet' i]",
            "[class*='sheet' i]",
            "[id*='modal' i]",
            "[class*='modal' i]",
            "[id*='overlay' i]",
            "[class*='overlay' i]",
            "[id*='history' i]",
            "[class*='history' i]",
            "[id*='conversation' i]",
            "[class*='conversation' i]"
        ].join(",");

        return [...document.querySelectorAll(selector)]
            .map(el => ({ el, score: scoreSurface(el) }))
            .filter(x => x.score >= 8)
            .sort((a, b) => b.score - a.score)
            .map(x => x.el);
    }

    function hardClose(el) {
        if (!el) return false;

        el.classList.remove(
            "open",
            "opened",
            "active",
            "show",
            "shown",
            "visible",
            "is-open",
            "drawer-open",
            "panel-open"
        );

        el.setAttribute("aria-hidden", "true");
        el.dataset.novaAggressiveClosed = "true";

        el.style.setProperty("display", "none", "important");
        el.style.setProperty("visibility", "hidden", "important");
        el.style.setProperty("opacity", "0", "important");
        el.style.setProperty("pointer-events", "none", "important");
        el.style.setProperty("transform", "translateX(120%)", "important");

        return true;
    }

    function closeAll(reason) {
        const surfaces = findSurfaces();
        surfaces.forEach(hardClose);

        console.log(LOG, "closeAll", {
            reason,
            closed: surfaces.length,
            surfaces
        });

        return surfaces.length > 0;
    }

    function looksCloseLike(el) {
        if (!el) return false;

        const t = txt(el).trim();

        return (
            t === "x" ||
            t === "×" ||
            t === "close" ||
            /(^|\s)(x|×|close|dismiss|hide|back)(\s|$)/.test(t) ||
            /close|dismiss|hide/.test(t)
        );
    }

    document.addEventListener("click", function (event) {
        const target = event.target;

        const clickable = target && target.closest
            ? target.closest("button, a, [role='button'], [aria-label], [title], [data-action], .close, .btn-close")
            : null;

        if (!clickable || !looksCloseLike(clickable)) {
            return;
        }

        const didClose = closeAll("captured-close-click");

        if (didClose) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
        }
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeAll("escape");
        }
    }, true);

    const oldApi = window.NovaMobileSessionUiEndgameV1 || {};

    window.NovaMobileSessionUiEndgameV1 = Object.assign(oldApi, {
        close: function () {
            return closeAll("manual-close");
        },
        closeAll: function () {
            return closeAll("manual-close-all");
        },
        dumpSurfaces: function () {
            const surfaces = findSurfaces();

            console.table(surfaces.map(function (el) {
                const rect = el.getBoundingClientRect();
                return {
                    tag: el.tagName,
                    id: el.id,
                    className: String(el.className || ""),
                    score: scoreSurface(el),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    text: (el.textContent || "").trim().slice(0, 80)
                };
            }));

            return surfaces;
        }
    });

    console.log(LOG, "installed");
})();
/* NOVA_SESSION_UI_AGGRESSIVE_CLOSE_V2_END */

/* NOVA_SESSION_UI_FORCE_SESSIONS_OPENER_V3_START */
(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSION_UI_FORCE_SESSIONS_OPENER_V3_20260704__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_UI_FORCE_SESSIONS_OPENER_V3_20260704__ = true;

    const LOG = "[Nova Mobile Force Sessions Opener V3]";

    function hardShow(el, display) {
        if (!el) return false;

        el.hidden = false;
        el.removeAttribute("hidden");
        el.removeAttribute("inert");
        el.setAttribute("aria-hidden", "false");

        el.style.setProperty("display", display || "block", "important");
        el.style.setProperty("visibility", "visible", "important");
        el.style.setProperty("opacity", "1", "important");
        el.style.setProperty("pointer-events", "auto", "important");

        return true;
    }

    function textOf(el) {
        if (!el) return "";

        return [
            el.id || "",
            el.className || "",
            el.getAttribute && (el.getAttribute("aria-label") || ""),
            el.getAttribute && (el.getAttribute("title") || ""),
            el.textContent || ""
        ].join(" ");
    }

    function findOriginalSessionsButton() {
        return (
            document.getElementById("nova-mobile-sessions-toggle") ||
            [...document.querySelectorAll("button, a, [role='button']")]
                .find(el => /sessions/i.test(textOf(el)))
        );
    }

    function createBossSessionsButton() {
        let btn = document.getElementById("nova-force-sessions-opener-v3");

        if (btn) {
            return btn;
        }

        btn = document.createElement("button");
        btn.id = "nova-force-sessions-opener-v3";
        btn.type = "button";
        btn.textContent = "Sessions";
        btn.setAttribute("aria-label", "Sessions");
        btn.setAttribute("title", "Sessions");

        btn.style.setProperty("position", "fixed", "important");
        btn.style.setProperty("top", "12px", "important");
        btn.style.setProperty("right", "12px", "important");
        btn.style.setProperty("z-index", "2147483647", "important");
        btn.style.setProperty("min-width", "92px", "important");
        btn.style.setProperty("height", "42px", "important");
        btn.style.setProperty("border-radius", "12px", "important");
        btn.style.setProperty("border", "1px solid rgba(255,255,255,0.25)", "important");
        btn.style.setProperty("background", "rgba(20,20,28,0.96)", "important");
        btn.style.setProperty("color", "#fff", "important");
        btn.style.setProperty("font-size", "14px", "important");
        btn.style.setProperty("font-weight", "700", "important");
        btn.style.setProperty("box-shadow", "0 8px 24px rgba(0,0,0,0.35)", "important");
        btn.style.setProperty("display", "inline-flex", "important");
        btn.style.setProperty("align-items", "center", "important");
        btn.style.setProperty("justify-content", "center", "important");
        btn.style.setProperty("pointer-events", "auto", "important");

        btn.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            openSessions("boss-button");
        }, true);

        document.body.appendChild(btn);
        return btn;
    }

    function findSessionPanel() {
        const candidates = [...document.querySelectorAll("body *")]
            .filter(el => {
                if (!el || el === document.body || el === document.documentElement) return false;

                const tag = (el.tagName || "").toLowerCase();
                if (/^(script|style|link|meta|button|input|textarea|select|option|svg|path)$/.test(tag)) return false;

                const idClass = [el.id || "", el.className || ""].join(" ");
                if (/composer|mobilechatmessages|chatmessages|chat-message|input|textarea|header$/i.test(idClass)) return false;

                const text = (el.textContent || "").trim();
                return /current sessions|session_[a-f0-9]|rename|pin|delete|chat history|session list/i.test(text);
            });

        let best = null;
        let bestScore = -999;

        for (const el of candidates) {
            const text = (el.textContent || "").trim();
            const idClass = [el.id || "", el.className || ""].join(" ");

            let score = 0;
            if (/current sessions/i.test(text)) score += 40;
            if (/session_[a-f0-9]/i.test(text)) score += 20;
            if (/rename|pin|delete/i.test(text)) score += 12;
            if (/session|drawer|panel|history|conversation/i.test(idClass)) score += 10;
            if (el.children && el.children.length >= 2) score += 5;

            if (score > bestScore) {
                bestScore = score;
                best = el;
            }
        }

        return best;
    }

    function showSessionPanel(panel) {
        if (!panel) return false;

        hardShow(panel, "block");

        panel.classList.add("open", "show", "visible", "active");

        panel.style.setProperty("position", "fixed", "important");
        panel.style.setProperty("top", "64px", "important");
        panel.style.setProperty("right", "8px", "important");
        panel.style.setProperty("bottom", "76px", "important");
        panel.style.setProperty("left", "auto", "important");
        panel.style.setProperty("width", "min(380px, calc(100vw - 16px))", "important");
        panel.style.setProperty("max-width", "calc(100vw - 16px)", "important");
        panel.style.setProperty("max-height", "calc(100vh - 140px)", "important");
        panel.style.setProperty("overflow", "auto", "important");
        panel.style.setProperty("z-index", "2147483646", "important");
        panel.style.setProperty("transform", "translateX(0)", "important");

        return true;
    }

    function openSessions(reason) {
        const original = findOriginalSessionsButton();
        const boss = createBossSessionsButton();

        if (original) {
            hardShow(original, "inline-flex");

            let parent = original.parentElement;
            for (let i = 0; parent && i < 4; i += 1) {
                hardShow(parent, "flex");
                parent = parent.parentElement;
            }

            try {
                original.click();
            } catch (_) {}
        }

        const panelNow = findSessionPanel();
        const openedNow = showSessionPanel(panelNow);

        setTimeout(function () {
            const panelLate = findSessionPanel();
            const openedLate = showSessionPanel(panelLate);

            console.log(LOG, "openSessions", {
                reason,
                hasOriginal: !!original,
                hasBoss: !!boss,
                openedNow,
                openedLate,
                panel: panelLate || panelNow
            });
        }, 120);

        return !!(original || boss);
    }

    function install() {
        createBossSessionsButton();

        const original = findOriginalSessionsButton();
        if (original) {
            hardShow(original, "inline-flex");
        }

        setTimeout(install, 1000);
    }

    const oldApi = window.NovaMobileSessionUiEndgameV1 || {};

    window.NovaMobileSessionUiEndgameV1 = Object.assign(oldApi, {
        openSessions,
        forceSessionsButton: function () {
            createBossSessionsButton();
            const original = findOriginalSessionsButton();
            if (original) hardShow(original, "inline-flex");
            return true;
        },
        findSessionPanel,
        findOriginalSessionsButton
    });

    install();

    console.log(LOG, "installed");
})();
/* NOVA_SESSION_UI_FORCE_SESSIONS_OPENER_V3_END */

/* NOVA_VISIBLE_SESSIONS_LAUNCHER_FINAL_V4_START */
(function () {
    "use strict";

    if (window.__NOVA_VISIBLE_SESSIONS_LAUNCHER_FINAL_V4_20260704__) {
        return;
    }

    window.__NOVA_VISIBLE_SESSIONS_LAUNCHER_FINAL_V4_20260704__ = true;

    const LOG = "[Nova Visible Sessions Launcher Final V4]";

    function showLauncher() {
        if (!document.body) {
            setTimeout(showLauncher, 50);
            return;
        }

        let btn = document.getElementById("nova-visible-sessions-launcher-final");

        if (!btn) {
            btn = document.createElement("button");
            btn.id = "nova-visible-sessions-launcher-final";
            btn.type = "button";
            btn.textContent = "☰ Sessions";
            btn.setAttribute("aria-label", "Sessions");
            btn.setAttribute("title", "Sessions");

            btn.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();

                console.log(LOG, "clicked");

                if (
                    window.NovaMobileSessionUiEndgameV1 &&
                    typeof window.NovaMobileSessionUiEndgameV1.openSessions === "function"
                ) {
                    window.NovaMobileSessionUiEndgameV1.openSessions("visible-launcher-click");
                }
            }, true);

            document.body.appendChild(btn);
        }

        btn.hidden = false;
        btn.removeAttribute("hidden");
        btn.removeAttribute("inert");
        btn.setAttribute("aria-hidden", "false");

        btn.style.setProperty("position", "fixed", "important");
        btn.style.setProperty("left", "12px", "important");
        btn.style.setProperty("bottom", "88px", "important");
        btn.style.setProperty("width", "150px", "important");
        btn.style.setProperty("height", "52px", "important");
        btn.style.setProperty("z-index", "2147483647", "important");
        btn.style.setProperty("display", "flex", "important");
        btn.style.setProperty("align-items", "center", "important");
        btn.style.setProperty("justify-content", "center", "important");
        btn.style.setProperty("border-radius", "16px", "important");
        btn.style.setProperty("border", "2px solid rgba(255,255,255,0.35)", "important");
        btn.style.setProperty("background", "#6d28d9", "important");
        btn.style.setProperty("color", "#fff", "important");
        btn.style.setProperty("font-size", "16px", "important");
        btn.style.setProperty("font-weight", "800", "important");
        btn.style.setProperty("box-shadow", "0 12px 30px rgba(0,0,0,0.45)", "important");
        btn.style.setProperty("pointer-events", "auto", "important");

        setTimeout(showLauncher, 1000);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", showLauncher, { once: true });
    } else {
        showLauncher();
    }

    console.log(LOG, "installed");
})();
/* NOVA_VISIBLE_SESSIONS_LAUNCHER_FINAL_V4_END */

/* NOVA_STANDALONE_SESSIONS_DRAWER_V5_START */
(function () {
    "use strict";

    if (window.__NOVA_STANDALONE_SESSIONS_DRAWER_V5_20260704__) {
        return;
    }

    window.__NOVA_STANDALONE_SESSIONS_DRAWER_V5_20260704__ = true;

    const LOG = "[Nova Standalone Sessions Drawer V5]";
    const BTN_ID = "nova-standalone-sessions-button-v5";
    const DRAWER_ID = "nova-standalone-sessions-drawer-v5";
    const STYLE_ID = "nova-standalone-sessions-style-v5";

    function installStyle() {
        let style = document.getElementById(STYLE_ID);

        if (!style) {
            style = document.createElement("style");
            style.id = STYLE_ID;
            document.head.appendChild(style);
        }

        style.textContent = `
#${BTN_ID} {
    position: fixed !important;
    left: 12px !important;
    bottom: 88px !important;
    width: 154px !important;
    height: 52px !important;
    z-index: 2147483647 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 16px !important;
    border: 2px solid rgba(255,255,255,0.35) !important;
    background: #6d28d9 !important;
    color: #fff !important;
    font-size: 16px !important;
    font-weight: 800 !important;
    box-shadow: 0 12px 30px rgba(0,0,0,0.45) !important;
    pointer-events: auto !important;
    opacity: 1 !important;
    visibility: visible !important;
}
#${DRAWER_ID} {
    position: fixed !important;
    top: 64px !important;
    right: 8px !important;
    bottom: 76px !important;
    width: min(390px, calc(100vw - 16px)) !important;
    z-index: 2147483646 !important;
    display: none !important;
    background: rgba(18,18,26,0.98) !important;
    color: #fff !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 18px !important;
    box-shadow: 0 18px 50px rgba(0,0,0,0.55) !important;
    overflow: hidden !important;
    pointer-events: auto !important;
}
#${DRAWER_ID}.nova-open {
    display: flex !important;
    flex-direction: column !important;
}
#${DRAWER_ID} .nova-sessions-head {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 12px !important;
    padding: 14px 14px 10px 14px !important;
    border-bottom: 1px solid rgba(255,255,255,0.12) !important;
}
#${DRAWER_ID} .nova-sessions-title {
    font-size: 17px !important;
    font-weight: 900 !important;
}
#${DRAWER_ID} .nova-sessions-close {
    width: 38px !important;
    height: 38px !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,0.22) !important;
    background: rgba(255,255,255,0.08) !important;
    color: #fff !important;
    font-size: 22px !important;
    font-weight: 900 !important;
}
#${DRAWER_ID} .nova-sessions-body {
    overflow: auto !important;
    padding: 10px !important;
}
#${DRAWER_ID} .nova-session-row {
    display: block !important;
    width: 100% !important;
    text-align: left !important;
    margin: 0 0 8px 0 !important;
    padding: 12px !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    background: rgba(255,255,255,0.06) !important;
    color: #fff !important;
}
#${DRAWER_ID} .nova-session-row-title {
    display: block !important;
    font-weight: 850 !important;
    font-size: 14px !important;
    margin-bottom: 4px !important;
}
#${DRAWER_ID} .nova-session-row-meta {
    display: block !important;
    opacity: 0.72 !important;
    font-size: 12px !important;
}
`;
    }

    function hardShowButton(btn) {
        if (!btn) return;

        btn.hidden = false;
        btn.removeAttribute("hidden");
        btn.removeAttribute("inert");
        btn.setAttribute("aria-hidden", "false");

        btn.style.setProperty("display", "flex", "important");
        btn.style.setProperty("visibility", "visible", "important");
        btn.style.setProperty("opacity", "1", "important");
        btn.style.setProperty("pointer-events", "auto", "important");
    }

    function ensureButton() {
        installStyle();

        let btn = document.getElementById(BTN_ID);

        if (!btn) {
            btn = document.createElement("button");
            btn.id = BTN_ID;
            btn.type = "button";
            btn.textContent = "☰ Sessions";
            btn.setAttribute("aria-label", "Sessions");
            btn.setAttribute("title", "Sessions");

            btn.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                openDrawer("button-click");
            }, true);

            document.body.appendChild(btn);
        }

        hardShowButton(btn);
        return btn;
    }

    function ensureDrawer() {
        installStyle();

        let drawer = document.getElementById(DRAWER_ID);

        if (!drawer) {
            drawer = document.createElement("section");
            drawer.id = DRAWER_ID;
            drawer.setAttribute("aria-label", "Sessions drawer");
            drawer.innerHTML = `
                <div class="nova-sessions-head">
                    <div class="nova-sessions-title">Sessions</div>
                    <button type="button" class="nova-sessions-close" aria-label="Close sessions">×</button>
                </div>
                <div class="nova-sessions-body">Loading sessions...</div>
            `;

            drawer.querySelector(".nova-sessions-close").addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                closeDrawer("close-button");
            }, true);

            document.body.appendChild(drawer);
        }

        return drawer;
    }

    function normalizeSessions(data) {
        if (Array.isArray(data)) return data;
        if (Array.isArray(data.sessions)) return data.sessions;
        if (data.session && Array.isArray(data.session.sessions)) return data.session.sessions;
        if (Array.isArray(data.items)) return data.items;
        return [];
    }

    function sessionTitle(s) {
        return (
            s.title ||
            s.name ||
            s.label ||
            s.id ||
            "Untitled session"
        );
    }

    function sessionMeta(s) {
        const id = s.id || "";
        const count = s.message_count ?? s.messages_count ?? s.count ?? "";
        const shortId = id ? id.slice(-8) : "";
        return [
            count !== "" ? `${count} messages` : "",
            shortId ? `…${shortId}` : ""
        ].filter(Boolean).join(" · ");
    }

    async function loadSessions() {
        const drawer = ensureDrawer();
        const body = drawer.querySelector(".nova-sessions-body");

        body.textContent = "Loading sessions...";

        try {
            const res = await fetch("/api/sessions?cache_bust=" + Date.now(), {
                credentials: "include",
                cache: "no-store",
                headers: {
                    "Accept": "application/json"
                }
            });

            const data = await res.json();
            const sessions = normalizeSessions(data);

            if (!sessions.length) {
                body.textContent = "No sessions found.";
                return;
            }

            body.innerHTML = "";

            sessions.forEach(function (s) {
                const id = s.id || s.session_id;
                const row = document.createElement("button");
                row.type = "button";
                row.className = "nova-session-row";
                row.innerHTML = `
                    <span class="nova-session-row-title"></span>
                    <span class="nova-session-row-meta"></span>
                `;

                row.querySelector(".nova-session-row-title").textContent = sessionTitle(s);
                row.querySelector(".nova-session-row-meta").textContent = sessionMeta(s);

                row.addEventListener("click", function () {
                    if (!id) return;
                    location.href = "/mobile?session_id=" + encodeURIComponent(id) + "&v=session-switch-" + Date.now();
                });

                body.appendChild(row);
            });
        } catch (err) {
            console.warn(LOG, "load sessions failed", err);
            body.textContent = "Could not load sessions.";
        }
    }

    function openDrawer(reason) {
        ensureButton();

        const drawer = ensureDrawer();
        drawer.classList.add("nova-open");
        drawer.hidden = false;
        drawer.removeAttribute("hidden");
        drawer.setAttribute("aria-hidden", "false");

        loadSessions();

        console.log(LOG, "opened", reason);
        return true;
    }

    function closeDrawer(reason) {
        const drawer = ensureDrawer();
        drawer.classList.remove("nova-open");
        drawer.setAttribute("aria-hidden", "true");

        console.log(LOG, "closed", reason);
        return true;
    }

    function boot() {
        if (!document.body) {
            setTimeout(boot, 50);
            return;
        }

        ensureButton();
        ensureDrawer();

        setTimeout(boot, 500);
    }

    const oldApi = window.NovaMobileSessionUiEndgameV1 || {};

    window.NovaMobileSessionUiEndgameV1 = Object.assign(oldApi, {
        standaloneOpenSessions: openDrawer,
        standaloneCloseSessions: closeDrawer,
        ensureStandaloneSessionsButton: ensureButton
    });

    boot();

    console.log(LOG, "installed");
})();
/* NOVA_STANDALONE_SESSIONS_DRAWER_V5_END */


