(function () {
    "use strict";

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

