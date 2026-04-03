(function () {
  "use strict";

  const LOG_PREFIX = "[NovaArtifacts]";
  const API = {
    list: "/api/artifacts",
    read(id) {
      return `/api/artifacts/${encodeURIComponent(id)}`;
    }
  };

  const state = {
    artifacts: [],
    filtered: [],
    activeArtifactId: "",
    activeArtifact: null,
    activeSessionId: "",
    filterText: "",
    booted: false,
    loading: false,
    refreshTimer: null
  };

  function log() {
    try {
      console.log(LOG_PREFIX, ...arguments);
    } catch (_) {}
  }

  function $(id) {
    return document.getElementById(id);
  }

  function qs(sel, root) {
    return (root || document).querySelector(sel);
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
      .replace(/"/g, "&quot;");
  }

  function nl2br(value) {
    return escapeHtml(value).replace(/\n/g, "<br>");
  }

  function formatTextBlock(text) {
    let html = escapeHtml(text || "");

    html = html.replace(
      /!\[([^\]]*)\]\((attachment:\/\/[^)]+|https?:\/\/[^)]+|\/api\/uploads\/[^)]+)\)/gi,
      function (_match, alt, url) {
        const resolved = String(url || "").replace(/^attachment:\/\//i, "/api/uploads/");
        return (
          '<img class="nova-inline-image" src="' +
          escapeHtml(resolved) +
          '" alt="' +
          escapeHtml(alt || "image") +
          '">'
        );
      }
    );

    html = html.replace(
      /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/gi,
      function (_match, label, url) {
        return (
          '<a href="' +
          escapeHtml(url) +
          '" target="_blank" rel="noreferrer">' +
          escapeHtml(label) +
          "</a>"
        );
      }
    );

    html = html
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\n/g, "<br>");

    return html;
  }

  function dispatch(name, detail) {
    try {
      window.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
    } catch (_) {}
  }

  function getPanelRoot() {
    return (
      $("artifactsPanel") ||
      qs("[data-panel='artifacts']") ||
      qs(".nova-artifacts-panel")
    );
  }

  function getListRoot() {
    return (
      $("artifactList") ||
      $("artifactsList") ||
      qs("[data-role='artifact-list']") ||
      qs("#artifactsPanel .nova-panel-scroll") ||
      qs(".nova-artifact-list")
    );
  }

  function getViewerRoot() {
    return (
      $("artifactViewer") ||
      $("artifactDetail") ||
      qs("[data-role='artifact-viewer']") ||
      qs(".nova-artifact-viewer")
    );
  }

  function getSearchInput() {
    return (
      $("artifactSearch") ||
      qs("[data-role='artifact-search']") ||
      qs("#artifactsPanel input[type='search']")
    );
  }

  function normalizeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function toIsoSortValue(value) {
    const v = safeText(value);
    return v || "";
  }

  function summarizeMeta(meta) {
    if (!meta || typeof meta !== "object") return "";

    const parts = [];

    if (meta.url) parts.push("url");
    if (meta.prompt) parts.push("prompt");
    if (meta.original_name) parts.push(meta.original_name);
    if (meta.analysis_type) parts.push(meta.analysis_type);
    if (meta.ssl_fallback_used) parts.push("ssl fallback");
    if (meta.reply_chars) parts.push(`reply ${meta.reply_chars} chars`);

    return parts.join(" • ");
  }

  function artifactKindLabel(kind) {
    const value = safeText(kind).replace(/_/g, " ").trim();
    if (!value) return "Artifact";
    return value.replace(/\b\w/g, function (m) {
      return m.toUpperCase();
    });
  }

  function normalizeArtifact(raw, index) {
    const item = raw || {};
    const viewer = item.viewer || {};
    const meta = item.meta || {};

    return {
      id: safeText(item.id || `artifact-${index}`),
      kind: safeText(item.kind || viewer.kind || "artifact"),
      title: safeText(item.title || artifactKindLabel(item.kind || viewer.kind || "artifact")),
      session_id: safeText(item.session_id || ""),
      created_at: safeText(item.created_at || ""),
      preview: safeText(item.preview || ""),
      content: safeText(item.content || ""),
      attachments: normalizeArray(item.attachments).map(function (att, i) {
        const a = att || {};
        return {
          id: safeText(a.id || `artifact-att-${index}-${i}`),
          name: safeText(a.name || a.filename || "attachment"),
          url: safeText(a.url || a.src || ""),
          type: safeText(a.type || a.kind || "")
        };
      }),
      meta: meta,
      viewer: {
        kind: safeText(viewer.kind || item.kind || "artifact"),
        content: safeText(viewer.content || item.content || ""),
        html: safeText(viewer.html || ""),
        url: safeText(viewer.url || meta.url || ""),
        media: normalizeArray(viewer.media).map(function (m, i) {
          const media = m || {};
          return {
            id: safeText(media.id || `media-${index}-${i}`),
            type: safeText(media.type || "file"),
            src: safeText(media.src || media.url || ""),
            alt: safeText(media.alt || media.name || "")
          };
        }),
        meta: viewer.meta || meta || {}
      }
    };
  }

  function setActiveSessionId(sessionId) {
    state.activeSessionId = safeText(sessionId || "");
  }

  function filterArtifacts() {
    const q = safeText(state.filterText).trim().toLowerCase();

    let items = state.artifacts.slice();

    if (state.activeSessionId) {
      items = items.filter(function (artifact) {
        return artifact.session_id === state.activeSessionId;
      });
    }

    if (q) {
      items = items.filter(function (artifact) {
        const haystack = [
          artifact.title,
          artifact.kind,
          artifact.preview,
          artifact.content,
          JSON.stringify(artifact.meta || {}),
          JSON.stringify(artifact.viewer && artifact.viewer.meta ? artifact.viewer.meta : {})
        ]
          .join(" ")
          .toLowerCase();

        return haystack.includes(q);
      });
    }

    items.sort(function (a, b) {
      return toIsoSortValue(b.created_at).localeCompare(toIsoSortValue(a.created_at));
    });

    state.filtered = items;
  }

  function render() {
    renderList();
    renderViewer();
  }

  function renderList() {
    const root = getListRoot();
    if (!root) return;

    filterArtifacts();

    if (!state.filtered.length) {
      root.innerHTML = '<div class="nova-empty-list">No artifacts yet.</div>';
      return;
    }

    root.innerHTML = state.filtered
      .map(function (artifact) {
        const active = artifact.id === state.activeArtifactId;
        const metaText = [
          artifactKindLabel(artifact.kind),
          artifact.created_at
        ]
          .filter(Boolean)
          .join(" • ");

        return (
          '<button class="nova-artifact-item' +
          (active ? " is-active" : "") +
          '" type="button" data-artifact-id="' +
          escapeHtml(artifact.id) +
          '">' +
          '<div class="nova-artifact-item-head">' +
          '<span class="nova-artifact-item-title">' +
          escapeHtml(artifact.title) +
          "</span>" +
          '<span class="nova-artifact-kind-badge">' +
          escapeHtml(artifactKindLabel(artifact.kind)) +
          "</span>" +
          "</div>" +
          (artifact.preview
            ? '<div class="nova-artifact-item-preview">' + nl2br(artifact.preview.slice(0, 220)) + "</div>"
            : "") +
          (metaText
            ? '<div class="nova-artifact-item-meta">' + escapeHtml(metaText) + "</div>"
            : "") +
          "</button>"
        );
      })
      .join("");
  }

  function renderViewer() {
    const root = getViewerRoot();
    if (!root) return;

    const artifact = state.activeArtifact;

    if (!artifact) {
      root.innerHTML =
        '<div class="nova-artifact-empty">' +
        '<div class="nova-artifact-empty-title">No artifact selected</div>' +
        '<div class="nova-artifact-empty-text">Select an artifact to view it here.</div>' +
        "</div>";
      return;
    }

    const viewer = artifact.viewer || {};
    const viewerKind = viewer.kind || artifact.kind || "artifact";
    const metaSummary = summarizeMeta(artifact.meta);
    const metaTable = buildMetaTable(artifact);
    const mediaHtml = buildMediaHtml(artifact);
    const attachmentsHtml = buildAttachmentsHtml(artifact.attachments);
    const primaryUrl =
      safeText(viewer.url) ||
      safeText(artifact.meta && artifact.meta.url) ||
      "";

    let bodyHtml = "";

    if (viewer.html) {
      bodyHtml = '<div class="nova-artifact-html">' + viewer.html + "</div>";
    } else {
      bodyHtml =
        '<div class="nova-artifact-text">' +
        formatTextBlock(viewer.content || artifact.content || artifact.preview || "") +
        "</div>";
    }

    root.innerHTML =
      '<article class="nova-artifact-view">' +
      '<header class="nova-artifact-header">' +
      '<div class="nova-artifact-header-main">' +
      '<div class="nova-artifact-title-row">' +
      '<h3 class="nova-artifact-title">' +
      escapeHtml(artifact.title) +
      "</h3>" +
      '<span class="nova-artifact-kind-pill">' +
      escapeHtml(artifactKindLabel(viewerKind)) +
      "</span>" +
      "</div>" +
      '<div class="nova-artifact-meta-line">' +
      escapeHtml(
        [artifact.created_at, artifact.session_id ? "session " + artifact.session_id : ""]
          .filter(Boolean)
          .join(" • ")
      ) +
      "</div>" +
      (metaSummary
        ? '<div class="nova-artifact-meta-line">' + escapeHtml(metaSummary) + "</div>"
        : "") +
      "</div>" +
      '<div class="nova-artifact-actions">' +
      (primaryUrl
        ? '<a class="nova-artifact-action" href="' +
          escapeHtml(primaryUrl) +
          '" target="_blank" rel="noreferrer">Open</a>'
        : '<button class="nova-artifact-action" type="button" data-copy-artifact-id="' +
          escapeHtml(artifact.id) +
          '">Copy</button>') +
      '<button class="nova-artifact-action" type="button" data-copy-artifact-id="' +
      escapeHtml(artifact.id) +
      '">Copy</button>' +
      '<button class="nova-artifact-action" type="button" data-open-owning-session="' +
      escapeHtml(artifact.session_id) +
      '">Session</button>' +
      "</div>" +
      "</header>" +
      (mediaHtml ? '<section class="nova-artifact-media">' + mediaHtml + "</section>" : "") +
      '<section class="nova-artifact-body">' + bodyHtml + "</section>" +
      (attachmentsHtml
        ? '<section class="nova-artifact-attachments"><h4>Attachments</h4>' + attachmentsHtml + "</section>"
        : "") +
      (metaTable ? '<section class="nova-artifact-debug"><h4>Meta</h4>' + metaTable + "</section>" : "") +
      "</article>";
  }

  function buildMediaHtml(artifact) {
    const viewer = artifact.viewer || {};
    const media = normalizeArray(viewer.media);

    if (!media.length) return "";

    return media
      .map(function (item) {
        const type = safeText(item.type).toLowerCase();
        const src = safeText(item.src);
        const alt = safeText(item.alt || artifact.title || "media");

        if (!src) return "";

        if (type === "image") {
          return (
            '<a class="nova-artifact-media-card is-image" href="' +
            escapeHtml(src) +
            '" target="_blank" rel="noreferrer">' +
            '<img src="' +
            escapeHtml(src) +
            '" alt="' +
            escapeHtml(alt) +
            '">' +
            "</a>"
          );
        }

        if (type === "video") {
          return (
            '<div class="nova-artifact-media-card is-video">' +
            '<video controls preload="metadata" src="' +
            escapeHtml(src) +
            '"></video>' +
            "</div>"
          );
        }

        if (type === "audio") {
          return (
            '<div class="nova-artifact-media-card is-audio">' +
            '<audio controls src="' +
            escapeHtml(src) +
            '"></audio>' +
            "</div>"
          );
        }

        return (
          '<a class="nova-artifact-media-card" href="' +
          escapeHtml(src) +
          '" target="_blank" rel="noreferrer">' +
          escapeHtml(src) +
          "</a>"
        );
      })
      .join("");
  }

  function buildAttachmentsHtml(list) {
    const attachments = normalizeArray(list);
    if (!attachments.length) return "";

    return attachments
      .map(function (item) {
        const name = escapeHtml(item.name || "attachment");
        const url = escapeHtml(item.url || "#");
        const type = safeText(item.type).toLowerCase();

        if (type === "image") {
          return (
            '<a class="nova-attachment-chip is-image" href="' +
            url +
            '" target="_blank" rel="noreferrer">' +
            '<img src="' +
            url +
            '" alt="' +
            name +
            '">' +
            '<span>' +
            name +
            "</span>" +
            "</a>"
          );
        }

        return (
          '<a class="nova-attachment-chip" href="' +
          url +
          '" target="_blank" rel="noreferrer">' +
          "<span>" +
          name +
          "</span>" +
          "</a>"
        );
      })
      .join("");
  }

  function buildMetaTable(artifact) {
    const rows = [];
    const meta = artifact.meta || {};
    const viewerMeta = (artifact.viewer && artifact.viewer.meta) || {};

    function pushObject(prefix, obj) {
      if (!obj || typeof obj !== "object") return;

      Object.keys(obj).forEach(function (key) {
        const value = obj[key];
        const label = prefix ? prefix + "." + key : key;

        if (value && typeof value === "object") {
          if (Array.isArray(value)) {
            rows.push([label, JSON.stringify(value)]);
          } else {
            pushObject(label, value);
          }
        } else {
          rows.push([label, safeText(value)]);
        }
      });
    }

    rows.push(["kind", artifact.kind]);
    rows.push(["viewer.kind", artifact.viewer && artifact.viewer.kind ? artifact.viewer.kind : artifact.kind]);
    if (artifact.viewer && artifact.viewer.url) {
      rows.push(["viewer.url", artifact.viewer.url]);
    }
    pushObject("meta", meta);
    pushObject("viewer.meta", viewerMeta);

    if (!rows.length) return "";

    return (
      '<div class="nova-meta-table">' +
      rows
        .map(function (pair) {
          return (
            '<div class="nova-meta-row">' +
            '<div class="nova-meta-key">' +
            escapeHtml(pair[0]) +
            "</div>" +
            '<div class="nova-meta-value">' +
            escapeHtml(pair[1]) +
            "</div>" +
            "</div>"
          );
        })
        .join("") +
      "</div>"
    );
  }

  function setActiveArtifactById(artifactId, preserveSelection) {
    const id = safeText(artifactId);

    if (!id) {
      state.activeArtifactId = "";
      state.activeArtifact = null;
      renderViewer();
      renderList();
      return;
    }

    const found = state.artifacts.find(function (artifact) {
      return artifact.id === id;
    });

    if (!found) {
      if (!preserveSelection) {
        state.activeArtifactId = "";
        state.activeArtifact = null;
        renderViewer();
        renderList();
      }
      return;
    }

    state.activeArtifactId = found.id;
    state.activeArtifact = found;
    renderViewer();
    renderList();
  }

  async function readArtifact(artifactId) {
    const id = safeText(artifactId);
    if (!id) return;

    try {
      const res = await fetch(API.read(id), {
        method: "GET",
        credentials: "same-origin",
        headers: {
          Accept: "application/json"
        }
      });

      const payload = await res.json();

      if (!res.ok || payload.ok === false || !payload.artifact) {
        throw new Error(payload.error || payload.message || "Failed to load artifact.");
      }

      const normalized = normalizeArtifact(payload.artifact, 0);
      const existingIndex = state.artifacts.findIndex(function (a) {
        return a.id === normalized.id;
      });

      if (existingIndex >= 0) {
        state.artifacts[existingIndex] = normalized;
      } else {
        state.artifacts.unshift(normalized);
      }

      setActiveArtifactById(normalized.id, false);
    } catch (error) {
      console.error(LOG_PREFIX, "readArtifact failed", error);
    }
  }

  async function refreshArtifacts(reason) {
    if (state.loading) return;
    state.loading = true;

    try {
      const url = new URL(API.list, window.location.origin);

      if (state.activeSessionId) {
        url.searchParams.set("session_id", state.activeSessionId);
      }

      log("refresh artifacts", {
        reason: reason || "",
        sessionId: state.activeSessionId,
        url: url.toString()
      });

      const res = await fetch(url.toString(), {
        method: "GET",
        credentials: "same-origin",
        headers: {
          Accept: "application/json"
        }
      });

      const payload = await res.json();

      if (!res.ok || payload.ok === false) {
        throw new Error(payload.error || payload.message || "Failed to load artifacts.");
      }

      state.artifacts = normalizeArray(payload.artifacts).map(normalizeArtifact);

      if (
        state.activeArtifactId &&
        !state.artifacts.some(function (artifact) {
          return artifact.id === state.activeArtifactId;
        })
      ) {
        state.activeArtifactId = "";
        state.activeArtifact = null;
      }

      if (!state.activeArtifactId && state.artifacts.length) {
        state.activeArtifactId = state.artifacts[0].id;
        state.activeArtifact = state.artifacts[0];
      } else if (state.activeArtifactId) {
        state.activeArtifact =
          state.artifacts.find(function (artifact) {
            return artifact.id === state.activeArtifactId;
          }) || null;
      }

      render();

      dispatch("nova:artifacts-refreshed", {
        artifacts: state.artifacts,
        activeArtifactId: state.activeArtifactId,
        activeSessionId: state.activeSessionId
      });
    } catch (error) {
      console.error(LOG_PREFIX, "refreshArtifacts failed", error);
    } finally {
      state.loading = false;
    }
  }

  function scheduleRefresh(reason, delay) {
    const wait = typeof delay === "number" ? delay : 0;

    if (state.refreshTimer) {
      clearTimeout(state.refreshTimer);
      state.refreshTimer = null;
    }

    state.refreshTimer = setTimeout(function () {
      state.refreshTimer = null;
      refreshArtifacts(reason);
    }, wait);
  }

  async function copyArtifactContent(artifactId) {
    const artifact = state.artifacts.find(function (item) {
      return item.id === artifactId;
    });

    if (!artifact) return;

    const text =
      safeText((artifact.viewer && artifact.viewer.content) || artifact.content || artifact.preview);

    try {
      await navigator.clipboard.writeText(text);
      log("copied artifact", artifactId);
    } catch (error) {
      console.error(LOG_PREFIX, "copy failed", error);
    }
  }

  function bindEvents() {
    document.addEventListener("click", function (event) {
      const artifactBtn = event.target.closest("[data-artifact-id]");
      if (artifactBtn) {
        const artifactId = safeText(artifactBtn.getAttribute("data-artifact-id"));
        if (artifactId) {
          setActiveArtifactById(artifactId, false);
          readArtifact(artifactId);
        }
        return;
      }

      const copyBtn = event.target.closest("[data-copy-artifact-id]");
      if (copyBtn) {
        const artifactId = safeText(copyBtn.getAttribute("data-copy-artifact-id"));
        if (artifactId) {
          copyArtifactContent(artifactId);
        }
        return;
      }

      const owningSessionBtn = event.target.closest("[data-open-owning-session]");
      if (owningSessionBtn) {
        const sessionId = safeText(owningSessionBtn.getAttribute("data-open-owning-session"));
        if (sessionId) {
          dispatch("nova:artifact-owning-session-request", {
            sessionId: sessionId
          });
          dispatch("nova:open-panel", {
            panel: "artifacts"
          });
        }
      }
    });

    const search = getSearchInput();
    if (search) {
      search.addEventListener("input", function () {
        state.filterText = safeText(search.value);
        renderList();
      });
    }

    window.addEventListener("nova:refresh-artifacts", function (event) {
      const nextSessionId = safeText(
        event.detail &&
          (event.detail.sessionId || event.detail.session_id || event.detail.activeSessionId)
      );
      if (nextSessionId) {
        setActiveSessionId(nextSessionId);
      }
      scheduleRefresh("event:refresh-artifacts", 0);
    });

    window.addEventListener("nova:artifacts-refresh-request", function (event) {
      const nextSessionId = safeText(
        event.detail &&
          (event.detail.sessionId || event.detail.session_id || event.detail.activeSessionId)
      );
      if (nextSessionId) {
        setActiveSessionId(nextSessionId);
      }
      scheduleRefresh("event:artifacts-refresh-request", 0);
    });

    window.addEventListener("nova:state-refreshed", function (event) {
      const nextSessionId = safeText(
        event.detail &&
          (event.detail.sessionId || event.detail.active_session_id || event.detail.session_id)
      );
      if (nextSessionId) {
        setActiveSessionId(nextSessionId);
      }
      scheduleRefresh("event:state-refreshed", 0);
    });

    window.addEventListener("nova:message-sent", function (event) {
      const nextSessionId = safeText(
        event.detail &&
          (event.detail.sessionId || event.detail.session_id)
      );
      if (nextSessionId) {
        setActiveSessionId(nextSessionId);
      }
      scheduleRefresh("event:message-sent", 80);
    });

    window.addEventListener("nova:artifact-owning-session-request", function (event) {
      const nextSessionId = safeText(
        event.detail &&
          (event.detail.sessionId || event.detail.session_id || event.detail.owning_session_id)
      );
      if (!nextSessionId) return;
      if (nextSessionId === state.activeSessionId) return;

      setActiveSessionId(nextSessionId);
      scheduleRefresh("event:artifact-owning-session-request", 0);
    });
  }

  function boot() {
    if (state.booted) return;
    state.booted = true;

    log("boot");
    bindEvents();
    render();
    scheduleRefresh("boot", 0);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();