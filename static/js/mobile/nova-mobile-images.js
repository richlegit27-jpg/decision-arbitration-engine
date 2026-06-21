/* NOVA_MOBILE_IMAGES_MODULE_20260606 */

(function () {
    "use strict";

    function getDeps() {
        return window.NovaMobileImageDeps || window.NovaMobileSessionDeps || {};
    }

    function safeToast(message) {
        if (typeof window.showToast === "function") {
            window.showToast(message);
            return;
        }

        console.log("[Nova Mobile Images]", message);
    }

    function safeVibrate(ms) {
        try {
            if (navigator.vibrate) {
                navigator.vibrate(ms || 8);
            }
        } catch (_) {}
    }

    function chatBox() {
        const deps = getDeps();

        if (typeof deps.chatBox === "function") {
            return deps.chatBox();
        }

        return (
            document.getElementById("mobileChatMessages") ||
            document.getElementById("nova-mobile-messages") ||
            document.querySelector(".mobile-chat-messages") ||
            document.querySelector("[data-mobile-messages]")
        );
    }

    function scrollBottom() {
        const deps = getDeps();

        if (typeof deps.scrollBottom === "function") {
            deps.scrollBottom();
            return;
        }

        const box = chatBox();

        if (box) {
            box.scrollTop = box.scrollHeight;
        }
    }

    function normalizeImageUrl(url) {
        const value = String(url || "").trim();

        if (!value) return "";

        try {
            const parsed = new URL(value, window.location.origin);
            return parsed.pathname + parsed.search;
        } catch (_) {
            return value;
        }
    }

    function isImageUrl(url) {
        const value = normalizeImageUrl(url);

        return (
            value.includes("/api/uploads/") ||
            value.includes("/generated_") ||
            value.includes("/image_") ||
            /\.(png|jpg|jpeg|gif|webp)(\?.*)?$/i.test(value)
        );
    }

    function extractImageUrlFromResponse(data) {
        if (!data) return "";

        const candidates = [
            data?.artifact?.image_url,
            data?.artifact?.preview,
            data?.artifact?.url,
            data?.artifacts?.[0]?.image_url,
            data?.artifacts?.[0]?.preview,
            data?.artifacts?.[0]?.url,
            data?.assistant_message?.image_url,
            data?.assistant_message?.url,
            data?.image_url,
            data?.url,
            data?.preview
        ];

        for (const candidate of candidates) {
            const value = normalizeImageUrl(candidate);

            if (value && isImageUrl(value)) {
                return value;
            }
        }

        return "";
    }

    function getGalleryImages() {
        try {
            const images = JSON.parse(localStorage.getItem("novaMobileImageGallery") || "[]");

            if (!Array.isArray(images)) {
                return [];
            }

            return images.filter(function (image) {
                return isImageUrl(image && image.url);
            });
        } catch (_) {
            return [];
        }
    }

    function saveMobileImageToGallery(url, altText) {
        const normalizedUrl = normalizeImageUrl(url);

        if (!normalizedUrl || !isImageUrl(normalizedUrl)) {
            return;
        }

        let images = [];

        try {
            images = JSON.parse(localStorage.getItem("novaMobileImageGallery") || "[]");
        } catch (_) {
            images = [];
        }

        images = images.filter(function (image) {
            return normalizeImageUrl(image.url) !== normalizedUrl;
        });

        images.unshift({
            url: normalizedUrl,
            alt: altText || "Nova image",
            savedAt: Date.now()
        });

        localStorage.setItem("novaMobileImageGallery", JSON.stringify(images.slice(0, 50)));
    }

    function openImageLightbox(url) {
        const normalizedUrl = normalizeImageUrl(url);

        if (!normalizedUrl) return;

        window.open(normalizedUrl, "_blank", "noopener,noreferrer");
    }

    function openNovaImageViewer(url, altText) {
        const normalizedUrl = normalizeImageUrl(url);

        if (!normalizedUrl) return;

        saveMobileImageToGallery(normalizedUrl, altText);

        let viewer = document.getElementById("nova-mobile-image-viewer");

        if (!viewer) {
            viewer = document.createElement("div");
            viewer.id = "nova-mobile-image-viewer";
            document.body.appendChild(viewer);
        }

        viewer.innerHTML = "";

        viewer.style.cssText =
            "position:fixed !important;" +
            "inset:0 !important;" +
            "z-index:2147483647 !important;" +
            "background:rgba(0,0,0,.92) !important;" +
            "display:flex !important;" +
            "flex-direction:column !important;" +
            "align-items:center !important;" +
            "justify-content:center !important;" +
            "padding:14px !important;";

        const closeBtn = document.createElement("button");
        closeBtn.type = "button";
        closeBtn.textContent = "Close";
        closeBtn.style.cssText =
            "position:absolute;top:12px;right:12px;z-index:2;padding:10px 14px;border-radius:12px;";

        const img = document.createElement("img");
        img.src = normalizedUrl;
        img.alt = altText || "Nova image";
        img.style.cssText =
            "max-width:100% !important;" +
            "max-height:82vh !important;" +
            "border-radius:14px !important;" +
            "box-shadow:0 20px 80px rgba(0,0,0,.7) !important;";

        closeBtn.onclick = function () {
            viewer.style.display = "none";
        };

        viewer.onclick = function (event) {
            if (event.target === viewer) {
                viewer.style.display = "none";
            }
        };

        viewer.appendChild(closeBtn);
        viewer.appendChild(img);

        safeVibrate(12);
    }

    function renderImageIntoBubble(bubble, url, altText) {
        const normalizedUrl = normalizeImageUrl(url);

        if (!bubble || !normalizedUrl) {
            return false;
        }

        bubble.innerHTML = "";

        const img = document.createElement("img");
        img.src = normalizedUrl;
        img.alt = altText || "Nova image";
        img.loading = "lazy";
        img.className = "nova-chat-image mobile-chat-image";
        img.style.display = "block";
        img.style.maxWidth = "100%";
        img.style.borderRadius = "12px";
        img.style.marginTop = "4px";

        img.onclick = function () {
            openNovaImageViewer(normalizedUrl, altText || "Nova image");
        };

        bubble.appendChild(img);
        saveMobileImageToGallery(normalizedUrl, altText);

        return true;
    }

    function appendImage(url, altText) {
        const box = chatBox();
        const normalizedUrl = normalizeImageUrl(url);

        if (!box || !normalizedUrl) return null;

        const wrapper = document.createElement("div");
        wrapper.dataset.role = "assistant";
        wrapper.className = "mobile-chat-message assistant mobile-chat-image-message";
        wrapper.style.margin = "10px auto 10px 0";
        wrapper.style.maxWidth = "90%";
        wrapper.style.padding = "12px 14px";
        wrapper.style.borderRadius = "16px";
        wrapper.style.background = "rgba(255,255,255,.10)";
        wrapper.style.color = "#f8fafc";

        renderImageIntoBubble(wrapper, normalizedUrl, altText);

        box.appendChild(wrapper);
        scrollBottom();

        return wrapper;
    }

    function openMobileImageGallery() {
        const images = getGalleryImages();

        if (!images.length) {
            safeToast("No images saved yet.");
            return;
        }

        openNovaImageViewer(images[0].url, images[0].alt || "Nova image");
    }

    async function copyText(text) {
        try {
            await navigator.clipboard.writeText(text || "");
            safeToast("Copied.");
        } catch (_) {
            safeToast("Copy failed.");
        }
    }

    window.NovaMobileImages = {
        normalizeImageUrl: normalizeImageUrl,
        isImageUrl: isImageUrl,
        extractImageUrlFromResponse: extractImageUrlFromResponse,
        renderImageIntoBubble: renderImageIntoBubble,
        appendImage: appendImage,
        openImageLightbox: openImageLightbox,
        openNovaImageViewer: openNovaImageViewer,
        saveMobileImageToGallery: saveMobileImageToGallery,
        getGalleryImages: getGalleryImages,
        openMobileImageGallery: openMobileImageGallery,
        copyText: copyText
    };

    console.log("[Nova Mobile Images] module ready");
})();

