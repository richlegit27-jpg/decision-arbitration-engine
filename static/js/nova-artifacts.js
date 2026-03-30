(function () {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.state = Nova.state || {};
  Nova.artifacts = Nova.artifacts || {};

  const SEL = {
    panel: "#novaArtifactsPanel",
    list: "#novaArtifactsList",
    empty: "#novaArtifactsEmpty",
    viewer: "#novaArtifactViewer",
    viewerTitle: "#novaArtifactViewerTitle",
    viewerMeta: "#novaArtifactViewerMeta",
    viewerContent: "#novaArtifactViewerContent",
    viewerClose: "#novaArtifactViewerClose",
    artifactsPanelToggle: "#artifactsPanelToggle",
    memoryPanelToggle: "#memoryPanelToggle",
    webPanelToggle: "#webPanelToggle",
  };

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  function injectStyles() {
    if (document.getElementById("novaArtifactsImageViewerStyles")) return;

    const style = document.createElement("style");
    style.id = "novaArtifactsImageViewerStyles";
    style.textContent = `
      .nova-artifact-item {
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 12px;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        background: rgba(255,255,255,0.03);
        margin-bottom: 10px;
      }

      .nova-artifact-item:hover {
        background: rgba(255,255,255,0.05);
      }

      .nova-artifact-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
      }

      .nova-artifact-title {
        font-weight: 600;
        font-size: 14px;
        line-height: 1.3;
        word-break: break-word;
      }

      .nova-artifact-kind {
        font-size: 11px;
        opacity: 0.8;
        padding: 4px 8px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.1);
        white-space: nowrap;
      }

      .nova-artifact-preview {
        font-size: 12px;
        opacity: 0.85;
        line-height: 1.45;
        word-break: break-word;
      }

      .nova-artifact-thumb-wrap {
        width: 100%;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
      }

      .nova-artifact-thumb {
        display: block;
        width: 100%;
        max-height: 220px;
        object-fit: cover;
      }

      .nova-artifact-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .nova-artifact-btn {
        appearance: none;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.06);
        color: inherit;
        padding: 8px 12px;
        border-radius: 10px;
        cursor: pointer;
        font: inherit;
        line-height: 1;
      }

      .nova-artifact-btn:hover {
        background: rgba(255,255,255,0.10);
      }

      .nova-artifact-viewer-image-wrap {
        width: 100%;
        margin-bottom: 12px;
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
      }

      .nova-artifact-viewer-image {
        display: block;
        width: 100%;
        max-height: 70vh;
        object-fit: contain;
      }

      .nova-artifact-viewer-pre {
        white-space: pre-wrap;
        word-break: break-word;
      }

      .nova-artifact-meta-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 8px;
        margin-bottom: 12px;
      }

      .nova-artifact-meta-chip {
        font-size: 12px;
        padding: 8px 10px;
        border-radius: 10px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        word-break: break-word;
      }

      .nova-artifacts-empty {
        opacity: 0.8;
        font-size: 13px;
        padding: 12px 0;
      }
    `;
    document.head.appendChild(style);
  }

  function getCurrentSessionId() {
    return (
      Nova.state.sessionId ||
      Nova.state.currentSessionId ||
      window.currentSessionId ||
      localStorage.getItem("nova_session_id") ||
      document.body?.dataset?.sessionId ||
      ""
    );
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatWhen(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return String(iso);
      return d.toLocaleString();
    } catch (_) {
      return String(iso);
    }
  }

  function artifactImageUrl(artifact) {
    return (
      artifact?.meta?.image_url ||
      artifact?.meta?.url ||
      artifact?.image_url ||
      ""
    );
  }

  function artifactPrompt(artifact) {
    return (
      artifact?.meta?.prompt ||
      artifact?.prompt ||
      artifact?.content ||
      ""
    );
  }

  function artifactTitle(artifact) {
    return artifact?.title || "Untitled Artifact";
  }

  function artifactKind(artifact) {
    return artifact?.kind || "note";
  }

  function viewerEls() {
    return {
      viewer: qs(SEL.viewer),
      title: qs(SEL.viewerTitle),
      meta: qs(SEL.viewerMeta),
      content: qs(SEL.viewerContent),
    };
  }

  function closeViewer() {
    const el = qs(SEL.viewer);
    if (!el) return;
    el.classList.remove("open");
    el.setAttribute("aria-hidden", "true");
  }

  function openViewer() {
    const el = qs(SEL.viewer);
    if (!el) return;
    el.classList.add("open");
    el.setAttribute("aria-hidden", "false");
  }

  async function fetchArtifacts() {
    const sessionId = getCurrentSessionId();
    const url = sessionId
      ? `/api/artifacts?session_id=${encodeURIComponent(sessionId)}`
      : "/api/artifacts";

    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
    });

    let data = {};
    try {
      data = await res.json();
    } catch (_) {
      data = {};
    }

    if (!res.ok || !data.ok) {
      throw new Error(data.error || "Failed to load artifacts.");
    }

    return Array.isArray(data.artifacts) ? data.artifacts : [];
  }

  function copyText(text) {
    return navigator.clipboard.writeText(String(text || ""));
  }

  function downloadUrl(url, fileName) {
    const a = document.createElement("a");
    a.href = url;
    if (fileName) a.download = fileName;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  async function deleteArtifact(artifactId) {
    const res = await fetch(`/api/artifacts/${encodeURIComponent(artifactId)}`, {
      method: "DELETE",
      headers: { Accept: "application/json" },
    });

    let data = {};
    try {
      data = await res.json();
    } catch (_) {
      data = {};
    }

    if (!res.ok || !data.ok) {
      throw new Error(data.error || "Delete failed.");
    }

    return data;
  }

  function renderViewerMeta(artifact) {
    const bits = [];

    if (artifactKind(artifact)) {
      bits.push(`<div class="nova-artifact-meta-chip"><strong>Kind:</strong> ${escapeHtml(artifactKind(artifact))}</div>`);
    }

    if (artifact?.meta?.file_name) {
      bits.push(`<div class="nova-artifact-meta-chip"><strong>File:</strong> ${escapeHtml(artifact.meta.file_name)}</div>`);
    }

    if (artifact?.meta?.mime_type) {
      bits.push(`<div class="nova-artifact-meta-chip"><strong>Type:</strong> ${escapeHtml(artifact.meta.mime_type)}</div>`);
    }

    if (artifact?.meta?.model) {
      bits.push(`<div class="nova-artifact-meta-chip"><strong>Model:</strong> ${escapeHtml(artifact.meta.model)}</div>`);
    }

    if (artifact?.meta?.width && artifact?.meta?.height) {
      bits.push(`<div class="nova-artifact-meta-chip"><strong>Size:</strong> ${escapeHtml(artifact.meta.width)} × ${escapeHtml(artifact.meta.height)}</div>`);
    }

    if (artifact?.created_at) {
      bits.push(`<div class="nova-artifact-meta-chip"><strong>Created:</strong> ${escapeHtml(formatWhen(artifact.created_at))}</div>`);
    }

    return bits.length
      ? `<div class="nova-artifact-meta-grid">${bits.join("")}</div>`
      : "";
  }

  function showArtifactViewer(artifact) {
    const { title, meta, content } = viewerEls();
    if (!title || !meta || !content) return;

    title.textContent = artifactTitle(artifact);
    meta.innerHTML = renderViewerMeta(artifact);

    const kind = artifactKind(artifact);
    const imageUrl = artifactImageUrl(artifact);
    const prompt = artifactPrompt(artifact);

    if (kind === "image" && imageUrl) {
      content.innerHTML = `
        <div class="nova-artifact-viewer-image-wrap">
          <img class="nova-artifact-viewer-image" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(artifactTitle(artifact))}">
        </div>
        <div class="nova-artifact-actions">
          <button type="button" class="nova-artifact-btn" data-viewer-action="download">Download</button>
          <button type="button" class="nova-artifact-btn" data-viewer-action="copy-prompt">Copy prompt</button>
          <button type="button" class="nova-artifact-btn" data-viewer-action="open-image">Open image</button>
        </div>
        <pre class="nova-artifact-viewer-pre">${escapeHtml(prompt || "")}</pre>
      `;

      const downloadBtn = content.querySelector('[data-viewer-action="download"]');
      const copyBtn = content.querySelector('[data-viewer-action="copy-prompt"]');
      const openBtn = content.querySelector('[data-viewer-action="open-image"]');

      if (downloadBtn) {
        downloadBtn.addEventListener("click", () => {
          downloadUrl(imageUrl, artifact?.meta?.file_name || "saved-image");
        });
      }

      if (copyBtn) {
        copyBtn.addEventListener("click", async () => {
          try {
            await copyText(prompt || "");
            copyBtn.textContent = "Copied";
          } catch (_) {
            copyBtn.textContent = "Copy failed";
          }
        });
      }

      if (openBtn) {
        openBtn.addEventListener("click", () => {
          window.open(imageUrl, "_blank", "noopener,noreferrer");
        });
      }
    } else {
      content.innerHTML = `
        <div class="nova-artifact-actions">
          <button type="button" class="nova-artifact-btn" data-viewer-action="copy-content">Copy</button>
        </div>
        <pre class="nova-artifact-viewer-pre">${escapeHtml(artifact?.content || "")}</pre>
      `;

      const copyBtn = content.querySelector('[data-viewer-action="copy-content"]');
      if (copyBtn) {
        copyBtn.addEventListener("click", async () => {
          try {
            await copyText(artifact?.content || "");
            copyBtn.textContent = "Copied";
          } catch (_) {
            copyBtn.textContent = "Copy failed";
          }
        });
      }
    }

    openViewer();
  }

  function makeArtifactCard(artifact) {
    const item = document.createElement("div");
    item.className = "nova-artifact-item";
    item.dataset.artifactId = artifact.id || "";
    item.dataset.kind = artifactKind(artifact);

    const title = artifactTitle(artifact);
    const kind = artifactKind(artifact);
    const imageUrl = artifactImageUrl(artifact);
    const prompt = artifactPrompt(artifact);
    const previewText = prompt || artifact?.content || "";

    item.innerHTML = `
      <div class="nova-artifact-head">
        <div class="nova-artifact-title">${escapeHtml(title)}</div>
        <div class="nova-artifact-kind">${escapeHtml(kind)}</div>
      </div>
      ${
        kind === "image" && imageUrl
          ? `
            <div class="nova-artifact-thumb-wrap">
              <img class="nova-artifact-thumb" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(title)}">
            </div>
          `
          : ""
      }
      <div class="nova-artifact-preview">${escapeHtml(previewText).slice(0, 220)}</div>
      <div class="nova-artifact-actions">
        <button type="button" class="nova-artifact-btn" data-action="open">Open</button>
        ${
          kind === "image" && imageUrl
            ? `<button type="button" class="nova-artifact-btn" data-action="download">Download</button>`
            : `<button type="button" class="nova-artifact-btn" data-action="copy">Copy</button>`
        }
        <button type="button" class="nova-artifact-btn" data-action="delete">Delete</button>
      </div>
    `;

    const openBtn = item.querySelector('[data-action="open"]');
    const downloadBtn = item.querySelector('[data-action="download"]');
    const copyBtn = item.querySelector('[data-action="copy"]');
    const deleteBtn = item.querySelector('[data-action="delete"]');

    if (openBtn) {
      openBtn.addEventListener("click", () => {
        showArtifactViewer(artifact);
      });
    }

    if (downloadBtn) {
      downloadBtn.addEventListener("click", () => {
        downloadUrl(imageUrl, artifact?.meta?.file_name || "saved-image");
      });
    }

    if (copyBtn) {
      copyBtn.addEventListener("click", async () => {
        try {
          await copyText(artifact?.content || "");
          copyBtn.textContent = "Copied";
        } catch (_) {
          copyBtn.textContent = "Copy failed";
        }
      });
    }

    if (deleteBtn) {
      deleteBtn.addEventListener("click", async () => {
        try {
          deleteBtn.disabled = true;
          await deleteArtifact(artifact.id);
          item.remove();
          const list = qs(SEL.list);
          if (list && !list.children.length) {
            renderEmpty("No saved artifacts yet.");
          }
          closeViewer();
        } catch (_) {
          deleteBtn.disabled = false;
          deleteBtn.textContent = "Delete failed";
        }
      });
    }

    return item;
  }

  function renderEmpty(message) {
    const list = qs(SEL.list);
    if (!list) return;
    list.innerHTML = `<div class="nova-artifacts-empty">${escapeHtml(message || "No artifacts yet.")}</div>`;
  }

  function renderArtifacts(artifacts) {
    const list = qs(SEL.list);
    if (!list) return;

    list.innerHTML = "";

    if (!Array.isArray(artifacts) || !artifacts.length) {
      renderEmpty("No saved artifacts yet.");
      return;
    }

    artifacts.forEach((artifact) => {
      list.appendChild(makeArtifactCard(artifact));
    });
  }

  async function refreshArtifacts() {
    try {
      const artifacts = await fetchArtifacts();
      Nova.artifacts.items = artifacts;
      renderArtifacts(artifacts);
    } catch (err) {
      renderEmpty(err?.message || "Failed to load artifacts.");
    }
  }

  function togglePanel(forceOpen) {
    const panel = qs(SEL.panel);
    if (!panel) return;

    const shouldOpen = typeof forceOpen === "boolean"
      ? forceOpen
      : !panel.classList.contains("open");

    qsa(".nova-right-panel.open").forEach((el) => {
      if (el !== panel) el.classList.remove("open");
    });

    panel.classList.toggle("open", shouldOpen);

    if (shouldOpen) {
      refreshArtifacts();
    }
  }

  function installPanelToggles() {
    const artifactsBtn = qs(SEL.artifactsPanelToggle);
    if (artifactsBtn) {
      artifactsBtn.addEventListener("click", () => togglePanel());
    }

    const closeBtn = qs(SEL.viewerClose);
    if (closeBtn) {
      closeBtn.addEventListener("click", closeViewer);
    }

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeViewer();
      }
    });
  }

  function installHooks() {
    document.addEventListener("nova:artifacts:refresh", refreshArtifacts);

    document.addEventListener("click", (event) => {
      const saveBtn = event.target.closest?.('[data-action="save"], [data-viewer-action]');
      if (!saveBtn) return;
    });
  }

  function bootstrap() {
    injectStyles();
    installPanelToggles();
    installHooks();
  }

  Nova.artifacts.refresh = refreshArtifacts;
  Nova.artifacts.openViewer = showArtifactViewer;
  Nova.artifacts.closeViewer = closeViewer;
  Nova.artifacts.togglePanel = togglePanel;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();