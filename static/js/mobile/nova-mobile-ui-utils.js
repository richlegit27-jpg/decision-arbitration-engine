(function () {
    "use strict";

    function togglePanel(panel) {
        if (!panel) return;

        panel.classList.toggle("hidden");
    }

    function closePanel(panel) {
        if (!panel) return;

        panel.classList.add("hidden");
    }

function closeAllPanels() {
    const panels = [
        document.querySelector("#memoryPanel"),
        document.querySelector("#sessionsPanel"),
        document.querySelector("#toolsPanel"),
        document.querySelector("#mobileMemoryPanel"),
        document.querySelector("#mobileSessionsPanel"),
        document.querySelector("#mobileToolsPanel"),
        document.querySelector("[data-mobile-memory-panel]"),
        document.querySelector("[data-mobile-sessions-panel]"),
        document.querySelector("[data-mobile-tools-panel]")
    ];

    panels.forEach(function (panel) {
        if (!panel) return;

        panel.classList.remove("open");
        panel.classList.remove("is-open");
        panel.setAttribute("aria-hidden", "true");
    });
}

    function runTool(tool) {
        switch (tool) {
            case "web":
                setInputText("Search the web for ");
                return;

            case "image":
                setInputText("/image ");
                return;

            case "upload":
                window.NovaMobileUpload.openUploadPicker();
                return;

            case "voice":
                window.NovaMobileVoice.startVoiceInput();
                return;

            case "memory":
                togglePanel(memoryPanel);
                return;

            case "execution":
                togglePanel(executionPanel);
                return;
        }
    }

    function getChatTranscript() {
        const messages = chatContainer
            ? Array.from(
                  chatContainer.querySelectorAll(
                      ".mobile-chat-message"
                  )
              )
            : [];

        return messages
            .map(function (message) {
                return cleanText(message.textContent || "");
            })
            .filter(Boolean)
            .join("\n\n");
    }

    function copyWholeChat() {
        copyText(
            getChatTranscript() || "No chat messages."
        );
    }

    function exportWholeChat() {
        const blob = new Blob(
            [
                getChatTranscript() ||
                    "No chat messages.",
            ],
            {
                type: "text/plain",
            }
        );

        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");

        link.href = url;
        link.download =
            "nova-chat-" + Date.now() + ".txt";

        document.body.appendChild(link);

        link.click();
        link.remove();

        URL.revokeObjectURL(url);

        showToast("Chat exported.");
        hapticSuccess();
    }

    window.NovaMobileUiUtils = {
        togglePanel,
        closePanel,
        closeAllPanels,
        runTool,
        getChatTranscript,
        copyWholeChat,
        exportWholeChat
    };

})();