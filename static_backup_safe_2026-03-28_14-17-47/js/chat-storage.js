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

    li.onclick = () => {
      window.NovaChatState.setActiveChat(chat.id);
      renderChatList();
    };

    const del = document.createElement("button");
    del.textContent = "✕";
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

})();