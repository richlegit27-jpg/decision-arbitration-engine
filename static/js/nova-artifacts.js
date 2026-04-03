(function () {
  "use strict";

  const LOG = "[NovaArtifacts]";
  const API = {
    list: "/api/artifacts",
    read(id) {
      return "/api/artifacts/" + encodeURIComponent(id);
    }
  };

  const state = {
    artifacts: [],
    filtered: [],
    activeId: "",
    active: null,
    filter: "all",
    search: "",
    activeSessionId: ""
  };

  function log() {
    try {
      console.log(LOG, ...arguments);
    } catch (_) {}
  }

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
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

  function dispatch(name, detail) {
    try {
      document.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
    } catch (_) {}
  }

  function artifactMedia(a) {
    const m = a && a.meta;
    if (m && Array.isArray(m.media)) return m.media;
    if (Array.isArray(a && a.attachments)) return a.attachments;
    return [];
  }

  function artifactImage(a) {
    return (
      artifactMedia(a).find(function (m) {
        return safe(m && m.type).toLowerCase() === "image" && safe(m && m.url);
      }) || null
    );
  }

  function containsSearch(a, query) {
    const hay = [a && a.title, a && a.kind, a && a.content, a && a.session_id]
      .join(" ")
      .toLowerCase();
    return hay.indexOf(query.toLowerCase()) >= 0;
  }

  async function loadArtifacts() {
    try {
      const res = await fetch(API.list, { credentials: "same-origin" });
      const data = await res.json();
      if (!res.ok || data.ok === false) throw new Error(data.error || "load failed");

      state.artifacts = Array.isArray(data.artifacts) ? data.artifacts : [];
      applyFilterSort();
      render();
    } catch (e) {
      console.error(LOG, "load failed", e);
    }
  }

  function applyFilterSort() {
    let list = state.artifacts.slice();

    if (state.search) {
      list = list.filter(function (a) {
        return containsSearch(a, state.search);
      });
    }

    if (state.filter === "pinned") {
      list = list.filter(function (a) {
        return !!a.pinned;
      });
    } else if (state.filter === "media") {
      list = list.filter(function (a) {
        return artifactMedia(a).length > 0;
      });
    } else if (state.filter === "chat_reply") {
      list = list.filter(function (a) {
        return safe(a.kind) === "chat_reply";
      });
    } else if (state.filter === "current_session") {
      list = list.filter(function (a) {
        return safe(a.session_id) === safe(state.activeSessionId);
      });
    }

    list.sort(function (a, b) {
      return new Date(b.created_at) - new Date(a.created_at);
    });

    state.filtered = list;
  }

  function renderList() {
    const el = qs("#artifactsList");
    const empty = qs("#artifactEmpty");
    if (!el) return;

    if (!state.filtered.length) {
      el.innerHTML = "";
      if (empty) empty.style.display = "";
      return;
    }

    if (empty) empty.style.display = "none";

    el.innerHTML = state.filtered
      .map(function (a) {
        const id = safe(a.id);
        const img = artifactImage(a);
        const isActive = state.activeId === id;
        const kind = safe(a.kind || "artifact");
        const preview = safe(a.content || "").slice(0, 120);
        const sessionBadge =
          safe(a.session_id) && safe(a.session_id) === safe(state.activeSessionId)
            ? '<span class="nova-message-badge">Current</span>'
            : "";

        return (
          '<div class="nova-artifact-card' +
          (isActive ? " active" : "") +
          '" data-id="' +
          esc(id) +
          '">' +
          '<div class="nova-artifact-card-top">' +
          '<div class="nova-artifact-title">' +
          esc(a.title || "Untitled") +
          "</div>" +
          '<div class="nova-artifact-badges">' +
          '<span class="nova-message-badge">' +
          esc(kind) +
          "</span>" +
          sessionBadge +
          "</div>" +
          "</div>" +
          (img
            ? '<div class="nova-artifact-thumb"><img src="' +
              esc(img.url) +
              '" alt="' +
              esc(a.title || "artifact image") +
              '" loading="lazy"></div>'
            : "") +
          '<div class="nova-artifact-preview">' +
          esc(preview) +
          "</div>" +
          "</div>"
        );
      })
      .join("");

    qsa(".nova-artifact-card", el).forEach(function (card) {
      card.onclick = function () {
        const artifactId = safe(card.dataset.id || "");
        if (!artifactId) return;

        const artifact = state.artifacts.find(function (a) {
          return safe(a.id) === artifactId;
        });
        if (!artifact) return;

        const targetSessionId = safe(artifact.session_id || "");
        const currentSessionId = safe(state.activeSessionId || "");

        if (targetSessionId && targetSessionId !== currentSessionId) {
          dispatch("nova:session-switch-request", {
            session_id: targetSessionId
          });
          return;
        }

        openArtifact(artifactId);
      };
    });
  }

  function buildViewerTop(artifact) {
    const img = artifactImage(artifact);
    const created = safe(artifact.created_at);
    const session = safe(artifact.session_id);
    const kind = safe(artifact.kind || "artifact");

    return (
      '<div class="nova-artifact-viewer-head-row">' +
      '<div class="nova-artifact-viewer-kind"><span class="nova-message-badge">' +
      esc(kind) +
      "</span></div>" +
      '<div class="nova-artifact-viewer-session">' +
      esc(session) +
      "</div>" +
      "</div>" +
      (created ? '<div class="nova-artifact-viewer-date">' + esc(created) + "</div>" : "") +
      (img
        ? '<div class="nova-artifact-viewer-main-image"><img src="' +
          esc(img.url) +
          '" alt="' +
          esc(artifact.title || "artifact image") +
          '" loading="lazy"></div>'
        : "")
    );
  }

  function buildViewerActions(artifact) {
    const img = artifactImage(artifact);
    const canReuseImage = !!(artifact && artifact.kind === "generated_image" && img);

    return (
      '<div class="nova-artifact-actions">' +
      '<button class="nova-shell-btn" type="button" data-artifact-copy="' +
      esc(artifact.id) +
      '">Copy</button>' +
      (canReuseImage
        ? '<button class="nova-shell-btn" type="button" data-artifact-reuse-image="' +
          esc(artifact.id) +
          '">Reuse Image</button>'
        : "") +
      '<button class="nova-shell-btn" type="button" data-artifact-open-session="' +
      esc(artifact.id) +
      '">Open Session</button>' +
      "</div>"
    );
  }

  function renderViewer() {
    const titleEl = qs("#artifactViewerTitle");
    const metaEl = qs("#artifactViewerMeta");
    const bodyEl = qs("#artifactViewerBody");
    const viewer = qs("#artifactViewer");

    if (!titleEl || !metaEl || !bodyEl || !viewer) return;

    if (!state.active) {
      viewer.setAttribute("data-empty", "true");
      titleEl.textContent = "No artifact selected";
      metaEl.textContent = "";
      bodyEl.innerHTML = '<div class="nova-artifact-empty-view">Select an artifact to view it here.</div>';
      return;
    }

    const artifact = state.active;
    viewer.setAttribute("data-empty", "false");
    titleEl.textContent = safe(artifact.title || "Untitled");
    metaEl.textContent = safe(artifact.kind || "");

    bodyEl.innerHTML =
      buildViewerTop(artifact) +
      '<div class="nova-artifact-viewer-content">' +
      formatContent(artifact) +
      "</div>" +
      buildViewerActions(artifact);

    const copyBtn = qs("[data-artifact-copy]", bodyEl);
    if (copyBtn) {
      copyBtn.addEventListener("click", async function () {
        try {
          await navigator.clipboard.writeText(safe(artifact.content));
        } catch (_) {}
      });
    }

    const openSessionBtn = qs("[data-artifact-open-session]", bodyEl);
    if (openSessionBtn) {
      openSessionBtn.addEventListener("click", function () {
        const targetSessionId = safe(artifact.session_id || "");
        if (!targetSessionId) return;

        if (targetSessionId !== safe(state.activeSessionId || "")) {
          dispatch("nova:session-switch-request", {
            session_id: targetSessionId
          });
        }
      });
    }

    const reuseBtn = qs("[data-artifact-reuse-image]", bodyEl);
    if (reuseBtn) {
      reuseBtn.addEventListener("click", function () {
        dispatch("nova:artifact-reuse-image", { artifact: artifact });
        if (window.NovaPanels && typeof window.NovaPanels.close === "function") {
          window.NovaPanels.close();
        }
      });
    }
  }

  function formatContent(artifact) {
    let html = esc(safe(artifact.content || ""));
    html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, function (_, alt, src) {
      return (
        '<div class="nova-inline-image-wrap"><img class="nova-inline-image" src="' +
        esc(src) +
        '" alt="' +
        esc(alt || "image") +
        '" loading="lazy"></div>'
      );
    });
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\n/g, "<br>");
    return html;
  }

  function render() {
    renderList();
    renderViewer();
  }

  async function openArtifact(id) {
    if (!id) return;
    state.activeId = id;

    try {
      const res = await fetch(API.read(id), { credentials: "same-origin" });
      const data = await res.json();
      if (!res.ok || data.ok === false) throw new Error(data.error || "read failed");

      state.active = data.artifact || null;
      render();
    } catch (e) {
      console.error(LOG, "open failed", e);
    }
  }

  function bindControls() {
    const search = qs("#artifactSearch");
    const filter = qs("#artifactFilter");
    const refresh = qs("#artifactRefresh");

    if (search) {
      search.addEventListener("input", function () {
        state.search = safe(search.value).trim();
        applyFilterSort();
        render();
      });
    }

    if (filter) {
      filter.addEventListener("change", function () {
        state.filter = safe(filter.value || "all");
        applyFilterSort();
        render();
      });
    }

    if (refresh) {
      refresh.addEventListener("click", function () {
        loadArtifacts();
      });
    }

    window.addEventListener("nova:artifacts-refreshed", function (event) {
      const detail = event.detail || {};
      if (Array.isArray(detail.artifacts) && detail.artifacts.length >= 0) {
        state.artifacts = detail.artifacts.slice();
      }
      if (detail.active_session_id) {
        state.activeSessionId = safe(detail.active_session_id);
      }
      applyFilterSort();
      render();
    });

    window.addEventListener("nova:session-activated", function (event) {
      const detail = event.detail || {};
      state.activeSessionId = safe(detail.session_id || "");
      applyFilterSort();
      render();
    });
  }

  function boot() {
    bindControls();
    loadArtifacts();
    log("ready");
  }

  boot();
})();