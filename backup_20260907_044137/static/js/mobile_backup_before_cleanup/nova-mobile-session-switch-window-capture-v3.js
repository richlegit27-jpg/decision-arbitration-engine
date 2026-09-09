(function () {
    "use strict";

    const MARK = "__NOVA_MOBILE_SESSION_SWITCH_WINDOW_CAPTURE_V3_20260704__";
    const PANEL_ID = "nova-session-switch-restore-panel-v1";

    if (window[MARK]) {
        return;
    }

    window[MARK] = true;

    let lastOpenAt = 0;
    let opening = false;

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

    function panelExists() {
        const panel = document.getElementById(PANEL_ID);
        return !!(panel && panel.isConnected);
    }

    function openSwitchPanelOnce(eventName) {
        const now = Date.now();

        if (panelExists()) {
            console.error("[Nova Session Switch Window Capture V3] panel already open");
            return;
        }

        if (opening || now - lastOpenAt < 1200) {
            console.error("[Nova Session Switch Window Capture V3] ignored duplicate open", eventName);
            return;
        }

        opening = true;
        lastOpenAt = now;

        const api = window.NovaMobileSessionSwitchRestoreV1;

        if (!api || typeof api.openPanel !== "function") {
            opening = false;
            console.error("[Nova Session Switch Window Capture V3] SwitchRestore API missing", api);
            return;
        }

        console.error("[Nova Session Switch Window Capture V3] opening switch panel", eventName);

        Promise.resolve(api.openPanel())
            .catch(function (err) {
                console.error("[Nova Session Switch Window Capture V3] open failed", err);
                alert("Sessions failed to open: " + err.message);
            })
            .finally(function () {
                setTimeout(function () {
                    opening = false;
                }, 900);
            });
    }

    function intercept(event) {
        if (event.target && event.target.closest && event.target.closest("#" + PANEL_ID)) {
            return;
        }

        const button = event.target && event.target.closest
            ? event.target.closest("button, [role='button'], a")
            : null;

        if (!isSessionsLauncher(button)) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        openSwitchPanelOnce(event.type);

        return false;
    }

    ["pointerdown", "touchstart", "mousedown", "click"].forEach(function (eventName) {
        window.addEventListener(eventName, intercept, true);
    });

    window.NovaMobileSessionSwitchWindowCaptureV3 = {
        version: "session-switch-window-capture-v3"
    };

    console.error("[Nova Session Switch Window Capture V3] installed");
})();
