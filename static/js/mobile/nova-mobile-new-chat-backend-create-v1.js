(function () {
    "use strict";

    var MARK = "NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_SINGLE_OWNER_20260705";

    if (window.__NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_SINGLE_OWNER_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_NEW_CHAT_BACKEND_CREATE_SINGLE_OWNER_20260705__ = true;

    var inFlight = false;

    function log() {
        try {
            console.log.apply(console, ["[" + MARK + "]"].concat(Array.from(arguments)));
        } catch (_) {}
    }

    function isNewChatButton(el) {
        if (!el) return false;

        var text = String(el.innerText || el.textContent || "").trim().toLowerCase();
        var id = String(el.id || "").toLowerCase();
        var klass = String(el.className || "").toLowerCase();
        var aria = String(el.getAttribute("aria-label") || "").toLowerCase();
        var title = String(el.getAttribute("title") || "").toLowerCase();
        var dataAction = String(el.getAttribute("data-action") || "").toLowerCase();
        var novaAction = String(el.getAttribute("data-nova-action") || "").toLowerCase();

        var haystack = [text, id, klass, aria, title, dataAction, novaAction].join(" ");

        if (haystack.indexOf("rename") >= 0) return false;
        if (haystack.indexOf("delete") >= 0) return false;
        if (haystack.indexOf("pin") >= 0) return false;
        if (haystack.indexOf("close") >= 0) return false;
        if (haystack.indexOf("send") >= 0) return false;
        if (haystack.indexOf("attach") >= 0) return false;

        return (
            text === "new chat" ||
            text === "+ new chat" ||
            haystack.indexOf("new-chat") >= 0 ||
            haystack.indexOf("new chat") >= 0 ||
            haystack.indexOf("new session") >= 0 ||
            haystack.indexOf("nova-mobile-new-chat") >= 0
        );
    }

    function extractSessionId(data) {
        if (!data || typeof data !== "object") return "";

        return (
            data.session_id ||
            data.id ||
            (data.session && (data.session.id || data.session.session_id)) ||
            (data.data && (data.data.id || data.data.session_id)) ||
            ""
        );
    }

    async function createNewChat(event) {
        try {
            if (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
            }
        } catch (_) {}

        if (inFlight) {
            log("ignored duplicate new chat");
            return;
        }

        inFlight = true;

        try {
            log("creating new chat");

            var response = await fetch("/api/sessions/new", {
                method: "POST",
                credentials: "include",
                cache: "no-store",
                headers: {
                    "Accept": "application/json"
                }
            });

            var raw = await response.text();

            if (!response.ok) {
                throw new Error("HTTP " + response.status + ": " + raw.slice(0, 500));
            }

            var data = {};
            try {
                data = JSON.parse(raw);
            } catch (_) {}

            var sid = extractSessionId(data);

            if (!sid) {
                throw new Error("New chat created but no session id returned: " + raw.slice(0, 500));
            }

            try {
                localStorage.setItem("nova_mobile_active_session_id", sid);
                localStorage.setItem("nova_active_session_id", sid);
            } catch (_) {}

            location.href = "/mobile?session_id=" + encodeURIComponent(sid) + "&v=new-chat-owner-" + Date.now();
        } catch (error) {
            console.error("[" + MARK + "] failed", error);
            alert("New Chat failed: " + (error && error.message ? error.message : String(error)));
        } finally {
            inFlight = false;
        }
    }

    function bindButtons() {
        var count = 0;

        Array.from(document.querySelectorAll("button, a, [role='button']")).forEach(function (el) {
            if (!isNewChatButton(el)) return;

            count += 1;

            if (el.dataset.novaNewChatSingleOwner === "1") return;

            el.dataset.novaNewChatSingleOwner = "1";
            el.addEventListener("click", createNewChat, true);

            try {
                el.disabled = false;
                el.removeAttribute("disabled");
                el.style.pointerEvents = "auto";
            } catch (_) {}
        });

        return count;
    }

    document.addEventListener("click", function (event) {
        var target = event.target;
        var button = target && target.closest && target.closest("button, a, [role='button']");
        if (!button) return;

        if (isNewChatButton(button)) {
            createNewChat(event);
        }
    }, true);

    function boot() {
        var count = bindButtons();
        log("ready", { bound: count });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }

    setTimeout(boot, 250);
    setTimeout(boot, 900);
    setTimeout(boot, 1800);

    var observer = new MutationObserver(boot);
    observer.observe(document.documentElement || document.body, {
        childList: true,
        subtree: true
    });

    window.NovaMobileNewChatBackendCreateV1 = {
        version: MARK,
        createNewChat: createNewChat,
        bindButtons: bindButtons
    };
})();
