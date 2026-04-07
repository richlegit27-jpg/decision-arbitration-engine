(function () {
  "use strict";

  if (window.NovaComposerBundle) return;

  function log() {
    try {
      console.log("[NovaComposerBundle]", ...arguments);
    } catch (_) {}
  }

  function warn() {
    try {
      console.warn("[NovaComposerBundle]", ...arguments);
    } catch (_) {}
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

  function renderSafeText(value) {
    return escapeHtml(String(value == null ? "" : value)).replace(/\n/g, "<br>");
  }

  function normalizeText(value) {
    return String(value == null ? "" : value).replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function makeId(prefix) {
    return (prefix || "id") + "_" + Math.random().toString(16).slice(2) + Date.now().toString(16);
  }

  function summarizeText(value, limit) {
    const text = normalizeText(value).trim();
    const max = Number(limit || 100);
    if (text.length <= max) return text;
    return text.slice(0, Math.max(0, max - 1)).trimEnd() + "…";
  }

  function isImageMime(mime) {
    return /^image\//i.test(String(mime || ""));
  }

  function isVideoMime(mime) {
    return /^video\//i.test(String(mime || ""));
  }

  function isAudioMime(mime) {
    return /^audio\//i.test(String(mime || ""));
  }

  function formatBytes(value) {
    const num = Number(value || 0);
    if (!num || num < 1) return "";
    if (num < 1024) return num + " B";
    if (num < 1024 * 1024) return (num / 1024).toFixed(1).replace(/\.0$/, "") + " KB";
    if (num < 1024 * 1024 * 1024) {
      return (num / (1024 * 1024)).toFixed(1).replace(/\.0$/, "") + " MB";
    }
    return (num / (1024 * 1024 * 1024)).toFixed(1).replace(/\.0$/, "") + " GB";
  }

  function normalizeAttachment(item) {
    const raw = item && typeof item === "object" ? item : {};
    const name =
      raw.filename ||
      raw.name ||
      raw.title ||
      raw.label ||
      "attachment";
    const mimeType =
      raw.mime_type ||
      raw.type ||
      "application/octet-stream";
    return {
      id: String(raw.id || raw.attachment_id || makeId("att")),
      name: String(name),
      filename: String(name),
      stored_name: String(raw.stored_name || raw.stored_filename || name),
      url: String(raw.url || raw.file_url || raw.source_url || ""),
      mime_type: String(mimeType),
      size: Number(raw.size || 0),
      status: String(raw.status || "uploaded"),
      upload_error: String(raw.upload_error || ""),
    };
  }

  function normalizeMessage(raw) {
    const item = raw && typeof raw === "object" ? raw : {};
    return {
      id: String(item.id || makeId("msg")),
      role: String(item.role || "assistant"),
      text: normalizeText(item.text || item.content || item.body || item.message || ""),
      created_at: String(item.created_at || new Date().toISOString()),
      pending: Boolean(item.pending),
      streaming: Boolean(item.streaming),
      stopped: Boolean(item.stopped),
      error: Boolean(item.error),
      source: String(item.source || ""),
      meta: item.meta && typeof item.meta === "object" ? item.meta : {},
      attachments: safeArray(item.attachments).map(normalizeAttachment),
    };
  }

  function attachmentSummary(attachment) {
    const name = attachment.filename || attachment.name || "attachment";
    const size = formatBytes(attachment.size);
    return size ? name + " · " + size : name;
  }

  const els = {
    appShell: qs("[data-app-shell]"),
    body: document.body,
    sidebar: qs("[data-left-sidebar]"),
    sidebarBackdrop: qs("[data-sidebar-backdrop]"),
    sidebarToggle: qs("[data-sidebar-toggle]"),
    sidebarClose: qs("[data-sidebar-close]"),
    newChatButton: qs("[data-new-chat]"),
    sessionList: qs("[data-session-list]"),
    chatThread: qs("[data-chat-thread]"),
    chatEmpty: qs("[data-chat-empty]"),
    chatInput: qs("[data-chat-input]"),
    composerForm: qs("[data-chat-form]"),
    sendButton: qs("[data-send-button]"),
    stopButton: qs("[data-stop-button]"),
    attachButton: qs("[data-attach-button]"),
    attachInput: qs("[data-attach-input]"),
    uploadStaging: qs("[data-upload-staging]"),
    topbarTitle: qs("[data-topbar-title]"),
    topbarSubtitle: qs("[data-topbar-subtitle]"),
    topbarStatus: qs("[data-topbar-status]"),
    artifactList: qs("[data-artifact-list]"),
    memoryList: qs("[data-memory-list]"),
    webList: qs("[data-web-list]"),
    rail: qs("[data-right-rail]"),
    railTitle: qs("[data-rail-title]"),
    railSubtitle: qs("[data-rail-subtitle]"),
    railViewer: qs("[data-rail-viewer]"),
    railTabs: qsa("[data-rail-tab]"),
    railPanels: qsa("[data-rail-panel]"),
  };

  const state = {
    booted: false,
    activeSessionId: "",
    sessions: [],
    messages: [],
    artifacts: [],
    memory: [],
    pendingUploads: [],
    uploadInFlightCount: 0,
    stream: {
      controller: null,
      running: false,
      messageId: "",
      mode: "",
      placeholderId: "",
      buffer: "",
    },
    rail: {
      tab: "artifacts",
      selectedId: "",
      selectedKind: "",
    },
  };

  function setTopbar(title, subtitle, statusText) {
    if (els.topbarTitle) {
      els.topbarTitle.textContent = title || "Nova";
    }
    if (els.topbarSubtitle) {
      els.topbarSubtitle.textContent = subtitle || "Fast local AI workspace";
    }
    if (els.topbarStatus) {
      els.topbarStatus.textContent = statusText || "Ready";
    }
  }

  function setBusyUi(isBusy) {
    if (els.sendButton) {
      els.sendButton.disabled = Boolean(isBusy);
    }
    if (els.stopButton) {
      els.stopButton.hidden = !isBusy;
      els.stopButton.disabled = !isBusy;
    }
    if (els.chatInput) {
      els.chatInput.disabled = false;
    }
    if (els.attachButton) {
      els.attachButton.disabled = Boolean(isBusy && state.uploadInFlightCount > 0);
    }
  }

  function autoResizeTextarea() {
    if (!els.chatInput) return;
    els.chatInput.style.height = "auto";
    els.chatInput.style.height = Math.min(els.chatInput.scrollHeight, 280) + "px";
  }

  function scrollChatToBottom(force) {
    if (!els.chatThread) return;
    const nearBottom =
      els.chatThread.scrollHeight - els.chatThread.scrollTop - els.chatThread.clientHeight < 160;
    if (force || nearBottom) {
      els.chatThread.scrollTop = els.chatThread.scrollHeight;
    }
  }

  function setChatEmptyVisible(isVisible) {
    if (!els.chatEmpty) return;
    els.chatEmpty.hidden = !isVisible;
  }

  function activeSession() {
    return state.sessions.find(function (session) {
      return String(session.id) === String(state.activeSessionId);
    }) || null;
  }

  function updateTopbarFromState() {
    const session = activeSession();
    const title = session && session.title ? session.title : "Nova";
    const subtitle =
      session && Number(session.message_count || safeArray(session.messages).length || 0) > 0
        ? Number(session.message_count || safeArray(session.messages).length || 0) + " messages"
        : "Fast local AI workspace";
    const statusText = state.stream.running ? "Generating" : "Ready";
    setTopbar(title, subtitle, statusText);
  }

  function findMessageById(messageId) {
    return state.messages.find(function (item) {
      return String(item.id) === String(messageId);
    }) || null;
  }

  function upsertMessage(rawMessage) {
    const message = normalizeMessage(rawMessage);
    const index = state.messages.findIndex(function (item) {
      return String(item.id) === String(message.id);
    });
    if (index >= 0) {
      state.messages[index] = Object.assign({}, state.messages[index], message);
    } else {
      state.messages.push(message);
    }
    renderChat();
    return message;
  }

  function removeMessageById(messageId) {
    const before = state.messages.length;
    state.messages = state.messages.filter(function (item) {
      return String(item.id) !== String(messageId);
    });
    if (state.messages.length !== before) {
      renderChat();
    }
  }

  function setSessions(list) {
    state.sessions = safeArray(list).map(function (item) {
      const session = item && typeof item === "object" ? item : {};
      return {
        id: String(session.id || makeId("session")),
        title: String(session.title || "Untitled chat"),
        created_at: String(session.created_at || ""),
        updated_at: String(session.updated_at || ""),
        pinned: Boolean(session.pinned),
        last_message_preview: String(session.last_message_preview || ""),
        message_count: Number(session.message_count || safeArray(session.messages).length || 0),
        messages: safeArray(session.messages).map(normalizeMessage),
      };
    });
    renderSessionList();
  }

  function applyStatePayload(payload) {
    const data = payload && typeof payload === "object" ? payload : {};
    state.activeSessionId = String(
      data.active_session_id ||
        data.session_id ||
        (data.session && data.session.id) ||
        state.activeSessionId ||
        ""
    );

    if (Array.isArray(data.sessions)) {
      setSessions(data.sessions);
    }

    if (Array.isArray(data.messages)) {
      state.messages = data.messages.map(normalizeMessage);
    } else if (data.session && Array.isArray(data.session.messages)) {
      state.messages = data.session.messages.map(normalizeMessage);
    }

    state.artifacts = safeArray(data.artifacts);
    state.memory = safeArray(data.memory);

    renderSessionList();
    renderChat();
    renderArtifacts();
    renderMemory();
    updateTopbarFromState();
  }

  function currentUserMessageForRegenerate(targetAssistantId) {
    const targetId = String(targetAssistantId || "");
    let targetIndex = -1;
    for (let i = 0; i < state.messages.length; i += 1) {
      if (String(state.messages[i].id) === targetId) {
        targetIndex = i;
        break;
      }
    }
    if (targetIndex <= 0) return null;
    for (let j = targetIndex - 1; j >= 0; j -= 1) {
      if (String(state.messages[j].role) === "user") {
        return state.messages[j];
      }
    }
    return null;
  }

  function createAssistantPlaceholder(mode, targetAssistantId) {
    const messageId = String(targetAssistantId || makeId("assistant"));
    const placeholder = normalizeMessage({
      id: messageId,
      role: "assistant",
      text: "",
      created_at: new Date().toISOString(),
      pending: true,
      streaming: true,
      source: mode || "send",
      attachments: [],
      meta: mode === "regenerate" ? { regenerate_of: messageId } : {},
    });
    upsertMessage(placeholder);
    return placeholder;
  }

  function attachmentChipHtml(attachment, options) {
    const item = normalizeAttachment(attachment);
    const opts = options && typeof options === "object" ? options : {};
    const removable = Boolean(opts.removable);
    const status = item.status || "uploaded";
    const error = item.upload_error || "";
    const summary = attachmentSummary(item);
    const removeButton = removable
      ? '<button type="button" class="nova-upload-chip__remove" data-upload-remove="' +
        escapeHtml(item.id) +
        '" aria-label="Remove attachment">×</button>'
      : "";
    const statusHtml =
      status === "uploading"
        ? '<span class="nova-upload-chip__status">Uploading…</span>'
        : status === "error"
        ? '<span class="nova-upload-chip__status nova-upload-chip__status--error">' +
          escapeHtml(error || "Upload failed") +
          "</span>"
        : "";
    return (
      '<div class="nova-upload-chip" data-upload-id="' +
      escapeHtml(item.id) +
      '">' +
      '<div class="nova-upload-chip__meta">' +
      '<div class="nova-upload-chip__name">' +
      escapeHtml(item.filename || item.name || "attachment") +
      "</div>" +
      '<div class="nova-upload-chip__sub">' +
      escapeHtml(summary) +
      "</div>" +
      statusHtml +
      "</div>" +
      removeButton +
      "</div>"
    );
  }

  function renderPendingUploads() {
    if (!els.uploadStaging) return;
    const items = state.pendingUploads;
    if (!items.length) {
      els.uploadStaging.innerHTML = "";
      els.uploadStaging.hidden = true;
      return;
    }
    els.uploadStaging.hidden = false;
    els.uploadStaging.innerHTML = items
      .map(function (item) {
        return attachmentChipHtml(item, { removable: item.status !== "uploading" });
      })
      .join("");
  }

  function renderAttachmentBlock(attachment) {
    const item = normalizeAttachment(attachment);
    const name = item.filename || item.name || "attachment";
    const href = item.url || "#";
    const mime = item.mime_type || "application/octet-stream";
    const sub = [];
    if (mime) sub.push(mime);
    if (item.size) sub.push(formatBytes(item.size));
    const subText = sub.join(" · ");

    if (item.url && isImageMime(mime)) {
      return (
        '<div class="message-attachment message-attachment--image">' +
        '<a href="' +
        escapeHtml(href) +
        '" target="_blank" rel="noopener noreferrer">' +
        '<img src="' +
        escapeHtml(href) +
        '" alt="' +
        escapeHtml(name) +
        '" class="message-attachment__image">' +
        "</a>" +
        '<div class="message-attachment__footer">' +
        '<a href="' +
        escapeHtml(href) +
        '" target="_blank" rel="noopener noreferrer" class="message-attachment__name">' +
        escapeHtml(name) +
        "</a>" +
        '<div class="message-attachment__sub">' +
        escapeHtml(subText) +
        "</div>" +
        "</div>" +
        "</div>"
      );
    }

    if (item.url && isVideoMime(mime)) {
      return (
        '<div class="message-attachment message-attachment--video">' +
        '<video controls preload="metadata" class="message-attachment__video">' +
        '<source src="' +
        escapeHtml(href) +
        '" type="' +
        escapeHtml(mime) +
        '">' +
        "</video>" +
        '<div class="message-attachment__footer">' +
        '<a href="' +
        escapeHtml(href) +
        '" target="_blank" rel="noopener noreferrer" class="message-attachment__name">' +
        escapeHtml(name) +
        "</a>" +
        '<div class="message-attachment__sub">' +
        escapeHtml(subText) +
        "</div>" +
        "</div>" +
        "</div>"
      );
    }

    if (item.url && isAudioMime(mime)) {
      return (
        '<div class="message-attachment message-attachment--audio">' +
        '<audio controls preload="metadata" class="message-attachment__audio">' +
        '<source src="' +
        escapeHtml(href) +
        '" type="' +
        escapeHtml(mime) +
        '">' +
        "</audio>" +
        '<div class="message-attachment__footer">' +
        '<a href="' +
        escapeHtml(href) +
        '" target="_blank" rel="noopener noreferrer" class="message-attachment__name">' +
        escapeHtml(name) +
        "</a>" +
        '<div class="message-attachment__sub">' +
        escapeHtml(subText) +
        "</div>" +
        "</div>" +
        "</div>"
      );
    }

    return (
      '<div class="message-attachment message-attachment--file">' +
      '<a href="' +
      escapeHtml(href || "#") +
      '" target="_blank" rel="noopener noreferrer" class="message-attachment__file-link">' +
      '<div class="message-attachment__icon">📎</div>' +
      '<div class="message-attachment__footer">' +
      '<div class="message-attachment__name">' +
      escapeHtml(name) +
      "</div>" +
      '<div class="message-attachment__sub">' +
      escapeHtml(subText) +
      "</div>" +
      "</div>" +
      "</a>" +
      "</div>"
    );
  }

  function renderMessageActions(message) {
    if (String(message.role) !== "assistant") return "";
    const disabled = state.stream.running ? ' aria-disabled="true"' : "";
    return (
      '<div class="message-actions">' +
      '<button type="button" class="message-action" data-copy-message="' +
      escapeHtml(message.id) +
      '"' +
      disabled +
      ">Copy</button>" +
      '<button type="button" class="message-action" data-regenerate-message="' +
      escapeHtml(message.id) +
      '"' +
      disabled +
      ">Regenerate</button>" +
      "</div>"
    );
  }

  function renderMessageCard(message) {
    const role = String(message.role || "assistant");
    const roleClass = role === "user" ? "message-card--user" : "message-card--assistant";
    const attachments = safeArray(message.attachments);
    const attachmentsHtml = attachments.length
      ? '<div class="message-attachments">' +
        attachments.map(renderAttachmentBlock).join("") +
        "</div>"
      : "";
    const bodyHtml = message.text
      ? '<div class="message-card__body">' + renderSafeText(message.text) + "</div>"
      : message.pending || message.streaming
      ? '<div class="message-card__body"><span class="message-card__cursor">▋</span></div>'
      : "";
    const metaBits = [];
    if (message.pending || message.streaming) metaBits.push("Streaming");
    if (message.error) metaBits.push("Error");
    if (message.stopped) metaBits.push("Stopped");
    if (message.source) metaBits.push(message.source);
    const metaHtml = metaBits.length
      ? '<div class="message-card__meta">' + escapeHtml(metaBits.join(" · ")) + "</div>"
      : "";
    return (
      '<article class="message-card ' +
      roleClass +
      '" data-message-id="' +
      escapeHtml(message.id) +
      '">' +
      '<div class="message-card__header">' +
      '<div class="message-card__role">' +
      escapeHtml(role === "user" ? "You" : "Nova") +
      "</div>" +
      metaHtml +
      "</div>" +
      bodyHtml +
      attachmentsHtml +
      renderMessageActions(message) +
      "</article>"
    );
  }

  function renderChat() {
    if (!els.chatThread) return;
    setChatEmptyVisible(state.messages.length === 0);
    els.chatThread.innerHTML = state.messages.map(renderMessageCard).join("");
    scrollChatToBottom(true);
  }

  function renderSessionList() {
    if (!els.sessionList) return;
    const sessions = state.sessions.slice().sort(function (a, b) {
      const ap = a.pinned ? 1 : 0;
      const bp = b.pinned ? 1 : 0;
      if (ap !== bp) return bp - ap;
      const at = Date.parse(a.updated_at || a.created_at || 0) || 0;
      const bt = Date.parse(b.updated_at || b.created_at || 0) || 0;
      return bt - at;
    });

    els.sessionList.innerHTML = sessions
      .map(function (session) {
        const active = String(session.id) === String(state.activeSessionId);
        return (
          '<button type="button" class="session-card' +
          (active ? " is-active" : "") +
          '" data-open-session="' +
          escapeHtml(session.id) +
          '">' +
          '<div class="session-card__title-row">' +
          '<div class="session-card__title">' +
          escapeHtml(session.title || "Untitled chat") +
          "</div>" +
          (session.pinned ? '<div class="session-card__pin">📌</div>' : "") +
          "</div>" +
          '<div class="session-card__preview">' +
          escapeHtml(session.last_message_preview || "No messages yet") +
          "</div>" +
          "</button>"
        );
      })
      .join("");
  }

  function renderArtifacts() {
    if (!els.artifactList) return;
    const items = safeArray(state.artifacts);
    els.artifactList.innerHTML = items.length
      ? items
          .map(function (item) {
            const id = String(item.id || "");
            const title = String(item.title || item.name || "Artifact");
            const preview = String(item.preview || item.body || item.summary || "");
            return (
              '<button type="button" class="rail-item" data-artifact-open="' +
              escapeHtml(id) +
              '">' +
              '<div class="rail-item__title">' +
              escapeHtml(title) +
              "</div>" +
              '<div class="rail-item__preview">' +
              escapeHtml(summarizeText(preview, 90)) +
              "</div>" +
              "</button>"
            );
          })
          .join("")
      : '<div class="rail-empty">No artifacts yet.</div>';
  }

  function renderMemory() {
    if (!els.memoryList) return;
    const items = safeArray(state.memory);
    els.memoryList.innerHTML = items.length
      ? items
          .map(function (item) {
            const text = String(item.text || item.content || item.body || "");
            const kind = String(item.kind || "note");
            return (
              '<div class="rail-item rail-item--static">' +
              '<div class="rail-item__title">' +
              escapeHtml(kind) +
              "</div>" +
              '<div class="rail-item__preview">' +
              escapeHtml(summarizeText(text, 120)) +
              "</div>" +
              "</div>"
            );
          })
          .join("")
      : '<div class="rail-empty">No memory yet.</div>';
  }

  async function apiGet(url) {
    const response = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
      },
    });
    const data = await response.json().catch(function () {
      return {};
    });
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || ("Request failed: " + response.status));
    }
    return data;
  }

  async function apiPost(url, body, extra) {
    const response = await fetch(
      url,
      Object.assign(
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(body || {}),
        },
        extra || {}
      )
    );
    const data = await response.json().catch(function () {
      return {};
    });
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || ("Request failed: " + response.status));
    }
    return data;
  }

  async function loadState() {
    const payload = await apiGet("/api/state");
    applyStatePayload(payload);
  }

  function setPendingUploadItem(nextItem) {
    const normalized = normalizeAttachment(nextItem);
    const index = state.pendingUploads.findIndex(function (item) {
      return String(item.id) === String(normalized.id);
    });
    if (index >= 0) {
      state.pendingUploads[index] = Object.assign({}, state.pendingUploads[index], normalized);
    } else {
      state.pendingUploads.push(normalized);
    }
    renderPendingUploads();
  }

  function removePendingUpload(attachmentId) {
    state.pendingUploads = state.pendingUploads.filter(function (item) {
      return String(item.id) !== String(attachmentId);
    });
    renderPendingUploads();
  }

  async function uploadOneFile(file) {
    const tempId = makeId("att_local");
    setPendingUploadItem({
      id: tempId,
      name: file && file.name ? file.name : "upload",
      filename: file && file.name ? file.name : "upload",
      mime_type: file && file.type ? file.type : "application/octet-stream",
      size: file && typeof file.size === "number" ? file.size : 0,
      status: "uploading",
    });

    const formData = new FormData();
    formData.append("file", file);

    state.uploadInFlightCount += 1;
    setBusyUi(state.stream.running);

    try {
      const response = await fetch("/api/upload", {
        method: "POST",
        credentials: "same-origin",
        body: formData,
      });

      const data = await response.json().catch(function () {
        return {};
      });

      if (!response.ok || data.ok === false) {
        throw new Error(data.error || "Upload failed.");
      }

      state.pendingUploads = state.pendingUploads.filter(function (item) {
        return String(item.id) !== String(tempId);
      });
      setPendingUploadItem(
        Object.assign({}, normalizeAttachment(data.attachment || data), {
          status: "uploaded",
          upload_error: "",
        })
      );
      return normalizeAttachment(data.attachment || data);
    } catch (error) {
      warn("upload failed", error);
      setPendingUploadItem({
        id: tempId,
        name: file && file.name ? file.name : "upload",
        filename: file && file.name ? file.name : "upload",
        mime_type: file && file.type ? file.type : "application/octet-stream",
        size: file && typeof file.size === "number" ? file.size : 0,
        status: "error",
        upload_error: error && error.message ? error.message : "Upload failed.",
      });
      throw error;
    } finally {
      state.uploadInFlightCount = Math.max(0, state.uploadInFlightCount - 1);
      setBusyUi(state.stream.running);
      renderPendingUploads();
    }
  }

  async function uploadFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    for (const file of files) {
      await uploadOneFile(file);
    }
  }

  function clearPendingUploads() {
    state.pendingUploads = [];
    if (els.attachInput) {
      els.attachInput.value = "";
    }
    renderPendingUploads();
  }

  function getSendPayload(base) {
    const source = base && typeof base === "object" ? base : {};
    return {
      session_id: String(state.activeSessionId || ""),
      user_text: String(source.user_text || ""),
      stream: true,
      regenerate_of: source.regenerate_of ? String(source.regenerate_of) : "",
      attachments: safeArray(source.attachments).map(normalizeAttachment),
    };
  }

  function appendUserMessageLocal(text, attachments) {
    const message = normalizeMessage({
      id: makeId("user"),
      role: "user",
      text: text,
      attachments: safeArray(attachments).map(normalizeAttachment),
      created_at: new Date().toISOString(),
    });
    upsertMessage(message);
    return message;
  }

  async function consumeChatStream(payload) {
    if (state.stream.running) {
      throw new Error("A generation is already running.");
    }

    const controller = new AbortController();
    state.stream.controller = controller;
    state.stream.running = true;
    state.stream.messageId = "";
    state.stream.placeholderId = "";
    state.stream.mode = payload.regenerate_of ? "regenerate" : "send";
    state.stream.buffer = "";
    setBusyUi(true);
    updateTopbarFromState();

    const response = await fetch("/api/chat", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    if (!response.ok || !response.body) {
      state.stream.running = false;
      state.stream.controller = null;
      setBusyUi(false);
      updateTopbarFromState();
      let message = "Chat failed.";
      try {
        const data = await response.json();
        if (data && data.error) message = data.error;
      } catch (_) {}
      throw new Error(message);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    try {
      while (true) {
        const result = await reader.read();
        if (result.done) break;
        buffer += decoder.decode(result.value, { stream: true });

        let boundary = buffer.indexOf("\n\n");
        while (boundary >= 0) {
          const rawEvent = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          boundary = buffer.indexOf("\n\n");

          const lines = rawEvent.split("\n");
          const dataLine = lines
            .filter(function (line) {
              return line.indexOf("data: ") === 0;
            })
            .map(function (line) {
              return line.slice(6);
            })
            .join("");

          if (!dataLine) continue;

          let evt = null;
          try {
            evt = JSON.parse(dataLine);
          } catch (error) {
            warn("bad sse json", error, dataLine);
            continue;
          }

          handleStreamEvent(evt);
        }
      }
    } finally {
      try {
        reader.releaseLock();
      } catch (_) {}
    }
  }

  function handleStreamEvent(evt) {
    const event = evt && typeof evt === "object" ? evt : {};
    const type = String(event.type || "");

    if (type === "start") {
      const messageId = String(event.message_id || event.assistant_message_id || makeId("assistant"));
      state.stream.messageId = messageId;

      const existing = findMessageById(messageId);
      if (existing) {
        upsertMessage(
          Object.assign({}, existing, {
            pending: true,
            streaming: true,
            source: state.stream.mode || "send",
          })
        );
      } else {
        const placeholder = createAssistantPlaceholder(state.stream.mode || "send", messageId);
        state.stream.placeholderId = placeholder.id;
      }

      scrollChatToBottom(true);
      return;
    }

    if (type === "token") {
      const messageId = String(event.message_id || event.assistant_message_id || state.stream.messageId || "");
      if (!messageId) return;

      const existing = findMessageById(messageId) || createAssistantPlaceholder(state.stream.mode || "send", messageId);
      upsertMessage(
        Object.assign({}, existing, {
          id: messageId,
          text: String(existing.text || "") + String(event.token || ""),
          pending: true,
          streaming: true,
          source: state.stream.mode || "send",
        })
      );
      scrollChatToBottom(false);
      return;
    }

    if (type === "final") {
      const finalMessage = normalizeMessage(
        event.message || {
          id: String(event.message_id || event.assistant_message_id || state.stream.messageId || makeId("assistant")),
          role: "assistant",
          text: state.stream.buffer || "",
        }
      );
      upsertMessage(
        Object.assign({}, finalMessage, {
          pending: false,
          streaming: false,
        })
      );

      if (Array.isArray(event.messages)) {
        state.messages = event.messages.map(normalizeMessage);
        renderChat();
      }
      if (Array.isArray(event.artifacts)) {
        state.artifacts = event.artifacts;
        renderArtifacts();
      }
      if (Array.isArray(event.memory)) {
        state.memory = event.memory;
        renderMemory();
      }

      state.stream.running = false;
      state.stream.controller = null;
      state.stream.messageId = "";
      state.stream.placeholderId = "";
      state.stream.buffer = "";
      setBusyUi(false);
      updateTopbarFromState();
      scrollChatToBottom(true);
      return;
    }

    if (type === "error") {
      const errorMessage = normalizeMessage(
        event.message || {
          id: String(event.message_id || event.assistant_message_id || state.stream.messageId || makeId("assistant")),
          role: "assistant",
          text: String(event.error || "Generation failed."),
          error: true,
        }
      );

      upsertMessage(
        Object.assign({}, errorMessage, {
          pending: false,
          streaming: false,
          error: true,
        })
      );

      state.stream.running = false;
      state.stream.controller = null;
      state.stream.messageId = "";
      state.stream.placeholderId = "";
      state.stream.buffer = "";
      setBusyUi(false);
      updateTopbarFromState();
      return;
    }
  }

  async function sendMessage() {
    const text = els.chatInput ? normalizeText(els.chatInput.value) : "";
    const attachments = state.pendingUploads
      .filter(function (item) {
        return String(item.status || "") === "uploaded";
      })
      .map(normalizeAttachment);

    const hasUploading = state.pendingUploads.some(function (item) {
      return String(item.status || "") === "uploading";
    });

    const hasUploadErrors = state.pendingUploads.some(function (item) {
      return String(item.status || "") === "error";
    });

    if (hasUploading) {
      throw new Error("Please wait for uploads to finish.");
    }

    if (hasUploadErrors) {
      throw new Error("Remove failed uploads before sending.");
    }

    if (!text.trim() && !attachments.length) {
      return;
    }

    if (!state.activeSessionId) {
      const created = await apiPost("/api/sessions/new", {});
      if (created && created.session && created.session.id) {
        state.activeSessionId = String(created.session.id);
      } else if (created && created.active_session_id) {
        state.activeSessionId = String(created.active_session_id);
      }
      await loadState();
    }

    appendUserMessageLocal(text, attachments);
    if (els.chatInput) {
      els.chatInput.value = "";
      autoResizeTextarea();
    }

    clearPendingUploads();

    const payload = getSendPayload({
      user_text: text,
      attachments: attachments,
    });

    await consumeChatStream(payload);
  }

  async function regenerateMessage(targetAssistantId) {
    const assistantId = String(targetAssistantId || "");
    if (!assistantId) return;

    const userMessage = currentUserMessageForRegenerate(assistantId);
    const attachments = userMessage ? safeArray(userMessage.attachments).map(normalizeAttachment) : [];

    const existing = findMessageById(assistantId);
    if (existing) {
      upsertMessage(
        Object.assign({}, existing, {
          text: "",
          pending: true,
          streaming: true,
          error: false,
          stopped: false,
          source: "regenerate",
        })
      );
    } else {
      createAssistantPlaceholder("regenerate", assistantId);
    }

    const payload = getSendPayload({
      user_text: "",
      attachments: attachments,
      regenerate_of: assistantId,
    });

    await consumeChatStream(payload);
  }

  function stopGeneration() {
    if (!state.stream.running || !state.stream.controller) return;
    try {
      state.stream.controller.abort();
    } catch (_) {}
    state.stream.running = false;
    state.stream.controller = null;
    setBusyUi(false);
    updateTopbarFromState();
  }

  async function openSession(sessionId) {
    const id = String(sessionId || "");
    if (!id) return;
    if (state.stream.running) {
      stopGeneration();
    }
    const payload = await apiPost("/api/sessions/open", { session_id: id });
    if (payload && payload.session) {
      state.activeSessionId = String(payload.session.id || id);
    }
    await loadState();
  }

  async function createNewChat() {
    if (state.stream.running) {
      stopGeneration();
    }
    await apiPost("/api/sessions/new", {});
    clearPendingUploads();
    if (els.chatInput) {
      els.chatInput.value = "";
      autoResizeTextarea();
    }
    await loadState();
  }

  async function copyMessage(messageId) {
    const message = findMessageById(messageId);
    if (!message) return;
    try {
      await navigator.clipboard.writeText(message.text || "");
    } catch (error) {
      warn("copy failed", error);
    }
  }

  function openAttachPicker() {
    if (!els.attachInput) return;
    els.attachInput.click();
  }

  function handleComposerSubmit(event) {
    if (event) {
      event.preventDefault();
    }
    sendMessage().catch(function (error) {
      warn("send failed", error);
      window.alert(error && error.message ? error.message : "Send failed.");
    });
  }

  function bindEvents() {
    if (els.composerForm) {
      els.composerForm.addEventListener("submit", handleComposerSubmit);
    }

    if (els.chatInput) {
      els.chatInput.addEventListener("input", autoResizeTextarea);
      els.chatInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          handleComposerSubmit(event);
        }
      });
    }

    if (els.attachButton) {
      els.attachButton.addEventListener("click", function (event) {
        event.preventDefault();
        openAttachPicker();
      });
    }

    if (els.attachInput) {
      els.attachInput.addEventListener("change", function (event) {
        const files = event && event.target && event.target.files ? event.target.files : [];
        uploadFiles(files).catch(function (error) {
          warn("upload files failed", error);
          window.alert(error && error.message ? error.message : "Upload failed.");
        });
      });
    }

    if (els.stopButton) {
      els.stopButton.addEventListener("click", function (event) {
        event.preventDefault();
        stopGeneration();
      });
    }

    if (els.newChatButton) {
      els.newChatButton.addEventListener("click", function (event) {
        event.preventDefault();
        createNewChat().catch(function (error) {
          warn("new chat failed", error);
        });
      });
    }

    document.addEventListener("click", function (event) {
      const removeChip = event.target.closest("[data-upload-remove]");
      if (removeChip) {
        event.preventDefault();
        removePendingUpload(removeChip.getAttribute("data-upload-remove"));
        return;
      }

      const openSessionButton = event.target.closest("[data-open-session]");
      if (openSessionButton) {
        event.preventDefault();
        openSession(openSessionButton.getAttribute("data-open-session")).catch(function (error) {
          warn("open session failed", error);
        });
        return;
      }

      const copyButton = event.target.closest("[data-copy-message]");
      if (copyButton) {
        event.preventDefault();
        copyMessage(copyButton.getAttribute("data-copy-message"));
        return;
      }

      const regenButton = event.target.closest("[data-regenerate-message]");
      if (regenButton) {
        event.preventDefault();
        if (state.stream.running) return;
        regenerateMessage(regenButton.getAttribute("data-regenerate-message")).catch(function (error) {
          warn("regenerate failed", error);
          window.alert(error && error.message ? error.message : "Regenerate failed.");
        });
      }
    });
  }

  async function boot() {
    if (state.booted) return;
    state.booted = true;

    log("boot start");
    bindEvents();
    autoResizeTextarea();
    renderPendingUploads();
    setBusyUi(false);
    setTopbar("Nova", "Fast local AI workspace", "Ready");

    try {
      await loadState();
    } catch (error) {
      warn("boot state load failed", error);
      renderChat();
      renderSessionList();
      renderArtifacts();
      renderMemory();
    }

    log("boot complete");
  }

  window.NovaComposerBundle = {
    state: state,
    sendMessage: sendMessage,
    regenerateMessage: regenerateMessage,
    stopGeneration: stopGeneration,
    loadState: loadState,
    uploadFiles: uploadFiles,
    clearPendingUploads: clearPendingUploads,
  };

  boot();
})();