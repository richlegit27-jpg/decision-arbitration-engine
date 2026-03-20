// C:\Users\Owner\nova\static\js\modules\render.js

import { renameChat, deleteChat } from "./api.js";
import { state, setEditing } from "./state.js";

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function nl2br(value) {
  return escapeHtml(value).replace(/\n/g, "<br>");
}

export function renderChats(chatListEl, chats, activeChatId, onChatClick, onChatsChanged) {
  if (!chatListEl) return;

  chatListEl.innerHTML = "";

  for (const chat of chats) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `chat-item${chat.chat_id === activeChatId ? " active" : ""}`;
    item.dataset.chatId = chat.chat_id;

    const title = document.createElement("div");
    title.className = "chat-item-title";
    title.textContent = chat.title || "New chat";

    const meta = document.createElement("div");
    meta.className = "chat-item-meta";
    meta.textContent = formatDate(chat.updated);

    const actions = document.createElement("div");
    actions.className = "chat-item-actions";

    const renameBtn = document.createElement("button");
    renameBtn.type = "button";
    renameBtn.className = "chat-item-action";
    renameBtn.textContent = "Rename";

    renameBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const nextTitle = window.prompt("Rename chat", chat.title || "New chat");
      if (!nextTitle) return;

      try {
        await renameChat(chat.chat_id, nextTitle);
        await onChatsChanged?.();
      } catch (err) {
        window.alert(`Rename failed: ${err.message}`);
      }
    });

    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "chat-item-action danger";
    deleteBtn.textContent = "Delete";

    deleteBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const ok = window.confirm("Delete this chat?");
      if (!ok) return;

      try {
        await deleteChat(chat.chat_id);
        await onChatsChanged?.(chat.chat_id);
      } catch (err) {
        window.alert(`Delete failed: ${err.message}`);
      }
    });

    actions.appendChild(renameBtn);
    actions.appendChild(deleteBtn);

    item.appendChild(title);
    item.appendChild(meta);
    item.appendChild(actions);

    item.addEventListener("click", () => onChatClick?.(chat.chat_id));
    chatListEl.appendChild(item);
  }
}

export function createMessageRow(role, content = "", attachments = []) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const bubble = document.createElement("div");
  bubble.className = `message-bubble ${role}`;

  const body = document.createElement("div");
  body.className = "message-body";
  body.innerHTML = nl2br(content);

  const actions = document.createElement("div");
  actions.className = "message-actions";

  const copyBtn = document.createElement("button");
  copyBtn.type = "button";
  copyBtn.className = "message-action-btn";
  copyBtn.textContent = "Copy";
  copyBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(content || "");
      copyBtn.textContent = "Copied";
      setTimeout(() => {
        copyBtn.textContent = "Copy";
      }, 1200);
    } catch {
      copyBtn.textContent = "Failed";
      setTimeout(() => {
        copyBtn.textContent = "Copy";
      }, 1200);
    }
  });

  actions.appendChild(copyBtn);

  if (role === "user") {
    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "message-action-btn";
    editBtn.textContent = "Edit";
    editBtn.addEventListener("click", () => {
      const input = document.getElementById("promptInput");
      if (!input) return;
      input.value = content || "";
      input.focus();
      setEditing(true, row);
    });
    actions.appendChild(editBtn);
  }

  bubble.appendChild(actions);
  bubble.appendChild(body);

  if (attachments?.length) {
    bubble.appendChild(renderAttachments(attachments));
  }

  row.appendChild(bubble);
  return row;
}

export function appendMessage(container, role, content = "", attachments = []) {
  const row = createMessageRow(role, content, attachments);
  container.appendChild(row);
  scrollToBottom(container);
  return row;
}

export function updateMessageContent(row, content) {
  const body = row?.querySelector(".message-body");
  if (!body) return;
  body.innerHTML = nl2br(content || "");
}

export function renderMessages(container, messages) {
  if (!container) return;
  container.innerHTML = "";

  for (const msg of messages || []) {
    appendMessage(container, msg.role, msg.content || "", msg.attachments || []);
  }

  scrollToBottom(container);
}

export function renderStatusMessage(container, text) {
  return appendMessage(container, "assistant", text || "");
}

export function renderAttachments(attachments) {
  const wrap = document.createElement("div");
  wrap.className = "message-attachments";

  for (const file of attachments) {
    const a = document.createElement("a");
    a.className = "attachment-chip";
    a.href = file.url || "#";
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = file.original_name || "attachment";

    wrap.appendChild(a);

    if (file.is_image && file.url) {
      const img = document.createElement("img");
      img.className = "attachment-preview";
      img.src = file.url;
      img.alt = file.original_name || "image";
      wrap.appendChild(img);
    }
  }

  return wrap;
}

export function renderPendingFiles(container, files) {
  if (!container) return;
  container.innerHTML = "";

  if (!files?.length) {
    container.hidden = true;
    return;
  }

  container.hidden = false;

  for (const file of files) {
    const chip = document.createElement("div");
    chip.className = "pending-file-chip";
    chip.textContent = `${file.name} (${formatBytes(file.size)})`;
    container.appendChild(chip);
  }
}

export function setComposerBusy(sendBtn, busy) {
  if (!sendBtn) return;
  sendBtn.disabled = Boolean(busy);
  sendBtn.textContent = busy ? "Sending..." : "Send";
}

export function setEmptyState(emptyStateEl, hasMessages) {
  if (!emptyStateEl) return;
  emptyStateEl.hidden = Boolean(hasMessages);
}

export function scrollToBottom(container) {
  if (!container) return;
  container.scrollTop = container.scrollHeight;
}

function formatDate(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function formatBytes(bytes) {
  const n = Number(bytes || 0);
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}