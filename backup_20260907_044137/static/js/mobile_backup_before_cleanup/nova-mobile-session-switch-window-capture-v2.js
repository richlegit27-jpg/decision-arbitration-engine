(function () {
    "use strict";

    const MARK = "__NOVA_MOBILE_SESSION_SWITCH_WINDOW_CAPTURE_V2_20260704__";

    if (window[MARK]) {
        return;
    }

    window[MARK] = true;

    let lastOpenAt = 0;

    function isSessionsLauncher(button) {
        if (!button) {
            return false;
        }

        const id = String(button.id || "").toLowerCase();
        const text = String(button.textContent || "").trim().toLowerCase();
        const aria = String(button.getAttribute("aria-label") || "").trim().toLowerCase();

        return (
            id === "nova-mobile-sessions-toggle" ||
            id === "nova-clean-session-launcher-v2" ||
            text === "sessions" ||
            aria === "sessions"
        );
    }

    function openSwitchPanel() {
        const now = Date.now();

        if (now - lastOpenAt < 350) {
            return;
        }

        lastOpenAt = now;

        const api = window.NovaMobileSessionSwitchRestoreV1;

        if (!api || typeof api.openPanel !== "function") {
            console.error("[Nova Session Switch Window Capture V2] SwitchRestore API missing", api);
            return;
        }

        console.error("[Nova Session Switch Window Capture V2] opening switch panel");

        api.openPanel().catch(function (err) {
            console.error("[Nova Session Switch Window Capture V2] open failed", err);
            alert("Sessions failed to open: " + err.message);
        });
    }

    function intercept(event) {
        const button = event.target && event.target.closest
            ? event.target.closest("button, [role='button'], a")
            : null;

        if (!isSessionsLauncher(button)) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        openSwitchPanel();

        return false;
    }

    ["pointerdown", "touchstart", "mousedown", "click"].forEach(function (eventName) {
        window.addEventListener(eventName, intercept, true);
        document.addEventListener(eventName, intercept, true);
    });

    console.error("[Nova Session Switch Window Capture V2] installed");
})();
