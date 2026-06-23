/*
NOVA_MOBILE_ASSISTANT_ACTIONS_RETRY_20260623
Assistant-only Copy + Regen buttons.
Bounded retry scanner so buttons appear after chat render.
No old laggy observer pile.
*/

(function () {
    "use strict";

    const FIX_ID = "NOVA_MOBILE_ASSISTANT_ACTIONS_RETRY_20260623";

    function textOf(value) {
        return String(value || "").replace(/\s+/g, " ").trim();
    }

    function lower(value) {
        return textOf(value).toLowerCase();
    }

    function toast(message) {
        if (typeof window.showToast === "function") {
            window.showToast(message);
            return;
        }

        if (window.NovaMobileUI && typeof window.NovaMobileUI.showToast === "function") {
            window.NovaMobileUI.showToast(message);
            return;
        }

        console.log("[" + FIX_ID + "] " + message);
    }

    function getChatRoot() {
        return (
            document.getElementById("mobileChatMessages") ||
            document.getElementById("nova-mobile-messages") ||
            document.getElementById("messagesContainer") ||
            document.getElementById("messages-container") ||
            document.querySelector("[data-mobile-chat-messages]") ||
            document.querySelector(".mobile-chat-messages") ||
            document.querySelector(".mobile-chat-container") ||
            document.querySelector(".chat-messages") ||
            document.querySelector("main")
        );
    }

    function attrBag(node) {
        if (!node) return "";

        return lower([
            node.className || "",
            node.getAttribute && node.getAttribute("data-role") || "",
            node.getAttribute && node.getAttribute("data-message-role") || "",
            node.getAttribute && node.getAttribute("role") || "",
            node.getAttribute && node.getAttribute("aria-label") || ""
        ].join(" "));
    }

    function looksUser(node) {
        if (!node || !node.matches) return false;

        const bag = attrBag(node);

        return (
            bag.includes("user") ||
            bag.includes("human") ||
            node.matches(".user, .user-message, .mobile-user-message, .nova-mobile-user-message, [data-role='user'], [data-message-role='user']")
        );
    }

    function looksAssistant(node) {
        if (!node || !node.matches || looksUser(node)) return false;

        const bag = attrBag(node);

        return (
            bag.includes("assistant") ||
            bag.includes("bot") ||
            bag.includes("ai") ||
            node.matches(".assistant, .assistant-message, .mobile-assistant-message, .nova-mobile-assistant-message, [data-role='assistant'], [data-message-role='assistant']")
        );
    }

    function findAssistantMessages() {
        const root = getChatRoot();

        if (!root) return [];

        const selectors = [
            ".assistant",
            ".assistant-message",
            ".mobile-assistant-message",
            ".nova-mobile-assistant-message",
            "[data-role='assistant']",
            "[data-message-role='assistant']",
            ".message.assistant",
            ".mobile-message.assistant",
            ".nova-mobile-message.assistant",
            "[class*='assistant']"
        ].join(",");

        let nodes = Array.from(root.querySelectorAll(selectors));

        nodes = nodes.filter(function (node) {
            if (!node || !node.isConnected) return false;
            if (looksUser(node)) return false;
            if (node.closest("#nova-mobile-tools-panel, #nova-mobile-artifacts-panel, #nova-mobile-execution-panel, #nova-mobile-memory-panel")) return false;

            const value = cleanAssistantText(node);

            return value && value.length > 1;
        });

        return Array.from(new Set(nodes)).slice(-40);
    }

    async function copyText(value) {
        value = String(value || "").trim();

        if (!value) {
            toast("Nothing to copy.");
            return;
        }

        if (typeof window.copyText === "function") {
            window.copyText(value);
            return;
        }

        if (window.NovaMobileUI && typeof window.NovaMobileUI.copyText === "function") {
            window.NovaMobileUI.copyText(value);
            return;
        }

        try {
            await navigator.clipboard.writeText(value);
            toast("Copied.");
        } catch (_) {
            const area = document.createElement("textarea");
            area.value = value;
            area.style.position = "fixed";
            area.style.left = "-9999px";

            document.body.appendChild(area);
            area.focus();
            area.select();

            try {
                document.execCommand("copy");
                toast("Copied.");
            } catch (error) {
                toast("Copy failed.");
            }

            area.remove();
        }
    }

    function cleanAssistantText(node) {
        if (!node) return "";

        const clone = node.cloneNode(true);

        clone.querySelectorAll([
            ".nova-mobile-assistant-actions",
            ".nova-mobile-message-actions",
            ".nova-code-copy-btn",
            ".nova-mobile-copy-message",
            ".nova-mobile-regenerate-message",
            "[data-mobile-assistant-action]",
            "button"
        ].join(",")).forEach(function (el) {
            el.remove();
        });

        return String(clone.innerText || clone.textContent || "")
            .replace(/\n{3,}/g, "\n\n")
            .replace(/\bCopy\s+Regen\b/gi, "")
            .trim();
    }

    function getLastUserPrompt() {
        const root = getChatRoot() || document;

        const userNodes = Array.from(
            root.querySelectorAll(
                ".user, .user-message, .mobile-user-message, .nova-mobile-user-message, [data-role='user'], [data-message-role='user'], [class*='user']"
            )
        ).filter(function (node) {
            return !node.closest("#nova-mobile-tools-panel, #nova-mobile-artifacts-panel, #nova-mobile-execution-panel, #nova-mobile-memory-panel");
        });

        const last = userNodes[userNodes.length - 1];

        if (last) {
            return String(last.innerText || last.textContent || "").trim();
        }

        return "";
    }

    function setInputValue(value) {
        const input =
            document.getElementById("nova-mobile-input") ||
            document.getElementById("input") ||
            document.querySelector("textarea, input[type='text']");

        if (!input) return false;

        input.value = value;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        return true;
    }

    function clickSend() {
        const send =
            document.getElementById("nova-mobile-send") ||
            document.getElementById("sendBtn") ||
            document.querySelector("[data-action='send']") ||
            document.querySelector("[data-send]") ||
            document.querySelector(".nova-mobile-send") ||
            document.querySelector(".mobile-send");

        if (!send) return false;

        send.click();
        return true;
    }

    function regenerateLast() {
        if (typeof window.NovaMobileRegenerateLast === "function") {
            window.NovaMobileRegenerateLast();
            return;
        }

        const prompt = getLastUserPrompt();

        if (!prompt) {
            toast("No user prompt found.");
            return;
        }

        if (typeof window.NovaMobileSendText === "function") {
            window.NovaMobileSendText(prompt);
            toast("Regenerating...");
            return;
        }

        if (setInputValue(prompt) && clickSend()) {
            toast("Regenerating...");
            return;
        }

        toast("Could not regenerate.");
    }

    function hasActionRow(node) {
        return !!(node && node.querySelector && node.querySelector(".nova-mobile-assistant-actions"));
    }

    function removeOldRows(node) {
        if (!node || !node.querySelectorAll) return;

        node.querySelectorAll(".nova-mobile-message-actions").forEach(function (row) {
            const text = lower(row.innerText || row.textContent || "");

            if (text.includes("copy") || text.includes("regen")) {
                row.remove();
            }
        });
    }

    function addActions(node) {
        if (!node || looksUser(node)) return;

        removeOldRows(node);

        if (hasActionRow(node)) {
            return;
        }

        node.dataset.novaAssistantActions = "1";

        if (getComputedStyle(node).position === "static") {
            node.style.position = "relative";
        }

        const row = document.createElement("div");
        row.className = "nova-mobile-assistant-actions";

        const copy = document.createElement("button");
        copy.type = "button";
        copy.className = "nova-mobile-assistant-action";
        copy.setAttribute("data-mobile-assistant-action", "copy");
        copy.textContent = "Copy";

        copy.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            copyText(cleanAssistantText(node));
            return false;
        }, true);

        const regen = document.createElement("button");
        regen.type = "button";
        regen.className = "nova-mobile-assistant-action";
        regen.setAttribute("data-mobile-assistant-action", "regen");
        regen.textContent = "Regen";

        regen.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            regenerateLast();
            return false;
        }, true);

        row.appendChild(copy);
        row.appendChild(regen);
        node.insertBefore(row, node.firstChild);
    }

    function scan() {
        const messages = findAssistantMessages();

        messages.forEach(addActions);

        return messages.length;
    }

    function scheduleScan() {
        window.clearTimeout(window.__novaAssistantActionsTimer);
        window.__novaAssistantActionsTimer = window.setTimeout(scan, 90);
    }

    function installObserver() {
        const root = getChatRoot();

        if (!root) return false;

        if (window.__novaAssistantActionsObserver) {
            window.__novaAssistantActionsObserver.disconnect();
        }

        window.__novaAssistantActionsObserver = new MutationObserver(scheduleScan);
        window.__novaAssistantActionsObserver.observe(root, {
            childList: true,
            subtree: true
        });

        return true;
    }

    function boot() {
        scan();
        installObserver();

        let tries = 0;

        const interval = window.setInterval(function () {
            tries += 1;

            scan();
            installObserver();

            if (tries >= 30) {
                window.clearInterval(interval);
            }
        }, 350);

        console.log("[" + FIX_ID + "] ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    window.NovaMobileAssistantActions = {
        scan: scan,
        regen: regenerateLast
    };
})();
