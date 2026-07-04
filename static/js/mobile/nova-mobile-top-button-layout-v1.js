(function () {
    "use strict";

    var MARKER = "__NOVA_MOBILE_TOP_BUTTON_LAYOUT_V1_20260704__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    function pill(button) {
        if (!button) {
            return;
        }

        button.hidden = false;
        button.style.display = "inline-flex";
        button.style.alignItems = "center";
        button.style.justifyContent = "center";
        button.style.position = "fixed";
        button.style.top = "calc(8px + env(safe-area-inset-top))";
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
        var account = document.getElementById("nova-mobile-account-top");
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

        if (account) {
            account.style.zIndex = "2147483647";
            account.style.pointerEvents = "auto";
        }

        // Move Logout to the left side, beside Account.
        if (logout) {
            pill(logout);
            logout.style.left = "86px";
            logout.style.right = "auto";
            logout.style.width = "68px";
            logout.style.maxWidth = "68px";
            logout.style.zIndex = "2147483647";
        }

        // Keep Sessions alone on the right and bind it directly.
        if (sessions) {
            pill(sessions);
            sessions.style.right = "8px";
            sessions.style.left = "auto";
            sessions.style.width = "82px";
            sessions.style.maxWidth = "82px";
            sessions.style.zIndex = "2147483647";
            sessions.style.pointerEvents = "auto";
            sessions.dataset.novaTopLayoutSessionsDirect = "1";

            sessions.onclick = function (event) {
                event.preventDefault();
                event.stopPropagation();

                if (window.NovaMobileSessionsFinalV2 && typeof window.NovaMobileSessionsFinalV2.open === "function") {
                    window.NovaMobileSessionsFinalV2.open("top-layout-direct-sessions-click");
                    return false;
                }

                console.warn("[Nova Mobile Top Button Layout V1] Sessions API missing");

                return false;
            };
        }

        // Hide extra floating Sessions if it exists.
        if (floatingSessions) {
            floatingSessions.style.display = "none";
            floatingSessions.hidden = true;
            floatingSessions.setAttribute("aria-hidden", "true");
            floatingSessions.style.pointerEvents = "none";
        }

        console.log("[Nova Mobile Top Button Layout V1] applied left logout right sessions");
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

    console.log("[Nova Mobile Top Button Layout V1] installed left logout right sessions");
})();

