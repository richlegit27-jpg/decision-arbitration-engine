(() => {
"use strict";

if (window.__novaRenderLoaded) {
  console.warn("Nova renderer already loaded.");
  return;
}
window.__novaRenderLoaded = true;

window.NovaApp = window.NovaApp || {};
const app = window.NovaApp;

function byId(id) {
  return document.getElementById(id);
}

function getRootState() {
  app.state = app.state || {};
  app.state.chats = Array.isArray(app.state.chats) ? app.state.chats : [];
  app.state.messagesByChatId =
    app.state.messagesByChatId && typeof app.state.messagesByChatId === "object"
      ? app.state.messagesByChatId
      : {};
  return app.state;
}

function getChatContainer() {
  return byId("chatMessages") || byId("messages") || byId("chatContainer");
}

function normalizeText(value) {
  return String(value ?? "").trim();
}

function normalizeRole(value) {
  const role = String(value ?? "").trim().toLowerCase();
  if (role === "user") return "user";
  if (role === "assistant") return "assistant";
  if (role === "system") return "system";
  return "assistant";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function ensureActiveChat() {
  const state = getRootState();

  if (state.activeChatId && state.messagesByChatId[state.activeChatId]) {
    return state.activeChatId;
  }

  if (state.activeChatId && !state.messagesByChatId[state.activeChatId]) {
    state.messagesByChatId[state.activeChatId] = [];
    return state.activeChatId;
  }

  if (state.chats.length > 0) {
    const firstChat = state.chats[0];
    if (firstChat && firstChat.id) {
      state.activeChatId = firstChat.id;
      if (!Array.isArray(state.messagesByChatId[firstChat.id])) {
        state.messagesByChatId[firstChat.id] = [];
      }
      return state.activeChatId;
    }
  }

  const newChatId = `chat_${Date.now()}`;
  const newChat = {
    id: newChatId,
    title: "New Chat",
    created_at: new Date().toISOString()
  };

  state.chats.unshift(newChat);
  state.messagesByChatId[newChatId] = [];
  state.activeChatId = newChatId;

  return newChatId;
}

function getActiveChatId() {
  const state = getRootState();
  return state.activeChatId || null;
}

function setActiveChat(chatId) {
  const state = getRootState();
  const normalizedId = String(chatId || "").trim();
  if (!normalizedId) return null;

  state.activeChatId = normalizedId;

  if (!Array.isArray(state.messagesByChatId[normalizedId])) {
    state.messagesByChatId[normalizedId] = [];
  }

  return normalizedId;
}

function getMessagesForChat(chatId) {
  const state = getRootState();
  const normalizedId = String(chatId || "").trim();
  if (!normalizedId) return [];
  const messages = state.messagesByChatId[normalizedId];
  return Array.isArray(messages) ? messages : [];
}

function setMessagesForChat(chatId, messages) {
  const state = getRootState();
  const normalizedId = String(chatId || "").trim();
  if (!normalizedId) return;

  state.messagesByChatId[normalizedId] = Array.isArray(messages) ? messages : [];

  if (!state.chats.some((chat) => chat && chat.id === normalizedId)) {
    state.chats.unshift({
      id: normalizedId,
      title: "New Chat",
      created_at: new Date().toISOString()
    });
  }

  const nonSystemMessages = state.messagesByChatId[normalizedId].filter(
    (msg) => normalizeRole(msg?.role) !== "system"
  );

  const firstUserMessage = nonSystemMessages.find(
    (msg) => normalizeRole(msg?.role) === "user" && normalizeText(msg?.content)
  );

  const chat = state.chats.find((item) => item && item.id === normalizedId);
  if (chat && (!chat.title || chat.title === "New Chat") && firstUserMessage) {
    const title = normalizeText(firstUserMessage.content).slice(0, 60);
    chat.title = title || "New Chat";
  }

  dispatchNovaEvent("nova:messages-updated", { chatId: normalizedId });
}

function getMessagesForActiveChat() {
  const chatId = ensureActiveChat();
  return getMessagesForChat(chatId);
}

function dispatchNovaEvent(name, detail = {}) {
  try {
    document.dispatchEvent(new CustomEvent(name, { detail }));
  } catch (error) {
    console.warn(`Nova event warning: ${name}`, error);
  }
}

function scrollToBottom(force = true) {
  const container = getChatContainer();
  if (!container) return;
  if (!force) return;
  container.scrollTop = container.scrollHeight;
}

function buildMarkdownHtml(contentValue) {
  const text = String(contentValue || "");
  if (!text.trim()) {
    return "";
  }

  if (window.marked && typeof window.marked.parse === "function") {
    try {
      return window.marked.parse(text);
    } catch (error) {
      console.warn("Nova markdown warning:", error);
      return escapeHtml(text).replace(/\n/g, "<br>");
    }
  }

  return escapeHtml(text).replace(/\n/g, "<br>");
}

function createMessageBubble(msg) {
  if (!msg || typeof msg !== "object") return null;

  const roleValue = normalizeRole(msg.role);
  const contentValue = normalizeText(msg.content);
  const imageBase64 = String(msg.image_base64 || "").trim();

  if (!contentValue && !imageBase64) {
    return null;
  }

  const bubble = document.createElement("div");
  bubble.className = `message-bubble ${roleValue}`;
  bubble.dataset.role = roleValue;
  bubble.dataset.messageId = String(msg.id || "");

  const role = document.createElement("div");
  role.className = "message-role";
  role.textContent = roleValue;

  const content = document.createElement("div");
  content.className = "message-content";

  if (contentValue) {
    content.innerHTML = buildMarkdownHtml(contentValue);
  }

  bubble.appendChild(role);
  bubble.appendChild(content);

  if (imageBase64) {
    const image = document.createElement("img");
    image.alt = "Generated image";
    image.src = `data:image/png;base64,${imageBase64}`;
    image.className = "message-image";
    bubble.appendChild(image);
  }

  return bubble;
}

function renderMessage(msg) {
  const container = getChatContainer();
  if (!container) return;

  const bubble = createMessageBubble(msg);
  if (!bubble) return;

  container.appendChild(bubble);
}

function renderMessagesList(messages, options = {}) {
  const container = getChatContainer();
  if (!container) return;

  container.innerHTML = "";

  if (!Array.isArray(messages) || !messages.length) {
    const empty = document.createElement("div");
    empty.className = "messages-empty";
    empty.textContent = "Start the conversation.";
    container.appendChild(empty);
    return;
  }

  for (const msg of messages) {
    renderMessage(msg);
  }

  scrollToBottom(options.forceScroll !== false);
}

function renderMessages(options = {}) {
  const messages = getMessagesForActiveChat();
  renderMessagesList(messages, options);
}

function updateChatMeta() {
  const state = getRootState();
  const chatId = getActiveChatId();
  const chats = Array.isArray(state.chats) ? state.chats : [];
  const currentChat = chats.find((chat) => chat && chat.id === chatId) || null;
  const messages = getMessagesForActiveChat();

  const chatTitle = byId("chatTitle");
  const chatSubtitle = byId("chatSubtitle");
  const chatCountMeta = byId("chatCountMeta");

  if (chatTitle) {
    chatTitle.textContent = currentChat?.title || "New Chat";
  }

  if (chatSubtitle) {
    const count = Array.isArray(messages) ? messages.length : 0;
    chatSubtitle.textContent = `${count} message${count === 1 ? "" : "s"}`;
  }

  if (chatCountMeta) {
    chatCountMeta.textContent = String(chats.length);
  }
}

function renderApp(options = {}) {
  renderMessages(options);
  updateChatMeta();

  if (app.sidebar && typeof app.sidebar.render === "function") {
    app.sidebar.render();
  }
}

function createNewChat() {
  const state = getRootState();

  const newChatId = `chat_${Date.now()}`;
  const newChat = {
    id: newChatId,
    title: "New Chat",
    created_at: new Date().toISOString()
  };

  state.chats.unshift(newChat);
  state.messagesByChatId[newChatId] = [];
  state.activeChatId = newChatId;

  dispatchNovaEvent("nova:chat-changed", { chatId: newChatId });
  renderApp({ forceScroll: false });

  return newChatId;
}

app.ensureActiveChat = ensureActiveChat;
app.getActiveChatId = getActiveChatId;
app.setActiveChat = setActiveChat;
app.getMessagesForChat = getMessagesForChat;
app.setMessagesForChat = setMessagesForChat;
app.getMessagesForActiveChat = getMessagesForActiveChat;
app.createNewChat = createNewChat;

app.render = app.render || {};
app.render.message = renderMessage;
app.render.messages = renderMessagesList;
app.render.renderMessages = renderMessages;
app.render.renderApp = renderApp;

app.renderMessages = renderMessages;
app.renderApp = renderApp;
app.updateChatMeta = updateChatMeta;

document.addEventListener("nova:messages-updated", () => {
  renderApp({ forceScroll: true });
});

document.addEventListener("nova:chat-changed", (event) => {
  const chatId = event?.detail?.chatId;
  if (chatId) {
    setActiveChat(chatId);
  }
  renderApp({ forceScroll: true });
});

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    ensureActiveChat();
    renderApp({ forceScroll: false });
  }, { once: true });
} else {
  ensureActiveChat();
  renderApp({ forceScroll: false });
}

console.log("Nova renderer loaded.");
})();