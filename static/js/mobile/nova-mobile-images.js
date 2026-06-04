(function () {
    "use strict";

    function normalizeImageUrl(url) {
        const value = String(url || "").trim();

        if (!value) return "";

        try {
            const parsed = new URL(
                value,
                window.location.origin
            );

            return parsed.pathname + parsed.search;
        } catch {
            return value;
        }
    }

    function openImageLightbox(url, altText) {
        window.open(
            url,
            "_blank",
            "noopener,noreferrer"
        );
    }

    function getGalleryImages() {
        try {
            const images = JSON.parse(
                localStorage.getItem(
                    "novaMobileImageGallery"
                ) || "[]"
            );

            if (!Array.isArray(images)) {
                return [];
            }

            return images.filter(function (image) {
                const url = normalizeImageUrl(
                    image && image.url
                );

                return (
                    url.match(
                        /\.(png|jpg|jpeg|gif|webp)(\?|$)/i
                    ) ||
                    url.includes("/generated_") ||
                    url.includes("/image_")
                );
            });
        } catch {
            return [];
        }
    }

    function openNovaImageViewer(url, altText) {
        if (!url) return;

        let currentUrl = url;
        let gallery = getGalleryImages();

        if (
            !gallery.some(function (image) {
                return (
                    normalizeImageUrl(image.url) ===
                    normalizeImageUrl(url)
                );
            })
        ) {
            gallery.unshift({
                url,
                alt: altText || "Nova image",
                savedAt: Date.now()
            });
        }

        let index = gallery.findIndex(function (image) {
            return (
                normalizeImageUrl(image.url) ===
                normalizeImageUrl(currentUrl)
            );
        });

        if (index < 0) {
            index = 0;
        }

        let viewer = document.getElementById(
            "nova-mobile-image-viewer"
        );

        if (!viewer) {
            viewer = document.createElement("div");
            viewer.id = "nova-mobile-image-viewer";
            viewer.className =
                "nova-mobile-image-viewer hidden";

            viewer.innerHTML = `
                <div class="nova-image-viewer-backdrop"></div>

                <div class="nova-image-viewer-shell">
                    <div class="nova-image-viewer-topbar">
                        <button type="button" class="nova-image-viewer-btn" data-image-viewer-action="close">Close</button>
                        <div class="nova-image-viewer-title">Nova Image</div>
                        <button type="button" class="nova-image-viewer-btn" data-image-viewer-action="copy">Copy</button>
                    </div>

                    <div class="nova-image-viewer-stage">
                        <button type="button" class="nova-image-viewer-nav left" data-image-viewer-action="prev">‹</button>
                        <img class="nova-image-viewer-img" alt="Nova image">
                        <button type="button" class="nova-image-viewer-nav right" data-image-viewer-action="next">›</button>
                    </div>

                    <div class="nova-image-viewer-actions">
                        <button type="button" class="mobile-inline-action" data-image-viewer-action="open">Open</button>
                        <button type="button" class="mobile-inline-action" data-image-viewer-action="share">Share</button>
                        <button type="button" class="mobile-inline-action" data-image-viewer-action="download">Download</button>
                    </div>
                </div>
            `;

            document.body.appendChild(viewer);
        }

        const img = viewer.querySelector(
            ".nova-image-viewer-img"
        );

        const title = viewer.querySelector(
            ".nova-image-viewer-title"
        );

        function render() {
            const item =
                gallery[index] || {
                    url: currentUrl,
                    alt: altText || "Nova image"
                };

            currentUrl = item.url;

            if (img) {
                img.src = item.url;
                img.alt = item.alt || "Nova image";
            }

            if (title) {
                title.textContent =
                    index +
                    1 +
                    " / " +
                    Math.max(gallery.length, 1);
            }
        }

        function closeViewer() {
            viewer.classList.add("hidden");

            document.body.classList.remove(
                "nova-image-viewer-open"
            );
        }

        function move(direction) {
            if (!gallery.length) return;

            index = index + direction;

            if (index < 0) {
                index = gallery.length - 1;
            }

            if (index >= gallery.length) {
                index = 0;
            }

            render();
            vibrate(8);
        }

        viewer.onclick = async function (event) {
            const actionButton =
                event.target.closest(
                    "[data-image-viewer-action]"
                );

            const backdrop =
                event.target.closest(
                    ".nova-image-viewer-backdrop"
                );

            if (backdrop) {
                closeViewer();
                return;
            }

            if (!actionButton) return;

            const action =
                actionButton.getAttribute(
                    "data-image-viewer-action"
                );

            if (action === "close") {
                closeViewer();
                return;
            }

            if (action === "prev") {
                move(-1);
                return;
            }

            if (action === "next") {
                move(1);
                return;
            }

            if (action === "copy") {
                copyText(currentUrl);
                return;
            }

            if (action === "open") {
                window.open(
                    currentUrl,
                    "_blank",
                    "noopener,noreferrer"
                );
                return;
            }

            if (action === "share") {
                if (navigator.share) {
                    try {
                        await navigator.share({
                            title: "Nova image",
                            url: currentUrl
                        });
                    } catch {
                        showToast("Share cancelled.");
                    }
                } else {
                    copyText(currentUrl);
                }

                return;
            }

            if (action === "download") {
                const link =
                    document.createElement("a");

                link.href = currentUrl;
                link.download =
                    "nova-image-" +
                    Date.now() +
                    ".png";

                document.body.appendChild(link);

                link.click();
                link.remove();
            }
        };

        let startX = 0;
        let startY = 0;

        viewer.ontouchstart = function (event) {
            const touch =
                event.touches &&
                event.touches[0];

            if (!touch) return;

            startX = touch.clientX;
            startY = touch.clientY;
        };

        viewer.ontouchend = function (event) {
            const touch =
                event.changedTouches &&
                event.changedTouches[0];

            if (!touch) return;

            const diffX =
                touch.clientX - startX;

            const diffY =
                touch.clientY - startY;

            if (
                Math.abs(diffY) > 120 &&
                diffY > 0
            ) {
                closeViewer();
                return;
            }

            if (
                Math.abs(diffX) > 80 &&
                Math.abs(diffX) >
                    Math.abs(diffY)
            ) {
                move(diffX < 0 ? 1 : -1);
            }
        };

        document.onkeydown = function (event) {
            if (
                viewer.classList.contains(
                    "hidden"
                )
            ) {
                return;
            }

            if (event.key === "Escape") {
                closeViewer();
            }

            if (event.key === "ArrowLeft") {
                move(-1);
            }

            if (event.key === "ArrowRight") {
                move(1);
            }
        };

        render();

        viewer.classList.remove("hidden");

        document.body.classList.add(
            "nova-image-viewer-open"
        );

        vibrate(12);
    }

    function saveMobileImageToGallery(url, altText) {
        if (!url) return;

        let images = [];

        try {
            images = JSON.parse(
                localStorage.getItem(
                    "novaMobileImageGallery"
                ) || "[]"
            );
        } catch {
            images = [];
        }

        const normalizedUrl =
            normalizeImageUrl(url);

        images = images.filter(function (image) {
            return (
                normalizeImageUrl(image.url) !==
                normalizedUrl
            );
        });

        images.unshift({
            url,
            alt: altText || "Nova image",
            savedAt: Date.now()
        });

        localStorage.setItem(
            "novaMobileImageGallery",
            JSON.stringify(
                images.slice(0, 50)
            )
        );
    }

    function openMobileImageGallery() {
        const images = getGalleryImages();

        if (!images.length) {
            if (
                typeof showToast === "function"
            ) {
                showToast(
                    "No images saved yet."
                );
            }

            return;
        }

        const latest = images[0];

        openNovaImageViewer(
            latest.url,
            latest.altText ||
                latest.alt ||
                "Nova image"
        );
    }

    function appendImage(url, altText) {
        if (!chatContainer || !url) return;

        const normalizedUrl =
            String(url || "").trim();

        const existingImage = Array.from(
            chatContainer.querySelectorAll(
                ".mobile-chat-image"
            )
        ).some(function (img) {
            return (
                String(
                    img.getAttribute("src") || ""
                ).trim() === normalizedUrl
            );
        });

        if (existingImage) {
            return;
        }

        saveMobileImageToGallery(
            url,
            altText
        );

        const wrapper =
            document.createElement("div");

        wrapper.className =
            "mobile-chat-message assistant mobile-chat-image-message";

        const img =
            document.createElement("img");

        img.className =
            "mobile-chat-image";

        img.src = normalizedUrl;

        img.alt =
            altText || "Nova image";

        img.loading = "lazy";

        img.addEventListener(
            "click",
            function () {
                openNovaImageViewer(
                    url,
                    altText
                );
            }
        );

        wrapper.appendChild(img);

        chatContainer.appendChild(wrapper);

        scrollBottom();

        setTimeout(
            saveCurrentMessages,
            0
        );
    }

    async function copyText(text) {
        try {
            await navigator.clipboard.writeText(
                text || ""
            );

            showToast("Copied.");
        } catch {
            showToast("Copy failed.");
        }
    }

    window.NovaMobileImages = {
        normalizeImageUrl,
        openImageLightbox,
        getGalleryImages,
        openNovaImageViewer,
        saveMobileImageToGallery,
        openMobileImageGallery,
        appendImage,
        copyText
    };

})();