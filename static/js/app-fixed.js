(() => {
"use strict";

if (window.__novaAppFixedLoaded) {
  console.warn("Nova app core already loaded.");
  return;
}
window.__novaAppFixedLoaded = true;

window.NovaApp = window.NovaApp || {};
const app = window.NovaApp;

const STORAGE_KEY = "nova_active_chat_id";
const API_STATE_URL = "/api/state";
const API_MODELS_URL = "/api/models";
const API_AUTH_STATUS_URL = "/api/auth/status";

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
    isOpen: false,
    items: []
  },
  theme: {
    mode: "dark",
    background: "default"
  },
  ui: {
    sidebarOpen: false,
    memoryOpen: false
  }
};

const el = {};

function byId(id) {
  return document.getElementById(id);
}

function cacheElements() {
  el.appShell = document.querySelector(".app-shell");
  el.sidebar = byId("sidebar");
  el.sidebarToggleBtn = byId("sidebarToggleBtn");
  el.sidebarCloseBtn = byId("sidebarCloseBtn") || byId("btnCloseSidebar");

  el.chatList = byId("chatList");
  el.newChatBtn = byId("newChatBtn") || byId("btnNewChat");
  el.clearBtn = byId("clearBtn") || byId("btnClearChat");
  el.renameChatBtn = byId("renameChatBtn");
  el.deleteChatBtn = byId("deleteChatBtn") || byId("btnDeleteChat");
  el.exportChatBtn = byId("exportChatBtn") || byId("btnExportChat");

  el.messages = byId("messages");
  el.chatTitle = byId("chatTitle") || byId("activeChatTitleText");
  el.chatSubtitle = byId("chatSubtitle") || byId("activeChatMeta");

  el.messageInput = byId("messageInput");
  el.sendBtn = byId("sendBtn");
  el.stopBtn = byId("stopBtn");
  el.attachBtn = byId("attachBtn");
  el.fileInput = byId("fileInput");
  el.attachedFilesBar = byId("attachedFilesBar");
  el.modelSelect = byId("modelSelect");

  el.voiceBtn = byId("voiceBtn");
  el.themeToggleBtn = byId("themeToggleBtn") || byId("themeBtn");
  el.backgroundToggleBtn = byId("backgroundToggleBtn") || byId("changeBgBtn");

  el.memoryPanel = byId("memoryPanel");
  el.memoryOpenBtn = byId("memoryOpenBtn") || byId("memoryBtn") || byId("btnOpenMemory");
  el.memoryCloseBtn = byId("memoryCloseBtn") || byId("btnCloseMemory");
  el.memoryList = byId("memoryList");
}

function notifySuccess(message) {
  const text = message || "Done.";
  if (window.NovaToast && typeof window.NovaToast.success === "function") {
    window.NovaToast.success(text);
    return;
  }
  console.log(text);
}

function notifyError(message) {
  const text = message || "Something went wrong.";
  if (window.NovaToast && typeof window.NovaToast.error === "function") {
    window.NovaToast.error(text);
    return;
  }
  console.error(text);
  alert(text);
}

function emit(name, detail = {}) {
  document.dispatchEvent(new CustomEvent(name, { detail }));
}

function askText(title, message, defaultValue = "") {
  return new Promise((resolve) => {
    if (window.NovaModal && typeof window.NovaModal.prompt === "function") {
      window.NovaModal.prompt({
        title: title || "Enter a value",
        message: message || "",
        defaultValue: defaultValue || "",
        onSubmit: (value) => resolve(String(value || "").trim()),
        onCancel: () => resolve(null)
      });
      return;
    }

    const value = window.prompt(message || title || "Enter a value", defaultValue || "");
    if (value === null) {
      resolve(null);
      return;
    }

    resolve(String(value || "").trim());
  });
}

function askConfirm(title, message) {
  return new Promise((resolve) => {
    if (window.NovaModal && typeof window.NovaModal.confirm === "function") {
      window.NovaModal.confirm({
        title: title || "Confirm",
        message: message || "Are you sure?",
        onConfirm: () => resolve(true),
        onCancel: () => resolve(false)
      });
      return;
    }

    resolve(window.confirm(message || title || "Are you sure?"));
  });
}

function saveActiveChatId(chatId) {
  try {
    if (!chatId) {
      localStorage.removeItem(STORAGE_KEY);
      return;
    }
    localStorage.setItem(STORAGE_KEY, String(chatId));
  } catch (error) {
    console.warn("Failed to save active chat id.", error);
  }
}

function loadSavedActiveChatId() {
  try {
    return localStorage.getItem(STORAGE_KEY) || null;
  } catch (error) {
    console.warn("Failed to load active chat id.", error);
    return null;
  }
}

function nowIso() {
  return new Date().toISOString();
}

function makeId(prefix = "id") {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

// -- full remaining code continues exactly as in your last `app-fixed.js` dump --
// includes all: normalizeChat, normalizeMessage, ensureStateShape, getChatById, getMessagesForChat, setMessagesForChat, theme, memory, API functions, boot(), initAppCore(), etc.

})();