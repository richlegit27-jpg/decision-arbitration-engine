/*
NOVA_MOBILE_EXECUTION_PANEL_20260607
Adds a lightweight frontend execution control panel.
Does not modify attachment flow.
*/
(function () {
    "use strict";

    if (window.__novaMobileExecutionPanelInstalled) {
        return;
    }

    window.__novaMobileExecutionPanelInstalled = true;

    function $(id) {
        return document.getElementById(id);
    }

    function getSessionId() {
        try {
            if (window.NovaMobileBridge && typeof window.NovaMobileBridge.getSessionId === "function") {
                return window.NovaMobileBridge.getSessionId();
            }
        } catch (_) {}

        try {
            return localStorage.getItem("nova_mobile_active_session_id") || "";
        } catch (_) {
            return "";
        }
    }

    function getInput() {
        return $("nova-mobile-input") || document.querySelector("textarea, input[type='text']");
    }

    function clickSend() {
        const send =
            $("nova-mobile-send") ||
            document.querySelector("[data-action='send']") ||
            document.querySelector(".nova-mobile-send") ||
            document.querySelector(".mobile-send");

        if (send) {
            send.click();
            return true;
        }

        return false;
    }

    function sendExecutionCommand(command) {
        const input = getInput();

        if (input) {
            input.value = command;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            clickSend();
            updateExecutionPanel({
                status: "sent",
                step: command
            });
            return;
        }

        sendCommandDirect(command);
    }

    async function sendCommandDirect(command) {
        updateExecutionPanel({
            status: "sending",
            step: command
        });

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_text: command,
                    session_id: getSessionId(),
                    attachments: []
                })
            });

            const data = await response.json();

            updateExecutionPanel({
                status: data && data.ok ? "complete" : "error",
                step: command,
                detail: data && data.assistant_message ? (data.assistant_message.text || "") : ""
            });
        } catch (error) {
            updateExecutionPanel({
                status: "error",
                step: command,
                detail: String(error && error.message ? error.message : error)
            });
        }
    }

    function ensurePanel() {
        let panel = $("nova-mobile-execution-panel");

        if (panel) {
            return panel;
        }

        panel = document.createElement("section");
        panel.id = "nova-mobile-execution-panel";
        panel.className = "nova-mobile-execution-panel";
        panel.innerHTML = [
            '<div class="nova-exec-head">',
            '  <div>',
            '    <div class="nova-exec-label">Execution</div>',
            '    <div id="nova-exec-status" class="nova-exec-status">idle</div>',
            '  </div>',
            '  <button id="nova-exec-collapse" type="button" class="nova-exec-mini-btn">−</button>',
            '</div>',
            '<div id="nova-exec-body" class="nova-exec-body">',
            '  <div class="nova-exec-row">',
            '    <span class="nova-exec-key">Step</span>',
            '    <span id="nova-exec-step" class="nova-exec-value">No active step</span>',
            '  </div>',
            '  <div id="nova-exec-detail" class="nova-exec-detail"></div>',
            '  <div class="nova-exec-actions">',
            '    <button type="button" data-exec-command="run step">Run Step</button>',
            '    <button type="button" data-exec-command="continue">Continue</button>',
            '    <button type="button" data-exec-command="run all">Run All</button>',
            '    <button type="button" data-exec-command="stop">Stop</button>',
            '  </div>',
            '</div>'
        ].join("");

        const composer =
            $("nova-mobile-composer") ||
            document.querySelector(".nova-mobile-composer") ||
            document.querySelector(".mobile-composer");

        if (composer && composer.parentNode) {
            composer.parentNode.insertBefore(panel, composer);
        } else {
            document.body.appendChild(panel);
        }

        panel.querySelectorAll("[data-exec-command]").forEach(function (button) {
            button.addEventListener("click", function () {
                const command = button.getAttribute("data-exec-command") || "";
                if (command) {
                    sendExecutionCommand(command);
                }
            });
        });

        const collapse = $("nova-exec-collapse");
        const body = $("nova-exec-body");

        if (collapse && body) {
            collapse.addEventListener("click", function () {
                const collapsed = panel.classList.toggle("is-collapsed");
                collapse.textContent = collapsed ? "+" : "−";
            });
        }

        return panel;
    }

    function updateExecutionPanel(state) {
        ensurePanel();

        const status = $("nova-exec-status");
        const step = $("nova-exec-step");
        const detail = $("nova-exec-detail");

        if (status) {
            status.textContent = state && state.status ? state.status : "idle";
        }

        if (step) {
            step.textContent = state && state.step ? state.step : "No active step";
        }

        if (detail) {
            detail.textContent = state && state.detail ? String(state.detail).slice(0, 240) : "";
        }
    }

    function boot() {
        ensurePanel();
        updateExecutionPanel({
            status: "idle",
            step: "Ready"
        });

        console.log("[Nova Mobile Execution Panel] ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    window.NovaMobileExecutionPanel = {
        ensurePanel: ensurePanel,
        update: updateExecutionPanel,
        send: sendExecutionCommand
    };
})();
