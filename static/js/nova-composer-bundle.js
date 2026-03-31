(function () {
  "use strict";

  console.log("nova-composer-bundle loaded");

  const CHAT_URL = "/api/chat";
  const STATE_URL = "/api/state";
  const DEFAULT_SESSION_ID = "default-session";

  const state = {
    sessionId: DEFAULT_SESSION_ID,
    sending: false,
    restoredOnce: false,
    restoring: false,
    restoreToken: 0,
    sendToken: 0,
    messagesById: new Set(),
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

  function getMessagesEl() {
    return el("messages");
  }

  function getInputEl() {
    return el("chatInput");
  }

  function getSendBtn() {
    return el("sendBtn");
  }

  function getEmptyStateEl() {
    return el("novaEmptyState");
  }

  function getSessionStatusEl() {
    return el("sessionStatus");
  }

  function getSessionTitleEl() {
    return el("sessionTitleText");
  }

  function getSessionMetaEl() {
    return el("activeSessionMeta");
  }

  function setStatus(text, tone) {
    const node = getSessionStatusEl();
    if (!node) return;
    node.textContent = text || "Ready";
    node.dataset.tone = tone || "muted";
  }

  function getSessionId() {
    const fromWindow =
      window.NovaSessionRail &&
      typeof window.NovaSessionRail.getCurrentSessionId === "function"
        ? window.NovaSessionRail.getCurrentSessionId()
        : null;

    const fromBody = document.body?.dataset?.sessionId || null;
    const fromStorage = localStorage.getItem("nova_active_session_id") || null;

    const resolved = fromWindow || fromBody || fromStorage || DEFAULT_SESSION_ID;
    state.sessionId = resolved;
    return resolved;
  }

  function setSessionId(sessionId) {
    const resolved = String(sessionId || DEFAULT_SESSION_ID).trim() || DEFAULT_SESSION_ID;
    state.sessionId = resolved;
    document.body.dataset.sessionId = resolved;
    localStorage.setItem("nova_active_session_id", resolved);
  }

  function formatTime(value) {
    const date = value ? new Date(value) : new Date();
    if (Number.isNaN(date.getTime())) {
      return new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    }
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  function updateEmptyState() {
    const messagesEl = getMessagesEl();
    const emptyEl = getEmptyStateEl();
    if (!messagesEl || !emptyEl) return;
    emptyEl.style.display = messagesEl.children.length > 0 ? "none" : "";
  }

  function scrollToBottom() {
    const messagesEl = getMessagesEl();
    if (!messagesEl) return;
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function setSending(isSending) {
    state.sending = !!isSending;

    const input = getInputEl();
    const sendBtn = getSendBtn();

    if (input) input.disabled = !!isSending;
    if (sendBtn) sendBtn.disabled = !!isSending;

    if (isSending) {
      setStatus("Sending...", "muted");
    } else {
      setStatus("Ready", "ok");
    }
  }

  function buildBadgesHtml(debug) {
    const badges = [];
    const safeDebug = debug || {};

    if (safeDebug.used_fallback) {
      badges.push('<span class="nova-badge nova-badge-warning">Fallback</span>');
    }

    if (safeDebug.memory_used) {
      const count = Number(safeDebug.memory_selected_count || 0);
      badges.push(`<span class="nova-badge">Memory ${escapeHtml(String(count))}</span>`);
    }

    if (safeDebug.artifact_saved === true) {
      badges.push('<span class="nova-badge nova-badge-soft">Artifact Saved</span>');
    } else if (safeDebug.artifact_saved === false) {
      badges.push('<span class="nova-badge">Artifact Skipped</span>');
    }

    if (safeDebug.web_used || (safeDebug.web && safeDebug.web.used)) {
      badges.push('<span class="nova-badge">Web</span>');
    }

    return badges.join("");
  }

  function createMessageNode(role, content, options) {
    const opts = options || {};
    const node = document.createElement("div");
    node.className = `nova-message nova-message-${role}`;
    node.dataset.role = role;

    if (opts.messageId) {
      node.dataset.messageId = opts.messageId;
    }

    if (opts.pending === true) {
      node.dataset.pending = "true";
    }

    if (opts.sessionId) {
      node.dataset.sessionId = opts.sessionId;
    }

    const inner = document.createElement("div");
    inner.className = "nova-message-inner";

    inner.innerHTML = `
      <div class="nova-message-header">
        <div class="nova-message-role">${role === "user" ? "You" : "Nova"}</div>
        <div class="nova-message-time">${escapeHtml(opts.timeText || formatTime(opts.createdAt))}</div>
      </div>
      <div class="nova-message-badges">${opts.badgesHtml || ""}</div>
      <div class="nova-message-markdown">${nl2br(content || "")}</div>
    `;

    node.appendChild(inner);
    return node;
  }

  function appendMessage(role, content, options) {
    const messagesEl = getMessagesEl();
    if (!messagesEl) return null;

    const node = createMessageNode(role, content, options || {});
    messagesEl.appendChild(node);
    updateEmptyState();
    scrollToBottom();

    if (options && options.messageId) {
      state.messagesById.add(options.messageId);
    }

    return node;
  }

  function replaceMessageContent(node, content, debug, messageId) {
    if (!node) return;

    if (messageId) {
      node.dataset.messageId = messageId;
      state.messagesById.add(messageId);
    }

    delete node.dataset.pending;

    const body = qs(".nova-message-markdown", node);
    const badges = qs(".nova-message-badges", node);

    if (body) {
      body.innerHTML = nl2br(content || "");
    }

    if (badges) {
      badges.innerHTML = buildBadgesHtml(debug || {});
    }

    scrollToBottom();
  }

  function clearMessages() {
    const messagesEl = getMessagesEl();
    if (!messagesEl) return;
    messagesEl.innerHTML = "";
    state.messagesById.clear();
    updateEmptyState();
  }

  function removePendingMessages() {
    qsa('.nova-message[data-pending="true"]', getMessagesEl()).forEach((node) => node.remove());
    updateEmptyState();
  }

  function collectHistoryFromDom() {
    const messagesEl = getMessagesEl();
    if (!messagesEl) return [];

    return qsa(".nova-message", messagesEl)
      .map((node) => {
        const role = node.dataset.role || "assistant";
        const content = qs(".nova-message-markdown", node)?.innerText?.trim() || "";
        if (!content) return null;
        return { role, content };
      })
      .filter(Boolean);
  }

  function buildPayload(userContent) {
    return {
      content: String(userContent || "").trim(),
      session_id: getSessionId(),
      history: collectHistoryFromDom(),
    };
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

  function updateTopbarFromSession(session) {
    const titleEl = getSessionTitleEl();
    const metaEl = getSessionMetaEl();

    if (titleEl) {
      titleEl.textContent = session?.title || "New Chat";
    }

    if (metaEl) {
      const count = Number(session?.message_count || 0);
      const pinned = session?.pinned ? " • pinned" : "";
      metaEl.textContent = `${count} msg${count === 1 ? "" : "s"}${pinned}`;
    }
  }

  function renderMessagesFromState(session) {
    const messages = Array.isArray(session?.messages) ? session.messages : [];
    clearMessages();

    messages.forEach((message) => {
      const role = message?.role === "user" ? "user" : "assistant";
      const content = message?.content || "";
      const messageId = message?.id || null;
      const createdAt = message?.created_at || null;
      const debug = message?.debug || message?.meta || {};

      appendMessage(role, content, {
        messageId,
        createdAt,
        sessionId: state.sessionId,
        badgesHtml: role === "assistant" ? buildBadgesHtml(debug) : "",
      });
    });

    updateTopbarFromSession(session);
    updateEmptyState();
    scrollToBottom();
  }

  async function restoreSessionState(forceSessionId) {
    const requestedSessionId =
      String(forceSessionId || getSessionId() || DEFAULT_SESSION_ID).trim() || DEFAULT_SESSION_ID;

    state.restoreToken += 1;
    const token = state.restoreToken;
    state.restoring = true;

    try {
      setStatus("Loading session...", "muted");
      removePendingMessages();

      const data = await fetchJson(`${STATE_URL}?session_id=${encodeURIComponent(requestedSessionId)}`);
      if (token !== state.restoreToken) return;

      const resolvedSessionId =
        data?.active_session_id ||
        data?.session?.id ||
        requestedSessionId;

      setSessionId(resolvedSessionId);
      renderMessagesFromState(data?.session || {});
      state.restoredOnce = true;

      document.dispatchEvent(
        new CustomEvent("nova:state-restored", {
          detail: {
            session_id: resolvedSessionId,
            state: data,
          },
        })
      );

      if (window.NovaArtifacts && typeof window.NovaArtifacts.refresh === "function") {
        try {
          await window.NovaArtifacts.refresh({
            reason: "state_restored",
            session_id: resolvedSessionId,
          });
        } catch (err) {
          console.warn("NovaArtifacts.refresh failed after restore:", err);
        }
      }

      setStatus("Session loaded", "ok");
    } catch (error) {
      if (token !== state.restoreToken) return;
      console.error("restoreSessionState failed:", error);
      setStatus(`State load failed: ${error.message || error}`, "error");
    } finally {
      if (token === state.restoreToken) {
        state.restoring = false;
        updateEmptyState();
        scrollToBottom();
      }
    }
  }

  async function sendMessage(rawValue) {
    const content = String(rawValue || "").trim();
    if (!content) return;
    if (state.sending) return;
    if (state.restoring) return;

    const input = getInputEl();
    const sessionIdAtSend = getSessionId();
    const payload = {
      content,
      session_id: sessionIdAtSend,
      history: collectHistoryFromDom(),
    };

    const currentSendToken = ++state.sendToken;

    appendMessage("user", content, {
      createdAt: new Date().toISOString(),
      sessionId: sessionIdAtSend,
    });

    if (input) {
      input.value = "";
      input.style.height = "";
    }

    const pendingNode = appendMessage("assistant", "Thinking...", {
      badgesHtml: '<span class="nova-badge">Pending</span>',
      createdAt: new Date().toISOString(),
      pending: true,
      sessionId: sessionIdAtSend,
    });

    setSending(true);

    try {
      const data = await fetchJson(CHAT_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const activeSessionNow = getSessionId();
      const returnedSessionId =
        data?.active_session_id ||
        data?.session?.id ||
        sessionIdAtSend;

      if (currentSendToken !== state.sendToken) return;

      if (activeSessionNow !== sessionIdAtSend) {
        pendingNode?.remove();
        updateEmptyState();
        return;
      }

      const assistantMessage = data?.assistant_message || {};
      const assistantContent =
        assistantMessage?.content ||
        data?.message ||
        "No reply returned.";

      const debug = data?.debug || assistantMessage?.debug || {};

      setSessionId(returnedSessionId);

      replaceMessageContent(
        pendingNode,
        assistantContent,
        debug,
        assistantMessage?.id || null
      );

      updateTopbarFromSession(data?.session || {});

      document.dispatchEvent(
        new CustomEvent("nova:assistant-reply", {
          detail: {
            session_id: getSessionId(),
            assistant_message: assistantMessage,
            debug,
            raw: data,
          },
        })
      );

      if (window.NovaArtifacts && typeof window.NovaArtifacts.refresh === "function") {
        try {
          await window.NovaArtifacts.refresh({
            reason: "assistant_reply",
            session_id: getSessionId(),
            reply: data,
            debug,
          });
        } catch (err) {
          console.warn("NovaArtifacts.refresh failed after reply:", err);
        }
      }

      setStatus("Reply received", "ok");
    } catch (error) {
      console.error("sendMessage failed:", error);

      const activeSessionNow = getSessionId();
      if (activeSessionNow !== sessionIdAtSend) {
        pendingNode?.remove();
        updateEmptyState();
        return;
      }

      replaceMessageContent(
        pendingNode,
        `Request failed: ${error.message || error}`,
        { used_fallback: true },
        null
      );
      setStatus(`Send failed: ${error.message || error}`, "error");
    } finally {
      setSending(false);
      updateEmptyState();
      scrollToBottom();
    }
  }

  function autosizeTextarea() {
    const input = getInputEl();
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 220)}px`;
  }

  function bindComposer() {
    const input = getInputEl();
    const sendBtn = getSendBtn();

    if (input && !input.dataset.boundNovaComposer) {
      input.dataset.boundNovaComposer = "true";

      input.addEventListener("input", autosizeTextarea);

      input.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendMessage(input.value);
        }
      });
    }

    if (sendBtn && !sendBtn.dataset.boundNovaComposer) {
      sendBtn.dataset.boundNovaComposer = "true";
      sendBtn.addEventListener("click", function () {
        sendMessage(input ? input.value : "");
      });
    }

    document.addEventListener("nova:session-changed", function (event) {
      const nextId = String(event?.detail?.session_id || "").trim();
      if (!nextId) return;
      setSessionId(nextId);
      restoreSessionState(nextId);
    });
  }

  function init() {
    setSessionId(getSessionId());
    bindComposer();
    updateEmptyState();
    restoreSessionState(getSessionId());
  }

  window.NovaComposerBundle = {
    init,
    sendMessage,
    restoreSessionState,
    collectHistoryFromDom,
    buildPayload,
    getSessionId,
    setSessionId,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();