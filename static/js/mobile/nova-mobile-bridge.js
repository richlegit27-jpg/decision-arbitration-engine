(() => {
    "use strict";

    if (window.__novaBridgeLoaded) return;

    window.__novaBridgeLoaded = true;

    const $ = (id) => document.getElementById(id);

    function hasCore() {
        return typeof window.Nova !== "undefined";
    }

    setInterval(() => {
        try {
            if (window.Nova?.state?.activeSessionId) {
                localStorage.setItem(
                    "nova_active_session_id",
                    window.Nova.state.activeSessionId
                );
            }
        } catch (_) {}
    }, 2000);

    document.addEventListener("click", () => {
        if (!hasCore()) {
            return;
        }
    });

    console.log("[Nova Bridge] dumb layer loaded");
})();