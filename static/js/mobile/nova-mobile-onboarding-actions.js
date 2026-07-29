(function () {
    "use strict";

    const MARK = "NOVA_MOBILE_ONBOARDING_ACTIONS_20260723";

    if (window.__NOVA_MOBILE_ONBOARDING_ACTIONS__) {
        return;
    }

    window.__NOVA_MOBILE_ONBOARDING_ACTIONS__ = true;

    function renderActions(payload) {

        console.log(
            "[ONBOARDING RENDER CALLED]",
            payload
        );

        if (!payload || payload.onboarding !== true) {
            return;
        }

        if (!Array.isArray(payload.actions)) {
            return;
        }

        const container =
            window.chatContainer ||
            document.getElementById("mobileChatMessages") ||
            document.getElementById("nova-mobile-chat") ||
            document.getElementById("nova-chat") ||
            document.getElementById("chat-container");

        console.log(
            "[ONBOARDING CONTAINER CHECK]",
            {
                chatContainer: window.chatContainer,
                mobileChatMessages:
                    document.getElementById("mobileChatMessages"),
                novaMobileChat:
                    document.getElementById("nova-mobile-chat"),
                novaChat:
                    document.getElementById("nova-chat"),
                chatContainerFallback:
                    document.getElementById("chat-container"),
                resolved: container
            }
        );

        if (!container) {
            console.error(
                "[ONBOARDING FAILED] No chat container found"
            );
            return;
        }

        if (payload.welcome_message) {
            const welcome = document.createElement("div");

            welcome.className = "nova-onboarding-welcome";
            welcome.textContent = payload.welcome_message;

            container.appendChild(welcome);
        }

        const row = document.createElement("div");

        row.className = "nova-onboarding-actions";

        payload.actions.forEach(function (action) {
            const button = document.createElement("button");

            button.type = "button";
            button.textContent =
                action.label || "Start";

            button.style.setProperty(
                "color",
                "#ffffff",
                "important"
            );

            button.style.setProperty(
                "background",
                "#355a8a",
                "important"
            );

            button.onclick = function () {
                const input =
                    document.getElementById("nova-mobile-input") ||
                    document.getElementById("message-input") ||
                    document.getElementById("chat-input");

                if (input) {
                    input.value =
                        action.prompt ||
                        action.label;

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

        console.log(
            "[ONBOARDING RENDER COMPLETE]"
        );
    }

    window.NovaMobileOnboardingActions = {
        render: renderActions,
        mark: MARK,
    };

})();