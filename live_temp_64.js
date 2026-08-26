
(function () {
    const MARK = "NOVA_DESKTOP_EXECUTION_NATIVE_TOOLS_PANEL_20260702";
    if (window[MARK]) return;
    window[MARK] = true;

    function findInput() {
        return document.querySelector("textarea") ||
               document.querySelector("input[type='text']") ||
               document.querySelector("[contenteditable='true']");
    }

    function setInput(value) {
        const input = findInput();
        if (!input) return;

        if (input.isContentEditable) {
            input.textContent = value;
            input.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: value }));
        } else {
            input.value = value;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.dispatchEvent(new Event("change", { bubbles: true }));
        }

        input.focus();
    }


    function start() {
document.querySelectorAll("#nova-desktop-execution-native [data-exec-fill]").forEach(button => {
    button.addEventListener("click", () => {
        const command = button.getAttribute("data-exec-fill") || "";

        console.log("[NOVA EXECUTION BUTTON]", command);

        handleSendClick(command);
    });
});


        console.log("[NOVA_DESKTOP_EXECUTION_NATIVE_TOOLS_PANEL_20260702] active");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start, { once: true });
    } else {
        start();
    }

})();
