(function () {
    "use strict";

    var MARKER = "__NOVA_MOBILE_TOP_BUTTON_LAYOUT_V1_20260704__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    function stylePill(button) {
        if (!button) {
            return;
        }

        button.style.position = "fixed";
        button.style.top = "calc(8px + env(safe-area-inset-top))";
        button.style.border = "1px solid rgba(255,255,255,0.22)";
        button.style.borderRadius = "12px";
        button.style.background = "rgba(20,20,30,0.96)";
        button.style.color = "#fff";
        button.style.padding = "8px 10px";
        button.style.fontWeight = "800";
        button.style.fontSize = "13px";
        button.style.lineHeight = "1";
        button.style.height = "34px";
        button.style.minWidth = "auto";
        button.style.pointerEvents = "auto";
        button.style.boxSizing = "border-box";
        button.style.whiteSpace = "nowrap";
    }

    function applyLayout() {
        var logout = document.getElementById("nova-mobile-auth-logout");
        var sessions = document.getElementById("nova-mobile-sessions-toggle");
        var floatingSessions = document.getElementById("nova-mobile-sessions-floating-v2");
        var header = document.querySelector(".mobile-header");

        if (header) {
            header.style.paddingRight = "170px";
            header.style.boxSizing = "border-box";
        }

        if (logout) {
            stylePill(logout);
            logout.style.right = "8px";
            logout.style.zIndex = "2147483647";
            logout.style.display = "";
            logout.hidden = false;
        }

        if (sessions) {
            stylePill(sessions);
            sessions.style.right = "82px";
            sessions.style.zIndex = "2147483646";
            sessions.style.marginRight = "0";
            sessions.style.display = "";
            sessions.hidden = false;
        }

        if (floatingSessions) {
            stylePill(floatingSessions);
            floatingSessions.style.right = "82px";
            floatingSessions.style.zIndex = "2147483646";
            floatingSessions.style.display = "";
            floatingSessions.hidden = false;
        }
    }

    applyLayout();

    setTimeout(applyLayout, 250);
    setTimeout(applyLayout, 750);
    setTimeout(applyLayout, 1500);
    setTimeout(applyLayout, 3000);

    window.NovaMobileTopButtonLayoutV1 = {
        apply: applyLayout
    };

    console.log("[Nova Mobile Top Button Layout V1] installed");
})();
