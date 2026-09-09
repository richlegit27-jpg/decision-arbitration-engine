(function () {
    "use strict";

    const MARK = "__NOVA_MOBILE_SESSION_SWITCH_WINDOW_CAPTURE_V4_20260704__";
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

    function getPanel() {
        return document.getElementById(PANEL_ID);
    }

    function forcePanelVisible(panel) {
        if (!panel) {
            return false;
        }

        panel.style.setProperty("display", "block", "important");
        panel.style.setProperty("visibility", "visible", "important");
        panel.style.setProperty("opacity", "1", "important");
        panel.style.setProperty("pointer-events", "auto", "important");
        panel.style.setProperty("position", "fixed", "important");
        panel.style.setProperty("top", "64px", "important");
        panel.style.setProperty("left", "10px", "important");
        panel.style.setProperty("right", "10px", "important");
        panel.style.setProperty("max-height", "72vh", "important");
        panel.style.setProperty("overflow", "auto", "important");
        panel.style.setProperty("z-index", "2147483647", "important");

        return true;
    }

    function panelExistsAndHasRows() {
        const panel = getPanel();

        if (!panel || !panel.isConnected) {
            return false;
        }

        forcePanelVisible(panel);

        const rows = panel.querySelectorAll("[data-session-id]").length;

        console.error("[Nova Session Switch Window Capture V4] panel already open rows", rows);

        return rows > 0;
    }

    function openSwitchPanelOnce(eventName) {
        const now = Date.now();

        if (panelExistsAndHasRows()) {
            return;
        }

        if (opening || now - lastOpenAt < 900) {
            console.error("[Nova Session Switch Window Capture V4] ignored duplicate open", eventName);
            return;
        }

        opening = true;
        lastOpenAt = now;

        const api = window.NovaMobileSessionSwitchRestoreV1;

        if (!api || typeof api.openPanel !== "function") {
            opening = false;
            console.error("[Nova Session Switch Window Capture V4] SwitchRestore API missing", api);
            return;
        }

        console.error("[Nova Session Switch Window Capture V4] opening switch panel", eventName);

        Promise.resolve(api.openPanel())
            .then(function () {
                setTimeout(function () {
                    forcePanelVisible(getPanel());
                }, 50);

                setTimeout(function () {
                    forcePanelVisible(getPanel());
                }, 250);
            })
            .catch(function (err) {
                console.error("[Nova Session Switch Window Capture V4] open failed", err);
                alert("Sessions failed to open: " + err.message);
            })
            .finally(function () {
                setTimeout(function () {
                    opening = false;
                }, 700);
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

    window.NovaMobileSessionSwitchWindowCaptureV4 = {
        version: "session-switch-window-capture-v4",
        open: function () {
            openSwitchPanelOnce("manual");
        },
        forceVisible: function () {
            forcePanelVisible(getPanel());
        }
    };

    console.error("[Nova Session Switch Window Capture V4] installed");
})();
