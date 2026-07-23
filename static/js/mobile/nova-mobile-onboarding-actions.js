(function () {
    "use strict";

    const MARK = "NOVA_MOBILE_ONBOARDING_ACTIONS_20260723";

    if (window.__NOVA_MOBILE_ONBOARDING_ACTIONS__) {
        return;
    }

    window.__NOVA_MOBILE_ONBOARDING_ACTIONS__ = true;

    function renderActions(payload) {
        if (!payload || payload.onboarding !== true) {
            return;
        }

        if (!Array.isArray(payload.actions)) {
            return;
        }

        const container =
            window.chatContainer ||
            document.getElementById("mobileChatMessages");

        if (!container) {
            return;
        }

        const row = document.createElement("div");
        row.className = "nova-onboarding-actions";

        payload.actions.forEach(function (action) {
            const button = document.createElement("button");

            button.type = "button";
            button.textContent = action.label || "Start";

button.onclick = function () {
    const input =
        document.getElementById("nova-mobile-input") ||
        document.getElementById("message-input") ||
        document.getElementById("chat-input");

    if (input) {
        input.value = action.prompt || action.label;

        try {
            sessionStorage.setItem(
                "nova_onboarding_intent",
                action.intent || ""
            );
        } catch (_) {}

        input.focus();
    }

    const sendButton =
        document.getElementById("nova-mobile-send");

    if (sendButton) {
        sendButton.click();
    }
};
            row.appendChild(button);
        });

        container.appendChild(row);
    }

    window.NovaMobileOnboardingActions = {
        render: renderActions,
        mark: MARK,
    };

})();