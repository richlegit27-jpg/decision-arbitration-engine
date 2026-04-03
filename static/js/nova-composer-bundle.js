(function () {
  "use strict";

  const LOG = "[NovaComposerBundle]";
  const API = {
    state: "/api/state",
    chat: "/api/chat",
    upload: "/api/upload",
    artifacts: "/api/artifacts",
    artifactRead(id) {
      return `/api/artifacts/${encodeURIComponent(id)}`;
    },
    artifactDelete(id) {
      return `/api/artifacts/${encodeURIComponent(id)}`;
    },
    sessionDelete(id) {
      return `/api/sessions/${encodeURIComponent(id)}`;
    },
    sessionRename(id) {
      return `/api/sessions/${encodeURIComponent(id)}/rename`;
    },
    sessionPin(id) {
      return `/api/sessions/${encodeURIComponent(id)}/pin`;
    }
  };

  const STORAGE = {
    sidebarCollapsed: "nova.sidebar.collapsed",
    rightRailPanel: "nova.rightRail.panel"
  };

  const state = {
    sessionId: "",
    session: null,
    sessions: [],
    messages: [],
    memory: [],
    artifacts: [],
    sending: false,
    uploading: false,
    activePanel: "",
    activeArtifactId: "",
    attachmentFiles: []
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

  function fmtDate(value) {
    if (!value) return "";
    try {
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return safe(value);
      return d.toLocaleString();
    } catch (_) {
      return safe(value);
    }
  }

  function artifactKindLabel(kind) {
    const map = {
      chat_reply: "Reply",
      image_generation: "Image",
      image_analysis: "Image Analysis",
      video_analysis: "Video Analysis",
      web_result: "Web"
    };
    return map[kind] || safe(kind || "Artifact").replace(/_/g, " ");
  }

  function saveLocalState() {
    try {
      localStorage.setItem(STORAGE.sidebarCollapsed, isSidebarCollapsed() ? "1" : "0");
      localStorage.setItem(STORAGE.rightRailPanel, state.activePanel || "");
    } catch (_) {}
  }

  function loadLocalState() {
    try {
      const sidebarCollapsed = localStorage.getItem(STORAGE.sidebarCollapsed) === "1";
      const panel = localStorage.getItem(STORAGE.rightRailPanel) || "";
      if (sidebarCollapsed) {
        document.body.classList.add("nova-sidebar-collapsed");
      } else {
        document.body.classList.remove("nova-sidebar-collapsed");
      }
      if (panel) {
        openPanel(panel);
      } else {
        closeRightRail();
      }
    } catch (_) {
      closeRightRail();
    }
  }

  function isSidebarCollapsed() {
    return document.body.classList.contains("nova-sidebar-collapsed");
  }

  function setSidebarCollapsed(collapsed) {
    document.body.classList.toggle("nova-sidebar-collapsed", !!collapsed);
    const sidebarToggle = qs("#sidebarToggle");
    const mobileSidebarToggle = qs("#mobileSidebarToggle");

    if (sidebarToggle) {
      sidebarToggle.setAttribute("aria-label", collapsed ? "Open sidebar" : "Collapse sidebar");
      sidebarToggle.title = collapsed ? "Open sidebar" : "Collapse sidebar";
    }
    if (mobileSidebarToggle) {
      mobileSidebarToggle.classList.toggle("nova-hidden", !collapsed);
    }
    saveLocalState();
  }

  function toggleSidebar() {
    setSidebarCollapsed(!isSidebarCollapsed());
  }

  function setTopbarSubtitle(text) {
    const el = qs("#topbarSubtitle");
    if (el) {
      el.textContent = text || "Ready";
    }
  }

  function openPanel(panelName) {
    state.activePanel = panelName || "";
    const rightRail = qs("#rightRail");
    const title = qs("#rightRailTitle");
    const subtitle = qs("#rightRailSubtitle");

    qsa(".nova-right-panel").forEach((panel) => {
      const isActive = panel.id === `${panelName}Panel`;
      panel.hidden = !isActive;
      panel.setAttribute("aria-hidden", isActive ? "false" : "true");
      panel.classList.toggle("is-active", isActive);
    });

    if (!panelName) {
      closeRightRail();
      return;
    }

    if (rightRail) {
      rightRail.classList.remove("is-collapsed");
    }

    if (title && subtitle) {
      if (panelName === "memory") {
        title.textContent = "Memory";
        subtitle.textContent = "Saved memory items and context";
      } else if (panelName === "artifacts") {
        title.textContent = "Artifacts";
        subtitle.textContent = "Saved outputs and generated files";
      } else if (panelName === "web") {
        title.textContent = "Web";
        subtitle.textContent = "Saved web fetch results";
      } else {
        title.textContent = "Panel";
        subtitle.textContent = "Open a panel";
      }
    }

    updatePanelToggleState();
    saveLocalState();
  }

  function closeRightRail() {
    state.activePanel = "";
    const rightRail = qs("#rightRail");
    if (rightRail) {
      rightRail.classList.add("is-collapsed");
    }

    qsa(".nova-right-panel").forEach((panel) => {
      panel.hidden = true;
      panel.setAttribute("aria-hidden", "true");
      panel.classList.remove("is-active");
    });

    updatePanelToggleState();
    saveLocalState();
  }

  function togglePanel(panelName) {
    if (state.activePanel === panelName) {
      closeRightRail();
      return;
    }
    openPanel(panelName);
  }

  function updatePanelToggleState() {
    const map = {
      memory: qs("#memoryPanelToggle"),
      artifacts: qs("#artifactsPanelToggle"),
      web: qs("#webPanelToggle")
    };

    Object.keys(map).forEach((key) => {
      const btn = map[key];
      if (!btn) return;
      btn.classList.toggle("is-active", state.activePanel === key);
      btn.setAttribute("aria-pressed", state.activePanel === key ? "true" : "false");
    });
  }

  function renderEmptyState() {
    const empty = qs("#novaEmptyState");
    if (!empty) return;
    empty.style.display = state.messages.length ? "none" : "grid";
  }

  function renderSessions() {
    const root = qs("#sessionsList");
    if (!root) return;

    if (!state.sessions.length) {
      root.innerHTML = `
        <div class="nova-empty-panel-state">
          <div class="nova-empty-panel-title">No sessions</div>
          <div class="nova-empty-panel-copy">Start a chat and it will appear here.</div>
        </div>
      `;
      return;
    }

    root.innerHTML = state.sessions
      .map((session) => {
        const active = safe(session.id) === safe(state.sessionId);
        const pinned = !!session.pinned;

        return `
          <div class="nova-session-card ${active ? "is-active" : ""}">
            <button
              class="nova-session-main"
              type="button"
              data-session-open="${esc(session.id)}"
              title="${esc(session.title || "New chat")}"
            >
              <div class="nova-session-title-row">
                <div class="nova-session-title">${esc(session.title || "New chat")}</div>
                ${pinned ? `<span class="nova-session-pin-badge">Pinned</span>` : ""}
              </div>
              <div class="nova-session-meta">
                <span>${esc(String(session.message_count || 0))} msg</span>
                <span>${esc(fmtDate(session.updated_at))}</span>
              </div>
              <div class="nova-session-preview">${esc(session.last_message_preview || "")}</div>
            </button>

            <div class="nova-session-actions">
              <button
                class="nova-session-action-btn"
                type="button"
                data-session-pin="${esc(session.id)}"
                title="${pinned ? "Unpin session" : "Pin session"}"
                aria-label="${pinned ? "Unpin session" : "Pin session"}"
              >
                ${pinned ? "★" : "☆"}
              </button>

              <button
                class="nova-session-action-btn"
                type="button"
                data-session-rename="${esc(session.id)}"
                title="Rename session"
                aria-label="Rename session"
              >
                ✎
              </button>

              <button
                class="nova-session-delete"
                type="button"
                data-session-delete="${esc(session.id)}"
                title="Delete session"
                aria-label="Delete session"
              >
                ×
              </button>
            </div>
          </div>
        `;
      })
      .join("");
  }

  function renderMessages() {
    const root = qs("#messages");
    if (!root) return;

    root.innerHTML = state.messages
      .map((msg) => {
        const role = safe(msg.role || "assistant");
        const isUser = role === "user";
        const meta = msg.meta || {};
        const badges = [];

        if (meta.artifact_kind) {
          badges.push(`<span class="nova-message-badge">${esc(artifactKindLabel(meta.artifact_kind))}</span>`);
        }
        if (meta.web && meta.web.used) {
          badges.push(`<span class="nova-message-badge">Web</span>`);
        }
        if (meta.image_used) {
          badges.push(`<span class="nova-message-badge">Image</span>`);
        }

        return `
          <div class="nova-message ${isUser ? "nova-message-user" : "nova-message-assistant"}">
            <div class="nova-message-inner">
              <div class="nova-message-head">
                <div class="nova-message-role">${esc(role)}</div>
                <div class="nova-message-time">${esc(fmtDate(msg.created_at))}</div>
              </div>

              ${badges.length ? `<div class="nova-message-badges">${badges.join("")}</div>` : ""}

              <div class="nova-message-markdown">${renderMessageContent(msg.content || "")}</div>
            </div>
          </div>
        `;
      })
      .join("");

    root.scrollTop = root.scrollHeight;
    renderEmptyState();
  }

  function renderMessageContent(text) {
    const value = safe(text);
    const imageMarkdown = value.match(/!\[[^\]]*?\]\((\/api\/uploads\/[^)]+)\)/i);

    if (imageMarkdown) {
      const plain = value.replace(imageMarkdown[0], "").trim();
      return `
        ${plain ? `<p>${esc(plain).replace(/\n/g, "<br>")}</p>` : ""}
        <div class="nova-message-media-card">
          <div class="nova-message-media-head">
            <div class="nova-message-media-title">Generated image</div>
          </div>
          <div class="nova-message-media-body">
            <img src="${esc(imageMarkdown[1])}" alt="Generated image" />
          </div>
        </div>
      `;
    }

    return `<p>${esc(value).replace(/\n/g, "<br>")}</p>`;
  }

  function renderMemory() {
    const root = qs("#memoryList");
    if (!root) return;

    if (!state.memory.length) {
      root.innerHTML = `
        <div class="nova-empty-panel-state">
          <div class="nova-empty-panel-title">No memory yet</div>
          <div class="nova-empty-panel-copy">Saved memory items will appear here.</div>
        </div>
      `;
      return;
    }

    root.innerHTML = state.memory
      .map((item) => {
        return `
          <div class="nova-memory-card">
            <div class="nova-memory-card-title">${esc(item.title || item.key || "Memory item")}</div>
            <div class="nova-memory-card-meta">${esc(fmtDate(item.updated_at || item.created_at))}</div>
            <div class="nova-memory-card-copy">${esc(item.value || item.content || item.text || "")}</div>
          </div>
        `;
      })
      .join("");
  }

  function getFilteredArtifacts() {
    const q = safe(qs("#artifactSearchInput")?.value).trim().toLowerCase();
    const filter = safe(qs("#artifactFilterSelect")?.value || "all");

    return state.artifacts.filter((artifact) => {
      if (filter !== "all" && safe(artifact.kind) !== filter) {
        return false;
      }

      if (!q) return true;

      const haystack = [
        artifact.title,
        artifact.preview,
        artifact.kind
      ]
        .map((x) => safe(x).toLowerCase())
        .join(" ");

      return haystack.includes(q);
    });
  }

  function renderArtifacts() {
    const listRoot = qs("#artifactsList");
    const viewerRoot = qs("#artifactViewer");
    if (!listRoot || !viewerRoot) return;

    const filtered = getFilteredArtifacts();

    if (!filtered.length) {
      state.activeArtifactId = "";
      listRoot.innerHTML = `
        <div class="nova-empty-panel-state">
          <div class="nova-empty-panel-title">No artifacts</div>
          <div class="nova-empty-panel-copy">Generate an image, save a reply, or fetch the web.</div>
        </div>
      `;
      viewerRoot.innerHTML = `
        <div class="nova-artifact-viewer-empty">
          <div class="nova-empty-panel-title">No artifact selected</div>
          <div class="nova-empty-panel-copy">Select an artifact to view it here.</div>
        </div>
      `;
      return;
    }

    if (!filtered.some((a) => safe(a.id) === safe(state.activeArtifactId))) {
      state.activeArtifactId = safe(filtered[0].id);
    }

    listRoot.innerHTML = filtered
      .map((artifact) => {
        const active = safe(artifact.id) === safe(state.activeArtifactId);
        return `
          <div class="nova-artifact-card ${active ? "is-active" : ""}">
            <button
              class="nova-artifact-card-btn"
              type="button"
              data-artifact-open="${esc(artifact.id)}"
            >
              <div class="nova-artifact-card-top">
                <span class="nova-artifact-kind-badge">${esc(artifactKindLabel(artifact.kind))}</span>
                <span class="nova-artifact-time">${esc(fmtDate(artifact.updated_at || artifact.created_at))}</span>
              </div>
              <div class="nova-artifact-card-title">${esc(artifact.title || "Artifact")}</div>
              <div class="nova-artifact-card-preview">${esc(artifact.preview || "")}</div>
            </button>
          </div>
        `;
      })
      .join("");

    renderArtifactViewer();
  }

  async function renderArtifactViewer() {
    const root = qs("#artifactViewer");
    if (!root) return;

    const artifactId = safe(state.activeArtifactId);
    if (!artifactId) {
      root.innerHTML = `
        <div class="nova-artifact-viewer-empty">
          <div class="nova-empty-panel-title">No artifact selected</div>
          <div class="nova-empty-panel-copy">Select an artifact to view it here.</div>
        </div>
      `;
      return;
    }

    root.innerHTML = `
      <div class="nova-artifact-viewer-empty">
        <div class="nova-empty-panel-title">Loading artifact...</div>
        <div class="nova-empty-panel-copy">Opening ${esc(artifactId)}</div>
      </div>
    `;

    try {
      const res = await fetch(API.artifactRead(artifactId), { credentials: "same-origin" });
      const data = await res.json();

      if (!res.ok || !data || !data.ok || !data.artifact) {
        throw new Error((data && data.error) || "Artifact load failed.");
      }

      const artifact = data.artifact;
      const viewer = artifact.viewer || {};
      const meta = artifact.meta || {};
      const imageUrl = viewer.image_url || viewer.media_url || "";
      const copy = viewer.copy || artifact.content || artifact.preview || "";
      const prompt = viewer.prompt || meta.prompt || "";

      root.innerHTML = `
        <div class="nova-viewer-shell">
          <div class="nova-viewer-head">
            <div class="nova-viewer-head-top">
              <div class="nova-viewer-title-wrap">
                <div class="nova-viewer-title">${esc(artifact.title || "Artifact")}</div>
                <div class="nova-viewer-sub">
                  ${esc(artifactKindLabel(artifact.kind))} · ${esc(fmtDate(artifact.updated_at || artifact.created_at))}
                </div>
              </div>

              <div class="nova-viewer-actions">
                ${imageUrl ? `<a class="nova-viewer-action" href="${esc(imageUrl)}" target="_blank" rel="noopener">Open</a>` : ""}
                <button class="nova-viewer-action" type="button" data-artifact-copy="${esc(artifact.id)}">Copy</button>
                <button class="nova-viewer-action nova-viewer-action-danger" type="button" data-artifact-delete="${esc(artifact.id)}">Delete</button>
              </div>
            </div>
          </div>

          <div class="nova-viewer-body">
            ${imageUrl ? `
              <div class="nova-viewer-media-wrap">
                <img class="nova-viewer-image" src="${esc(imageUrl)}" alt="${esc(artifact.title || "Artifact image")}" />
              </div>
            ` : ""}

            ${prompt ? `
              <div class="nova-meta-card">
                <div class="nova-meta-label">Prompt</div>
                <div class="nova-meta-value">${esc(prompt)}</div>
              </div>
            ` : ""}

            ${copy ? `
              <div class="nova-meta-card">
                <div class="nova-meta-label">Content</div>
                <div class="nova-viewer-copy">${esc(copy)}</div>
              </div>
            ` : ""}

            <div class="nova-viewer-meta-grid">
              <div class="nova-meta-card">
                <div class="nova-meta-label">Artifact ID</div>
                <div class="nova-meta-value">${esc(artifact.id || "")}</div>
              </div>
              <div class="nova-meta-card">
                <div class="nova-meta-label">Session</div>
                <div class="nova-meta-value">${esc(artifact.session_id || "")}</div>
              </div>
            </div>
          </div>
        </div>
      `;
    } catch (err) {
      root.innerHTML = `
        <div class="nova-artifact-viewer-empty">
          <div class="nova-empty-panel-title">Artifact failed to load</div>
          <div class="nova-empty-panel-copy">${esc(err.message || "Unknown error")}</div>
        </div>
      `;
    }
  }

  function renderWeb() {
    const root = qs("#webList");
    if (!root) return;

    const webItems = state.artifacts.filter((artifact) => safe(artifact.kind) === "web_result");

    if (!webItems.length) {
      root.innerHTML = `
        <div class="nova-empty-panel-state">
          <div class="nova-empty-panel-title">No web results</div>
          <div class="nova-empty-panel-copy">Use /web https://example.com or paste a URL in chat.</div>
        </div>
      `;
      return;
    }

    root.innerHTML = webItems
      .map((artifact) => {
        return `
          <div class="nova-web-card">
            <div class="nova-web-card-title">${esc(artifact.title || "Web result")}</div>
            <div class="nova-web-card-url">${esc(fmtDate(artifact.updated_at || artifact.created_at))}</div>
            <div class="nova-web-card-copy">${esc(artifact.preview || "")}</div>
            <div class="nova-web-actions">
              <button class="nova-viewer-action" type="button" data-web-open-artifact="${esc(artifact.id)}">Open</button>
            </div>
          </div>
        `;
      })
      .join("");
  }

  async function refreshState(options) {
    const opts = options || {};
    const url = state.sessionId
      ? `${API.state}?session_id=${encodeURIComponent(state.sessionId)}`
      : API.state;

    log("refreshState request", { url });

    const res = await fetch(url, { credentials: "same-origin", cache: "no-store" });
    const data = await res.json();
    log("refreshState response", data);

    if (!res.ok || !data || !data.ok) {
      throw new Error((data && data.error) || "State load failed.");
    }

    state.sessions = Array.isArray(data.sessions) ? data.sessions : [];
    state.artifacts = Array.isArray(data.artifacts) ? data.artifacts : [];
    state.memory = Array.isArray(data.memory) ? data.memory : [];
    state.messages = Array.isArray(data.messages) ? data.messages : [];
    state.session = data.session || null;
    state.sessionId = safe(data.active_session_id || (data.session && data.session.id) || "");

    if (!opts.preserveArtifactSelection) {
      if (!state.artifacts.some((a) => safe(a.id) === safe(state.activeArtifactId))) {
        state.activeArtifactId = state.artifacts[0] ? safe(state.artifacts[0].id) : "";
      }
    }

    renderSessions();
    renderMessages();
    renderMemory();
    renderArtifacts();
    renderWeb();

    setTopbarSubtitle(state.session ? (state.session.title || "Ready") : "Ready");
  }

  function buildAttachmentsPayload() {
    return state.attachmentFiles.map((item) => ({
      id: item.id,
      name: item.name,
      stored_name: item.stored_name,
      url: item.url,
      kind: item.kind,
      mime_type: item.mime_type
    }));
  }

  function renderAttachmentChips() {
    const root = qs("#attachmentChips");
    if (!root) return;

    if (!state.attachmentFiles.length) {
      root.innerHTML = "";
      return;
    }

    root.innerHTML = state.attachmentFiles
      .map((file, index) => {
        return `
          <span class="nova-attachment-chip">
            <span>${esc(file.name || "Attachment")}</span>
            <button
              class="nova-attachment-chip-remove"
              type="button"
              data-attachment-remove="${esc(String(index))}"
              aria-label="Remove attachment"
              title="Remove attachment"
            >
              ×
            </button>
          </span>
        `;
      })
      .join("");
  }

  async function uploadSelectedFiles(files) {
    if (!files || !files.length) return;

    const form = new FormData();
    Array.from(files).forEach((file) => form.append("files", file));

    state.uploading = true;
    try {
      const res = await fetch(API.upload, {
        method: "POST",
        body: form,
        credentials: "same-origin"
      });
      const data = await res.json();

      if (!res.ok || !data || !data.ok) {
        throw new Error((data && data.error) || "Upload failed.");
      }

      const uploaded = Array.isArray(data.files) ? data.files : [];
      state.attachmentFiles = state.attachmentFiles.concat(uploaded);
      renderAttachmentChips();
    } finally {
      state.uploading = false;
    }
  }

  async function sendMessage() {
    if (state.sending) return;

    const input = qs("#chatInput");
    if (!input) return;

    const content = safe(input.value).trim();
    if (!content && !state.attachmentFiles.length) return;

    state.sending = true;
    const sendBtn = qs("#sendBtn");
    if (sendBtn) sendBtn.disabled = true;

    try {
      const res = await fetch(API.chat, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          content,
          session_id: state.sessionId || "",
          attachments: buildAttachmentsPayload()
        })
      });

      const data = await res.json();

      if (!res.ok || !data || !data.ok) {
        throw new Error((data && data.error) || "Chat request failed.");
      }

      input.value = "";
      state.attachmentFiles = [];
      renderAttachmentChips();

      if (data.session && data.session.id) {
        state.sessionId = safe(data.session.id);
      }

      await refreshState({ preserveArtifactSelection: false });

      if (data.artifact && data.artifact.id) {
        state.activeArtifactId = safe(data.artifact.id);
        if (data.artifact.kind === "web_result") {
          openPanel("web");
        } else {
          openPanel("artifacts");
        }
        renderArtifacts();
        renderWeb();
      }
    } finally {
      state.sending = false;
      if (sendBtn) sendBtn.disabled = false;
    }
  }

  async function deleteArtifact(id) {
    if (!id) return;

    const ok = window.confirm("Delete this artifact?");
    if (!ok) return;

    try {
      const res = await fetch(API.artifactDelete(id), {
        method: "DELETE",
        credentials: "same-origin"
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data || !data.ok) {
        throw new Error((data && data.error) || "Artifact delete endpoint is missing or failed.");
      }

      if (safe(state.activeArtifactId) === safe(id)) {
        state.activeArtifactId = "";
      }

      await refreshState({ preserveArtifactSelection: false });
    } catch (err) {
      alert(err.message || "Artifact delete failed.");
    }
  }

  async function deleteSession(id) {
    if (!id) return;

    const ok = window.confirm("Delete this session?");
    if (!ok) return;

    try {
      const deletingActive = safe(state.sessionId) === safe(id);

      const res = await fetch(API.sessionDelete(id), {
        method: "DELETE",
        credentials: "same-origin"
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data || !data.ok) {
        throw new Error((data && data.error) || "Session delete endpoint is missing or failed.");
      }

      const nextSessionId = safe(data.next_session_id || "");

      if (deletingActive) {
        state.sessionId = nextSessionId;
        state.session = null;
        state.messages = [];
        state.artifacts = [];
        state.activeArtifactId = "";
      } else if (!state.sessionId) {
        state.sessionId = nextSessionId;
      }

      await refreshState({ preserveArtifactSelection: false });

      if (!state.sessionId) {
        state.session = null;
        state.messages = [];
        state.artifacts = [];
        state.activeArtifactId = "";
        renderSessions();
        renderMessages();
        renderArtifacts();
        renderWeb();
        setTopbarSubtitle("Ready");
      }
    } catch (err) {
      alert(err.message || "Session delete failed.");
    }
  }

  async function renameSession(id) {
    if (!id) return;

    const current = state.sessions.find((s) => safe(s.id) === safe(id));
    const currentTitle = safe(current && current.title ? current.title : "New chat");
    const title = window.prompt("Rename session", currentTitle);

    if (title == null) return;

    const trimmed = safe(title).trim();
    if (!trimmed) {
      alert("Session title is required.");
      return;
    }

    try {
      const res = await fetch(API.sessionRename(id), {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ title: trimmed })
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data || !data.ok) {
        throw new Error((data && data.error) || "Session rename failed.");
      }

      await refreshState({ preserveArtifactSelection: true });
    } catch (err) {
      alert(err.message || "Session rename failed.");
    }
  }

  async function pinSession(id) {
    if (!id) return;

    const current = state.sessions.find((s) => safe(s.id) === safe(id));
    const nextPinned = !Boolean(current && current.pinned);

    try {
      const res = await fetch(API.sessionPin(id), {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ pinned: nextPinned })
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data || !data.ok) {
        throw new Error((data && data.error) || "Session pin failed.");
      }

      await refreshState({ preserveArtifactSelection: true });
    } catch (err) {
      alert(err.message || "Session pin failed.");
    }
  }

  async function createNewChat() {
    state.sessionId = "";
    state.session = null;
    state.messages = [];
    state.artifacts = [];
    state.activeArtifactId = "";
    renderMessages();
    renderArtifacts();
    renderWeb();
    setTopbarSubtitle("New chat");
    qs("#chatInput")?.focus();
    await refreshState({ preserveArtifactSelection: true });
  }

  function handleClick(event) {
    const target = event.target.closest("[data-session-open],[data-session-delete],[data-session-rename],[data-session-pin],[data-artifact-open],[data-artifact-delete],[data-artifact-copy],[data-web-open-artifact],[data-attachment-remove]");
    if (!target) return;

    const sessionOpen = target.getAttribute("data-session-open");
    const sessionDelete = target.getAttribute("data-session-delete");
    const sessionRename = target.getAttribute("data-session-rename");
    const sessionPin = target.getAttribute("data-session-pin");
    const artifactOpen = target.getAttribute("data-artifact-open");
    const artifactDelete = target.getAttribute("data-artifact-delete");
    const artifactCopy = target.getAttribute("data-artifact-copy");
    const webOpenArtifact = target.getAttribute("data-web-open-artifact");
    const attachmentRemove = target.getAttribute("data-attachment-remove");

    if (sessionOpen) {
      state.sessionId = sessionOpen;
      refreshState({ preserveArtifactSelection: true });
      return;
    }

    if (sessionDelete) {
      deleteSession(sessionDelete);
      return;
    }

    if (sessionRename) {
      renameSession(sessionRename);
      return;
    }

    if (sessionPin) {
      pinSession(sessionPin);
      return;
    }

    if (artifactOpen) {
      state.activeArtifactId = artifactOpen;
      renderArtifacts();
      return;
    }

    if (artifactDelete) {
      deleteArtifact(artifactDelete);
      return;
    }

    if (artifactCopy) {
      navigator.clipboard.writeText(safe(qs(".nova-viewer-copy")?.textContent || ""));
      return;
    }

    if (webOpenArtifact) {
      state.activeArtifactId = webOpenArtifact;
      openPanel("artifacts");
      renderArtifacts();
      return;
    }

    if (attachmentRemove != null) {
      const idx = Number(attachmentRemove);
      if (!Number.isNaN(idx)) {
        state.attachmentFiles.splice(idx, 1);
        renderAttachmentChips();
      }
    }
  }

  function wireEvents() {
    qs("#sidebarToggle")?.addEventListener("click", toggleSidebar);
    qs("#mobileSidebarToggle")?.addEventListener("click", () => setSidebarCollapsed(false));
    qs("#rightRailClose")?.addEventListener("click", closeRightRail);

    qs("#memoryPanelToggle")?.addEventListener("click", () => togglePanel("memory"));
    qs("#artifactsPanelToggle")?.addEventListener("click", () => togglePanel("artifacts"));
    qs("#webPanelToggle")?.addEventListener("click", () => togglePanel("web"));

    qs("#sendBtn")?.addEventListener("click", sendMessage);
    qs("#newChatBtn")?.addEventListener("click", createNewChat);

    qs("#uploadBtn")?.addEventListener("click", () => qs("#fileInput")?.click());
    qs("#fileInput")?.addEventListener("change", async (e) => {
      const files = e.target.files;
      await uploadSelectedFiles(files);
      e.target.value = "";
    });

    qs("#chatInput")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    qs("#artifactSearchInput")?.addEventListener("input", renderArtifacts);
    qs("#artifactFilterSelect")?.addEventListener("change", renderArtifacts);

    document.addEventListener("click", handleClick);
  }

  async function boot() {
    log("boot start");
    wireEvents();
    loadLocalState();
    await refreshState({ preserveArtifactSelection: false });
    log("boot complete");
  }

  boot().catch((err) => {
    console.error(LOG, err);
    setTopbarSubtitle(err.message || "Boot failed");
  });
})();