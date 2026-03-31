(function () {
  "use strict";

  const API = {
    list: "/api/artifacts",
    read(id) {
      return `/api/artifacts/${encodeURIComponent(id)}`;
    },
    save: "/api/artifacts/save",
    cleanJunk: "/api/artifacts/clean-junk",
  };

  const state = {
    artifacts: [],
    filtered: [],
    activeArtifactId: "",
    activeArtifact: null,
    loading: false,
  };

  const els = {
    panel: null,
    list: null,
    viewer: null,
    refreshBtn: null,
    openSessionBtn: null,
    copyBtn: null,
    cleanJunkBtn: null,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function safeJsonParse(text) {
    try {
      return JSON.parse(text);
    } catch (_err) {
      return null;
    }
  }

  async function api(path, options) {
    const response = await fetch(path, {
      method: (options && options.method) || "GET",
      headers: {
        "Content-Type": "application/json",
        ...((options && options.headers) || {}),
      },
      body: options && options.body ? JSON.stringify(options.body) : undefined,
    });

    const rawText = await response.text();
    const data = safeJsonParse(rawText);

    if (!response.ok) {
      const error = new Error(
        (data && (data.message || data.error)) || `Request failed: ${response.status}`
      );
      error.status = response.status;
      error.data = data;
      error.rawText = rawText;
      throw error;
    }

    if (!data || typeof data !== "object") {
      const error = new Error("Server returned non-JSON response.");
      error.status = response.status;
      error.rawText = rawText;
      throw error;
    }

    return data;
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function truncate(value, max) {
    const text = String(value || "");
    return text.length > max ? `${text.slice(0, max - 1)}…` : text;
  }

  function formatDateTime(value) {
    if (!value) return "";
    try {
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return String(value);
      return d.toLocaleString([], {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_err) {
      return String(value);
    }
  }

  function getStatusApi() {
    return window.NovaSessionStatus || null;
  }

  function statusPending(text) {
    const api = getStatusApi();
    if (api && typeof api.pending === "function") api.pending(text);
  }

  function statusSuccess(text) {
    const api = getStatusApi();
    if (api && typeof api.success === "function") api.success(text);
  }

  function statusError(text) {
    const api = getStatusApi();
    if (api && typeof api.error === "function") api.error(text);
  }

  function ensureElements() {
    els.panel = byId("artifactsPanel");
    els.list = byId("artifactList");
    els.viewer = byId("artifactViewer");
    els.refreshBtn = byId("artifactRefreshBtn");
    els.openSessionBtn = byId("artifactOpenSessionBtn");
    els.copyBtn = byId("artifactCopyBtn");
    els.cleanJunkBtn = byId("artifactCleanJunkBtn");
  }

  function setLoading(isLoading) {
    state.loading = Boolean(isLoading);

    if (els.refreshBtn) els.refreshBtn.disabled = state.loading;
    if (els.cleanJunkBtn) els.cleanJunkBtn.disabled = state.loading;

    const blockButtons = !state.activeArtifact || state.loading;
    if (els.openSessionBtn) els.openSessionBtn.disabled = blockButtons;
    if (els.copyBtn) els.copyBtn.disabled = blockButtons;
  }

  function normalizeArtifact(raw) {
    const artifact = raw && typeof raw === "object" ? raw : {};
    return {
      id: String(artifact.id || ""),
      title: String(artifact.title || "Untitled Artifact"),
      kind: String(artifact.kind || "artifact"),
      content: String(artifact.content || ""),
      session_id: String(artifact.session_id || ""),
      message_id: String(artifact.message_id || ""),
      created_at: artifact.created_at || "",
      updated_at: artifact.updated_at || "",
      meta: artifact.meta && typeof artifact.meta === "object" ? artifact.meta : {},
    };
  }

  function sortArtifacts(items) {
    return [...items].sort(function (a, b) {
      const aTime = String(a.updated_at || a.created_at || "");
      const bTime = String(b.updated_at || b.created_at || "");
      return aTime < bTime ? 1 : aTime > bTime ? -1 : 0;
    });
  }

  function getActiveArtifact() {
    if (state.activeArtifact && state.activeArtifact.id === state.activeArtifactId) {
      return state.activeArtifact;
    }
    return state.artifacts.find(function (item) {
      return item.id === state.activeArtifactId;
    }) || null;
  }

  function setActiveArtifact(artifact) {
    const normalized = artifact ? normalizeArtifact(artifact) : null;
    state.activeArtifact = normalized;
    state.activeArtifactId = normalized ? normalized.id : "";
    renderList();
    renderViewer();
    setLoading(state.loading);
  }

  function renderList() {
    if (!els.list) return;

    els.list.innerHTML = "";

    if (!state.filtered.length) {
      els.list.innerHTML = `
        <div class="nova-empty-state">
          No artifacts yet.
        </div>
      `;
      return;
    }

    state.filtered.forEach(function (artifact) {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "nova-artifact-card";
      if (artifact.id === state.activeArtifactId) {
        card.classList.add("is-active");
      }

      const created = formatDateTime(artifact.created_at);
      const updated = formatDateTime(artifact.updated_at);
      const hasSession = Boolean(artifact.session_id);

      card.innerHTML = `
        <div class="nova-meta-row">
          <span class="nova-badge">${escapeHtml(artifact.kind)}</span>
          ${hasSession ? `<span class="nova-badge">session</span>` : ""}
        </div>
        <div><strong>${escapeHtml(artifact.title || "Untitled Artifact")}</strong></div>
        <div class="nova-kv">
          <div>${escapeHtml(truncate(artifact.content || "No content.", 140))}</div>
          ${created ? `<div>Created: ${escapeHtml(created)}</div>` : ""}
          ${updated ? `<div>Updated: ${escapeHtml(updated)}</div>` : ""}
        </div>
      `;

      card.addEventListener("click", function () {
        openArtifact(artifact.id);
      });

      els.list.appendChild(card);
    });
  }

  function renderViewer() {
    if (!els.viewer) return;

    const artifact = getActiveArtifact();

    if (!artifact) {
      els.viewer.innerHTML = `
        <div class="nova-empty-state">
          No artifact selected yet.
        </div>
      `;
      return;
    }

    const debugMeta =
      artifact.meta &&
      typeof artifact.meta === "object" &&
      artifact.meta.debug &&
      typeof artifact.meta.debug === "object"
        ? artifact.meta.debug
        : null;

    const metaRows = [
      artifact.id ? `<div><strong>ID:</strong> ${escapeHtml(artifact.id)}</div>` : "",
      artifact.kind ? `<div><strong>Kind:</strong> ${escapeHtml(artifact.kind)}</div>` : "",
      artifact.session_id ? `<div><strong>Session:</strong> ${escapeHtml(artifact.session_id)}</div>` : "",
      artifact.message_id ? `<div><strong>Message:</strong> ${escapeHtml(artifact.message_id)}</div>` : "",
      artifact.created_at ? `<div><strong>Created:</strong> ${escapeHtml(formatDateTime(artifact.created_at))}</div>` : "",
      artifact.updated_at ? `<div><strong>Updated:</strong> ${escapeHtml(formatDateTime(artifact.updated_at))}</div>` : "",
    ].filter(Boolean);

    els.viewer.innerHTML = `
      <div class="nova-artifact-card is-active">
        <div class="nova-meta-row">
          <span class="nova-badge">${escapeHtml(artifact.kind)}</span>
          ${artifact.session_id ? `<span class="nova-badge">owning session</span>` : ""}
        </div>
        <div><strong>${escapeHtml(artifact.title || "Untitled Artifact")}</strong></div>
        <div class="nova-kv">
          ${metaRows.join("")}
        </div>
        <pre class="nova-pre">${escapeHtml(artifact.content || "")}</pre>
        ${
          debugMeta
            ? `
          <div class="nova-kv">
            <div><strong>Debug:</strong></div>
            <pre class="nova-pre">${escapeHtml(JSON.stringify(debugMeta, null, 2))}</pre>
          </div>
        `
            : ""
        }
      </div>
    `;
  }

  async function fetchArtifacts() {
    const data = await api(API.list);
    const rawArtifacts = Array.isArray(data.artifacts) ? data.artifacts : [];
    const normalized = sortArtifacts(rawArtifacts.map(normalizeArtifact));
    state.artifacts = normalized;
    state.filtered = normalized;
    return normalized;
  }

  async function reload(options) {
    const opts = options && typeof options === "object" ? options : {};
    const preserveSelection = opts.preserveSelection !== false;
    const preferredId = String(opts.preferredId || "").trim();
    const showStatus = opts.showStatus !== false;

    if (showStatus) statusPending("Refreshing artifacts...");
    setLoading(true);

    try {
      const artifacts = await fetchArtifacts();

      let nextArtifact = null;

      if (preferredId) {
        nextArtifact =
          artifacts.find(function (item) {
            return item.id === preferredId;
          }) || null;
      }

      if (!nextArtifact && preserveSelection && state.activeArtifactId) {
        nextArtifact =
          artifacts.find(function (item) {
            return item.id === state.activeArtifactId;
          }) || null;
      }

      if (!nextArtifact && artifacts.length) {
        nextArtifact = artifacts[0];
      }

      setActiveArtifact(nextArtifact);

      if (showStatus) {
        statusSuccess(
          artifacts.length
            ? `Artifacts refreshed (${artifacts.length}).`
            : "Artifacts refreshed."
        );
      }

      return artifacts;
    } catch (error) {
      console.error("NovaArtifacts.reload failed:", error);
      statusError(error.message || "Failed to refresh artifacts.");
      renderList();
      renderViewer();
      throw error;
    } finally {
      setLoading(false);
    }
  }

  async function openArtifact(artifactId) {
    const cleanId = String(artifactId || "").trim();
    if (!cleanId) return;

    statusPending("Opening artifact...");
    setLoading(true);

    try {
      const data = await api(API.read(cleanId));
      const artifact = normalizeArtifact(data.artifact || {});
      setActiveArtifact(artifact);
      statusSuccess("Artifact opened.");
    } catch (error) {
      console.error("NovaArtifacts.openArtifact failed:", error);
      statusError(error.message || "Failed to open artifact.");
    } finally {
      setLoading(false);
    }
  }

  async function openOwningSession() {
    const artifact = getActiveArtifact();
    if (!artifact) {
      statusError("Select an artifact first.");
      return;
    }

    if (!artifact.session_id) {
      statusError("This artifact has no owning session.");
      return;
    }

    try {
      statusPending("Opening owning session...");
      if (
        window.NovaComposerBundle &&
        typeof window.NovaComposerBundle.hardRestoreSession === "function"
      ) {
        await window.NovaComposerBundle.hardRestoreSession(artifact.session_id);
        statusSuccess("Owning session opened.");
      } else {
        throw new Error("NovaComposerBundle.hardRestoreSession is unavailable.");
      }
    } catch (error) {
      console.error("NovaArtifacts.openOwningSession failed:", error);
      statusError(error.message || "Failed to open owning session.");
    }
  }

  async function copyActiveArtifact() {
    const artifact = getActiveArtifact();
    if (!artifact) {
      statusError("Select an artifact first.");
      return;
    }

    const payload = [
      artifact.title || "Untitled Artifact",
      "",
      artifact.content || "",
    ].join("\n");

    try {
      if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
        await navigator.clipboard.writeText(payload);
      } else {
        const ta = document.createElement("textarea");
        ta.value = payload;
        ta.setAttribute("readonly", "readonly");
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        ta.setSelectionRange(0, ta.value.length);
        const ok = document.execCommand("copy");
        document.body.removeChild(ta);
        if (!ok) {
          throw new Error("Copy failed.");
        }
      }

      statusSuccess("Artifact copied.");
    } catch (error) {
      console.error("NovaArtifacts.copyActiveArtifact failed:", error);
      statusError(error.message || "Failed to copy artifact.");
    }
  }

  async function cleanJunk() {
    const confirmed = window.confirm("Clean junk artifacts from backend truth?");
    if (!confirmed) return;

    statusPending("Cleaning artifact junk...");
    setLoading(true);

    try {
      const data = await api(API.cleanJunk, { method: "POST" });
      const result = data.result && typeof data.result === "object" ? data.result : {};
      await reload({ preserveSelection: true, showStatus: false });
      const removedCount =
        typeof result.removed_count !== "undefined"
          ? Number(result.removed_count || 0)
          : typeof result.deleted !== "undefined"
            ? Number(result.deleted || 0)
            : 0;

      statusSuccess(`Cleaned junk${removedCount ? ` (${removedCount})` : ""}.`);
    } catch (error) {
      console.error("NovaArtifacts.cleanJunk failed:", error);
      statusError(error.message || "Failed to clean artifact junk.");
    } finally {
      setLoading(false);
    }
  }

  function bindEvents() {
    if (els.refreshBtn) {
      els.refreshBtn.addEventListener("click", function () {
        reload({ preserveSelection: true });
      });
    }

    if (els.openSessionBtn) {
      els.openSessionBtn.addEventListener("click", function () {
        openOwningSession();
      });
    }

    if (els.copyBtn) {
      els.copyBtn.addEventListener("click", function () {
        copyActiveArtifact();
      });
    }

    if (els.cleanJunkBtn) {
      els.cleanJunkBtn.addEventListener("click", function () {
        cleanJunk();
      });
    }

    document.addEventListener("nova:chat-response", function () {
      reload({ preserveSelection: true, showStatus: false }).catch(function () {});
    });

    document.addEventListener("nova:session-restored", function () {
      renderList();
      renderViewer();
      setLoading(state.loading);
    });
  }

  async function init() {
    ensureElements();

    if (!els.list || !els.viewer) {
      console.warn("NovaArtifacts.init skipped: required elements missing");
      return;
    }

    bindEvents();
    setLoading(false);

    try {
      await reload({ preserveSelection: false, showStatus: false });
      console.log("Nova artifacts loaded");
    } catch (error) {
      console.error("NovaArtifacts.init failed:", error);
    }
  }

  window.NovaArtifacts = {
    init,
    reload,
    openArtifact,
    openOwningSession,
    copyActiveArtifact,
    cleanJunk,
    getActiveArtifact() {
      return getActiveArtifact();
    },
    getArtifacts() {
      return [...state.artifacts];
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();