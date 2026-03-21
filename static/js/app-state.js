(() => {
"use strict";

if (window.NovaApp && window.NovaApp.state) {
  console.warn("Nova app-state already loaded.");
  return;
}

const STORAGE_KEY = "nova_active_chat_id";

const state = {
  chats: [],
  activeChatId: null,
  messagesByChatId: {},
  attachedFiles: [],
  models: [],
  selectedModel: "gpt-4.1-mini",
  isLoadingChat: false,
  isAuthenticated: true,
  voice: {
    supported: false,
    listening: false,
    recognition: null,
    blockedReason: ""
  },
  memory: {
    isOpen: false
  }
};

const el = {};

function byId(id) {
  return document.getElementById(id);
}

function cacheElements() {
  el.appShell = byId("appShell");
  el.chatMessages = byId("chatMessages");
  el.chatList = byId("chatList");
  el.sendBtn = byId("sendBtn");
  el.stopBtn = byId("stopBtn");
  el.modelSelect = byId("modelSelect");
  el.renameChatBtn = byId("renameChatBtn");
  el.deleteChatBtn = byId("deleteChatBtn");
  el.exportChatBtn = byId("exportChatBtn");
  el.newChatBtn = byId("newChatBtn");
  el.activeChatTitleText = byId("activeChatTitleText");
  el.activeChatMeta = byId("activeChatMeta");
  el.messageInput = byId("messageInput");
  el.fileInput = byId("fileInput");
  el.attachBtn = byId("attachBtn");
  el.attachedFilesBar = byId("attachedFilesBar");
  el.sidebar = byId("sidebar");
  el.sidebarToggleBtn = byId("sidebarToggleBtn");
  el.btnCloseSidebar = byId("btnCloseSidebar");
  el.memoryPanel = byId("memoryPanel");
  el.openMemoryBtn = byId("openMemoryBtn");
  el.closeMemoryBtn = byId("closeMemoryBtn");
  el.themeToggleBtn = byId("themeToggleBtn");
  el.voiceBtn = byId("voiceBtn");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getStoredActiveChatId() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch (error) {
    console.warn("Failed to read active chat from localStorage.", error);
    return null;
  }
}

function setStoredActiveChatId(chatId) {
  try {
    if (!chatId) {
      localStorage.removeItem(STORAGE_KEY);
      return;
    }
    localStorage.setItem(STORAGE_KEY, chatId);
  } catch (error) {
    console.warn("Failed to write active chat to localStorage.", error);
  }
}

function clearStoredActiveChatId() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.warn("Failed to clear active chat from localStorage.", error);
  }
}

function setActiveChatId(chatId) {
  state.activeChatId = chatId || null;
  setStoredActiveChatId(state.activeChatId);
}

function getActiveChatId() {
  return state.activeChatId;
}

function getActiveChat() {
  if (!state.activeChatId) return null;
  return state.chats.find((chat) => chat.id === state.activeChatId) || null;
}

function setChats(chats) {
  state.chats = Array.isArray(chats) ? chats : [];
}

function setMessages(chatId, messages) {
  if (!chatId) return;
  state.messagesByChatId[chatId] = Array.isArray(messages) ? messages : [];
}

function getMessages(chatId) {
  if (!chatId) return [];
  return Array.isArray(state.messagesByChatId[chatId]) ? state.messagesByChatId[chatId] : [];
}

function addMessage(chatId, message) {
  if (!chatId || !message) return;
  if (!Array.isArray(state.messagesByChatId[chatId])) {
    state.messagesByChatId[chatId] = [];
  }
  state.messagesByChatId[chatId].push(message);
}

function replaceMessage(chatId, messageId, nextMessage) {
  if (!chatId || !messageId || !nextMessage) return false;
  const list = getMessages(chatId);
  const index = list.findIndex((item) => item && item.id === messageId);
  if (index === -1) return false;
  list[index] = nextMessage;
  return true;
}

function updateMessageContent(chatId, messageId, content) {
  if (!chatId || !messageId) return false;
  const list = getMessages(chatId);
  const index = list.findIndex((item) => item && item.id === messageId);
  if (index === -1) return false;
  list[index] = {
    ...list[index],
    content: String(content ?? "")
  };
  return true;
}

function removeMessage(chatId, messageId) {
  if (!chatId || !messageId) return false;
  const list = getMessages(chatId);
  const next = list.filter((item) => item && item.id !== messageId);
  if (next.length === list.length) return false;
  state.messagesByChatId[chatId] = next;
  return true;
}

function setAttachedFiles(files) {
  state.attachedFiles = Array.isArray(files) ? files : [];
}

function addAttachedFile(file) {
  if (!file) return;
  state.attachedFiles.push(file);
}

function clearAttachedFiles() {
  state.attachedFiles = [];
  if (el.fileInput) {
    el.fileInput.value = "";
  }
}

function setModels(models) {
  state.models = Array.isArray(models) ? models : [];
}

function setSelectedModel(model) {
  state.selectedModel = model || "gpt-4.1-mini";
  if (el.modelSelect) {
    el.modelSelect.value = state.selectedModel;
  }
}

function initState() {
  cacheElements();
  state.activeChatId = getStoredActiveChatId();
}

window.NovaApp = window.NovaApp || {};
window.NovaApp.state = state;
window.NovaApp.el = el;
window.NovaApp.byId = byId;
window.NovaApp.escapeHtml = escapeHtml;
window.NovaApp.cacheElements = cacheElements;
window.NovaApp.getStoredActiveChatId = getStoredActiveChatId;
window.NovaApp.setStoredActiveChatId = setStoredActiveChatId;
window.NovaApp.clearStoredActiveChatId = clearStoredActiveChatId;
window.NovaApp.setActiveChatId = setActiveChatId;
window.NovaApp.getActiveChatId = getActiveChatId;
window.NovaApp.getActiveChat = getActiveChat;
window.NovaApp.setChats = setChats;
window.NovaApp.setMessages = setMessages;
window.NovaApp.getMessages = getMessages;
window.NovaApp.addMessage = addMessage;
window.NovaApp.replaceMessage = replaceMessage;
window.NovaApp.updateMessageContent = updateMessageContent;
window.NovaApp.removeMessage = removeMessage;
window.NovaApp.setAttachedFiles = setAttachedFiles;
window.NovaApp.addAttachedFile = addAttachedFile;
window.NovaApp.clearAttachedFiles = clearAttachedFiles;
window.NovaApp.setModels = setModels;
window.NovaApp.setSelectedModel = setSelectedModel;
window.NovaApp.initState = initState;

document.addEventListener("DOMContentLoaded", initState);
})();