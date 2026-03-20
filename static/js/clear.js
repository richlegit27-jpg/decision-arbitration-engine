(() => {
"use strict";

if (window.__novaClearLoaded) {
  console.warn("Nova clear already loaded.");
  return;
}
window.__novaClearLoaded = true;

window.NovaApp = window.NovaApp || {};
const app = window.NovaApp;

function byId(id) {
  return document.getElementById(id);
}

function getClearBtn() {
  return app.el?.clearBtn || byId("clearBtn");
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
  alert(text);
}

function getActiveChatId() {
  if (typeof app.getActiveChatId === "function") {
    return app.getActiveChatId();
  }
  return app.state?.activeChatId || null;
}

function getMessagesForChat(chatId) {
  if (!chatId) return [];
  if (!app.state) return [];
  if (!app.state.messagesByChatId) return [];
  return Array.isArray(app.state.messagesByChatId[chatId])
    ? app.state.messagesByChatId[chatId]
    : [];
}

function setMessagesForChat(chatId, messages) {
  if (!chatId) return;
  if (!app.state) {
    app.state = {};
  }
  if (!app.state.messagesByChatId) {
    app.state.messagesByChatId = {};
  }

  app.state.messagesByChatId[chatId] = Array.isArray(messages) ? messages : [];
}

function updateClearButtonState() {
  const clearBtn = getClearBtn();
  if (!clearBtn) return;

  const chatId = getActiveChatId();
  const messages = getMessagesForChat(chatId);
  const hasMessages = messages.length > 0;

  clearBtn.disabled = !chatId || !hasMessages;
  clearBtn.title = hasMessages ? "Clear this chat" : "No messages to clear";
}

function renderAfterClear() {
  if (typeof app.renderMessages === "function") {
    app.renderMessages();
  }

  if (typeof app.renderChatList === "function") {
    app.renderChatList();
  }

  if (typeof app.persistState === "function") {
    app.persistState();
  } else if (typeof app.saveState === "function") {
    app.saveState();
  }

  if (typeof app.syncComposerState === "function") {
    app.syncComposerState();
  }

  updateClearButtonState();
}

async function clearActiveChat() {
  const chatId = getActiveChatId();

  if (!chatId) {
    notifyError("No active chat found.");
    updateClearButtonState();
    return;
  }

  const currentMessages = getMessagesForChat(chatId);
  if (!currentMessages.length) {
    notifyError("This chat is already empty.");
    updateClearButtonState();
    return;
  }

  let confirmed = true;

  if (window.NovaModal && typeof window.NovaModal.confirm === "function") {
    try {
      confirmed = await window.NovaModal.confirm({
        title: "Clear chat?",
        message: "This will remove all messages from the current chat.",
        confirmText: "Clear",
        cancelText: "Cancel",
        danger: true
      });
    } catch (error) {
      console.warn("NovaModal confirm failed, falling back to confirm().", error);
      confirmed = window.confirm("Clear this chat?");
    }
  } else {
    confirmed = window.confirm("Clear this chat?");
  }

  if (!confirmed) {
    return;
  }

  setMessagesForChat(chatId, []);
  renderAfterClear();
  notifySuccess("Chat cleared.");
}

function bindClearEvents() {
  const clearBtn = getClearBtn();

  if (clearBtn && !clearBtn.dataset.clearBound) {
    clearBtn.dataset.clearBound = "true";
    clearBtn.addEventListener("click", clearActiveChat);
  }
}

function initClear() {
  bindClearEvents();
  updateClearButtonState();
}

app.clear = {
  initClear,
  clearActiveChat,
  updateClearButtonState
};

document.addEventListener("DOMContentLoaded", initClear);
document.addEventListener("click", updateClearButtonState);
document.addEventListener("nova:chat-changed", updateClearButtonState);
document.addEventListener("nova:messages-updated", updateClearButtonState);
})();