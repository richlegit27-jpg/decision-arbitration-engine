(function () {
    "use strict";

    console.log(
        "[NOVA EXECUTION CONTROLS] script loaded"
    );

    function getActiveProjectId() {
        return (
            window.__NOVA_PROJECT_STATE &&
            window.__NOVA_PROJECT_STATE.activeProjectId
        ) || null;
    }

async function runProjectAction(
    projectId,
    action
) {
    if (!projectId || !action) {
        return;
    }

    const projects =
        window.NovaDesktopProjects;

    if (!projects) {
        console.error(
            "NovaDesktopProjects is not available."
        );
        return;
    }

    try {
        if (
            typeof
            projects.controlProjectExecution
            !== "function"
        ) {
            console.error(
                "controlProjectExecution is not available."
            );
            return;
        }

        await projects.controlProjectExecution(
            projectId,
            action
        );

    } catch (error) {
        console.error(
            "Project execution action failed:",
            action,
            error
        );
    }
}

    function bindButton(
        elementId,
        action
    ) {
        const button =
            document.getElementById(elementId);

        if (!button) {
            console.warn(
                "[NOVA EXECUTION CONTROLS] Button not found:",
                elementId
            );

            return;
        }

        if (
            button.dataset.novaExecutionWired === "true"
        ) {
            return;
        }

        button.dataset.novaExecutionWired = "true";

        button.addEventListener(
            "click",
            async function () {
                console.log(
                    "[NOVA EXECUTION CONTROLS] Button clicked:",
                    action
                );

                button.disabled = true;

                try {
await runProjectAction(
    getActiveProjectId(),
    action
);
                } finally {
                    button.disabled = false;
                }
            }
        );

        console.log(
            "[NOVA EXECUTION CONTROLS] Wired:",
            elementId,
            action
        );
    }

    function wireExecutionButtons() {
        /*
         * Left sidebar controls.
         */

        bindButton(
            "novaLeftRunAll",
            "run_all"
        );

        bindButton(
            "novaLeftStop",
            "stop"
        );

        bindButton(
            "novaLeftReset",
            "reset"
        );

        /*
         * Existing right-panel controls.
         * These remain supported.
         */
        bindButton(
            "desktopContinueProject",
            "continue"
        );

        bindButton(
            "desktopApproveProject",
            "approve"
        );

        bindButton(
            "desktopRunAll",
            "run_all"
        );

        bindButton(
            "desktopPause",
            "pause"
        );
    }

    function initialize() {
        wireExecutionButtons();

        setTimeout(
            wireExecutionButtons,
            500
        );

        setTimeout(
            wireExecutionButtons,
            1500
        );
    }

    if (
        document.readyState === "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            initialize,
            { once: true }
        );
    } else {
        initialize();
    }

    window.NovaProjectExecutionControls = {
        wireExecutionButtons,
        runProjectAction
    };

})();
