(function () {
    "use strict";

    var MARKER = "__NOVA_MOBILE_TOP_BUTTON_LAYOUT_V3_20260704__";

    if (window[MARKER]) {
        return;
    }

    window[MARKER] = true;

    function allClickables() {
        return Array.from(document.querySelectorAll(
            "button,a,[role='button'],input[type='button'],input[type='submit']"
        ));
    }

    function textOf(el) {
        if (!el) {
            return "";
        }

        return [
            el.textContent || "",
            el.value || "",
            el.id || "",
            el.getAttribute("aria-label") || "",
            el.getAttribute("title") || "",
            el.className || ""
        ].join(" ").replace(/\s+/g, " ").trim();
    }

    function visibleScore(el) {
        if (!el) {
            return 0;
        }

        var style = window.getComputedStyle(el);
        var rect = el.getBoundingClientRect();

        if (style.display === "none" || style.visibility === "hidden" || el.hidden) {
            return 0;
        }

        return Math.round((rect.width || 0) + (rect.height || 0));
    }

    function findButton(preferredId, pattern) {
        var byId = document.getElementById(preferredId);
        var list = allClickables().filter(function (el) {
            return pattern.test(textOf(el));
        });

        if (byId) {
            list.unshift(byId);
        }

        list = Array.from(new Set(list));

        list.sort(function (a, b) {
            var aId = a.id === preferredId ? 10000 : 0;
            var bId = b.id === preferredId ? 10000 : 0;
            return (bId + visibleScore(b)) - (aId + visibleScore(a));
        });

        return list[0] || null;
    }

    function hideDuplicates(target, pattern) {
        allClickables().forEach(function (el) {
            if (el === target) {
                return;
            }

            if (!pattern.test(textOf(el))) {
                return;
            }

            el.style.display = "none";
            el.hidden = true;
            el.setAttribute("aria-hidden", "true");
            el.style.pointerEvents = "none";
        });
    }

    function baseButton(button) {
        if (!button) {
            return;
        }

        button.hidden = false;
        button.removeAttribute("aria-hidden");
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
        if (
            window.NovaMobileSessionsFinalV2 &&
            typeof window.NovaMobileSessionsFinalV2.open === "function"
        ) {
            window.NovaMobileSessionsFinalV2.open(reason || "top-layout-v3-sessions-click");
            return true;
        }

        console.warn("[Nova Mobile Top Button Layout V3] Sessions API missing");
        return false;
    }

    function bindSessionsButton(button) {
        if (!button) {
            return;
        }

        button.dataset.novaTopLayoutV3SessionsDirect = "1";

        button.onclick = function (event) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();

            openSessions("top-layout-v3-direct-click");

            return false;
        };
    }

    function applyLayout() {
        var header = document.querySelector(".mobile-header");
        var sessionsPattern = /\bsessions?\b/i;
        var logoutPattern = /\b(log\s*out|logout|sign\s*out)\b/i;

        var sessions = findButton("nova-mobile-sessions-toggle", sessionsPattern);
        var logout = findButton("nova-mobile-auth-logout", logoutPattern);
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

        if (floatingSessions && floatingSessions !== sessions) {
            floatingSessions.style.display = "none";
            floatingSessions.hidden = true;
            floatingSessions.setAttribute("aria-hidden", "true");
            floatingSessions.style.pointerEvents = "none";
        }

        hideDuplicates(sessions, sessionsPattern);
        hideDuplicates(logout, logoutPattern);

        if (sessions) {
            baseButton(sessions);
            sessions.id = "nova-mobile-sessions-toggle";
            sessions.textContent = "Sessions";
            sessions.style.top = "calc(8px + env(safe-area-inset-top))";
            sessions.style.right = "8px";
            sessions.style.left = "auto";
            sessions.style.width = "92px";
            sessions.style.maxWidth = "92px";
            sessions.style.zIndex = "2147483647";
            bindSessionsButton(sessions);
        }

        if (logout) {
            baseButton(logout);
            logout.id = "nova-mobile-auth-logout";
            logout.textContent = "Logout";
            logout.style.top = "calc(48px + env(safe-area-inset-top))";
            logout.style.left = "8px";
            logout.style.right = "auto";
            logout.style.width = "82px";
            logout.style.maxWidth = "82px";
            logout.style.zIndex = "2147483646";
        }

        console.log("[Nova Mobile Top Button Layout V3] located buttons", {
            sessions: sessions ? textOf(sessions) : null,
            logout: logout ? textOf(logout) : null
        });
    }

    document.addEventListener("click", function (event) {
        var sessions = document.getElementById("nova-mobile-sessions-toggle");

        if (!sessions) {
            return;
        }

        if (event.target === sessions || sessions.contains(event.target)) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            openSessions("top-layout-v3-capture-click");
        }
    }, true);

    applyLayout();

    setTimeout(applyLayout, 100);
    setTimeout(applyLayout, 300);
    setTimeout(applyLayout, 750);
    setTimeout(applyLayout, 1500);
    setTimeout(applyLayout, 3000);

    window.NovaMobileTopButtonLayoutV3 = {
        apply: applyLayout,
        openSessions: openSessions
    };

    console.log("[Nova Mobile Top Button Layout V3] installed");
})();
