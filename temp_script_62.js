
(function () {
    "use strict";

    const FIX_ID = "NOVA_ARTIFACTS_PANEL_SIZE_AND_JSON_CLICK_FIX_20260622";

    function getApiKey() {
        return (
            window.API_KEY ||
            window.NOVA_API_KEY ||
            window.apiKey ||
            localStorage.getItem("nova_api_key") ||
            ""
        );
    }

    function ensureArtifactOverlay() {
        let overlay = document.getElementById("novaArtifactReadableOverlay");

        if (!overlay) {
            overlay = document.createElement("div");
            overlay.id = "novaArtifactReadableOverlay";
            overlay.innerHTML = `
                <div id="novaArtifactReadableBox">
                    <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px;border-bottom:1px solid rgba(255,255,255,.10);">
                        <strong id="novaArtifactReadableTitle" style="color:#f8fafc;font-size:15px;">Artifact</strong>
                        <button id="novaArtifactReadableClose" type="button" style="border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.08);color:#f8fafc;border-radius:999px;padding:7px 11px;font-weight:800;cursor:pointer;">Close</button>
                    </div>
                    <div id="novaArtifactReadableContent" class="nova-artifact-readable-content" style="padding:16px;color:#e5e7eb;line-height:1.55;"></div>
                </div>
            `;
            document.body.appendChild(overlay);
        }

        const closeBtn = overlay.querySelector("#novaArtifactReadableClose");
        if (closeBtn && !closeBtn.dataset.novaBound) {
            closeBtn.dataset.novaBound = "1";
            closeBtn.addEventListener("click", function () {
                overlay.style.display = "none";
                overlay.classList.remove("is-open");
            });
        }

        if (!overlay.dataset.novaBackdropBound) {
            overlay.dataset.novaBackdropBound = "1";
            overlay.addEventListener("click", function (event) {
                if (event.target === overlay) {
                    overlay.style.display = "none";
                    overlay.classList.remove("is-open");
                }
            });
        }

        return overlay;
    }

    function pickArtifactObject(data) {
        if (!data) return {};

        if (data.artifact) return data.artifact;
        if (data.item) return data.item;
        if (data.result) return data.result;
        if (data.data && !Array.isArray(data.data)) return data.data;

        return data;
    }

    function pickTitle(item, fallback) {
        return (
            item.title ||
            item.name ||
            item.filename ||
            item.file_name ||
            item.label ||
            fallback ||
            "Artifact"
        );
    }

    function pickContent(item) {
        return (
            item.markdown ||
            item.content ||
            item.text ||
            item.body ||
            item.html ||
            item.output ||
            item.value ||
            item.description ||
            ""
        );
    }

    function showArtifact(item, fallbackTitle) {
        const overlay = ensureArtifactOverlay();
        const titleEl = overlay.querySelector("#novaArtifactReadableTitle");
        const contentEl = overlay.querySelector("#novaArtifactReadableContent");

        const title = pickTitle(item, fallbackTitle);
        const content = pickContent(item);

        if (titleEl) {
            titleEl.textContent = title;
        }

        if (contentEl) {
            contentEl.innerHTML = "";

            if (content) {
                if (item.html && !item.markdown && !item.text && !item.content && !item.body) {
                    contentEl.innerHTML = String(content);
                } else if (window.marked && typeof window.marked.parse === "function") {
                    contentEl.innerHTML = window.marked.parse(String(content));
                } else {
                    const pre = document.createElement("pre");
                    pre.style.margin = "0";
                    pre.style.whiteSpace = "pre-wrap";
                    pre.style.overflowWrap = "anywhere";
                    pre.textContent = String(content);
                    contentEl.appendChild(pre);
                }
            } else {
                const pre = document.createElement("pre");
                pre.style.margin = "0";
                pre.style.whiteSpace = "pre-wrap";
                pre.style.overflowWrap = "anywhere";
                pre.textContent = JSON.stringify(item, null, 2);
                contentEl.appendChild(pre);
            }
        }

        overlay.style.display = "flex";
        overlay.classList.add("is-open");
    }

    function artifactUrlFromCard(card) {
        if (!card) return "";

        const direct =
            card.dataset.artifactUrl ||
            card.dataset.url ||
            card.dataset.href ||
            "";

        if (direct) return direct;

        const href = card.getAttribute("href");
        if (href) return href;

        const link = card.querySelector("a[href]");
        if (link) return link.getAttribute("href") || "";

        const id =
            card.dataset.artifactId ||
            card.dataset.id ||
            card.getAttribute("data-artifact-id") ||
            card.getAttribute("data-id") ||
            "";

        if (id) return "/api/artifacts/" + encodeURIComponent(id);

        return "";
    }

    function looksLikeArtifactUrl(url) {
        return /artifact/i.test(String(url || ""));
    }

    async function openArtifactFromCard(card) {
        const fallbackTitle =
            card.dataset.title ||
            card.getAttribute("title") ||
            card.querySelector("strong, .title")?.textContent?.trim() ||
            "Artifact";

        const url = artifactUrlFromCard(card);

        if (!url || !looksLikeArtifactUrl(url)) {
            const inlineText = card.innerText || card.textContent || "";
            showArtifact({ title: fallbackTitle, text: inlineText }, fallbackTitle);
            return;
        }

        const headers = {};
        const apiKey = getApiKey();

        if (apiKey) {
            headers["x-api-key"] = apiKey;
        }

        const response = await fetch(url, {
            method: "GET",
            headers
        });

        const contentType = response.headers.get("content-type") || "";
        let data;

        if (contentType.includes("application/json")) {
            data = await response.json();
        } else {
            data = {
                title: fallbackTitle,
                text: await response.text()
            };
        }

        const item = pickArtifactObject(data);
        showArtifact(item, fallbackTitle);
    }

    document.addEventListener("click", function (event) {
        const panel = event.target.closest(
            "#novaLeftArtifactsPanel, .nova-left-artifacts-panel, .nova-left-artifacts-list"
        );

        if (!panel) return;

        const card = event.target.closest(
            ".nova-left-artifact-card, [data-artifact-id], [data-artifact-url], a[href*='artifact'], button[data-artifact-id]"
        );

        if (!card) return;

        event.preventDefault();
        event.stopPropagation();

        openArtifactFromCard(card).catch(function (error) {
            console.warn("[" + FIX_ID + "] artifact readable open failed", error);

            const fallbackTitle =
                card.dataset.title ||
                card.querySelector("strong, .title")?.textContent?.trim() ||
                "Artifact";

            showArtifact({
                title: fallbackTitle,
                text: "Could not open this artifact cleanly. The raw JSON click has been blocked, but the artifact endpoint did not return readable content."
            }, fallbackTitle);
        });
    }, true);

    ensureArtifactOverlay();

    console.log("[" + FIX_ID + "] ready");
})();
