(function () {
    "use strict";

    var VERSION = "NOVA_MOBILE_HEADER_DOM_OWNER_20260705_LIVE_002";

    if (window.__NOVA_MOBILE_HEADER_DOM_OWNER_LIVE_002__) {
        return;
    }

    window.__NOVA_MOBILE_HEADER_DOM_OWNER_LIVE_002__ = true;

    function css(el, prop, value) {
        if (el && el.style) {
            el.style.setProperty(prop, value, "important");
        }
    }

    function removeBad() {
        [
            "nova-mobile-account-top",
            "nova-auth-workmode-register-v2",
            "nova-mobile-auth-logout",
            "nova-mobile-sessions-final-button-v1"
        ].forEach(function (id) {
            document.querySelectorAll("#" + id).forEach(function (el) {
                el.remove();
            });
        });

        document.querySelectorAll("button,a,[role='button']").forEach(function (el) {
            var text = (el.innerText || el.textContent || "").trim();

            if (/^(Account|Logout|Logging out\.\.\.|Create account)$/i.test(text)) {
                el.remove();
            }
        });
    }

    function own() {
        removeBad();

        var header =
            document.querySelector(".mobile-header") ||
            document.querySelector("#mobileHeader") ||
            document.querySelector(".nova-mobile-header") ||
            document.querySelector("header");

        if (!header) {
            return false;
        }

        css(header, "display", "flex");
        css(header, "align-items", "center");
        css(header, "justify-content", "space-between");
        css(header, "gap", "10px");
        css(header, "position", "sticky");
        css(header, "top", "0");
        css(header, "z-index", "4000");
        css(header, "pointer-events", "auto");

        var actions = document.querySelector(".mobile-header-actions");

        if (!actions) {
            actions = document.createElement("div");
            actions.className = "mobile-header-actions";
            header.appendChild(actions);
        }

        if (actions.parentElement !== header) {
            header.appendChild(actions);
        }

        css(actions, "display", "flex");
        css(actions, "align-items", "center");
        css(actions, "justify-content", "flex-end");
        css(actions, "gap", "8px");
        css(actions, "margin-left", "auto");
        css(actions, "position", "static");
        css(actions, "transform", "none");
        css(actions, "inset", "auto");
        css(actions, "pointer-events", "auto");

        var newBtn =
            document.getElementById("nova-mobile-new-chat") ||
            Array.from(document.querySelectorAll("button")).find(function (b) {
                return (b.innerText || b.textContent || "").trim() === "New";
            });

        if (!newBtn) {
            newBtn = document.createElement("button");
            newBtn.type = "button";
            newBtn.textContent = "New";
            newBtn.id = "nova-mobile-new-chat";
            newBtn.className = "mobile-header-btn";
        }

        var sessionsBtn =
            document.getElementById("nova-mobile-sessions-toggle") ||
            Array.from(document.querySelectorAll("button")).find(function (b) {
                return (b.innerText || b.textContent || "").trim() === "Sessions";
            });

        if (!sessionsBtn) {
            sessionsBtn = document.createElement("button");
            sessionsBtn.type = "button";
            sessionsBtn.textContent = "Sessions";
            sessionsBtn.id = "nova-mobile-sessions-toggle";
            sessionsBtn.className = "mobile-header-btn";
        }

        newBtn.id = "nova-mobile-new-chat";
        sessionsBtn.id = "nova-mobile-sessions-toggle";

        if (!/\bmobile-header-btn\b/.test(newBtn.className || "")) {
            newBtn.className = ((newBtn.className || "") + " mobile-header-btn").trim();
        }

        if (!/\bmobile-header-btn\b/.test(sessionsBtn.className || "")) {
            sessionsBtn.className = ((sessionsBtn.className || "") + " mobile-header-btn").trim();
        }

        actions.innerHTML = "";
        actions.appendChild(newBtn);
        actions.appendChild(sessionsBtn);

        [newBtn, sessionsBtn].forEach(function (btn) {
            css(btn, "display", "inline-flex");
            css(btn, "visibility", "visible");
            css(btn, "opacity", "1");
            css(btn, "position", "static");
            css(btn, "transform", "none");
            css(btn, "inset", "auto");
            css(btn, "float", "none");
            css(btn, "pointer-events", "auto");
            css(btn, "align-items", "center");
            css(btn, "justify-content", "center");
            css(btn, "z-index", "4001");
        });

        return true;
    }

    window.NovaMobileHeaderOwnerV1 = {
        version: VERSION,
        own: own
    };

    function run() {
        own();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", run);
    } else {
        run();
    }

    window.addEventListener("load", run);
    window.addEventListener("pageshow", run);

    try {
        new MutationObserver(function () {
            requestAnimationFrame(run);
        }).observe(document.documentElement, {
            childList: true,
            subtree: true
        });
    } catch (err) {}

    var n = 0;
    var timer = setInterval(function () {
        n += 1;
        run();

        if (n >= 30) {
            clearInterval(timer);
        }
    }, 300);

    console.log("[Nova Mobile Header Owner]", VERSION, "installed");
})();
