(function () {
  "use strict";

  console.log("Nova artifacts loaded");

  const API = {
    artifacts: "/api/artifacts",
    pin: "/api/artifacts/pin",
    delete: "/api/artifacts/delete",
    state: "/api/state",
  };

  const state = {
    sessionId: "default-session",
    artifacts: [],
    selectedArtifactId: null,
    loadingArtifacts: false,
    loadingMemory: false,
    loadingWeb: false,
    lastReplyDebug: null,
    refreshQueued: false,
    autoSelectNewestOnReply: true,
    lastKnownArtifactIds: new Set(),
    pendingHighlightArtifactId: null,
    lastOpenedPanel: "memory",
  };

  function el(id) {
    return document.getElementById(id);
  }

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function nl2br(value) {
    return escapeHtml(value).replace(/\n/g, "<br>");
  }

  function getSessionId() {
    const fromComposer =
      window.NovaComposerBundle &&
      typeof window.NovaComposerBundle.getSessionId === "function"
        ? window.NovaComposerBundle.getSessionId()
        : null;

    const fromBody = document.body?.dataset?.sessionId || null;
    const fromStorage = localStorage.getItem("nova_active_session_id") || null;

    const resolved = fromComposer || fromBody || fromStorage || "default-session";
    state.sessionId = resolved;
    return resolved;
  }

  function setSessionId(sessionId) {
    const resolved = String(sessionId || "default-session").trim() || "default-session";
    state.sessionId = resolved;
    document.body.dataset.sessionId = resolved;
    localStorage.setItem("nova_active_session_id", resolved);
  }

  function getArtifactListEl() {
    return el("artifactList");
  }

  function getArtifactViewerEl() {
    return el("artifactViewer");
  }

  function getMemoryPanelBodyEl() {
    return el("memoryPanelBody");
  }

  function getWebPanelBodyEl() {
    return el("webPanelBody");
  }

  function getRightRailShell() {
    return el("novaAppShell");
  }

  function getRailPanel(name) {
    if (name === "artifacts") return el("artifactsPanel");
    if (name === "memory") return el("memoryPanel");
    if (name === "web") return el("webPanel");
    return null;
  }

  function getRailTab(name) {
    if (name === "artifacts") return el("railTabArtifacts");
    if (name === "memory") return el("railTabMemory");
    if (name === "web") return el("railTabWeb");
    return null;
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options || {});
    const text = await response.text();

    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch (error) {
      throw new Error(`Invalid JSON from ${url}: ${text.slice(0, 300)}`);
    }

    if (!response.ok) {
      throw new Error(data?.message || data?.error || `HTTP ${response.status}`);
    }

    return data;
  }

  function normalizeArtifacts(data) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.artifacts)) return data.artifacts;
    if (Array.isArray(data?.items)) return data.items;
    return [];
  }

  function normalizeMemoryItems(data) {
    if (Array.isArray(data?.memory_items)) return data.memory_items;
    if (Array.isArray(data?.memory)) return data.memory;
    if (Array.isArray(data?.session?.memory)) return data.session.memory;
    return [];
  }

  function sortArtifacts(items) {
    return [...items].sort((a, b) => {
      const aPinned = a?.pinned ? 1 : 0;
      const bPinned = b?.pinned ? 1 : 0;
      if (aPinned !== bPinned) return bPinned - aPinned;

      const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
      const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
      return bTime - aTime;
    });
  }

  function sortArtifactsNewestFirst(items) {
    return [...items].sort((a, b) => {
      const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
      const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
      return bTime - aTime;
    });
  }

  function artifactKindLabel(artifact) {
    return artifact?.kind || artifact?.type || "artifact";
  }

  function artifactTitle(artifact) {
    return (
      artifact?.title ||
      artifact?.name ||
      (artifact?.content ? String(artifact.content).slice(0, 80) : "") ||
      "Untitled artifact"
    );
  }

  function artifactContent(artifact) {
    return artifact?.content || artifact?.text || artifact?.body || "";
  }

  function getSelectedArtifact() {
    if (!state.selectedArtifactId) return null;
    return state.artifacts.find((item) => item.id === state.selectedArtifactId) || null;
  }

  function openRailPanel(name) {
    state.lastOpenedPanel = name || "memory";

    if (window.NovaPanels && typeof window.NovaPanels.open === "function") {
      window.NovaPanels.open(name);
      return;
    }

    const shell = getRightRailShell();
    if (shell) {
      shell.classList.add("rail-open");
    }

    ["memory", "artifacts", "web"].forEach((panelName) => {
      const panel = getRailPanel(panelName);
      const tab = getRailTab(panelName);
      const isActive = panelName === name;

      if (panel) panel.classList.toggle("is-active", isActive);
      if (tab) tab.classList.toggle("is-active", isActive);
    });
  }

  function flashArtifactRow(artifactId) {
    if (!artifactId) return;
    const row = qs(`[data-artifact-id="${CSS.escape(artifactId)}"]`, getArtifactListEl());
    if (!row) return;

    row.classList.add("artifact-row-flash");
    row.style.outline = "2px solid rgba(121,225,176,0.7)";
    row.style.outlineOffset = "2px";

    setTimeout(() => {
      row.classList.remove("artifact-row-flash");
      row.style.outline = "";
      row.style.outlineOffset = "";
    }, 1600);
  }

  function ensureSelectedArtifactStillValid() {
    if (!state.artifacts.length) {
      state.selectedArtifactId = null;
      return;
    }

    if (
      state.selectedArtifactId &&
      state.artifacts.some((item) => item.id === state.selectedArtifactId)
    ) {
      return;
    }

    state.selectedArtifactId = state.artifacts[0].id;
  }

  function chooseNewestArtifact() {
    const sorted = sortArtifactsNewestFirst(state.artifacts);
    return sorted[0] || null;
  }

  function detectNewestNewArtifact() {
    const currentIds = new Set(state.artifacts.map((item) => item.id));
    const newArtifacts = sortArtifactsNewestFirst(
      state.artifacts.filter((item) => !state.lastKnownArtifactIds.has(item.id))
    );

    state.lastKnownArtifactIds = currentIds;
    return newArtifacts[0] || null;
  }

  function artifactPreviewLine(artifact) {
    const content = artifactContent(artifact);
    if (!content) return "";
    return String(content).replace(/\s+/g, " ").trim().slice(0, 140);
  }

  function renderArtifactsList() {
    const listEl = getArtifactListEl();
    if (!listEl) return;

    if (!state.artifacts.length) {
      listEl.innerHTML = '<div class="panel-empty">No artifacts yet.</div>';
      return;
    }

    const rows = sortArtifacts(state.artifacts)
      .map((artifact) => {
        const isSelected = artifact.id === state.selectedArtifactId;
        const isHighlighted = artifact.id === state.pendingHighlightArtifactId;
        const pinnedBadge = artifact.pinned
          ? '<span class="nova-badge nova-badge-warning">Pinned</span>'
          : "";
        const preview = artifactPreviewLine(artifact);

        return `
          <div
            class="artifact-row${isSelected ? " is-selected" : ""}${isHighlighted ? " is-highlighted" : ""}"
            data-artifact-id="${escapeHtml(artifact.id || "")}"
            style="
              border: 1px solid rgba(130, 158, 222, 0.14);
              border-radius: 16px;
              padding: 12px;
              background: ${
                isSelected
                  ? "rgba(110,168,255,0.12)"
                  : isHighlighted
                    ? "rgba(121,225,176,0.08)"
                    : "rgba(255,255,255,0.025)"
              };
              display: grid;
              gap: 10px;
              transition: 0.18s ease;
            "
          >
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;">
              <div style="min-width:0;">
                <div style="font-weight:800;line-height:1.4;word-break:break-word;">
                  ${escapeHtml(artifactTitle(artifact))}
                </div>
                ${
                  preview
                    ? `
                  <div style="margin-top:6px;color:#9eb1d1;font-size:0.84rem;line-height:1.45;word-break:break-word;">
                    ${escapeHtml(preview)}
                  </div>
                `
                    : ""
                }
                <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:8px;">
                  <span class="nova-badge">${escapeHtml(artifactKindLabel(artifact))}</span>
                  ${pinnedBadge}
                  ${
                    isHighlighted
                      ? '<span class="nova-badge nova-badge-soft">New</span>'
                      : ""
                  }
                </div>
              </div>
            </div>

            <div style="display:flex;gap:8px;flex-wrap:wrap;">
              <button class="nova-btn artifact-open-btn" type="button" data-action="open" data-artifact-id="${escapeHtml(artifact.id || "")}">Open</button>
              <button class="nova-btn artifact-pin-btn" type="button" data-action="pin" data-artifact-id="${escapeHtml(artifact.id || "")}">
                ${artifact.pinned ? "Unpin" : "Pin"}
              </button>
              <button class="nova-btn artifact-delete-btn" type="button" data-action="delete" data-artifact-id="${escapeHtml(artifact.id || "")}">Delete</button>
            </div>
          </div>
        `;
      })
      .join("");

    listEl.innerHTML = rows;

    if (state.pendingHighlightArtifactId) {
      requestAnimationFrame(() => {
        flashArtifactRow(state.pendingHighlightArtifactId);
      });
    }
  }

  function renderArtifactViewer() {
    const viewerEl = getArtifactViewerEl();
    if (!viewerEl) return;

    const artifact = getSelectedArtifact();

    if (!artifact) {
      viewerEl.innerHTML = "Select an artifact.";
      return;
    }

    const meta = artifact?.meta || {};
    const content = artifactContent(artifact);

    viewerEl.innerHTML = `
      <div style="display:grid;gap:12px;">
        <div>
          <div style="font-size:1rem;font-weight:800;line-height:1.4;">
            ${escapeHtml(artifactTitle(artifact))}
          </div>
          <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:8px;">
            <span class="nova-badge">${escapeHtml(artifactKindLabel(artifact))}</span>
            ${artifact.pinned ? '<span class="nova-badge nova-badge-warning">Pinned</span>' : ""}
            ${
              artifact.id === state.pendingHighlightArtifactId
                ? '<span class="nova-badge nova-badge-soft">Newest</span>'
                : ""
            }
          </div>
        </div>

        <div style="color:#9eb1d1;font-size:0.84rem;line-height:1.5;">
          <div><strong>ID:</strong> ${escapeHtml(artifact.id || "")}</div>
          <div><strong>Created:</strong> ${escapeHtml(artifact.created_at || "")}</div>
          <div><strong>Updated:</strong> ${escapeHtml(artifact.updated_at || artifact.created_at || "")}</div>
        </div>

        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <button class="nova-btn" type="button" data-viewer-action="pin" data-artifact-id="${escapeHtml(artifact.id || "")}">
            ${artifact.pinned ? "Unpin" : "Pin"}
          </button>
          <button class="nova-btn" type="button" data-viewer-action="delete" data-artifact-id="${escapeHtml(artifact.id || "")}">
            Delete
          </button>
          <button class="nova-btn" type="button" data-viewer-action="copy" data-artifact-id="${escapeHtml(artifact.id || "")}">
            Copy
          </button>
        </div>

        <div style="border-top:1px solid rgba(130,158,222,0.14);padding-top:12px;line-height:1.65;word-break:break-word;">
          ${nl2br(content || "")}
        </div>

        <details>
          <summary style="cursor:pointer;color:#9eb1d1;font-weight:700;">Debug meta</summary>
          <pre style="margin:10px 0 0;white-space:pre-wrap;word-break:break-word;color:#eef4ff;background:rgba(255,255,255,0.03);padding:12px;border-radius:12px;border:1px solid rgba(130,158,222,0.14);">${escapeHtml(JSON.stringify(meta, null, 2))}</pre>
        </details>
      </div>
    `;
  }

  function renderArtifacts() {
    ensureSelectedArtifactStillValid();
    renderArtifactsList();
    renderArtifactViewer();
  }

  function renderMemory(memoryItems) {
    const memoryEl = getMemoryPanelBodyEl();
    if (!memoryEl) return;

    if (!Array.isArray(memoryItems) || !memoryItems.length) {
      memoryEl.innerHTML = '<div class="panel-empty">No memory loaded yet.</div>';
      return;
    }

    memoryEl.innerHTML = memoryItems
      .slice(0, 12)
      .map((item) => {
        const title =
          item?.title ||
          item?.name ||
          (item?.content ? String(item.content).slice(0, 90) : "") ||
          "Memory";

        return `
          <div
            style="
              border:1px solid rgba(130,158,222,0.14);
              border-radius:14px;
              padding:12px;
              background:rgba(255,255,255,0.025);
              display:grid;
              gap:8px;
            "
          >
            <div style="font-weight:700;line-height:1.45;word-break:break-word;">
              ${escapeHtml(title)}
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;">
              ${item?.pinned ? '<span class="nova-badge nova-badge-warning">Pinned</span>' : ""}
              ${
                item?.created_at
                  ? `<span class="nova-badge">${escapeHtml(item.created_at)}</span>`
                  : ""
              }
            </div>
          </div>
        `;
      })
      .join("");
  }

  function buildWebPanelHtml(debug) {
    const safeDebug = debug || {};
    const web = safeDebug?.web || safeDebug?.web_debug || {};
    const webUsed = !!(safeDebug.web_used || web.used);

    const urls = Array.isArray(web?.urls) ? web.urls : [];
    const titles = Array.isArray(web?.titles) ? web.titles : [];
    const resultCount = Number(web?.result_count || 0);
    const okCount = Number(web?.ok_count || 0);
    const failedCount = Number(web?.failed_count || 0);

    if (!webUsed && !urls.length && !titles.length && !resultCount && !okCount && !failedCount) {
      return '<div class="panel-empty">No web data yet.</div>';
    }

    return `
      <div style="display:grid;gap:12px;">
        <div style="display:grid;gap:8px;">
          <div><strong>Used:</strong> ${escapeHtml(String(webUsed))}</div>
          <div><strong>Results:</strong> ${escapeHtml(String(resultCount))}</div>
          <div><strong>OK:</strong> ${escapeHtml(String(okCount))}</div>
          <div><strong>Failed:</strong> ${escapeHtml(String(failedCount))}</div>
        </div>

        ${
          titles.length
            ? `
          <div>
            <div style="font-weight:800;color:#9eb1d1;margin-bottom:8px;">Titles</div>
            <div style="display:grid;gap:8px;">
              ${titles
                .map(
                  (title) => `
                <div style="border:1px solid rgba(130,158,222,0.14);border-radius:12px;padding:10px;background:rgba(255,255,255,0.025);">
                  ${escapeHtml(title)}
                </div>
              `
                )
                .join("")}
            </div>
          </div>
        `
            : ""
        }

        ${
          urls.length
            ? `
          <div>
            <div style="font-weight:800;color:#9eb1d1;margin-bottom:8px;">URLs</div>
            <div style="display:grid;gap:8px;">
              ${urls
                .map(
                  (url) => `
                <div style="border:1px solid rgba(130,158,222,0.14);border-radius:12px;padding:10px;background:rgba(255,255,255,0.025);word-break:break-all;">
                  ${escapeHtml(url)}
                </div>
              `
                )
                .join("")}
            </div>
          </div>
        `
            : ""
        }
      </div>
    `;
  }

  function renderWeb(debug) {
    const webEl = getWebPanelBodyEl();
    if (!webEl) return;
    webEl.innerHTML = buildWebPanelHtml(debug || state.lastReplyDebug || {});
  }

  async function refreshArtifacts(detail) {
    if (state.loadingArtifacts) return;
    state.loadingArtifacts = true;

    try {
      const sessionId = getSessionId();
      setSessionId(sessionId);

      const data = await fetchJson(`${API.artifacts}?session_id=${encodeURIComponent(sessionId)}`);
      state.artifacts = normalizeArtifacts(data);

      const newestNewArtifact = detectNewestNewArtifact();

      if (detail?.reason === "assistant_reply") {
        if (newestNewArtifact) {
          state.pendingHighlightArtifactId = newestNewArtifact.id;

          if (state.autoSelectNewestOnReply) {
            state.selectedArtifactId = newestNewArtifact.id;
            openRailPanel("artifacts");
          }
        } else if (state.autoSelectNewestOnReply && state.artifacts.length) {
          const newestExisting = chooseNewestArtifact();
          if (newestExisting) {
            state.selectedArtifactId = newestExisting.id;
          }
        }
      } else {
        if (
          state.pendingHighlightArtifactId &&
          !state.artifacts.some((item) => item.id === state.pendingHighlightArtifactId)
        ) {
          state.pendingHighlightArtifactId = null;
        }
      }

      renderArtifacts();

      if (detail?.reason === "assistant_reply" && state.pendingHighlightArtifactId) {
        setTimeout(() => {
          state.pendingHighlightArtifactId = null;
          renderArtifacts();
        }, 2200);
      }
    } catch (error) {
      console.error("refreshArtifacts failed:", error);
      const listEl = getArtifactListEl();
      const viewerEl = getArtifactViewerEl();

      if (listEl) {
        listEl.innerHTML = `<div class="panel-empty">Artifacts failed to load: ${escapeHtml(error.message || error)}</div>`;
      }

      if (viewerEl && !state.artifacts.length) {
        viewerEl.textContent = "Select an artifact.";
      }
    } finally {
      state.loadingArtifacts = false;
    }
  }

  async function refreshMemory() {
    if (state.loadingMemory) return;
    state.loadingMemory = true;

    try {
      const sessionId = getSessionId();
      const data = await fetchJson(`${API.state}?session_id=${encodeURIComponent(sessionId)}`);
      renderMemory(normalizeMemoryItems(data));
    } catch (error) {
      console.error("refreshMemory failed:", error);
      const memoryEl = getMemoryPanelBodyEl();
      if (memoryEl) {
        memoryEl.innerHTML = `<div class="panel-empty">Memory failed to load: ${escapeHtml(error.message || error)}</div>`;
      }
    } finally {
      state.loadingMemory = false;
    }
  }

  async function refreshWeb(detail) {
    if (state.loadingWeb) return;
    state.loadingWeb = true;

    try {
      if (detail?.debug) {
        state.lastReplyDebug = detail.debug;
      } else if (detail?.reply?.debug) {
        state.lastReplyDebug = detail.reply.debug;
      }
      renderWeb(state.lastReplyDebug || {});
    } finally {
      state.loadingWeb = false;
    }
  }

  async function refreshAll(detail) {
    if (detail?.session_id) {
      setSessionId(detail.session_id);
    }

    if (detail?.debug) {
      state.lastReplyDebug = detail.debug;
    } else if (detail?.reply?.debug) {
      state.lastReplyDebug = detail.reply.debug;
    }

    await refreshArtifacts(detail || {});
    await refreshMemory();
    await refreshWeb(detail || {});
  }

  function queueRefresh(detail) {
    if (state.refreshQueued) return;
    state.refreshQueued = true;

    setTimeout(async function () {
      state.refreshQueued = false;
      await refreshAll(detail || {});
    }, 0);
  }

  async function setPinned(artifactId, pinned) {
    await fetchJson(API.pin, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        artifact_id: artifactId,
        pinned: !!pinned,
      }),
    });

    await refreshArtifacts({ reason: "artifact_pin" });
  }

  async function deleteArtifact(artifactId) {
    await fetchJson(API.delete, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        artifact_id: artifactId,
      }),
    });

    if (state.selectedArtifactId === artifactId) {
      state.selectedArtifactId = null;
    }

    if (state.pendingHighlightArtifactId === artifactId) {
      state.pendingHighlightArtifactId = null;
    }

    await refreshArtifacts({ reason: "artifact_delete" });
  }

  async function copyArtifactContent(artifactId) {
    const artifact = state.artifacts.find((item) => item.id === artifactId);
    if (!artifact) return;

    const content = artifactContent(artifact);
    await navigator.clipboard.writeText(content || "");
  }

  function bindArtifactListClicks() {
    const listEl = getArtifactListEl();
    if (!listEl || listEl.dataset.boundNovaArtifacts === "true") return;

    listEl.dataset.boundNovaArtifacts = "true";

    listEl.addEventListener("click", async function (event) {
      const actionEl = event.target.closest("[data-action]");
      const rowEl = event.target.closest("[data-artifact-id]");

      if (!rowEl) return;

      const artifactId = rowEl.dataset.artifactId;
      if (!artifactId) return;

      const action = actionEl?.dataset?.action || "open";

      try {
        if (action === "open") {
          state.selectedArtifactId = artifactId;
          openRailPanel("artifacts");
          renderArtifacts();
          return;
        }

        if (action === "pin") {
          const artifact = state.artifacts.find((item) => item.id === artifactId);
          await setPinned(artifactId, !artifact?.pinned);
          return;
        }

        if (action === "delete") {
          await deleteArtifact(artifactId);
          return;
        }
      } catch (error) {
        console.error(`artifact action failed (${action}):`, error);
      }
    });
  }

  function bindViewerClicks() {
    const viewerEl = getArtifactViewerEl();
    if (!viewerEl || viewerEl.dataset.boundNovaArtifacts === "true") return;

    viewerEl.dataset.boundNovaArtifacts = "true";

    viewerEl.addEventListener("click", async function (event) {
      const actionEl = event.target.closest("[data-viewer-action]");
      if (!actionEl) return;

      const action = actionEl.dataset.viewerAction;
      const artifactId = actionEl.dataset.artifactId;
      if (!artifactId) return;

      try {
        if (action === "pin") {
          const artifact = state.artifacts.find((item) => item.id === artifactId);
          await setPinned(artifactId, !artifact?.pinned);
          return;
        }

        if (action === "delete") {
          await deleteArtifact(artifactId);
          return;
        }

        if (action === "copy") {
          await copyArtifactContent(artifactId);
          actionEl.textContent = "Copied";
          setTimeout(() => {
            actionEl.textContent = "Copy";
          }, 1200);
        }
      } catch (error) {
        console.error(`viewer action failed (${action}):`, error);
      }
    });
  }

  function bindRailTabTracking() {
    ["memory", "artifacts", "web"].forEach((name) => {
      const tab = getRailTab(name);
      if (!tab || tab.dataset.boundTrack === "true") return;

      tab.dataset.boundTrack = "true";
      tab.addEventListener("click", function () {
        state.lastOpenedPanel = name;
      });
    });

    const memoryBtn = el("memoryPanelToggle");
    const artifactsBtn = el("artifactsPanelToggle");
    const webBtn = el("webPanelToggle");

    if (memoryBtn && memoryBtn.dataset.boundTrack !== "true") {
      memoryBtn.dataset.boundTrack = "true";
      memoryBtn.addEventListener("click", function () {
        state.lastOpenedPanel = "memory";
      });
    }

    if (artifactsBtn && artifactsBtn.dataset.boundTrack !== "true") {
      artifactsBtn.dataset.boundTrack = "true";
      artifactsBtn.addEventListener("click", function () {
        state.lastOpenedPanel = "artifacts";
      });
    }

    if (webBtn && webBtn.dataset.boundTrack !== "true") {
      webBtn.dataset.boundTrack = "true";
      webBtn.addEventListener("click", function () {
        state.lastOpenedPanel = "web";
      });
    }
  }

  function bindEvents() {
    document.addEventListener("nova:assistant-reply", function (event) {
      queueRefresh({
        ...(event.detail || {}),
        reason: "assistant_reply",
      });
    });

    document.addEventListener("nova:state-restored", function (event) {
      queueRefresh({
        ...(event.detail || {}),
        reason: "state_restored",
      });
    });

    document.addEventListener("nova:artifacts-refresh", function (event) {
      queueRefresh(event.detail || {});
    });

    document.addEventListener("nova:memory-refresh", function (event) {
      queueRefresh(event.detail || {});
    });

    document.addEventListener("nova:web-refresh", function (event) {
      queueRefresh(event.detail || {});
    });
  }

  async function init() {
    setSessionId(getSessionId());
    bindArtifactListClicks();
    bindViewerClicks();
    bindRailTabTracking();
    bindEvents();
    await refreshAll({ reason: "init" });
  }

  window.NovaArtifacts = {
    init,
    refresh: refreshAll,
    refreshArtifacts,
    refreshMemory,
    refreshWeb,
    openArtifacts() {
      openRailPanel("artifacts");
    },
    getState() {
      return {
        sessionId: state.sessionId,
        artifacts: state.artifacts,
        selectedArtifactId: state.selectedArtifactId,
        pendingHighlightArtifactId: state.pendingHighlightArtifactId,
        lastOpenedPanel: state.lastOpenedPanel,
      };
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();