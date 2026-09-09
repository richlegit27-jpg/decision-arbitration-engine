(function () {
    "use strict";

    if (window.__NOVA_MOBILE_SESSION_FLAT_ACTIONS_V1_20260703__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_FLAT_ACTIONS_V1_20260703__ = true;

    var VERSION = "session-flat-actions-v1-20260703";

    function isValidSessionId(value) {
        var text;

        if (!value) {
            return false;
        }

        text = String(value).trim();

        if (
            !text ||
            text === "null" ||
            text === "undefined" ||
            text.indexOf("=") === 0 ||
            text.indexOf(" ") >= 0
        ) {
            return false;
        }

        return (
            text.indexOf("session_") === 0 ||
            text.indexOf("mobile_") === 0 ||
            text.indexOf("debug_") === 0 ||
            text.indexOf("regression_") === 0
        );
    }

    function getActiveSessionId() {
        try {
            return (
                window.NovaMobileActiveSessionId ||
                localStorage.getItem("nova_mobile_active_session_id") ||
                localStorage.getItem("nova_active_session_id") ||
                new URL(window.location.href).searchParams.get("session_id")
            );
        } catch (err) {
            return window.NovaMobileActiveSessionId || null;
        }
    }

    function setActiveSessionId(sessionId) {
        var url;

        if (!isValidSessionId(sessionId)) {
            return;
        }

        window.NovaMobileActiveSessionId = sessionId;

        try {
            localStorage.setItem("nova_mobile_active_session_id", sessionId);
            localStorage.setItem("nova_active_session_id", sessionId);
            localStorage.removeItem("active_session_id");
        } catch (err) {}

        try {
            url = new URL(window.location.href);
            url.searchParams.set("session_id", sessionId);
            window.history.replaceState(null, "", url.pathname + url.search + url.hash);
        } catch (err) {}
    }

    async function fetchJson(url, body) {
        var response;
        var text;
        var data;

        response = await fetch(url, {
            method: "POST",
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body || {})
        });

        text = await response.text();

        try {
            data = text ? JSON.parse(text) : {};
        } catch (err) {
            data = {
                ok: false,
                error: text || response.statusText
            };
        }

        if (!response.ok || data.ok === false) {
            throw new Error(data.error || response.statusText || ("HTTP " + response.status));
        }

        return data;
    }

    async function getSessionList() {
        var response = await fetch("/api/sessions?cache_bust=" + Date.now(), {
            method: "GET",
            credentials: "include",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        });

        return await response.json();
    }

    function getSessionId(session) {
        if (!session) {
            return null;
        }

        return session.session_id || session.id || null;
    }

    function getMessageCount(session) {
        if (!session) {
            return 0;
        }

        if (typeof session.message_count === "number") {
            return session.message_count;
        }

        if (Array.isArray(session.messages)) {
            return session.messages.length;
        }

        return 0;
    }

    function pickNextSession(sessions, deletedId, previousActiveId) {
        var filtered;
        var normalWithMessages;
        var normalAny;

        filtered = (Array.isArray(sessions) ? sessions : []).filter(function (session) {
            var id = getSessionId(session);
            return isValidSessionId(id) && id !== deletedId;
        });

        if (isValidSessionId(previousActiveId) && previousActiveId !== deletedId) {
            if (filtered.some(function (session) {
                return getSessionId(session) === previousActiveId;
            })) {
                return previousActiveId;
            }
        }

        normalWithMessages = filtered.find(function (session) {
            var id = getSessionId(session);
            return (
                id &&
                id.indexOf("regression_") !== 0 &&
                getMessageCount(session) > 0
            );
        });

        if (normalWithMessages) {
            return getSessionId(normalWithMessages);
        }

        normalAny = filtered.find(function (session) {
            var id = getSessionId(session);
            return id && id.indexOf("regression_") !== 0;
        });

        if (normalAny) {
            return getSessionId(normalAny);
        }

        return filtered.length ? getSessionId(filtered[0]) : null;
    }

    async function switchBackendActive(sessionId) {
        if (!isValidSessionId(sessionId)) {
            return;
        }

        try {
            await fetchJson("/api/sessions/switch", {
                session_id: sessionId
            });
        } catch (err) {
            console.warn("[Nova Session Flat Actions] backend switch skipped", err);
        }
    }

    async function renderActiveSession(sessionId) {
        if (!isValidSessionId(sessionId)) {
            return;
        }

        setActiveSessionId(sessionId);

        if (
            window.NovaMobileChatRestoreKeeperV1 &&
            typeof window.NovaMobileChatRestoreKeeperV1.loadAndRender === "function"
        ) {
            await window.NovaMobileChatRestoreKeeperV1.loadAndRender("flat-actions-active");
            return;
        }

        if (
            window.NovaMobileSessionDrawerOwnerV1 &&
            typeof window.NovaMobileSessionDrawerOwnerV1.openSession === "function"
        ) {
            await window.NovaMobileSessionDrawerOwnerV1.openSession(sessionId);
        }
    }

    async function reloadDrawer() {
        if (
            window.NovaMobileSessionDrawerOwnerV1 &&
            typeof window.NovaMobileSessionDrawerOwnerV1.reload === "function"
        ) {
            await window.NovaMobileSessionDrawerOwnerV1.reload();
        }
    }

    function rowLooksPinned(row) {
        var text;

        text = row ? (row.innerText || row.textContent || "") : "";

        return (
            text.indexOf("📌") >= 0 ||
            text.indexOf("Unpin") >= 0
        );
    }

    async function renameSession(sessionId, row) {
        var currentTitle;
        var nextTitle;

        currentTitle = "";

        try {
            currentTitle = row.querySelector(".nova-session-drawer-title-v1").textContent || "";
            currentTitle = currentTitle.replace(/^📌\s*/, "").trim();
        } catch (err) {}

        nextTitle = window.prompt("Rename session:", currentTitle || "New Chat");

        if (!nextTitle || !nextTitle.trim()) {
            return;
        }

        nextTitle = nextTitle.trim();

        await fetchJson("/api/sessions/rename", {
            session_id: sessionId,
            title: nextTitle
        });

        console.log("[Nova Session Flat Actions] renamed", sessionId, nextTitle);

        await reloadDrawer();
    }

    async function pinSession(sessionId, row) {
        var nextPinned;

        nextPinned = !rowLooksPinned(row);

        await fetchJson("/api/sessions/pin", {
            session_id: sessionId,
            pinned: nextPinned
        });

        console.log("[Nova Session Flat Actions] pin changed", sessionId, nextPinned);

        await reloadDrawer();
    }

    async function deleteSession(sessionId) {
        var previousActiveId;
        var result;
        var list;
        var nextSessionId;
        var deletedWasActive;

        if (!window.confirm("Delete this session?")) {
            return;
        }

        previousActiveId = getActiveSessionId();
        deletedWasActive = previousActiveId === sessionId;

        result = await fetchJson("/api/sessions/delete", {
            session_id: sessionId
        });

        console.log("[Nova Session Flat Actions] deleted", sessionId, result);

        list = await getSessionList();

        nextSessionId = pickNextSession(
            list.sessions || result.sessions || [],
            sessionId,
            previousActiveId
        );

        if (isValidSessionId(nextSessionId)) {
            setActiveSessionId(nextSessionId);

            if (deletedWasActive) {
                await switchBackendActive(nextSessionId);
                await renderActiveSession(nextSessionId);
            } else {
                await switchBackendActive(nextSessionId);
            }
        }

        await reloadDrawer();
    }

    async function handleAction(event) {
        var button;
        var row;
        var action;
        var sessionId;

        button = event.target && event.target.closest
            ? event.target.closest("button[data-action]")
            : null;

        if (!button) {
            return;
        }

        row = button.closest(".nova-session-drawer-row-v1");

        if (!row) {
            return;
        }

        if (!button.closest("#nova-session-drawer-owner-backdrop-v1")) {
            return;
        }

        action = button.getAttribute("data-action");

        if (
            action !== "rename" &&
            action !== "pin" &&
            action !== "delete"
        ) {
            return;
        }

        sessionId = row.getAttribute("data-session-id");

        if (!isValidSessionId(sessionId)) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        try {
            if (action === "rename") {
                await renameSession(sessionId, row);
            } else if (action === "pin") {
                await pinSession(sessionId, row);
            } else if (action === "delete") {
                await deleteSession(sessionId);
            }
        } catch (err) {
            console.error("[Nova Session Flat Actions] action failed", action, err);
            window.alert("Session action failed: " + (err.message || err));
            await reloadDrawer().catch(function () {});
        }
    }

    document.addEventListener("click", function (event) {
        handleAction(event);
    }, true);

    window.NovaMobileSessionFlatActionsV1 = {
        version: VERSION,
        renameSession: renameSession,
        pinSession: pinSession,
        deleteSession: deleteSession
    };

    console.log("[Nova Session Flat Actions] ready", VERSION);
}());
