// notepad C:\Users\Owner\nova\static\js\nova-render.js
(function () {
  "use strict";

  const Nova = (window.Nova = window.Nova || {});
  Nova.render = Nova.render || {};
  Nova.state = Nova.state || {};
  Nova.utils = Nova.utils || {};

  const state = Object.assign(
    {
      sessions: [],
      messages: [],
      artifacts: [],
      activeSessionId: null,
      pendingAssistantMessageId: null,
      isStreaming: false,
      composerLocked: false,
      artifactsLoaded: false,
      artifactDetail: null,
      webDebug: {
        enabled: true,
        lastMeta: null,
        lastWeb: null,
        history: [],
      },
    },
    Nova.state || {}
  );

  Nova.state = state;

  function qs(id) {
    return document.getElementById(id);
  }

  function qsa(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function safeString(value) {
    return value == null ? "" : String(value);
  }

  function escapeHtml(value) {
    return safeString(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function nl2br(value) {
    return escapeHtml(value).replace(/\n/g, "<br>");
  }

  function formatDateTime(value) {
    if (!value) return "";
    try {
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return safeString(value);
      return d.toLocaleString([], {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_) {
      return safeString(value);
    }
  }

  function formatTime(value) {
    if (!value) return "";
    try {
      const d = new Date(value);
      if (Number.isNaN(d.getTime())) return "";
      return d.toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_) {
      return "";
    }
  }

  function initialsFromRole(role) {
    const map = {
      user: "U",
      assistant: "N",
      system: "S",
      tool: "T",
    };
    return map[safeString(role).toLowerCase()] || "•";
  }

  function isUser(role) {
    return safeString(role).toLowerCase() === "user";
  }

  function isAssistant(role) {
    return safeString(role).toLowerCase() === "assistant";
  }

  function makeEvent(name, detail) {
    return new CustomEvent(name, {
      bubbles: true,
      cancelable: true,
      detail: detail || {},
    });
  }

  function emit(name, detail) {
    document.dispatchEvent(makeEvent(name, detail));
  }

  function normalizeMessage(message, index) {
    const item = message && typeof message === "object" ? message : {};
    return {
      id: safeString(item.id || `msg_${index}_${Date.now()}`),
      role: safeString(item.role || "assistant").toLowerCase(),
      content: safeString(item.content || ""),
      created_at: item.created_at || item.timestamp || "",
      attachments: safeArray(item.attachments),
      images: safeArray(item.images),
      videos: safeArray(item.videos),
      audios: safeArray(item.audios),
      media: safeArray(item.media),
      meta: item.meta && typeof item.meta === "object" ? item.meta : {},
      error: !!item.error,
    };
  }

  function normalizeSession(session, index) {
    const item = session && typeof session === "object" ? session : {};
    return {
      id: safeString(item.id || `session_${index}`),
      title: safeString(item.title || "Untitled Chat"),
      updated_at: item.updated_at || item.created_at || "",
      created_at: item.created_at || "",
      pinned: !!item.pinned,
      messages: safeArray(item.messages),
    };
  }

  function normalizeArtifact(artifact, index) {
    const item = artifact && typeof artifact === "object" ? artifact : {};
    return {
      id: safeString(item.id || `artifact_${index}`),
      title: safeString(item.title || "Untitled Artifact"),
      type: safeString(item.type || "artifact"),
      content: safeString(item.content || ""),
      updated_at: item.updated_at || item.created_at || "",
      created_at: item.created_at || "",
      pinned: !!item.pinned,
      session_id: item.session_id || "",
      attachments: safeArray(item.attachments),
      images: safeArray(item.images),
      videos: safeArray(item.videos),
      audios: safeArray(item.audios),
      media: safeArray(item.media),
      meta: item.meta && typeof item.meta === "object" ? item.meta : {},
    };
  }

  function renderMarkdownLite(text) {
    let html = escapeHtml(text);

    html = html.replace(/```([\s\S]*?)```/g, function (_, code) {
      return `<pre class="nova-code-block"><code>${escapeHtml(code)}</code></pre>`;
    });

    html = html.replace(/`([^`]+)`/g, '<code class="nova-inline-code">$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, function (_, label, url) {
      return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
    });

    return html.replace(/\n/g, "<br>");
  }

  function renderAttachmentChip(att) {
    const item = att && typeof att === "object" ? att : {};
    const name = safeString(item.name || item.filename || item.title || item.url || "attachment");
    const url = safeString(item.url || item.source_url || "");
    const type = safeString(item.type || item.mime_type || "file");

    if (url) {
      return `
        <a class="nova-attachment-chip" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">
          <span class="nova-attachment-chip-type">${escapeHtml(type)}</span>
          <span class="nova-attachment-chip-name">${escapeHtml(name)}</span>
        </a>
      `;
    }

    return `
      <div class="nova-attachment-chip">
        <span class="nova-attachment-chip-type">${escapeHtml(type)}</span>
        <span class="nova-attachment-chip-name">${escapeHtml(name)}</span>
      </div>
    `;
  }

  function renderImage(item) {
    const image = item && typeof item === "object" ? item : {};
    const url = safeString(image.url || image.preview_url || image.source_url || "");
    const alt = safeString(image.alt || image.title || "image");
    if (!url) return "";
    return `
      <a class="nova-media-card nova-media-image" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">
        <img src="${escapeHtml(url)}" alt="${escapeHtml(alt)}" loading="lazy" />
      </a>
    `;
  }

  function renderVideo(item) {
    const video = item && typeof item === "object" ? item : {};
    const url = safeString(video.url || video.preview_url || video.source_url || "");
    const poster = safeString(video.poster || video.thumbnail_url || "");
    if (!url) return "";
    return `
      <div class="nova-media-card nova-media-video">
        <video controls preload="metadata" ${poster ? `poster="${escapeHtml(poster)}"` : ""}>
          <source src="${escapeHtml(url)}" />
        </video>
      </div>
    `;
  }

  function renderAudio(item) {
    const audio = item && typeof item === "object" ? item : {};
    const url = safeString(audio.url || audio.preview_url || audio.source_url || "");
    if (!url) return "";
    return `
      <div class="nova-media-card nova-media-audio">
        <audio controls preload="none">
          <source src="${escapeHtml(url)}" />
        </audio>
      </div>
    `;
  }

  function renderMediaBlock(message) {
    const images = safeArray(message.images);
    const videos = safeArray(message.videos);
    const audios = safeArray(message.audios);
    const attachments = safeArray(message.attachments);

    const imageHtml = images.map(renderImage).join("");
    const videoHtml = videos.map(renderVideo).join("");
    const audioHtml = audios.map(renderAudio).join("");
    const attachmentHtml = attachments.map(renderAttachmentChip).join("");

    if (!imageHtml && !videoHtml && !audioHtml && !attachmentHtml) return "";

    return `
      <div class="nova-message-media">
        ${imageHtml ? `<div class="nova-media-grid">${imageHtml}</div>` : ""}
        ${videoHtml ? `<div class="nova-media-stack">${videoHtml}</div>` : ""}
        ${audioHtml ? `<div class="nova-media-stack">${audioHtml}</div>` : ""}
        ${attachmentHtml ? `<div class="nova-attachment-row">${attachmentHtml}</div>` : ""}
      </div>
    `;
  }

  function renderMessageActions(message) {
    const role = safeString(message.role);
    const msgId = safeString(message.id);

    return `
      <div class="nova-message-actions">
        ${isAssistant(role) ? `<button type="button" class="nova-action-btn" data-action="copy-message" data-message-id="${escapeHtml(msgId)}">Copy</button>` : ""}
        ${isAssistant(role) ? `<button type="button" class="nova-action-btn" data-action="save-artifact" data-message-id="${escapeHtml(msgId)}">Save</button>` : ""}
        <button type="button" class="nova-action-btn" data-action="retry-message" data-message-id="${escapeHtml(msgId)}">Retry</button>
      </div>
    `;
  }

  function renderSingleMessage(message, index) {
    const m = normalizeMessage(message, index);
    const contentHtml = m.content
      ? renderMarkdownLite(m.content)
      : `<span class="nova-message-empty">${isAssistant(m.role) && state.isStreaming && state.pendingAssistantMessageId === m.id ? "Thinking..." : "(empty)"}</span>`;

    return `
      <article class="nova-message nova-message-${escapeHtml(m.role)} ${m.error ? "is-error" : ""}" data-message-id="${escapeHtml(m.id)}" data-role="${escapeHtml(m.role)}">
        <div class="nova-message-avatar">${escapeHtml(initialsFromRole(m.role))}</div>
        <div class="nova-message-main">
          <div class="nova-message-topline">
            <div class="nova-message-role">${escapeHtml(m.role)}</div>
            <div class="nova-message-time">${escapeHtml(formatTime(m.created_at))}</div>
          </div>
          <div class="nova-message-bubble">
            <div class="nova-message-content">${contentHtml}</div>
            ${renderMediaBlock(m)}
          </div>
          ${renderMessageActions(m)}
        </div>
      </article>
    `;
  }

  function renderMessages() {
    const host =
      qs("novaMessages") ||
      qs("chatMessages") ||
      qs("messages") ||
      document.querySelector("[data-nova-messages]");

    if (!host) return;

    const messages = safeArray(state.messages).map(normalizeMessage);

    if (!messages.length) {
      host.innerHTML = `
        <div class="nova-empty-state">
          <div class="nova-empty-title">Nova is ready</div>
          <div class="nova-empty-copy">Start a new message to test chat, streaming, buttons, artifacts, and memory.</div>
        </div>
      `;
      return;
    }

    host.innerHTML = messages.map(renderSingleMessage).join("");
    scrollMessagesToBottom(host);
  }

  function scrollMessagesToBottom(host) {
    try {
      const shouldStick =
        Math.abs((host.scrollHeight - host.clientHeight) - host.scrollTop) < 140 ||
        state.isStreaming;

      if (shouldStick) {
        host.scrollTop = host.scrollHeight;
      }
    } catch (_) {}
  }

  function renderSessionItem(session, index) {
    const s = normalizeSession(session, index);
    const isActive = s.id === state.activeSessionId;

    return `
      <button
        type="button"
        class="nova-session-item ${isActive ? "is-active" : ""}"
        data-action="open-session"
        data-session-id="${escapeHtml(s.id)}"
        aria-pressed="${isActive ? "true" : "false"}"
      >
        <div class="nova-session-main">
          <div class="nova-session-title">${escapeHtml(s.title)}</div>
          <div class="nova-session-meta">
            <span>${escapeHtml(formatDateTime(s.updated_at || s.created_at))}</span>
            ${s.pinned ? `<span class="nova-session-pin">Pinned</span>` : ""}
          </div>
        </div>
        <div class="nova-session-actions">
          <span class="nova-inline-action" data-action="toggle-session-pin" data-session-id="${escapeHtml(s.id)}" title="Pin">📌</span>
          <span class="nova-inline-action" data-action="rename-session" data-session-id="${escapeHtml(s.id)}" title="Rename">✏️</span>
          <span class="nova-inline-action" data-action="delete-session" data-session-id="${escapeHtml(s.id)}" title="Delete">🗑️</span>
        </div>
      </button>
    `;
  }

  function renderSessions() {
    const host =
      qs("novaSessionList") ||
      qs("sessionList") ||
      qs("sessionsList") ||
      document.querySelector("[data-nova-sessions]");

    if (!host) return;

    const sessions = safeArray(state.sessions).map(normalizeSession);

    if (!sessions.length) {
      host.innerHTML = `
        <div class="nova-empty-mini">
          <div class="nova-empty-mini-title">No chats yet</div>
          <div class="nova-empty-mini-copy">Create a new session to begin.</div>
        </div>
      `;
      return;
    }

    host.innerHTML = sessions.map(renderSessionItem).join("");
  }

  function renderArtifactItem(artifact, index) {
    const a = normalizeArtifact(artifact, index);
    const preview = a.content ? a.content.slice(0, 140) : `${a.type} artifact`;

    return `
      <article
        class="nova-artifact-card ${state.artifactDetail && state.artifactDetail.id === a.id ? "is-active" : ""}"
        data-action="open-artifact"
        data-artifact-id="${escapeHtml(a.id)}"
        tabindex="0"
        role="button"
      >
        <div class="nova-artifact-card-main">
          <div class="nova-artifact-card-top">
            <div class="nova-artifact-card-title">${escapeHtml(a.title)}</div>
            ${a.pinned ? `<div class="nova-artifact-card-pin">📌</div>` : ""}
          </div>
          <div class="nova-artifact-card-type">${escapeHtml(a.type)}</div>
          <div class="nova-artifact-card-preview">${escapeHtml(preview)}</div>
          <div class="nova-artifact-card-time">${escapeHtml(formatDateTime(a.updated_at || a.created_at))}</div>
        </div>
        <div class="nova-artifact-card-actions">
          <button type="button" class="nova-action-btn" data-action="toggle-artifact-pin" data-artifact-id="${escapeHtml(a.id)}">Pin</button>
          <button type="button" class="nova-action-btn" data-action="delete-artifact" data-artifact-id="${escapeHtml(a.id)}">Delete</button>
        </div>
      </article>
    `;
  }

  function renderArtifacts() {
    const host =
      qs("novaArtifactsList") ||
      qs("artifactRail") ||
      qs("artifactsList") ||
      document.querySelector("[data-nova-artifacts]");

    if (!host) return;

    const items = safeArray(state.artifacts).map(normalizeArtifact);

    if (!items.length) {
      host.innerHTML = `
        <div class="nova-empty-mini">
          <div class="nova-empty-mini-title">No artifacts yet</div>
          <div class="nova-empty-mini-copy">Saved chats, media, and exports will show up here.</div>
        </div>
      `;
      return;
    }

    host.innerHTML = items.map(renderArtifactItem).join("");
  }

  function renderArtifactDetail() {
    const host =
      qs("novaArtifactDetail") ||
      qs("artifactDetail") ||
      document.querySelector("[data-nova-artifact-detail]");

    if (!host) return;

    const a = state.artifactDetail ? normalizeArtifact(state.artifactDetail) : null;

    if (!a) {
      host.innerHTML = `
        <div class="nova-empty-mini">
          <div class="nova-empty-mini-title">No artifact selected</div>
          <div class="nova-empty-mini-copy">Click an artifact card to inspect it here.</div>
        </div>
      `;
      return;
    }

    host.innerHTML = `
      <div class="nova-artifact-detail-wrap">
        <div class="nova-artifact-detail-top">
          <div>
            <div class="nova-artifact-detail-title">${escapeHtml(a.title)}</div>
            <div class="nova-artifact-detail-meta">
              <span>${escapeHtml(a.type)}</span>
              <span>${escapeHtml(formatDateTime(a.updated_at || a.created_at))}</span>
            </div>
          </div>
          <div class="nova-artifact-detail-actions">
            <button type="button" class="nova-action-btn" data-action="toggle-artifact-pin" data-artifact-id="${escapeHtml(a.id)}">Pin</button>
            <button type="button" class="nova-action-btn" data-action="export-artifact" data-artifact-id="${escapeHtml(a.id)}">Export</button>
          </div>
        </div>
        <div class="nova-artifact-detail-content">${nl2br(a.content || "")}</div>
      </div>
    `;
  }

  function renderWebDebug() {
    const emptyEl = qs("novaWebDebugEmpty");
    const host =
      qs("novaWebDebugBody") ||
      qs("novaWebDebugContent") ||
      document.querySelector("[data-nova-web-debug]");

    if (!host) return;

    const web = state.webDebug && typeof state.webDebug === "object" ? state.webDebug : {};
    const lastMeta = web.lastMeta && typeof web.lastMeta === "object" ? web.lastMeta : null;
    const lastWeb = web.lastWeb && typeof web.lastWeb === "object" ? web.lastWeb : null;
    const history = safeArray(web.history);

    const hasAny = !!lastMeta || !!lastWeb || history.length > 0;

    if (emptyEl) {
      emptyEl.style.display = hasAny ? "none" : "";
    }

    if (!hasAny) {
      host.innerHTML = "";
      return;
    }

    host.innerHTML = `
      ${lastMeta ? `<pre class="nova-debug-block">${escapeHtml(JSON.stringify(lastMeta, null, 2))}</pre>` : ""}
      ${lastWeb ? `<pre class="nova-debug-block">${escapeHtml(JSON.stringify(lastWeb, null, 2))}</pre>` : ""}
      ${
        history.length
          ? `<pre class="nova-debug-block">${escapeHtml(JSON.stringify(history.slice(-10), null, 2))}</pre>`
          : ""
      }
    `;
  }

  function updateTopButtons() {
    const sendBtn = qs("sendBtn") || qs("novaSendBtn") || document.querySelector('[data-action="send-message"]');
    const stopBtn = qs("stopBtn") || qs("novaStopBtn") || document.querySelector('[data-action="stop-stream"]');
    const composer = qs("composerInput") || qs("novaComposer") || qs("messageInput") || document.querySelector("textarea");

    if (composer) {
      composer.disabled = !!state.composerLocked;
    }

    if (sendBtn) {
      sendBtn.disabled = !!state.composerLocked || !!state.isStreaming;
    }

    if (stopBtn) {
      stopBtn.disabled = !state.isStreaming;
      stopBtn.hidden = !state.isStreaming;
    }
  }

  function autoGrowComposer() {
    const composer = qs("composerInput") || qs("novaComposer") || qs("messageInput") || document.querySelector("textarea");
    if (!composer) return;
    composer.style.height = "auto";
    composer.style.height = Math.min(composer.scrollHeight, 220) + "px";
  }

  function getMessageById(messageId) {
    const messages = safeArray(state.messages);
    for (let i = 0; i < messages.length; i += 1) {
      const m = normalizeMessage(messages[i], i);
      if (m.id === messageId) return m;
    }
    return null;
  }

  function handleDelegatedClick(event) {
    const actionEl = event.target.closest("[data-action]");
    if (!actionEl) return;

    const action = safeString(actionEl.getAttribute("data-action"));
    if (!action) return;

    const sessionId = safeString(actionEl.getAttribute("data-session-id"));
    const artifactId = safeString(actionEl.getAttribute("data-artifact-id"));
    const messageId = safeString(actionEl.getAttribute("data-message-id"));

    if (actionEl.classList.contains("nova-inline-action") || actionEl.classList.contains("nova-action-btn")) {
      event.preventDefault();
      event.stopPropagation();
    }

    switch (action) {
      case "open-session":
        emit("nova:session:open", { sessionId });
        break;

      case "rename-session":
        emit("nova:session:rename", { sessionId });
        break;

      case "delete-session":
        emit("nova:session:delete", { sessionId });
        break;

      case "toggle-session-pin":
        emit("nova:session:toggle-pin", { sessionId });
        break;

      case "open-artifact":
        emit("nova:artifact:open", { artifactId });
        break;

      case "toggle-artifact-pin":
        emit("nova:artifact:toggle-pin", { artifactId });
        break;

      case "delete-artifact":
        emit("nova:artifact:delete", { artifactId });
        break;

      case "export-artifact":
        emit("nova:artifact:export", { artifactId });
        break;

      case "copy-message": {
        const message = getMessageById(messageId);
        const text = safeString(message && message.content);
        if (!text) return;
        navigator.clipboard.writeText(text).then(
          function () {
            emit("nova:toast", { kind: "ok", text: "Copied" });
          },
          function () {
            emit("nova:toast", { kind: "error", text: "Copy failed" });
          }
        );
        break;
      }

      case "save-artifact": {
        const message = getMessageById(messageId);
        emit("nova:message:save-artifact", { messageId, message });
        break;
      }

      case "retry-message":
        emit("nova:message:retry", { messageId });
        break;

      case "send-message":
        emit("nova:chat:send", {});
        break;

      case "stop-stream":
        emit("nova:chat:stop", {});
        break;

      default:
        break;
    }
  }

  function handleKeydown(event) {
    const artifactCard = event.target.closest('.nova-artifact-card[data-action="open-artifact"]');
    if (artifactCard && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      emit("nova:artifact:open", {
        artifactId: safeString(artifactCard.getAttribute("data-artifact-id")),
      });
    }
  }

  function handleComposerKeydown(event) {
    const composer = event.target;
    if (!composer || composer.tagName !== "TEXTAREA") return;

    autoGrowComposer();

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!state.composerLocked && !state.isStreaming) {
        emit("nova:chat:send", {});
      }
    }
  }

  function bindGlobalUi() {
    document.addEventListener("click", handleDelegatedClick);
    document.addEventListener("keydown", handleKeydown);

    const composer = qs("composerInput") || qs("novaComposer") || qs("messageInput") || document.querySelector("textarea");
    if (composer) {
      composer.addEventListener("input", autoGrowComposer);
      composer.addEventListener("keydown", handleComposerKeydown);
      autoGrowComposer();
    }
  }

  function renderAll() {
    renderSessions();
    renderMessages();
    renderArtifacts();
    renderArtifactDetail();
    renderWebDebug();
    updateTopButtons();
  }

  function syncState(partial) {
    if (!partial || typeof partial !== "object") return;
    Object.assign(state, partial);
    Nova.state = state;
    renderAll();
  }

  function replaceMessages(messages) {
    state.messages = safeArray(messages);
    renderMessages();
    updateTopButtons();
  }

  function replaceSessions(sessions) {
    state.sessions = safeArray(sessions);
    renderSessions();
  }

  function replaceArtifacts(artifacts) {
    state.artifacts = safeArray(artifacts);
    renderArtifacts();
  }

  function setArtifactDetail(artifact) {
    state.artifactDetail = artifact || null;
    renderArtifactDetail();
    renderArtifacts();
  }

  function setStreaming(isStreaming, pendingAssistantMessageId) {
    state.isStreaming = !!isStreaming;
    state.pendingAssistantMessageId = pendingAssistantMessageId || null;
    updateTopButtons();
    renderMessages();
  }

  Nova.render.renderAll = renderAll;
  Nova.render.renderMessages = renderMessages;
  Nova.render.renderSessions = renderSessions;
  Nova.render.renderArtifacts = renderArtifacts;
  Nova.render.renderArtifactDetail = renderArtifactDetail;
  Nova.render.renderWebDebug = renderWebDebug;
  Nova.render.syncState = syncState;
  Nova.render.replaceMessages = replaceMessages;
  Nova.render.replaceSessions = replaceSessions;
  Nova.render.replaceArtifacts = replaceArtifacts;
  Nova.render.setArtifactDetail = setArtifactDetail;
  Nova.render.setStreaming = setStreaming;
  Nova.render.autoGrowComposer = autoGrowComposer;

  document.addEventListener("DOMContentLoaded", function () {
    bindGlobalUi();
    renderAll();
  });

  document.addEventListener("nova:state:update", function (event) {
    syncState((event && event.detail) || {});
  });

  document.addEventListener("nova:messages:update", function (event) {
    replaceMessages(event && event.detail && event.detail.messages);
  });

  document.addEventListener("nova:sessions:update", function (event) {
    replaceSessions(event && event.detail && event.detail.sessions);
  });

  document.addEventListener("nova:artifacts:update", function (event) {
    replaceArtifacts(event && event.detail && event.detail.artifacts);
  });

  document.addEventListener("nova:artifact:detail", function (event) {
    setArtifactDetail(event && event.detail && event.detail.artifact);
  });

  document.addEventListener("nova:streaming:update", function (event) {
    const detail = (event && event.detail) || {};
    setStreaming(!!detail.isStreaming, detail.pendingAssistantMessageId || null);
  });
})();