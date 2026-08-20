(() => {
"use strict"

// ----------------------------
// Element references
// ----------------------------
const el = {
  newChatBtn: document.getElementById("btnNewChat"),
  chatList: document.getElementById("chatList")
};

let createInFlight = false;

// ----------------------------
// Render chat list
// ----------------------------
function renderChatList(){
  if(!el.chatList) return;
  el.chatList.innerHTML = "";

  const chats = window.NovaChatState?.state?.chats || [];
  if(!chats.length){
    el.chatList.innerHTML = "<div class='chat-list-empty'>No chats yet</div>";
    return;
  }

  chats.forEach(chat => {
    const li = document.createElement("div");
    li.className = "chat-list-item";
    li.textContent = chat.title;
    li.dataset.chatId = chat.id;

li.onclick = async () => {
  window.NovaChatState.setActiveChat(chat.id);

  renderChatList();

  if(window.NovaChatApp?.loadActiveChatMessages){
    await window.NovaChatApp.loadActiveChatMessages();
  }
};

    const del = document.createElement("button");
    del.textContent = "âœ•";
    del.style.float = "right";
    del.onclick = e => {
      e.stopPropagation();
      window.NovaChatStorage?.deleteChat(chat.id);
      renderChatList();
    };

    li.appendChild(del);
    el.chatList.appendChild(li);
  });
}

// ----------------------------
// Open new chat
// ----------------------------
async function openNewChat(){
  if(createInFlight) return;
  createInFlight = true;

  if(el.newChatBtn){
    el.newChatBtn.disabled = true;
    el.newChatBtn.textContent = "Creating...";
  }

  try{
    if(!window.NovaChatStorage || !window.NovaChatStorage.createAndSaveChat){
      throw new Error("NovaChatStorage.createAndSaveChat is not available");
    }

    const chat = await window.NovaChatStorage.createAndSaveChat("New Chat");
    if(chat){
      renderChatList();
    }

    if(window.innerWidth <= 980){
      document.body.classList.remove("sidebar-open");
    }

  }catch(error){
    console.error("New Chat error:", error);
    alert(error?.message || "Could not create chat.");
  }finally{
    createInFlight = false;
    if(el.newChatBtn){
      el.newChatBtn.disabled = false;
      el.newChatBtn.textContent = "+ New Chat";
    }
  }
}

// ----------------------------
// Init
// ----------------------------
function init(){
  renderChatList();

  if(el.newChatBtn){
    el.newChatBtn.addEventListener("click", openNewChat);
  }
}

// Run
if(document.readyState === "loading"){
  document.addEventListener("DOMContentLoaded", init);
}else{
  init();
}

async function loadChats(){

  const response = await fetch("/api/sessions");

  if(!response.ok){
    throw new Error("Failed to load chats");
  }

  const data = await response.json();

  const chats = Array.isArray(data.items)
    ? data.items
    : [];

  const state = window.NovaChatState?.state;

  if(!state){
    throw new Error("NovaChatState missing");
  }

  state.chats = chats;

  const activeChat = chats.find(
    chat => String(chat.id) === String(state.activeChatId)
  );

  const hasActiveChat = !!activeChat;

const activeHasMessages =
    activeChat &&
    (
      (Array.isArray(activeChat.messages) && activeChat.messages.length > 0) ||
      Number(activeChat.message_count || 0) > 0
    );

const chatWithMessages = chats.find(
  chat =>
    (Array.isArray(chat.messages) && chat.messages.length > 0) ||
    Number(chat.message_count || 0) > 0
);

  if(!hasActiveChat){
    state.activeChatId = chatWithMessages?.id || chats[0]?.id || null;
  }
  else if(!activeHasMessages && chatWithMessages){
    state.activeChatId = chatWithMessages.id;
  }

  renderChatList();

  return chats;
}

async function loadMessages(chatId){

  if(!chatId){
    return [];
  }

  const response = await fetch(
    `/api/sessions/${encodeURIComponent(chatId)}`
  );

  if(!response.ok){
    return [];
  }

  const data = await response.json();

  if(Array.isArray(data.messages)){
    return data.messages;
  }

  if(data.session && Array.isArray(data.session.messages)){
    return data.session.messages;
  }

  return [];
}


window.NovaChatStorage = {
  renderChatList,
  openNewChat,
  loadChats,
  loadMessages
};

})();