(function () {
    "use strict";

    var MARKER = "__NOVA_MOBILE_SESSION_LAUNCHER_AUTHORITY_V1_20260704__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    var HEADER_BUTTON_ID = "nova-mobile-sessions-toggle";
    var CLEAN_BUTTON_ID = "nova-clean-session-launcher-v2";
    var RESTORE_PANEL_ID = "nova-session-switch-restore-panel-v1";

    function byId(id) {
        return document.getElementById(id);
    }

    function panelOpen() {
        return !!byId(RESTORE_PANEL_ID);
    }

    function hideDuplicateLauncher() {
        var clean = byId(CLEAN_BUTTON_ID);

        if (!clean) {
            return false;
        }

        clean.style.position = "fixed";
        clean.style.left = "-9999px";
        clean.style.top = "-9999px";
        clean.style.width = "1px";
        clean.style.height = "1px";
        clean.style.opacity = "0";
        clean.style.pointerEvents = "none";
        clean.style.zIndex = "-1";
        clean.setAttribute("aria-hidden", "true");
        clean.setAttribute("tabindex", "-1");
        clean.dataset.novaHiddenDuplicateLauncher = "1";

        return true;
    }

    function normalizeHeaderButton() {
        var header = byId(HEADER_BUTTON_ID);

        if (!header) {
            return false;
        }

        header.textContent = "Sessions";
        header.setAttribute("aria-label", "Sessions");
        header.dataset.novaSessionLauncherAuthority = "1";

        return true;
    }

    function clickCleanLauncher(reason) {
        var clean = byId(CLEAN_BUTTON_ID);

        if (!clean) {
            console.warn("[Nova Session Launcher Authority V1] clean launcher missing", {
                reason: reason || "unknown"
            });

            return false;
        }

        clean.dispatchEvent(new MouseEvent("click", {
            bubbles: true,
            cancelable: true,
            view: window
        }));

        console.log("[Nova Session Launcher Authority V1] forwarded to clean launcher", {
            reason: reason || "unknown",
            panelOpen: panelOpen()
        });

        return true;
    }

    function openSessions(reason) {
        if (panelOpen()) {
            return true;
        }

        return clickCleanLauncher(reason || "open");
    }

    function install() {
        normalizeHeaderButton();
        hideDuplicateLauncher();
    }

    document.addEventListener("click", function (event) {
        var target = event.target;

        if (!target || !target.closest) {
            return;
        }

        var header = target.closest("#" + HEADER_BUTTON_ID);

        if (!header) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        install();
        openSessions("header-button");
    }, true);

    var observer = new MutationObserver(function () {
        install();
    });

    try {
        observer.observe(document.documentElement, {
            childList: true,
            subtree: true
        });
    } catch (_) {}

    install();

    setTimeout(install, 250);
    setTimeout(install, 750);
    setTimeout(install, 1500);
    setTimeout(install, 3000);

    window.NovaSessionLauncherAuthorityV1 = {
        open: openSessions,
        install: install,
        panelOpen: panelOpen,
        hideDuplicateLauncher: hideDuplicateLauncher,
        clickCleanLauncher: clickCleanLauncher
    };

    console.log("[Nova Session Launcher Authority V1] installed");
})();
