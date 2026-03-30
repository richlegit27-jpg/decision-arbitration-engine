(function () {
  "use strict";

  window.Nova = window.Nova || {};

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function messagesRoot() {
    return document.getElementById("messages");
  }

  function emptyState() {
    return document.getElementById("novaEmptyState");
  }

  function hideEmptyState() {
    const el = emptyState();
    if (el) el.style.display = "none";
  }

  function showEmptyStateIfNeeded() {
    const root = messagesRoot();
    const el = emptyState();
    if (!root || !el) return;
    el.style.display = root.children.length ? "none" : "";
  }

  function scrollToBottom() {
    const root = messagesRoot();
    if (!root) return;
    root.scrollTop = root.scrollHeight;
  }

  function createBubble(role) {
    const row = document.createElement("div");
    row.className = `nova-chat-message ${role}-message`;
    return row;
  }

  function appendNode(node) {
    const root = messagesRoot();
    if (!root || !node) return null;
    hideEmptyState();
    root.appendChild(node);
    scrollToBottom();
    return node;
  }

  function appendText(role, text) {
    const bubble = createBubble(role);
    bubble.textContent = String(text ?? "");
    return appendNode(bubble);
  }

  function appendHtml(role, html) {
    const bubble = createBubble(role);
    bubble.innerHTML = html;
    return appendNode(bubble);
  }

  function appendAttachmentPreview(fileInfo) {
    if (!fileInfo || !fileInfo.url) return null;

    const bubble = createBubble("attachment");
    const mime = String(fileInfo.mime_type || fileInfo.type || "").toLowerCase();
    const name = String(fileInfo.name || fileInfo.filename || "attachment");
    const url = String(fileInfo.url || "");

    if (mime.startsWith("image/")) {
      const img = document.createElement("img");
      img.src = url;
      img.alt = name;
      img.style.maxWidth = "250px";
      img.style.borderRadius = "10px";
      img.style.display = "block";
      bubble.appendChild(img);
    } else if (mime.startsWith("video/")) {
      const video = document.createElement("video");
      video.src = url;
      video.controls = true;
      video.style.maxWidth = "250px";
      video.style.borderRadius = "10px";
      bubble.appendChild(video);
    } else {
      const link = document.createElement("a");
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = `Open: ${name}`;
      bubble.appendChild(link);
    }

    return appendNode(bubble);
  }

  function appendGeneratedImage(image, captionText) {
    if (!image || !image.url) return null;

    const bubble = createBubble("assistant");
    const wrap = document.createElement("div");
    wrap.style.display = "flex";
    wrap.style.flexDirection = "column";
    wrap.style.gap = "8px";

    if (captionText) {
      const caption = document.createElement("div");
      caption.textContent = captionText;
      wrap.appendChild(caption);
    }

    const img = document.createElement("img");
    img.src = image.url;
    img.alt = image.file_name || "generated-image";
    img.style.maxWidth = "350px";
    img.style.borderRadius = "12px";
    img.style.display = "block";
    wrap.appendChild(img);

    const link = document.createElement("a");
    link.href = image.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Open image";
    wrap.appendChild(link);

    bubble.appendChild(wrap);
    return appendNode(bubble);
  }

  function appendAssistantPayload(payload) {
    const text = typeof payload?.message === "string" ? payload.message : "";
    const image = payload?.image || null;

    if (image && image.url) {
      return appendGeneratedImage(image, text);
    }

    return appendText("assistant", text || "[empty reply]");
  }

  function clear() {
    const root = messagesRoot();
    if (!root) return;
    root.innerHTML = "";
    showEmptyStateIfNeeded();
  }

  window.Nova.render = {
    appendText,
    appendHtml,
    appendTextMessage: appendText,
    appendUserMessage(text) {
      return appendText("user", text);
    },
    appendAssistantMessage(text) {
      return appendText("assistant", text);
    },
    appendAssistantPayload,
    appendAttachmentPreview,
    appendGeneratedImage,
    clear,
    scrollToBottom,
    showEmptyStateIfNeeded,
  };
})();