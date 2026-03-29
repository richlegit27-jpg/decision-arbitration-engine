(() => {
"use strict";

const bootstrap = window.NOVA_BOOTSTRAP || {};
const chatStateApi = window.NovaChatState || null;
const chatStorageApi = window.NovaChatStorage || null;

if(!chatStateApi) throw new Error("Nova requires window.NovaChatState");

const el = {
  chatList: document.getElementById("chatList"),
  newChatBtn: document.getElementById("newChatBtn"),
  composerForm: document.getElementById("composerForm"),
  composerInput: document.getElementById("composerInput"),
  sendBtn: document.getElementById("sendBtn"),
  attachBtn: document.getElementById("attachBtn"),
  imageBtn: document.getElementById("imageBtn"),
  voiceBtn: document.getElementById("voiceBtn"),
  pendingAttachments: document.getElementById("pendingAttachments"),
  memoryPanel: document.getElementById("memoryPanel"),
  memoryList: document.getElementById("memoryList"),
  deleteAllMemoryBtn: document.getElementById("deleteAllMemoryBtn"),
  closeMemoryPanelBtn: document.getElementById("closeMemoryPanelBtn"),
  filesPanel: document.getElementById("filesPanel"),
  filesList: document.getElementById("filesList"),
  uploadedFilesList: document.getElementById("uploadedFilesList"),
  clearFilesBtn: document.getElementById("clearFilesBtn"),
  closeFilesPanelBtn: document.getElementById("closeFilesPanelBtn"),
  themeToggleBtn: document.getElementById("themeToggleBtn"),
  sidebarToggleBtn: document.getElementById("sidebarToggleBtn"),
  logoutBtn: document.getElementById("logoutBtn")
};

let createInFlight = false;

// ---------------- Chat List ----------------
function renderChatList(){
  el.chatList.innerHTML = "";
  chatStateApi.state.chats.forEach(chat => {
    const li = document.createElement("li");
    li.className = "chat-item";
    li.textContent = chat.title;
    li.dataset.chatId = chat.id;
    li.onclick = () => setActiveChat(chat.id);
    const del = document.createElement("button");
    del.className = "chat-delete-btn";
    del.textContent = "✕";
    del.onclick = e => { e.stopPropagation(); deleteChat(chat.id); };
    li.appendChild(del);
    el.chatList.appendChild(li);
  });
}

async function openNewChat(){
  if(createInFlight) return;
  createInFlight = true;
  el.newChatBtn.disabled = true;
  el.newChatBtn.textContent = "Creating...";
  try {
    if(!chatStorageApi?.createAndSaveChat) throw new Error("NovaChatStorage not available");
    const chat = await chatStorageApi.createAndSaveChat("New Chat");
    if(chat) renderChatList();
  } catch(e){ console.error(e); alert(e.message); }
  finally{ createInFlight=false; el.newChatBtn.disabled=false; el.newChatBtn.textContent="+ New Chat"; }
}

function setActiveChat(chatId){ chatStateApi.setActiveChat(chatId); renderChatList(); }
function deleteChat(chatId){ if(chatStorageApi?.deleteChat){ chatStorageApi.deleteChat(chatId).then(renderChatList); } else { chatStateApi.deleteChat(chatId); renderChatList(); } }

// ---------------- Composer ----------------
if(el.composerForm){
  el.composerForm.addEventListener("submit", e=>{
    e.preventDefault();
    const text=el.composerInput.value.trim();
    if(!text) return;
    chatStateApi.state.messages.push({id:chatStateApi.generateId(),content:text,role:"user",created_at:chatStateApi.nowIso()});
    el.composerInput.value="";
    window.dispatchEvent(new CustomEvent("nova:messages-changed"));
  });
}

function addAttachment(file){
  chatStateApi.state.pendingAttachments = chatStateApi.state.pendingAttachments||[];
  chatStateApi.state.pendingAttachments.push(file);
  renderAttachments();
}
function renderAttachments(){
  el.pendingAttachments.innerHTML="";
  chatStateApi.state.pendingAttachments.forEach(att=>{
    const div=document.createElement("div");
    div.textContent=att.name||"Attachment";
    el.pendingAttachments.appendChild(div);
  });
}
if(el.attachBtn) el.attachBtn.onclick=()=>addAttachment({name:"File.txt",size:1024});
if(el.imageBtn) el.imageBtn.onclick=()=>addAttachment({name:"Image.png",size:1024});
if(el.voiceBtn) el.voiceBtn.onclick=()=>addAttachment({name:"Voice.mp3",size:1024});

// ---------------- Memory Panel ----------------
if(el.closeMemoryPanelBtn) el.closeMemoryPanelBtn.onclick=()=>el.memoryPanel.style.display="none";
if(el.deleteAllMemoryBtn) el.deleteAllMemoryBtn.onclick=()=>{ chatStateApi.state.memoryItems=[]; el.memoryList.innerHTML=""; };
function renderMemory(){
  el.memoryList.innerHTML="";
  chatStateApi.state.memoryItems.forEach(mem=>{
    const div=document.createElement("div"); div.textContent=mem.text; el.memoryList.appendChild(div);
  });
}

// ---------------- Files Panel ----------------
if(el.closeFilesPanelBtn) el.closeFilesPanelBtn.onclick=()=>el.filesPanel.style.display="none";
if(el.clearFilesBtn) el.clearFilesBtn.onclick=()=>{
  chatStateApi.state.pendingAttachments=[];
  el.filesList.innerHTML="";
  el.uploadedFilesList.innerHTML="";
};

// ---------------- Footer ----------------
if(el.themeToggleBtn) el.themeToggleBtn.onclick=()=>document.body.classList.toggle("chat-bg-dark");
if(el.sidebarToggleBtn) el.sidebarToggleBtn.onclick=()=>document.body.classList.toggle("sidebar-open");
if(el.logoutBtn) el.logoutBtn.onclick=async ()=>{
  await fetch("/api/logout",{method:"POST",credentials:"include"});
  chatStateApi.state.chats=[]; chatStateApi.state.activeChatId=null; chatStateApi.state.messages=[];
  renderChatList();
};

// ---------------- Init ----------------
function init(){
  renderChatList();
  renderAttachments();
  renderMemory();
}
window.addEventListener("DOMContentLoaded",init);
window.addEventListener("nova:chat-changed",()=>{ renderChatList(); });
window.addEventListener("nova:messages-changed",()=>{ renderAttachments(); });
})();