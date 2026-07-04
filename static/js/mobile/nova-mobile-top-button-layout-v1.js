(function () {
    "use strict";

    var MARKER = "__NOVA_MOBILE_TOP_BUTTON_LAYOUT_V1_20260704__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    function pill(button, rightPx, widthPx) {
        if (!button) {
            return;
        }

        button.hidden = false;
        button.style.display = "inline-flex";
        button.style.alignItems = "center";
        button.style.justifyContent = "center";
        button.style.position = "fixed";
        button.style.top = "calc(8px + env(safe-area-inset-top))";
        button.style.right = rightPx + "px";
        button.style.left = "auto";
        button.style.width = widthPx + "px";
        button.style.maxWidth = widthPx + "px";
        button.style.height = "34px";
        button.style.margin = "0";
        button.style.padding = "0 8px";
        button.style.border = "1px solid rgba(255,255,255,0.22)";
        button.style.borderRadius = "12px";
        button.style.background = "rgba(20,20,30,0.96)";
        button.style.color = "#fff";
        button.style.fontWeight = "800";
        button.style.fontSize = "12px";
        button.style.lineHeight = "1";
        button.style.boxSizing = "border-box";
        button.style.whiteSpace = "nowrap";
        button.style.overflow = "hidden";
        button.style.textOverflow = "ellipsis";
        button.style.pointerEvents = "auto";
    }

    function applyLayout() {
        var header = document.querySelector(".mobile-header");
        var logout = document.getElementById("nova-mobile-auth-logout");
        var sessions = document.getElementById("nova-mobile-sessions-toggle");
        var floatingSessions = document.getElementById("nova-mobile-sessions-floating-v2");

        if (header) {
            header.style.paddingRight = "";
            header.style.transform = "";
            header.style.right = "";
            header.style.left = "";
            header.style.width = "";
            header.style.maxWidth = "100vw";
            header.style.overflow = "visible";
            header.style.boxSizing = "border-box";
        }

        pill(logout, 8, 64);
        pill(sessions, 78, 78);

        // Hide the extra floating Sessions button if it exists. One Sessions button only.
        if (floatingSessions) {
            floatingSessions.style.display = "none";
            floatingSessions.hidden = true;
            floatingSessions.setAttribute("aria-hidden", "true");
            floatingSessions.style.pointerEvents = "none";
        }

        if (logout) {
            logout.style.zIndex = "2147483647";
        }

        if (sessions) {
            sessions.style.zIndex = "2147483646";
        }

        console.log("[Nova Mobile Top Button Layout V1] applied simple layout");
    }

    applyLayout();

    setTimeout(applyLayout, 100);
    setTimeout(applyLayout, 300);
    setTimeout(applyLayout, 750);
    setTimeout(applyLayout, 1500);
    setTimeout(applyLayout, 3000);

    window.NovaMobileTopButtonLayoutV1 = {
        apply: applyLayout
    };

    console.log("[Nova Mobile Top Button Layout V1] installed simple layout");
})();
