/*
 * NOVA CHAT LEGACY SEND DISABLED
 *
 * The desktop composer is now the single send owner.
 * This file remains loaded only for compatibility with
 * older callers that reference window.sendText().
 */

(function () {
    "use strict";

    async function sendText(textOverride) {
        console.warn(
            "[NOVA LEGACY SEND REDIRECT] chat.js -> NovaComposerActions"
        );

        const actions = window.NovaComposerActions;

        if (
            actions &&
            typeof actions.sendCurrentMessage === "function"
        ) {
            const text =
                typeof textOverride === "string"
                    ? textOverride.trim()
                    : "";

            return await actions.sendCurrentMessage(
                text
                    ? { forcedText: text }
                    : {}
            );
        }

        console.error(
            "[NOVA] NovaComposerActions.sendCurrentMessage unavailable"
        );

        return {
            ok: false,
            reason: "composer_actions_unavailable"
        };
    }

    window.sendText = sendText;

    console.log(
        "[NOVA] legacy chat.js loaded — send redirected to ComposerActions"
    );
})();
