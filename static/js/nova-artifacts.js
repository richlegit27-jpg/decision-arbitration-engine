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
    refreshTimer: null
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
        document.querySelector("[data-action='refresh-artifacts']") ||
        null,
      searchInput:
        document.querySelector("#artifactSearchInput") ||
        document.querySelector("#artifactsSearchInput") ||
        document.querySelector("[data-role='artifact-search']") ||
        null,
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

  function extractArtifacts(payload) {
    if (!payload) return [];
    if (Array.isArray(payload.artifacts)) return payload.artifacts;
    if (payload.data && Array.isArray(payload.data.artifacts)) return payload.data.artifacts;
    if (payload.state && Array.isArray(payload.state.artifacts)) return payload.state.artifacts;
    if (Array.isArray(payload.items)) return payload.items;
    if (Array.isArray(payload)) return payload;
    return [];
  }

  function artifactPreview(item) {
    const content = artifactContent(item).trim().replace(/\s+/g, " ");
    if (!content) return "No content";
    if (content.length <= 140) return content;
    return content.slice(0, 140).trim() + "…";
  }

  function sortArtifacts(items) {
    return (Array.isArray(items) ? items : []).slice().sort((a, b) => {
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

  function applyFilter() {
    const needle = safeText(state.filterText).trim().toLowerCase();
    const sorted = sortArtifacts(state.artifacts);

    if (!needle) {
      state.filtered = sorted;
      return;
    }

    state.filtered = sorted.filter((item) => {
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
      if (empty) empty.hidden = false;
      return;
    }

    if (empty) empty.hidden = true;

    list.innerHTML = state.filtered
      .map((item) => {
        const id = artifactId(item);
        const active = id === state.activeArtifactId;
        const title = artifactTitle(item);
        const kind = artifactKind(item);
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
        viewerBody.innerHTML = `
          <div class="nova-artifact-empty-view">
            Select an artifact to view it here.
          </div>
        `;
      }
      if (viewer) viewer.setAttribute("data-empty", "true");
      return;
    }

    const title = artifactTitle(item);
    const kind = artifactKind(item);
    const sessionId = artifactSessionId(item);
    const created = formatDate(artifactCreatedAt(item));
    const updated = formatDate(artifactUpdatedAt(item));
    const meta = artifactMeta(item);
    const content = artifactContent(item);

    if (viewerTitle) viewerTitle.textContent = title;

    if (viewerMeta) {
      const parts = [];
      parts.push(kind);
      if (sessionId) parts.push("session " + sessionId);
      if (created) parts.push("created " + created);
      if (updated && updated !== created) parts.push("updated " + updated);
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
          <pre class="nova-artifact-view-content">${escapeHtml(content || "")}</pre>
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
    const { refreshBtn, searchInput, copyBtn, openBtn, deleteBtn } = getEls();

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