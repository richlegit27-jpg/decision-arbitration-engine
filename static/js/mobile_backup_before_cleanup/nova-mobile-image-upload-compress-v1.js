(function () {
    "use strict";

    if (window.__NOVA_MOBILE_IMAGE_UPLOAD_COMPRESS_V1_20260705__) {
        return;
    }

    window.__NOVA_MOBILE_IMAGE_UPLOAD_COMPRESS_V1_20260705__ = true;

    const LOG = "[Nova Mobile Image Upload Compress V1]";

    const MAX_DIMENSION = 1280;
    const START_QUALITY = 0.82;
    const MIN_COMPRESS_BYTES = 900 * 1024;

    function isImageFile(file) {
        return file && /^image\//i.test(file.type || "");
    }

    function needsCompression(file) {
        return isImageFile(file) && file.size > MIN_COMPRESS_BYTES;
    }

    function loadImage(file) {
        return new Promise(function (resolve, reject) {
            const url = URL.createObjectURL(file);
            const img = new Image();

            img.onload = function () {
                URL.revokeObjectURL(url);
                resolve(img);
            };

            img.onerror = function () {
                URL.revokeObjectURL(url);
                reject(new Error("Image decode failed"));
            };

            img.src = url;
        });
    }

    function canvasToBlob(canvas, quality) {
        return new Promise(function (resolve) {
            canvas.toBlob(function (blob) {
                resolve(blob);
            }, "image/jpeg", quality);
        });
    }

    async function compressImageFile(file) {
        if (!needsCompression(file)) {
            return file;
        }

        const img = await loadImage(file);

        let width = img.naturalWidth || img.width;
        let height = img.naturalHeight || img.height;

        if (!width || !height) {
            return file;
        }

        const scale = Math.min(1, MAX_DIMENSION / Math.max(width, height));
        const outWidth = Math.max(1, Math.round(width * scale));
        const outHeight = Math.max(1, Math.round(height * scale));

        const canvas = document.createElement("canvas");
        canvas.width = outWidth;
        canvas.height = outHeight;

        const ctx = canvas.getContext("2d", {
            alpha: false
        });

        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, outWidth, outHeight);
        ctx.drawImage(img, 0, 0, outWidth, outHeight);

        let blob = await canvasToBlob(canvas, START_QUALITY);

        if (!blob) {
            return file;
        }

        if (blob.size > 900 * 1024) {
            blob = await canvasToBlob(canvas, 0.72) || blob;
        }

        if (blob.size > 900 * 1024) {
            blob = await canvasToBlob(canvas, 0.62) || blob;
        }

        const baseName = String(file.name || "image")
            .replace(/\.[^.]+$/, "")
            .replace(/[^\w.-]+/g, "_")
            .slice(0, 80) || "image";

        const compressed = new File([blob], baseName + "_nova_compressed.jpg", {
            type: "image/jpeg",
            lastModified: Date.now()
        });

        console.log(LOG, "compressed image", {
            fromName: file.name,
            fromType: file.type,
            fromBytes: file.size,
            toName: compressed.name,
            toType: compressed.type,
            toBytes: compressed.size,
            width: outWidth,
            height: outHeight
        });

        return compressed;
    }

    async function compressFileList(fileList) {
        const files = Array.from(fileList || []);

        if (!files.some(needsCompression)) {
            return null;
        }

        const dt = new DataTransfer();

        for (const file of files) {
            const out = await compressImageFile(file);
            dt.items.add(out);
        }

        return dt.files;
    }

    document.addEventListener("change", async function (event) {
        const input = event.target;

        if (!input || input.tagName !== "INPUT" || input.type !== "file") {
            return;
        }

        if (input.dataset.novaImageCompressing === "1") {
            return;
        }

        if (!input.files || !input.files.length) {
            return;
        }

        if (!Array.from(input.files).some(needsCompression)) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        try {
            input.dataset.novaImageCompressing = "1";

            const compressedFiles = await compressFileList(input.files);

            if (compressedFiles && compressedFiles.length) {
                input.files = compressedFiles;
            }

            input.dataset.novaImageCompressed = "1";

            input.dispatchEvent(new Event("change", {
                bubbles: true,
                cancelable: true
            }));
        } catch (err) {
            console.warn(LOG, "compression failed; using original file", err);

            input.dispatchEvent(new Event("change", {
                bubbles: true,
                cancelable: true
            }));
        } finally {
            setTimeout(function () {
                delete input.dataset.novaImageCompressing;
            }, 0);
        }
    }, true);

    window.NovaMobileImageUploadCompressV1 = {
        version: "v1",
        needsCompression: needsCompression,
        compressImageFile: compressImageFile
    };

    console.log(LOG, "installed");
})();
