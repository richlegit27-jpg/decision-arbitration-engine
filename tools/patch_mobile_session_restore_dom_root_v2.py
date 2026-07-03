from pathlib import Path

path = Path("static/js/mobile/nova-mobile-session-restore-lock.js")
text = path.read_text(encoding="utf-8")

start = text.index("    function findChatRoot() {")
end = text.index("    function renderMessage(message) {", start)

new_find = r'''    function isVisibleNode(node) {
        if (!node || !node.getBoundingClientRect) {
            return false;
        }

        const rect = node.getBoundingClientRect();
        const style = window.getComputedStyle ? window.getComputedStyle(node) : null;

        if (style && (style.display === "none" || style.visibility === "hidden")) {
            return false;
        }

        return rect.width > 40 && rect.height > 40;
    }

    function isBadChatRootCandidate(node) {
        if (!node) {
            return true;
        }

        const raw = (
            String(node.id || "") + " " +
            String(node.className || "") + " " +
            String(node.getAttribute("role") || "") + " " +
            String(node.getAttribute("aria-label") || "") + " " +
            String(node.getAttribute("data-action") || "")
        ).toLowerCase();

        return (
            raw.includes("composer") ||
            raw.includes("input") ||
            raw.includes("textarea") ||
            raw.includes("prompt") ||
            raw.includes("button") ||
            raw.includes("toolbar") ||
            raw.includes("drawer") ||
            raw.includes("session-list") ||
            raw.includes("sessions-list") ||
            raw.includes("auth") ||
            raw.includes("panel") ||
            raw.includes("menu") ||
            raw.includes("nav") ||
            raw.includes("header") ||
            raw.includes("footer") ||
            raw.includes("modal")
        );
    }

    function scoreChatRootCandidate(node) {
        if (!node || isBadChatRootCandidate(node) || !isVisibleNode(node)) {
            return -9999;
        }

        const raw = (
            String(node.id || "") + " " +
            String(node.className || "") + " " +
            String(node.getAttribute("role") || "") + " " +
            String(node.getAttribute("aria-live") || "") + " " +
            String(node.getAttribute("data-nova-chat-messages") || "") + " " +
            String(node.getAttribute("data-chat-messages") || "") + " " +
            String(node.getAttribute("data-messages") || "")
        ).toLowerCase();

        let score = 0;

        if (raw.includes("message")) score += 80;
        if (raw.includes("messages")) score += 90;
        if (raw.includes("chat")) score += 70;
        if (raw.includes("conversation")) score += 70;
        if (raw.includes("thread")) score += 65;
        if (raw.includes("feed")) score += 55;
        if (raw.includes("history")) score += 55;
        if (raw.includes("log")) score += 45;
        if (raw.includes("stream")) score += 45;
        if (raw.includes("nova")) score += 20;
        if (raw.includes("mobile")) score += 20;
        if (raw.includes("aria-live")) score += 35;
        if (node.getAttribute("role") === "log") score += 90;

        try {
            const rect = node.getBoundingClientRect();
            if (rect.height > 120) score += 20;
            if (rect.height > 250) score += 25;
            if (node.scrollHeight > rect.height + 20) score += 20;
        } catch (_) {}

        const messageChildren = node.querySelectorAll(
            ".message, .nova-message, .nova-mobile-message, .chat-message, .assistant, .user, [data-role], [data-message-id], [data-nova-message]"
        ).length;

        score += Math.min(messageChildren * 20, 160);

        return score;
    }

    function createFallbackChatRoot() {
        let root = document.getElementById("nova-mobile-restored-session-messages");

        if (root) {
            return root;
        }

        root = document.createElement("div");
        root.id = "nova-mobile-restored-session-messages";
        root.className = "nova-mobile-restored-session-messages nova-mobile-messages chat-messages";
        root.setAttribute("data-nova-chat-messages", "true");
        root.setAttribute("data-session-restore-fallback", "true");
        root.style.cssText = [
            "box-sizing:border-box",
            "width:100%",
            "min-height:45vh",
            "max-height:calc(100vh - 170px)",
            "overflow-y:auto",
            "-webkit-overflow-scrolling:touch",
            "padding:12px",
            "display:flex",
            "flex-direction:column",
            "gap:10px"
        ].join(";");

        const composer = document.querySelector(
            "#composer, #mobile-composer, #nova-composer, #nova-mobile-composer, .composer, .mobile-composer, .nova-composer, .nova-mobile-composer, form textarea, textarea"
        );

        const anchor = composer && composer.closest
            ? composer.closest("form, footer, .composer, .mobile-composer, .nova-composer, .nova-mobile-composer")
            : null;

        if (anchor && anchor.parentNode) {
            anchor.parentNode.insertBefore(root, anchor);
        } else {
            const main = document.querySelector("main") || document.body;
            main.appendChild(root);
        }

        log("created fallback chat root", root);
        return root;
    }

    function findChatRoot() {
        const selectors = [
            "[data-nova-chat-messages]",
            "[data-chat-messages]",
            "[data-messages]",
            "[data-nova-messages]",
            "[data-chat-root]",
            "[data-thread]",
            "[role='log']",
            "[aria-live='polite']",
            "[aria-live='assertive']",

            "#nova-mobile-messages",
            "#nova-chat-messages",
            "#mobile-chat-messages",
            "#chat-messages",
            "#messages",
            "#message-list",
            "#messages-list",
            "#messageList",
            "#chat-history",
            "#chat-log",
            "#chat-feed",
            "#conversation",
            "#conversation-feed",
            "#conversation-log",
            "#thread",
            "#chat-thread",
            "#nova-thread",
            "#nova-chat-thread",
            "#nova-chat-feed",
            "#mobile-chat-feed",
            "#nova-mobile-chat-feed",
            "#nova-chat-window",
            "#mobile-chat-window",
            "#nova-mobile-chat",
            "#nova-mobile-chat-area",
            "#mobile-chat",
            "#mobile-chat-area",

            ".nova-mobile-messages",
            ".nova-chat-messages",
            ".mobile-chat-messages",
            ".chat-messages",
            ".messages",
            ".message-list",
            ".messages-list",
            ".chat-history",
            ".chat-log",
            ".chat-feed",
            ".conversation",
            ".conversation-feed",
            ".conversation-log",
            ".thread",
            ".chat-thread",
            ".nova-thread",
            ".nova-chat-thread",
            ".nova-chat-feed",
            ".mobile-chat-feed",
            ".nova-mobile-chat-feed",
            ".nova-chat-window",
            ".mobile-chat-window",
            ".nova-mobile-chat",
            ".nova-mobile-chat-area",
            ".mobile-chat",
            ".mobile-chat-area"
        ];

        for (const selector of selectors) {
            const nodes = Array.from(document.querySelectorAll(selector));
            const best = nodes
                .map(function (node) {
                    return {
                        node: node,
                        score: scoreChatRootCandidate(node)
                    };
                })
                .filter(function (item) {
                    return item.score > 0;
                })
                .sort(function (a, b) {
                    return b.score - a.score;
                })[0];

            if (best && best.node) {
                best.node.setAttribute("data-nova-chat-messages", "true");
                log("found chat root by selector", selector, "score", best.score, best.node);
                return best.node;
            }
        }

        const broadNodes = Array.from(document.querySelectorAll("main, section, article, div, ul, ol"));
        const bestBroad = broadNodes
            .map(function (node) {
                return {
                    node: node,
                    score: scoreChatRootCandidate(node)
                };
            })
            .filter(function (item) {
                return item.score > 40;
            })
            .sort(function (a, b) {
                return b.score - a.score;
            })[0];

        if (bestBroad && bestBroad.node) {
            bestBroad.node.setAttribute("data-nova-chat-messages", "true");
            log("found chat root by DOM scoring", "score", bestBroad.score, bestBroad.node);
            return bestBroad.node;
        }

        return createFallbackChatRoot();
    }

'''

text = text[:start] + new_find + text[end:]

text = text.replace(
    'const VERSION = "session-restore-lock-20260702";',
    'const VERSION = "session-restore-lock-20260702-dom-root-v2";'
)

if "SESSION_RESTORE_DOM_ROOT_V2" not in text:
    text = text.replace(
        'window.__NOVA_MOBILE_SESSION_RESTORE_LOCK_20260702__ = true;',
        'window.__NOVA_MOBILE_SESSION_RESTORE_LOCK_20260702__ = true;\n    window.__NOVA_MOBILE_SESSION_RESTORE_DOM_ROOT_V2__ = true;'
    )

path.write_text(text, encoding="utf-8")
print("patched", path)
