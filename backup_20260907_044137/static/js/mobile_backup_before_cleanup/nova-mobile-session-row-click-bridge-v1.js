(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSION_ROW_CLICK_BRIDGE_V1_20260704__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_ROW_CLICK_BRIDGE_V1_20260704__ = true;

    const LOG = "[Nova Session Row Click Bridge V1]";

    function currentSessionId() {
        return new URLSearchParams(location.search).get("session_id") || "";
    }

    function cleanSid(value) {
        if (!value) return "";
        const text = String(value);
        const match = text.match(/session_[A-Za-z0-9_:-]+/);
        return match ? match[0] : "";
    }

    function sidFromHref(value) {
        if (!value) return "";
        try {
            const url = new URL(value, location.origin);
            return url.searchParams.get("session_id") || cleanSid(value);
        } catch (_) {
            return cleanSid(value);
        }
    }

    function sidFromElement(el) {
        let node = el;

        for (let depth = 0; node && depth < 8; depth += 1, node = node.parentElement) {
            if (!node.getAttribute) continue;

            const attrs = [
                "data-session-id",
                "data-nova-session-id",
                "data-sid",
                "data-id",
                "href",
                "onclick",
                "id",
                "class",
                "aria-label",
                "title"
            ];

            for (const attr of attrs) {
                const value = node.getAttribute(attr);
                const sid = attr === "href" ? sidFromHref(value) : cleanSid(value);
                if (sid) return sid;
            }
        }

        return "";
    }

    function isBlockedAction(el) {
        const text = [
            el && el.innerText,
            el && el.textContent,
            el && el.id,
            el && el.className,
            el && el.getAttribute && el.getAttribute("aria-label"),
            el && el.getAttribute && el.getAttribute("title")
        ].join(" ").toLowerCase();

        return (
            text.includes("rename") ||
            text.includes("delete") ||
            text.includes("remove") ||
            text.includes("pin") ||
            text.includes("close") ||
            text.includes("×") ||
            text.includes("new chat")
        );
    }

    function switchToSession(sid) {
        if (!sid) return false;

        const current = currentSessionId();

        if (sid === current) {
            console.log(LOG, "already on session", sid);
            return false;
        }

        try {
            localStorage.setItem("nova_mobile_active_session_id", sid);
            sessionStorage.setItem("nova_mobile_active_session_id", sid);
        } catch (_) {}

        console.log(LOG, "switching", { from: current, to: sid });

        location.href = "/mobile?session_id=" + encodeURIComponent(sid) + "&v=session-row-click-bridge-" + Date.now();
        return true;
    }

    async function decorateVisibleSessionRows() {
        let sessions = [];

        try {
            const r = await fetch("/api/sessions?v=" + Date.now(), {
                credentials: "include",
                cache: "no-store"
            });
            const data = await r.json();
            sessions = data.sessions || data.items || [];
        } catch (e) {
            console.warn(LOG, "session list fetch failed", e);
            return;
        }

        if (!sessions.length) return;

        const panels = [...document.querySelectorAll("aside, section, div")]
            .filter(el => {
                const meta = [
                    el.id,
                    el.className,
                    el.getAttribute && el.getAttribute("aria-label"),
                    el.getAttribute && el.getAttribute("data-nova-owner")
                ].join(" ");

                const r = el.getBoundingClientRect();
                return /session/i.test(meta) && (r.width || r.height || el.getClientRects().length);
            });

        const panel = panels.find(el => {
            const text = (el.innerText || "").toLowerCase();
            return text.includes("session") || text.includes("rename") || text.includes("delete");
        });

        if (!panel) return;

        const candidates = [...panel.querySelectorAll("button, a, [role='button'], div, li")]
            .filter(el => {
                const r = el.getBoundingClientRect();
                return !!(r.width || r.height || el.getClientRects().length);
            });

        let decorated = 0;

        for (const session of sessions) {
            const sid = session.id || "";
            const title = (session.title || "").trim();
            const shortId = sid.slice(-6);

            if (!sid) continue;

            const row = candidates.find(el => {
                if (sidFromElement(el)) return false;

                const text = (el.innerText || el.textContent || "").trim();
                if (!text) return false;

                return (
                    text.includes(sid) ||
                    (shortId && text.includes(shortId)) ||
                    (title && text.includes(title))
                );
            });

            if (row) {
                row.setAttribute("data-nova-session-id", sid);
                row.style.cursor = "pointer";
                decorated += 1;
            }
        }

        if (decorated) {
            console.log(LOG, "decorated rows", decorated);
        }
    }

    document.addEventListener("click", function (event) {
        const target = event.target && event.target.closest
            ? event.target.closest("button, a, [role='button'], div, li")
            : event.target;

        if (!target || isBlockedAction(target)) {
            return;
        }

        const sid = sidFromElement(target);

        if (!sid) {
            setTimeout(decorateVisibleSessionRows, 50);
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        switchToSession(sid);
    }, true);

    document.addEventListener("pointerdown", function () {
        setTimeout(decorateVisibleSessionRows, 80);
    }, true);

    setTimeout(decorateVisibleSessionRows, 500);
    setTimeout(decorateVisibleSessionRows, 1500);

    console.log(LOG, "installed");
})();
