/*
NOVA_MOBILE_SUMMARY_HORSEMEN_PANEL_20260623
Clean mobile Summary panel + 4 Horsemen buttons.
Adds feature back without floating debug-box weirdness.
*/

(function () {
    "use strict";

    const FIX_ID = "NOVA_MOBILE_SUMMARY_HORSEMEN_PANEL_20260623";

    function $(id) {
        return document.getElementById(id);
    }

    function text(value) {
        return String(value || "").trim();
    }

    function getSessionId() {
        return (
            window.NOVA_ACTIVE_SESSION_ID ||
            window.NovaActiveSessionId ||
            localStorage.getItem("nova_mobile_active_session_id") ||
            localStorage.getItem("nova_active_session_id") ||
            localStorage.getItem("active_session_id") ||
            ""
        );
    }

    function getMessagesRoot() {
        return (
            $("mobileChatMessages") ||
            $("nova-mobile-messages") ||
            $("messagesContainer") ||
            $("messages-container") ||
            document.querySelector("[data-mobile-chat-messages]") ||
            document.querySelector(".mobile-chat-messages") ||
            document.querySelector(".chat-messages")
        );
    }

    function countChars() {
        const root = getMessagesRoot();
        if (!root) return 0;

        return text(root.innerText || root.textContent || "").length;
    }

    function latestAssistantText() {
        const root = getMessagesRoot();
        if (!root) return "";

        const nodes = Array.from(root.querySelectorAll(
            ".assistant, .assistant-message, .mobile-assistant-message, .nova-mobile-assistant-message, [data-role='assistant'], [data-message-role='assistant'], [class*='assistant']"
        ));

        const last = nodes.reverse().find(function (node) {
            const value = text(node.innerText || node.textContent || "");
            return value && !value.toLowerCase().includes("copy regen");
        });

        return last ? text(last.innerText || last.textContent || "") : "";
    }

    function ensurePanel() {
        let panel = $("nova-mobile-summary-horsemen");

        if (panel) return panel;

        const composer =
            $("nova-mobile-composer") ||
            document.querySelector(".nova-mobile-composer") ||
            document.querySelector(".mobile-composer") ||
            document.querySelector("footer");

        panel = document.createElement("section");
        panel.id = "nova-mobile-summary-horsemen";
        panel.className = "nova-mobile-summary-horsemen";
        panel.innerHTML = [
            '<div class="nova-mobile-summary-head">',
                '<div>',
                    '<div class="nova-mobile-summary-title">Nova Summary</div>',
                    '<div class="nova-mobile-summary-sub" id="nova-mobile-summary-sub">ready</div>',
                '</div>',
                '<button type="button" class="nova-mobile-summary-toggle" id="nova-mobile-summary-toggle">Hide</button>',
            '</div>',
            '<div class="nova-mobile-summary-body" id="nova-mobile-summary-body">',
                '<div class="nova-mobile-summary-line"><span>Status</span><strong id="nova-mobile-summary-status">ready</strong></div>',
                '<div class="nova-mobile-summary-line"><span>Summary chars</span><strong id="nova-mobile-summary-chars">0</strong></div>',
                '<div class="nova-mobile-summary-line"><span>Session</span><strong id="nova-mobile-summary-session">none</strong></div>',
                '<div class="nova-mobile-horsemen-row">',
                    '<button type="button" data-horseman="summary">Summary</button>',
                    '<button type="button" data-horseman="memory">Memory</button>',
                    '<button type="button" data-horseman="artifacts">Artifacts</button>',
                    '<button type="button" data-horseman="sessions">Sessions</button>',
                '</div>',
            '</div>'
        ].join("");

        if (composer && composer.parentNode) {
            composer.parentNode.insertBefore(panel, composer);
        } else {
            document.body.appendChild(panel);
        }

        return panel;
    }

    function setStatus(value) {
        const el = $("nova-mobile-summary-status");
        if (el) el.textContent = value;
    }

    function updatePanel() {
        ensurePanel();

        const sid = getSessionId();
        const chars = countChars();

        const sub = $("nova-mobile-summary-sub");
        const charEl = $("nova-mobile-summary-chars");
        const sidEl = $("nova-mobile-summary-session");

        if (sub) sub.textContent = chars ? "tracking current chat" : "ready";
        if (charEl) charEl.textContent = String(chars);
        if (sidEl) sidEl.textContent = sid ? sid.slice(-8) : "none";

        setStatus("ready");
    }

    function clickKnown(selectors) {
        for (const selector of selectors) {
            const el = document.querySelector(selector);
            if (el) {
                el.click();
                return true;
            }
        }

        return false;
    }

    function openSummary() {
        updatePanel();

        const value = latestAssistantText();

        if (value) {
            window.__NovaMobileLastSummaryText = value;
        }

        setStatus(value ? "summary captured" : "no summary yet");
    }

    function openMemory() {
        if (clickKnown([
            "#nova-mobile-memory-btn",
            "#mobileMemoryBtn",
            "[data-panel='memory']",
            "[data-action='memory']",
            ".nova-mobile-memory-button"
        ])) {
            setStatus("memory opened");
            return;
        }

        setStatus("memory ready");
    }

    function openArtifacts() {
        if (clickKnown([
            "#nova-mobile-artifacts-btn",
            "#mobileArtifactsBtn",
            "[data-panel='artifacts']",
            "[data-action='artifacts']",
            ".nova-mobile-artifacts-button"
        ])) {
            setStatus("artifacts opened");
            return;
        }

        setStatus("artifacts ready");
    }

    function openSessions() {
        if (clickKnown([
            "#nova-mobile-sessions-btn",
            "#mobileSessionsBtn",
            "[data-panel='sessions']",
            "[data-action='sessions']",
            ".nova-mobile-sessions-button",
            ".session-toggle"
        ])) {
            setStatus("sessions opened");
            return;
        }

        setStatus("sessions ready");
    }

    function bindPanel() {
        const panel = ensurePanel();

        const toggle = $("nova-mobile-summary-toggle");
        const body = $("nova-mobile-summary-body");

        if (toggle && body && !toggle.dataset.novaBound) {
            toggle.dataset.novaBound = "1";
            toggle.addEventListener("click", function () {
                const hidden = body.classList.toggle("is-hidden");
                toggle.textContent = hidden ? "Show" : "Hide";
                panel.classList.toggle("is-collapsed", hidden);
            });
        }

        panel.querySelectorAll("[data-horseman]").forEach(function (button) {
            if (button.dataset.novaBound) return;
            button.dataset.novaBound = "1";

            button.addEventListener("click", function () {
                const type = button.getAttribute("data-horseman");

                if (type === "summary") openSummary();
                if (type === "memory") openMemory();
                if (type === "artifacts") openArtifacts();
                if (type === "sessions") openSessions();

                updatePanel();
            });
        });
    }

    function boot() {
        bindPanel();
        updatePanel();

        window.setInterval(updatePanel, 1500);

        const root = getMessagesRoot();
        if (root && !window.__novaMobileSummaryHorsemenObserver) {
            window.__novaMobileSummaryHorsemenObserver = new MutationObserver(updatePanel);
            window.__novaMobileSummaryHorsemenObserver.observe(root, {
                childList: true,
                subtree: true,
                characterData: true
            });
        }

        console.log("[" + FIX_ID + "] ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    window.NovaMobileSummaryHorsemen = {
        boot: boot,
        update: updatePanel,
        openSummary: openSummary
    };
})();
