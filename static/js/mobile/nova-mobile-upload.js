(function () {
    "use strict";

    function createUploadProgress(file) {
        const wrapper = document.createElement("div");

        wrapper.className =
            "mobile-chat-message system mobile-upload-card";

        const content = document.createElement("div");

        content.className =
            "mobile-upload-card-content";

        const icon = document.createElement("div");

        icon.className = "mobile-upload-icon";
        icon.textContent = "â†‘";

        const meta = document.createElement("div");

        meta.className = "mobile-upload-meta";

        const title = document.createElement("div");

        title.className = "mobile-upload-title";

        title.textContent =
            file && file.name
                ? file.name
                : "Uploading file...";

        const label = document.createElement("div");

        label.className = "mobile-upload-label";
        label.textContent = "Uploading...";

        const progress = document.createElement("div");

        progress.className =
            "mobile-upload-progress";

        const bar = document.createElement("div");

        bar.className =
            "mobile-upload-progress-bar indeterminate";

        progress.appendChild(bar);

        meta.appendChild(title);
        meta.appendChild(label);
        meta.appendChild(progress);

        content.appendChild(icon);
        content.appendChild(meta);

        wrapper.appendChild(content);

        if (window.chatContainer) {
            window.chatContainer.appendChild(
                wrapper
            );
        }

        return {
            wrapper,
            content,
            icon,
            meta,
            title,
            label,
            progress,
            bar
        };
    }

    function markUploadSuccess(uploadUi, name) {
        if (!uploadUi) return;

        uploadUi.bar.classList.remove(
            "indeterminate"
        );

        uploadUi.bar.style.width = "100%";
        uploadUi.icon.textContent = "âœ“";
        uploadUi.label.textContent = "Uploaded";

        uploadUi.title.textContent =
            name || "Uploaded";

        setTimeout(function () {
            uploadUi.wrapper.remove();
        }, 1200);
    }

    function markUploadFailed(uploadUi) {
        if (!uploadUi) return;

        uploadUi.bar.classList.remove(
            "indeterminate"
        );

        uploadUi.icon.textContent = "!";
        uploadUi.label.textContent =
            "Upload failed.";

        setTimeout(function () {
            uploadUi.wrapper.remove();
        }, 2000);
    }

    function normalizeUploadedFiles(data) {
        if (!data) return [];

        if (Array.isArray(data.files)) {
            return data.files;
        }

        if (data.file) {
            return [data.file];
        }

        return [];
    }

    async function analyzeUploadedAttachment(fileMeta) {
        if (
            typeof window.sendMessage !==
            "function"
        ) {
            return;
        }

        await window.sendMessage({
            text: "Analyze uploaded attachment",
            attachments: [fileMeta],
            regenerate: false
        });
    }

    async function uploadAndAnalyzeFile(file, uploadUi) {
        const formData = new FormData();

        formData.append("file", file);

        const response = await fetch(
            "/api/upload",
            {
                method: "POST",
                body: formData
            }
        );

        if (!response.ok) {
            throw new Error("Upload failed");
        }

        const data = await response.json();

        const uploaded =
            normalizeUploadedFiles(data);

        if (!uploaded.length) {
            throw new Error(
                "Upload response missing file URL"
            );
        }

        for (const item of uploaded) {
            const name =
                item.name ||
                item.filename ||
                "Uploaded";

            const url =
                item.url ||
                item.file_url ||
                item.image_url ||
                "";

            markUploadSuccess(
                uploadUi,
                name
            );

            await analyzeUploadedAttachment({
                name,
                url,
                file_url: url,
                image_url: url,
                mime_type:
                    item.mime_type ||
                    item.type ||
                    ""
            });
        }
    }

    function openUploadPicker() {
        const input =
            document.createElement("input");

        input.type = "file";
        input.multiple = true;

        input.addEventListener(
            "change",
            async function () {
                const files = Array.from(
                    input.files || []
                );

                for (const file of files) {
                    const uploadUi =
                        createUploadProgress(file);

                    try {
                        await uploadAndAnalyzeFile(
                            file,
                            uploadUi
                        );
                    } catch (err) {
                        console.error(
                            "[Nova Mobile] upload/analyze failed:",
                            err
                        );

                        markUploadFailed(
                            uploadUi
                        );

                        if (
                            typeof window.showToast ===
                            "function"
                        ) {
                            window.showToast(
                                "Upload or analysis failed."
                            );
                        }
                    }
                }
            }
        );

        input.click();
    }

    window.NovaMobileUpload = {
        openUploadPicker
    };

    console.log(
        "[Nova Mobile] upload module ready"
    );

})();

