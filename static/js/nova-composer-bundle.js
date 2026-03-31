(function () {
  "use strict";

  const API_BASE = "";
  const STORAGE_KEY = "nova_active_session_id";
  const DEBUG_PREFIX = "[NovaComposerBundle]";
  const DEBUG_ENABLED = true;

  const state = {
    sending: false,
    activeSessionId: "",
    lastResponse: null,
    lastRequest: null,
    requestSeq: 0,
    debugPanelOpen: false,
  };

  const els = {
    messages: null,
    chatInput: null,
    sendBtn: null,
    emptyState: null,
    sessionList: null,
    sessionRail: null,
    sessionNewBtn: null,
    sessionRenameBtn: null,
    sessionPinBtn: null,
    sessionDeleteBtn: null,
    appShell: null,
    debugToggleBtn: null,
    debugPanel: null,
    debugStatus: null,
    debugRequest: null,
    debugResponse: null,
    debugRefreshBtn: null,
    debugCloseBtn: null,
    debugCopyBtn: null,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function qs(selector) {
    return document.querySelector(selector);
  }

  function debugLog() {
    if (!DEBUG_ENABLED) return;
    try {
      console.log(DEBUG_PREFIX, ...arguments);
    } catch (_err) {}
  }

  function debugWarn() {
    if (!DEBUG_ENABLED) return;
    try {
      console.warn(DEBUG_PREFIX, ...arguments);
    } catch (_err) {}
  }

  function debugError() {
    if (!DEBUG_ENABLED) return;
    try {
      console.error(DEBUG_PREFIX, ...arguments);
    } catch (_err) {}
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

  function safeJsonParse(text) {
    try {
      return JSON.parse(text);
    } catch (_err) {
      return null;
    }
  }

  function trimText(value, max) {
    const text = String(value == null ? "" : value);
    return text.length > max ? `${text.slice(0, max)}…` : text;
  }

  function nowIso() {
    try {
      return new Date().toISOString();
    } catch (_err) {
      return "";
    }
  }

  function makeAbsoluteUrl(path) {
    try {
      return new URL(`${API_BASE}${path}`, window.location.origin).toString();
    } catch (_err) {
      return `${API_BASE}${path}`;
    }
  }

  function prettyJson(value) {
    try {
      return JSON.stringify(value == null ? null : value, null, 2);
    } catch (_err) {
      return String(value);
    }
  }

  function copyText(text) {
    const value = String(text || "");
    if (!value) return Promise.resolve(false);

    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      return navigator.clipboard.writeText(value).then(
        function () {
          return true;
        },
        function () {
          return legacyCopyText(value);
        }
      );
    }

    return Promise.resolve(legacyCopyText(value));
  }

  function legacyCopyText(text) {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "readonly");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      ta.style.pointerEvents = "none";
      document.body.appendChild(ta);
      ta.select();
      ta.setSelectionRange(0, ta.value.length);
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return Boolean(ok);
    } catch (_err) {
      return false;
    }
  }

  async function api(path, options) {
    const method = (options && options.method) || "GET";
    const headers = {
      "Content-Type": "application/json",
      ...((options && options.headers) || {}),
    };
    const bodyObject = options && options.body ? options.body : undefined;
    const bodyText = bodyObject ? JSON.stringify(bodyObject) : undefined;
    const url = `${API_BASE}${path}`;
    const absoluteUrl = makeAbsoluteUrl(path);
    const requestId = ++state.requestSeq;
    const startedAtMs = Date.now();

    state.lastRequest = {
      id: requestId,
      method,
      path,
      url,
      absoluteUrl,
      started_at: nowIso(),
      body: bodyObject || null,
    };
    renderDebugPanel();

    debugLog(`request #${requestId} start`, {
      id: requestId,
      method,
      path,
      url,
      absoluteUrl,
      sameOrigin: absoluteUrl.indexOf(window.location.origin) === 0,
      body: bodyObject || null,
    });

    let response;
    let rawText = "";
    let data = null;

    try {
      response = await fetch(url, {
        method,
        headers,
        body: bodyText,
      });

      rawText = await response.text();
      data = safeJsonParse(rawText);

      const finishedAtMs = Date.now();
      const elapsedMs = finishedAtMs - startedAtMs;

      const responseMeta = {
        id: requestId,
        method,
        path,
        url,
        absoluteUrl,
        status: response.status,
        ok: response.ok,
        elapsed_ms: elapsedMs,
        received_at: nowIso(),
        response_json: data,
        response_text_preview: trimText(rawText, 4000),
      };

      state.lastResponse = responseMeta;
      renderDebugPanel();

      debugLog(`request #${requestId} response`, responseMeta);

      if (!response.ok) {
        const error = new Error(
          (data && (data.message || data.error)) ||
            `Request failed: ${response.status}`
        );
        error.status = response.status;
        error.data = data;
        error.rawText = rawText;
        error.requestId = requestId;
        error.path = path;
        error.url = absoluteUrl;
        throw error;
      }

      if (!data || typeof data !== "object") {
        const error = new Error("Server returned non-JSON response.");
        error.status = response.status;
        error.rawText = rawText;
        error.requestId = requestId;
        error.path = path;
        error.url = absoluteUrl;
        throw error;
      }

      return data;
    } catch (error) {
      const finishedAtMs = Date.now();
      const elapsedMs = finishedAtMs - startedAtMs;

      state.lastResponse = {
        id: requestId,
        method,
        path,
        url,
        absoluteUrl,
        status: error && typeof error.status !== "undefined" ? error.status : null,
        ok: false,
        elapsed_ms: elapsedMs,
        received_at: nowIso(),
        error_name: error && error.name ? error.name : "Error",
        error_message: error && error.message ? error.message : String(error),
        response_json: data,
        response_text_preview: trimText(rawText, 4000),
      };
      renderDebugPanel();

      debugError(`request #${requestId} failed`, {
        id: requestId,
        method,
        path,
        url,
        absoluteUrl,
        elapsed_ms: elapsedMs,
        error_name: error && error.name ? error.name : "Error",
        error_message: error && error.message ? error.message : String(error),
        status: error && typeof error.status !== "undefined" ? error.status : null,
        response_json: data,
        response_text_preview: trimText(rawText, 800),
        body: bodyObject || null,
      });

      throw error;
    }
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatTime(value) {
    if (!value) return "";
    try {
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return "";
      return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    } catch (_err) {
      return "";
    }
  }

  function truncate(value, max) {
    const text = String(value || "");
    return text.length > max ? `${text.slice(0, max - 1)}…` : text;
  }

  function setActiveSessionId(sessionId) {
    state.activeSessionId = String(sessionId || "").trim();
    if (state.activeSessionId) {
      localStorage.setItem(STORAGE_KEY, state.activeSessionId);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
    debugLog("active session set", { session_id: state.activeSessionId || null });
  }

  function getStoredSessionId() {
    return String(localStorage.getItem(STORAGE_KEY) || "").trim();
  }

  function ensureElements() {
    els.messages = byId("messages");
    els.chatInput = byId("chatInput");
    els.sendBtn = byId("sendBtn");
    els.emptyState = byId("novaEmptyState");
    els.sessionList = byId("sessionList") || qs("[data-session-list]");
    els.sessionRail = byId("sessionRail");
    els.sessionNewBtn = byId("sessionNewBtn");
    els.sessionRenameBtn = byId("sessionRenameBtn");
    els.sessionPinBtn = byId("sessionPinBtn");
    els.sessionDeleteBtn = byId("sessionDeleteBtn");
    els.appShell = byId("novaAppShell");

    debugLog("elements wired", {
      messages: Boolean(els.messages),
      chatInput: Boolean(els.chatInput),
      sendBtn: Boolean(els.sendBtn),
      emptyState: Boolean(els.emptyState),
      sessionList: Boolean(els.sessionList),
      sessionRail: Boolean(els.sessionRail),
      sessionNewBtn: Boolean(els.sessionNewBtn),
      sessionRenameBtn: Boolean(els.sessionRenameBtn),
      sessionPinBtn: Boolean(els.sessionPinBtn),
      sessionDeleteBtn: Boolean(els.sessionDeleteBtn),
      build:
        window.NovaFrontendLock && window.NovaFrontendLock.build
          ? window.NovaFrontendLock.build
          : null,
    });
  }

  function setSending(isSending) {
    state.sending = Boolean(isSending);

    if (els.sendBtn) {
      els.sendBtn.disabled = state.sending;
      els.sendBtn.textContent = state.sending ? "Sending..." : "Send";
    }

    if (els.chatInput) {
      els.chatInput.disabled = state.sending;
    }

    debugLog("sending state", { sending: state.sending });
  }

  function updateEmptyState() {
    if (!els.emptyState || !els.messages) return;
    const hasMessages = els.messages.children.length > 0;
    els.emptyState.style.display = hasMessages ? "none" : "";
  }

  function scrollMessagesToBottom() {
    if (!els.messages) return;
    const wrap = els.messages.closest(".nova-chat-wrap");
    if (wrap) {
      wrap.scrollTop = wrap.scrollHeight;
    } else {
      els.messages.scrollTop = els.messages.scrollHeight;
    }
  }

  function badgeHtml(label) {
    return `<span class="nova-badge">${escapeHtml(label)}</span>`;
  }

  function normalizeMessage(message, fallbackRole) {
    const role = String((message && message.role) || fallbackRole || "assistant");
    const content = String((message && message.content) || "");
    const createdAt = (message && message.created_at) || "";
    const meta = (message && message.meta) || {};
    const attachments = Array.isArray(message && message.attachments)
      ? message.attachments
      : [];

    return {
      id: String((message && message.id) || ""),
      role,
      content,
      created_at: createdAt,
      meta,
      attachments,
    };
  }

  function renderMessage(message) {
    if (!els.messages) return;

    const normalized = normalizeMessage(message);
    const role = normalized.role === "user" ? "user" : "assistant";
    const timeLabel = formatTime(normalized.created_at);

    const wrapper = document.createElement("article");
    wrapper.className = `nova-message nova-message-${role}`;
    wrapper.dataset.messageRole = role;
    if (normalized.id) wrapper.dataset.messageId = normalized.id;

    const badges = [];
    if (role === "assistant") badges.push(badgeHtml("Nova"));
    if (normalized.meta && normalized.meta.fallback) badges.push(badgeHtml("Fallback"));
    if (normalized.meta && normalized.meta.fallback_reason) {
      badges.push(badgeHtml(truncate(normalized.meta.fallback_reason, 28)));
    }
    if (normalized.attachments.length) {
      badges.push(badgeHtml(`Files ${normalized.attachments.length}`));
    }

    wrapper.innerHTML = `
      <div class="nova-artifact-card">
        <div class="nova-meta-row">
          ${badges.join("")}
          ${timeLabel ? `<span class="nova-badge">${escapeHtml(timeLabel)}</span>` : ""}
        </div>
        <pre class="nova-pre">${escapeHtml(normalized.content)}</pre>
      </div>
    `;

    els.messages.appendChild(wrapper);
  }

  function renderMessages(messages) {
    if (!els.messages) return;
    els.messages.innerHTML = "";

    const safeMessages = Array.isArray(messages) ? messages : [];
    for (const message of safeMessages) {
      renderMessage(message);
    }

    updateEmptyState();
    scrollMessagesToBottom();

    debugLog("messages rendered", {
      count: safeMessages.length,
      active_session_id: state.activeSessionId || null,
    });
  }

  function renderSessionList(sessions) {
    const container =
      els.sessionList ||
      els.sessionRail ||
      byId("sessionList") ||
      byId("sessionRail") ||
      qs("[data-session-list]");

    if (!container) {
      debugWarn("renderSessionList skipped: no container found");
      return;
    }

    const renderInto =
      container.id === "sessionRail" && byId("sessionList")
        ? byId("sessionList")
        : container;

    renderInto.innerHTML = "";

    const safeSessions = Array.isArray(sessions) ? sessions : [];

    for (const session of safeSessions) {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "nova-artifact-card";
      if (String(session.id || "") === state.activeSessionId) {
        item.classList.add("is-active");
      }

      const badges = [];
      if (session.pinned) badges.push(badgeHtml("Pinned"));
      if (Number(session.message_count || 0) > 0) {
        badges.push(badgeHtml(`${Number(session.message_count || 0)} msgs`));
      }

      item.innerHTML = `
        <div class="nova-meta-row">
          ${badges.join("")}
        </div>
        <div><strong>${escapeHtml(session.title || "Untitled")}</strong></div>
        <div class="nova-kv">
          <div>${escapeHtml(truncate(session.last_message_preview || "No messages yet.", 100))}</div>
        </div>
      `;

      item.addEventListener("click", function () {
        hardRestoreSession(session.id);
      });

      renderInto.appendChild(item);
    }

    debugLog("session list rendered", {
      count: safeSessions.length,
      active_session_id: state.activeSessionId || null,
      render_target_id: renderInto.id || null,
    });
  }

  function buildOptimisticUserMessage(content) {
    return {
      id: `temp-user-${Date.now()}`,
      role: "user",
      content: String(content || ""),
      created_at: new Date().toISOString(),
      attachments: [],
      meta: {
        optimistic: true,
      },
    };
  }

  function normalizeChatResponse(payload) {
    const debug = payload && typeof payload === "object" ? payload.debug || {} : {};
    const session =
      payload && payload.session && typeof payload.session === "object"
        ? payload.session
        : null;

    const assistantMessage =
      payload && payload.assistant_message && typeof payload.assistant_message === "object"
        ? normalizeMessage(payload.assistant_message, "assistant")
        : null;

    let messages = [];
    if (session && Array.isArray(session.messages)) {
      messages = session.messages.map((m) => normalizeMessage(m));
    } else if (assistantMessage) {
      messages = [assistantMessage];
    }

    return {
      ok: Boolean(payload && payload.ok !== false),
      session,
      assistant_message: assistantMessage,
      debug,
      messages,
      raw: payload || {},
    };
  }

  function ensureDebugPanel() {
    if (els.debugPanel) return;

    const host = els.appShell || document.body;
    if (!host) return;

    const styleId = "nova-composer-debug-panel-style";
    if (!document.getElementById(styleId)) {
      const style = document.createElement("style");
      style.id = styleId;
      style.textContent = `
        .nova-debug-toggle {
          position: fixed;
          right: 18px;
          bottom: 18px;
          z-index: 9998;
          border: 1px solid rgba(130,158,222,0.24);
          background: rgba(15,27,49,0.96);
          color: #eef4ff;
          border-radius: 12px;
          padding: 10px 12px;
          font-size: 12px;
          font-weight: 800;
          cursor: pointer;
          box-shadow: 0 18px 60px rgba(0,0,0,0.28);
        }
        .nova-debug-panel {
          position: fixed;
          right: 18px;
          bottom: 68px;
          width: min(720px, calc(100vw - 36px));
          max-height: min(78vh, 860px);
          z-index: 9999;
          display: none;
          grid-template-rows: auto auto minmax(0,1fr);
          overflow: hidden;
          border-radius: 18px;
          border: 1px solid rgba(130,158,222,0.24);
          background: rgba(12,20,37,0.98);
          color: #eef4ff;
          box-shadow: 0 24px 80px rgba(0,0,0,0.34);
          backdrop-filter: blur(14px);
        }
        .nova-debug-panel.is-open {
          display: grid;
        }
        .nova-debug-head {
          padding: 14px 16px;
          border-bottom: 1px solid rgba(130,158,222,0.14);
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          background: rgba(255,255,255,0.02);
        }
        .nova-debug-title {
          font-size: 13px;
          font-weight: 900;
          letter-spacing: .02em;
        }
        .nova-debug-status {
          color: #9cafcf;
          font-size: 12px;
        }
        .nova-debug-actions {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          padding: 12px 16px;
          border-bottom: 1px solid rgba(130,158,222,0.14);
        }
        .nova-debug-btn {
          appearance: none;
          border: 1px solid rgba(130,158,222,0.24);
          background: rgba(255,255,255,0.04);
          color: #eef4ff;
          border-radius: 10px;
          padding: 8px 10px;
          font-size: 11px;
          font-weight: 800;
          cursor: pointer;
        }
        .nova-debug-btn:hover {
          background: rgba(255,255,255,0.08);
        }
        .nova-debug-body {
          min-height: 0;
          overflow: auto;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0;
        }
        .nova-debug-col {
          min-height: 0;
          display: grid;
          grid-template-rows: auto minmax(0,1fr);
          border-right: 1px solid rgba(130,158,222,0.12);
        }
        .nova-debug-col:last-child {
          border-right: none;
        }
        .nova-debug-col-head {
          padding: 10px 14px;
          border-bottom: 1px solid rgba(130,158,222,0.12);
          font-size: 11px;
          font-weight: 900;
          letter-spacing: .04em;
          color: #9cafcf;
          text-transform: uppercase;
          background: rgba(255,255,255,0.02);
        }
        .nova-debug-pre {
          margin: 0;
          padding: 14px;
          overflow: auto;
          white-space: pre-wrap;
          word-break: break-word;
          font: 12px/1.5 Consolas, "Courier New", monospace;
          color: #eef4ff;
        }
        @media (max-width: 900px) {
          .nova-debug-panel {
            right: 10px;
            left: 10px;
            width: auto;
            bottom: 60px;
          }
          .nova-debug-body {
            grid-template-columns: 1fr;
          }
          .nova-debug-col {
            border-right: none;
            border-bottom: 1px solid rgba(130,158,222,0.12);
          }
          .nova-debug-col:last-child {
            border-bottom: none;
          }
        }
      `;
      document.head.appendChild(style);
    }

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "nova-debug-toggle";
    toggle.id = "novaDebugToggleBtn";
    toggle.textContent = "Debug";

    const panel = document.createElement("section");
    panel.className = "nova-debug-panel";
    panel.id = "novaDebugPanel";
    panel.setAttribute("aria-hidden", "true");

    panel.innerHTML = `
      <div class="nova-debug-head">
        <div>
          <div class="nova-debug-title">Nova Request Debug</div>
          <div class="nova-debug-status" id="novaDebugStatus">No request yet.</div>
        </div>
      </div>
      <div class="nova-debug-actions">
        <button type="button" class="nova-debug-btn" id="novaDebugRefreshBtn">Refresh</button>
        <button type="button" class="nova-debug-btn" id="novaDebugCopyBtn">Copy</button>
        <button type="button" class="nova-debug-btn" id="novaDebugCloseBtn">Close</button>
      </div>
      <div class="nova-debug-body">
        <div class="nova-debug-col">
          <div class="nova-debug-col-head">Last Request</div>
          <pre class="nova-debug-pre" id="novaDebugRequest">{}</pre>
        </div>
        <div class="nova-debug-col">
          <div class="nova-debug-col-head">Last Response</div>
          <pre class="nova-debug-pre" id="novaDebugResponse">{}</pre>
        </div>
      </div>
    `;

    document.body.appendChild(toggle);
    document.body.appendChild(panel);

    els.debugToggleBtn = toggle;
    els.debugPanel = panel;
    els.debugStatus = byId("novaDebugStatus");
    els.debugRequest = byId("novaDebugRequest");
    els.debugResponse = byId("novaDebugResponse");
    els.debugRefreshBtn = byId("novaDebugRefreshBtn");
    els.debugCloseBtn = byId("novaDebugCloseBtn");
    els.debugCopyBtn = byId("novaDebugCopyBtn");

    toggle.addEventListener("click", function () {
      toggleDebugPanel();
    });

    if (els.debugCloseBtn) {
      els.debugCloseBtn.addEventListener("click", function () {
        closeDebugPanel();
      });
    }

    if (els.debugRefreshBtn) {
      els.debugRefreshBtn.addEventListener("click", function () {
        renderDebugPanel();
      });
    }

    if (els.debugCopyBtn) {
      els.debugCopyBtn.addEventListener("click", function () {
        const payload = {
          request: state.lastRequest,
          response: state.lastResponse,
          debugState: {
            sending: state.sending,
            activeSessionId: state.activeSessionId,
            requestSeq: state.requestSeq,
            frontendLock: window.NovaFrontendLock || null,
            href: window.location.href,
            origin: window.location.origin,
          },
        };

        copyText(prettyJson(payload)).then(function (ok) {
          statusSuccess(ok ? "Debug copied." : "Copy failed.");
        });
      });
    }

    renderDebugPanel();
    debugLog("debug panel ready");
  }

  function openDebugPanel() {
    state.debugPanelOpen = true;
    renderDebugPanel();
  }

  function closeDebugPanel() {
    state.debugPanelOpen = false;
    renderDebugPanel();
  }

  function toggleDebugPanel() {
    state.debugPanelOpen = !state.debugPanelOpen;
    renderDebugPanel();
  }

  function renderDebugPanel() {
    ensureDebugPanel();
    if (!els.debugPanel) return;

    const requestText = prettyJson(state.lastRequest);
    const responseText = prettyJson(state.lastResponse);

    if (els.debugRequest) {
      els.debugRequest.textContent = requestText;
    }

    if (els.debugResponse) {
      els.debugResponse.textContent = responseText;
    }

    if (els.debugStatus) {
      if (state.lastRequest && state.lastResponse) {
        const statusBits = [
          `#${state.lastRequest.id || "-"}`,
          state.lastRequest.method || "",
          state.lastRequest.path || "",
          typeof state.lastResponse.status !== "undefined" && state.lastResponse.status !== null
            ? `status ${state.lastResponse.status}`
            : "no status",
          typeof state.lastResponse.elapsed_ms !== "undefined"
            ? `${state.lastResponse.elapsed_ms} ms`
            : "",
        ].filter(Boolean);
        els.debugStatus.textContent = statusBits.join(" • ");
      } else if (state.lastRequest) {
        els.debugStatus.textContent = `#${state.lastRequest.id || "-"} ${state.lastRequest.method || ""} ${state.lastRequest.path || ""}`;
      } else {
        els.debugStatus.textContent = "No request yet.";
      }
    }

    if (els.debugPanel) {
      els.debugPanel.classList.toggle("is-open", state.debugPanelOpen);
      els.debugPanel.setAttribute("aria-hidden", state.debugPanelOpen ? "false" : "true");
    }

    if (els.debugToggleBtn) {
      els.debugToggleBtn.textContent = state.debugPanelOpen ? "Debug ×" : "Debug";
    }
  }

  async function reloadSessionsAndHighlight() {
    try {
      debugLog("reloadSessionsAndHighlight start");
      const data = await api("/api/sessions");
      renderSessionList(data.sessions || []);
      debugLog("reloadSessionsAndHighlight done", {
        sessions_count: Array.isArray(data.sessions) ? data.sessions.length : 0,
      });
    } catch (error) {
      debugError("reloadSessionsAndHighlight failed", error);
    }
  }

  async function hardRestoreSession(sessionId) {
    const cleanId = String(sessionId || "").trim();
    if (!cleanId) return;

    statusPending("Restoring session...");
    debugLog("hardRestoreSession start", { session_id: cleanId });

    try {
      const data = await api(`/api/sessions/${encodeURIComponent(cleanId)}`);
      const session = data.session || null;
      if (!session) throw new Error("Session payload missing.");

      setActiveSessionId(session.id || cleanId);
      renderMessages(Array.isArray(session.messages) ? session.messages : []);
      await reloadSessionsAndHighlight();

      document.dispatchEvent(
        new CustomEvent("nova:session-restored", {
          detail: { session },
        })
      );

      debugLog("hardRestoreSession done", {
        session_id: session.id || cleanId,
        message_count: Array.isArray(session.messages) ? session.messages.length : 0,
      });

      statusSuccess("Session restored.");
    } catch (error) {
      debugError("hardRestoreSession failed", error);
      statusError(error.message || "Failed to restore session.");
    }
  }

  async function ensureActiveSession() {
    if (state.activeSessionId) return state.activeSessionId;

    const stored = getStoredSessionId();
    if (stored) {
      state.activeSessionId = stored;
      debugLog("ensureActiveSession using stored session", { session_id: stored });
      return stored;
    }

    statusPending("Creating session...");
    debugLog("ensureActiveSession creating new session");

    const data = await api("/api/sessions", {
      method: "POST",
      body: { title: "New Session" },
    });

    const session = data.session || {};
    setActiveSessionId(session.id || "");
    await reloadSessionsAndHighlight();
    statusSuccess("Session created.");

    debugLog("ensureActiveSession created", {
      session_id: state.activeSessionId || null,
    });

    return state.activeSessionId;
  }

  async function createNewSession() {
    try {
      statusPending("Creating session...");
      debugLog("createNewSession start");

      const data = await api("/api/sessions", {
        method: "POST",
        body: { title: "New Session" },
      });

      const session = data.session || {};
      setActiveSessionId(session.id || "");
      renderMessages(Array.isArray(session.messages) ? session.messages : []);
      await reloadSessionsAndHighlight();

      document.dispatchEvent(
        new CustomEvent("nova:session-created", {
          detail: { session },
        })
      );

      debugLog("createNewSession done", {
        session_id: session.id || null,
      });

      statusSuccess("New session ready.");
    } catch (error) {
      debugError("createNewSession failed", error);
      statusError(error.message || "Failed to create session.");
    }
  }

  async function renameActiveSession() {
    if (!state.activeSessionId) return;
    const currentTitle =
      qs(".nova-artifact-card.is-active strong")?.textContent || "Session";
    const title = window.prompt("Rename session", currentTitle);
    if (!title || !title.trim()) return;

    try {
      statusPending("Renaming session...");
      debugLog("renameActiveSession start", {
        session_id: state.activeSessionId,
        title: title.trim(),
      });

      await api(`/api/sessions/${encodeURIComponent(state.activeSessionId)}`, {
        method: "PATCH",
        body: { title: title.trim() },
      });
      await hardRestoreSession(state.activeSessionId);
      statusSuccess("Session renamed.");
    } catch (error) {
      debugError("renameActiveSession failed", error);
      statusError(error.message || "Failed to rename session.");
    }
  }

  async function togglePinActiveSession() {
    if (!state.activeSessionId) return;

    try {
      statusPending("Updating pin...");
      debugLog("togglePinActiveSession start", {
        session_id: state.activeSessionId,
      });

      const current = await api(`/api/sessions/${encodeURIComponent(state.activeSessionId)}`);
      const session = current.session || {};
      const nextPinned = !Boolean(session.pinned);

      await api(`/api/sessions/${encodeURIComponent(state.activeSessionId)}`, {
        method: "PATCH",
        body: { pinned: nextPinned },
      });

      await hardRestoreSession(state.activeSessionId);
      statusSuccess(nextPinned ? "Session pinned." : "Session unpinned.");
    } catch (error) {
      debugError("togglePinActiveSession failed", error);
      statusError(error.message || "Failed to update pin.");
    }
  }

  async function deleteActiveSession() {
    if (!state.activeSessionId) return;

    const ok = window.confirm("Delete this session?");
    if (!ok) return;

    const deletingId = state.activeSessionId;

    try {
      statusPending("Deleting session...");
      debugLog("deleteActiveSession start", {
        session_id: deletingId,
      });

      await api(`/api/sessions/${encodeURIComponent(deletingId)}`, {
        method: "DELETE",
      });

      setActiveSessionId("");
      renderMessages([]);
      await reloadSessionsAndHighlight();

      const sessionsData = await api("/api/sessions");
      const sessions = Array.isArray(sessionsData.sessions) ? sessionsData.sessions : [];
      if (sessions.length > 0) {
        await hardRestoreSession(sessions[0].id);
      } else {
        statusSuccess("Session deleted.");
      }

      debugLog("deleteActiveSession done", {
        deleted_session_id: deletingId,
        remaining_sessions: sessions.length,
      });
    } catch (error) {
      debugError("deleteActiveSession failed", error);
      statusError(error.message || "Failed to delete session.");
    }
  }

  async function sendMessage() {
    if (state.sending) return;
    if (!els.chatInput) return;

    const content = String(els.chatInput.value || "").trim();
    if (!content) return;

    setSending(true);
    statusPending("Sending...");

    const originalContent = content;
    els.chatInput.value = "";

    debugLog("sendMessage start", {
      active_session_id: state.activeSessionId || null,
      content_preview: trimText(originalContent, 200),
      content_length: originalContent.length,
    });

    try {
      const sessionId = await ensureActiveSession();

      renderMessage(buildOptimisticUserMessage(originalContent));
      updateEmptyState();
      scrollMessagesToBottom();

      const payload = await api("/api/chat", {
        method: "POST",
        body: {
          content: originalContent,
          session_id: sessionId,
          attachments: [],
        },
      });

      const normalized = normalizeChatResponse(payload);

      debugLog("sendMessage normalized response", {
        ok: normalized.ok,
        session_id: normalized.session && normalized.session.id ? normalized.session.id : null,
        message_count:
          normalized.session && Array.isArray(normalized.session.messages)
            ? normalized.session.messages.length
            : normalized.messages.length,
        has_assistant_message: Boolean(normalized.assistant_message),
        debug: normalized.debug || {},
      });

      if (normalized.session && normalized.session.id) {
        setActiveSessionId(normalized.session.id);
      }

      if (normalized.session && Array.isArray(normalized.session.messages)) {
        renderMessages(normalized.session.messages);
      } else if (normalized.assistant_message) {
        renderMessages([
          buildOptimisticUserMessage(originalContent),
          normalized.assistant_message,
        ]);
      } else {
        throw new Error("Chat response missing assistant_message and session.messages.");
      }

      await reloadSessionsAndHighlight();

      document.dispatchEvent(
        new CustomEvent("nova:chat-response", {
          detail: normalized.raw,
        })
      );

      if (
        window.NovaArtifacts &&
        typeof window.NovaArtifacts.reload === "function"
      ) {
        debugLog("triggering NovaArtifacts.reload()");
        window.NovaArtifacts.reload();
      }

      const debug = normalized.debug || {};
      if (debug.fallback) {
        statusSuccess(
          debug.fallback_reason
            ? `Fallback: ${debug.fallback_reason}`
            : "Fallback response loaded."
        );
      } else {
        statusSuccess("Reply received.");
      }

      debugLog("sendMessage done", {
        active_session_id: state.activeSessionId || null,
      });
    } catch (error) {
      debugError("sendMessage failed", {
        error_name: error && error.name ? error.name : "Error",
        error_message: error && error.message ? error.message : String(error),
        status: error && typeof error.status !== "undefined" ? error.status : null,
        request_id: error && typeof error.requestId !== "undefined" ? error.requestId : null,
        path: error && error.path ? error.path : null,
        url: error && error.url ? error.url : null,
        data: error && error.data ? error.data : null,
        rawText: error && error.rawText ? trimText(error.rawText, 1000) : null,
      });

      els.chatInput.value = originalContent;
      statusError(error.message || "Send failed.");
    } finally {
      setSending(false);
    }
  }

  function bindComposer() {
    if (els.sendBtn) {
      els.sendBtn.addEventListener("click", sendMessage);
    }

    if (els.chatInput) {
      els.chatInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendMessage();
        }
      });
    }

    debugLog("composer bound");
  }

  function bindSessionButtons() {
    if (els.sessionNewBtn) {
      els.sessionNewBtn.addEventListener("click", createNewSession);
    }
    if (els.sessionRenameBtn) {
      els.sessionRenameBtn.addEventListener("click", renameActiveSession);
    }
    if (els.sessionPinBtn) {
      els.sessionPinBtn.addEventListener("click", togglePinActiveSession);
    }
    if (els.sessionDeleteBtn) {
      els.sessionDeleteBtn.addEventListener("click", deleteActiveSession);
    }

    debugLog("session buttons bound");
  }

  async function boot() {
    ensureElements();
    ensureDebugPanel();
    bindComposer();
    bindSessionButtons();
    setSending(false);

    debugLog("boot start", {
      href: window.location.href,
      origin: window.location.origin,
      frontend_lock: window.NovaFrontendLock || null,
    });

    try {
      const sessionsData = await api("/api/sessions");
      const sessions = Array.isArray(sessionsData.sessions) ? sessionsData.sessions : [];
      renderSessionList(sessions);

      const storedId = getStoredSessionId();
      const selected =
        (storedId && sessions.find((s) => String(s.id) === storedId)) ||
        sessions[0] ||
        null;

      debugLog("boot session selection", {
        stored_id: storedId || null,
        selected_id: selected && selected.id ? selected.id : null,
        sessions_count: sessions.length,
      });

      if (selected && selected.id) {
        await hardRestoreSession(selected.id);
      } else {
        updateEmptyState();
      }
    } catch (error) {
      debugError("boot failed", error);
      statusError(error.message || "Boot failed.");
      updateEmptyState();
    }
  }

  const NovaComposerBundle = {
    init: boot,
    sendMessage,
    createNewSession,
    hardRestoreSession,
    reloadSessions: reloadSessionsAndHighlight,
    openDebugPanel,
    closeDebugPanel,
    toggleDebugPanel,
    renderDebugPanel,
    getActiveSessionId() {
      return state.activeSessionId;
    },
    getLastResponse() {
      return state.lastResponse;
    },
    getLastRequest() {
      return state.lastRequest;
    },
    debugState() {
      return {
        sending: state.sending,
        activeSessionId: state.activeSessionId,
        lastResponse: state.lastResponse,
        lastRequest: state.lastRequest,
        requestSeq: state.requestSeq,
        debugPanelOpen: state.debugPanelOpen,
        frontendLock: window.NovaFrontendLock || null,
        href: window.location.href,
        origin: window.location.origin,
      };
    },
  };

  window.NovaComposerBundle = NovaComposerBundle;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();