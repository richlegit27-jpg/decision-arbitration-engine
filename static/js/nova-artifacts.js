(function () {
  "use strict";

  const LOG_PREFIX = "[NovaArtifacts]";
  const API = {
    list: "/api/artifacts",
    read(id) {
      return "/api/artifacts/" + encodeURIComponent(id);
    }
  };

  const state = {
    booted: false,
    loading: false,
    artifacts: [],
    filtered: [],
    activeArtifactId: "",
    activeArtifact: null,
    filterText: "",
    eventsBound: false,
    refreshTimer: null,
    stylesInjected: false
  };

  function log() {
    try {
      console.log(LOG_PREFIX, ...arguments);
    } catch (_) {}
  }

  function safeText(value) {
    if (value === null || value === undefined) return "";
    return String(value);
  }

  function escapeHtml(value) {
    return safeText(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatDate(value) {
    const raw = safeText(value).trim();
    if (!raw) return "";
    const dt = new Date(raw);
    if (Number.isNaN(dt.getTime())) return raw;
    try {
      return dt.toLocaleString();
    } catch (_) {
      return raw;
    }
  }

  function getEls() {
    return {
      panel:
        document.querySelector("#artifactsPanel") ||
        document.querySelector("#artifactPanel") ||
        document.querySelector("[data-panel='artifacts']") ||
        null,
      list:
        document.querySelector("#artifactList") ||
        document.querySelector("#artifactsList") ||
        document.querySelector("#novaArtifactList") ||
        document.querySelector("[data-role='artifact-list']") ||
        null,
      empty:
        document.querySelector("#artifactEmpty") ||
        document.querySelector("#artifactsEmpty") ||
        document.querySelector(".nova-artifacts-empty") ||
        null,
      viewer:
        document.querySelector("#artifactViewer") ||
        document.querySelector("#artifactsViewer") ||
        document.querySelector("#novaArtifactViewer") ||
        document.querySelector("[data-role='artifact-viewer']") ||
        null,
      viewerTitle:
        document.querySelector("#artifactViewerTitle") ||
        document.querySelector("#activeArtifactTitle") ||
        document.querySelector("[data-role='artifact-viewer-title']") ||
        null,
      viewerMeta:
        document.querySelector("#artifactViewerMeta") ||
        document.querySelector("#activeArtifactMeta") ||
        document.querySelector("[data-role='artifact-viewer-meta']") ||
        null,
      viewerBody:
        document.querySelector("#artifactViewerBody") ||
        document.querySelector("#artifactContent") ||
        document.querySelector("#activeArtifactContent") ||
        document.querySelector("[data-role='artifact-viewer-body']") ||
        null,
      refreshBtn:
        document.querySelector("#refreshArtifactsBtn") ||
        document.querySelector("#artifactRefresh") ||
        document.querySelector("[data-action='refresh-artifacts']") ||
        null,
      searchInput:
        document.querySelector("#artifactSearchInput") ||
        document.querySelector("#artifactsSearchInput") ||
        document.querySelector("#artifactSearch") ||
        document.querySelector("[data-role='artifact-search']") ||
        null,
      filterSelect:
        document.querySelector("#artifactFilter") || null,
      copyBtn:
        document.querySelector("#copyArtifactBtn") ||
        document.querySelector("[data-action='copy-artifact']") ||
        null,
      openBtn:
        document.querySelector("#openArtifactBtn") ||
        document.querySelector("[data-action='open-artifact']") ||
        null,
      deleteBtn:
        document.querySelector("#deleteArtifactBtn") ||
        document.querySelector("[data-action='delete-artifact']") ||
        null
    };
  }

  async function apiFetch(url, options) {
    const response = await fetch(url, options || {});
    let data = null;

    try {
      data = await response.json();
    } catch (_) {
      data = null;
    }

    if (!response.ok) {
      throw new Error(
        (data && (data.error || data.message)) ||
          response.status + " " + response.statusText ||
          "Request failed"
      );
    }

    return data || {};
  }

  function artifactId(item) {
    return safeText(item && (item.id || item.artifact_id || item.artifactId)).trim();
  }

  function artifactTitle(item) {
    return safeText(item && (item.title || item.name || "Untitled artifact")).trim() || "Untitled artifact";
  }

  function artifactKind(item) {
    return safeText(item && (item.kind || item.type || "artifact")).trim() || "artifact";
  }

  function artifactContent(item) {
    return safeText(item && (item.content || item.text || item.body || ""));
  }

  function artifactSessionId(item) {
    return safeText(item && (item.session_id || item.sessionId || "")).trim();
  }

  function artifactCreatedAt(item) {
    return safeText(
      item &&
        (item.created_at ||
          item.createdAt ||
          item.updated_at ||
          item.updatedAt ||
          "")
    ).trim();
  }

  function artifactUpdatedAt(item) {
    return safeText(
      item &&
        (item.updated_at ||
          item.updatedAt ||
          item.created_at ||
          item.createdAt ||
          "")
    ).trim();
  }

  function artifactMeta(item) {
    return item && item.meta && typeof item.meta === "object" ? item.meta : null;
  }

  function artifactPinned(item) {
    return !!(item && (item.pinned || item.is_pinned || item.pin));
  }

  function extractArtifacts(payload) {
    if (!payload) return [];
    if (Array.isArray(payload.artifacts)) return payload.artifacts;
    if (payload.data && Array.isArray(payload.data.artifacts)) return payload.data.artifacts;
    if (payload.state && Array.isArray(payload.state.artifacts)) return payload.state.artifacts;
    if (Array.isArray(payload.items)) return payload.items;
    if (Array.isArray(payload)) return payload;
    return [];
  }

  function kindLabel(kind) {
    const raw = safeText(kind).trim().toLowerCase();
    if (!raw) return "Artifact";
    if (raw === "chat_reply") return "Chat Reply";
    if (raw === "web_result") return "Web Result";
    if (raw === "doc_analysis") return "Document Analysis";
    return raw
      .split(/[_\-\s]+/)
      .filter(Boolean)
      .map(function (part) {
        return part.charAt(0).toUpperCase() + part.slice(1);
      })
      .join(" ");
  }

  function cleanTitle(raw) {
    let title = safeText(raw).trim();
    if (!title) return "Untitled Artifact";

    title = title.replace(/\s+/g, " ").trim();

    if (/^chat reply\s*-\s*/i.test(title)) {
      title = title.replace(/^chat reply\s*-\s*/i, "").trim();
    }

    if (!title) return "Chat Reply";
    if (title.length > 92) return title.slice(0, 92).trim() + "…";
    return title;
  }

  function cleanPreviewText(text) {
    let value = safeText(text);

    value = value.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, function (_, alt) {
      const label = safeText(alt).trim();
      return label ? "[image: " + label + "]" : "[image]";
    });

    value = value.replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1");
    value = value.replace(/`([^`]+)`/g, "$1");
    value = value.replace(/\*\*([^*]+)\*\*/g, "$1");
    value = value.replace(/\*([^*]+)\*/g, "$1");
    value = value.replace(/^#+\s*/gm, "");
    value = value.replace(/^\s*-\s+/gm, "• ");
    value = value.replace(/\n{3,}/g, "\n\n");
    value = value.replace(/[ \t]+\n/g, "\n");
    value = value.trim();

    return value;
  }

  function artifactPreview(item) {
    const content = cleanPreviewText(artifactContent(item)).replace(/\s+/g, " ").trim();
    if (!content) return "No content";
    if (content.length <= 160) return content;
    return content.slice(0, 160).trim() + "…";
  }

  function sortArtifacts(items) {
    return (Array.isArray(items) ? items : []).slice().sort((a, b) => {
      const aPinned = artifactPinned(a) ? 1 : 0;
      const bPinned = artifactPinned(b) ? 1 : 0;
      if (aPinned !== bPinned) return bPinned - aPinned;

      const aTs = new Date(artifactUpdatedAt(a)).getTime() || 0;
      const bTs = new Date(artifactUpdatedAt(b)).getTime() || 0;
      return bTs - aTs;
    });
  }

  function findArtifact(id) {
    const wanted = safeText(id || state.activeArtifactId).trim();
    if (!wanted) return null;
    return state.artifacts.find((item) => artifactId(item) === wanted) || null;
  }

  function dispatch(name, detail) {
    try {
      document.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
    } catch (error) {
      console.error(LOG_PREFIX, "dispatch failed", name, error);
    }
  }

  function injectStylesOnce() {
    if (state.stylesInjected) return;
    state.stylesInjected = true;

    const style = document.createElement("style");
    style.textContent = `
      #artifactList {
        display: grid;
        gap: 10px;
      }

      .nova-artifact-item {
        display: block;
      }

      .nova-artifact-main {
        width: 100%;
        text-align: left;
        appearance: none;
        border: 1px solid rgba(130,158,222,0.12);
        background: rgba(255,255,255,0.03);
        color: var(--text);
        border-radius: 16px;
        padding: 12px;
        cursor: pointer;
        transition: border-color 140ms ease, transform 140ms ease, box-shadow 140ms ease, background 140ms ease;
      }

      .nova-artifact-main:hover {
        transform: translateY(-1px);
        border-color: rgba(110,168,255,0.24);
        box-shadow: 0 16px 28px rgba(0,0,0,0.18);
        background: rgba(255,255,255,0.045);
      }

      .nova-artifact-item.active .nova-artifact-main {
        border-color: rgba(110,168,255,0.34);
        background: rgba(110,168,255,0.09);
        box-shadow: 0 16px 32px rgba(0,0,0,0.20);
      }

      .nova-artifact-item-top {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 10px;
      }

      .nova-artifact-item-title {
        min-width: 0;
        font-weight: 800;
        font-size: 13px;
        line-height: 1.35;
        color: var(--text);
        word-break: break-word;
      }

      .nova-artifact-item-preview {
        margin-top: 8px;
        color: var(--muted);
        font-size: 12px;
        line-height: 1.5;
        word-break: break-word;
      }

      .nova-artifact-item-bottom {
        margin-top: 10px;
        color: var(--muted);
        font-size: 11px;
      }

      .nova-artifact-viewer {
        margin-top: 14px;
        border: 1px solid rgba(130,158,222,0.12);
        border-radius: 18px;
        background: rgba(255,255,255,0.03);
        overflow: hidden;
      }

      .nova-artifact-viewer-top {
        padding: 14px 14px 10px;
        border-bottom: 1px solid rgba(130,158,222,0.10);
        background: rgba(255,255,255,0.02);
      }

      .nova-artifact-viewer-title {
        font-size: 14px;
        font-weight: 900;
        line-height: 1.35;
        color: var(--text);
        word-break: break-word;
      }

      .nova-artifact-viewer-meta {
        margin-top: 6px;
        color: var(--muted);
        font-size: 11px;
        line-height: 1.45;
        word-break: break-word;
      }

      .nova-artifact-viewer-body {
        padding: 14px;
        display: grid;
        gap: 12px;
      }

      .nova-artifact-view-kind-row {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }

      .nova-artifact-empty-view {
        color: var(--muted);
        font-size: 12px;
        line-height: 1.5;
      }

      .nova-artifact-content {
        color: var(--text);
        font-size: 13px;
        line-height: 1.65;
        word-break: break-word;
      }

      .nova-artifact-content p {
        margin: 0 0 12px;
      }

      .nova-artifact-content p:last-child {
        margin-bottom: 0;
      }

      .nova-artifact-content ul,
      .nova-artifact-content ol {
        margin: 0 0 12px 18px;
        padding: 0;
      }

      .nova-artifact-content li {
        margin: 0 0 6px;
      }

      .nova-artifact-content code {
        padding: 1px 6px;
        border-radius: 8px;
        background: rgba(255,255,255,0.08);
        font-size: 12px;
      }

      .nova-artifact-content pre {
        margin: 0 0 12px;
        padding: 12px;
        border-radius: 14px;
        border: 1px solid rgba(130,158,222,0.10);
        background: rgba(7,14,28,0.88);
        color: #dbe6ff;
        font-size: 12px;
        line-height: 1.55;
        white-space: pre-wrap;
        word-break: break-word;
        overflow: auto;
      }

      .nova-artifact-content pre:last-child {
        margin-bottom: 0;
      }

      .nova-artifact-content a {
        color: var(--accent);
        text-decoration: none;
      }

      .nova-artifact-content strong {
        font-weight: 800;
      }

      .nova-artifact-meta-block {
        border: 1px solid rgba(130,158,222,0.10);
        border-radius: 14px;
        background: rgba(255,255,255,0.02);
        overflow: hidden;
      }

      .nova-artifact-meta-block summary {
        cursor: pointer;
        list-style: none;
        padding: 12px 14px;
        font-size: 12px;
        font-weight: 800;
        color: var(--muted);
      }

      .nova-artifact-meta-block summary::-webkit-details-marker {
        display: none;
      }

      .nova-artifact-meta-block pre {
        margin: 0;
        padding: 0 14px 14px;
        color: #cfdcff;
        font-size: 12px;
        line-height: 1.55;
        white-space: pre-wrap;
        word-break: break-word;
        overflow: auto;
      }
    `;

    document.head.appendChild(style);
  }

  function activeFilterValue() {
    const { filterSelect } = getEls();
    return safeText(filterSelect && filterSelect.value).trim().toLowerCase() || "all";
  }

  function passesKindFilter(item) {
    const value = activeFilterValue();
    if (!value || value === "all") return true;
    if (value === "pinned") return artifactPinned(item);
    if (value === "media") {
      const kind = artifactKind(item).toLowerCase();
      return kind.indexOf("image") !== -1 || kind.indexOf("video") !== -1 || kind.indexOf("audio") !== -1 || kind.indexOf("media") !== -1;
    }
    return artifactKind(item).toLowerCase() === value;
  }

  function applyFilter() {
    const needle = safeText(state.filterText).trim().toLowerCase();
    const sorted = sortArtifacts(state.artifacts);

    state.filtered = sorted.filter(function (item) {
      if (!passesKindFilter(item)) return false;
      if (!needle) return true;

      const haystack = [
        artifactTitle(item),
        artifactKind(item),
        artifactContent(item),
        artifactSessionId(item)
      ]
        .join(" ")
        .toLowerCase();

      return haystack.indexOf(needle) !== -1;
    });
  }

  function renderList() {
    const { list, empty } = getEls();
    if (!list) {
      log("missing artifact list element");
      return;
    }

    applyFilter();

    if (!state.filtered.length) {
      list.innerHTML = "";
      if (empty) {
        empty.style.display = "";
        empty.hidden = false;
        empty.textContent = "No artifacts found.";
      }
      return;
    }

    if (empty) {
      empty.style.display = "none";
      empty.hidden = true;
    }

    list.innerHTML = state.filtered
      .map((item) => {
        const id = artifactId(item);
        const active = id === state.activeArtifactId;
        const title = cleanTitle(artifactTitle(item));
        const kind = kindLabel(artifactKind(item));
        const preview = artifactPreview(item);
        const created = formatDate(artifactCreatedAt(item));

        return `
          <article class="nova-artifact-item${active ? " active" : ""}" data-artifact-id="${escapeHtml(id)}">
            <button
              type="button"
              class="nova-artifact-main"
              data-action="open-artifact"
              data-artifact-id="${escapeHtml(id)}"
            >
              <div class="nova-artifact-item-top">
                <span class="nova-artifact-item-title">${escapeHtml(title)}</span>
                <span class="nova-badge">${escapeHtml(kind)}</span>
              </div>
              <div class="nova-artifact-item-preview">${escapeHtml(preview)}</div>
              <div class="nova-artifact-item-bottom">${escapeHtml(created || "No timestamp")}</div>
            </button>
          </article>
        `;
      })
      .join("");

    bindListEvents();
  }

  function convertInlineMarkdown(text) {
    let value = escapeHtml(text);
    value = value.replace(/`([^`]+)`/g, "<code>$1</code>");
    value = value.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    value = value.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
    value = value.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function (_, label, href) {
      return '<a href="' + escapeHtml(href) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(label) + "</a>";
    });
    return value;
  }

  function renderMarkdownLike(text) {
    const raw = safeText(text).replace(/\r\n/g, "\n");
    if (!raw.trim()) return '<div class="nova-artifact-empty-view">No content.</div>';

    const lines = raw.split("\n");
    const html = [];
    let inList = false;
    let inCode = false;
    let codeLines = [];

    function closeList() {
      if (!inList) return;
      html.push("</ul>");
      inList = false;
    }

    function closeCode() {
      if (!inCode) return;
      html.push("<pre>" + escapeHtml(codeLines.join("\n")) + "</pre>");
      inCode = false;
      codeLines = [];
    }

    for (let i = 0; i < lines.length; i += 1) {
      const line = lines[i];
      const trimmed = line.trim();

      if (/^```/.test(trimmed)) {
        closeList();
        if (inCode) {
          closeCode();
        } else {
          inCode = true;
          codeLines = [];
        }
        continue;
      }

      if (inCode) {
        codeLines.push(line);
        continue;
      }

      if (!trimmed) {
        closeList();
        continue;
      }

      const imageOnly = trimmed.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
      if (imageOnly) {
        closeList();
        const alt = safeText(imageOnly[1]).trim() || "attachment";
        const src = safeText(imageOnly[2]).trim();
        html.push(
          '<p><strong>Image:</strong> <code>' +
            escapeHtml(alt) +
            "</code> <span style=\"color:var(--muted);\">(" +
            escapeHtml(src) +
            ")</span></p>"
        );
        continue;
      }

      const bullet = trimmed.match(/^[-*]\s+(.*)$/);
      if (bullet) {
        if (!inList) {
          html.push("<ul>");
          inList = true;
        }
        html.push("<li>" + convertInlineMarkdown(bullet[1]) + "</li>");
        continue;
      }

      closeList();

      if (/^#{1,6}\s+/.test(trimmed)) {
        const headingText = trimmed.replace(/^#{1,6}\s+/, "");
        html.push("<p><strong>" + convertInlineMarkdown(headingText) + "</strong></p>");
        continue;
      }

      html.push("<p>" + convertInlineMarkdown(trimmed) + "</p>");
    }

    closeList();
    closeCode();

    return html.join("");
  }

  function renderViewer() {
    const { viewer, viewerTitle, viewerMeta, viewerBody, copyBtn, openBtn, deleteBtn } = getEls();
    const item = state.activeArtifact || findArtifact(state.activeArtifactId);

    if (copyBtn) {
      copyBtn.disabled = !item;
      copyBtn.setAttribute("aria-disabled", item ? "false" : "true");
    }

    if (openBtn) {
      openBtn.disabled = !item;
      openBtn.setAttribute("aria-disabled", item ? "false" : "true");
    }

    if (deleteBtn) {
      deleteBtn.disabled = true;
      deleteBtn.setAttribute("aria-disabled", "true");
      deleteBtn.title = "Disabled in stable artifacts build";
    }

    if (!viewer && !viewerTitle && !viewerMeta && !viewerBody) {
      return;
    }

    if (!item) {
      if (viewerTitle) viewerTitle.textContent = "No artifact selected";
      if (viewerMeta) viewerMeta.textContent = "";
      if (viewerBody) {
        viewerBody.innerHTML = '<div class="nova-artifact-empty-view">Select an artifact to view it here.</div>';
      }
      if (viewer) viewer.setAttribute("data-empty", "true");
      return;
    }

    const title = cleanTitle(artifactTitle(item));
    const kind = kindLabel(artifactKind(item));
    const sessionId = artifactSessionId(item);
    const created = formatDate(artifactCreatedAt(item));
    const updated = formatDate(artifactUpdatedAt(item));
    const meta = artifactMeta(item);
    const content = artifactContent(item);

    if (viewerTitle) viewerTitle.textContent = title;

    if (viewerMeta) {
      const parts = [];
      parts.push(kind);
      if (created) parts.push(created);
      if (updated && updated !== created) parts.push("updated " + updated);
      if (artifactPinned(item)) parts.push("Pinned");
      if (sessionId) parts.push("session linked");
      viewerMeta.textContent = parts.join(" • ");
    }

    if (viewerBody) {
      let metaBlock = "";
      if (meta) {
        metaBlock = `
          <details class="nova-artifact-meta-block">
            <summary>Meta</summary>
            <pre>${escapeHtml(JSON.stringify(meta, null, 2))}</pre>
          </details>
        `;
      }

      viewerBody.innerHTML = `
        <div class="nova-artifact-view-body">
          <div class="nova-artifact-view-kind-row">
            <span class="nova-badge">${escapeHtml(kind)}</span>
          </div>
          <div class="nova-artifact-content">${renderMarkdownLike(content || "")}</div>
          ${metaBlock}
        </div>
      `;
    }

    if (viewer) viewer.setAttribute("data-empty", "false");
  }

  function render() {
    renderList();
    renderViewer();
  }

  function renderSoon() {
    if (state.refreshTimer) {
      clearTimeout(state.refreshTimer);
      state.refreshTimer = null;
    }

    state.refreshTimer = window.setTimeout(function () {
      state.refreshTimer = null;
      render();
    }, 40);
  }

  async function loadArtifacts(reason) {
    if (state.loading) return;
    state.loading = true;

    try {
      const payload = await apiFetch(API.list, {
        method: "GET",
        headers: { Accept: "application/json" }
      });

      state.artifacts = extractArtifacts(payload);

      if (state.activeArtifactId) {
        const stillExists = findArtifact(state.activeArtifactId);
        if (!stillExists) {
          state.activeArtifactId = "";
          state.activeArtifact = null;
        } else if (!state.activeArtifact || artifactId(state.activeArtifact) !== state.activeArtifactId) {
          state.activeArtifact = stillExists;
        }
      }

      render();

      dispatch("nova:artifacts-refreshed", {
        reason: reason || "manual",
        artifacts: state.artifacts.slice(),
        activeArtifactId: state.activeArtifactId
      });

      log("artifacts loaded", {
        reason: reason || "manual",
        count: state.artifacts.length,
        activeArtifactId: state.activeArtifactId
      });
    } catch (error) {
      console.error(LOG_PREFIX, "loadArtifacts failed", error);
    } finally {
      state.loading = false;
    }
  }

  async function openArtifact(id) {
    const wanted = safeText(id).trim();
    if (!wanted) return null;

    state.activeArtifactId = wanted;
    renderSoon();

    try {
      const payload = await apiFetch(API.read(wanted), {
        method: "GET",
        headers: { Accept: "application/json" }
      });

      const item = payload && payload.artifact ? payload.artifact : payload;
      if (!item || !artifactId(item)) {
        throw new Error("Artifact payload missing artifact");
      }

      state.activeArtifactId = artifactId(item);
      state.activeArtifact = item;
      render();

      dispatch("nova:artifact-opened", {
        artifactId: state.activeArtifactId,
        artifact: item
      });

      log("artifact opened", {
        artifactId: state.activeArtifactId,
        kind: artifactKind(item)
      });

      return item;
    } catch (error) {
      console.error(LOG_PREFIX, "openArtifact failed", error);
      const fallback = findArtifact(wanted);
      if (fallback) {
        state.activeArtifact = fallback;
        renderSoon();
      }
      return null;
    }
  }

  async function copyActiveArtifact() {
    const item = state.activeArtifact || findArtifact(state.activeArtifactId);
    if (!item) return;

    const text = artifactContent(item);
    if (!text) return;

    try {
      await navigator.clipboard.writeText(text);
      log("artifact copied", { artifactId: artifactId(item) });
    } catch (error) {
      console.error(LOG_PREFIX, "copy failed", error);
    }
  }

  function bindListEvents() {
    const { list } = getEls();
    if (!list) return;

    list.querySelectorAll("[data-action='open-artifact']").forEach((button) => {
      if (button.dataset.novaBound === "1") return;
      button.dataset.novaBound = "1";

      button.addEventListener("click", function () {
        const id = safeText(button.getAttribute("data-artifact-id")).trim();
        if (!id) return;

        openArtifact(id).catch(function (error) {
          console.error(LOG_PREFIX, "artifact click failed", error);
        });
      });
    });
  }

  function wireTopControls() {
    const { refreshBtn, searchInput, filterSelect, copyBtn, openBtn, deleteBtn } = getEls();

    if (refreshBtn && refreshBtn.dataset.novaBound !== "1") {
      refreshBtn.dataset.novaBound = "1";
      refreshBtn.addEventListener("click", function () {
        loadArtifacts("manual-refresh").catch(function (error) {
          console.error(LOG_PREFIX, "manual refresh failed", error);
        });
      });
    }

    if (searchInput && searchInput.dataset.novaBound !== "1") {
      searchInput.dataset.novaBound = "1";
      searchInput.addEventListener("input", function () {
        state.filterText = safeText(searchInput.value);
        renderSoon();
      });
    }

    if (filterSelect && filterSelect.dataset.novaBound !== "1") {
      filterSelect.dataset.novaBound = "1";
      filterSelect.addEventListener("change", function () {
        renderSoon();
      });
    }

    if (copyBtn && copyBtn.dataset.novaBound !== "1") {
      copyBtn.dataset.novaBound = "1";
      copyBtn.addEventListener("click", function (event) {
        event.preventDefault();
        copyActiveArtifact().catch(function (error) {
          console.error(LOG_PREFIX, "copy active failed", error);
        });
      });
    }

    if (openBtn && openBtn.dataset.novaBound !== "1") {
      openBtn.dataset.novaBound = "1";
      openBtn.addEventListener("click", function (event) {
        event.preventDefault();
        if (!state.activeArtifactId) return;
        openArtifact(state.activeArtifactId).catch(function (error) {
          console.error(LOG_PREFIX, "reopen active failed", error);
        });
      });
    }

    if (deleteBtn && deleteBtn.dataset.novaBound !== "1") {
      deleteBtn.dataset.novaBound = "1";
      deleteBtn.addEventListener("click", function (event) {
        event.preventDefault();
      });
    }
  }

  function wireEvents() {
    if (state.eventsBound) return;
    state.eventsBound = true;

    document.addEventListener("nova:message-sent", function () {
      loadArtifacts("message-sent");
    });

    document.addEventListener("nova:artifact-saved", function () {
      loadArtifacts("artifact-saved");
    });

    document.addEventListener("nova:sessions-refreshed", function () {
      renderSoon();
    });
  }

  function boot() {
    if (state.booted) return;
    state.booted = true;

    injectStylesOnce();
    wireTopControls();
    wireEvents();
    loadArtifacts("boot");

    log("booted");
  }

  window.NovaArtifacts = {
    refresh() {
      return loadArtifacts("api-refresh");
    },
    open(id) {
      return openArtifact(id);
    },
    getState() {
      return {
        artifacts: state.artifacts.slice(),
        activeArtifactId: state.activeArtifactId,
        activeArtifact: state.activeArtifact
      };
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();