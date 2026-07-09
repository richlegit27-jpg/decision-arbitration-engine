(function () {
    "use strict";

    const VERSION = "mobile-session-drawer-restore-v5";
    window.__NOVA_MOBILE_SESSION_DRAWER_RESTORE_V5__ = true;

    let sessionCache = [];
    let sessionCacheAt = 0;

    function log() {
        try { console.log("[NOVA MOBILE DRAWER RESTORE V5]", ...arguments); } catch (_) {}
    }

    function warn() {
        try { console.warn("[NOVA MOBILE DRAWER RESTORE V5]", ...arguments); } catch (_) {}
    }

    function textOf(node) {
        return String(node && node.textContent || "").replace(/\s+/g, " ").trim();
    }

    function isNewChatNode(node) {
        const raw = (
            String(node && node.id || "") + " " +
            String(node && node.className || "") + " " +
            String(node && node.getAttribute && node.getAttribute("data-action") || "") + " " +
            textOf(node)
        ).toLowerCase();

        return raw.includes("new chat") || raw.includes("new-chat") || raw.includes("newchat");
    }

    function isSessionArea(node) {
        if (!node || !node.closest) {
            return false;
        }

        if (node.closest("[data-session-id], [data-session_id], [data-nova-session-id]")) {
            return true;
        }

        const area = node.closest(
            "[id*='session' i], [class*='session' i], [id*='history' i], [class*='history' i], [id*='drawer' i], [class*='drawer' i], [id*='sidebar' i], [class*='sidebar' i], [id*='conversation' i], [class*='conversation' i]"
        );

        return Boolean(area);
    }

    function explicitSessionId(node) {
        if (!node || !node.closest) {
            return "";
        }

        const item = node.closest(
            "[data-session-id], [data-session_id], [data-nova-session-id], [data-id], [data-key], [data-session], a[href]"
        );

        if (!item) {
            return "";
        }

        const attrs = [
            "data-session-id",
            "data-session_id",
            "data-nova-session-id",
            "data-id",
            "data-key",
            "data-session"
        ];

        for (const attr of attrs) {
            const value = String(item.getAttribute(attr) || "").trim();
            if (looksLikeSessionId(value)) {
                return value;
            }
        }

        const href = String(item.getAttribute("href") || "");
        if (href) {
            try {
                const url = new URL(href, location.origin);
                const params = ["session_id", "session", "id"];
                for (const param of params) {
                    const value = String(url.searchParams.get(param) || "").trim();
                    if (looksLikeSessionId(value)) {
                        return value;
                    }
                }

                const pathMatch = url.pathname.match(/sessions?\/([^/?#]+)/i);
                if (pathMatch && looksLikeSessionId(pathMatch[1])) {
                    return decodeURIComponent(pathMatch[1]);
                }
            } catch (_) {}
        }

        return "";
    }

    function looksLikeSessionId(value) {
        const id = String(value || "").trim();

        if (id.length < 6) {
            return false;
        }

        if (/^(mobile_|session_|restore_|mobile_restore_|mobile_v4_)/i.test(id)) {
            return true;
        }

        if (/^[a-z0-9_-]{12,}$/i.test(id) && !/^(button|submit|rename|delete|pin|new)$/i.test(id)) {
            return true;
        }

        return false;
    }

    async function loadSessions() {
        const now = Date.now();

        if (sessionCache.length && now - sessionCacheAt < 5000) {
            return sessionCache;
        }

        const response = await fetch("/api/sessions", {
            credentials: "include",
            cache: "no-store",
            headers: { "Accept": "application/json" }
        });

        const payload = await response.json();
        const sessions = payload.sessions || payload.items || payload.data || payload.results || [];

        sessionCache = Array.isArray(sessions) ? sessions : [];
        sessionCacheAt = now;

        return sessionCache;
    }

    function normalizeSession(session) {
        return {
            id: String(session && (session.id || session.session_id || session.key || "") || "").trim(),
            title: String(session && (session.title || session.name || session.label || "") || "").replace(/\s+/g, " ").trim()
        };
    }

    async function resolveByText(node) {
        const row = node && node.closest
            ? node.closest("li, button, a, div, article, section, [role='button'], [role='listitem']")
            : node;

        const rowText = textOf(row || node);

        if (!rowText || rowText.length < 2) {
            return "";
        }

        const sessions = (await loadSessions()).map(normalizeSession).filter(function (session) {
            return session.id;
        });

        const lowered = rowText.toLowerCase();

        const exact = sessions.find(function (session) {
            return session.title && lowered === session.title.toLowerCase();
        });

        if (exact) {
            return exact.id;
        }

        const contained = sessions.find(function (session) {
            const title = session.title.toLowerCase();
            return title && (lowered.includes(title) || title.includes(lowered));
        });

        if (contained) {
            return contained.id;
        }

        const idContained = sessions.find(function (session) {
            return lowered.includes(session.id.toLowerCase()) || lowered.includes(session.id.slice(-6).toLowerCase());
        });

        if (idContained) {
            return idContained.id;
        }

        return "";
    }

    async function restoreFromClick(event) {
        const node = event.target;

        if (!node || !isSessionArea(node)) {
            return;
        }

        const clickable = node.closest
            ? node.closest("button, a, li, div, article, section, [role='button'], [role='listitem']")
            : node;

        if (!clickable || isNewChatNode(clickable)) {
            return;
        }

        let id = explicitSessionId(clickable);

        if (!id) {
            try {
                id = await resolveByText(clickable);
            } catch (error) {
                warn("session text resolution failed", error && error.message ? error.message : error);
            }
        }

        if (!id) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        if (typeof window.NovaMobileRestoreSession !== "function") {
            warn("NovaMobileRestoreSession is missing");
            return;
        }

        log("restoring from drawer click", id, textOf(clickable));

        try {
            const restored = await window.NovaMobileRestoreSession(id);
            log("drawer restore complete", restored && restored.id, restored && restored.messages && restored.messages.length);
        } catch (error) {
            warn("drawer restore failed", id, error && error.message ? error.message : error);
        }
    }

    document.addEventListener("click", function (event) {
        restoreFromClick(event);
    }, true);

    document.addEventListener("touchend", function (event) {
        restoreFromClick(event);
    }, true);

    window.NovaMobileDrawerRestoreV5 = {
        version: VERSION,
        loadSessions: loadSessions,
        resolveByText: resolveByText
    };

    log("active", VERSION);
})();
