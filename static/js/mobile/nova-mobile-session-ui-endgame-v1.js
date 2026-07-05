(function () {
    "use strict";

    window.__NOVA_FORCE_SESSIONS_OPENER_V3_DISABLED_20260704__ = true;

    const existing = document.getElementById("nova-force-sessions-opener-v3");
    if (existing && existing.parentNode) {
        existing.parentNode.removeChild(existing);
    }

    console.log("[DISABLED] Nova Force Sessions Opener V3 removed");
})();
