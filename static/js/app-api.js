(() => {
"use strict";

window.NovaApp = window.NovaApp || {};

const existingApi =
  window.NovaApp.api &&
  typeof window.NovaApp.api === "object"
    ? window.NovaApp.api
    : {};

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
    const message = getErrorMessage(
      payload,
      `Request failed: ${response.status}`
    );
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

  const payload = await request(
    `/api/chats/${encodeURIComponent(chatId)}/messages`
  );

  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload.messages)) return payload.messages;
  return [];
}

async function renameChat(chatId, title) {
  if (!chatId) {
    throw new Error("Chat ID is required.");
  }

  const payload = await request(
    `/api/chats/${encodeURIComponent(chatId)}`,
    {
      method: "PATCH",
      json: { title: String(title || "").trim() }
    }
  );

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

  const response = await fetch(
    `/api/chats/${encodeURIComponent(chatId)}/export`,
    {
      method: "GET",
      credentials: "same-origin"
    }
  );

  if (!response.ok) {
    const payload = await parseJsonSafe(response);
    const message = getErrorMessage(
      payload,
      `Export failed: ${response.status}`
    );
    throw new Error(message);
  }

  const blob = await response.blob();
  const disposition =
    response.headers.get("Content-Disposition") || "";

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
  return request("/api/models/select", {
    method: "POST",
    json: { model: String(model || "").trim() }
  });
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
  const list = Array.isArray(files)
    ? files
    : Array.from(files || []);

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
    const message = getErrorMessage(
      payload,
      `Upload failed: ${response.status}`
    );
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
    app.state.messagesByChatId =
      app.state.messagesByChatId || {};

    app.state.messagesByChatId[chatId] = messages;
  }

  return messages;
}

async function hydrateModelsIntoState() {
  const modelsPayload = await getModels();

  const rawModels =
    Array.isArray(modelsPayload?.model_details)
      ? modelsPayload.model_details
      : Array.isArray(modelsPayload)
        ? modelsPayload
        : Array.isArray(modelsPayload?.models)
          ? modelsPayload.models
          : [];

  // Use the billing tiers supplied by the live model API.
  const costTierOrder = {
    cheapest: 0,
    cheap: 1,
    standard: 2,
    balanced: 3,
    advanced: 4,
    premium: 5,
    pro: 6,
    maximum: 7
  };

  const models = rawModels
    .map((model) => {
      if (typeof model === "string") {
        return {
          value: model,
          label: model,
          category: "General",
          billing_tier: "unknown",
          cost_tier: "Cost unknown"
        };
      }

      const value =
        model?.value ||
        model?.id ||
        model?.name ||
        "";

      const description = String(model?.description || "").toLowerCase();
      const modelName = String(model?.label || model?.name || value);
      const categorySet = new Set();

      if (/fast|speed|efficient|everyday|routine|high-throughput|simple/.test(description)) {
        categorySet.add("Fast");
      }

      if (/coding|code|developer|software/.test(description)) {
        categorySet.add("Coding");
      }

      if (/reasoning|complex|problem solving|difficult|precision|multi-step/.test(description)) {
        categorySet.add("Reasoning");
      }

      if (/multimodal|image|audio|video|vision/.test(description)) {
        categorySet.add("Multimodal");
      }

      if (/agent|agentic|execution/.test(description)) {
        categorySet.add("Agentic");
      }

      if (/general|everyday|general-purpose/.test(description)) {
        categorySet.add("General");
      }

      if (categorySet.size === 0) {
        categorySet.add("General");
      }

      const category = [...categorySet].join(", ");
      const billingTier = String(model?.billing_tier || "unknown").toLowerCase();

      const costTierLabels = {
        cheapest: "CHEAPEST",
        cheap: "CHEAP",
        standard: "STANDARD",
        balanced: "BALANCED",
        advanced: "ADVANCED",
        premium: "PREMIUM",
        pro: "PRO",
        maximum: "MAXIMUM"
      };

      const costTier = costTierLabels[billingTier] || "COST UNKNOWN";

      return {
        ...model,
        value,
        category,
        billing_tier: billingTier,
        cost_tier: costTier,
        label: `${modelName} | ${category} | ${costTier}`
      };
    })
    .sort((a, b) => {
      const aTier = costTierOrder[a.billing_tier] ?? 99;
      const bTier = costTierOrder[b.billing_tier] ?? 99;

      return aTier - bTier;
    });

  // Prefer the user's saved browser selection when it still exists.
  let savedModel = "";

  try {
    savedModel =
      localStorage.getItem("nova_selected_model") ||
      "";
  } catch (_error) {
    savedModel = "";
  }

  const savedModelExists = models.some(
    (model) => String(model.value) === String(savedModel)
  );

  const currentModel = app.state?.selectedModel || "";

  const currentModelExists = models.some(
    (model) => String(model.value) === String(currentModel)
  );

  const selected =
    (savedModelExists ? savedModel : "") ||
    (currentModelExists ? currentModel : "") ||
    modelsPayload?.selected_model ||
    modelsPayload?.active_model ||
    modelsPayload?.default_model ||
    models[0]?.value ||
    "";

  if (typeof app.setModels === "function") {
    app.setModels(models);
  } else if (app.state) {
    app.state.models = models;
  }

  if (typeof app.setSelectedModel === "function") {
    app.setSelectedModel(selected);
  } else if (app.state) {
    app.state.selectedModel = selected;
  }

  const modelSelect = document.getElementById("modelSelect");

  if (modelSelect) {
    modelSelect.innerHTML = models
      .map((model) => {
        const value = String(model.value)
          .replace(/&/g, "&amp;")
          .replace(/"/g, "&quot;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;");

        const label = String(model.label)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;");

        return `<option value="${value}">${label}</option>`;
      })
      .join("");

    modelSelect.value = selected;

    console.log(
      "[NOVA MODELS] rendered cheapest to most expensive",
      [...modelSelect.options].map(
        (option) =>
          `${option.textContent.trim()} [${option.value}]`
      )
    );
  }

  return {
    models,
    selectedModel: selected
  };
}

app.api = {
  ...existingApi,
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