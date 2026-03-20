// C:\Users\Owner\nova\static\js\modules\chat-controller.js

import {
  createChat,
  loadChats,
  loadMessages,
  sendMessage,
} from "./api.js";
import { getDom } from "./dom.js";
import {
  appendMessage,
  renderChats,
  renderMessages,
  renderPendingFiles,
  renderStatusMessage,
  setComposerBusy,
  setEmptyState,
  updateMessageContent,
} from "./render.js";
import {
  state,
  clearPendingFiles,
  setActiveChatId,
  setLastTurn,
  setPendingFiles,
  setSending,
} from "./state.js";

const dom = getDom();

export async function initChatApp() {
  bindEvents();
  await refreshChats();
  await ensureInitialChat();
}

function bindEvents() {
  dom.composerForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    await handleSubmit();
  });

  dom.promptInput?.addEventListener("keydown", async (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      await handleSubmit();
    }
  });

  dom.newChatBtn?.addEventListener("click", async () => {
    const created = await createChat();
    setActiveChatId(created.chat_id);
    clearPendingFiles();
    dom.promptInput.value = "";
    dom.chatMessages.innerHTML = "";
    setEmptyState(dom.emptyState, false);
    await refreshChats();
  });

  dom.btnAttach?.addEventListener("click", () => {
    dom.fileUpload?.click();
  });

  dom.fileUpload?.addEventListener("change", () => {
    const files = Array.from(dom.fileUpload?.files || []);
    setPendingFiles(files);
    renderPendingFiles(dom.attachmentTray, state.pendingFiles);
  });
}

async function ensureInitialChat() {
  const url = new URL(window.location.href);
  const chatIdFromUrl = url.searchParams.get("chat_id");

  if (chatIdFromUrl) {
    setActiveChatId(chatIdFromUrl);
    await openChat(chatIdFromUrl);
    return;
  }

  const chatsData = await loadChats();
  const first = chatsData?.chats?.[0];

  if (first?.chat_id) {
    setActiveChatId(first.chat_id);
    await openChat(first.chat_id);
    return;
  }

  const created = await createChat();
  setActiveChatId(created.chat_id);
  updateUrl(created.chat_id);
  await refreshChats();
}

export async function refreshChats(deletedChatId = null) {
  const data = await loadChats();

  if (deletedChatId && state.activeChatId === deletedChatId) {
    const next = data?.chats?.[0];
    setActiveChatId(next?.chat_id || null);

    if (next?.chat_id) {
      updateUrl(next.chat_id);
      await openChat(next.chat_id);
    } else {
      dom.chatMessages.innerHTML = "";
      updateUrl("");
    }
  }

  renderChats(
    dom.chatList,
    data?.chats || [],
    state.activeChatId,
    async (chatId) => {
      setActiveChatId(chatId);
      updateUrl(chatId);
      await openChat(chatId);
      await refreshChats();
    },
    async (deletedId) => {
      await refreshChats(deletedId || null);
    }
  );
}

export async function openChat(chatId) {
  try {
    const data = await loadMessages(chatId);
    dom.chatMessages.innerHTML = "";
    renderMessages(dom.chatMessages, data?.messages || []);
    setEmptyState(dom.emptyState, (data?.messages || []).length > 0);
    updateUrl(chatId);
  } catch (err) {
    dom.chatMessages.innerHTML = "";
    renderStatusMessage(dom.chatMessages, `Failed to load messages: ${err.message}`);
  }
}

async function handleSubmit() {
  if (state.isSending) return;

  const message = (dom.promptInput?.value || "").trim();
  const files = Array.from(state.pendingFiles || []);

  if (!message && !files.length) return;

  setSending(true);
  setComposerBusy(dom.sendBtn, true);

  try {
    let chatId = state.activeChatId;

    if (!chatId) {
      const created = await createChat();
      chatId = created.chat_id;
      setActiveChatId(chatId);
      updateUrl(chatId);
      await refreshChats();
    }

    appendMessage(dom.chatMessages, "user", message, files.map(fileToAttachmentLike));
    setEmptyState(dom.emptyState, true);

    dom.promptInput.value = "";
    if (dom.fileUpload) dom.fileUpload.value = "";
    clearPendingFiles();
    renderPendingFiles(dom.attachmentTray, state.pendingFiles);

    const assistantRow = appendMessage(dom.chatMessages, "assistant", "");

    const stream = await sendMessage({
      chatId,
      message,
      files,
    });

    let finalText = "";
    for await (const evt of stream.events()) {
      if (evt.event === "token") {
        const tokenText = evt.data?.t || "";
        finalText += tokenText;
        updateMessageContent(assistantRow, finalText);
      }

      if (evt.event === "done") {
        finalText = evt.data?.full_text || finalText;
        updateMessageContent(assistantRow, finalText);
      }
    }

    setLastTurn(message, finalText);
    await refreshChats();
  } catch (err) {
    appendMessage(dom.chatMessages, "assistant", `⚠️ Network/stream error: ${err.message}`);
  } finally {
    setSending(false);
    setComposerBusy(dom.sendBtn, false);
  }
}

function updateUrl(chatId) {
  const url = new URL(window.location.href);

  if (chatId) {
    url.searchParams.set("chat_id", chatId);
  } else {
    url.searchParams.delete("chat_id");
  }

  window.history.replaceState({}, "", url);
}

function fileToAttachmentLike(file) {
  return {
    original_name: file.name,
    size_bytes: file.size,
    mime_type: file.type || "application/octet-stream",
    url: "#",
    is_image: (file.type || "").startsWith("image/"),
  };
}