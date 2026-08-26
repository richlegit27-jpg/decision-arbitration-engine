
(function () {
    "use strict";

    const FIX_ID = "NOVA_LEFT_ARTIFACT_IMAGE_GALLERY_FIX_20260622";

    function getImageSrc(card) {
        const img = card && card.querySelector ? card.querySelector("img") : null;
        if (!img) return "";

        return (
            img.currentSrc ||
            img.src ||
            img.getAttribute("src") ||
            ""
        );
    }

    function getCleanTitle(card, img) {
        const raw =
            card.dataset.title ||
            card.querySelector("strong, .title, [data-title]")?.textContent ||
            img?.alt ||
            card.getAttribute("title") ||
            card.textContent ||
            "Generated image";

        const clean = String(raw || "")
            .replace(/\s+/g, " ")
            .replace(/open in new browser/ig, "")
            .replace(/generated image close/ig, "Generated image")
            .trim();

        return clean || "Generated image";
    }

    function ensureImageOverlay() {
        let overlay = document.getElementById("novaImageArtifactPreviewOverlay");

        if (!overlay) {
            overlay = document.createElement("div");
            overlay.id = "novaImageArtifactPreviewOverlay";
            overlay.innerHTML = `
                <div id="novaImageArtifactPreviewBox">
                    <div id="novaImageArtifactPreviewHead">
                        <div id="novaImageArtifactPreviewTitle">Generated image</div>
                        <button id="novaImageArtifactPreviewClose" type="button">Close</button>
                    </div>
                    <div id="novaImageArtifactPreviewBody">
                        <img id="novaImageArtifactPreviewImg" alt="Generated image preview">
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);
        }

        const closeBtn = overlay.querySelector("#novaImageArtifactPreviewClose");

        if (closeBtn && !closeBtn.dataset.novaBound) {
            closeBtn.dataset.novaBound = "1";
            closeBtn.addEventListener("click", function () {
                overlay.classList.remove("is-open");
            });
        }

        if (!overlay.dataset.novaBackdropBound) {
            overlay.dataset.novaBackdropBound = "1";
            overlay.addEventListener("click", function (event) {
                if (event.target === overlay) {
                    overlay.classList.remove("is-open");
                }
            });
        }

        return overlay;
    }

    function openImagePreview(src, title) {
        if (!src) return;

        const oldReadable = document.getElementById("novaArtifactReadableOverlay");
        if (oldReadable) {
            oldReadable.style.display = "none";
            oldReadable.classList.remove("is-open");
        }

        const overlay = ensureImageOverlay();
        const titleEl = overlay.querySelector("#novaImageArtifactPreviewTitle");
        const imgEl = overlay.querySelector("#novaImageArtifactPreviewImg");

        if (titleEl) {
            titleEl.textContent = title || "Generated image";
        }

        if (imgEl) {
            imgEl.src = src;
            imgEl.alt = title || "Generated image";
        }

        overlay.classList.add("is-open");
    }

    function cleanImageArtifactCards() {
        const cards = document.querySelectorAll(
            "#novaLeftArtifactsList .nova-left-artifact-card, " +
            "#novaLeftArtifactsPanel .nova-left-artifact-card, " +
            ".nova-left-artifacts-panel .nova-left-artifact-card"
        );

        cards.forEach(function (card) {
            const oldImg = card.querySelector("img");
            const src = getImageSrc(card);

            if (!src || !oldImg) return;

            const title = getCleanTitle(card, oldImg);

            card.classList.add("nova-image-artifact-card");
            card.dataset.novaImageSrc = src;
            card.dataset.novaImageTitle = title;

            if (card.dataset.novaGalleryCleaned === "1") return;

            card.dataset.novaGalleryCleaned = "1";

            if (card.tagName === "BUTTON") {
                card.type = "button";
            }

            card.removeAttribute("href");

            const img = document.createElement("img");
            img.src = src;
            img.alt = title;
            img.loading = "lazy";
            img.decoding = "async";

            const label = document.createElement("span");
            label.className = "nova-image-artifact-title";
            label.textContent = title;

            card.innerHTML = "";
            card.appendChild(img);
            card.appendChild(label);
        });
    }

    function scheduleClean() {
        [50, 200, 600, 1200].forEach(function (ms) {
            setTimeout(cleanImageArtifactCards, ms);
        });
    }

    document.addEventListener("click", function (event) {
        cleanImageArtifactCards();

        const card = event.target.closest(
            "#novaLeftArtifactsList .nova-left-artifact-card, " +
            "#novaLeftArtifactsPanel .nova-left-artifact-card, " +
            ".nova-left-artifacts-panel .nova-left-artifact-card"
        );

        if (!card) return;

        const src = card.dataset.novaImageSrc || getImageSrc(card);
        if (!src) return;

        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        openImagePreview(src, card.dataset.novaImageTitle || "Generated image");

        return false;
    }, true);

    const observer = new MutationObserver(scheduleClean);

    observer.observe(document.documentElement, {
        childList: true,
        subtree: true
    });

    window.NovaCleanImageArtifactCards = cleanImageArtifactCards;
    window.NovaOpenImageArtifactPreview = openImagePreview;

    ensureImageOverlay();
    scheduleClean();

    console.log("[" + FIX_ID + "] ready");
})();
