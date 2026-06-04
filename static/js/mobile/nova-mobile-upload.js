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
        icon.textContent = "↑";

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
        uploadUi.icon.textContent = "✓";
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