(function () {
    "use strict";

    var MARKER = "__NOVA_MOBILE_SESSION_DRAWER_CLOSE_AUTHORITY_V1_20260704__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    var PANEL_ID = "nova-session-switch-restore-panel-v1";

    function getPanel() {
        return document.getElementById(PANEL_ID);
    }

    function clearDrawerState() {
        try {
            document.documentElement.style.overflow = "";
            document.body.style.overflow = "";

            document.documentElement.classList.remove(
                "nova-session-drawer-open",
                "nova-sessions-open",
                "session-drawer-open"
            );

            document.body.classList.remove(
                "nova-session-drawer-open",
                "nova-sessions-open",
                "session-drawer-open"
            );
        } catch (_) {}
    }

    function closePanel(reason) {
        var panel = getPanel();

        if (!panel) {
            clearDrawerState();
            return false;
        }

        try {
            panel.style.display = "none";
            panel.setAttribute("hidden", "hidden");
            panel.remove();
        } catch (_) {
            try {
                panel.parentNode && panel.parentNode.removeChild(panel);
            } catch (__) {}
        }

        clearDrawerState();

        console.log("[Nova Session Drawer Close Authority V1] closed", {
            reason: reason || "unknown"
        });

        return true;
    }

    function textOf(el) {
        if (!el) {
            return "";
        }

        return String(
            el.getAttribute("aria-label") ||
            el.getAttribute("title") ||
            el.innerText ||
            el.textContent ||
            ""
        ).trim();
    }

    function isCloseClick(event, panel) {
        var target = event.target;

        if (!target || !panel || !panel.contains(target)) {
            return false;
        }

        var control = target.closest(
            "button,a,[role='button'],[aria-label],[title],[data-close],[data-action]"
        );

        var label = textOf(control || target).toLowerCase();

        if (/\bclose\b/.test(label)) {
            return true;
        }

        var rect = panel.getBoundingClientRect();

        var inTopBar =
            event.clientY >= rect.top &&
            event.clientY <= rect.top + 72;

        var inRightCloseZone =
            event.clientX >= rect.right - 150 &&
            event.clientX <= rect.right + 5;

        return inTopBar && inRightCloseZone;
    }

    document.addEventListener("click", function (event) {
        var panel = getPanel();

        if (!panel) {
            return;
        }

        if (!isCloseClick(event, panel)) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        closePanel("close-click");
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") {
            return;
        }

        if (!getPanel()) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        closePanel("escape");
    }, true);

    window.NovaSessionDrawerCloseAuthorityV1 = {
        close: closePanel,
        getPanel: getPanel
    };

    console.log("[Nova Session Drawer Close Authority V1] installed");
})();
