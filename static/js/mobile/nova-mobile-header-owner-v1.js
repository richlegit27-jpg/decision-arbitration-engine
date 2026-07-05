(function () {
    "use strict";

    var VERSION = "NOVA_MOBILE_HEADER_DOM_OWNER_20260705";

    if (window.__NOVA_MOBILE_HEADER_DOM_OWNER_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_HEADER_DOM_OWNER_20260705__ = true;

    var BAD_IDS = [
        "nova-mobile-account-top",
        "nova-auth-workmode-register-v2",
        "nova-mobile-auth-logout",
        "nova-mobile-sessions-final-button-v1"
    ];

    function byId(id) {
        return document.getElementById(id);
    }

    function setImportant(el, prop, value) {
        if (!el || !el.style) {
            return;
        }

        el.style.setProperty(prop, value, "important");
    }

    function installCriticalStyle() {
        if (byId("nova-mobile-header-owner-style-v1")) {
            return;
        }

        var style = document.createElement("style");
        style.id = "nova-mobile-header-owner-style-v1";
        style.textContent = `
/* NOVA_MOBILE_HEADER_DOM_OWNER_STYLE_20260705 */
#nova-mobile-account-top,
#nova-auth-workmode-register-v2,
#nova-mobile-auth-logout,
#nova-mobile-sessions-final-button-v1 {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
    position: absolute !important;
    left: -99999px !important;
    top: -99999px !important;
    width: 0 !important;
    height: 0 !important;
    max-width: 0 !important;
    max-height: 0 !important;
    overflow: hidden !important;
    z-index: -1 !important;
}

.mobile-header,
#mobileHeader,
.nova-mobile-header {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 10px !important;
    position: sticky !important;
    top: 0 !important;
    z-index: 4000 !important;
    width: 100% !important;
    box-sizing: border-box !important;
}

.mobile-header-actions {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end !important;
    gap: 8px !important;
    margin-left: auto !important;
    position: static !important;
    transform: none !important;
    inset: auto !important;
}

#nova-mobile-new-chat,
#nova-mobile-sessions-toggle {
    display: inline-flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    position: static !important;
    transform: none !important;
    inset: auto !important;
    float: none !important;
    z-index: 4001 !important;
}
/* /NOVA_MOBILE_HEADER_DOM_OWNER_STYLE_20260705 */
`;

        (document.head || document.documentElement).appendChild(style);
    }

    function removeBadControls() {
        BAD_IDS.forEach(function (id) {
            Array.from(document.querySelectorAll("#" + id)).forEach(function (el) {
                el.remove();
            });
        });

        Array.from(document.querySelectorAll("button,a,[role='button']")).forEach(function (el) {
            var text = (el.innerText || el.textContent || "").trim();
            var id = el.id || "";
            var cls = String(el.className || "");

            var badByText = /^(Account|Logout|Logging out\.\.\.|Create account)$/i.test(text);
            var badByName = /mobile-account|auth-logout|workmode-register|sessions-final/i.test(id + " " + cls);

            if (badByText || badByName) {
                el.remove();
            }
        });
    }

    function findHeader() {
        return (
            document.querySelector(".mobile-header") ||
            document.querySelector("#mobileHeader") ||
            document.querySelector(".nova-mobile-header") ||
            document.querySelector("header")
        );
    }

    function ensureActions(header) {
        var actions = document.querySelector(".mobile-header-actions");

        if (!actions) {
            actions = document.createElement("div");
            actions.className = "mobile-header-actions";
        }

        if (header && actions.parentElement !== header) {
            header.appendChild(actions);
        }

        setImportant(actions, "display", "flex");
        setImportant(actions, "align-items", "center");
        setImportant(actions, "justify-content", "flex-end");
        setImportant(actions, "gap", "8px");
        setImportant(actions, "margin-left", "auto");
        setImportant(actions, "position", "static");
        setImportant(actions, "transform", "none");
        setImportant(actions, "inset", "auto");
        setImportant(actions, "pointer-events", "auto");

        return actions;
    }

    function findButtonByText(label) {
        return Array.from(document.querySelectorAll("button,a,[role='button']")).find(function (el) {
            return ((el.innerText || el.textContent || "").trim().toLowerCase() === label.toLowerCase());
        });
    }

    function ensureButton(id, label) {
        var btn = byId(id) || findButtonByText(label);

        if (!btn) {
            btn = document.createElement("button");
            btn.type = "button";
            btn.textContent = label;
        }

        btn.id = id;

        if (btn.tagName === "BUTTON") {
            btn.type = "button";
        }

        if (!/\bmobile-header-btn\b/.test(String(btn.className || ""))) {
            btn.className = ((btn.className || "") + " mobile-header-btn").trim();
        }

        setImportant(btn, "display", "inline-flex");
        setImportant(btn, "visibility", "visible");
        setImportant(btn, "opacity", "1");
        setImportant(btn, "position", "static");
        setImportant(btn, "transform", "none");
        setImportant(btn, "inset", "auto");
        setImportant(btn, "float", "none");
        setImportant(btn, "pointer-events", "auto");
        setImportant(btn, "align-items", "center");
        setImportant(btn, "justify-content", "center");
        setImportant(btn, "z-index", "4001");

        return btn;
    }

    function bindSessions(btn) {
        if (!btn || btn.__novaHeaderOwnerSessionsBound) {
            return;
        }

        btn.__novaHeaderOwnerSessionsBound = true;

        btn.addEventListener("click", function () {
            var owner = window.NovaMobileSessionDrawerOwnerV1 || window.NovaMobileSessions || {};

            if (typeof owner.toggle === "function") {
                owner.toggle();
                return;
            }

            if (typeof owner.open === "function") {
                owner.open();
                return;
            }

            document.dispatchEvent(new CustomEvent("nova:mobile:sessions:toggle"));
            window.dispatchEvent(new CustomEvent("nova:mobile:sessions:toggle"));
        });
    }

    function bindNew(btn) {
        if (!btn || btn.__novaHeaderOwnerNewBound) {
            return;
        }

        btn.__novaHeaderOwnerNewBound = true;

        btn.addEventListener("click", function () {
            var owner = window.NovaMobileNewChatBackendCreateV1 || {};

            if (typeof owner.create === "function") {
                owner.create();
                return;
            }

            if (typeof owner.newChat === "function") {
                owner.newChat();
                return;
            }

            if (typeof owner.start === "function") {
                owner.start();
                return;
            }

            document.dispatchEvent(new CustomEvent("nova:mobile:new-chat"));
            window.dispatchEvent(new CustomEvent("nova:mobile:new-chat"));
        });
    }

    function ownHeader() {
        installCriticalStyle();
        removeBadControls();

        var header = findHeader();

        if (!header) {
            return;
        }

        setImportant(header, "display", "flex");
        setImportant(header, "align-items", "center");
        setImportant(header, "justify-content", "space-between");
        setImportant(header, "gap", "10px");
        setImportant(header, "position", "sticky");
        setImportant(header, "top", "0");
        setImportant(header, "z-index", "4000");
        setImportant(header, "width", "100%");
        setImportant(header, "box-sizing", "border-box");
        setImportant(header, "pointer-events", "auto");

        var actions = ensureActions(header);
        var newBtn = ensureButton("nova-mobile-new-chat", "New");
        var sessionsBtn = ensureButton("nova-mobile-sessions-toggle", "Sessions");

        Array.from(actions.children).forEach(function (child) {
            if (child !== newBtn && child !== sessionsBtn) {
                child.remove();
            }
        });

        if (newBtn.parentElement !== actions) {
            actions.appendChild(newBtn);
        }

        if (sessionsBtn.parentElement !== actions) {
            actions.appendChild(sessionsBtn);
        }

        bindNew(newBtn);
        bindSessions(sessionsBtn);

        window.NovaMobileHeaderOwnerV1 = {
            version: VERSION,
            own: ownHeader
        };
    }

    var scheduled = false;

    function scheduleOwn() {
        if (scheduled) {
            return;
        }

        scheduled = true;

        requestAnimationFrame(function () {
            scheduled = false;
            ownHeader();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", ownHeader);
    } else {
        ownHeader();
    }

    window.addEventListener("load", ownHeader);
    window.addEventListener("pageshow", ownHeader);
    document.addEventListener("visibilitychange", ownHeader);

    try {
        new MutationObserver(scheduleOwn).observe(document.documentElement, {
            childList: true,
            subtree: true
        });
    } catch (err) {
        // MutationObserver is only a safety net.
    }

    var runs = 0;
    var timer = setInterval(function () {
        runs += 1;
        ownHeader();

        if (runs >= 20) {
            clearInterval(timer);
        }
    }, 500);

    console.log("[Nova Mobile Header Owner]", VERSION, "installed");
})();
