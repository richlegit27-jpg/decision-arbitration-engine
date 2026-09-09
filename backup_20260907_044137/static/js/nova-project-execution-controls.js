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

    async function runProjectAction(action) {
        const projectId = getActiveProjectId();

        console.log(
            "[NOVA EXECUTION CONTROLS] action requested:",
            action,
            projectId
        );

        if (!projectId) {
            console.warn(
                "[NOVA EXECUTION CONTROLS] No active project"
            );
            return;
        }

        const projects =
            window.NovaDesktopProjects;

        if (!projects) {
            console.error(
                "[NOVA EXECUTION CONTROLS] NovaDesktopProjects is not ready"
            );
            return;
        }

        try {
            if (
                action === "continue" &&
                typeof projects.continueProject === "function"
            ) {
                await projects.continueProject(
                    projectId
                );

                return;
            }

            if (
                action === "run_all" &&
                typeof projects.runAllProject === "function"
            ) {
                await projects.runAllProject(
                    projectId
                );

                return;
            }

            if (
                action === "pause" &&
                typeof projects.controlProjectExecution === "function"
            ) {
                await projects.controlProjectExecution(
                    projectId,
                    "pause"
                );

                return;
            }

            console.error(
                "[NOVA EXECUTION CONTROLS] Unsupported action:",
                action
            );

        } catch (error) {
            console.error(
                "[NOVA EXECUTION CONTROLS] Action failed:",
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

                await runProjectAction(action);
            }
        );

        console.log(
            "[NOVA EXECUTION CONTROLS] Wired:",
            elementId,
            action
        );
    }

    function wireExecutionButtons() {
        bindButton(
            "desktopContinueProject",
            "continue"
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