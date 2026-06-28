(() => {
    "use strict";

    if (window.__novaBridgeLoaded) return;
    window.__novaBridgeLoaded = true;

    const $ = (id) => document.getElementById(id);

    function hasCore() {
        return typeof window.Nova !== "undefined";
    }

    document.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-session-id], .session-btn");
        if (!btn) return;

        const id = btn.getAttribute("data-session-id");
        if (!id || !hasCore()) return;

        window.Nova.openSession?.(id);
    }, true);

    document.addEventListener("click", (e) => {
        const el = e.target.closest("#nova-open-sessions, .open-sessions-btn");
        if (!el || !hasCore()) return;

        window.Nova.openSessions?.();
    }, true);

    setInterval(() => {
        try {
            if (window.Nova?.state?.activeSessionId) {
                localStorage.setItem(
                    "nova_active_session_id",
                    window.Nova.state.activeSessionId
                );
            }
        } catch {}
    }, 2000);

    console.log("[Nova Bridge] dumb layer loaded");
})();