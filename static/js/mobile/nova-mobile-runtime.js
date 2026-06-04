(function () {
    "use strict";

    function syncSessionFromResponse(data) {
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

        if (
            !nextSessionId ||
            typeof nextSessionId !== "string"
        ) {
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

    window.NovaMobileRuntime = {
        setGeneratingState,
        setConnectionState,
        clearGeneratingUiState,
        stopGeneration,
        syncSessionFromResponse
    };

})();