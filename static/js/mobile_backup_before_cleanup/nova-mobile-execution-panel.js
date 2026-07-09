/*
NOVA_MOBILE_EXECUTION_PANEL_EXISTING_IDS_20260623
Uses the existing template panel:
- nova-mobile-execution-panel
- nova-mobile-execution-status
- nova-mobile-execution-progress-bar
- nova-mobile-execution-badge
- nova-mobile-execution-last-update

No heavy backend/session scans.
No global page-wide search.
*/

(function () {
    "use strict";

    function $(id) {
        return document.getElementById(id);
    }

    function clean(value) {
        return String(value || "")
            .replace(/\r/g, "")
            .replace(/[ \t]+/g, " ")
            .trim();
    }


    const EXECUTION_CACHE_KEY = "nova_mobile_latest_execution_state";

    function saveCachedExecution(execution) {
        if (!execution) return;

        try {
            localStorage.setItem(
                EXECUTION_CACHE_KEY,
                JSON.stringify({
                    saved_at: new Date().toISOString(),
                    execution: execution
                })
            );
        } catch (_) {}
    }

    function loadCachedExecution() {
        try {
            const raw = localStorage.getItem(EXECUTION_CACHE_KEY);
            if (!raw) return null;

            const parsed = JSON.parse(raw);
            return parsed && parsed.execution ? parsed.execution : null;
        } catch (_) {
            return null;
        }
    }

    function short(value, maxLength) {
        value = clean(value);

        if (value.length <= maxLength) {
            return value;
        }

        return value.slice(0, maxLength) + "?";
    }

    function getPanel() {
        return $("nova-mobile-execution-panel");
    }

    function getStatusEl() {
        return $("nova-mobile-execution-status");
    }

    function getProgressBar() {
        return $("nova-mobile-execution-progress-bar");
    }

    function getBadge() {
        return $("nova-mobile-execution-badge");
    }

    function getLastUpdate() {
        return $("nova-mobile-execution-last-update");
    }

    function setPanelVisible(visible) {
        const panel = getPanel();

        if (!panel) {
            return;
        }

        if (visible) {
            panel.classList.remove("hidden");
            panel.setAttribute("aria-hidden", "false");
            panel.style.cssText = [
                "display:flex !important",
                "position:fixed !important",
                "left:10px !important",
                "right:10px !important",
                "top:90px !important",
                "z-index:999999 !important",
                "flex-direction:column !important",
                "gap:10px !important",
                "padding:14px !important",
                "background:#111827 !important",
                "border:1px solid rgba(255,255,255,.18) !important",
                "border-radius:18px !important",
                "max-height:calc(100vh - 120px) !important",
                "overflow:auto !important",
                "box-shadow:0 18px 50px rgba(0,0,0,.42) !important"
            ].join(";");
        } else {
            panel.classList.add("hidden");
            panel.setAttribute("aria-hidden", "true");
            panel.style.cssText = "display:none !important;";
        }
    }

    function closeToolsPanel() {
        const toolsPanel = $("nova-mobile-tools-panel");

        if (!toolsPanel) {
            return;
        }

        toolsPanel.classList.add("hidden");
        toolsPanel.style.cssText = "display:none !important;";
    }

    function renderIdle(message) {
        const statusEl = getStatusEl();
        const progressBar = getProgressBar();
        const badge = getBadge();
        const lastUpdate = getLastUpdate();

        if (statusEl) {
            statusEl.textContent = message || "No active execution loaded.";
        }

        if (progressBar) {
            progressBar.style.width = "0%";
        }

        if (badge) {
            badge.textContent = "idle";
            badge.dataset.status = "idle";
        }

        if (lastUpdate) {
            lastUpdate.textContent = "Last update: " + new Date().toLocaleTimeString();
        }
    }

    function renderExecution(execution) {
        const statusEl = getStatusEl();
        const progressBar = getProgressBar();
        const badge = getBadge();
        const lastUpdate = getLastUpdate();

        if (!statusEl) {
            return;
        }

        if (!execution) {
            renderIdle("No active execution loaded. Start one with: auto-plan make a simple todo app");
            return;
        }

        const status = execution.status || "active";
        const goal = execution.goal || execution.original_user_text || execution.title || "Execution mission";
        const currentStep = execution.current_step || execution.step || execution.current || "Waiting for next step";

        const currentIndex =
            typeof execution.current_index === "number"
                ? execution.current_index + 1
                : typeof execution.currentIndex === "number"
                    ? execution.currentIndex
                    : execution.current_index
                        ? Number(execution.current_index) + 1
                        : execution.currentIndex
                            ? Number(execution.currentIndex)
                            : 1;

        const totalSteps =
            Array.isArray(execution.steps)
                ? execution.steps.length
                : execution.total_steps || execution.totalSteps || 3;

        const safeCurrent = Number.isFinite(Number(currentIndex)) ? Number(currentIndex) : 1;
        const safeTotal = Number.isFinite(Number(totalSteps)) && Number(totalSteps) > 0 ? Number(totalSteps) : 3;

        saveCachedExecution({
            status: status,
            goal: goal,
            current_index: safeCurrent - 1,
            total_steps: safeTotal,
            current_step: currentStep
        });

        const progress = Math.max(
            0,
            Math.min(100, Math.round((safeCurrent / safeTotal) * 100))
        );

        statusEl.innerHTML = "";

        [
            ["Status", status],
            ["Goal", short(goal, 160)],
            ["Step " + safeCurrent + "/" + safeTotal, short(currentStep, 220)]
        ].forEach(function (row) {
            const line = document.createElement("div");
            line.className = "nova-mobile-execution-status-line";

            const label = document.createElement("span");
            label.className = "nova-mobile-execution-status-label";
            label.textContent = row[0] + ": ";

            const value = document.createElement("span");
            value.className = "nova-mobile-execution-status-value";
            value.textContent = row[1];

            line.appendChild(label);
            line.appendChild(value);
            statusEl.appendChild(line);
        });

        if (progressBar) {
            progressBar.style.width = progress + "%";
        }

        if (badge) {
            badge.textContent = status;
            badge.dataset.status = status;
        }

        if (lastUpdate) {
            lastUpdate.textContent = "Last update: " + new Date().toLocaleTimeString();
        }
    }

    function latestMatch(text, regex) {
        const matches = Array.from(String(text || "").matchAll(regex));

        if (!matches.length) {
            return null;
        }

        return matches[matches.length - 1];
    }

    function parseExecutionText(text) {
        text = String(text || "").replace(/\r/g, "");

        const mission = latestMatch(text, /Execution mission started:\s*([^\n]+)/gi);
        const step = latestMatch(text, /Step\s+(\d+)\s*\/\s*(\d+)\s*:\s*([^\n]+)/gi);
        const plan = latestMatch(text, /Execution plan created\.?\s*([^\n]*)/gi);

        if (!mission && !step && !plan) {
            return null;
        }

        return {
            status: "active",
            goal: mission ? clean(mission[1]) : "Execution plan",
            current_index: step ? Math.max(0, parseInt(step[1], 10) - 1) : 0,
            total_steps: step ? parseInt(step[2], 10) : 3,
            current_step: step ? clean(step[3]) : "Waiting for next step"
        };
    }

    function executionFromResponse(data) {
        if (!data || typeof data !== "object") {
            return null;
        }

        const direct =
            data.execution_state ||
            data.execution ||
            data.assistant_message?.meta?.execution_state ||
            data.assistant_message?.execution_state ||
            data.meta?.execution_state ||
            null;

        if (direct && typeof direct === "object") {
            return direct;
        }

        const text =
            data.assistant_message?.text ||
            data.assistant_message?.content ||
            data.text ||
            data.message ||
            data.response ||
            "";

        return parseExecutionText(text);
    }

    function getVisibleChatText() {
        const containers = [
            $("mobileChatMessages"),
            $("messagesContainer"),
            $("messages-container"),
            document.querySelector("[data-mobile-chat-messages]"),
            document.querySelector(".mobile-chat-messages"),
            document.querySelector(".chat-messages")
        ].filter(Boolean);

        let messages = [];

        containers.forEach(function (container) {
            const found = Array.from(
                container.querySelectorAll(
                    ".mobile-chat-message, .mobile-message, .message, .bubble, [data-message-role], [data-role]"
                )
            );

            if (found.length) {
                messages = messages.concat(found);
            } else {
                messages.push(container);
            }
        });

        if (!messages.length) {
            messages = Array.from(
                document.querySelectorAll(
                    ".mobile-chat-message, .mobile-message, .message, .bubble, [data-message-role], [data-role]"
                )
            );
        }

        return messages
            .slice(-30)
            .map(function (el) {
                return el.innerText || el.textContent || "";
            })
            .join("\n");
    }

    function refreshFromVisibleChat() {
        const execution = parseExecutionText(getVisibleChatText());

        if (execution) {
            renderExecution(execution);
            return true;
        }

        const cached = loadCachedExecution();

        if (cached) {
            renderExecution(cached);
            return true;
        }

        renderIdle("No active execution found yet. Start one with: auto-plan make a simple todo app");
        return false;
    }

    function openPanel() {
        closeToolsPanel();
        setPanelVisible(true);
        refreshFromVisibleChat();
    }

    function closePanel() {
        setPanelVisible(false);
    }

    function getInput() {
        return $("nova-mobile-input") || $("input") || document.querySelector("textarea, input[type='text']");
    }

    function clickSend() {
        const send =
            $("nova-mobile-send") ||
            $("sendBtn") ||
            document.querySelector("[data-action='send']") ||
            document.querySelector("[data-send]") ||
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

        if (!input) {
            renderIdle("Input not found. Could not send: " + command);
            return;
        }

        input.value = command;
        input.dispatchEvent(new Event("input", { bubbles: true }));

        clickSend();

        renderExecution({
            status: "sent",
            goal: "Execution command",
            current_index: 0,
            total_steps: 3,
            current_step: command
        });

        closePanel();
    }

    function replaceAndBind(button, handler) {
        if (!button || button.dataset.novaExecutionPanelV2 === "1") {
            return;
        }

        const clone = button.cloneNode(true);

        clone.dataset.novaExecutionPanelV2 = "1";
        clone.removeAttribute("onclick");

        clone.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            handler(event);
            return false;
        }, true);

        button.parentNode.replaceChild(clone, button);
    }

    function wireButtons() {
        Array.from(document.querySelectorAll("[data-mobile-tool='execution']"))
            .forEach(function (button) {
                replaceAndBind(button, openPanel);
            });

        Array.from(document.querySelectorAll("button"))
            .filter(function (button) {
                return clean(button.innerText || button.textContent || "").toLowerCase() === "open execution panel";
            })
            .forEach(function (button) {
                replaceAndBind(button, openPanel);
            });

        replaceAndBind($("nova-mobile-execution-close"), closePanel);

        Array.from(document.querySelectorAll("[data-mobile-tool='refresh_execution']"))
            .forEach(function (button) {
                replaceAndBind(button, refreshFromVisibleChat);
            });

        Array.from(document.querySelectorAll("[data-mobile-tool='run_step']"))
            .forEach(function (button) {
                replaceAndBind(button, function () {
                    sendExecutionCommand("next");
                });
            });

        Array.from(document.querySelectorAll("[data-mobile-tool='run_all']"))
            .forEach(function (button) {
                replaceAndBind(button, function () {
                    sendExecutionCommand("run all");
                });
            });
    }

    function patchNovaMobileState() {
        if (!window.NovaMobileState || window.NovaMobileState.__executionPanelV2Patched) {
            return;
        }

        const original = window.NovaMobileState.syncExecutionStatusFromResponse;

        window.NovaMobileState.syncExecutionStatusFromResponse = function (data) {
            if (typeof original === "function") {
                try {
                    original(data);
                } catch (_) {}
            }

            const execution = executionFromResponse(data);

            if (execution) {
                saveCachedExecution(execution);
                renderExecution(execution);
            }
        };

        window.NovaMobileState.__executionPanelV2Patched = true;
    }

    function boot() {
        wireButtons();
        patchNovaMobileState();

        if (getStatusEl()) {
            renderIdle("No active execution loaded.");
        }

        console.log("[Nova Mobile Execution Panel Existing IDs] ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    window.NovaMobileExecutionPanel = {
        open: openPanel,
        close: closePanel,
        refresh: refreshFromVisibleChat,
        update: renderExecution,
        syncFromResponse: function (data) {
            const execution = executionFromResponse(data);

            if (execution) {
                saveCachedExecution(execution);
                renderExecution(execution);
                return true;
            }

            return false;
        },
        send: sendExecutionCommand
    };

    window.NovaOpenMobileExecution = openPanel;
    window.NovaCloseMobileExecution = closePanel;
    window.NovaRefreshMobileExecution = refreshFromVisibleChat;
})();
