(() => {
"use strict";

if (window.NovaApp && window.NovaApp.api) {
  console.warn("Nova app-api already loaded.");
  return;
}

window.NovaApp = window.NovaApp || {};
const app = window.NovaApp;

async function parseJsonSafe(response) {
  const text = await response.text();

  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text);
  } catch (error) {
    console.warn("Failed to parse JSON response.", error);
    return {
      detail: text
    };
  }
}

function getErrorMessage(payload, fallbackMessage) {
  if (!payload) {
    return fallbackMessage || "Request failed.";
  }

  if (typeof payload === "string") {
    return payload;
  }

  if (typeof payload.detail === "string" && payload.detail.trim()) {
    return payload.detail.trim();
  }

  if (typeof payload.error === "string" && payload.error.trim()) {
    return payload.error.trim();
  }

  if (typeof payload.message === "string" && payload.message.trim()) {
    return payload.message.trim();
  }

  return fallbackMessage || "Request failed.";
}

async function request(url, options = {}) {
  const config = {
    method: options.method || "GET",
    headers: {
      ...(options.headers || {})
    },
    credentials: "same-origin"
  };

  if (options.body !== undefined) {
    config.body = options.body;
  }

  if (options.json !== undefined) {
    config.body = JSON.stringify(options.json);
    config.headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, config);
  const payload = await parseJsonSafe(response);

  if (!response.ok) {
    const message = getErrorMessage(payload, `Request failed: ${response.status}`);
    throw new Error(message);
  }

  return payload;
}

async function getAuthStatus() {
  return request("/api/auth/status");
}

async function getModels() {
  return request("/api/models");
}

async function getChats() {
  const payload = await request("/api/chats");
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.chats)) return payload.chats;
  return [];
}

async function createChat(title = "New Chat") {
  const payload = await request("/api/chats", {
    method: "POST",
    json: { title }
  });

  if (payload && payload.chat) return payload.chat;
  return payload;
}

async function getChat(chatId) {
  if (!chatId) {
    throw new Error("Chat ID is required.");
  }

  return request(`/api/chats/${encodeURIComponent(chatId)}`);
}

async function getMessages(chatId) {
  if (!chatId) {
    throw new Error("Chat ID is required.");
  }

  const payload = await request(`/api/chats/${encodeURIComponent(chatId)}/messages`);
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.messages)) return payload.messages;
  return [];
}

async function renameChat(chatId, title) {
  if (!chatId) {
    throw new Error("Chat ID is required.");
  }

  const payload = await request(`/api/chats/${encodeURIComponent(chatId)}`, {
    method: "PATCH",
    json: { title: String(title || "").trim() }
  });

  if (payload && payload.chat) return payload.chat;
  return payload;
}

async function deleteChat(chatId) {
  if (!chatId) {
    throw new Error("Chat ID is required.");
  }

  return request(`/api/chats/${encodeURIComponent(chatId)}`, {
    method: "DELETE"
  });
}

async function exportChat(chatId) {
  if (!chatId) {
    throw new Error("Chat ID is required.");
  }

  const response = await fetch(`/api/chats/${encodeURIComponent(chatId)}/export`, {
    method: "GET",
    credentials: "same-origin"
  });

  if (!response.ok) {
    const payload = await parseJsonSafe(response);
    const message = getErrorMessage(payload, `Export failed: ${response.status}`);
    throw new Error(message);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  let filename = `nova-chat-${chatId}.json`;

  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  const basicMatch = disposition.match(/filename="?([^"]+)"?/i);

  if (utf8Match && utf8Match[1]) {
    filename = decodeURIComponent(utf8Match[1]);
  } else if (basicMatch && basicMatch[1]) {
    filename = basicMatch[1];
  }

  return { blob, filename };
}

async function setActiveModel(model) {
  const payload = await request("/api/models/select", {
    method: "POST",
    json: { model: String(model || "").trim() }
  });

  return payload;
}

async function getMemory() {
  const payload = await request("/api/memory");
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.items)) return payload.items;
  if (Array.isArray(payload.memories)) return payload.memories;
  return [];
}

async function clearMemory() {
  return request("/api/memory", {
    method: "DELETE"
  });
}

async function uploadFiles(files) {
  const list = Array.isArray(files) ? files : Array.from(files || []);
  if (!list.length) {
    return [];
  }

  const formData = new FormData();
  for (const file of list) {
    formData.append("files", file);
  }

  const response = await fetch("/api/files/upload", {
    method: "POST",
    body: formData,
    credentials: "same-origin"
  });

  const payload = await parseJsonSafe(response);

  if (!response.ok) {
    const message = getErrorMessage(payload, `Upload failed: ${response.status}`);
    throw new Error(message);
  }

  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.files)) return payload.files;
  return [];
}

async function hydrateChatsIntoState() {
  const chats = await getChats();

  if (typeof app.setChats === "function") {
    app.setChats(chats);
  } else if (app.state) {
    app.state.chats = chats;
  }

  return chats;
}

async function hydrateMessagesIntoState(chatId) {
  const messages = await getMessages(chatId);

  if (typeof app.setMessages === "function") {
    app.setMessages(chatId, messages);
  } else if (app.state) {
    app.state.messagesByChatId = app.state.messagesByChatId || {};
    app.state.messagesByChatId[chatId] = messages;
  }

  return messages;
}

async function hydrateModelsIntoState() {
  const modelsPayload = await getModels();
  const models = Array.isArray(modelsPayload)
    ? modelsPayload
    : Array.isArray(modelsPayload.models)
      ? modelsPayload.models
      : [];

  if (typeof app.setModels === "function") {
    app.setModels(models);
  } else if (app.state) {
    app.state.models = models;
  }

  const selected =
    modelsPayload?.selected_model ||
    modelsPayload?.active_model ||
    app.state?.selectedModel ||
    "gpt-4.1-mini";

  if (typeof app.setSelectedModel === "function") {
    app.setSelectedModel(selected);
  } else if (app.state) {
    app.state.selectedModel = selected;
  }

  return {
    models,
    selectedModel: selected
  };
}

app.api = {
  request,
  getAuthStatus,
  getModels,
  getChats,
  createChat,
  getChat,
  getMessages,
  renameChat,
  deleteChat,
  exportChat,
  setActiveModel,
  getMemory,
  clearMemory,
  uploadFiles,
  hydrateChatsIntoState,
  hydrateMessagesIntoState,
  hydrateModelsIntoState
};

})();