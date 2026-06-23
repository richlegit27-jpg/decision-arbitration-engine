/*
NOVA_MOBILE_ASSISTANT_ACTIONS_20260623
Assistant-only Copy + Regen buttons.
Does not attach to user messages.
Does not restore broken top Copy/Export.
Uses only the chat container, not the whole page.
*/

(function () {
    "use strict";

    const FIX_ID = "NOVA_MOBILE_ASSISTANT_ACTIONS_20260623";

    function textOf(value) {
        return String(value || "").replace(/\s+/g, " ").trim();
    }

    function lower(value) {
        return textOf(value).toLowerCase();
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
            document.querySelector(".chat-messages")
        );
    }

    function looksUser(node) {
        if (!node || !node.matches) return false;

        const bag = lower(
            [
                node.className,
                node.getAttribute("data-role"),
                node.getAttribute("data-message-role"),
                node.getAttribute("role"),
                node.getAttribute("aria-label")
            ].join(" ")
        );

        return (
            bag.includes("user") ||
            bag.includes("human") ||
            node.matches(".user, .user-message, .mobile-user-message, .nova-mobile-user-message, [data-role='user'], [data-message-role='user']")
        );
    }

    function looksAssistant(node) {
        if (!node || !node.matches || looksUser(node)) return false;

        const bag = lower(
            [
                node.className,
                node.getAttribute("data-role"),
                node.getAttribute("data-message-role"),
                node.getAttribute("role"),
                node.getAttribute("aria-label")
            ].join(" ")
        );

        if (
            bag.includes("assistant") ||
            bag.includes("bot") ||
            bag.includes("ai") ||
            node.matches(".assistant, .assistant-message, .mobile-assistant-message, .nova-mobile-assistant-message, [data-role='assistant'], [data-message-role='assistant']")
        ) {
            return true;
        }

        return false;
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
            ".nova-mobile-message.assistant"
        ].join(",");

        let nodes = Array.from(root.querySelectorAll(selectors));

        if (!nodes.length) {
            nodes = Array.from(
                root.querySelectorAll(
                    ".message, .mobile-message, .nova-mobile-message, .chat-message, .message-bubble, [class*='message'], [class*='bubble']"
                )
            ).filter(looksAssistant);
        }

        return nodes
            .filter(function (node) {
                return node && node.isConnected && !looksUser(node);
            })
            .slice(-40);
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

    function cleanAssistantText(node) {
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
            .trim();
    }

    function getLastUserPrompt() {
        const root = getChatRoot() || document;

        const userNodes = Array.from(
            root.querySelectorAll(
                ".user, .user-message, .mobile-user-message, .nova-mobile-user-message, [data-role='user'], [data-message-role='user']"
            )
        );

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

    function addActions(node) {
        if (!node || node.dataset.novaAssistantActions === "1") return;
        if (looksUser(node)) return;

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

    function removeDuplicateOldRows(node) {
        const rows = Array.from(node.querySelectorAll(".nova-mobile-message-actions"));

        rows.forEach(function (row) {
            const text = lower(row.innerText || row.textContent || "");

            if (text.includes("copy") || text.includes("regen")) {
                row.remove();
            }
        });
    }

    function scan() {
        findAssistantMessages().forEach(function (node) {
            removeDuplicateOldRows(node);
            addActions(node);
        });
    }

    function scheduleScan() {
        window.clearTimeout(window.__novaAssistantActionsTimer);
        window.__novaAssistantActionsTimer = window.setTimeout(scan, 80);
    }

    function boot() {
        scan();

        const root = getChatRoot();

        if (root && !window.__novaAssistantActionsObserver) {
            window.__novaAssistantActionsObserver = new MutationObserver(scheduleScan);
            window.__novaAssistantActionsObserver.observe(root, {
                childList: true,
                subtree: true
            });
        }

        [150, 500, 1200].forEach(function (ms) {
            window.setTimeout(scan, ms);
        });

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
