(() => {
    "use strict";

    if (window.__novaExecutionLoaded) {
        return;
    }

    window.__novaExecutionLoaded = true;

    const Nova = (window.Nova = window.Nova || {});

    Nova.execution = Nova.execution || {};

    const execution = Nova.execution;

    execution.state = null;
    execution.isRunning = false;
    execution.abortController = null;

    function getPanel() {
        return document.getElementById(
            "nova-desktop-execution-native"
        );
    }

    function getExecutionBody() {
        const panel = getPanel();

        if (!panel) {
            return null;
        }

        return panel.querySelector(
            "[data-execution-panel]"
        );
    }

    function escapeHtml(value) {
        return String(
            value ?? ""
        )
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function normalizeState(value) {
        if (
            value &&
            typeof value === "object" &&
            !Array.isArray(value)
        ) {
            return value;
        }

        return null;
    }

    function render() {
        const container =
            getExecutionBody();

        if (!container) {
            return;
        }

        const state =
            normalizeState(execution.state);

        if (!state) {
            container.innerHTML = `
                <div class="nova-panel-muted">
                    No active mission yet. Start with
                    <strong>auto-plan &lt;goal&gt;</strong>.
                </div>
            `;

            return;
        }

        const steps =
            Array.isArray(state.steps)
                ? state.steps
                : [];

        const status =
            String(
                state.status ||
                "ready"
            );

        const title =
            String(
                state.title ||
                "Execution"
            );

        const goal =
            String(
                state.goal ||
                ""
            );

        const result =
            String(
                state.result ||
                ""
            );

        const error =
            String(
                state.error ||
                ""
            );

        const stepsHtml =
            steps.length
                ? steps.map(
                    (step, index) => {
                        const stepStatus =
                            String(
                                step?.status ||
                                "pending"
                            );

                        const stepTitle =
                            String(
                                step?.title ||
                                step?.action ||
                                `Step ${index + 1}`
                            );

                        let output = "";

                        if (
                            step?.output !== undefined &&
                            step?.output !== null
                        ) {
                            if (
                                typeof step.output === "string"
                            ) {
                                output =
                                    step.output;
                            } else if (
                                typeof step.output === "object"
                            ) {
                                output =
                                    step.output.message ||
                                    step.output.result ||
                                    JSON.stringify(
                                        step.output
                                    );
                            }
                        }

                        return `
                            <div
                                class="nova-execution-step"
                                data-status="${escapeHtml(stepStatus)}"
                            >
                                <div
                                    class="nova-execution-step-header"
                                >
                                    <span
                                        class="nova-execution-step-number"
                                    >
                                        ${index + 1}
                                    </span>

                                    <span
                                        class="nova-execution-step-title"
                                    >
                                        ${escapeHtml(stepTitle)}
                                    </span>

                                    <span
                                        class="nova-execution-step-status"
                                    >
                                        ${escapeHtml(stepStatus)}
                                    </span>
                                </div>

                                ${
                                    output
                                        ? `
                                            <div
                                                class="nova-execution-step-output"
                                            >
                                                ${escapeHtml(output)}
                                            </div>
                                        `
                                        : ""
                                }
                            </div>
                        `;
                    }
                ).join("")
                : `
                    <div class="nova-panel-muted">
                        No execution steps available.
                    </div>
                `;

        container.innerHTML = `
            <div class="nova-execution-header">
                <div class="nova-execution-title">
                    ${escapeHtml(title)}
                </div>

                <div
                    class="nova-execution-status"
                    data-status="${escapeHtml(status)}"
                >
                    ${escapeHtml(status)}
                </div>
            </div>

            ${
                goal
                    ? `
                        <div class="nova-execution-goal">
                            ${escapeHtml(goal)}
                        </div>
                    `
                    : ""
            }

            <div class="nova-execution-steps">
                ${stepsHtml}
            </div>

            ${
                result
                    ? `
                        <div class="nova-execution-result">
                            ${escapeHtml(result)}
                        </div>
                    `
                    : ""
            }

            ${
                error
                    ? `
                        <div class="nova-execution-error">
                            ${escapeHtml(error)}
                        </div>
                    `
                    : ""
            }
        `;
    }

    function mergeExecutionState(
        incoming
    ) {
        const next =
            normalizeState(incoming);

        if (!next) {
            return execution.state;
        }

        execution.state = {
            ...(
                normalizeState(
                    execution.state
                ) || {}
            ),
            ...next,
        };

        return execution.state;
    }

    function getSessionId() {
        const state =
            NovaChatApp?.state ||
            Nova?.state ||
            {};

        return String(
            state.activeChatId ||
            state.activeSessionId ||
            state.session_id ||
            state.sessionId ||
            execution.state?.session_id ||
            execution.state?.id ||
            "nova-execution"
        );
    }

    function getActionFromCommand(command) {
        const value =
            String(command || "")
                .trim()
                .toLowerCase();

        if (
            value === "run all" ||
            value === "run"
        ) {
            return "run";
        }

        if (
            value === "continue" ||
            value === "next"
        ) {
            return "continue";
        }

        if (
            value === "stop" ||
            value === "pause"
        ) {
            return "stop";
        }

        if (
            value === "retry"
        ) {
            return "retry";
        }

        return value || "run";
    }

    async function run(command) {
        if (execution.isRunning) {
            console.warn(
                "[Nova Execution] already running"
            );

            return;
        }

        if (
            !Nova.api ||
            typeof Nova.api.streamExecution !== "function"
        ) {
            console.error(
                "[Nova Execution] streamExecution API unavailable"
            );

            return;
        }

        const action =
            getActionFromCommand(command);

        const currentState =
            normalizeState(
                execution.state
            );

        if (!currentState) {
            console.warn(
                "[Nova Execution] no execution state available"
            );

            return;
        }

        execution.isRunning = true;

        execution.abortController =
            new AbortController();

        try {
            await Nova.api.streamExecution(
                {
                    session_id:
                        getSessionId(),

                    action,

                    execution_state:
                        currentState,
                },
                {
                    signal:
                        execution.abortController.signal,

                    onStart(data) {
                        console.log(
                            "[Nova Execution] start",
                            data
                        );

                        if (
                            data?.execution_state
                        ) {
                            mergeExecutionState(
                                data.execution_state
                            );

                            render();
                        }
                    },

                    onStepStart(data) {
                        console.log(
                            "[Nova Execution] step_start",
                            data
                        );

                        if (
                            data?.execution_state
                        ) {
                            mergeExecutionState(
                                data.execution_state
                            );
                        }

                        render();
                    },

                    onStepDone(data) {
                        console.log(
                            "[Nova Execution] step_done",
                            data
                        );

                        if (
                            data?.execution_state
                        ) {
                            mergeExecutionState(
                                data.execution_state
                            );
                        }

                        render();
                    },

                    onDone(data) {
                        console.log(
                            "[Nova Execution] done",
                            data
                        );

                        if (
                            data?.execution_state
                        ) {
                            mergeExecutionState(
                                data.execution_state
                            );
                        }

                        execution.isRunning =
                            false;

                        execution.abortController =
                            null;

                        render();

                        window.dispatchEvent(
                            new CustomEvent(
                                "nova:execution:done",
                                {
                                    detail:
                                        execution.state,
                                }
                            )
                        );
                    },

                    onError(data) {
                        console.error(
                            "[Nova Execution] error",
                            data
                        );

                        const errorMessage =
                            typeof data === "string"
                                ? data
                                : (
                                    data?.error ||
                                    data?.message ||
                                    "Execution failed."
                                );

                        execution.state = {
                            ...(
                                execution.state ||
                                {}
                            ),

                            status: "error",

                            error:
                                errorMessage,
                        };

                        execution.isRunning =
                            false;

                        execution.abortController =
                            null;

                        render();
                    },

                    onEvent(event) {
                        console.log(
                            "[Nova Execution] event",
                            event
                        );
                    },
                }
            );
        } catch (error) {
            if (
                error?.name ===
                "AbortError"
            ) {
                console.log(
                    "[Nova Execution] aborted"
                );
            } else {
                console.error(
                    "[Nova Execution] failed",
                    error
                );

                execution.state = {
                    ...(
                        execution.state ||
                        {}
                    ),

                    status: "error",

                    error:
                        error?.message ||
                        "Execution request failed.",
                };
            }

            render();
        } finally {
            execution.isRunning =
                false;

            execution.abortController =
                null;
        }
    }

    function stop() {
        if (
            execution.abortController
        ) {
            execution.abortController.abort();
        }

        execution.isRunning =
            false;

        execution.abortController =
            null;

        if (
            execution.state
        ) {
            execution.state = {
                ...execution.state,

                status: "paused",
            };
        }

        render();
    }

    function setState(state) {
        execution.state =
            normalizeState(state);

        render();
    }

    function bindButtons() {
        const buttons =
            document.querySelectorAll(
                "[data-exec-fill]"
            );

        buttons.forEach(
            (button) => {
                if (
                    button.dataset
                        .novaExecutionBound
                ) {
                    return;
                }

                button.dataset
                    .novaExecutionBound =
                    "true";

                button.addEventListener(
                    "click",
                    () => {
                        const command =
                            button.getAttribute(
                                "data-exec-fill"
                            );

                        if (
                            command === "stop" ||
                            command === "pause"
                        ) {
                            stop();

                            return;
                        }

                        run(command);
                    }
                );
            }
        );
    }

    execution.setState =
        setState;

    execution.render =
        render;

    execution.run =
        run;

    execution.stop =
        stop;

    execution.bindButtons =
        bindButtons;

    function initialize() {
        bindButtons();
        render();

        console.log(
            "[Nova Execution] initialized"
        );
    }

    if (
        document.readyState ===
        "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            initialize,
            {
                once: true,
            }
        );
    } else {
        initialize();
    }

    window.addEventListener(
        "nova:execution-state",
        (event) => {
            if (
                event?.detail
            ) {
                setState(
                    event.detail
                );
            }
        }
    );
})();