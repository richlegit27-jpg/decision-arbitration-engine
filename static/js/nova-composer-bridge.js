(() => {
"use strict";

window.NovaComposer = {

    init(config = {}) {
        console.log("[NovaComposer Bridge] init");

        if (window.NovaComposerService?.init) {
            return window.NovaComposerService.init(config);
        }
    },

    sendMessage(...args) {
if (window.NovaComposerActions?.sendCurrentMessage) {
    return window.NovaComposerActions.sendCurrentMessage(...args);
}

        if (window.NovaComposerReactive?.sendMessage) {
            return window.NovaComposerReactive.sendMessage(...args);
        }
    },

    stopGenerating(...args) {
        if (window.NovaComposerActions?.stopGenerating) {
            return window.NovaComposerActions.stopGenerating(...args);
        }
    },

    updateComposerState(...args) {
        if (window.NovaComposerInput?.updateComposerState) {
            return window.NovaComposerInput.updateComposerState(...args);
        }
    },

    setPendingFiles(...args) {
        if (window.NovaComposerAttachments?.setPendingFiles) {
            return window.NovaComposerAttachments.setPendingFiles(...args);
        }
    }

};

console.log("[NovaComposer Bridge] ready");

})();