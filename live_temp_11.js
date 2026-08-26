
(function () {
    "use strict";

    if (window.__NOVA_LEFT_PANEL_ARTIFACTS_FINAL_20260621__) return;
    window.__NOVA_LEFT_PANEL_ARTIFACTS_FINAL_20260621__ = true;

    function esc(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function getButton() {
        return document.getElementById("openArtifactsBtn");
    }

    function ensureLeftArtifactsPanel() {
        let panel = document.getElementById("novaLeftArtifactsPanel");
        if (panel) return panel;

        const btn = getButton();
        const sidebar =
            (btn && btn.closest("aside")) ||
            document.querySelector("aside.sidebar") ||
            document.querySelector("aside") ||
            document.body;

        panel = document.createElement("section");
        panel.id = "novaLeftArtifactsPanel";
        panel.className = "nova-left-artifacts-panel";
        panel.innerHTML = `
            <div class="nova-left-artifacts-head">
                <strong>Artifacts</strong>
                <span id="novaLeftArtifactsCount">0</span>
            </div>
            <div id="novaLeftArtifactsList" class="nova-left-artifacts-list">
                <div class="session-placeholder">Click Artifacts to load.</div>
            </div>
        `;

        const footer = btn && btn.closest(".side-footer-links");

        if (footer && footer.parentNode) {
            footer.parentNode.insertBefore(panel, footer.nextSibling);
        } else {
            sidebar.appendChild(panel);
        }

        return panel;
    }

    function hideOldRightArtifacts() {
        const oldSection =
            document.querySelector(".panel.tools .artifacts-section") ||
            document.querySelector(".artifacts-section");

        if (!oldSection) return;

        oldSection.classList.remove("nova-artifacts-open");
        oldSection.style.setProperty("display", "none", "important");
    }

    function hideLeftArtifacts() {
        const panel = ensureLeftArtifactsPanel();
        panel.classList.remove("nova-left-artifacts-open");
        panel.style.setProperty("display", "none", "important");
        hideOldRightArtifacts();
    }

    function showLeftArtifacts() {
        const panel = ensureLeftArtifactsPanel();
        panel.classList.add("nova-left-artifacts-open");
        panel.style.setProperty("display", "block", "important");
        hideOldRightArtifacts();
        loadLeftArtifacts();
    }

    function toggleLeftArtifacts() {
        const panel = ensureLeftArtifactsPanel();
        const isOpen =
            panel.classList.contains("nova-left-artifacts-open") &&
            window.getComputedStyle(panel).display !== "none";

        if (isOpen) {
            hideLeftArtifacts();
        } else {
            showLeftArtifacts();
        }
    }

    function openLeftArtifactViewer(artifact) {
        const artifactId = artifact.id || artifact.artifact_id || artifact.uuid || "";

        let overlay = document.getElementById("novaArtifactReadableOverlay");
        if (!overlay) {
            overlay = document.createElement("div");
            overlay.id = "novaArtifactReadableOverlay";
            overlay.style.cssText =
                "position:fixed;inset:0;z-index:99999;background:rgba(5,6,18,.72);" +
                "display:flex;align-items:center;justify-content:center;padding:24px;";

            overlay.innerHTML = `
                <div id="novaArtifactReadableBox" style="
                    width:min(980px,96vw);
                    max-height:88vh;
                    overflow:auto;
                    background:#111226;
                    color:#f4f1ff;
                    border:1px solid rgba(255,255,255,.16);
                    border-radius:18px;
                    box-shadow:0 22px 80px rgba(0,0,0,.45);
                    padding:22px;
                    font-family:Inter,system-ui,Segoe UI,Arial,sans-serif;
                ">
                    <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px;">
                        <strong id="novaArtifactReadableTitle" style="font-size:20px;">Artifact</strong>
                        <button id="novaArtifactReadableClose" type="button" style="
                            border:1px solid rgba(255,255,255,.18);
                            background:rgba(255,255,255,.10);
                            color:#fff;
                            border-radius:999px;
                            width:34px;
                            height:34px;
                            cursor:pointer;
                            font-size:20px;
                            line-height:1;
                        ">&times;</button>
                    </div>
                    <div id="novaArtifactReadableMeta" style="opacity:.68;font-size:13px;margin-bottom:14px;"></div>
                    <div id="novaArtifactReadableContent" style="line-height:1.55;">Loading artifact...</div>
                </div>
            `;

            document.body.appendChild(overlay);

            overlay.addEventListener("click", function (event) {
                if (event.target === overlay) {
                    overlay.remove();
                }
            });

            const close = overlay.querySelector("#novaArtifactReadableClose");
            if (close) {
                close.addEventListener("click", function () {
                    overlay.remove();
                });
            }
        }

        function render(record) {
            const item = record.artifact || record.item || record.data || record || artifact;

            const title = item.title || item.name || item.filename || artifact.title || artifact.name || "Nova Artifact";
            const kind = item.kind || item.type || item.mime_type || artifact.kind || artifact.type || "artifact";

            const imageUrl =
                item.image_url ||
                item.preview ||
                item.url ||
                item.file_url ||
                (item.viewer && item.viewer.image_url) ||
                artifact.image_url ||
                artifact.preview ||
                "";

            const body =
                item.content ||
                item.body ||
                item.text ||
                item.markdown ||
                item.output ||
                item.summary ||
                item.prompt ||
                artifact.content ||
                artifact.body ||
                artifact.text ||
                artifact.summary ||
                artifact.prompt ||
                "";

            const titleNode = document.getElementById("novaArtifactReadableTitle");
            const metaNode = document.getElementById("novaArtifactReadableMeta");
            const contentNode = document.getElementById("novaArtifactReadableContent");

            if (titleNode) titleNode.textContent = title;
            if (metaNode) metaNode.textContent = kind;

            if (!contentNode) return;

            let html = "";

            if (imageUrl && /\.(png|jpg|jpeg|gif|webp|svg)(\?|#|$)/i.test(String(imageUrl))) {
                html += `<img src="${esc(imageUrl)}" alt="" style="max-width:100%;border-radius:14px;margin-bottom:14px;display:block;">`;
            }

            if (body) {
                html += `<pre style="white-space:pre-wrap;word-break:break-word;background:rgba(0,0,0,.25);border-radius:14px;padding:14px;margin:0;">${esc(body)}</pre>`;
            } else {
                html += `<pre style="white-space:pre-wrap;word-break:break-word;background:rgba(0,0,0,.25);border-radius:14px;padding:14px;margin:0;">${esc(JSON.stringify(item, null, 2))}</pre>`;
            }

            contentNode.innerHTML = html;
        }

        if (!artifactId) {
            render(artifact);
            return;
        }

        fetch("/api/artifacts/" + encodeURIComponent(artifactId), { cache: "no-store" })
            .then(function (res) { return res.json(); })
            .then(render)
            .catch(function () {
                render(artifact);
            });
    }

    async function loadLeftArtifacts() {
        const list = document.getElementById("novaLeftArtifactsList");
        const count = document.getElementById("novaLeftArtifactsCount");

        if (!list) return;

        list.innerHTML = "<div class='session-placeholder'>Loading artifacts...</div>";

        try {
            const res = await fetch("/api/artifacts", { cache: "no-store" });
            const data = await res.json();

            const artifacts =
                data.artifacts ||
                data.items ||
                data.data ||
                (data.payload && data.payload.artifacts) ||
                (data.payload && data.payload.items) ||
                [];

            if (count) count.textContent = String(artifacts.length);

            if (!artifacts.length) {
                list.innerHTML = "<div class='session-placeholder'>No artifacts yet.</div>";
                return;
            }

            list.innerHTML = "";

            artifacts.slice(0, 30).forEach(function (a) {
                const title = a.title || a.name || "Artifact";
                const kind = a.kind || a.type || "";
                const summary = String(a.summary || a.body || a.prompt || "").slice(0, 160);
                const imageUrl = a.image_url || a.preview || (a.viewer && a.viewer.image_url) || "";
                const artifactId = a.id || a.artifact_id || a.uuid || "";
                const directUrl = a.url || a.file_url || a.path || "";
                const openUrl = directUrl || (artifactId ? "/api/artifacts/" + encodeURIComponent(artifactId) : "");

                const shouldUseViewer = !!artifactId;

                const card = document.createElement(shouldUseViewer ? "button" : (directUrl ? "a" : "button"));
                card.className = "nova-left-artifact-card";

                if (artifactId) {
                    card.dataset.artifactId = artifactId;
                }

                if (shouldUseViewer) {
                    card.type = "button";
                    card.style.textAlign = "left";
                    card.title = "Open artifact";
                    card.addEventListener("click", function (event) {
                        event.preventDefault();
                        event.stopPropagation();
                        openLeftArtifactViewer(a);
                    });
                } else if (directUrl) {
                    card.href = directUrl;
                    card.target = "_blank";
                    card.rel = "noopener noreferrer";
                    card.title = "Open artifact";
                } else {
                    card.type = "button";
                    card.style.textAlign = "left";
                    card.title = "Open artifact";
                    card.addEventListener("click", function (event) {
                        event.preventDefault();
                        event.stopPropagation();
                        openLeftArtifactViewer(a);
                    });
                }

                card.innerHTML = `
                    ${imageUrl ? `<img src="${esc(imageUrl)}" alt="">` : ""}
                    <strong>${esc(title)}</strong>
                    ${kind ? `<span>${esc(kind)}</span>` : ""}
                    ${summary ? `<p>${esc(summary)}</p>` : ""}
                `;

                list.appendChild(card);
            });
        } catch (error) {
            list.innerHTML =
                "<pre style='white-space:pre-wrap;color:#ff8080;'>" +
                esc(error && error.stack ? error.stack : error) +
                "</pre>";
        }
    }

    function bootClosed() {
        ensureLeftArtifactsPanel();
        hideLeftArtifacts();
        hideOldRightArtifacts();
    }

    document.addEventListener("DOMContentLoaded", bootClosed);
    setTimeout(bootClosed, 100);
    setTimeout(bootClosed, 700);

    document.addEventListener("click", function (event) {
        const btn = event.target.closest("#openArtifactsBtn");
        if (!btn) return;

        event.preventDefault();
        event.stopPropagation();

        if (typeof event.stopImmediatePropagation === "function") {
            event.stopImmediatePropagation();
        }

        toggleLeftArtifacts();
    }, true);

    window.NovaShowDesktopArtifacts = showLeftArtifacts;
    window.NovaHideDesktopArtifacts = hideLeftArtifacts;
    window.NovaToggleDesktopArtifacts = toggleLeftArtifacts;

    console.log("[Nova Left Artifacts] final controller ready");
})();
