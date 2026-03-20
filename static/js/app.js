(() => {
"use strict";

const STORAGE_KEY = "nova_active_chat_id";

const state = {
  chats: [],
  activeChatId: null,
  messagesByChatId: {},
  attachedFiles: [],
  models: [
    { value: "nova-default", label: "Nova Default" },
    { value: "nova-fast", label: "Nova Fast" },
    { value: "nova-precise", label: "Nova Precise" }
  ],
  selectedModel: "nova-default",
  isLoadingChat: false
};

const el = {};

function byId(id){
  return document.getElementById(id);
}

function escapeHtml(value){
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function notifyError(message){
  if(window.NovaToast && typeof window.NovaToast.error === "function"){
    window.NovaToast.error(message || "Something went wrong.");
    return;
  }
  alert(message || "Something went wrong.");
}

function formatCount(count){
  return `${count} message${count === 1 ? "" : "s"}`;
}

function formatTime(value){
  if(!value) return "";
  const date = new Date(value);
  if(Number.isNaN(date.getTime())) return "";
  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function extractChat(data){
  if(!data) return null;
  if(data.item && typeof data.item === "object") return data.item;
  if(data.chat && typeof data.chat === "object") return data.chat;
  if(data.id) return data;
  return null;
}

function extractChats(data){
  if(Array.isArray(data?.items)) return data.items;
  if(Array.isArray(data?.chats)) return data.chats;
  if(Array.isArray(data)) return data;
  return [];
}

function extractMessages(data){
  if(Array.isArray(data?.messages)) return data.messages;
  if(Array.isArray(data?.items)) return data.items;
  if(Array.isArray(data)) return data;
  return [];
}

async function apiFetch(url, options = {}){
  const response = await fetch(url, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  if(response.status === 401){
    window.location.href = "/login";
    throw new Error("Not authenticated");
  }

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await response.json().catch(() => ({})) : await response.text();

  if(!response.ok){
    const detail =
      (isJson && data && (data.detail || data.message || data.error)) ||
      (typeof data === "string" && data) ||
      `Request failed with status ${response.status}`;

    throw new Error(detail);
  }

  return data;
}

function cacheElements(){
  el.chatMessages = byId("chatMessages");
  el.chatList = byId("chatList");
  el.sendBtn = byId("sendBtn");
  el.stopBtn = byId("stopBtn");
  el.modelSelect = byId("modelSelect");
  el.renameChatBtn = byId("renameChatBtn");
  el.activeChatTitleText = byId("activeChatTitleText");
  el.activeChatMeta = byId("activeChatMeta");
  el.messageInput = byId("messageInput");
  el.newChatBtn = byId("btnNewChat");
  el.clearChatBtn = byId("btnClearChat");
  el.deleteChatBtn = byId("btnDeleteChat");
  el.exportChatBtn = byId("btnExportChat");
  el.attachedFilesBar = byId("attachedFilesBar");
  el.fileInput = byId("fileInput");
  el.attachBtn = byId("attachBtn");
}

function saveActiveChatId(){
  if(state.activeChatId){
    localStorage.setItem(STORAGE_KEY, String(state.activeChatId));
  }else{
    localStorage.removeItem(STORAGE_KEY);
  }
}

function loadActiveChatId(){
  const raw = localStorage.getItem(STORAGE_KEY);
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function getActiveChat(){
  if(!state.activeChatId) return null;
  return state.chats.find(chat => Number(chat.id) === Number(state.activeChatId)) || null;
}

function getActiveMessages(){
  const activeId = state.activeChatId;
  if(!activeId) return [];
  return Array.isArray(state.messagesByChatId[activeId]) ? state.messagesByChatId[activeId] : [];
}

function setActiveChatId(chatId){
  state.activeChatId = chatId ? Number(chatId) : null;
  saveActiveChatId();
  renderChatList();
  renderActiveChatCard();
  renderMessages();
}

function autosizeComposer(){
  if(!el.messageInput) return;
  el.messageInput.style.height = "auto";
  el.messageInput.style.height = `${Math.min(el.messageInput.scrollHeight, 220)}px`;
}

function renderModelSelect(){
  if(!el.modelSelect) return;

  el.modelSelect.innerHTML = state.models
    .map(model => `<option value="${escapeHtml(model.value)}">${escapeHtml(model.label)}</option>`)
    .join("");

  el.modelSelect.value = state.selectedModel;
}

function renderAttachedFiles(){
  if(!el.attachedFilesBar) return;

  if(!state.attachedFiles.length){
    el.attachedFilesBar.innerHTML = "";
    el.attachedFilesBar.style.display = "none";
    return;
  }

  el.attachedFilesBar.style.display = "flex";
  el.attachedFilesBar.innerHTML = state.attachedFiles.map((file, index) => `
    <div class="mini-chip" data-file-index="${index}">
      <span>📎 ${escapeHtml(file.name)}</span>
      <button
        type="button"
        class="icon-btn"
        data-remove-file="${index}"
        title="Remove file"
        style="width:24px;height:24px;min-height:24px;padding:0;"
      >✕</button>
    </div>
  `).join("");
}

function renderChatList(){
  if(!el.chatList) return;

  if(!state.chats.length){
    el.chatList.innerHTML = `
      <div class="chat-list-empty">
        <div class="card-subtext">No chats yet.</div>
      </div>
    `;
    return;
  }

  el.chatList.innerHTML = state.chats.map(chat => {
    const isActive = Number(chat.id) === Number(state.activeChatId);
    const messageCount = Number(chat.message_count || 0);

    return `
      <button
        type="button"
        class="chat-list-item ${isActive ? "active" : ""}"
        data-chat-id="${chat.id}"
      >
        <div class="chat-list-item-title">${escapeHtml(chat.title || "Untitled chat")}</div>
        <div class="chat-list-item-meta">${escapeHtml(formatCount(messageCount))}</div>
      </button>
    `;
  }).join("");
}

function renderActiveChatCard(){
  const activeChat = getActiveChat();

  if(el.activeChatTitleText){
    el.activeChatTitleText.textContent = activeChat ? (activeChat.title || "Untitled chat") : "No active chat";
  }

  if(el.activeChatMeta){
    if(!activeChat){
      el.activeChatMeta.textContent = "0 messages";
    }else{
      const messageCount = getActiveMessages().length || Number(activeChat.message_count || 0);
      const updated = activeChat.updated_at ? ` • Updated ${formatTime(activeChat.updated_at)}` : "";
      el.activeChatMeta.textContent = `${formatCount(messageCount)}${updated}`;
    }
  }

  if(el.renameChatBtn){
    el.renameChatBtn.disabled = !activeChat;
  }

  if(el.clearChatBtn){
    el.clearChatBtn.disabled = !activeChat;
  }

  if(el.deleteChatBtn){
    el.deleteChatBtn.disabled = !activeChat;
  }

  if(el.exportChatBtn){
    el.exportChatBtn.disabled = !activeChat;
  }
}

function renderMessages(){
  if(!el.chatMessages) return;

  const messages = getActiveMessages();

  if(!state.activeChatId){
    el.chatMessages.innerHTML = `
      <div class="empty-state-card fade-in">
        <div class="empty-icon">💬</div>
        <h3>No active chat</h3>
        <p>Create a new chat to get moving.</p>
      </div>
    `;
    return;
  }

  if(!messages.length){
    el.chatMessages.innerHTML = `
      <div class="empty-state-card fade-in">
        <div class="empty-icon">⚡</div>
        <h3>New chat ready</h3>
        <p>Type a message to start the conversation.</p>
      </div>
    `;
    return;
  }

  el.chatMessages.innerHTML = messages.map(message => {
    const role = String(message.role || "assistant").toLowerCase();
    const roleLabel = role === "user" ? "You" : role === "system" ? "System" : "Nova";
    const safeContent = escapeHtml(message.content || "").replaceAll("\n", "<br>");

    return `
      <div class="chat-message ${role === "user" ? "user" : "assistant"} fade-in">
        <div class="chat-message-header">
          <strong>${escapeHtml(roleLabel)}</strong>
          <span class="chat-message-time">${escapeHtml(formatTime(message.created_at))}</span>
        </div>
        <div class="chat-message-body">${safeContent}</div>
      </div>
    `;
  }).join("");

  el.chatMessages.scrollTop = el.chatMessages.scrollHeight;
}

async function loadChats(){
  const data = await apiFetch("/api/chats");
  state.chats = extractChats(data);

  if(!state.chats.length){
    setActiveChatId(null);
    return;
  }

  const savedId = loadActiveChatId();
  const hasSaved = savedId && state.chats.some(chat => Number(chat.id) === Number(savedId));

  if(hasSaved){
    state.activeChatId = Number(savedId);
  }else if(state.activeChatId && state.chats.some(chat => Number(chat.id) === Number(state.activeChatId))){
    state.activeChatId = Number(state.activeChatId);
  }else{
    state.activeChatId = Number(state.chats[0].id);
  }

  saveActiveChatId();
}

async function loadChat(chatId){
  if(!chatId) return;

  state.isLoadingChat = true;
  renderMessages();

  try{
    const data = await apiFetch(`/api/chats/${chatId}`);
    const chat = extractChat(data);
    const messages = extractMessages(data);

    if(chat){
      const existingIndex = state.chats.findIndex(item => Number(item.id) === Number(chat.id));
      const mergedChat = {
        ...chat,
        message_count: messages.length
      };

      if(existingIndex >= 0){
        state.chats[existingIndex] = { ...state.chats[existingIndex], ...mergedChat };
      }else{
        state.chats.unshift(mergedChat);
      }

      state.messagesByChatId[chat.id] = messages;
      sortChatsInPlace();
      setActiveChatId(chat.id);
    }
  }finally{
    state.isLoadingChat = false;
    renderChatList();
    renderActiveChatCard();
    renderMessages();
  }
}

function sortChatsInPlace(){
  state.chats.sort((a, b) => {
    const aTime = new Date(a.updated_at || a.created_at || 0).getTime();
    const bTime = new Date(b.updated_at || b.created_at || 0).getTime();
    return bTime - aTime || Number(b.id) - Number(a.id);
  });
}

async function createChat(title = "New chat"){
  await apiFetch("/api/chats", {
    method: "POST",
    body: JSON.stringify({ title })
  });

  await loadChats();

  if(!state.chats.length){
    throw new Error("Chat list did not refresh after create.");
  }

  const newestChat = state.chats[0];
  if(!newestChat || !newestChat.id){
    throw new Error("Newest chat was missing after create.");
  }

  state.messagesByChatId[newestChat.id] = Array.isArray(state.messagesByChatId[newestChat.id])
    ? state.messagesByChatId[newestChat.id]
    : [];

  setActiveChatId(newestChat.id);
  await loadChat(newestChat.id);
  return newestChat;
}

async function ensureActiveChat(){
  const active = getActiveChat();
  if(active) return active;
  return await createChat("New chat");
}

async function renameActiveChat(){
  const active = getActiveChat();
  if(!active) return;

  const nextTitle = window.prompt("Rename chat:", active.title || "Untitled chat");
  if(nextTitle === null) return;

  const data = await apiFetch(`/api/chats/${active.id}`, {
    method: "PATCH",
    body: JSON.stringify({ title: nextTitle })
  });

  const updated = extractChat(data);
  if(!updated) return;

  const index = state.chats.findIndex(chat => Number(chat.id) === Number(updated.id));
  if(index >= 0){
    state.chats[index] = {
      ...state.chats[index],
      ...updated,
      message_count: getActiveMessages().length
    };
  }

  sortChatsInPlace();
  renderChatList();
  renderActiveChatCard();
}

async function clearActiveChat(){
  const active = getActiveChat();
  if(!active) return;

  const ok = window.confirm(`Clear all messages in "${active.title}"?`);
  if(!ok) return;

  await apiFetch(`/api/chats/${active.id}/messages`, {
    method: "DELETE"
  });

  state.messagesByChatId[active.id] = [];

  const index = state.chats.findIndex(chat => Number(chat.id) === Number(active.id));
  if(index >= 0){
    state.chats[index] = {
      ...state.chats[index],
      message_count: 0,
      updated_at: new Date().toISOString()
    };
  }

  sortChatsInPlace();
  renderChatList();
  renderActiveChatCard();
  renderMessages();
}

async function deleteActiveChat(){
  const active = getActiveChat();
  if(!active) return;

  const ok = window.confirm(`Delete "${active.title}"?`);
  if(!ok) return;

  await apiFetch(`/api/chats/${active.id}`, {
    method: "DELETE"
  });

  delete state.messagesByChatId[active.id];
  state.chats = state.chats.filter(chat => Number(chat.id) !== Number(active.id));

  if(state.chats.length){
    setActiveChatId(state.chats[0].id);
    await loadChat(state.chats[0].id);
  }else{
    setActiveChatId(null);
  }

  renderChatList();
  renderActiveChatCard();
  renderMessages();
}

function exportActiveChat(){
  const active = getActiveChat();
  if(!active) return;

  const messages = getActiveMessages();
  const lines = [
    `Title: ${active.title || "Untitled chat"}`,
    `Exported: ${new Date().toLocaleString()}`,
    ""
  ];

  for(const message of messages){
    const role = String(message.role || "assistant").toUpperCase();
    const time = formatTime(message.created_at);
    lines.push(`[${role}] ${time}`);
    lines.push(message.content || "");
    lines.push("");
  }

  const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const safeName = String(active.title || "nova-chat").replace(/[^\w\-]+/g, "_");

  link.href = url;
  link.download = `${safeName}.txt`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function bindEvents(){
  if(el.newChatBtn){
    el.newChatBtn.addEventListener("click", async () => {
      try{
        await createChat("New chat");
        if(el.messageInput){
          el.messageInput.focus();
        }
      }catch(error){
        console.error(error);
        notifyError(error.message || "Could not create chat.");
      }
    });
  }

  if(el.renameChatBtn){
    el.renameChatBtn.addEventListener("click", async () => {
      try{
        await renameActiveChat();
      }catch(error){
        console.error(error);
        notifyError(error.message || "Could not rename chat.");
      }
    });
  }

  if(el.clearChatBtn){
    el.clearChatBtn.addEventListener("click", async () => {
      try{
        await clearActiveChat();
      }catch(error){
        console.error(error);
        notifyError(error.message || "Could not clear chat.");
      }
    });
  }

  if(el.deleteChatBtn){
    el.deleteChatBtn.addEventListener("click", async () => {
      try{
        await deleteActiveChat();
      }catch(error){
        console.error(error);
        notifyError(error.message || "Could not delete chat.");
      }
    });
  }

  if(el.exportChatBtn){
    el.exportChatBtn.addEventListener("click", () => {
      try{
        exportActiveChat();
      }catch(error){
        console.error(error);
        notifyError(error.message || "Could not export chat.");
      }
    });
  }

  if(el.chatList){
    el.chatList.addEventListener("click", async (event) => {
      const button = event.target.closest("[data-chat-id]");
      if(!button) return;

      const chatId = Number(button.getAttribute("data-chat-id"));
      if(!chatId) return;

      try{
        await loadChat(chatId);
      }catch(error){
        console.error(error);
        notifyError(error.message || "Could not load chat.");
      }
    });
  }

  if(el.modelSelect){
    el.modelSelect.addEventListener("change", () => {
      state.selectedModel = el.modelSelect.value || "nova-default";
    });
  }

  if(el.attachBtn && el.fileInput){
    el.attachBtn.addEventListener("click", () => {
      el.fileInput.click();
    });

    el.fileInput.addEventListener("change", () => {
      const files = Array.from(el.fileInput.files || []);
      state.attachedFiles = files;
      renderAttachedFiles();
    });
  }

  if(el.attachedFilesBar){
    el.attachedFilesBar.addEventListener("click", (event) => {
      const removeBtn = event.target.closest("[data-remove-file]");
      if(!removeBtn) return;

      const index = Number(removeBtn.getAttribute("data-remove-file"));
      if(!Number.isFinite(index)) return;

      state.attachedFiles.splice(index, 1);

      if(el.fileInput){
        const transfer = new DataTransfer();
        for(const file of state.attachedFiles){
          transfer.items.add(file);
        }
        el.fileInput.files = transfer.files;
      }

      renderAttachedFiles();
    });
  }

  if(el.messageInput){
    el.messageInput.addEventListener("input", autosizeComposer);
  }

  window.addEventListener("nova:chat-created", (event) => {
    const detail = event.detail || {};
    const chat = extractChat(detail.chat || detail);

    if(!chat || !chat.id) return;

    state.messagesByChatId[chat.id] = Array.isArray(detail.messages) ? detail.messages : [];
    const existingIndex = state.chats.findIndex(item => Number(item.id) === Number(chat.id));

    if(existingIndex >= 0){
      state.chats[existingIndex] = {
        ...state.chats[existingIndex],
        ...chat,
        message_count: state.messagesByChatId[chat.id].length
      };
    }else{
      state.chats.unshift({
        ...chat,
        message_count: state.messagesByChatId[chat.id].length
      });
    }

    sortChatsInPlace();
    setActiveChatId(chat.id);
    renderChatList();
    renderActiveChatCard();
    renderMessages();
  });

  window.addEventListener("nova:message-added", (event) => {
    const detail = event.detail || {};
    const chatId = Number(detail.chatId);
    const message = detail.message;

    if(!chatId || !message) return;

    if(!Array.isArray(state.messagesByChatId[chatId])){
      state.messagesByChatId[chatId] = [];
    }

    state.messagesByChatId[chatId].push(message);

    const chatIndex = state.chats.findIndex(chat => Number(chat.id) === chatId);
    if(chatIndex >= 0){
      state.chats[chatIndex] = {
        ...state.chats[chatIndex],
        updated_at: message.created_at || new Date().toISOString(),
        message_count: state.messagesByChatId[chatId].length
      };

      if(
        state.messagesByChatId[chatId].length === 1 &&
        message.role === "user" &&
        (!state.chats[chatIndex].title || state.chats[chatIndex].title === "New chat" || state.chats[chatIndex].title === "Untitled chat")
      ){
        const trimmed = String(message.content || "").trim();
        state.chats[chatIndex].title = trimmed.slice(0, 48) || state.chats[chatIndex].title;
      }
    }

    sortChatsInPlace();
    renderChatList();
    renderActiveChatCard();

    if(Number(state.activeChatId) === chatId){
      renderMessages();
    }
  });
}

async function init(){
  cacheElements();
  renderModelSelect();
  renderAttachedFiles();
  bindEvents();
  autosizeComposer();

  try{
    await loadChats();

    if(state.activeChatId){
      await loadChat(state.activeChatId);
    }else{
      renderChatList();
      renderActiveChatCard();
      renderMessages();
    }
  }catch(error){
    console.error(error);
    renderChatList();
    renderActiveChatCard();
    renderMessages();
  }

  window.NovaApp = {
    state,
    apiFetch,
    getActiveChat,
    getActiveMessages,
    ensureActiveChat,
    createChat,
    loadChat,
    renderChatList,
    renderActiveChatCard,
    renderMessages
  };
}

document.addEventListener("DOMContentLoaded", init);
})();