(function () {
    "use strict";

    console.log("[BRIDGE TEST] session restore bridge started");

    if (window.__NOVA_MOBILE_SESSION_RESTORE_BRIDGE_V1__) {
        return;
    }

    window.__NOVA_MOBILE_SESSION_RESTORE_BRIDGE_V1__ = true;

    const LOG = "[Nova Mobile Session Restore Bridge]";

    function text(value) {
        return String(value || "");
    }

    function findChatContainer() {
        return (
            document.getElementById("mobileChatMessages") ||
            document.getElementById("nova-mobile-chat-messages") ||
            document.querySelector("[data-nova-chat-messages]") ||
            document.querySelector(".mobile-chat-container") ||
            document.querySelector(".chat-messages")
        );
    }

function getMessageText(message) {
    return text(
        message.text ||
        message.content ||
        message.message ||
        message.body ||
        ""
    );
}

function getMessageRole(message) {
    return message.role === "user" ? "user" : "assistant";
}

    function addAttachmentNodes(wrapper, attachments) {
        if (!Array.isArray(attachments) || attachments.length < 1) {
            return;
        }

        const list = document.createElement("div");
        list.className = "nova-mobile-restored-attachments";

        attachments.forEach((attachment) => {
            const url = attachment.url || attachment.file_url || attachment.path || attachment.href || "";
            const name = attachment.filename || attachment.name || attachment.original_name || "attachment";

            if (!url) {
                return;
            }

            const chip = document.createElement("a");
            chip.className = "nova-mobile-restored-attachment-chip";
            chip.href = url;
            chip.target = "_blank";
            chip.rel = "noopener noreferrer";
            chip.textContent = name;

            list.appendChild(chip);
        });

        if (list.children.length > 0) {
            wrapper.appendChild(list);
        }
    }

    function renderMessages(messages) {
        const box = findChatContainer();

        if (!box) {
            console.error(LOG, "no chat container found");
            return false;
        }

        box.innerHTML = "";

        messages.forEach((message) => {
            const role = getMessageRole(message);
            const bubble = document.createElement("div");

            bubble.className = [
                "nova-mobile-visible-message-v1",
                "nova-mobile-polished-bubble",
                "nova-mobile-polished-" + role
            ].join(" ");

            bubble.setAttribute("data-session-restore-bridge", "1");
            bubble.setAttribute("data-message-role", role);

            const body = document.createElement("div");
            body.className = "nova-mobile-restored-message-text";
            body.textContent = getMessageText(message);

            bubble.appendChild(body);
            addAttachmentNodes(bubble, message.attachments);

            box.appendChild(bubble);
        });

        box.scrollTop = box.scrollHeight;

        console.log(LOG, "rendered messages", {
            count: messages.length,
            bubbles: box.querySelectorAll("[data-session-restore-bridge]").length
        });

        return true;
    }

    function setActiveSession(sessionId, session) {
        localStorage.setItem("nova_mobile_active_session_id", sessionId);
        localStorage.setItem("nova_active_session_id", sessionId);

window.__NOVA_ACTIVE_SESSION_ID = sessionId;
window.NOVA_ACTIVE_SESSION_ID = sessionId;
window.NovaActiveSessionId = sessionId;

window.NovaMobileActiveSessionId = sessionId;
window.__novaMobileActiveSessionId = sessionId;
window.novaMobileActiveSessionId = sessionId;

        try {
            const url = new URL(window.location.href);
            url.searchParams.set("session_id", sessionId);
            window.history.replaceState({}, "", url.toString());
        } catch (error) {
            console.warn(LOG, "could not update url", error);
        }

        const shortId = sessionId.slice(-6);
        const title = session && session.title ? session.title : "Session";

        document.querySelectorAll(
            "#nova-mobile-session-title, .nova-mobile-session-title, [data-nova-session-title]"
        ).forEach((node) => {
            node.textContent = "Session: " + title + " · " + shortId;
        });
    }

    function closeSessionDrawer() {
        document.querySelectorAll(
            "#nova-mobile-session-drawer, #nova-mobile-sessions-panel, .nova-mobile-session-drawer, .nova-mobile-sessions-panel, [data-nova-sessions-drawer]"
        ).forEach((drawer) => {
            drawer.classList.remove("open", "active", "visible", "is-open", "show");
            drawer.removeAttribute("aria-hidden");
        });
    }

    function extractSessionIdFromElement(element) {
        if (!element) {
            return "";
        }

        const direct =
            element.dataset.sessionId ||
            element.dataset.novaSessionId ||
            element.dataset.id ||
            element.getAttribute("data-session-id") ||
            element.getAttribute("data-nova-session-id") ||
            element.getAttribute("data-id") ||
            "";

        if (/^session_[A-Za-z0-9]+$/.test(direct)) {
            return direct;
        }

        const href = element.getAttribute("href") || "";
        const hrefMatch =
            href.match(/[?&]session_id=(session_[A-Za-z0-9]+)/) ||
            href.match(/\/sessions\/(session_[A-Za-z0-9]+)/);

        if (hrefMatch) {
            return hrefMatch[1];
        }

        const html = element.outerHTML || "";
        const htmlMatch = html.match(/session_[A-Za-z0-9]+/);

        return htmlMatch ? htmlMatch[0] : "";
    }

    function isSessionActionElement(element) {
        const label = text(element.innerText || element.textContent).trim().toLowerCase();
        const action = text(element.dataset.action || element.getAttribute("data-action")).toLowerCase();

if (
    label === "account" ||
    label === "logout" ||
    label.includes("delete") ||
    label.includes("rename") ||
    label.includes("pin") ||
    action.includes("delete") ||
    action.includes("rename") ||
    action.includes("pin") ||
    action === "new-chat"
) {
    return false;
}


    async function restoreSession(sessionId) {
        if (!sessionId) {
            return false;
        }

console.log("[RESTORE CLICK]", sessionId);

        console.log(LOG, "restore requested", sessionId);

        const response = await fetch("/api/sessions/" + encodeURIComponent(sessionId) + "?cb=" + Date.now(), {
            credentials: "same-origin"
        });

        const data = await response.json();

        if (!response.ok || data.ok === false || !data.session) {
            console.error(LOG, "restore failed", data);
            return false;
        }

        const session = data.session;
        const messages = Array.isArray(session.messages) ? session.messages : [];

        setActiveSession(session.id || sessionId, session);
        renderMessages(messages);
        closeSessionDrawer();

        console.log(LOG, "restore complete", {
            sessionId: session.id || sessionId,
            messageCount: messages.length
        });

        return true;
    }

console.log("[BRIDGE DEBUG] reached export");

    window.NovaMobileRestoreSession = {
        restore: restoreSession,
        renderMessages: renderMessages
    };

const startRestore = () => {
    const sessionId = new URLSearchParams(window.location.search).get("session_id");

    console.log(LOG, "startup restore check", {
        sessionId,
        href: window.location.href,
        readyState: document.readyState
    });

    if (!sessionId) {
        return;
    }

    setTimeout(() => {
        restoreSession(sessionId).catch((error) => {
            console.error(LOG, "initial restore failed", error);
        });
    }, 300);
};

if (document.readyState === "complete") {
    startRestore();
} else {
    window.addEventListener("load", startRestore, { once: true });
}

console.log(LOG, "installed");

})();


