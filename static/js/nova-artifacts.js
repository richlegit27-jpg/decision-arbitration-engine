(function () {
  "use strict";

  const LOG = "[NovaArtifacts]";
  const API = {
    list: "/api/artifacts",
    read(id) {
      return "/api/artifacts/" + encodeURIComponent(id);
    },
    delete: "/api/artifacts/delete",
    pin: "/api/artifacts/pin"
  };

  const state = {
    booted: false,
    artifacts: [],
    filtered: [],
    activeArtifactId: "",
    activeArtifact: null,
    activeSessionId: "",
    filterText: "",
    showPinnedOnly: false,
    showCurrentSessionOnly: false,
    lastListMarkup: "",
    lastViewerMarkup: "",
    lastComposerArtifactSignature: "",
    isLoadingList: false,
    isOpeningArtifact: false
  };

  function log() {
    try { console.log(LOG, ...arguments); } catch (_) {}
  }

  function error() {
    try { console.error(LOG, ...arguments); } catch (_) {}
  }

  function $(id) {
    return document.getElementById(id);
  }

  function safe(value) {
    return value == null ? "" : String(value);
  }

  function esc(value) {
    return safe(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function pretty(value) {
    if (value == null || value === "") return "—";
    if (typeof value === "string") return value;
    try {
      return JSON.stringify(value, null, 2);
    } catch (_) {
      return safe(value);
    }
  }

  function setComposerStatus(text) {
    const el = $("composerStatus");
    if (el) el.textContent = safe(text || "");
  }

  function dispatch(name, detail) {
    try {
      window.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
    } catch (_) {}
  }

  function artifactId(item) {
    return safe(item && (item.id || item.artifact_id || item._id || ""));
  }

  function artifactSessionId(item) {
    return safe(item && (item.session_id || item.sessionId || item.chat_session_id || ""));
  }

  function artifactKind(item) {
    return safe(item && (item.kind || item.type || item.artifact_kind || "artifact"));
  }

  function artifactTitle(item) {
    return safe(item && (
      item.title ||
      item.name ||
      item.label ||
      item.filename ||
      item.kind ||
      "Untitled artifact"
    ));
  }

  function artifactContent(item) {
    return safe(item && (
      item.content ||
      item.text ||
      item.body ||
      item.preview ||
      item.summary ||
      item.description ||
      ""
    ));
  }

  function artifactPinned(item) {
    return !!(item && item.pinned);
  }

  function artifactMeta(item) {
    if (!item || typeof item !== "object") return {};
    return item.meta && typeof item.meta === "object" ? item.meta : {};
  }

  function formatTime(value) {
    const raw = safe(value);
    if (!raw) return "";
    try {
      const d = new Date(raw);
      if (Number.isNaN(d.getTime())) return raw;
      return d.toLocaleString();
    } catch (_) {
      return raw;
    }
  }

  function summarizeText(value, limit) {
    const text = safe(value).trim();
    const max = typeof limit === "number" ? limit : 180;
    if (!text) return "";
    if (text.length <= max) return text;
    return text.slice(0, max) + "…";
  }

  function isImageUrl(value) {
    const text = safe(value);
    return !!text && (
      /^https?:\/\//i.test(text) ||
      text.startsWith("/uploads/") ||
      text.startsWith("uploads/")
    ) && /\.(png|jpg|jpeg|gif|webp|bmp|svg)(\?.*)?$/i.test(text);
  }

  function contentHtml(text) {
    const raw = safe(text);
    if (!raw) {
      return '<div class="nova-artifact-empty">No content in this artifact yet.</div>';
    }

    if (isImageUrl(raw)) {
      return `
        <div class="nova-artifact-image-wrap">
          <img class="nova-artifact-image" src="${esc(raw)}" alt="Artifact image" />
          <div class="nova-artifact-image-actions">
            <a class="nova-subtle-btn" href="${esc(raw)}" target="_blank" rel="noopener noreferrer">Open image</a>
          </div>
        </div>
      `;
    }

    return `<pre class="nova-artifact-content-pre">${esc(raw)}</pre>`;
  }

  function sortArtifacts(items) {
    return asArray(items).slice().sort(function (a, b) {
      const ap = artifactPinned(a) ? 1 : 0;
      const bp = artifactPinned(b) ? 1 : 0;
      if (ap !== bp) return bp - ap;

      const at = safe(a && (a.updated_at || a.created_at || ""));
      const bt = safe(b && (b.updated_at || b.created_at || ""));
      return bt.localeCompare(at);
    });
  }

  function ensureMountStructure() {
    const mount = $("artifactsMount");
    if (!mount) return null;

    if ($("artifactListPane") && $("artifactViewerPane") && $("artifactSearchInput")) {
      return mount;
    }

    mount.innerHTML = `
      <div class="nova-artifact-workspace">
        <div class="nova-artifact-list-pane">
          <div class="nova-artifact-toolbar">
            <input
              id="artifactSearchInput"
              class="nova-artifact-search"
              type="text"
              placeholder="Search artifacts"
              aria-label="Search artifacts"
            />
            <div class="nova-artifact-toolbar-actions">
              <button id="artifactPinnedFilterBtn" class="nova-subtle-btn" type="button">Pinned</button>
              <button id="artifactSessionFilterBtn" class="nova-subtle-btn" type="button">This Chat</button>
              <button id="artifactRefreshBtn" class="nova-subtle-btn" type="button">Refresh</button>
            </div>
          </div>
          <div id="artifactFilterSummary" class="nova-artifact-filter-summary"></div>
          <div id="artifactListPane" class="nova-artifact-list"></div>
        </div>
        <div id="artifactViewerPane" class="nova-artifact-viewer-pane">
          <div class="nova-artifact-viewer-empty">Click an artifact to inspect content, meta, and debug.</div>
        </div>
      </div>
    `;
    return mount;
  }

  function renderFilterSummary() {
    const el = $("artifactFilterSummary");
    if (!el) return;
    const parts = [];
    parts.push(`${state.filtered.length} shown`);
    parts.push(`${state.artifacts.length} total`);
    if (state.showPinnedOnly) parts.push("pinned");
    if (state.showCurrentSessionOnly) parts.push("this chat");
    if (state.filterText) parts.push(`search: ${state.filterText}`);
    el.textContent = parts.join(" • ");

    const pinnedBtn = $("artifactPinnedFilterBtn");
    const sessionBtn = $("artifactSessionFilterBtn");
    if (pinnedBtn) pinnedBtn.classList.toggle("is-active", !!state.showPinnedOnly);
    if (sessionBtn) sessionBtn.classList.toggle("is-active", !!state.showCurrentSessionOnly);
  }

  function cardHtml(item) {
    const id = artifactId(item);
    const active = id && id === state.activeArtifactId ? " active" : "";
    return `
      <button class="nova-artifact-card${active}" type="button" data-artifact-id="${esc(id)}">
        <div class="nova-artifact-card-top">
          <span class="nova-artifact-kind">${esc(artifactKind(item))}</span>
          <div class="nova-artifact-card-top-right">
            ${artifactPinned(item) ? `<span class="nova-artifact-session-chip is-pinned">Pinned</span>` : ``}
            <span class="nova-artifact-time">${esc(formatTime(item.updated_at || item.created_at || ""))}</span>
          </div>
        </div>
        <div class="nova-artifact-card-title">${esc(artifactTitle(item))}</div>
        ${artifactContent(item) ? `<div class="nova-artifact-card-preview">${esc(summarizeText(artifactContent(item), 180))}</div>` : ``}
        <div class="nova-artifact-card-bottom">
          <span class="nova-artifact-session-chip">${esc(artifactSessionId(item) || "no session")}</span>
        </div>
      </button>
    `;
  }

  function viewerHtml(item) {
    if (!item) {
      return `<div class="nova-artifact-viewer-empty">Click an artifact to inspect content, meta, and debug.</div>`;
    }

    const id = artifactId(item);
    const kind = artifactKind(item);
    const title = artifactTitle(item);
    const sessionId = artifactSessionId(item);
    const pinned = artifactPinned(item);
    const meta = artifactMeta(item);
    const rawMeta = {
      id: item.id,
      kind: item.kind,
      pinned: !!item.pinned,
      session_id: item.session_id,
      title: item.title,
      created_at: item.created_at,
      updated_at: item.updated_at,
      meta: item.meta || {},
      web: item.web || null,
      debug: item.debug || null,
      extra: item.extra || null
    };

    return `
      <div class="nova-artifact-viewer">
        <div class="nova-artifact-viewer-header">
          <div class="nova-artifact-viewer-title-wrap">
            <div class="nova-artifact-viewer-topline">
              <span class="nova-artifact-kind">${esc(kind)}</span>
              ${pinned ? `<span class="nova-artifact-session-chip is-pinned">Pinned</span>` : ``}
              ${id ? `<span class="nova-artifact-id">id ${esc(id)}</span>` : ``}
            </div>
            <div class="nova-artifact-viewer-title">${esc(title)}</div>
            <div class="nova-artifact-viewer-meta-line">
              ${item.created_at ? `<span>Created: ${esc(formatTime(item.created_at))}</span>` : ``}
              ${item.updated_at ? `<span>Updated: ${esc(formatTime(item.updated_at))}</span>` : ``}
              ${sessionId ? `<span>Session: ${esc(sessionId)}</span>` : ``}
            </div>
          </div>

          <div class="nova-artifact-viewer-actions">
            ${sessionId ? `<button id="artifactJumpSessionBtn" class="nova-subtle-btn" type="button" data-session-id="${esc(sessionId)}">Jump to session</button>` : ``}
            <button id="artifactPinBtn" class="nova-subtle-btn" type="button">${pinned ? "Unpin" : "Pin"}</button>
            <button id="artifactRefreshMetaBtn" class="nova-subtle-btn" type="button">Refresh meta</button>
            <button id="artifactDeleteBtn" class="nova-subtle-btn danger" type="button">Delete</button>
            <button id="artifactCopyBtn" class="nova-subtle-btn" type="button">Copy content</button>
            <button id="artifactCopyMetaBtn" class="nova-subtle-btn" type="button">Copy meta</button>
          </div>
        </div>

        <div class="nova-artifact-viewer-grid">
          <div class="nova-artifact-viewer-block nova-artifact-viewer-block-content">
            <div class="nova-artifact-viewer-block-title">Content</div>
            <div class="nova-artifact-viewer-content">${contentHtml(artifactContent(item))}</div>
          </div>

          <div class="nova-artifact-viewer-block">
            <div class="nova-artifact-viewer-block-title">Backend meta</div>
            <pre class="nova-artifact-meta-pre">${esc(pretty(meta))}</pre>
          </div>

          <div class="nova-artifact-viewer-block">
            <div class="nova-artifact-viewer-block-title">Raw meta</div>
            <pre class="nova-artifact-meta-pre">${esc(pretty(rawMeta))}</pre>
          </div>
        </div>
      </div>
    `;
  }

  function applyFilter() {
    const query = safe(state.filterText).trim().toLowerCase();
    const currentSessionId = safe(state.activeSessionId);

    state.filtered = sortArtifacts(state.artifacts).filter(function (item) {
      if (state.showPinnedOnly && !artifactPinned(item)) return false;
      if (state.showCurrentSessionOnly && currentSessionId && artifactSessionId(item) !== currentSessionId) return false;

      if (!query) return true;

      const haystack = [
        artifactTitle(item),
        artifactKind(item),
        artifactContent(item),
        pretty(artifactMeta(item))
      ].join(" ").toLowerCase();

      return haystack.indexOf(query) >= 0;
    });
  }

  function renderList() {
    renderFilterSummary();

    const pane = $("artifactListPane");
    if (!pane) return;

    const markup = state.filtered.length
      ? state.filtered.map(cardHtml).join("")
      : `<div class="nova-artifact-empty">No artifacts match your filters.</div>`;

    if (markup !== state.lastListMarkup) {
      pane.innerHTML = markup;
      state.lastListMarkup = markup;
    }

    dispatch("nova:artifact-count-changed", {
      count: state.artifacts.length,
      filtered: state.filtered.length
    });
  }

  function renderViewer() {
    const pane = $("artifactViewerPane");
    if (!pane) return;

    const markup = viewerHtml(state.activeArtifact);
    if (markup !== state.lastViewerMarkup) {
      pane.innerHTML = markup;
      state.lastViewerMarkup = markup;
    }
  }

  function setArtifacts(nextArtifacts) {
    state.artifacts = sortArtifacts(nextArtifacts);
    applyFilter();

    if (state.activeArtifactId) {
      const fresh = state.artifacts.find(function (item) {
        return artifactId(item) === state.activeArtifactId;
      });
      if (fresh) state.activeArtifact = fresh;
    }

    renderList();
    renderViewer();
  }

  async function readJson(res) {
    try {
      return await res.json();
    } catch (_) {
      return null;
    }
  }

  async function postJson(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {})
    });
    const data = await readJson(res);
    if (!res.ok) {
      throw new Error(safe(data && (data.error || data.message)) || `Request failed (${res.status})`);
    }
    return data || {};
  }

  async function loadArtifacts(options) {
    const opts = options || {};
    if (state.isLoadingList) return;
    state.isLoadingList = true;

    if (!opts.silent) setComposerStatus("Loading artifacts…");

    try {
      const res = await fetch(API.list, { method: "GET" });
      const data = await readJson(res);

      if (!res.ok) {
        throw new Error(safe(data && (data.error || data.message)) || "Failed to load artifacts");
      }

      const items = data && (data.artifacts || data.items || data.results || data);
      setArtifacts(asArray(items));

      if (!opts.silent) setComposerStatus(`Artifacts loaded (${state.artifacts.length})`);
    } catch (e) {
      error("loadArtifacts failed", e);
      if (!opts.silent) setComposerStatus(safe(e.message || "Artifact load failed."));
    } finally {
      state.isLoadingList = false;
    }
  }

  async function openArtifact(id, options) {
    const opts = options || {};
    const wanted = safe(id);
    if (!wanted) return;

    if (!opts.force && state.activeArtifactId === wanted && state.activeArtifact) {
      renderViewer();
      return;
    }

    if (state.isOpeningArtifact) return;
    state.isOpeningArtifact = true;

    if (!opts.silent) setComposerStatus("Opening artifact…");

    try {
      const res = await fetch(API.read(wanted), { method: "GET" });
      const data = await readJson(res);

      if (!res.ok) {
        throw new Error(safe(data && (data.error || data.message)) || "Failed to load artifact");
      }

      const item = data && data.artifact ? data.artifact : data;
      state.activeArtifactId = artifactId(item);
      state.activeArtifact = item;

      const existingIndex = state.artifacts.findIndex(function (a) {
        return artifactId(a) === state.activeArtifactId;
      });

      if (existingIndex >= 0) {
        state.artifacts[existingIndex] = item;
      } else {
        state.artifacts.unshift(item);
      }

      applyFilter();
      state.lastListMarkup = "";
      renderList();
      renderViewer();

      dispatch("nova:artifact-opened", {
        artifact_id: state.activeArtifactId,
        artifact: item,
        session_id: artifactSessionId(item)
      });

      if (!opts.silent) setComposerStatus("Artifact opened");
    } catch (e) {
      error("openArtifact failed", e);
      if (!opts.silent) setComposerStatus(safe(e.message || "Artifact open failed."));
    } finally {
      state.isOpeningArtifact = false;
    }
  }

  async function togglePinActiveArtifact() {
    if (!state.activeArtifact) return;
    try {
      setComposerStatus("Saving pin…");
      await postJson(API.pin, { artifact_id: artifactId(state.activeArtifact) });
      await loadArtifacts({ silent: true });
      await openArtifact(artifactId(state.activeArtifact), { silent: true, force: true });
      setComposerStatus("Pin saved.");
    } catch (e) {
      setComposerStatus(safe(e.message || "Pin failed."));
    }
  }

  async function deleteActiveArtifact() {
    if (!state.activeArtifact) return;
    if (!window.confirm("Delete this artifact?")) return;

    try {
      setComposerStatus("Deleting artifact…");
      const id = artifactId(state.activeArtifact);
      const result = await postJson(API.delete, { artifact_id: id });

      state.activeArtifact = null;
      state.activeArtifactId = "";
      state.lastViewerMarkup = "";
      await loadArtifacts({ silent: true });

      const nextId = safe(result && result.next_artifact_id);
      if (nextId) {
        await openArtifact(nextId, { silent: true, force: true });
      } else {
        renderViewer();
      }

      setComposerStatus("Artifact deleted.");
    } catch (e) {
      setComposerStatus(safe(e.message || "Delete failed."));
    }
  }

  async function refreshActiveArtifact() {
    if (!state.activeArtifactId) return;
    await openArtifact(state.activeArtifactId, { silent: true, force: true });
    setComposerStatus("Artifact refreshed.");
  }

  function copyText(text, okText) {
    navigator.clipboard.writeText(safe(text || ""))
      .then(function () {
        setComposerStatus(okText || "Copied.");
      })
      .catch(function (e) {
        setComposerStatus(safe(e.message || "Copy failed."));
      });
  }

  function bindMountEvents() {
    const mount = $("artifactsMount");
    if (!mount) return;

    mount.addEventListener("click", function (event) {
      const target = event.target;
      if (!target) return;

      const card = target.closest("[data-artifact-id]");
      if (card) {
        openArtifact(card.getAttribute("data-artifact-id"));
        return;
      }

      const refreshBtn = target.closest("#artifactRefreshBtn");
      if (refreshBtn) {
        loadArtifacts();
        return;
      }

      const pinnedBtn = target.closest("#artifactPinnedFilterBtn");
      if (pinnedBtn) {
        state.showPinnedOnly = !state.showPinnedOnly;
        state.lastListMarkup = "";
        applyFilter();
        renderList();
        return;
      }

      const sessionBtn = target.closest("#artifactSessionFilterBtn");
      if (sessionBtn) {
        state.showCurrentSessionOnly = !state.showCurrentSessionOnly;
        state.lastListMarkup = "";
        applyFilter();
        renderList();
        return;
      }

      const pinBtn = target.closest("#artifactPinBtn");
      if (pinBtn) {
        togglePinActiveArtifact();
        return;
      }

      const deleteBtn = target.closest("#artifactDeleteBtn");
      if (deleteBtn) {
        deleteActiveArtifact();
        return;
      }

      const refreshMetaBtn = target.closest("#artifactRefreshMetaBtn");
      if (refreshMetaBtn) {
        refreshActiveArtifact();
        return;
      }

      const jumpBtn = target.closest("#artifactJumpSessionBtn");
      if (jumpBtn) {
        dispatch("nova:jump-to-session", {
          session_id: safe(jumpBtn.getAttribute("data-session-id")),
          source: "artifact-viewer"
        });
        return;
      }

      const copyBtn = target.closest("#artifactCopyBtn");
      if (copyBtn) {
        copyText(artifactContent(state.activeArtifact), "Artifact content copied.");
        return;
      }

      const copyMetaBtn = target.closest("#artifactCopyMetaBtn");
      if (copyMetaBtn) {
        copyText(pretty(state.activeArtifact), "Artifact meta copied.");
      }
    });

    mount.addEventListener("input", function (event) {
      const search = event.target.closest("#artifactSearchInput");
      if (!search) return;
      state.filterText = safe(search.value);
      state.lastListMarkup = "";
      applyFilter();
      renderList();
    });
  }

  function bindEvents() {
    window.addEventListener("nova:composer-state", function (event) {
      const detail = event && event.detail ? event.detail : {};
      const sessionId = safe(detail.session_id || detail.sessionId || "");
      const artifacts = asArray(detail.artifacts);

      state.activeSessionId = sessionId;

      const signature = JSON.stringify({
        sessionId: sessionId,
        artifacts: artifacts.map(function (item) {
          return {
            id: artifactId(item),
            title: artifactTitle(item),
            kind: artifactKind(item),
            pinned: artifactPinned(item),
            updated_at: safe(item && (item.updated_at || item.created_at || "")),
            session_id: artifactSessionId(item)
          };
        })
      });

      if (signature === state.lastComposerArtifactSignature) return;
      state.lastComposerArtifactSignature = signature;

      setArtifacts(artifacts);
    });

    window.addEventListener("nova:artifact-opened", function (event) {
      const detail = event && event.detail ? event.detail : {};
      if (!detail.artifact || typeof detail.artifact !== "object") return;
      state.activeArtifactId = safe(detail.artifact_id || artifactId(detail.artifact));
      state.activeArtifact = detail.artifact;
      renderViewer();
    });
  }

  async function boot() {
    if (state.booted) return;
    state.booted = true;

    ensureMountStructure();
    bindMountEvents();
    bindEvents();
    await loadArtifacts({ silent: false });

    log("boot complete", {
      artifacts: state.artifacts.length
    });
  }

  window.NovaArtifacts = {
    state: state,
    boot: boot,
    loadArtifacts: loadArtifacts,
    openArtifact: openArtifact
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();