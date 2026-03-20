(() => {
"use strict";

if (window.__novaComposerLoaded) {
  console.warn("Nova composer already loaded.");
  return;
}
window.__novaComposerLoaded = true;

window.NovaApp = window.NovaApp || {};
const app = window.NovaApp;

const state = {
  isSending: false,
  activeController: null,
  isInitialized: false
};

function byId(id) {
  return document.getElementById(id);
}

function getMessageInput() {
  return byId("messageInput");
}

function getSendBtn() {
  return byId("sendBtn");
}

function getStopBtn() {
  return byId("stopBtn");
}

function ensureAppState() {
  app.state = app.state || {};
  app.state.chats = Array.isArray(app.state.chats) ? app.state.chats : [];
  app.state.messagesByChatId =
    app.state.messagesByChatId && typeof app.state.messagesByChatId === "object"
      ? app.state.messagesByChatId
      : {};
  return app.state;
}

function ensureActiveChatId() {
  ensureAppState();

  if (typeof app.ensureActiveChat === "function") {
    const id = app.ensureActiveChat();
    if (id) return id;
  }

  if (app.state.activeChatId) {
    return app.state.activeChatId;
  }

  const newChatId = `chat_${Date.now()}`;
  const newChat = {
    id: newChatId,
    title: "New Chat",
    created_at: new Date().toISOString()
  };

  app.state.chats.unshift(newChat);
  app.state.messagesByChatId[newChatId] = [];
  app.state.activeChatId = newChatId;

  if (app.sidebar && typeof app.sidebar.render === "function") {
    app.sidebar.render();
  }

  return newChatId;
}

function getMessagesForChat(chatId) {
  ensureAppState();

  if (typeof app.getMessagesForChat === "function") {
    const result = app.getMessagesForChat(chatId);
    return Array.isArray(result) ? result : [];
  }

  return Array.isArray(app.state.messagesByChatId[chatId])
    ? app.state.messagesByChatId[chatId]
    : [];
}

function setMessagesForChat(chatId, messages) {
  ensureAppState();

  const safeMessages = Array.isArray(messages) ? messages : [];

  if (typeof app.setMessagesForChat === "function") {
    app.setMessagesForChat(chatId, safeMessages);
  } else {
    app.state.messagesByChatId[chatId] = safeMessages;
  }

  if (typeof app.renderApp === "function") {
    app.renderApp();
    return;
  }

  if (typeof app.renderMessages === "function") {
    app.renderMessages();
  }
}

function getMessageText() {
  const input = getMessageInput();
  if (!input) return "";
  return String(input.value || "").trim();
}

function clearMessageInput() {
  const input = getMessageInput();
  if (!input) return;
  input.value = "";
  input.style.height = "auto";
}

function autosizeInput() {
  const input = getMessageInput();
  if (!input) return;
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 220)}px`;
}

function syncSendingUi() {
  const sendBtn = getSendBtn();
  const stopBtn = getStopBtn();

  if (sendBtn) {
    sendBtn.disabled = state.isSending;
    sendBtn.setAttribute("aria-disabled", state.isSending ? "true" : "false");
  }

  if (stopBtn) {
    stopBtn.disabled = !state.isSending;
    stopBtn.setAttribute("aria-disabled", state.isSending ? "false" : "true");
  }

  document.body.classList.toggle("is-thinking", state.isSending);
  document.body.classList.toggle("is-streaming", state.isSending);
}

function finishSending() {
  state.isSending = false;
  state.activeController = null;
  syncSendingUi();
}

function isAbortError(error) {
  return error && (error.name === "AbortError" || String(error).toLowerCase().includes("abort"));
}

async function sendMessage() {
  const input = getMessageInput();
  const text = getMessageText();

  if (!input || !text || state.isSending) {
    return;
  }

  const chatId = ensureActiveChatId();
  const baseMessages = getMessagesForChat(chatId);

  const userMessage = {
    id: `msg_${Date.now()}`,
    role: "user",
    content: text,
    created_at: new Date().toISOString()
  };

  const assistantMessage = {
    id: `msg_${Date.now()}_assistant`,
    role: "assistant",
    content: "",
    created_at: new Date().toISOString()
  };

  let workingMessages = [...baseMessages, userMessage, assistantMessage];
  setMessagesForChat(chatId, workingMessages);

  clearMessageInput();
  autosizeInput();

  state.isSending = true;
  state.activeController = new AbortController();
  syncSendingUi();

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        chat_id: chatId,
        message: text,
        model: app.state?.selectedModel || "gpt-4.1-mini"
      }),
      signal: state.activeController.signal
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    if (!response.body) {
      throw new Error("Response body missing.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        const lines = part.split("\n");

        for (const rawLine of lines) {
          const line = rawLine.trim();
          if (!line.startsWith("data:")) {
            continue;
          }

          const payload = line.slice(5).trim();
          if (!payload) {
            continue;
          }

          if (payload === "[DONE]") {
            continue;
          }

          try {
            const data = JSON.parse(payload);

            if (data.type === "token") {
              assistantMessage.content += String(data.content || "");
              workingMessages = [...baseMessages, userMessage, assistantMessage];
              setMessagesForChat(chatId, workingMessages);
              continue;
            }

            if (data.type === "message" && data.content) {
              assistantMessage.content = String(data.content);
              workingMessages = [...baseMessages, userMessage, assistantMessage];
              setMessagesForChat(chatId, workingMessages);
              continue;
            }

            if (data.type === "error") {
              throw new Error(String(data.content || "Streaming error."));
            }
          } catch (parseError) {
            console.warn("Nova composer stream parse warning:", parseError);
          }
        }
      }
    }

    if (!assistantMessage.content.trim()) {
      assistantMessage.content = "Nova returned no content.";
      workingMessages = [...baseMessages, userMessage, assistantMessage];
      setMessagesForChat(chatId, workingMessages);
    }
  } catch (error) {
    if (isAbortError(error)) {
      if (!assistantMessage.content.trim()) {
        assistantMessage.content = "[Stopped]";
        workingMessages = [...baseMessages, userMessage, assistantMessage];
        setMessagesForChat(chatId, workingMessages);
      }
    } else {
      console.error("Nova send error:", error);
      assistantMessage.content = "Nova hit an error.";
      workingMessages = [...baseMessages, userMessage, assistantMessage];
      setMessagesForChat(chatId, workingMessages);
    }
  } finally {
    finishSending();
  }
}

function stopMessage() {
  if (!state.isSending) {
    finishSending();
    return;
  }

  if (state.activeController) {
    try {
      state.activeController.abort();
    } catch (error) {
      console.warn("Nova stop warning:", error);
    }
  }

  finishSending();
}

function bindButtons() {
  const sendBtn = getSendBtn();
  const stopBtn = getStopBtn();
  const input = getMessageInput();

  if (sendBtn && sendBtn.dataset.novaComposerBound !== "1") {
    sendBtn.dataset.novaComposerBound = "1";
    sendBtn.addEventListener("click", (event) => {
      event.preventDefault();
      sendMessage();
    });
  }

  if (stopBtn && stopBtn.dataset.novaComposerBound !== "1") {
    stopBtn.dataset.novaComposerBound = "1";
    stopBtn.addEventListener("click", (event) => {
      event.preventDefault();
      stopMessage();
    });
  }

  if (input && input.dataset.novaComposerKeyBound !== "1") {
    input.dataset.novaComposerKeyBound = "1";
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });
  }

  if (input && input.dataset.novaComposerInputBound !== "1") {
    input.dataset.novaComposerInputBound = "1";
    input.addEventListener("input", autosizeInput);
  }
}

function initComposer() {
  if (state.isInitialized) {
    syncSendingUi();
    autosizeInput();
    return;
  }

  bindButtons();
  autosizeInput();
  syncSendingUi();

  state.isInitialized = true;
  console.log("Nova composer loaded.");
}

app.sendMessage = sendMessage;
app.stopMessage = stopMessage;
app.composer = {
  state,
  initComposer,
  sendMessage,
  stopMessage
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initComposer, { once: true });
} else {
  initComposer();
}
})();