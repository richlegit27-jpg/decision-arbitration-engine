// NOVA_MOBILE_COPY_ACTION_FIX_20260702
// Scoped copy-button fix only. No fetch patching. No message rendering. No duplicate answer path.

(function () {
    if (window.__NOVA_MOBILE_COPY_ACTION_FIX_20260702__) {
        return;
    }
    window.__NOVA_MOBILE_COPY_ACTION_FIX_20260702__ = true;

    function textOf(el) {
        return String(el?.innerText || el?.textContent || "").trim();
    }

    function isCopyButton(el) {
        if (!el) {
            return false;
        }

        const label = String(
            el.getAttribute?.("aria-label") ||
            el.getAttribute?.("title") ||
            el.getAttribute?.("data-action") ||
            el.innerText ||
            el.textContent ||
            ""
        ).trim().toLowerCase();

        return label === "copy" ||
            label.includes("copy message") ||
            el.classList?.contains("copy") ||
            el.classList?.contains("copy-button") ||
            el.classList?.contains("nova-copy-button") ||
            el.matches?.("[data-action='copy'], [data-copy], .message-copy, .copy-message");
    }

    function findCopyButton(target) {
        let node = target;
        while (node && node !== document.body) {
            if (isCopyButton(node)) {
                return node;
            }
            node = node.parentElement;
        }
        return null;
    }

    function findMessageBubble(el) {
        return el.closest(
            ".nova-message-assistant, " +
            ".mobile-chat-message.assistant, " +
            ".nova-mobile-polished-assistant, " +
            ".assistant-message, " +
            ".message.assistant"
        );
    }

    function cleanedBubbleText(bubble) {
        if (!bubble) {
            return "";
        }

        const clone = bubble.cloneNode(true);

        clone.querySelectorAll(
            "button, [role='button'], .nova-mobile-message-actions, .message-actions, .bubble-actions, .assistant-actions, .copy, .regen, .regenerate"
        ).forEach(el => el.remove());

        return textOf(clone)
            .replace(/\bCopy\b\s*/gi, "")
            .replace(/\bRegen\b\s*/gi, "")
            .replace(/\bRegenerate\b\s*/gi, "")
            .trim();
    }

    async function copyText(text) {
        if (!text) {
            return false;
        }

        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch {
            const area = document.createElement("textarea");
            area.value = text;
            area.setAttribute("readonly", "readonly");
            area.style.position = "fixed";
            area.style.left = "-9999px";
            area.style.top = "0";
            document.body.appendChild(area);
            area.select();

            let ok = false;
            try {
                ok = document.execCommand("copy");
            } catch {
                ok = false;
            }

            area.remove();
            return ok;
        }
    }

    function flash(button, ok) {
        const old = textOf(button) || "Copy";
        button.dataset.novaCopyOldText = old;
        button.textContent = ok ? "Copied" : "Copy failed";

        setTimeout(() => {
            button.textContent = button.dataset.novaCopyOldText || "Copy";
        }, 900);
    }

    document.addEventListener("click", async function (event) {
        const button = findCopyButton(event.target);
        if (!button) {
            return;
        }

        const bubble = findMessageBubble(button);
        const text = cleanedBubbleText(bubble);

        if (!text) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        const ok = await copyText(text);
        flash(button, ok);
    }, false);

    console.log("[NOVA_MOBILE_COPY_ACTION_FIX_20260702] active");
})();
