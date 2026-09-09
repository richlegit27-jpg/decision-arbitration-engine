(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSION_DRAWER_ACTIONS_V1_20260704__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_DRAWER_ACTIONS_V1_20260704__ = true;

    const LOG = "[Nova Session Drawer Actions V1]";
    const STYLE_ID = "nova-mobile-session-drawer-actions-style-v1";

    let metaById = Object.create(null);
    let syncing = false;

    function currentSessionId() {
        return new URLSearchParams(location.search).get("session_id") || "";
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function ensureStyle() {
        if (document.getElementById(STYLE_ID)) {
            return;
        }

        const style = document.createElement("style");
        style.id = STYLE_ID;
        style.textContent = `
.nova-session-actions-row {
    display: flex !important;
    gap: 8px !important;
    margin: -2px 0 10px 0 !important;
    padding: 0 4px 4px 4px !important;
    box-sizing: border-box !important;
}
.nova-session-action-btn {
    flex: 1 1 0 !important;
    min-height: 34px !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    background: rgba(255,255,255,0.10) !important;
    color: #f7f2ff !important;
    font: 900 11px Arial, system-ui, sans-serif !important;
    cursor: pointer !important;
    pointer-events: auto !important;
}
.nova-session-action-btn:active {
    transform: scale(0.98) !important;
}
.nova-session-action-btn.is-danger {
    background: rgba(239,68,68,0.22) !important;
    border-color: rgba(248,113,113,0.45) !important;
}
.nova-session-action-btn.is-pinned {
    background: rgba(168,85,247,0.30) !important;
    border-color: rgba(216,180,254,0.55) !important;
}
`;
        document.head.appendChild(style);
    }

    async function postJson(url, body, method) {
        const response = await fetch(url, {
            method: method || "POST",
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: body === undefined ? undefined : JSON.stringify(body)
        });

        let data = null;

        try {
            data = await response.json();
        } catch (_) {
            data = {};
        }

        if (!response.ok || data.ok === false) {
            const message = data.error || data.message || ("HTTP " + response.status);
            throw new Error(message);
        }

        return data;
    }

    async function trySessionAction(name, candidates) {
        let lastError = null;

        for (const candidate of candidates) {
            try {
                const data = await postJson(candidate.url, candidate.body, candidate.method);
                console.log(LOG, name + " success", candidate.url, data);
                return data;
            } catch (error) {
                lastError = error;
                console.warn(LOG, name + " failed candidate", candidate.url, error.message);
            }
        }

        throw lastError || new Error(name + " failed");
    }

    async function refreshMeta() {
        try {
            const response = await fetch("/api/sessions?v=" + Date.now(), {
                credentials: "include",
                cache: "no-store",
                headers: {
                    "Accept": "application/json"
                }
            });

            const data = await response.json();
            const sessions = data.sessions || data.items || [];

            metaById = Object.create(null);

            sessions.forEach(function (session) {
                if (session && session.id) {
                    metaById[session.id] = session;
                }
            });

            return sessions;
        } catch (error) {
            console.warn(LOG, "meta refresh failed", error);
            return [];
        }
    }

    function refreshDrawer() {
        if (window.NovaMobileSessionDrawerBridgeV1 && typeof window.NovaMobileSessionDrawerBridgeV1.open === "function") {
            window.NovaMobileSessionDrawerBridgeV1.open();
        }
    }

    async function renameSession(sid) {
        const session = metaById[sid] || {};
        const oldTitle = session.title || "Untitled session";
        const title = prompt("Rename session:", oldTitle);

        if (!title || !title.trim()) {
            return;
        }

        const cleanTitle = title.trim();

        await trySessionAction("rename", [
            {
                url: "/api/sessions/" + encodeURIComponent(sid) + "/rename",
                body: { title: cleanTitle }
            },
            {
                url: "/api/sessions/rename",
                body: { session_id: sid, id: sid, title: cleanTitle }
            }
        ]);

        await refreshMeta();
        refreshDrawer();
    }

    async function deleteSession(sid) {
        const session = metaById[sid] || {};
        const title = session.title || sid.slice(-8);
        const active = currentSessionId();

        if (!confirm("Delete session \"" + title + "\"?")) {
            return;
        }

        await trySessionAction("delete", [
            {
                url: "/api/sessions/" + encodeURIComponent(sid) + "/delete",
                body: {}
            },
            {
                url: "/api/sessions/delete",
                body: { session_id: sid, id: sid }
            },
            {
                url: "/api/sessions/" + encodeURIComponent(sid),
                method: "DELETE",
                body: {}
            }
        ]);

        const sessions = await refreshMeta();

        if (sid === active) {
            const next = sessions.find(function (session) {
                return session && session.id && session.id !== sid;
            });

            if (next && next.id) {
                location.href = "/mobile?session_id=" + encodeURIComponent(next.id) + "&v=session-delete-" + Date.now();
            } else {
                location.href = "/mobile?v=session-delete-empty-" + Date.now();
            }

            return;
        }

        refreshDrawer();
    }

    async function pinSession(sid, btn) {
        const session = metaById[sid] || {};
        const pinned = !!(session.pinned || session.is_pinned || session.pin);
        const nextPinned = !pinned;

        await trySessionAction("pin", [
            {
                url: "/api/sessions/" + encodeURIComponent(sid) + "/pin",
                body: { pinned: nextPinned, is_pinned: nextPinned }
            },
            {
                url: "/api/sessions/pin",
                body: { session_id: sid, id: sid, pinned: nextPinned, is_pinned: nextPinned }
            },
            {
                url: "/api/sessions/" + encodeURIComponent(sid) + "/toggle-pin",
                body: {}
            }
        ]);

        if (btn) {
            btn.disabled = true;
        }

        await refreshMeta();
        refreshDrawer();
    }

    function button(label, action, extraClass, pinned) {
        return `
            <button
                type="button"
                class="nova-session-action-btn ${extraClass || ""}"
                data-nova-session-action="${escapeHtml(action)}"
                data-nova-pinned="${pinned ? "1" : "0"}"
            >${escapeHtml(label)}</button>
        `;
    }

    function injectActions() {
        if (syncing) {
            return;
        }

        syncing = true;

        try {
            ensureStyle();

            document.querySelectorAll(".nova-session-bridge-row[data-nova-session-id]").forEach(function (row) {
                const sid = row.getAttribute("data-nova-session-id");

                if (!sid) {
                    return;
                }

                const next = row.nextElementSibling;

                if (next && next.classList && next.classList.contains("nova-session-actions-row")) {
                    return;
                }

                const session = metaById[sid] || {};
                const pinned = !!(session.pinned || session.is_pinned || session.pin);
                const pinLabel = pinned ? "Unpin" : "Pin";
                const pinClass = pinned ? "is-pinned" : "";

                const actions = document.createElement("div");
                actions.className = "nova-session-actions-row";
                actions.setAttribute("data-nova-session-actions-for", sid);
                actions.innerHTML = [
                    button(pinLabel, "pin", pinClass, pinned),
                    button("Rename", "rename", "", pinned),
                    button("Delete", "delete", "is-danger", pinned)
                ].join("");

                actions.addEventListener("click", async function (event) {
                    const btn = event.target && event.target.closest
                        ? event.target.closest("[data-nova-session-action]")
                        : null;

                    if (!btn) {
                        return;
                    }

                    event.preventDefault();
                    event.stopPropagation();
                    event.stopImmediatePropagation();

                    const action = btn.getAttribute("data-nova-session-action");

                    try {
                        btn.disabled = true;

                        if (action === "rename") {
                            await renameSession(sid);
                        } else if (action === "delete") {
                            await deleteSession(sid);
                        } else if (action === "pin") {
                            await pinSession(sid, btn);
                        }
                    } catch (error) {
                        console.error(LOG, action + " failed", error);
                        alert((action || "Action") + " failed: " + (error.message || error));
                    } finally {
                        btn.disabled = false;
                    }
                }, true);

                row.parentNode.insertBefore(actions, row.nextSibling);
            });
        } finally {
            syncing = false;
        }
    }

    async function sync() {
        await refreshMeta();
        injectActions();
    }

    const observer = new MutationObserver(function () {
        injectActions();
    });

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true
    });

    document.addEventListener("click", function () {
        setTimeout(injectActions, 50);
        setTimeout(injectActions, 250);
    }, true);

    setInterval(injectActions, 600);
    setTimeout(sync, 300);
    setTimeout(sync, 1000);

    window.NovaMobileSessionDrawerActionsV1 = {
        sync: sync,
        inject: injectActions,
        refreshMeta: refreshMeta
    };

    console.log(LOG, "installed");
})();