/* NOVA_MOBILE_HARD_ATTACH_BUTTON_BRIDGE_20260607 */
(function () {
    "use strict";

    if (window.NovaMobileHardAttachButtonBridgeInstalled) {
        return;
    }

    window.NovaMobileHardAttachButtonBridgeInstalled = true;

    function getOrCreateFileInput() {
        var input = document.getElementById("nova-mobile-hard-file-input");

        if (input) {
            return input;
        }

        input = document.createElement("input");
        input.id = "nova-mobile-hard-file-input";
        input.type = "file";
        input.multiple = true;
        input.style.position = "fixed";
        input.style.left = "-9999px";
        input.style.top = "-9999px";
        input.style.width = "1px";
        input.style.height = "1px";
        input.style.opacity = "0";

        document.body.appendChild(input);

        input.addEventListener("change", function () {
            var files = Array.from(input.files || []);

            if (!files.length) {
                return;
            }

            files.forEach(function (file) {
                var form = new FormData();
                form.append("file", file);

                fetch("/api/upload", {
                    method: "POST",
                    body: form
                })
                    .then(function (response) {
                        return response.json();
                    })
                    .then(function (data) {
                        console.log("[Nova Mobile Hard Attach Button Bridge] uploaded", data);

                        if (typeof window.NovaMobileHardAttachmentPayloadStore === "function") {
                            window.NovaMobileHardAttachmentPayloadStore(data);
                        }

                        window.dispatchEvent(new CustomEvent("nova-mobile-upload-complete", {
                            detail: data
                        }));

                        window.dispatchEvent(new CustomEvent("nova-mobile-attachment-uploaded", {
                            detail: data
                        }));
                    })
                    .catch(function (error) {
                        console.error("[Nova Mobile Hard Attach Button Bridge] upload failed", error);
                    });
            });

            input.value = "";
        });

        return input;
    }

    function isAttachButton(button) {
        if (!button) {
            return false;
        }

        var id = String(button.id || "").toLowerCase();
        var cls = String(button.className || "").toLowerCase();
        var label = String(
            button.getAttribute("aria-label") ||
            button.getAttribute("title") ||
            button.textContent ||
            ""
        ).toLowerCase();

        return (
            id.indexOf("attach") !== -1 ||
            cls.indexOf("attach") !== -1 ||
            label.indexOf("attach") !== -1 ||
            label.indexOf("upload") !== -1 ||
            label.indexOf("file") !== -1
        );
    }

    function bindAttachButtons() {
        Array.from(document.querySelectorAll("button, [role='button']")).forEach(function (button) {
            if (!isAttachButton(button)) {
                return;
            }

            if (button.dataset.novaHardAttachBridge === "1") {
                return;
            }

            button.dataset.novaHardAttachBridge = "1";

            button.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();

                var input = getOrCreateFileInput();
                input.click();

                console.log("[Nova Mobile Hard Attach Button Bridge] attach click handled", button.id || button.textContent || button.className);
            }, true);
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        setTimeout(bindAttachButtons, 0);
        setTimeout(bindAttachButtons, 500);
        setTimeout(bindAttachButtons, 1500);
    });

    document.addEventListener("click", function () {
        setTimeout(bindAttachButtons, 0);
    }, true);

    window.NovaMobileHardAttachBind = bindAttachButtons;
    window.NovaMobileHardAttachInput = getOrCreateFileInput;

    console.log("[Nova Mobile Hard Attach Button Bridge] ready");
})();
