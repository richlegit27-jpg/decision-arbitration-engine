/*
NOVA_MOBILE_ARTIFACTS_PANEL_SAFE_20260623
Safe mobile artifacts panel.
No global tap catcher.
No MutationObserver.
No page-wide click hijack.
Renders only newest 8 artifacts.
*/

(function () {
    "use strict";

    const FIX_ID = "NOVA_MOBILE_ARTIFACTS_PANEL_SAFE_20260623";
    const MAX_ITEMS = 8;

    let cachedArtifacts = null;
    let loading = false;

    function $(id) {
        return document.getElementById(id);
    }

    function clean(value) {
        return String(value || "")
            .replace(/\r/g, "")
            .replace(/[ \t]+/g, " ")
            .trim();
    }

    function short(value, maxLength) {
        value = clean(value);

        if (value.length <= maxLength) {
            return value;
        }

        return value.slice(0, maxLength) + "?";
    }

    function getApiKey() {
        return (
            window.API_KEY ||
            window.NOVA_API_KEY ||
            window.apiKey ||
            localStorage.getItem("nova_api_key") ||
            localStorage.getItem("NOVA_API_KEY") ||
            "dev"
        );
    }

    function getToolsPanel() {
        return $("nova-mobile-tools-panel");
    }

    function hideToolsPanel() {
        const panel = getToolsPanel();

        if (!panel) return;

        panel.classList.add("hidden");
        panel.style.cssText = "display:none !important;";
    }

    function imageUrl(item) {
        return (
            item.image_url ||
            item.preview ||
            (item.viewer && item.viewer.image_url) ||
            (item.meta && item.meta.image_url) ||
            ""
        );
    }

    function titleOf(item, index) {
        const prompt = clean(item.prompt || item.body || item.summary || "");

        if (item.title && item.title !== "Generated image") {
            return short(item.title, 80);
        }

        if (prompt) {
            return short(prompt, 80);
        }

        return "Artifact " + index;
    }

    function summaryOf(item) {
        return short(item.summary || item.prompt || item.body || "", 120);
    }

    function ensurePanel() {
        let panel = $("nova-mobile-artifacts-panel");

        if (panel) {
            return panel;
        }

        panel = document.createElement("section");
        panel.id = "nova-mobile-artifacts-panel";
        panel.className = "mobile-panel hidden";
        panel.setAttribute("aria-label", "Mobile artifacts");
        panel.setAttribute("aria-hidden", "true");

        panel.innerHTML = [
            '<button id="nova-mobile-artifacts-close" type="button">Close Artifacts</button>',
            '<div class="mobile-panel-title">Artifacts</div>',
            '<div id="nova-mobile-artifacts-count" class="mobile-panel-text">0 artifacts loaded.</div>',
            '<div id="nova-mobile-artifacts-body" class="nova-mobile-artifacts-body">',
            '    <div class="nova-mobile-artifacts-state">Open artifacts to load.</div>',
            '</div>'
        ].join("");

        document.body.appendChild(panel);

        return panel;
    }

    function showPanel() {
        hideToolsPanel();

        const panel = ensurePanel();

        panel.classList.remove("hidden");
        panel.setAttribute("aria-hidden", "false");
        panel.style.cssText = [
            "display:flex !important",
            "position:fixed !important",
            "left:10px !important",
            "right:10px !important",
            "top:90px !important",
            "z-index:999999 !important",
            "flex-direction:column !important",
            "gap:10px !important",
            "padding:14px !important",
            "background:#111827 !important",
            "border:1px solid rgba(255,255,255,.18) !important",
            "border-radius:18px !important",
            "max-height:calc(100vh - 120px) !important",
            "overflow:auto !important",
            "box-shadow:0 18px 50px rgba(0,0,0,.42) !important"
        ].join(";");

        loadArtifacts();
    }

    function closePanel() {
        const panel = ensurePanel();

        panel.classList.add("hidden");
        panel.setAttribute("aria-hidden", "true");
        panel.style.cssText = "display:none !important;";
    }

    function setState(message) {
        const body = $("nova-mobile-artifacts-body");
        const count = $("nova-mobile-artifacts-count");

        if (count) {
            count.textContent = message || "";
        }

        if (body) {
            body.innerHTML = "";

            const state = document.createElement("div");
            state.className = "nova-mobile-artifacts-state";
            state.textContent = message || "No artifacts loaded.";

            body.appendChild(state);
        }
    }

    function extractArtifacts(payload) {
        if (!payload) return [];
        if (Array.isArray(payload)) return payload;
        if (Array.isArray(payload.artifacts)) return payload.artifacts;
        if (payload.data && Array.isArray(payload.data.artifacts)) return payload.data.artifacts;
        if (payload.data && Array.isArray(payload.data)) return payload.data;
        return [];
    }

    function renderArtifacts(items, totalCount) {
        const body = $("nova-mobile-artifacts-body");
        const count = $("nova-mobile-artifacts-count");

        if (!body) return;

        body.innerHTML = "";

        if (count) {
            count.textContent = String(totalCount || items.length) + " artifacts found. Showing newest " + items.length + ".";
        }

        if (!items.length) {
            setState("No artifacts found.");
            return;
        }

        items.forEach(function (item, index) {
            const card = document.createElement("article");
            card.className = "nova-mobile-artifact-card";

            const title = document.createElement("div");
            title.className = "nova-mobile-artifact-title";
            title.textContent = titleOf(item, index + 1);

            const meta = document.createElement("div");
            meta.className = "nova-mobile-artifact-meta";
            meta.textContent = clean(item.kind || item.type || item.group || "artifact");

            const url = imageUrl(item);

            card.appendChild(title);
            card.appendChild(meta);

            if (url) {
                const img = document.createElement("img");
                img.className = "nova-mobile-artifact-image";
                img.src = url;
                img.alt = title.textContent;
                img.loading = "lazy";
                card.appendChild(img);
            }

            const summary = summaryOf(item);

            if (summary) {
                const summaryEl = document.createElement("div");
                summaryEl.className = "nova-mobile-artifact-summary";
                summaryEl.textContent = summary;
                card.appendChild(summaryEl);
            }

            if (url) {
                const open = document.createElement("button");
                open.type = "button";
                open.className = "nova-mobile-artifact-open";
                open.textContent = "Open";
                open.addEventListener("click", function (event) {
                    event.preventDefault();
                    event.stopPropagation();
                    window.open(url, "_blank", "noopener,noreferrer");
                });

                card.appendChild(open);
            }

            body.appendChild(card);
        });
    }

    async function loadArtifacts() {
        if (cachedArtifacts) {
            renderArtifacts(cachedArtifacts.items, cachedArtifacts.total);
            return;
        }

        if (loading) return;

        loading = true;
        setState("Loading artifacts?");

        try {
            const response = await fetch("/api/artifacts", {
                method: "GET",
                headers: {
                    "x-api-key": getApiKey()
                }
            });

            const payload = await response.json();

            if (!response.ok) {
                throw new Error("Artifacts request failed: " + response.status);
            }

            const allItems = extractArtifacts(payload);
            const items = allItems.slice(0, MAX_ITEMS);

            cachedArtifacts = {
                total: allItems.length,
                items: items
            };

            renderArtifacts(items, allItems.length);
        } catch (error) {
            console.warn("[" + FIX_ID + "] failed", error);
            setState("Could not load artifacts: " + String(error && error.message || error));
        } finally {
            loading = false;
        }
    }

    function refreshArtifacts() {
        cachedArtifacts = null;
        loadArtifacts();
    }

    function ensureArtifactsButton() {
        const toolsPanel = getToolsPanel();

        if (!toolsPanel) {
            return;
        }

        const existing = $("nova-mobile-artifacts-open");

        if (existing && existing.parentNode) {
            existing.parentNode.removeChild(existing);
        }

        const button = document.createElement("button");
        button.id = "nova-mobile-artifacts-open";
        button.type = "button";
        button.setAttribute("data-mobile-tool", "artifacts");
        button.textContent = "Artifacts";

        /*
        Keep Artifacts as the very last menu item.
        This means the normal Close button stays directly above it.
        */
        toolsPanel.appendChild(button);
    }

    function bindButton(button, handler) {
        if (!button || button.dataset.novaArtifactsSafeBound === "1") {
            return;
        }

        const clone = button.cloneNode(true);

        clone.dataset.novaArtifactsSafeBound = "1";
        clone.removeAttribute("onclick");

        clone.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            handler(event);
            return false;
        }, true);

        button.parentNode.replaceChild(clone, button);
    }

    function wireButtons() {
        ensureArtifactsButton();

        [
            $("nova-mobile-artifacts-open"),
            $("nova-mobile-artifacts-close")
        ].forEach(function (button) {
            if (!button) return;

            if (button.id === "nova-mobile-artifacts-open") {
                bindButton(button, showPanel);
            }

            if (button.id === "nova-mobile-artifacts-close") {
                bindButton(button, closePanel);
            }
        });

        Array.from(document.querySelectorAll("[data-mobile-tool='artifacts'], [data-mobile-tool='artifact']"))
            .forEach(function (button) {
                bindButton(button, showPanel);
            });
    }

    function boot() {
        ensurePanel();
        wireButtons();

        setTimeout(wireButtons, 400);
        setTimeout(wireButtons, 1000);

        console.log("[Nova Mobile Artifacts Panel Safe] ready");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }

    window.NovaMobileArtifactsPanel = {
        open: showPanel,
        close: closePanel,
        refresh: refreshArtifacts
    };

    window.NovaOpenMobileArtifacts = showPanel;
    window.NovaCloseMobileArtifacts = closePanel;
    window.NovaRefreshMobileArtifacts = refreshArtifacts;
})();
