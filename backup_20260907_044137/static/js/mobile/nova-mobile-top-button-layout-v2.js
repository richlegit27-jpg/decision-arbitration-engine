(function () {
    "use strict";

    var MARKER = "__NOVA_MOBILE_TOP_BUTTON_LAYOUT_V2_20260704__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    function baseButton(button) {
        if (!button) {
            return;
        }

        button.hidden = false;
        button.style.display = "inline-flex";
        button.style.alignItems = "center";
        button.style.justifyContent = "center";
        button.style.position = "fixed";
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
        button.style.transform = "none";
    }

    function openSessions(reason) {
        if (window.NovaMobileSessionsFinalV2 && typeof window.NovaMobileSessionsFinalV2.open === "function") {
            window.NovaMobileSessionsFinalV2.open(reason || "top-layout-v2-sessions-click");
            return true;
        }

        console.warn("[Nova Mobile Top Button Layout V2] Sessions API missing");
        return false;
    }

    function bindSessionsButton(sessions) {
        if (!sessions) {
            return;
        }

        sessions.dataset.novaTopLayoutV2SessionsDirect = "1";

        sessions.onclick = function (event) {
            event.preventDefault();
            event.stopPropagation();
            openSessions("top-layout-v2-direct-click");
            return false;
        };
    }

    function applyLayout() {
        var header = document.querySelector(".mobile-header");
        var account = document.getElementById("nova-mobile-account-top");
        var logout = document.getElementById("nova-mobile-auth-logout");
        var sessions = document.getElementById("nova-mobile-sessions-toggle");
        var floatingSessions = document.getElementById("nova-mobile-sessions-floating-v2");

        if (header) {
            header.style.paddingRight = "";
            header.style.paddingLeft = "";
            header.style.transform = "";
            header.style.right = "";
            header.style.left = "";
            header.style.width = "";
            header.style.maxWidth = "100vw";
            header.style.overflow = "visible";
            header.style.boxSizing = "border-box";
        }

        if (account) {
            account.style.zIndex = "2147483647";
            account.style.pointerEvents = "auto";
        }

        // Sessions alone on top-right.
        if (sessions) {
            baseButton(sessions);
            sessions.style.top = "calc(8px + env(safe-area-inset-top))";
            sessions.style.right = "8px";
            sessions.style.left = "auto";
            sessions.style.width = "86px";
            sessions.style.maxWidth = "86px";
            sessions.style.zIndex = "2147483647";
            bindSessionsButton(sessions);
        }

        // Logout lower-left, away from Sessions.
        if (logout) {
            baseButton(logout);
            logout.style.top = "calc(48px + env(safe-area-inset-top))";
            logout.style.left = "8px";
            logout.style.right = "auto";
            logout.style.width = "76px";
            logout.style.maxWidth = "76px";
            logout.style.zIndex = "2147483646";
        }

        // Hide duplicate floating Sessions button.
        if (floatingSessions) {
            floatingSessions.style.display = "none";
            floatingSessions.hidden = true;
            floatingSessions.setAttribute("aria-hidden", "true");
            floatingSessions.style.pointerEvents = "none";
        }

        console.log("[Nova Mobile Top Button Layout V2] applied separated buttons");
    }

    document.addEventListener("click", function (event) {
        var target = event.target && event.target.closest && event.target.closest("#nova-mobile-sessions-toggle");

        if (!target) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        openSessions("top-layout-v2-delegated-click");
    }, true);

    applyLayout();

    setTimeout(applyLayout, 100);
    setTimeout(applyLayout, 300);
    setTimeout(applyLayout, 750);
    setTimeout(applyLayout, 1500);
    setTimeout(applyLayout, 3000);

    window.NovaMobileTopButtonLayoutV2 = {
        apply: applyLayout,
        openSessions: openSessions
    };

    console.log("[Nova Mobile Top Button Layout V2] installed");
})();
