(() => {
  "use strict";

  const API = {
    state: "/api/state",
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
    memory: "/api/memory",
    deleteMemory: "/api/memory/delete",
    newSession: "/api/session/new",
    renameSession: "/api/session/rename",
    deleteSession: "/api/session/delete",
    duplicateSession: "/api/session/duplicate",
    pinSession: "/api/session/pin",
    exportSession: "/api/session/export",
    stream: "/api/chat/stream",
    upload: "/api/upload",
  };

  const STORAGE_KEYS = {
    theme: "nova_mobile_theme",
    background: "nova_mobile_background",
  };

  const app = {
    state: {
      sessions: [],
      messages: [],
      memoryItems: [],
      activeSessionId: null,
      currentModel: "gpt-4.1-mini",
      isSending: false,
      attachedFiles: [],
      currentAssistantBubble: null,
      lastUserMessage: "",
    },
  };

  window.NovaMobileDebug = {
    app,
    getState() {
      return app.state;
    },
    getMessages() {
      return app.state.messages || [];
    },
    getLastMessage() {
      const messages = app.state.messages || [];
      return messages[messages.length - 1] || null;
    },
    getLastAssistant() {
      const messages = app.state.messages || [];
      for (let i = messages.length - 1; i >= 0; i -= 1) {
        if (String(messages[i]?.role || "").toLowerCase() === "assistant") {
          return messages[i];
        }
      }
      return null;
    },
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function safeText(value) {
    return String(value ?? "").trim();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function nowUnix() {
    return Math.floor(Date.now() / 1000);
  }

  function formatTime(ts) {
    if (!ts) return "";
    try {
      return new Date(Number(ts) * 1000).toLocaleString();
    } catch {
      return "";
    }
  }

  function getSessionId(session) {
    return session?.id || session?.session_id || "";
  }

  function getMessageTimestamp(msg) {
    return msg?.created_at || msg?.timestamp || nowUnix();
  }

  function getCurrentSession() {
    return (
      app.state.sessions.find(
        (session) => getSessionId(session) === app.state.activeSessionId
      ) || null
    );
  }

  function getLastAssistantMessage() {
    for (let i = app.state.messages.length - 1; i >= 0; i -= 1) {
      if (safeText(app.state.messages[i]?.role).toLowerCase() === "assistant") {
        return app.state.messages[i];
      }
    }
    return null;
  }

  function getLastUserMessage() {
    for (let i = app.state.messages.length - 1; i >= 0; i -= 1) {
      if (safeText(app.state.messages[i]?.role).toLowerCase() === "user") {
        return app.state.messages[i];
      }
    }
    return null;
  }

  function setSendDisabled(disabled) {
    const sendBtn = byId("mobileSendBtn");
    const attachBtn = byId("mobileAttachBtn");
    const input = byId("mobileMessageInput");

    if (sendBtn) {
      sendBtn.disabled = disabled;
      sendBtn.textContent = disabled ? "..." : "Send";
    }

    if (attachBtn) {
      attachBtn.disabled = disabled;
    }

    if (input) {
      input.disabled = disabled;
    }
  }

  async function apiGet(url) {
    const res = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`GET failed: ${url}`);
    }

    return res.json();
  }

  async function apiPost(url, payload) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    });

    if (!res.ok) {
      let msg = `POST failed: ${url}`;
      try {
        const data = await res.json();
        msg = data.error || data.detail || data.message || msg;
      } catch {}
      throw new Error(msg);
    }

    return res.json();
  }

  async function uploadFiles(files) {
    const list = Array.isArray(files) ? files : [];
    if (!list.length) return [];

    const formData = new FormData();
    for (const file of list) {
      formData.append("files", file);
    }

    const res = await fetch(API.upload, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      throw new Error("Upload failed");
    }

    const data = await res.json();
    return Array.isArray(data.files) ? data.files : [];
  }

  function setStatus(text) {
    const el = byId("mobileModelStatus");
    if (el) {
      el.textContent = safeText(text || "Model ready");
    }
  }

  function updateHeader() {
    const titleEl = byId("mobileChatTitle");
    const subtitleEl = byId("mobileChatSubtitle");
    const currentSession = getCurrentSession();

    if (titleEl) {
      titleEl.textContent = currentSession?.title || "Nova";
    }

    if (subtitleEl) {
      subtitleEl.textContent = app.state.isSending
        ? "Thinking..."
        : `${app.state.messages.length || 0} messages`;
    }
  }

  function openScreen(screenId) {
    const el = byId(screenId);
    if (!el) return;
    el.classList.remove("hidden");
    el.setAttribute("aria-hidden", "false");
    document.body.classList.add("mobile-screen-open");
  }

  function closeScreen(screenId) {
    const el = byId(screenId);
    if (!el) return;
    el.classList.add("hidden");
    el.setAttribute("aria-hidden", "true");

    const menuOpen = byId("mobileMenuScreen") && !byId("mobileMenuScreen").classList.contains("hidden");
    const memoryOpen = byId("mobileMemoryScreen") && !byId("mobileMemoryScreen").classList.contains("hidden");

    if (!menuOpen && !memoryOpen) {
      document.body.classList.remove("mobile-screen-open");
    }
  }

  function closeAllScreens() {
    closeScreen("mobileMenuScreen");
    closeScreen("mobileMemoryScreen");
  }

  function autosizeInput() {
    const input = byId("mobileMessageInput");
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  }

  function scrollMessagesToBottom(behavior = "auto") {
    const container = byId("mobileChatMessages");
    if (!container) return;

    try {
      container.scrollTo({
        top: container.scrollHeight,
        behavior,
      });
    } catch {
      container.scrollTop = container.scrollHeight;
    }
  }

  function applyTheme(theme) {
    const value = theme === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", value);
    localStorage.setItem(STORAGE_KEYS.theme, value);
  }

  function cycleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    applyTheme(current === "dark" ? "light" : "dark");
    setStatus(`Theme: ${document.documentElement.getAttribute("data-theme")}`);
  }

  function applyBackground(mode) {
    const body = document.body;
    if (!body) return;

    body.dataset.mobileBackground = mode;
    localStorage.setItem(STORAGE_KEYS.background, mode);

    if (mode === "flat") {
      body.style.background = "#08101f";
    } else if (mode === "deep") {
      body.style.background =
        "linear-gradient(180deg, #060d19 0%, #08101f 50%, #0d1730 100%)";
    } else {
      body.style.background =
        "radial-gradient(circle at top, rgba(90, 132, 255, 0.16), transparent 32%), linear-gradient(180deg, #0d1730 0%, #08101f 100%)";
    }
  }

  function cycleBackground() {
    const current = document.body?.dataset?.mobileBackground || "glow";
    const next = current === "glow" ? "deep" : current === "deep" ? "flat" : "glow";
    applyBackground(next);
    setStatus(`Background: ${next}`);
  }

  function initAppearance() {
    applyTheme(localStorage.getItem(STORAGE_KEYS.theme) || "dark");
    applyBackground(localStorage.getItem(STORAGE_KEYS.background) || "glow");
  }

  function renderAttachedFiles() {
    const bar = byId("mobileAttachedFiles");
    if (!bar) return;

    if (!app.state.attachedFiles.length) {
      bar.innerHTML = "";
      return;
    }

    bar.innerHTML = app.state.attachedFiles
      .map(
        (file, index) => `
          <div class="mobile-file-chip">
            <span>${escapeHtml(file.name)} (${Math.max(1, Math.round((file.size || 0) / 1024))} KB)</span>
            <button type="button" class="mobile-file-chip-remove" data-file-index="${index}" aria-label="Remove file">✕</button>
          </div>
        `
      )
      .join("");

    bar.querySelectorAll("[data-file-index]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const index = Number(btn.getAttribute("data-file-index"));
        if (Number.isInteger(index) && index >= 0) {
          app.state.attachedFiles.splice(index, 1);
          renderAttachedFiles();
          setStatus("Attachment removed");
        }
      });
    });
  }

  function renderEmptyState(container) {
    container.innerHTML = `
      <div class="mobile-empty-state">
        <div class="mobile-empty-card">
          <div class="mobile-empty-title">Nova is ready</div>
          <div class="mobile-empty-subtitle">Send a message or continue your current workflow.</div>
        </div>
      </div>
    `;
  }

  // MOBILE_SOURCE_CARDS_RENDER_LOCK
  function renderMobileSourceCards(msg) {
    const meta = msg && typeof msg.meta === "object" && msg.meta ? msg.meta : {};
    const sources = Array.isArray(meta.sources)
      ? meta.sources
      : Array.isArray(msg?.sources)
      ? msg.sources
      : [];

    if (!sources.length) return "";

    const cards = sources.slice(0, 5).map((item, index) => {
      const title = safeText(item.title || item.name || item.url || `Source ${index + 1}`);
      const source = safeText(item.source || item.domain || item.publisher || "Source");
      const snippet = safeText(item.snippet || item.description || "");
      const url = safeText(item.url || item.href || item.link || "");

      return `
        <button
          type="button"
          class="mobile-source-card"
          data-mobile-source-url="${escapeHtml(url)}"
          data-mobile-source-title="${escapeHtml(title)}"
        >
          <div class="mobile-source-card-top">
            <span class="mobile-source-number">${index + 1}</span>
            <span class="mobile-source-domain">${escapeHtml(source)}</span>
          </div>
          <div class="mobile-source-title">${escapeHtml(title)}</div>
          ${
            snippet
              ? `<div class="mobile-source-snippet">${escapeHtml(snippet)}</div>`
              : ""
          }
        </button>
      `;
    }).join("");

    return `<div class="mobile-source-list">${cards}</div>`;
  }

  // MOBILE_FINAL_RESPONSE_IMAGE_RENDER_LOCK
  function getFinalResponseImageUrl(item) {
    if (!item || typeof item !== "object") return "";

    if (item.image_url) return String(item.image_url);
    if (item.imageUrl) return String(item.imageUrl);
    if (item.preview) return String(item.preview);

    const assistant = item.assistant_message;
    if (assistant && typeof assistant === "object") {
      if (assistant.image_url) return String(assistant.image_url);
      if (assistant.imageUrl) return String(assistant.imageUrl);
      if (assistant.preview) return String(assistant.preview);
      if (assistant.url) return String(assistant.url);
    }

    const artifact = item.saved_artifact || item.artifact;
    if (artifact && typeof artifact === "object") {
      if (artifact.image_url) return String(artifact.image_url);
      if (artifact.imageUrl) return String(artifact.imageUrl);
      if (artifact.preview) return String(artifact.preview);
      if (artifact.url) return String(artifact.url);

      if (artifact.meta && artifact.meta.image_url) {
        return String(artifact.meta.image_url);
      }

      if (artifact.viewer && artifact.viewer.image_url) {
        return String(artifact.viewer.image_url);
      }
    }

    return "";
  }

  function renderFinalResponseImage(item) {
    const imageUrl = getFinalResponseImageUrl(item);

    if (!imageUrl) return "";

    return `
      <div class="mobile-generated-image-wrap">
        <img
          class="mobile-generated-image"
          src="${escapeHtml(imageUrl)}"
          alt="Generated image"
          loading="lazy"
        />
      </div>
    `;
  }

  function renderMessages() {
    const container = byId("mobileChatMessages");
    if (!container) return;

    app.state.currentAssistantBubble = null;

    if (!app.state.messages.length) {
      renderEmptyState(container);
      updateHeader();
      return;
    }

    const html = app.state.messages
      .map((msg, index) => {
        const role = safeText(msg.role || "assistant").toLowerCase();
        const content = escapeHtml(msg.content || "").replace(/\n/g, "<br>");
        const timeText = escapeHtml(formatTime(getMessageTimestamp(msg)));
        const isAssistant = role === "assistant";
        const sourceCards = isAssistant ? renderMobileSourceCards(msg) : "";
        const generatedImage = isAssistant ? renderFinalResponseImage(msg) : "";

        return `
          <div class="mobile-message-row ${role}">
            <div class="mobile-message-bubble">
              <div class="mobile-message-role">${escapeHtml(role)}</div>
              <div class="mobile-message-content">${content}</div>
              ${generatedImage}
              ${sourceCards}
              <div class="mobile-message-time">${timeText}</div>
              ${
                isAssistant
                  ? `
                <div class="mobile-message-actions">
                  <button type="button" class="mobile-inline-action" data-copy-index="${index}">Copy</button>
                  <button type="button" class="mobile-inline-action" data-regenerate-index="${index}">Regenerate</button>
                </div>
              `
                  : ""
              }
            </div>
          </div>
        `;
      })
      .join("");

    container.innerHTML = `<div class="mobile-message-list">${html}</div>`;

    container.querySelectorAll("[data-copy-index]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const index = Number(btn.getAttribute("data-copy-index"));
        const msg = app.state.messages[index];
        if (!msg) return;
        await copyText(msg.content || "");
      });
    });

    container.querySelectorAll("[data-regenerate-index]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const index = Number(btn.getAttribute("data-regenerate-index"));
        await regenerateFromAssistantIndex(index);
      });
    });

    container.querySelectorAll("[data-mobile-source-url]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const url = safeText(btn.getAttribute("data-mobile-source-url"));
        if (!url) return;
        window.open(url, "_blank", "noopener,noreferrer");
      });
    });

    scrollMessagesToBottom();
    updateHeader();
  }

  function createStreamingAssistantBubble() {
    const container = byId("mobileChatMessages");
    if (!container) return null;

    let list = container.querySelector(".mobile-message-list");
    if (!list) {
      container.innerHTML = `<div class="mobile-message-list"></div>`;
      list = container.querySelector(".mobile-message-list");
    }

    const row = document.createElement("div");
    row.className = "mobile-message-row assistant";

    const bubble = document.createElement("div");
    bubble.className = "mobile-message-bubble";

    const role = document.createElement("div");
    role.className = "mobile-message-role";
    role.textContent = "assistant";

    const content = document.createElement("div");
    content.className = "mobile-message-content";
    content.innerHTML = "";

    const time = document.createElement("div");
    time.className = "mobile-message-time";
    time.textContent = "Streaming...";

    bubble.appendChild(role);
    bubble.appendChild(content);
    bubble.appendChild(time);
    row.appendChild(bubble);
    list.appendChild(row);

    scrollMessagesToBottom("smooth");
    app.state.currentAssistantBubble = {
      row,
      bubble,
      content,
      time,
      text: "",
      done: false,
    };

    return app.state.currentAssistantBubble;
  }

  function appendStreamingDelta(delta) {
    if (!app.state.currentAssistantBubble) {
      createStreamingAssistantBubble();
    }

    if (!app.state.currentAssistantBubble) return;

    app.state.currentAssistantBubble.text += String(delta || "");
    app.state.currentAssistantBubble.content.innerHTML = escapeHtml(
      app.state.currentAssistantBubble.text
    ).replace(/\n/g, "<br>");

    scrollMessagesToBottom("smooth");
  }

  function extractFinalAssistantText(payload, fallbackText) {
    if (!payload || typeof payload !== "object") return String(fallbackText || "");

    const assistant = payload.assistant_message;

    if (assistant && typeof assistant === "object") {
      return String(
        assistant.text ||
        assistant.content ||
        assistant.message ||
        fallbackText ||
        ""
      );
    }

    return String(
      payload.text ||
      payload.content ||
      payload.message ||
      fallbackText ||
      ""
    );
  }

  function persistFinalResponseMessage(payload, fallbackText) {
    if (!payload || typeof payload !== "object") return;

    const text = extractFinalAssistantText(payload, fallbackText);
    const imageUrl = getFinalResponseImageUrl(payload);

    if (!text && !imageUrl) return;

    const assistant = payload.assistant_message && typeof payload.assistant_message === "object"
      ? payload.assistant_message
      : {};

    const message = {
      role: "assistant",
      text: text,
      content: text,
      created_at: nowUnix(),
    };

    if (imageUrl) {
      message.image_url = imageUrl;
      message.imageUrl = imageUrl;
      message.preview = imageUrl;
      message.assistant_message = Object.assign({}, assistant, {
        image_url: imageUrl,
      });
    }

    if (payload.saved_artifact) {
      message.saved_artifact = payload.saved_artifact;
    }

    app.state.messages = Array.isArray(app.state.messages) ? app.state.messages : [];

    const last = app.state.messages[app.state.messages.length - 1];
    const lastText = String((last && (last.text || last.content)) || "");

    if (last && last.role === "assistant" && lastText === text) {
      if (imageUrl) {
        last.image_url = imageUrl;
        last.imageUrl = imageUrl;
        last.preview = imageUrl;
        last.assistant_message = message.assistant_message;
      }

      if (payload.saved_artifact) {
        last.saved_artifact = payload.saved_artifact;
      }
    } else {
      app.state.messages.push(message);
    }

    if (payload.session_id || payload.active_session_id) {
      app.state.activeSessionId = payload.session_id || payload.active_session_id;

      try {
        localStorage.setItem("novaMobileActiveSessionId", app.state.activeSessionId);
      } catch (_) {}
    }

    app.state.__skipPostSendSessionReload = true;
  }

  function finalizeStreamingAssistantBubble(finalText = "") {
    if (!app.state.currentAssistantBubble) return;

    const bubble = app.state.currentAssistantBubble;
    if (finalText) {
      bubble.text = String(finalText);
      bubble.content.innerHTML = escapeHtml(bubble.text).replace(/\n/g, "<br>");
    }

    bubble.done = true;
    bubble.time.textContent = formatTime(nowUnix());
  }

  function finishStreamingAssistantBubble() {
    if (!app.state.currentAssistantBubble) return;
    finalizeStreamingAssistantBubble(app.state.currentAssistantBubble.text || "");
    app.state.currentAssistantBubble = null;
  }

  function renderSessions() {
    const list = byId("mobileSessionList");
    if (!list) return;

    if (!app.state.sessions.length) {
      list.innerHTML = `<div class="mobile-card">No chats yet.</div>`;
      return;
    }

    list.innerHTML = app.state.sessions
      .map((session) => {
        const sessionId = getSessionId(session);
        const activeClass = sessionId === app.state.activeSessionId ? " is-active" : "";
        const pinned = Boolean(session.pinned);

        return `
          <div class="mobile-session-card${activeClass}">
            <button class="mobile-session-item${activeClass}" data-session-id="${escapeHtml(sessionId)}" type="button">
              <div class="mobile-session-title">${escapeHtml(session.title || "New Chat")}</div>
              <div class="mobile-session-meta">${escapeHtml(String(session.message_count || 0))} messages${pinned ? " • pinned" : ""}</div>
            </button>
            <div class="mobile-session-actions">
              <button type="button" class="mobile-session-action" data-rename-session="${escapeHtml(sessionId)}">Rename</button>
              <button type="button" class="mobile-session-action" data-duplicate-session="${escapeHtml(sessionId)}">Duplicate</button>
              <button type="button" class="mobile-session-action" data-pin-session="${escapeHtml(sessionId)}" data-pin-value="${pinned ? "0" : "1"}">${pinned ? "Unpin" : "Pin"}</button>
              <button type="button" class="mobile-session-action" data-export-session="${escapeHtml(sessionId)}">Export</button>
              <button type="button" class="mobile-session-action mobile-session-action-danger" data-delete-session="${escapeHtml(sessionId)}">Delete</button>
            </div>
          </div>
        `;
      })
      .join("");

    list.querySelectorAll("[data-session-id]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const sessionId = btn.getAttribute("data-session-id");
        await loadSession(sessionId);
        closeScreen("mobileMenuScreen");
      });
    });

    list.querySelectorAll("[data-rename-session]").forEach((btn) => {
      btn.addEventListener("click", async (event) => {
        event.stopPropagation();
        const sessionId = btn.getAttribute("data-rename-session");
        await renameSession(sessionId);
      });
    });

    list.querySelectorAll("[data-duplicate-session]").forEach((btn) => {
      btn.addEventListener("click", async (event) => {
        event.stopPropagation();
        const sessionId = btn.getAttribute("data-duplicate-session");
        await duplicateSession(sessionId);
      });
    });

    list.querySelectorAll("[data-pin-session]").forEach((btn) => {
      btn.addEventListener("click", async (event) => {
        event.stopPropagation();
        const sessionId = btn.getAttribute("data-pin-session");
        const pinned = btn.getAttribute("data-pin-value") === "1";
        await pinSession(sessionId, pinned);
      });
    });

    list.querySelectorAll("[data-export-session]").forEach((btn) => {
      btn.addEventListener("click", async (event) => {
        event.stopPropagation();
        const sessionId = btn.getAttribute("data-export-session");
        await exportSession(sessionId);
      });
    });

    list.querySelectorAll("[data-delete-session]").forEach((btn) => {
      btn.addEventListener("click", async (event) => {
        event.stopPropagation();
        const sessionId = btn.getAttribute("data-delete-session");
        await deleteSession(sessionId);
      });
    });
  }

  function renderMemory() {
    const list = byId("mobileMemoryList");
    const status = byId("mobileMemoryStatus");

    if (!list) return;

    if (status) {
      status.textContent = app.state.memoryItems.length
        ? `${app.state.memoryItems.length} memory item(s)`
        : "No saved memory yet.";
    }

    if (!app.state.memoryItems.length) {
      list.innerHTML = `<div class="mobile-card">No saved memory yet.</div>`;
      return;
    }

    list.innerHTML = app.state.memoryItems
      .map((item) => {
        const kind = escapeHtml(item.kind || "memory");
        const value = escapeHtml(item.value || "");
        const timeText = escapeHtml(formatTime(item.created_at || nowUnix()));
        const memoryId = escapeHtml(item.id || "");

        return `
          <div class="mobile-memory-item">
            <div class="mobile-memory-item-top">
              <div class="mobile-memory-kind">${kind}</div>
              <button type="button" class="mobile-memory-delete-btn" data-delete-memory="${memoryId}" aria-label="Delete memory">✕</button>
            </div>
            <div class="mobile-memory-value">${value}</div>
            <div class="mobile-message-time">${timeText}</div>
          </div>
        `;
      })
      .join("");

    list.querySelectorAll("[data-delete-memory]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const memoryId = btn.getAttribute("data-delete-memory");
        await deleteMemory(memoryId);
      });
    });
  }

  async function loadState() {
    const data = await apiGet(API.state);

    app.state.sessions = Array.isArray(data.sessions) ? data.sessions : [];
    app.state.currentModel = safeText(data.current_model || data.model || "gpt-4.1-mini");

    const preferredSessionId =
      data.active_session_id ||
      data.current_session_id ||
      (app.state.sessions[0] ? getSessionId(app.state.sessions[0]) : null);

    if (!app.state.activeSessionId && preferredSessionId) {
      app.state.activeSessionId = preferredSessionId;
    }

    renderSessions();
    updateHeader();
  }

  async function loadSession(sessionId) {
    if (!sessionId) return;

    const data = await apiGet(API.getChat(sessionId));
    app.state.activeSessionId = data.session_id || sessionId;
    app.state.messages = Array.isArray(data.messages) ? data.messages : [];

    const lastUser = getLastUserMessage();
    app.state.lastUserMessage = safeText(lastUser?.content || "");

    renderMessages();
    renderSessions();
  }

  async function loadMemory() {
    const data = await apiGet(API.memory);
    app.state.memoryItems = Array.isArray(data.memory) ? data.memory : [];
    renderMemory();
  }

  async function createNewSession() {
    const data = await apiPost(API.newSession, {});
    await loadState();

    if (data.session_id) {
      await loadSession(data.session_id);
    } else if (app.state.sessions[0]) {
      await loadSession(getSessionId(app.state.sessions[0]));
    }

    closeAllScreens();
    setStatus("New chat ready");
  }

  async function addMemory(kind, value) {
    await apiPost(API.memory, { kind, value });
    await loadMemory();
    setStatus("Memory saved");
  }

  async function deleteMemory(memoryId) {
    if (!memoryId) return;
    await apiPost(API.deleteMemory, { id: memoryId });
    await loadMemory();
    setStatus("Memory deleted");
  }

  async function renameSession(sessionId) {
    if (!sessionId) return;

    const session = app.state.sessions.find((s) => getSessionId(s) === sessionId);
    const currentTitle = session?.title || "New Chat";
    const nextTitle = window.prompt("Rename chat", currentTitle);

    if (nextTitle === null) return;

    const title = safeText(nextTitle);
    if (!title) return;

    await apiPost(API.renameSession, {
      session_id: sessionId,
      title,
    });

    await loadState();
    if (sessionId === app.state.activeSessionId) {
      await loadSession(sessionId);
    }
    setStatus("Chat renamed");
  }

  async function duplicateSession(sessionId) {
    if (!sessionId) return;

    const data = await apiPost(API.duplicateSession, {
      session_id: sessionId,
    });

    await loadState();

    const duplicatedId = getSessionId(data.session || {});
    if (duplicatedId) {
      await loadSession(duplicatedId);
    }

    setStatus("Chat duplicated");
  }

  async function pinSession(sessionId, pinned) {
    if (!sessionId) return;

    await apiPost(API.pinSession, {
      session_id: sessionId,
      pinned,
    });

    await loadState();
    renderSessions();
    setStatus(pinned ? "Chat pinned" : "Chat unpinned");
  }

  async function deleteSession(sessionId) {
    if (!sessionId) return;

    const ok = window.confirm("Delete this chat?");
    if (!ok) return;

    const wasActive = sessionId === app.state.activeSessionId;

    await apiPost(API.deleteSession, {
      session_id: sessionId,
    });

    app.state.activeSessionId = wasActive ? null : app.state.activeSessionId;

    await loadState();

    if (!app.state.activeSessionId && app.state.sessions[0]) {
      app.state.activeSessionId = getSessionId(app.state.sessions[0]);
    }

    if (app.state.activeSessionId) {
      await loadSession(app.state.activeSessionId);
    } else {
      app.state.messages = [];
      renderMessages();
    }

    setStatus("Chat deleted");
  }

  async function exportSession(sessionId) {
    if (!sessionId) return;

    const data = await apiPost(API.exportSession, {
      session_id: sessionId,
    });

    const session = data.session || {};
    const title = safeText(session.title || "nova-chat").replace(/[\\/:*?"<>|]+/g, "_");
    const blob = new Blob([JSON.stringify(session, null, 2)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title || "nova-chat"}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    setStatus("Chat exported");
  }

  async function copyText(text) {
    const value = String(text || "");
    if (!value) return;

    try {
      await navigator.clipboard.writeText(value);
      setStatus("Copied");
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = value;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
      setStatus("Copied");
    }
  }

  async function regenerateReply() {
    const lastUser = getLastUserMessage();
    const userText = safeText(lastUser?.content || app.state.lastUserMessage);

    if (!userText || app.state.isSending) return;

    const input = byId("mobileMessageInput");
    if (input) {
      input.value = userText;
      autosizeInput();
    }

    await sendMessage({ overrideContent: userText, isRegenerate: true });
  }

  async function regenerateFromAssistantIndex(index) {
    if (app.state.isSending) return;

    let matchedUserText = "";
    for (let i = index - 1; i >= 0; i -= 1) {
      const msg = app.state.messages[i];
      if (safeText(msg?.role).toLowerCase() === "user") {
        matchedUserText = safeText(msg.content || "");
        break;
      }
    }

    if (!matchedUserText) {
      matchedUserText = safeText(app.state.lastUserMessage);
    }

    if (!matchedUserText) return;

    const input = byId("mobileMessageInput");
    if (input) {
      input.value = matchedUserText;
      autosizeInput();
    }

    await sendMessage({ overrideContent: matchedUserText, isRegenerate: true });
  }

  function parseSSEBlock(rawBlock) {
    const lines = String(rawBlock || "").split(/\r?\n/);
    let event = "";
    const dataLines = [];

    for (const line of lines) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
        continue;
      }
      if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }

    const payloadText = dataLines.join("\n").trim();
    let data = {};

    if (payloadText && payloadText !== "[DONE]") {
      data = JSON.parse(payloadText);
    }

    return { event, data };
  }

  async function sendMessage(options = {}) {
    const input = byId("mobileMessageInput");
    if (!input || app.state.isSending) return;

    const overrideContent = safeText(options.overrideContent || "");
    const content = overrideContent || safeText(input.value);
    const hasFiles = app.state.attachedFiles.length > 0;
    const isRegenerate = Boolean(options.isRegenerate);

    if (!content && !hasFiles) return;

    if (!app.state.activeSessionId) {
      await createNewSession();
    }

    app.state.isSending = true;
    setSendDisabled(true);
    setStatus(isRegenerate ? "Regenerating..." : "Responding...");
    updateHeader();

    const userText = content;
    const activeSessionIdBeforeSend = app.state.activeSessionId;

    let localAssistantText = "";
    let streamFinished = false;

    try {
      let uploadedFiles = [];

      if (hasFiles && !isRegenerate) {
        setStatus("Uploading...");
        uploadedFiles = await uploadFiles(app.state.attachedFiles);
      }

      app.state.lastUserMessage = userText;

      app.state.messages.push({
        id: `local-user-${Date.now()}`,
        role: "user",
        content: userText,
        created_at: nowUnix(),
      });
      renderMessages();

      if (!overrideContent) {
        input.value = "";
      }

      if (!isRegenerate) {
        app.state.attachedFiles = [];
        renderAttachedFiles();
      }

      autosizeInput();
      createStreamingAssistantBubble();

      const res = await fetch(API.stream, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream, application/json, text/plain, */*",
        },
        body: JSON.stringify({
          session_id: activeSessionIdBeforeSend,
          content: userText,
          message: userText,
          model: app.state.currentModel,
          uploaded_files: uploadedFiles,
        }),
      });

      if (!res.ok) {
        throw new Error(`Send failed (${res.status})`);
      }

      if (!res.body || typeof res.body.getReader !== "function") {
        const fallbackText = safeText(await res.text()) || "No response.";
        localAssistantText = fallbackText;
        finalizeStreamingAssistantBubble(localAssistantText);
        finishStreamingAssistantBubble();
        streamFinished = true;
      } else {
        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            buffer += decoder.decode();
            break;
          }

          buffer += decoder.decode(value || new Uint8Array(), { stream: true });

          let separatorIndex;
          while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
            const rawBlock = buffer.slice(0, separatorIndex).trim();
            buffer = buffer.slice(separatorIndex + 2);

            if (!rawBlock) continue;
            if (rawBlock === "data: [DONE]") continue;

            let parsed;
            try {
              parsed = parseSSEBlock(rawBlock);
            } catch (err) {
              console.warn("Failed to parse SSE block:", rawBlock, err);
              continue;
            }

            const data = parsed.data || {};
            const type = data.type || parsed.event || "";

            if (type === "meta") {
              if (data.session_id) {
                app.state.activeSessionId = data.session_id;
              }
              continue;
            }

            if (type === "delta") {
              const delta =
                typeof data.delta === "string"
                  ? data.delta
                  : typeof data.content === "string"
                  ? data.content
                  : "";

              if (!delta) continue;

              localAssistantText += delta;
              appendStreamingDelta(delta);
              continue;
            }

            if (type === "done") {
              const finalText =
                typeof data.response === "string"
                  ? data.response
                  : typeof data.message?.content === "string"
                  ? data.message.content
                  : typeof data.content === "string"
                  ? data.content
                  : localAssistantText;

              if (data.session_id) {
                app.state.activeSessionId = data.session_id;
              }

              localAssistantText = finalText || localAssistantText;
              persistFinalResponseMessage(data, localAssistantText);
              finalizeStreamingAssistantBubble(localAssistantText);
              finishStreamingAssistantBubble();
              streamFinished = true;
              continue;
            }

            if (type === "error") {
              throw new Error(data.error || data.message || "Stream failed");
            }
          }
        }

        const trailing = buffer.trim();
        if (trailing && trailing !== "data: [DONE]") {
          try {
            const parsed = parseSSEBlock(trailing);
            const data = parsed.data || {};
            const type = data.type || parsed.event || "";

            if (type === "done") {
              const finalText =
                typeof data.response === "string"
                  ? data.response
                  : typeof data.message?.content === "string"
                  ? data.message.content
                  : typeof data.content === "string"
                  ? data.content
                  : localAssistantText;

              if (data.session_id) {
                app.state.activeSessionId = data.session_id;
              }

              localAssistantText = finalText || localAssistantText;
              persistFinalResponseMessage(data, localAssistantText);
              finalizeStreamingAssistantBubble(localAssistantText);
              finishStreamingAssistantBubble();
              streamFinished = true;
            }
          } catch (err) {
            console.warn("Trailing SSE parse failed:", err);
          }
        }

        if (!streamFinished) {
          finalizeStreamingAssistantBubble(localAssistantText);
          finishStreamingAssistantBubble();
        }
      }

      if (app.state.__skipPostSendSessionReload) {
        delete app.state.__skipPostSendSessionReload;

        await loadMemory().catch(function () {});
        renderMessages();
        renderSessions();
        renderMemory();
      } else {
        await loadState();
        await loadSession(app.state.activeSessionId || activeSessionIdBeforeSend);
        await loadMemory();
        renderMessages();
        renderSessions();
        renderMemory();
      }

      setStatus(isRegenerate ? "Regenerated" : "Model ready");
    } catch (err) {
      console.error(err);

      if (app.state.currentAssistantBubble) {
        const errorText =
          localAssistantText ||
          `Error: ${err?.message || String(err) || "Stream failed"}`;
        finalizeStreamingAssistantBubble(errorText);
        finishStreamingAssistantBubble();
      }

      await loadState().catch(() => {});
      if (app.state.activeSessionId || activeSessionIdBeforeSend) {
        await loadSession(app.state.activeSessionId || activeSessionIdBeforeSend).catch(() => {});
      }

      setStatus("Send failed");
    } finally {
      app.state.isSending = false;
      setSendDisabled(false);
      updateHeader();
      autosizeInput();
      scrollMessagesToBottom("smooth");
    }
  }

  function bindEvents() {
    byId("mobileMenuBtn")?.addEventListener("click", () => {
      renderSessions();
      openScreen("mobileMenuScreen");
    });

    byId("closeMobileMenuBtn")?.addEventListener("click", () => {
      closeScreen("mobileMenuScreen");
    });

    byId("mobileMemoryBtn")?.addEventListener("click", async () => {
      await loadMemory();
      openScreen("mobileMemoryScreen");
    });

    byId("closeMobileMemoryBtn")?.addEventListener("click", () => {
      closeScreen("mobileMemoryScreen");
    });

    byId("mobileNewSessionBtn")?.addEventListener("click", async () => {
      await createNewSession();
    });

    byId("mobileAttachBtn")?.addEventListener("click", () => {
      if (app.state.isSending) return;
      byId("mobileFileInput")?.click();
    });

    byId("mobileFileInput")?.addEventListener("change", (event) => {
      const files = Array.from(event.target.files || []);
      app.state.attachedFiles = files;
      renderAttachedFiles();

      if (files.length) {
        setStatus(`${files.length} attachment${files.length === 1 ? "" : "s"} ready`);
      }

      if (event.target) {
        event.target.value = "";
      }
    });

    byId("mobileSendBtn")?.addEventListener("click", () => sendMessage());

    byId("mobileMessageInput")?.addEventListener("input", autosizeInput);

    byId("mobileMessageInput")?.addEventListener("keydown", async (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        await sendMessage();
      }
    });

    byId("mobileMemoryForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();

      const kind = safeText(byId("mobileMemoryKind")?.value || "memory");
      const value = safeText(byId("mobileMemoryValue")?.value || "");

      if (!value) return;

      await addMemory(kind, value);

      const memoryValueEl = byId("mobileMemoryValue");
      if (memoryValueEl) {
        memoryValueEl.value = "";
      }
    });

    byId("mobileThemeToggleBtn")?.addEventListener("click", () => {
      cycleTheme();
    });

    byId("mobileBackgroundBtn")?.addEventListener("click", () => {
      cycleBackground();
    });

    document.addEventListener("keydown", async (event) => {
      if (event.key === "Escape") {
        closeAllScreens();
      }

      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "r") {
        event.preventDefault();
        await regenerateReply();
      }
    });

    document.addEventListener("visibilitychange", async () => {
      if (!document.hidden) {
        try {
          await loadState();
          if (app.state.activeSessionId) {
            await loadSession(app.state.activeSessionId);
          }
        } catch (err) {
          console.error("Visibility refresh failed:", err);
        }
      }
    });
  }

  async function bootstrap() {
    initAppearance();
    bindEvents();
    setStatus("Loading...");
    setSendDisabled(false);

    await loadState();

    if (app.state.activeSessionId) {
      await loadSession(app.state.activeSessionId);
    } else {
      renderMessages();
    }

    await loadMemory();
    renderAttachedFiles();
    autosizeInput();
    setStatus("Model ready");
  }

  
// MOBILE_ATTACHMENT_QUICK_PROMPTS_LOCK
function getMobileAttachmentContextForPrompt() {
    const parts = [];

    try {
        const stateAttachments = Array.isArray(state?.attachments) ? state.attachments : [];
        const pendingAttachments = Array.isArray(state?.pendingAttachments) ? state.pendingAttachments : [];
        const stagedAttachments = Array.isArray(window.NovaMobileState?.attachments) ? window.NovaMobileState.attachments : [];

        const all = []
            .concat(stateAttachments)
            .concat(pendingAttachments)
            .concat(stagedAttachments)
            .filter(Boolean);

        const seen = new Set();

        for (const item of all) {
            const name = String(
                item.original_filename ||
                item.filename ||
                item.name ||
                item.title ||
                ""
            ).trim();

            const extracted = String(
                item.extracted_text ||
                item.text ||
                item.content ||
                item.summary ||
                item.description ||
                ""
            ).trim();

            const url = String(
                item.file_url ||
                item.url ||
                ""
            ).trim();

            const key = `${name}|${url}|${extracted.slice(0, 80)}`;
            if (seen.has(key)) {
                continue;
            }
            seen.add(key);

            if (name) {
                parts.push(`Attachment: ${name}`);
            }

            if (extracted) {
                parts.push(`Extracted attachment text:\n${extracted}`);
            } else if (url) {
                parts.push(`Attachment URL: ${url}`);
            }
        }
    } catch (err) {
        console.warn("[Nova Mobile] attachment context prompt helper failed", err);
    }

    return parts.join("\n\n").trim();
}

function buildMobileAttachmentAwarePrompt(actionText) {
    const action = String(actionText || "").trim();
    const typed = String(
        getComposerText?.() ||
        document.querySelector("#mobile-input")?.value ||
        document.querySelector("#composer-input")?.value ||
        document.querySelector("textarea")?.value ||
        ""
    ).trim();

    const attachmentContext = getMobileAttachmentContextForPrompt();

    const lines = [];

    if (action) {
        lines.push(action);
    }

    if (typed) {
        lines.push(`User typed text:\n${typed}`);
    }

    if (attachmentContext) {
        lines.push(`Use the uploaded attachment context below. Do not say you cannot see the attachment if extracted text is present.\n\n${attachmentContext}`);
    }

    return lines.join("\n\n").trim() || action || typed;
}



// MOBILE_QUICK_ACTION_FULL_CONTEXT_LOCK
function novaMobileReadComposerText() {
    const selectors = [
        "#mobile-input",
        "#composer-input",
        "#nova-mobile-input",
        "#chat-input",
        "textarea",
        "[contenteditable='true']"
    ];

    for (const selector of selectors) {
        const el = document.querySelector(selector);
        if (!el) {
            continue;
        }

        const value = String(el.value || el.innerText || el.textContent || "").trim();
        if (value) {
            return value;
        }
    }

    return "";
}

function novaMobileCollectAttachmentContext() {
    const buckets = [];

    try {
        if (window.NovaMobileState && Array.isArray(window.NovaMobileState.attachments)) {
            buckets.push(...window.NovaMobileState.attachments);
        }

        if (window.NovaMobileStorage && Array.isArray(window.NovaMobileStorage.attachments)) {
            buckets.push(...window.NovaMobileStorage.attachments);
        }

        if (typeof state !== "undefined" && state) {
            if (Array.isArray(state.attachments)) {
                buckets.push(...state.attachments);
            }

            if (Array.isArray(state.pendingAttachments)) {
                buckets.push(...state.pendingAttachments);
            }

            if (Array.isArray(state.uploads)) {
                buckets.push(...state.uploads);
            }
        }
    } catch (err) {
        console.warn("[Nova Mobile] attachment bucket read failed", err);
    }

    const seen = new Set();
    const lines = [];

    for (const item of buckets) {
        if (!item) {
            continue;
        }

        const name = String(
            item.original_filename ||
            item.filename ||
            item.name ||
            item.title ||
            ""
        ).trim();

        const mime = String(
            item.mime_type ||
            item.type ||
            ""
        ).trim();

        const extracted = String(
            item.extracted_text ||
            item.extractedText ||
            item.ocr_text ||
            item.ocrText ||
            item.text ||
            item.content ||
            item.summary ||
            item.description ||
            ""
        ).trim();

        const url = String(
            item.file_url ||
            item.fileUrl ||
            item.url ||
            item.src ||
            ""
        ).trim();

        const key = `${name}|${mime}|${url}|${extracted.slice(0, 120)}`;
        if (seen.has(key)) {
            continue;
        }
        seen.add(key);

        if (name) {
            lines.push(`Attachment filename: ${name}`);
        }

        if (mime) {
            lines.push(`Attachment type: ${mime}`);
        }

        if (url) {
            lines.push(`Attachment URL: ${url}`);
        }

        if (extracted) {
            lines.push(`Extracted attachment text:\n${extracted}`);
        }

        if (name || mime || url || extracted) {
            lines.push("---");
        }
    }

    return lines.join("\n").trim();
}

function novaMobileBuildQuickActionPrompt(rawAction) {
    const action = String(rawAction || "").trim();
    const typedText = novaMobileReadComposerText();
    const attachmentContext = novaMobileCollectAttachmentContext();

    let instruction = action;

    const lower = action.toLowerCase();

    if (lower.includes("summarize")) {
        instruction = "Summarize the uploaded attachment content. If typed text is present, include it as extra user context.";
    } else if (lower.includes("keypoint") || lower.includes("key point")) {
        instruction = "Give the key points from the uploaded attachment content. If typed text is present, include it as extra user context.";
    } else if (lower.includes("improve")) {
        instruction = "Improve the uploaded attachment content or typed text while preserving the meaning.";
    } else if (lower.includes("continue")) {
        instruction = "Continue from the uploaded attachment content or typed text.";
    } else if (lower === "next" || lower.includes("next")) {
        instruction = "Give the next best action based on the uploaded attachment content or typed text.";
    }

    const parts = [
        "[MOBILE QUICK ACTION ATTACHMENT CONTEXT ACTIVE]",
        instruction
    ];

    if (typedText) {
        parts.push(`Typed user text:\n${typedText}`);
    }

    if (attachmentContext) {
        parts.push(
            "Uploaded attachment context below. Use this directly. Do not say you cannot see the attachment when extracted text, filename, or URL is present.\n\n" +
            attachmentContext
        );
    }

    return parts.join("\n\n").trim();
}


document.addEventListener("DOMContentLoaded", () => {
    bootstrap().catch((err) => {
      console.error("Mobile bootstrap failed:", err);
      setStatus("Bootstrap failed");
      setSendDisabled(false);
    });
  });
})();


// MOBILE_ATTACHMENT_SUMMARY_BUTTON_LOCK
(function () {
    function novaFindLatestAttachment() {
        const candidates = [];

        try {
            if (window.lastUploadedAttachment) {
                candidates.push(window.lastUploadedAttachment);
            }

            if (Array.isArray(window.uploadedAttachments)) {
                candidates.push(...window.uploadedAttachments);
            }

            if (Array.isArray(window.stagedAttachments)) {
                candidates.push(...window.stagedAttachments);
            }

            if (Array.isArray(window.pendingAttachments)) {
                candidates.push(...window.pendingAttachments);
            }

            if (window.NovaMobileState && Array.isArray(window.NovaMobileState.attachments)) {
                candidates.push(...window.NovaMobileState.attachments);
            }
        } catch (error) {
            console.warn("[Nova Mobile] attachment scan failed", error);
        }

        const valid = candidates.filter(function (item) {
            if (!item || typeof item !== "object") {
                return false;
            }

            return Boolean(item.url || item.file_url || item.path || item.filename);
        });

        return valid.length ? valid[valid.length - 1] : null;
    }

    function novaAttachmentUrl(attachment) {
        return String(
            attachment.url ||
            attachment.file_url ||
            attachment.upload_url ||
            ""
        ).trim();
    }

    function novaAttachmentMime(attachment) {
        return String(
            attachment.mime_type ||
            attachment.type ||
            attachment.mime ||
            ""
        ).trim();
    }

    function novaToastAttachmentSummary(text) {
        let box = document.getElementById("nova-attachment-summary-output");

        if (!box) {
            box = document.createElement("div");
            box.id = "nova-attachment-summary-output";
            box.style.position = "fixed";
            box.style.left = "12px";
            box.style.right = "12px";
            box.style.bottom = "92px";
            box.style.zIndex = "99999";
            box.style.maxHeight = "45vh";
            box.style.overflow = "auto";
            box.style.padding = "12px";
            box.style.borderRadius = "14px";
            box.style.background = "rgba(20, 20, 28, 0.96)";
            box.style.color = "white";
            box.style.fontSize = "13px";
            box.style.lineHeight = "1.35";
            box.style.whiteSpace = "pre-wrap";
            box.style.boxShadow = "0 8px 28px rgba(0,0,0,0.35)";
            document.body.appendChild(box);
        }

        box.textContent = text;
        box.hidden = false;
    }

    async function novaSummarizeLatestAttachment() {
        const attachment = novaFindLatestAttachment();

        if (!attachment) {
            novaToastAttachmentSummary("No uploaded attachment found yet.");
            return;
        }

        const url = novaAttachmentUrl(attachment);
        const mimeType = novaAttachmentMime(attachment);

        if (!url && !attachment.path) {
            novaToastAttachmentSummary("Attachment found, but it has no usable URL/path.");
            return;
        }

        novaToastAttachmentSummary("Extracting and summarizing attachment...");

        try {
            const response = await fetch("/api/attachment/summarize", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    url: url,
                    path: attachment.path || "",
                    mime_type: mimeType,
                }),
            });

            const result = await response.json();

            if (!result || !result.ok) {
                novaToastAttachmentSummary("Attachment summary failed:\n" + JSON.stringify(result, null, 2));
                return;
            }

            const points = Array.isArray(result.key_points)
                ? result.key_points.slice(0, 10).map(function (point, index) {
                    return (index + 1) + ". " + point;
                }).join("\n")
                : "";

            novaToastAttachmentSummary(
                "Summary:\n" +
                String(result.summary || "").trim() +
                "\n\nKey Points:\n" +
                points +
                "\n\nChars: raw=" + result.raw_chars + " clean=" + result.clean_chars
            );
        } catch (error) {
            novaToastAttachmentSummary("Attachment summary request failed:\n" + String(error));
        }
    }

    function novaInstallAttachmentSummaryButton() {
        if (document.getElementById("nova-attachment-summary-btn")) {
            return;
        }

        const button = document.createElement("button");
        button.id = "nova-attachment-summary-btn";
        button.type = "button";
        button.textContent = "Summarize Attachment";
        button.style.position = "fixed";
        button.style.right = "12px";
        button.style.bottom = "48px";
        button.style.zIndex = "99999";
        button.style.padding = "10px 12px";
        button.style.borderRadius = "999px";
        button.style.border = "0";
        button.style.fontWeight = "700";
        button.style.background = "#7c3aed";
        button.style.color = "white";
        button.style.boxShadow = "0 8px 22px rgba(0,0,0,0.28)";

        button.addEventListener("click", novaSummarizeLatestAttachment);

        document.body.appendChild(button);

        console.log("[Nova Mobile] attachment summary button installed");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", novaInstallAttachmentSummaryButton);
    } else {
        novaInstallAttachmentSummaryButton();
    }

    window.NovaSummarizeLatestAttachment = novaSummarizeLatestAttachment;
})();


// MOBILE_CAPTURE_LATEST_UPLOAD_LOCK
(function () {
    if (window.__novaUploadCaptureInstalled) {
        return;
    }

    window.__novaUploadCaptureInstalled = true;

    const originalFetch = window.fetch.bind(window);

    window.fetch = async function novaFetchWithUploadCapture(input, init) {
        const response = await originalFetch(input, init);

        try {
            const url = typeof input === "string"
                ? input
                : String((input && input.url) || "");

            const method = String((init && init.method) || "GET").toUpperCase();

            if (method === "POST" && url.includes("/api/upload")) {
                const clone = response.clone();
                const data = await clone.json();

                if (data && data.ok !== false) {
                    const attachment = {
                        url: data.url || data.file_url || data.path || "",
                        file_url: data.file_url || data.url || "",
                        path: data.path || "",
                        filename: data.filename || data.stored || data.name || "",
                        original_filename: data.original_filename || data.original || data.filename || "",
                        mime_type: data.mime_type || data.type || "",
                        size: data.size || data.size_bytes || 0,
                    };

                    if (attachment.url || attachment.file_url || attachment.path) {
                        window.lastUploadedAttachment = attachment;

                        if (!Array.isArray(window.uploadedAttachments)) {
                            window.uploadedAttachments = [];
                        }

                        window.uploadedAttachments.push(attachment);

                        try {
                            sessionStorage.setItem(
                                "novaLastUploadedAttachment",
                                JSON.stringify(attachment)
                            );
                        } catch (storageError) {
                            console.warn("[Nova Mobile] could not store latest upload", storageError);
                        }

                        console.log("[Nova Mobile] captured latest upload for attachment tools", attachment);
                    }
                }
            }
        } catch (error) {
            console.warn("[Nova Mobile] upload capture failed", error);
        }

        return response;
    };

    console.log("[Nova Mobile] upload capture installed");
})();


// MOBILE_ATTACHMENT_KEYPOINTS_BUTTON_LOCK
(function () {
    function novaFindLatestAttachmentForKeypoints() {
        const candidates = [];

        try {
            if (window.lastUploadedAttachment) {
                candidates.push(window.lastUploadedAttachment);
            }

            if (Array.isArray(window.uploadedAttachments)) {
                candidates.push(...window.uploadedAttachments);
            }

            if (Array.isArray(window.stagedAttachments)) {
                candidates.push(...window.stagedAttachments);
            }

            if (Array.isArray(window.pendingAttachments)) {
                candidates.push(...window.pendingAttachments);
            }

            try {
                const saved = sessionStorage.getItem("novaLastUploadedAttachment");
                if (saved) {
                    candidates.push(JSON.parse(saved));
                }
            } catch (storageError) {
                console.warn("[Nova Mobile] latest upload storage read failed", storageError);
            }
        } catch (error) {
            console.warn("[Nova Mobile] keypoints attachment scan failed", error);
        }

        const valid = candidates.filter(function (item) {
            if (!item || typeof item !== "object") {
                return false;
            }

            return Boolean(item.url || item.file_url || item.path || item.filename);
        });

        return valid.length ? valid[valid.length - 1] : null;
    }

    function novaShowAttachmentKeypoints(text) {
        let box = document.getElementById("nova-attachment-summary-output");

        if (!box) {
            box = document.createElement("div");
            box.id = "nova-attachment-summary-output";
            box.style.position = "fixed";
            box.style.left = "12px";
            box.style.right = "12px";
            box.style.bottom = "92px";
            box.style.zIndex = "99999";
            box.style.maxHeight = "45vh";
            box.style.overflow = "auto";
            box.style.padding = "12px";
            box.style.borderRadius = "14px";
            box.style.background = "rgba(20, 20, 28, 0.96)";
            box.style.color = "white";
            box.style.fontSize = "13px";
            box.style.lineHeight = "1.35";
            box.style.whiteSpace = "pre-wrap";
            box.style.boxShadow = "0 8px 28px rgba(0,0,0,0.35)";
            document.body.appendChild(box);
        }

        box.textContent = text;
        box.hidden = false;
    }

    async function novaGetLatestAttachmentKeypoints() {
        const attachment = novaFindLatestAttachmentForKeypoints();

        if (!attachment) {
            novaShowAttachmentKeypoints("No uploaded attachment found yet.");
            return;
        }

        const url = String(attachment.url || attachment.file_url || attachment.upload_url || "").trim();
        const mimeType = String(attachment.mime_type || attachment.type || attachment.mime || "").trim();

        if (!url && !attachment.path) {
            novaShowAttachmentKeypoints("Attachment found, but it has no usable URL/path.");
            return;
        }

        novaShowAttachmentKeypoints("Extracting key points...");

        try {
            const response = await fetch("/api/attachment/keypoints", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    url: url,
                    path: attachment.path || "",
                    mime_type: mimeType,
                }),
            });

            const result = await response.json();

            if (!result || !result.ok) {
                novaShowAttachmentKeypoints("Key points failed:\n" + JSON.stringify(result, null, 2));
                return;
            }

            const points = Array.isArray(result.key_points)
                ? result.key_points.slice(0, 10).map(function (point, index) {
                    return (index + 1) + ". " + point;
                }).join("\n")
                : "";

            novaShowAttachmentKeypoints(
                "Key Points:\n" +
                points +
                "\n\nSummary:\n" +
                String(result.summary || "").trim() +
                "\n\nPoints: " + result.points_count +
                "\nRaw chars: " + result.raw_chars
            );
        } catch (error) {
            novaShowAttachmentKeypoints("Key points request failed:\n" + String(error));
        }
    }

    function novaInstallAttachmentKeypointsButton() {
        if (document.getElementById("nova-attachment-keypoints-btn")) {
            return;
        }

        const button = document.createElement("button");
        button.id = "nova-attachment-keypoints-btn";
        button.type = "button";
        button.textContent = "Key Points";
        button.style.position = "fixed";
        button.style.left = "12px";
        button.style.bottom = "48px";
        button.style.zIndex = "99999";
        button.style.padding = "10px 12px";
        button.style.borderRadius = "999px";
        button.style.border = "0";
        button.style.fontWeight = "700";
        button.style.background = "#4f46e5";
        button.style.color = "white";
        button.style.boxShadow = "0 8px 22px rgba(0,0,0,0.28)";

        button.addEventListener("click", novaGetLatestAttachmentKeypoints);

        document.body.appendChild(button);

        console.log("[Nova Mobile] attachment keypoints button installed");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", novaInstallAttachmentKeypointsButton);
    } else {
        novaInstallAttachmentKeypointsButton();
    }

    window.NovaGetLatestAttachmentKeypoints = novaGetLatestAttachmentKeypoints;
})();


// MOBILE_LATEST_ATTACHMENT_ONLY_LOCK_20260603
(function () {
    "use strict";

    function novaLatestAttachmentLog() {
        try {
            console.log.apply(console, ["[Nova Mobile Latest Attachment]"].concat(Array.from(arguments)));
        } catch (error) {
            // no-op
        }
    }

    function getNovaState() {
        try {
            if (window.NovaMobileState && typeof window.NovaMobileState === "object") {
                return window.NovaMobileState;
            }

            if (window.NovaMobile && window.NovaMobile.state) {
                return window.NovaMobile.state;
            }

            if (window.__novaMobileState && typeof window.__novaMobileState === "object") {
                return window.__novaMobileState;
            }
        } catch (error) {
            // no-op
        }

        return null;
    }

    function normalizeAttachment(item) {
        if (!item || typeof item !== "object") {
            return null;
        }

        var filename = String(
            item.filename ||
            item.stored_filename ||
            item.name ||
            ""
        ).trim();

        var originalFilename = String(
            item.original_filename ||
            item.original_name ||
            item.name ||
            filename ||
            ""
        ).trim();

        var fileUrl = String(
            item.file_url ||
            item.url ||
            ""
        ).trim();

        var url = String(
            item.url ||
            item.file_url ||
            ""
        ).trim();

        if (!filename && fileUrl) {
            filename = fileUrl.replace(/\\/g, "/").split("/").pop();
        }

        if (!originalFilename) {
            originalFilename = filename;
        }

        if (!filename && !originalFilename && !fileUrl && !url) {
            return null;
        }

        var clean = Object.assign({}, item);
        clean.filename = filename;
        clean.original_filename = originalFilename;
        clean.file_url = fileUrl || url;
        clean.url = url || fileUrl;
        clean.name = clean.name || originalFilename || filename;

        return clean;
    }

    function clearStagedAttachments(reason) {
        var state = getNovaState();

        try {
            if (state) {
                state.stagedAttachments = [];
                state.pendingAttachments = [];
                state.attachments = [];
                state.selectedAttachments = [];
                state.uploadQueue = [];
                state.lastAttachmentPayload = null;
                state.lastUploadedAttachment = null;
                state.latestUploadedAttachment = null;
            }

            window.__novaLatestUploadedAttachment = null;
            window.__novaCurrentUploadAttachment = null;
            window.__novaStagedAttachments = [];

            localStorage.removeItem("nova_mobile_staged_attachments");
            localStorage.removeItem("nova_staged_attachments");
            localStorage.removeItem("nova_mobile_attachments");
            sessionStorage.removeItem("nova_mobile_staged_attachments");
            sessionStorage.removeItem("nova_staged_attachments");
            sessionStorage.removeItem("nova_mobile_attachments");

            novaLatestAttachmentLog("cleared staged attachments", reason || "");
        } catch (error) {
            novaLatestAttachmentLog("clear failed", error);
        }
    }

    function setLatestAttachment(item, reason) {
        var clean = normalizeAttachment(item);

        if (!clean) {
            return null;
        }

        var state = getNovaState();

        try {
            if (state) {
                state.stagedAttachments = [clean];
                state.pendingAttachments = [clean];
                state.attachments = [clean];
                state.selectedAttachments = [clean];
                state.lastAttachmentPayload = clean;
                state.lastUploadedAttachment = clean;
                state.latestUploadedAttachment = clean;
            }

            window.__novaLatestUploadedAttachment = clean;
            window.__novaCurrentUploadAttachment = clean;
            window.__novaStagedAttachments = [clean];

            novaLatestAttachmentLog(
                "latest attachment set",
                reason || "",
                clean.original_filename || clean.filename || clean.url
            );
        } catch (error) {
            novaLatestAttachmentLog("set latest failed", error);
        }

        return clean;
    }

    function getLatestAttachmentOnly() {
        var state = getNovaState();
        var candidates = [];

        try {
            if (window.__novaLatestUploadedAttachment) {
                candidates.push(window.__novaLatestUploadedAttachment);
            }

            if (window.__novaCurrentUploadAttachment) {
                candidates.push(window.__novaCurrentUploadAttachment);
            }

            if (state) {
                candidates.push(state.latestUploadedAttachment);
                candidates.push(state.lastUploadedAttachment);
                candidates.push(state.lastAttachmentPayload);

                [
                    state.stagedAttachments,
                    state.pendingAttachments,
                    state.selectedAttachments,
                    state.attachments
                ].forEach(function (list) {
                    if (Array.isArray(list) && list.length) {
                        candidates.push(list[list.length - 1]);
                    }
                });
            }

            for (var index = 0; index < candidates.length; index += 1) {
                var clean = normalizeAttachment(candidates[index]);

                if (clean) {
                    return [clean];
                }
            }
        } catch (error) {
            novaLatestAttachmentLog("get latest failed", error);
        }

        return [];
    }

    window.NovaMobileLatestAttachment = {
        clear: clearStagedAttachments,
        set: setLatestAttachment,
        getOnly: getLatestAttachmentOnly
    };

    // Clear stale attachment state whenever user selects a new file.
    document.addEventListener("change", function (event) {
        var target = event.target;

        if (!target || target.type !== "file") {
            return;
        }

        clearStagedAttachments("file input changed");
    }, true);

    // Watch upload responses and capture the newest upload payload.
    var originalFetch = window.fetch;

    if (typeof originalFetch === "function") {
        window.fetch = function () {
            var args = arguments;

            return originalFetch.apply(this, args).then(function (response) {
                try {
                    var url = "";

                    if (args && args[0]) {
                        url = typeof args[0] === "string" ? args[0] : String(args[0].url || "");
                    }

                    if (url.indexOf("/api/upload") !== -1) {
                        response.clone().json().then(function (payload) {
                            if (payload && payload.ok) {
                                setLatestAttachment(payload, "upload response");
                            }
                        }).catch(function () {
                            // no-op
                        });
                    }
                } catch (error) {
                    novaLatestAttachmentLog("upload response hook failed", error);
                }

                return response;
            });
        };
    }

    // Before /api/chat send, force body.attachments to newest upload only.
    if (typeof originalFetch === "function") {
        var currentFetch = window.fetch;

        window.fetch = function () {
            var args = Array.from(arguments);

            try {
                var url = "";

                if (args && args[0]) {
                    url = typeof args[0] === "string" ? args[0] : String(args[0].url || "");
                }

                var options = args[1];

                if (
                    url.indexOf("/api/chat") !== -1 &&
                    options &&
                    typeof options === "object" &&
                    typeof options.body === "string"
                ) {
                    var body = JSON.parse(options.body);
                    var latestOnly = getLatestAttachmentOnly();

                    if (latestOnly.length) {
                        body.attachments = latestOnly;
                        options.body = JSON.stringify(body);

                        novaLatestAttachmentLog(
                            "forced chat attachments latest-only",
                            latestOnly[0].original_filename || latestOnly[0].filename || latestOnly[0].url
                        );
                    }

                    args[1] = options;
                }
            } catch (error) {
                novaLatestAttachmentLog("chat payload hook failed", error);
            }

            return currentFetch.apply(this, args).then(function (response) {
                try {
                    var url = "";

                    if (args && args[0]) {
                        url = typeof args[0] === "string" ? args[0] : String(args[0].url || "");
                    }

                    if (url.indexOf("/api/chat") !== -1) {
                        clearStagedAttachments("chat sent");
                    }
                } catch (error) {
                    novaLatestAttachmentLog("post-chat clear failed", error);
                }

                return response;
            });
        };
    }

    novaLatestAttachmentLog("latest attachment guard active");
}());


/* MOBILE_APP_FORCE_COPY_REGEN_LOCK */
(function () {
    "use strict";

    if (window.__novaMobileAppForceCopyRegen) {
        return;
    }

    window.__novaMobileAppForceCopyRegen = true;

    function qs(selector, root) {
        return (root || document).querySelector(selector);
    }

    function qsa(selector, root) {
        return Array.prototype.slice.call((root || document).querySelectorAll(selector));
    }

    function textOf(node) {
        return String((node && (node.innerText || node.textContent)) || "").trim();
    }

    function findInput() {
        return (
            qs("#nova-mobile-input") ||
            qs("#mobile-input") ||
            qs("textarea") ||
            qs("input[type='text']")
        );
    }

    function getChatBox() {
        return (
            qs("#mobileChatMessages") ||
            qs("#mobileMessages") ||
            qs("#messages") ||
            qs(".mobile-chat-container")
        );
    }

    function isUserNode(node) {
        var cls = String(node.className || "").toLowerCase();
        var role = String(node.getAttribute && (
            node.getAttribute("data-role") ||
            node.getAttribute("data-message-role") ||
            ""
        )).toLowerCase();

        return role === "user" || cls.indexOf("user") !== -1;
    }

    function isAssistantNode(node) {
        if (!node || !node.appendChild) {
            return false;
        }

        if (node.querySelector("[data-mobile-copy-answer], [data-mobile-regen-answer]")) {
            return false;
        }

        if (node.querySelector("textarea, input, select")) {
            return false;
        }

        if (node.closest("form, footer, header, nav, .mobile-composer, .composer")) {
            return false;
        }

        if (isUserNode(node)) {
            return false;
        }

        var text = textOf(node);

        if (!text || text === "Thinking..." || text.length < 2) {
            return false;
        }

        var cls = String(node.className || "").toLowerCase();
        var role = String(node.getAttribute && (
            node.getAttribute("data-role") ||
            node.getAttribute("data-message-role") ||
            ""
        )).toLowerCase();

        if (role === "assistant") {
            return true;
        }

        if (
            cls.indexOf("assistant") !== -1 ||
            cls.indexOf("nova") !== -1 ||
            cls.indexOf("message") !== -1 ||
            cls.indexOf("bubble") !== -1 ||
            cls.indexOf("fallback") !== -1
        ) {
            return true;
        }

        return true;
    }

    function makeActions() {
        var wrap = document.createElement("div");
        wrap.className = "mobile-message-actions nova-mobile-forced-copy-regen";
        wrap.setAttribute("data-forced-copy-regen", "1");
        wrap.style.cssText = [
            "display:flex !important",
            "gap:8px !important",
            "margin-top:10px !important",
            "visibility:visible !important",
            "opacity:1 !important",
            "pointer-events:auto !important",
            "position:relative !important",
            "z-index:999999 !important"
        ].join(";");

        wrap.innerHTML =
            '<button type="button" data-mobile-copy-answer="1" style="display:inline-flex !important;visibility:visible !important;opacity:1 !important;padding:6px 10px !important;border-radius:10px !important;border:1px solid rgba(255,255,255,.22) !important;background:rgba(255,255,255,.10) !important;color:inherit !important;font-size:12px !important;">Copy</button>' +
            '<button type="button" data-mobile-regen-answer="1" style="display:inline-flex !important;visibility:visible !important;opacity:1 !important;padding:6px 10px !important;border-radius:10px !important;border:1px solid rgba(255,255,255,.22) !important;background:rgba(255,255,255,.10) !important;color:inherit !important;font-size:12px !important;">Regenerate</button>';

        return wrap;
    }

    function ensureActions() {
        var box = getChatBox();

        if (!box) {
            return;
        }

        Array.prototype.slice.call(box.children || []).forEach(function (node) {
            if (isAssistantNode(node)) {
                node.appendChild(makeActions());
            }
        });
    }

    document.addEventListener("click", async function (event) {
        var copyBtn = event.target.closest("[data-mobile-copy-answer]");
        var regenBtn = event.target.closest("[data-mobile-regen-answer]");

        if (copyBtn) {
            event.preventDefault();
            event.stopPropagation();

            var bubble = copyBtn.closest("#mobileChatMessages > *, #mobileMessages > *, #messages > *, .mobile-chat-container > *") || copyBtn.parentElement.parentElement;
            var clone = bubble ? bubble.cloneNode(true) : null;

            if (clone) {
                qsa(".mobile-message-actions, [data-forced-copy-regen]", clone).forEach(function (node) {
                    node.remove();
                });
            }

            var answer = textOf(clone || bubble || document.body);

            try {
                await navigator.clipboard.writeText(answer || "");
                copyBtn.textContent = "Copied";
            } catch (err) {
                copyBtn.textContent = "Failed";
            }

            setTimeout(function () {
                copyBtn.textContent = "Copy";
            }, 900);

            return;
        }

        if (regenBtn) {
            event.preventDefault();
            event.stopPropagation();

            var input = findInput();
            var last = String(window.__novaMobileLastUserText || "").trim();

            if (!last) {
                var box = getChatBox();
                var userNodes = box ? Array.prototype.slice.call(box.children || []).filter(isUserNode) : [];
                var lastUser = userNodes[userNodes.length - 1];
                last = textOf(lastUser);
            }

            if (!input || !last) {
                regenBtn.textContent = "!";
                setTimeout(function () {
                    regenBtn.textContent = "Regenerate";
                }, 900);
                return;
            }

            input.value = last;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            input.focus();

            var sendBtn = qs("#nova-mobile-send");

            if (sendBtn) {
                sendBtn.click();
            }
        }
    }, true);

    var observer = new MutationObserver(function () {
        ensureActions();
    });

    function boot() {
        ensureActions();

        if (document.body) {
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                characterData: true
            });
        }

        setInterval(ensureActions, 750);

        console.log("[Nova Mobile] app force copy/regen active");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();


/* MOBILE_ATTACHMENT_PAYLOAD_GUARD_LOCK */
(function () {
    "use strict";

    if (window.__novaMobileAttachmentPayloadGuard) {
        return;
    }

    window.__novaMobileAttachmentPayloadGuard = true;

    var originalFetch = window.fetch;

    function safeJsonParse(value, fallback) {
        try {
            return JSON.parse(value);
        } catch (error) {
            return fallback;
        }
    }

    function normalizeAttachment(item) {
        item = item || {};

        var url = String(item.url || item.file_url || item.path || "").trim();
        var fileUrl = String(item.file_url || item.url || item.path || "").trim();
        var filename = String(item.filename || item.original_filename || item.name || "").trim();

        if (!url && !fileUrl && !filename) {
            return null;
        }

        return {
            filename: filename || "attachment",
            original_filename: String(item.original_filename || item.filename || item.name || filename || "attachment").trim(),
            size: Number(item.size || item.size_bytes || 0),
            mime_type: String(item.mime_type || item.type || "application/octet-stream").trim(),
            url: url || fileUrl,
            file_url: fileUrl || url,
            status: String(item.status || "uploaded").trim()
        };
    }

    function getStagedAttachments() {
        var attachments = [];

        [
            "nova_mobile_attachments",
            "nova_mobile_latest_attachment",
            "nova_latest_attachment"
        ].forEach(function (key) {
            try {
                var raw = sessionStorage.getItem(key) || localStorage.getItem(key) || "";

                if (!raw) {
                    return;
                }

                var parsed = safeJsonParse(raw, null);

                if (Array.isArray(parsed)) {
                    parsed.forEach(function (item) {
                        var normalized = normalizeAttachment(item);

                        if (normalized) {
                            attachments.push(normalized);
                        }
                    });
                    return;
                }

                var normalized = normalizeAttachment(parsed);

                if (normalized) {
                    attachments.push(normalized);
                }
            } catch (error) {}
        });

        var seen = {};
        return attachments.filter(function (item) {
            var key = String(item.file_url || item.url || item.filename || "").trim();

            if (!key || seen[key]) {
                return false;
            }

            seen[key] = true;
            return true;
        });
    }

    function shouldPatchChatRequest(resource, init) {
        var url = "";

        if (typeof resource === "string") {
            url = resource;
        } else if (resource && resource.url) {
            url = resource.url;
        }

        var method = String((init && init.method) || "GET").toUpperCase();

        return method === "POST" && url.indexOf("/api/chat") !== -1;
    }

    window.fetch = function (resource, init) {
        init = init || {};

        if (shouldPatchChatRequest(resource, init) && init.body) {
            var bodyText = typeof init.body === "string" ? init.body : "";
            var payload = safeJsonParse(bodyText, null);

            if (payload && typeof payload === "object") {
                var staged = getStagedAttachments();

                if ((!Array.isArray(payload.attachments) || payload.attachments.length === 0) && staged.length > 0) {
                    payload.attachments = staged;
                    init = Object.assign({}, init, {
                        body: JSON.stringify(payload)
                    });

                    console.log("[Nova Mobile Attachment Payload Guard] injected staged attachments into chat payload", staged);
                } else {
                    console.log("[Nova Mobile Attachment Payload Guard] chat payload attachments", Array.isArray(payload.attachments) ? payload.attachments.length : 0);
                }
            }
        }

        return originalFetch.call(this, resource, init);
    };

    console.log("[Nova Mobile Attachment Payload Guard] active");
})();


/* MOBILE_CLEAN_ATTACHMENT_CONTEXT_LOCK */
(function () {
    "use strict";

    if (window.__novaMobileCleanAttachmentContext) {
        return;
    }

    window.__novaMobileCleanAttachmentContext = true;

    function safeRemoveStorage(key) {
        try {
            sessionStorage.removeItem(key);
        } catch (error) {}

        try {
            localStorage.removeItem(key);
        } catch (error) {}
    }

    function cleanOldAttachmentState() {
        [
            "nova_mobile_latest_attachment",
            "nova_latest_attachment",
            "nova_mobile_attachments"
        ].forEach(safeRemoveStorage);

        console.log("[Nova Mobile Clean Attachment Context] stale attachment storage cleared");
    }

    function cleanBadAttachmentText(text) {
        return String(text || "")
            .replace(/\[Attachment analysis failed:\s*tesseract is not installed[^\]]*\]\.?/gi, "")
            .replace(/Attachment analysis failed:\s*tesseract is not installed[^\n.]*(\.|\n)?/gi, "")
            .replace(/This attachment appears to contain image\/search\/PDF extraction text about:\s*/gi, "Attachment analysis:\n")
            .replace(/This attachment appears to contain extracted image\/PDF content about:\s*/gi, "")
            .replace(/\n{3,}/g, "\n\n")
            .trim();
    }

    var originalFetch = window.fetch;

    // MOBILE_ACTIVE_RESPONSE_REWRITE_IMAGE_APPEND_LOCK
    function novaExtractGeneratedImageUrl(payload) {
        if (!payload || typeof payload !== "object") {
            return "";
        }

        if (payload.image_url) return String(payload.image_url);
        if (payload.imageUrl) return String(payload.imageUrl);
        if (payload.preview) return String(payload.preview);

        var assistant = payload.assistant_message;

        if (assistant && typeof assistant === "object") {
            if (assistant.image_url) return String(assistant.image_url);
            if (assistant.imageUrl) return String(assistant.imageUrl);
            if (assistant.preview) return String(assistant.preview);
            if (assistant.url) return String(assistant.url);
        }

        var artifact = payload.saved_artifact || payload.artifact;

        if (artifact && typeof artifact === "object") {
            if (artifact.image_url) return String(artifact.image_url);
            if (artifact.imageUrl) return String(artifact.imageUrl);
            if (artifact.preview) return String(artifact.preview);
            if (artifact.url) return String(artifact.url);

            if (artifact.meta && artifact.meta.image_url) {
                return String(artifact.meta.image_url);
            }

            if (artifact.viewer && artifact.viewer.image_url) {
                return String(artifact.viewer.image_url);
            }
        }

        return "";
    }

    function novaExtractGeneratedAssistantText(payload) {
        if (!payload || typeof payload !== "object") {
            return "";
        }

        var assistant = payload.assistant_message;

        if (assistant && typeof assistant === "object") {
            return String(
                assistant.text ||
                assistant.content ||
                assistant.message ||
                ""
            );
        }

        if (payload.saved_artifact && payload.saved_artifact.summary) {
            return String(payload.saved_artifact.summary);
        }

        return String(payload.text || payload.content || payload.message || "");
    }

    function novaPreserveGeneratedImagePayload(cleaned, originalPayload) {
        var imageUrl =
            novaExtractGeneratedImageUrl(cleaned) ||
            novaExtractGeneratedImageUrl(originalPayload);

        if (!imageUrl) {
            return cleaned;
        }

        cleaned = cleaned && typeof cleaned === "object" ? cleaned : {};

        cleaned.image_url = imageUrl;
        cleaned.imageUrl = imageUrl;
        cleaned.preview = cleaned.preview || imageUrl;

        if (!cleaned.assistant_message || typeof cleaned.assistant_message !== "object") {
            cleaned.assistant_message = {};
        }

        cleaned.assistant_message.image_url = imageUrl;
        cleaned.assistant_message.imageUrl = imageUrl;

        var text =
            novaExtractGeneratedAssistantText(cleaned) ||
            novaExtractGeneratedAssistantText(originalPayload);

        if (text) {
            cleaned.assistant_message.text = text;
            cleaned.assistant_message.content = text;
        }

        if (!cleaned.saved_artifact && originalPayload && originalPayload.saved_artifact) {
            cleaned.saved_artifact = originalPayload.saved_artifact;
        }

        return cleaned;
    }

    function novaAppendGeneratedImageToLatestBubble(imageUrl) {
        if (!imageUrl) {
            return;
        }

        try {
            var bubbles = Array.from(document.querySelectorAll(
                ".mobile-message-row.assistant .mobile-message-bubble, .mobile-message-bubble"
            ));

            if (!bubbles.length) {
                return;
            }

            var bubble = bubbles[bubbles.length - 1];

            if (!bubble || bubble.querySelector("[data-nova-generated-image-url]")) {
                return;
            }

            var wrap = document.createElement("div");
            wrap.className = "mobile-generated-image-wrap";
            wrap.setAttribute("data-nova-generated-image-url", imageUrl);

            var img = document.createElement("img");
            img.className = "mobile-generated-image";
            img.src = imageUrl;
            img.alt = "Generated image";
            img.loading = "lazy";

            wrap.appendChild(img);
            bubble.appendChild(wrap);

            console.log("[Nova Mobile Image Render] appended generated image", imageUrl);
        } catch (error) {
            console.warn("[Nova Mobile Image Render] append failed", error);
        }
    }

    function novaSaveGeneratedImageToDebugState(payload) {
        try {
            var debug = window.NovaMobileDebug;
            var app = debug && debug.app;
            var state = app && app.state;

            if (!state) {
                return;
            }

            state.messages = Array.isArray(state.messages) ? state.messages : [];

            var imageUrl = novaExtractGeneratedImageUrl(payload);
            var text = novaExtractGeneratedAssistantText(payload);

            if (!imageUrl && !text) {
                return;
            }

            var message = {
                role: "assistant",
                text: text,
                content: text,
                image_url: imageUrl || undefined,
                preview: imageUrl || undefined,
                assistant_message: {
                    text: text,
                    image_url: imageUrl || undefined
                },
                saved_artifact: payload.saved_artifact
            };

            var last = state.messages[state.messages.length - 1];
            var lastText = String((last && (last.text || last.content)) || "");

            if (last && last.role === "assistant" && lastText === text) {
                if (imageUrl) {
                    last.image_url = imageUrl;
                    last.preview = imageUrl;
                    last.assistant_message = message.assistant_message;
                }

                if (payload.saved_artifact) {
                    last.saved_artifact = payload.saved_artifact;
                }
            } else {
                state.messages.push(message);
            }
        } catch (error) {
            console.warn("[Nova Mobile Image Render] state save failed", error);
        }
    }

    window.fetch = function (resource, init) {
        return originalFetch.call(this, resource, init).then(function (response) {
            var url = "";

            if (typeof resource === "string") {
                url = resource;
            } else if (resource && resource.url) {
                url = resource.url;
            }

            if (url.indexOf("/api/chat") === -1 && url.indexOf("/api/attachment") === -1) {
                return response;
            }

            var clone = response.clone();

            clone.json().then(function (payload) {
                if (!payload || typeof payload !== "object") {
                    return;
                }

                if (payload.summary) {
                    payload.summary = cleanBadAttachmentText(payload.summary);
                }

                if (payload.preview) {
                    payload.preview = cleanBadAttachmentText(payload.preview);
                }

                if (Array.isArray(payload.key_points)) {
                    payload.key_points = payload.key_points
                        .map(cleanBadAttachmentText)
                        .filter(Boolean);
                }

                if (payload.assistant_message && payload.assistant_message.text) {
                    payload.assistant_message.text = cleanBadAttachmentText(payload.assistant_message.text);
                }
            }).catch(function () {});

            return response;
        });
    };

    document.addEventListener("change", function (event) {
        if (event.target && event.target.id === "nova-mobile-file-input") {
            cleanOldAttachmentState();
        }
    }, true);

    console.log("[Nova Mobile Clean Attachment Context] active");
})();


/* MOBILE_ATTACHMENT_RESPONSE_REWRITE_LOCK */
(function () {
    "use strict";

    if (window.__novaMobileAttachmentResponseRewrite) {
        return;
    }

    window.__novaMobileAttachmentResponseRewrite = true;

    var originalFetch = window.fetch;

    function cleanText(value) {
        var text = String(value || "");

        text = text
            .replace(/\ufeff/g, "")
            .replace(/This attachment appears to contain image\/search\/PDF extraction text about:\s*/gi, "")
            .replace(/This attachment appears to contain extracted image\/PDF content about:\s*/gi, "")
            .replace(/Key points:\s*;\s*/gi, "")
            .replace(/Attachment ([^:\n]+) content:\s*;\s*/gi, "Attachment $1 content:\n")
            .replace(/;\s*Attachment ([^:\n]+) content:/gi, "\nAttachment $1 content:")
            .replace(/\[Attachment analysis failed:\s*tesseract is not installed[^\]]*\]\.?/gi, "")
            .replace(/Attachment analysis failed:\s*tesseract is not installed[^\n.]*(\.|\n)?/gi, "")
            .replace(/\n{3,}/g, "\n\n")
            .trim();

        return text;
    }

    function cleanPayload(payload) {
        if (!payload || typeof payload !== "object") {
            return payload;
        }

        if (payload.summary) {
            payload.summary = cleanText(payload.summary);
        }

        if (payload.preview) {
            payload.preview = cleanText(payload.preview);
        }

        if (Array.isArray(payload.key_points)) {
            payload.key_points = payload.key_points
                .map(cleanText)
                .filter(function (item) {
                    return item && item.length > 0;
                });
        }

        if (payload.assistant_message && payload.assistant_message.text) {
            payload.assistant_message.text = cleanText(payload.assistant_message.text);
        }

        return payload;
    }

    function shouldRewrite(resource) {
        var url = "";

        if (typeof resource === "string") {
            url = resource;
        } else if (resource && resource.url) {
            url = resource.url;
        }

        return (
            url.indexOf("/api/attachment") !== -1 ||
            url.indexOf("/api/chat") !== -1
        );
    }

    window.fetch = function (resource, init) {
        return originalFetch.call(this, resource, init).then(function (response) {
            if (!shouldRewrite(resource)) {
                return response;
            }

            var contentType = response.headers.get("content-type") || "";

            if (contentType.indexOf("application/json") === -1) {
                return response;
            }

            return response.clone().json().then(function (payload) {
                var cleaned = cleanPayload(payload);
                cleaned = novaPreserveGeneratedImagePayload(cleaned, payload);

                var imageUrl = novaExtractGeneratedImageUrl(cleaned);

                if (imageUrl) {
                    novaSaveGeneratedImageToDebugState(cleaned);

                    setTimeout(function () {
                        novaAppendGeneratedImageToLatestBubble(imageUrl);
                    }, 50);
                }

                var body = JSON.stringify(cleaned);

                var headers = new Headers(response.headers);
                headers.set("content-type", "application/json");

                console.log("[Nova Mobile Attachment Response Rewrite] cleaned attachment/chat response");

                return new Response(body, {
                    status: response.status,
                    statusText: response.statusText,
                    headers: headers
                });
            }).catch(function () {
                return response;
            });
        });
    };

    console.log("[Nova Mobile Attachment Response Rewrite] active");
})();


// MOBILE_FINAL_RESPONSE_IMAGE_RENDER_LOCK

// MOBILE_ACTIVE_RESPONSE_REWRITE_IMAGE_APPEND_LOCK


/* MOBILE_IMAGE_RESPONSE_NORMALIZER_LOCK */
(() => {
    if (window.__novaMobileImageResponseNormalizerActive) return;
    window.__novaMobileImageResponseNormalizerActive = true;

    const originalFetch = window.fetch ? window.fetch.bind(window) : null;
    if (!originalFetch) {
        console.warn("[Nova Mobile] fetch not available for image response normalizer");
        return;
    }

    function pickImageUrl(payload) {
        const candidates = [
            payload?.image_url,
            payload?.assistant_message?.image_url,
            payload?.assistant_message?.preview,
            payload?.saved_artifact?.image_url,
            payload?.saved_artifact?.preview,
            payload?.saved_artifact?.viewer?.image_url,
        ];

        for (const value of candidates) {
            if (typeof value === "string" && value.trim()) {
                return value.trim();
            }
        }

        return "";
    }

    function promoteImageFields(payload) {
        if (!payload || typeof payload !== "object") return payload;

        const imageUrl = pickImageUrl(payload);
        if (!imageUrl) return payload;

        if (!payload.image_url) payload.image_url = imageUrl;
        if (!payload.preview) payload.preview = imageUrl;

        if (!payload.assistant_message || typeof payload.assistant_message !== "object") {
            payload.assistant_message = {
                role: "assistant",
                text: String(payload?.assistant_message?.text || payload?.text || "").trim(),
            };
        }

        if (!payload.assistant_message.image_url) payload.assistant_message.image_url = imageUrl;
        if (!payload.assistant_message.preview) payload.assistant_message.preview = imageUrl;

        if (payload.saved_artifact && typeof payload.saved_artifact === "object") {
            if (!payload.saved_artifact.image_url) payload.saved_artifact.image_url = imageUrl;
            if (!payload.saved_artifact.preview) payload.saved_artifact.preview = imageUrl;
        }

        return payload;
    }

    window.fetch = async function (...args) {
        const response = await originalFetch(...args);

        try {
            const url = String(
                typeof args[0] === "string"
                    ? args[0]
                    : args[0]?.url || ""
            );

            if (!url.includes("/api/chat")) {
                return response;
            }

            const contentType = String(response.headers.get("content-type") || "").lower?.() || String(response.headers.get("content-type") || "").toLowerCase();
            if (!contentType.includes("application/json")) {
                return response;
            }

            const cloned = response.clone();
            const payload = await cloned.json();

            if (!payload || typeof payload !== "object") {
                return response;
            }

            promoteImageFields(payload);

            const promotedImage = pickImageUrl(payload);
            if (promotedImage) {
                console.log("[Nova Mobile] image response normalized", {
                    image_url: promotedImage,
                    session_id: payload.session_id || payload.active_session_id || "",
                });
            }

            return new Response(
                JSON.stringify(payload),
                {
                    status: response.status,
                    statusText: response.statusText,
                    headers: response.headers,
                }
            );
        } catch (error) {
            console.warn("[Nova Mobile] image response normalizer fallback", error);
            return response;
        }
    };

    console.log("[Nova Mobile] image response normalizer active");
})();


// ACTIVE_MOBILE_APP_FORCE_IMAGE_RENDER_LOCK
(function () {
    if (window.__novaActiveImageRenderHookInstalled) {
        return;
    }

    window.__novaActiveImageRenderHookInstalled = true;

    function pickImageUrl(payload) {
        if (!payload || typeof payload !== "object") return "";

        if (payload.image_url) return String(payload.image_url);
        if (payload.imageUrl) return String(payload.imageUrl);
        if (payload.preview) return String(payload.preview);

        var assistant = payload.assistant_message;
        if (assistant && typeof assistant === "object") {
            if (assistant.image_url) return String(assistant.image_url);
            if (assistant.imageUrl) return String(assistant.imageUrl);
            if (assistant.preview) return String(assistant.preview);
            if (assistant.url) return String(assistant.url);
        }

        var artifact = payload.saved_artifact || payload.artifact;
        if (artifact && typeof artifact === "object") {
            if (artifact.image_url) return String(artifact.image_url);
            if (artifact.imageUrl) return String(artifact.imageUrl);
            if (artifact.preview) return String(artifact.preview);
            if (artifact.url) return String(artifact.url);

            if (artifact.viewer && artifact.viewer.image_url) {
                return String(artifact.viewer.image_url);
            }

            if (artifact.meta && artifact.meta.image_url) {
                return String(artifact.meta.image_url);
            }
        }

        return "";
    }

    function appendDirectImageBubble(imageUrl, payload) {
        try {
            var container =
                document.getElementById("mobileChatMessages") ||
                document.getElementById("chatMessages") ||
                document.getElementById("messageList") ||
                document.getElementById("messages");

            if (!container) return false;

            var existing = container.querySelector('[data-nova-direct-image="' + imageUrl.replace(/"/g, '&quot;') + '"]');
            if (existing) return true;

            var bubble = document.createElement("div");
            bubble.className = "message assistant";
            bubble.setAttribute("data-nova-direct-image", imageUrl);

            var text =
                (payload &&
                 payload.assistant_message &&
                 (payload.assistant_message.text || payload.assistant_message.content)) ||
                "Generated image";

            bubble.innerHTML =
                '<div class="mobile-message-content">' +
                    '<div class="message-text"></div>' +
                    '<img src="' + imageUrl + '" alt="Generated image" style="max-width:100%;border-radius:12px;display:block;margin-top:10px;" />' +
                '</div>';

            var textNode = bubble.querySelector(".message-text");
            if (textNode) {
                textNode.textContent = text || "Generated image";
            }

            container.appendChild(bubble);

            return true;
        } catch (error) {
            console.warn("[Nova Mobile] direct image bubble append failed", error);
            return false;
        }
    }

    function pushIntoDebugState(imageUrl, payload) {
        try {
            var debug = window.NovaMobileDebug;
            var app = debug && debug.app;
            var state = app && app.state;

            if (!state) return false;

            if (!Array.isArray(state.messages)) {
                state.messages = [];
            }

            var messages = state.messages;
            var last = messages.length ? messages[messages.length - 1] : null;

            if (last && last.role === "assistant") {
                last.image_url = imageUrl;
                last.imageUrl = imageUrl;
                last.preview = imageUrl;

                if (!last.assistant_message || typeof last.assistant_message !== "object") {
                    last.assistant_message = {};
                }

                if (!last.assistant_message.image_url) {
                    last.assistant_message.image_url = imageUrl;
                }

                if (!last.assistant_message.preview) {
                    last.assistant_message.preview = imageUrl;
                }
            } else {
                messages.push({
                    role: "assistant",
                    text:
                        (payload &&
                         payload.assistant_message &&
                         (payload.assistant_message.text || payload.assistant_message.content)) ||
                        "Generated image",
                    image_url: imageUrl,
                    imageUrl: imageUrl,
                    preview: imageUrl,
                    assistant_message: {
                        image_url: imageUrl,
                        preview: imageUrl
                    }
                });
            }

            if (typeof app.renderMessages === "function") {
                app.renderMessages();
            } else if (typeof window.renderMessages === "function") {
                window.renderMessages();
            }

            return true;
        } catch (error) {
            console.warn("[Nova Mobile] debug state image push failed", error);
            return false;
        }
    }

    function renderImageFromPayload(payload) {
        var imageUrl = pickImageUrl(payload);

        if (!imageUrl) {
            return;
        }

        var rendered = false;

        rendered = pushIntoDebugState(imageUrl, payload) || rendered;

        if (
            window.NovaMobileImages &&
            typeof window.NovaMobileImages.appendImage === "function"
        ) {
            try {
                window.NovaMobileImages.appendImage(imageUrl, "Generated image");
                rendered = true;
            } catch (error) {
                console.warn("[Nova Mobile] NovaMobileImages.appendImage failed", error);
            }
        }

        rendered = appendDirectImageBubble(imageUrl, payload) || rendered;

        console.log("[Nova Mobile] forced generated image render", {
            image_url: imageUrl,
            rendered: rendered
        });
    }

    var originalFetch = window.fetch ? window.fetch.bind(window) : null;

    if (!originalFetch) {
        console.warn("[Nova Mobile] fetch unavailable for forced image render hook");
        return;
    }

    window.fetch = async function () {
        var response = await originalFetch.apply(this, arguments);

        try {
            var resource = arguments[0];
            var url = String(
                typeof resource === "string"
                    ? resource
                    : resource && resource.url
                        ? resource.url
                        : ""
            );

            if (url.indexOf("/api/chat") !== -1) {
                response.clone().json().then(function (payload) {
                    renderImageFromPayload(payload);
                }).catch(function () {});
            }
        } catch (error) {
            console.warn("[Nova Mobile] forced image render hook failed", error);
        }

        return response;
    };

    console.log("[Nova Mobile] forced image render hook active");
})();

