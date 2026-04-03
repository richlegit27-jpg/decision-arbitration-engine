(function () {
  "use strict";

  const LOG = "[NovaComposerBundle]";
  const API = {
    state: "/api/state",
    chat: "/api/chat",
    upload: "/api/upload"
  };

  const state = {
    sessionId: "",
    sessions: [],
    sending: false,
    pendingArtifactOpenId: ""
  };

  function log() {
    try { console.log(LOG, ...arguments); } catch (_) {}
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
      window.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
    } catch (_) {}
  }

  function setLastDebug(requestValue, responseValue) {
    window.__novaLastRequest = requestValue || {};
    window.__novaLastResponse = responseValue || {};
    dispatch("nova:debug-update", {});
  }

  function getMessagesEl() { return qs("#messages"); }
  function getInputEl() { return qs("#chatInput"); }
  function getSendBtn() { return qs("#sendBtn"); }
  function getUploadBtn() { return qs("#uploadBtn"); }
  function getFileInput() { return qs("#fileInput"); }
  function getSessionListEl() { return qs("#sessionList"); }

  function setConnectionStatus(text) {
    const el = qs("#connectionStatus");
    if (el) el.textContent = safe(text);
  }

  function currentStaged() {
    return window.NovaUploadStage && typeof window.NovaUploadStage.get === "function"
      ? window.NovaUploadStage.get()
      : [];
  }

  function clearStaged() {
    if (window.NovaUploadStage && typeof window.NovaUploadStage.clear === "function") {
      window.NovaUploadStage.clear();
    }
  }

  function normalizeAttachment(item) {
    if (!item || typeof item !== "object") return null;
    return {
      id: item.id || "",
      filename: item.filename || item.name || "attachment",
      stored_filename: item.stored_filename || "",
      url: item.url || "",
      mime_type: item.mime_type || item.mime || "",
      size: item.size || 0,
      type: item.type || ""
    };
  }

  function formatTime(value) {
    if (!value) return "";
    try {
      return new Date(value).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    } catch (_) {
      return "";
    }
  }

  function markdownToHtml(text) {
    let html = esc(text || "");

    html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, function (_, alt, src) {
      return (
        '<div class="nova-inline-image-wrap">' +
          '<img class="nova-inline-image" src="' + esc(src) + '" alt="' + esc(alt || "image") + '" loading="lazy">' +
        "</div>"
      );
    });

    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\n/g, "<br>");
    return html;
  }

  function renderAttachments(attachments) {
    const list = Array.isArray(attachments) ? attachments.filter(Boolean) : [];
    if (!list.length) return "";

    return (
      '<div class="nova-message-attachments">' +
      list.map(function (item) {
        const type = safe(item.type || "").toLowerCase();
        const url = safe(item.url);
        const name = safe(item.filename || item.name || "attachment");

        if (type === "image" && url) {
          return (
            '<div class="nova-message-attachment">' +
              '<img class="nova-message-image" src="' + esc(url) + '" alt="' + esc(name) + '" loading="lazy">' +
              '<div class="nova-message-attachment-meta">' + esc(name) + "</div>" +
            "</div>"
          );
        }

        if (url) {
          return (
            '<div class="nova-message-attachment">' +
              '<a href="' + esc(url) + '" target="_blank" rel="noreferrer">' + esc(name) + "</a>" +
            "</div>"
          );
        }

        return '<div class="nova-message-attachment">' + esc(name) + "</div>";
      }).join("") +
      "</div>"
    );
  }

  function renderMessage(message) {
    const role = safe(message && message.role) || "assistant";
    const content = safe(message && message.content);
    const attachments = Array.isArray(message && message.attachments) ? message.attachments : [];
    const createdAt = safe(message && message.created_at);

    return (
      '<article class="nova-message nova-message-' + esc(role) + '">' +
        '<div class="nova-message-inner">' +
          '<div class="nova-message-top">' +
            '<div class="nova-message-role">' + esc(role === "user" ? "You" : "Nova") + "</div>" +
            '<div class="nova-message-time">' + esc(formatTime(createdAt)) + "</div>" +
          "</div>" +
          '<div class="nova-message-markdown">' + markdownToHtml(content) + "</div>" +
          renderAttachments(attachments) +
        "</div>" +
      "</article>"
    );
  }

  function appendMessage(message) {
    const el = getMessagesEl();
    if (!el) return;
    el.insertAdjacentHTML("beforeend", renderMessage(message));
    el.scrollTop = el.scrollHeight;
    const empty = qs("#novaEmptyState");
    if (empty) empty.style.display = "none";
  }

  function setMessages(messages) {
    const el = getMessagesEl();
    if (!el) return;
    const list = Array.isArray(messages) ? messages : [];
    el.innerHTML = list.map(renderMessage).join("");
    const empty = qs("#novaEmptyState");
    if (empty) empty.style.display = list.length ? "none" : "";
    el.scrollTop = el.scrollHeight;
  }

  function setActiveSessionTitle(title) {
    const el = qs("#activeSessionTitle");
    if (el) el.textContent = safe(title || "New Chat");
  }

  function sessionPreview(session) {
    return safe(session.last_message_preview || session.title || "New Chat");
  }

  function activateSessionById(sessionId, options) {
    const detail = options || {};
    const id = safe(sessionId || "");
    if (!id) return false;

    const session = state.sessions.find(function (item) {
      return item.id === id;
    });
    if (!session) return false;

    state.sessionId = session.id;
    persistSessionId();
    setActiveSessionTitle(session.title || "New Chat");
    setMessages(Array.isArray(session.messages) ? session.messages : []);
    renderSessions();

    dispatch("nova:session-activated", {
      session_id: session.id,
      reason: safe(detail.reason || "activate-session")
    });

    return true;
  }

  function renderSessions() {
    const el = getSessionListEl();
    if (!el) return;
    el.innerHTML = state.sessions.map(function (session) {
      const active = session.id === state.sessionId;
      return (
        '<button class="nova-session-item' + (active ? " is-active" : "") + '" type="button" data-session-id="' + esc(session.id) + '">' +
          '<div class="nova-session-item-title">' + esc(session.title || "New Chat") + "</div>" +
          '<div class="nova-session-item-copy">' + esc(sessionPreview(session)) + "</div>" +
        "</button>"
      );
    }).join("");

    qsa("[data-session-id]", el).forEach(function (btn) {
      btn.addEventListener("click", function () {
        const id = btn.getAttribute("data-session-id") || "";
        activateSessionById(id, { reason: "session-list-click" });
      });
    });
  }

  function persistSessionId() {
    try { localStorage.setItem("nova.activeSessionId", state.sessionId || ""); } catch (_) {}
  }

  function restoreSessionId() {
    try { return localStorage.getItem("nova.activeSessionId") || ""; } catch (_) { return ""; }
  }

  function setSending(isSending) {
    state.sending = !!isSending;
    const sendBtn = getSendBtn();
    if (sendBtn) {
      sendBtn.disabled = state.sending;
      sendBtn.textContent = state.sending ? "Sending..." : "Send";
    }
  }

  async function refreshState() {
    const res = await fetch(API.state, { credentials: "same-origin" });
    const data = await res.json();

    const sessions = Array.isArray(data.sessions) ? data.sessions : [];
    state.sessions = sessions;

    const restored = restoreSessionId();
    const matched = sessions.find(function (s) { return s.id === restored; });
    const first = sessions[0];

    if (matched) {
      activateSessionById(matched.id);
    } else if (first) {
      activateSessionById(first.id);
    } else {
      state.sessionId = "";
      setActiveSessionTitle("New Chat");
      setMessages([]);
    }

    renderSessions();
  }

  async function sendMessage() {
    if (state.sending) return;

    const input = getInputEl();
    const text = safe(input && input.value).trim();
    const attachments = currentStaged();

    if (!text && !attachments.length) return;

    if (input) input.value = "";
    setSending(true);

    appendMessage({
      role: "user",
      content: text,
      attachments: attachments,
      created_at: new Date().toISOString()
    });

    try {
      const res = await fetch(API.chat, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: text,
          session_id: state.sessionId || "",
          attachments: attachments
        })
      });

      const data = await res.json();

      if (data.session && data.session.id) {
        state.sessionId = data.session.id;
        persistSessionId();
      }

      if (data.session) {
        const i = state.sessions.findIndex(s => s.id === data.session.id);
        if (i >= 0) state.sessions[i] = data.session;
        else state.sessions.unshift(data.session);
        renderSessions();
        setActiveSessionTitle(data.session.title || "New Chat");
      }

      if (data.assistant_message) appendMessage(data.assistant_message);

      clearStaged();

      dispatch("nova:artifacts-refreshed", {
        artifacts: data.artifacts || [],
        active_session_id: state.sessionId
      });

    } catch (e) {
      appendMessage({
        role: "assistant",
        content: "Nova error: " + safe(e.message),
        created_at: new Date().toISOString()
      });
    } finally {
      setSending(false);
    }
  }

  function setupComposer() {
    qs("#sendBtn")?.addEventListener("click", sendMessage);

    qs("#chatInput")?.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    window.addEventListener("nova:session-switch-request", function (event) {
      const d = event.detail || {};
      state.pendingArtifactOpenId = d.artifact_id || "";
      activateSessionById(d.session_id, { reason: "artifact-switch" });
    });

    window.addEventListener("nova:session-activated", function (event) {
      if (state.pendingArtifactOpenId) {
        const id = state.pendingArtifactOpenId;
        state.pendingArtifactOpenId = "";
        dispatch("nova:artifact-open-request", {
          artifact_id: id,
          suppress_session_switch: true
        });
      }

      dispatch("nova:artifacts-refreshed", {
        active_session_id: state.sessionId
      });
    });
  }

  async function boot() {
    setupComposer();
    await refreshState();
    dispatch("nova:artifacts-refreshed", { active_session_id: state.sessionId });
    log("ready", { session_id: state.sessionId });
  }

  boot();
})();