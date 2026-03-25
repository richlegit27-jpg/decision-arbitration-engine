(() => {
  "use strict";

  if (window.__novaUltimateLoaded) return;
  window.__novaUltimateLoaded = true;

  const API = {
    state: "/api/state",
    newSession: "/api/session/new",
    getChat: (sessionId) => `/api/chat/${encodeURIComponent(sessionId)}`,
    stream: "/api/chat/stream",
    memory: "/api/memory",
    addMemory: "/api/memory",
    deleteMemory: "/api/memory/delete",
    upload: "/api/upload",
  };

  const DEFAULT_MODEL = "gpt-4.1-mini";
  const MAX_INPUT_HEIGHT = 180;

  const state = {
    sessions: [],
    messages: [],
    memoryItems: [],
    activeSessionId: null,
    currentModel: DEFAULT_MODEL,
    isSending: false,
    attachedFiles: [],
    lastUserMessage: "",
    lastRouter: null,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function qs(sel, root = document) {
    return root.querySelector(sel);
  }

  function qsa(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
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
    if (ts === null || ts === undefined || ts === "") return "";

    try {
      if (typeof ts === "string") {
        const trimmed = ts.trim();
        if (!trimmed) return "";

        const numeric = Number(trimmed);
        if (!Number.isNaN(numeric)) {
          const ms = numeric > 9999999999 ? numeric : numeric * 1000;
          const date = new Date(ms);
          return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
        }

        const isoDate = new Date(trimmed);
        return Number.isNaN(isoDate.getTime()) ? "" : isoDate.toLocaleString();
      }

      if (typeof ts === "number") {
        const ms = ts > 9999999999 ? ts : ts * 1000;
        const date = new Date(ms);
        return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
      }

      const fallback = new Date(ts);
      return Number.isNaN(fallback.getTime()) ? "" : fallback.toLocaleString();
    } catch {
      return "";
    }
  }

  async function apiGet(url) {
    const res = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
      credentials: "same-origin",
    });

    if (!res.ok) {
      let msg = `GET failed: ${url}`;
      try {
        const data = await res.json();
        msg = data.detail || data.message || data.error || msg;
      } catch {}
      throw new Error(msg);
    }

    return res.json();
  }

  async function apiPost(url, payload) {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      credentials: "same-origin",
      body: JSON.stringify(payload || {}),
    });

    if (!res.ok) {
      let msg = `POST failed: ${url}`;
      try {
        const data = await res.json();
        msg = data.detail || data.message || data.error || msg;
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
      credentials: "same-origin",
    });

    if (!res.ok) {
      throw new Error("Upload failed");
    }

    const data = await res.json();
    return Array.isArray(data.files) ? data.files : [];
  }

  function setStatus(text) {
    const el =
      byId("statusText") ||
      byId("modelStatus") ||
      byId("chatStatus") ||
      byId("mobileModelStatus");
    if (el) el.textContent = safeText(text || "Ready");
  }

  function autosizeInput() {
    const input = byId("messageInput");
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, MAX_INPUT_HEIGHT)}px`;
  }

  function scrollChatToBottom() {
    const container = byId("chatMessages");
    if (!container) return;
    container.scrollTop = container.scrollHeight;
  }

  function updateLastUserMessage() {
    const last = [...state.messages]
      .reverse()
      .find((msg) => safeText(msg.role).toLowerCase() === "user" && safeText(msg.content));

    state.lastUserMessage = last ? String(last.content || "") : "";

    const regenBtn = byId("regenerateBtn");
    if (regenBtn) {
      regenBtn.disabled = state.isSending || !state.lastUserMessage;
    }
  }

  function setSendingState(isSending) {
    state.isSending = Boolean(isSending);

    const sendBtn = byId("sendBtn");
    const regenBtn = byId("regenerateBtn");
    const input = byId("messageInput");
    const attachBtn = byId("attachBtn");
    const newBtn = byId("newSessionBtn");

    if (sendBtn) {
      sendBtn.disabled = state.isSending;
      sendBtn.setAttribute("aria-busy", state.isSending ? "true" : "false");
    }

    if (regenBtn) {
      regenBtn.disabled = state.isSending || !state.lastUserMessage;
      regenBtn.setAttribute("aria-busy", state.isSending ? "true" : "false");
    }

    if (input) input.disabled = state.isSending;
    if (attachBtn) attachBtn.disabled = state.isSending;
    if (newBtn) newBtn.disabled = state.isSending;

    document.body.classList.toggle("is-sending", state.isSending);
  }

  async function copyTextToClipboard(text) {
    const value = String(text ?? "");
    if (!value) return false;

    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
        return true;
      }
    } catch {}

    try {
      const temp = document.createElement("textarea");
      temp.value = value;
      temp.setAttribute("readonly", "readonly");
      temp.style.position = "fixed";
      temp.style.left = "-9999px";
      document.body.appendChild(temp);
      temp.focus();
      temp.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(temp);
      return ok;
    } catch {
      return false;
    }
  }

  function normalizeWebResults(rawResults) {
    const list = Array.isArray(rawResults) ? rawResults : [];
    const seen = new Set();

    return list
      .map((item) => {
        const url = safeText(item?.url || item?.link || item?.href);
        const title = safeText(item?.title || item?.name || url || "Untitled source");
        const snippet = safeText(
          item?.snippet ||
            item?.content ||
            item?.body ||
            item?.text ||
            item?.description
        );

        let domain = "";
        try {
          domain = url ? new URL(url).hostname.replace(/^www\./i, "") : "";
        } catch {
          domain = "";
        }

        const dedupeKey = `${url}__${title}`.toLowerCase();
        if (!url && !title && !snippet) return null;
        if (seen.has(dedupeKey)) return null;
        seen.add(dedupeKey);

        return {
          url,
          title,
          domain,
          snippet: snippet.length > 220 ? `${snippet.slice(0, 217)}...` : snippet,
        };
      })
      .filter(Boolean);
  }

  function renderWebResultsHtml(webResults) {
    const results = normalizeWebResults(webResults);
    if (!results.length) return "";

    return `
      <div class="nova-web-results">
        <div class="nova-web-results-header">Web sources</div>
        <div class="nova-web-results-list">
          ${results
            .map(
              (item) => `
            <article class="nova-web-card">
              <div class="nova-web-card-top">
                <div class="nova-web-card-title">${escapeHtml(item.title || "Untitled source")}</div>
                <div class="nova-web-card-domain">${escapeHtml(item.domain || "external source")}</div>
              </div>
              ${
                item.snippet
                  ? `<div class="nova-web-card-snippet">${escapeHtml(item.snippet)}</div>`
                  : `<div class="nova-web-card-snippet is-empty">No preview available.</div>`
              }
              ${
                item.url
                  ? `
                    <div class="nova-web-card-actions">
                      <a
                        class="nova-web-open-link"
                        href="${escapeHtml(item.url)}"
                        target="_blank"
                        rel="noopener noreferrer"
                      >Open</a>
                    </div>
                  `
                  : ""
              }
            </article>
          `
            )
            .join("")}
        </div>
      </div>
    `;
  }

  function injectWebResultStyles() {
    if (byId("novaWebResultStyles")) return;

    const style = document.createElement("style");
    style.id = "novaWebResultStyles";
    style.textContent = `
      .nova-web-results {
        margin-top: 12px;
        border-top: 1px solid rgba(255,255,255,0.08);
        padding-top: 12px;
      }

      .nova-web-results-header {
        font-size: 12px;
        font-weight: 700;
        opacity: 0.8;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }

      .nova-web-results-list {
        display: grid;
        gap: 10px;
      }

      .nova-web-card {
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 14px;
        padding: 12px;
        background: rgba(255,255,255,0.03);
        backdrop-filter: blur(6px);
      }

      .nova-web-card-top {
        display: flex;
        flex-direction: column;
        gap: 4px;
        margin-bottom: 8px;
      }

      .nova-web-card-title {
        font-size: 14px;
        font-weight: 700;
        line-height: 1.35;
      }

      .nova-web-card-domain {
        font-size: 12px;
        opacity: 0.7;
      }

      .nova-web-card-snippet {
        font-size: 13px;
        line-height: 1.5;
        opacity: 0.92;
      }

      .nova-web-card-snippet.is-empty {
        font-size: 13px;
        opacity: 0.65;
      }

      .nova-web-card-actions {
        margin-top: 10px;
      }

      .nova-web-open-link {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 34px;
        padding: 0 12px;
        border-radius: 10px;
        text-decoration: none;
        font-size: 13px;
        font-weight: 700;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.05);
        color: inherit;
      }

      .nova-web-open-link:hover {
        background: rgba(255,255,255,0.09);
      }
    `;
    document.head.appendChild(style);
  }

  function renderAttachedFiles() {
    const bar = byId("attachedFilesBar") || byId("attachedFiles");
    if (!bar) return;

    bar.innerHTML = "";

    if (!state.attachedFiles.length) {
      bar.classList.remove("has-files");
      return;
    }

    bar.classList.add("has-files");

    state.attachedFiles.forEach((file, index) => {
      const chip = document.createElement("div");
      chip.className = "file-chip";
      chip.innerHTML = `
        <span>${escapeHtml(file.name)} (${Math.max(1, Math.round((Number(file.size) || 0) / 1024))} KB)</span>
        <button type="button" data-file-index="${index}" aria-label="Remove file">✕</button>
      `;
      bar.appendChild(chip);
    });

    qsa("[data-file-index]", bar).forEach((btn) => {
      btn.addEventListener("click", () => {
        const index = Number(btn.getAttribute("data-file-index"));
        if (Number.isNaN(index)) return;
        state.attachedFiles.splice(index, 1);
        renderAttachedFiles();

        const fileInput = byId("fileInput");
        if (!state.attachedFiles.length && fileInput) {
          fileInput.value = "";
        }
      });
    });
  }

  function updateSessionBadge() {
    const titleEl = byId("chatTitle") || byId("sessionTitle");
    const subtitleEl = byId("chatSubtitle") || byId("sessionSubtitle");

    const currentSession = state.sessions.find(
      (item) => item.id === state.activeSessionId || item.session_id === state.activeSessionId
    );

    if (titleEl) titleEl.textContent = currentSession?.title || "Nova";
    if (subtitleEl) {
      subtitleEl.textContent = state.isSending
        ? "Thinking..."
        : `${state.messages.length || 0} messages`;
    }
  }

  function buildRouterBadgeHtml(router) {
    if (!router) return "";

    const mode = safeText(router.mode || "general");
    const intent = safeText(router.intent || "chat");
    const memoryHits = Number.isFinite(router.memory_hits)
      ? router.memory_hits
      : Number(router.memory_hits || 0);
    const normalizedMemoryCount = Number.isFinite(router.memory_count)
      ? router.memory_count
      : Number(router.memory_count || memoryHits || 0);

    return `
      <div class="router-badge">
        <span class="router-badge-pill rb-mode" data-mode="${escapeHtml(mode)}">${escapeHtml(mode)}</span>
        <span class="router-badge-pill rb-intent">${escapeHtml(intent)}</span>
        <span class="router-badge-pill rb-memory">mem:${escapeHtml(normalizedMemoryCount)}</span>
      </div>
    `;
  }

  function updateRouterDebug(router) {
    state.lastRouter = router || null;

    const content = byId("routerContent");
    if (!content || !router) return;

    const preview = Array.isArray(router.memory_preview)
      ? router.memory_preview
      : Array.isArray(router.memory_items)
      ? router.memory_items
      : Array.isArray(router.memory_used)
      ? router.memory_used
      : [];

    const previewHtml = preview.length
      ? `<ul class="router-debug-list">${preview
          .map((item) => `<li>${escapeHtml(item)}</li>`)
          .join("")}</ul>`
      : `<div class="router-debug-empty">—</div>`;

    const ts = Number(router.timestamp || 0);
    const timeText = ts ? formatTime(ts) : "—";
    const memoryHits = Number.isFinite(router.memory_hits)
      ? router.memory_hits
      : Number(router.memory_count || 0);

    content.innerHTML = `
      <div class="router-debug-row"><strong>Mode:</strong> ${escapeHtml(router.mode || "general")}</div>
      <div class="router-debug-row"><strong>Intent:</strong> ${escapeHtml(router.intent || "chat")}</div>
      <div class="router-debug-row"><strong>Reason:</strong> ${escapeHtml(router.reason || "auto")}</div>
      <div class="router-debug-row"><strong>Memory Hits:</strong> ${escapeHtml(memoryHits ?? 0)}</div>
      <div class="router-debug-row"><strong>Time:</strong> ${escapeHtml(timeText)}</div>
      <div class="router-debug-row"><strong>Memory Used:</strong>${previewHtml}</div>
    `;
  }

  function normalizeRouterMeta(payload) {
    if (!payload || typeof payload !== "object") return null;

    const raw =
      (payload.router_meta && typeof payload.router_meta === "object" && payload.router_meta) ||
      (payload.router && typeof payload.router === "object" && payload.router) ||
      null;

    if (!raw) return null;

    return {
      mode: raw.mode ?? "general",
      intent: raw.intent ?? "conversation",
      confidence: raw.confidence ?? null,
      reason: raw.reason ?? "",
      memory_used: raw.memory_used ?? false,
      memory_count: Number(raw.memory_count ?? raw.memory_hits ?? 0),
      memory_hits: Number(raw.memory_hits ?? raw.memory_count ?? 0),
      memory_items: Array.isArray(raw.memory_items) ? raw.memory_items : [],
      memory_preview: Array.isArray(raw.memory_preview)
        ? raw.memory_preview
        : Array.isArray(raw.memory_items)
        ? raw.memory_items
        : [],
      model: raw.model ?? null,
      provider: raw.provider ?? null,
      route_time_ms: raw.route_time_ms ?? null,
      source: raw.source ?? null,
      timestamp: raw.timestamp ?? null,
      updated_at: raw.updated_at ?? null,
    };
  }

  function applyIncomingRouterMeta(payload) {
    const meta = normalizeRouterMeta(payload);
    if (!meta) return null;

    state.lastRouter = meta;
    window.__novaLastRouterMeta = meta;

    try {
      window.dispatchEvent(new CustomEvent("nova:router-meta", { detail: meta }));
    } catch {}

    updateRouterDebug(meta);

    if (window.NovaRouterPanel && typeof window.NovaRouterPanel.applyRouterMeta === "function") {
      try {
        window.NovaRouterPanel.applyRouterMeta(meta);
      } catch {}
    }

    return meta;
  }

  function renderSessions() {
    const list =
      byId("sessionList") ||
      byId("sessionsList") ||
      qs("[data-role='session-list']");

    if (!list) return;

    if (!state.sessions.length) {
      list.innerHTML = `<div class="session-empty">No chats yet.</div>`;
      return;
    }

    list.innerHTML = state.sessions
      .map((session) => {
        const sessionId = session.id || session.session_id || "";
        const isActive = sessionId === state.activeSessionId;

        return `
          <button
            class="session-item ${isActive ? "active" : ""}"
            type="button"
            data-session-id="${escapeHtml(sessionId)}"
          >
            <div class="session-item-title">${escapeHtml(session.title || "New Chat")}</div>
            <div class="session-item-meta">${escapeHtml(String(session.message_count || 0))} messages</div>
          </button>
        `;
      })
      .join("");

    qsa("[data-session-id]", list).forEach((btn) => {
      btn.addEventListener("click", async () => {
        const sessionId = btn.getAttribute("data-session-id");
        if (!sessionId || sessionId === state.activeSessionId) return;

        try {
          setStatus("Loading chat...");
          await loadSession(sessionId);
          setStatus("Ready");
        } catch (err) {
          console.error(err);
          setStatus("Load failed");
        }
      });
    });
  }

  function renderMemory() {
    const list = byId("memoryList");
    if (!list) return;

    if (!state.memoryItems.length) {
      list.innerHTML = `<div class="memory-empty">No saved memory yet.</div>`;
      return;
    }

    list.innerHTML = state.memoryItems
      .map(
        (item) => `
        <div class="memory-item" data-memory-id="${escapeHtml(item.id || "")}">
          <div class="memory-item-main">
            <div class="memory-item-kind">${escapeHtml(item.kind || "memory")}</div>
            <div class="memory-item-value">${escapeHtml(item.value || "")}</div>
            <div class="memory-item-meta">${escapeHtml(
              formatTime(item.updated_at || item.created_at || nowUnix())
            )}</div>
          </div>

          <div class="memory-item-actions">
            <button
              class="memory-delete-btn"
              type="button"
              data-memory-delete="${escapeHtml(item.id || "")}"
              title="Delete memory"
              aria-label="Delete memory"
            >
              ✕
            </button>
          </div>
        </div>
      `
      )
      .join("");
  }

  function renderMessages() {
    const container = byId("chatMessages");
    if (!container) return;

    if (!state.messages.length) {
      container.innerHTML = `
        <div class="chat-empty-state">
          <div class="chat-empty-card">
            <div class="chat-empty-title">Nova is ready</div>
            <div class="chat-empty-subtitle">Start a new message.</div>
          </div>
        </div>
      `;
      updateLastUserMessage();
      updateSessionBadge();
      return;
    }

    container.innerHTML = state.messages
      .map((msg, index) => {
        const role = safeText(msg.role || "assistant").toLowerCase();
        const content = escapeHtml(msg.content || "").replace(/\n/g, "<br>");
        const time = formatTime(msg.timestamp || msg.created_at || nowUnix());
        const isAssistant = role === "assistant";
        const routerBadge = isAssistant
          ? buildRouterBadgeHtml(msg.router || msg.router_meta || null)
          : "";
        const cursorHtml =
          isAssistant && msg.streaming
            ? `<span class="nova-stream-cursor" aria-hidden="true">▍</span>`
            : "";
        const webResultsHtml =
          isAssistant && !msg.streaming
            ? renderWebResultsHtml(msg.web_results || msg.webResults || [])
            : "";

        return `
          <article class="chat-message ${escapeHtml(role)}">
            <div class="chat-message-role">${escapeHtml(role)}</div>
            ${routerBadge}
            <div class="chat-message-content">${content || "&nbsp;"}${cursorHtml}</div>
            ${webResultsHtml}
            <div class="chat-message-footer">
              <div class="chat-message-time">${escapeHtml(time)}</div>
              ${
                isAssistant
                  ? `
                <div class="chat-message-actions">
                  <button
                    type="button"
                    class="chat-message-action-btn"
                    data-copy-index="${index}"
                    aria-label="Copy message"
                  >
                    Copy
                  </button>
                </div>
              `
                  : ""
              }
            </div>
          </article>
        `;
      })
      .join("");

    qsa("[data-copy-index]", container).forEach((btn) => {
      btn.addEventListener("click", async () => {
        const index = Number(btn.getAttribute("data-copy-index"));
        if (Number.isNaN(index)) return;

        const msg = state.messages[index];
        if (!msg) return;

        const original = btn.textContent;
        const ok = await copyTextToClipboard(msg.content || "");
        btn.textContent = ok ? "Copied" : "Failed";

        setTimeout(() => {
          btn.textContent = original || "Copy";
        }, 1200);
      });
    });

    const lastAssistant = [...state.messages]
      .reverse()
      .find(
        (msg) => safeText(msg.role).toLowerCase() === "assistant" && (msg.router || msg.router_meta)
      );

    if (lastAssistant?.router || lastAssistant?.router_meta) {
      updateRouterDebug(lastAssistant.router || lastAssistant.router_meta);
    }

    updateLastUserMessage();
    updateSessionBadge();
    scrollChatToBottom();
  }

  function addLocalMessage(role, content, router = null, webResults = []) {
    state.messages.push({
      role: safeText(role || "assistant"),
      content: String(content ?? ""),
      timestamp: nowUnix(),
      router,
      web_results: Array.isArray(webResults) ? webResults : [],
    });
    renderMessages();
  }

  async function loadState() {
    const data = await apiGet(API.state);
    state.sessions = Array.isArray(data.sessions) ? data.sessions : [];

    const currentSessionId = data.current_session_id || null;

    if (state.activeSessionId) {
      const exists = state.sessions.some(
        (s) => (s.id || s.session_id) === state.activeSessionId
      );
      if (!exists) {
        state.activeSessionId =
          state.sessions[0]?.id || state.sessions[0]?.session_id || currentSessionId || null;
      }
    } else if (state.sessions.length) {
      state.activeSessionId = state.sessions[0].id || state.sessions[0].session_id || currentSessionId;
    } else {
      state.activeSessionId = currentSessionId;
    }

    if (data.router_meta || data.last_router_meta || data.router) {
      applyIncomingRouterMeta({
        router_meta: data.router_meta || data.last_router_meta || null,
        router: data.router || null,
      });
    }

    renderSessions();
    updateSessionBadge();
  }

  async function loadSession(sessionId) {
    if (!sessionId) return;

    const data = await apiGet(API.getChat(sessionId));
    state.activeSessionId = data.session?.id || data.session_id || sessionId;

    const incomingMessages = Array.isArray(data.messages)
      ? data.messages
      : Array.isArray(data.session?.messages)
      ? data.session.messages
      : [];

    state.messages = incomingMessages.map((msg) => ({
      ...msg,
      web_results: Array.isArray(msg?.web_results || msg?.webResults)
        ? msg.web_results || msg.webResults
        : [],
    }));

    if (data.router_meta || data.last_router_meta || data.router) {
      applyIncomingRouterMeta({
        router_meta: data.router_meta || data.last_router_meta || null,
        router: data.router || data.session?.router_meta || null,
      });
    }

    renderMessages();
    renderSessions();
  }

  async function loadMemory() {
    const data = await apiGet(API.memory);
    state.memoryItems = Array.isArray(data.memory)
      ? data.memory
      : Array.isArray(data.items)
      ? data.items
      : [];
    renderMemory();
  }

  async function createNewSession() {
    const data = await apiPost(API.newSession, {});
    await loadState();

    const newId = data.session?.id || data.session_id || null;

    if (newId) {
      await loadSession(newId);
    } else {
      state.messages = [];
      renderMessages();
    }
  }

  async function addMemory(kind, value) {
    await apiPost(API.addMemory, { kind, value });
    await loadMemory();
  }

  async function deleteMemory(id) {
    await apiPost(API.deleteMemory, { id });
    await loadMemory();
  }

  function parseSSEBlock(block) {
    const lines = String(block || "").split(/\r?\n/);
    let eventName = "message";
    const dataLines = [];

    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }

    const rawData = dataLines.join("\n").trim();
    if (!rawData) {
      return { event: eventName, data: {} };
    }

    if (rawData === "[DONE]") {
      return { event: eventName, data: { type: "done_marker" } };
    }

    try {
      return { event: eventName, data: JSON.parse(rawData) };
    } catch {
      return { event: eventName, data: { raw: rawData } };
    }
  }

  async function streamSend(content, attachedFilesOverride = null, options = {}) {
    const input = byId("messageInput");
    const normalizedContent = safeText(content);
    const pendingFiles = Array.isArray(attachedFilesOverride)
      ? [...attachedFilesOverride]
      : [...state.attachedFiles];

    if (!normalizedContent && !pendingFiles.length) return;

    if (!state.activeSessionId) {
      await createNewSession();
    }

    const suppressLocalUser = Boolean(options.suppressLocalUser);
    let assistantStreamMessage = null;
    let uploadedFiles = [];
    const activeSessionIdBeforeSend = state.activeSessionId;

    setSendingState(true);
    setStatus("Responding...");

    try {
      if (!suppressLocalUser) {
        if (normalizedContent) {
          addLocalMessage("user", normalizedContent);
        } else if (pendingFiles.length) {
          addLocalMessage("user", `[Uploaded ${pendingFiles.length} file(s)]`);
        }
      }

      assistantStreamMessage = {
        role: "assistant",
        content: "",
        timestamp: nowUnix(),
        router: null,
        web_results: [],
        streaming: true,
      };
      state.messages.push(assistantStreamMessage);

      let finalContent = "";
      let streamRouter = null;
      let pendingDelta = "";
      let renderScheduled = false;
      let streamFinished = false;

      function flushPendingDelta() {
        if (!pendingDelta) return;
        finalContent += pendingDelta;
        assistantStreamMessage.content = finalContent;
        pendingDelta = "";
      }

      function scheduleRender() {
        if (renderScheduled) return;
        renderScheduled = true;
        requestAnimationFrame(() => {
          renderScheduled = false;
          flushPendingDelta();
          renderMessages();
        });
      }

      function applyRouter(routerLike) {
        const normalized = applyIncomingRouterMeta(routerLike);
        if (!normalized) return;
        streamRouter = normalized;
        assistantStreamMessage.router = normalized;
        scheduleRender();
      }

      function finalizeAssistant(finalText = "") {
        flushPendingDelta();

        if (typeof finalText === "string" && finalText) {
          assistantStreamMessage.content = finalText;
          finalContent = finalText;
        } else {
          assistantStreamMessage.content = assistantStreamMessage.content || finalContent || "";
          finalContent = assistantStreamMessage.content;
        }

        if (streamRouter) {
          assistantStreamMessage.router = streamRouter;
        }

        assistantStreamMessage.streaming = false;
        streamFinished = true;
        renderMessages();
      }

      function handlePayload(data, fallbackEvent = "") {
        const payload = data && typeof data === "object" ? data : {};
        const dataType = safeText(payload.type).toLowerCase();
        const eventType = safeText(fallbackEvent).toLowerCase();
        const resolvedType = dataType || eventType;

        if (!resolvedType || resolvedType === "done_marker") {
          return;
        }

        if (
          resolvedType === "meta" ||
          resolvedType === "router" ||
          payload.router ||
          payload.router_meta
        ) {
          applyRouter(payload);
        }

        if (resolvedType === "start") {
          if (payload.session_id) {
            state.activeSessionId = payload.session_id;
          }
          return;
        }

        if (resolvedType === "meta" || resolvedType === "router") {
          if (payload.session_id) {
            state.activeSessionId = payload.session_id;
          }
          return;
        }

        if (resolvedType === "delta") {
          const delta =
            typeof payload.delta === "string"
              ? payload.delta
              : typeof payload.content === "string"
              ? payload.content
              : typeof payload.text === "string"
              ? payload.text
              : "";

          if (!delta) return;

          pendingDelta += delta;
          scheduleRender();
          return;
        }

        if (resolvedType === "done") {
          const final =
            typeof payload.response === "string"
              ? payload.response
              : typeof payload.message?.content === "string"
              ? payload.message.content
              : typeof payload.content === "string"
              ? payload.content
              : finalContent;

          if (payload.session_id) {
            state.activeSessionId = payload.session_id;
          }

          assistantStreamMessage.web_results = Array.isArray(payload.web_results)
            ? payload.web_results
            : Array.isArray(payload.message?.web_results)
            ? payload.message.web_results
            : [];

          finalizeAssistant(final || assistantStreamMessage.content || finalContent);
          return;
        }

        if (resolvedType === "error") {
          throw new Error(payload.message || payload.error || "Stream failed");
        }
      }

      renderMessages();

      if (input && attachedFilesOverride === null && !suppressLocalUser) {
        input.value = "";
        autosizeInput();
      }

      if (pendingFiles.length) {
        setStatus("Uploading...");
        uploadedFiles = await uploadFiles(pendingFiles);
        setStatus("Responding...");
      }

      const model = safeText(state.currentModel) || DEFAULT_MODEL;

      let res;
      try {
        res = await fetch(API.stream, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream, application/json, text/plain, */*",
          },
          credentials: "same-origin",
          body: JSON.stringify({
            session_id: state.activeSessionId,
            content: normalizedContent,
            message: normalizedContent,
            model,
            uploaded_files: uploadedFiles,
          }),
        });
      } catch (err) {
        console.error("STREAM FETCH FAILED:", err);
        throw new Error(`Network error reaching ${API.stream}. Check backend, port, tunnel, or crashed route.`);
      }

      if (!res.ok) {
        let details = "";
        try {
          details = await res.text();
        } catch {}

        console.error("STREAM HTTP ERROR:", res.status, details);

        if (res.status === 401) {
          throw new Error("Unauthorized. Log in to Nova again.");
        }

        throw new Error(
          `Send failed (${res.status})${details ? `: ${details.slice(0, 300)}` : ""}`
        );
      }

      if (!res.body || typeof res.body.getReader !== "function") {
        const text = await res.text();
        finalizeAssistant(safeText(text) || "No response.");
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

            if (!rawBlock || rawBlock === "data: [DONE]") continue;

            let parsed;
            try {
              parsed = parseSSEBlock(rawBlock);
            } catch (err) {
              console.warn("Failed to parse SSE block:", rawBlock, err);
              continue;
            }

            handlePayload(parsed.data || {}, parsed.event || "");
          }
        }

        const trailing = buffer.trim();
        if (trailing && trailing !== "data: [DONE]") {
          try {
            const parsed = parseSSEBlock(trailing);
            handlePayload(parsed.data || {}, parsed.event || "");
          } catch (err) {
            console.warn("Trailing SSE parse failed:", err);
          }
        }

        if (!streamFinished) {
          finalizeAssistant(assistantStreamMessage.content || finalContent || "");
        }
      }

      if (attachedFilesOverride === null) {
        state.attachedFiles = [];
        renderAttachedFiles();
        const fileInput = byId("fileInput");
        if (fileInput) fileInput.value = "";
      }

      await loadState();
      if (state.activeSessionId || activeSessionIdBeforeSend) {
        await loadSession(state.activeSessionId || activeSessionIdBeforeSend);
      }
      await loadMemory();
      renderMessages();
      renderSessions();
      renderMemory();
      setStatus("Ready");
    } catch (err) {
      console.error(err);

      if (assistantStreamMessage) {
        assistantStreamMessage.streaming = false;
        assistantStreamMessage.content =
          assistantStreamMessage.content || `Error: ${err.message || err}`;
        assistantStreamMessage.router = {
          mode: "general",
          intent: "error",
          reason: "frontend exception",
          memory_hits: 0,
          memory_count: 0,
          memory_preview: [],
          timestamp: nowUnix(),
        };
        applyIncomingRouterMeta({ router: assistantStreamMessage.router });
        renderMessages();
      } else {
        const errorRouter = {
          mode: "general",
          intent: "error",
          reason: "frontend exception",
          memory_hits: 0,
          memory_count: 0,
          memory_preview: [],
          timestamp: nowUnix(),
        };
        applyIncomingRouterMeta({ router: errorRouter });
        addLocalMessage("assistant", "Something went wrong sending that message.", errorRouter);
      }

      try {
        await loadState();
        if (state.activeSessionId || activeSessionIdBeforeSend) {
          await loadSession(state.activeSessionId || activeSessionIdBeforeSend);
        }
      } catch (_) {}

      setStatus("Send failed");
    } finally {
      setSendingState(false);
      renderMessages();
      autosizeInput();
      scrollChatToBottom();
      if (safeText((byId("modelStatus") || {}).textContent).toLowerCase() === "responding...") {
        setStatus("Ready");
      }
    }
  }

  async function sendMessage() {
    const input = byId("messageInput");
    const text = safeText(input?.value || "");
    if ((!text && !state.attachedFiles.length) || state.isSending) return;
    await streamSend(text);
  }

  async function regenerateLastReply() {
    if (!state.lastUserMessage || state.isSending) return;
    await streamSend(state.lastUserMessage, [], { suppressLocalUser: false });
  }

  function setPanelBodyState(isOpen) {
    document.body.classList.toggle("panel-open", Boolean(isOpen));
  }

  function isMobilePanel() {
    return window.matchMedia("(max-width: 980px)").matches;
  }

  function closeMobilePanels() {
    document.body.classList.remove("mobile-left-open", "mobile-right-open");
    setPanelBodyState(false);
  }

  function openLeftMobile() {
    document.body.classList.remove("mobile-right-open");
    document.body.classList.add("mobile-left-open");
    setPanelBodyState(true);
  }

  function openRightMobile() {
    document.body.classList.remove("mobile-left-open");
    document.body.classList.add("mobile-right-open");
    setPanelBodyState(true);
  }

  function syncPanelMode() {
    if (!isMobilePanel()) {
      closeMobilePanels();
    }
  }

  function resolveToggleRole(button) {
    if (!button) return null;

    const id = safeText(button.id).toLowerCase();
    const controls = safeText(button.getAttribute("aria-controls")).toLowerCase();
    const action = safeText(button.getAttribute("data-action")).toLowerCase();
    const label = safeText(button.getAttribute("aria-label")).toLowerCase();
    const title = safeText(button.getAttribute("title")).toLowerCase();
    const text = safeText(button.textContent).toLowerCase();

    const blob = [id, controls, action, label, title, text].join(" ");

    const explicitSidebarIds = new Set([
      "togglesidebar",
      "mobilesidebarbtn",
      "opensidebarbtn",
      "sidebartoggle",
    ]);

    const explicitMemoryIds = new Set([
      "togglememory",
      "togglememorypanel",
      "mobilememorybtn",
      "openmemorybtn",
      "memorytoggle",
    ]);

    if (explicitSidebarIds.has(id)) return "sidebar";
    if (explicitMemoryIds.has(id)) return "memory";

    if (controls === "sidebar") return "sidebar";
    if (controls === "memorypanel") return "memory";

    if (action === "toggle-sidebar") return "sidebar";
    if (action === "toggle-memory") return "memory";

    if (
      blob.includes("memory") ||
      button.closest("#memoryPanel") ||
      button.closest(".topbar-right")
    ) {
      return "memory";
    }

    if (
      blob.includes("sidebar") ||
      blob.includes("menu") ||
      button.closest("#sidebar") ||
      button.closest(".topbar-left")
    ) {
      return "sidebar";
    }

    return null;
  }

  function initPanelFix() {
    const sidebar = byId("sidebar");
    const memoryPanel = byId("memoryPanel");

    document.addEventListener(
      "click",
      (e) => {
        if (!isMobilePanel()) return;

        const button = e.target.closest("button, [role='button']");
        if (!button) return;

        const role = resolveToggleRole(button);
        if (!role) return;

        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation?.();

        if (role === "sidebar") {
          if (document.body.classList.contains("mobile-left-open")) {
            closeMobilePanels();
          } else {
            openLeftMobile();
          }
          return;
        }

        if (role === "memory") {
          if (document.body.classList.contains("mobile-right-open")) {
            closeMobilePanels();
          } else {
            openRightMobile();
          }
        }
      },
      true
    );

    document.addEventListener("click", (e) => {
      if (!isMobilePanel()) return;

      const target = e.target;
      const insideSidebar = sidebar?.contains(target);
      const insideMemory = memoryPanel?.contains(target);
      const clickedButton = target.closest("button, [role='button']");
      const role = resolveToggleRole(clickedButton);

      if (insideSidebar || insideMemory || role === "sidebar" || role === "memory") {
        return;
      }

      closeMobilePanels();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeMobilePanels();
      }
    });

    window.addEventListener("resize", syncPanelMode);
    window.addEventListener("orientationchange", syncPanelMode);

    syncPanelMode();
  }

  function ensureDesktopActionButtons() {
    const composer =
      byId("composerActions") ||
      byId("chatComposerActions") ||
      qs(".composer-actions") ||
      qs(".input-actions") ||
      byId("sendBtn")?.parentElement;

    if (!composer) return;

    if (!byId("regenerateBtn")) {
      const regenBtn = document.createElement("button");
      regenBtn.type = "button";
      regenBtn.id = "regenerateBtn";
      regenBtn.className = "nova-action-btn secondary";
      regenBtn.textContent = "Regenerate";

      const sendBtn = byId("sendBtn");
      if (sendBtn && sendBtn.parentElement === composer) {
        composer.insertBefore(regenBtn, sendBtn);
      } else {
        composer.appendChild(regenBtn);
      }
    }
  }

  function bindEvents() {
    ensureDesktopActionButtons();

    byId("newSessionBtn")?.addEventListener("click", async () => {
      try {
        setStatus("Creating chat...");
        await createNewSession();
        setStatus("Ready");
      } catch (err) {
        console.error(err);
        setStatus("Create failed");
      }
    });

    byId("sendBtn")?.addEventListener("click", sendMessage);
    byId("regenerateBtn")?.addEventListener("click", regenerateLastReply);

    byId("messageInput")?.addEventListener("input", autosizeInput);

    byId("messageInput")?.addEventListener("keydown", async (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        await sendMessage();
      }
    });

    byId("attachBtn")?.addEventListener("click", () => {
      if (state.isSending) return;
      byId("fileInput")?.click();
    });

    byId("fileInput")?.addEventListener("change", (event) => {
      const files = Array.from(event.target.files || []);
      if (!files.length) return;

      const existing = new Map(
        state.attachedFiles.map((file) => [`${file.name}__${file.size}`, file])
      );

      for (const file of files) {
        existing.set(`${file.name}__${file.size}`, file);
      }

      state.attachedFiles = Array.from(existing.values());
      renderAttachedFiles();

      const input = byId("fileInput");
      if (input) input.value = "";
    });

    byId("memoryForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();

      const kind = safeText(byId("memoryKind")?.value || "memory");
      const valueEl = byId("memoryValue");
      const value = safeText(valueEl?.value || "");

      if (!value) return;

      try {
        setStatus("Saving memory...");
        await addMemory(kind, value);
        if (valueEl) valueEl.value = "";
        setStatus("Ready");
      } catch (err) {
        console.error(err);
        setStatus("Save failed");
      }
    });

    document.addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-memory-delete]");
      if (!btn) return;

      const id = btn.getAttribute("data-memory-delete");
      if (!id) return;

      const ok = window.confirm("Delete this memory?");
      if (!ok) return;

      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = "...";

      try {
        await deleteMemory(id);
        setStatus("Memory deleted");
      } catch (err) {
        console.error(err);
        btn.disabled = false;
        btn.textContent = originalText;
        setStatus("Delete failed");
        alert("Delete failed");
      }
    });
  }

  async function bootstrap() {
    injectWebResultStyles();
    bindEvents();
    initPanelFix();
    setStatus("Loading...");

    await loadState();

    if (state.activeSessionId) {
      await loadSession(state.activeSessionId);
    } else {
      renderMessages();
    }

    await loadMemory();
    renderAttachedFiles();
    autosizeInput();
    setSendingState(false);
    setStatus("Ready");
  }

  document.addEventListener("DOMContentLoaded", () => {
    bootstrap().catch((err) => {
      console.error("Desktop bootstrap failed:", err);
      setStatus("Bootstrap failed");
      setSendingState(false);
    });
  });
})();