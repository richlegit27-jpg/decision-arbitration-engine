
(function () {
    function initDesktopAttachments() {
        const btn = document.getElementById("attachBtn");
        const input = document.getElementById("desktopFileInput");

        if (!btn || !input || btn.dataset.novaAttachmentBound) {
            return;
        }

        btn.dataset.novaAttachmentBound = "true";

        btn.addEventListener("click", () => {
            input.value = "";
            input.click();
        });

        input.addEventListener("change", () => {
            const file = input.files && input.files[0];

            if (!file) {
                return;
            }

            uploadDesktopAttachment(file).catch((error) => {
                console.error("[Nova Desktop Upload Error]", error);
            });
        });

        console.log("[Nova Desktop Attachments] bound");
    }

    initDesktopAttachments();
    setTimeout(initDesktopAttachments, 500);
})();
