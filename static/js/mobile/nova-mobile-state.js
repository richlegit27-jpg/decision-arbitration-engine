(function () {
    "use strict";

    function syncExecutionStatusFromResponse(data) {
        const statusEl = document.querySelector("#nova-mobile-execution-status");
        const progressBar = document.querySelector("#nova-mobile-execution-progress-bar");
        const badge = document.querySelector("#nova-mobile-execution-badge");

        if (!statusEl || !data) return;

        const execution =
            data.execution_state ||
            data.execution ||
            data.assistant_message?.meta?.execution_state ||
            null;

        if (!execution || typeof execution !== "object") return;

        const status = execution.status || "unknown";
        const currentStep =
            execution.current_step ||
            execution.step ||
            execution.current ||
            "";

        const currentIndex =
            typeof execution.current_index === "number"
                ? execution.current_index + 1
                : "";

        const totalSteps = Array.isArray(execution.steps)
            ? execution.steps.length
            : "";

        if (badge) {
            badge.textContent = status;
            badge.dataset.status = status;
        }

        if (
            progressBar &&
            typeof currentIndex === "number" &&
            typeof totalSteps === "number" &&
            totalSteps > 0
        ) {
            const progress = Math.min(
                100,
                Math.max(0, Math.round((currentIndex / totalSteps) * 100))
            );

            progressBar.style.width = `${progress}%`;
        }

        if (currentStep && currentIndex && totalSteps) {
            statusEl.textContent =
                `Status: ${status} · Step ${currentIndex}/${totalSteps}: ${currentStep}`;
            return;
        }

        statusEl.textContent = `Status: ${status}`;
    }

    function syncSessionFromResponse(data) {
        syncExecutionStatusFromResponse(data);

        if (!data) return;

        let nextSessionId =
            data.active_session_id ||
            data.session_id ||
            "";

        if (
            !nextSessionId &&
            data.session &&
            typeof data.session === "object"
        ) {
            nextSessionId = data.session.id || "";
        }

        if (!nextSessionId || typeof nextSessionId !== "string") {
            return;
        }

        nextSessionId = nextSessionId.trim();

        if (!nextSessionId) return;

        window.__novaActiveSessionId = nextSessionId;

        localStorage.setItem(
            "novaMobileSessionId",
            window.__novaActiveSessionId
        );
    }

    window.NovaMobileState = {
        syncExecutionStatusFromResponse,
        syncSessionFromResponse
    };

    console.log("[Nova Mobile] state module ready");
})();