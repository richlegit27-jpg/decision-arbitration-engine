(() => {
"use strict";

if(window.__novaUltimateLoaded){ console.warn("Nova Ultimate already loaded."); return; }
window.__novaUltimateLoaded = true;

const app = {
  state: {
    chats: [],
    activeChatId: null,
    memory: [],
    theme: localStorage.getItem("nova_theme")||"dark",
  }
};

// --- DOM refs ---
const sidebar = document.getElementById("sidebar");
const toggleSidebar = document.getElementById("toggleSidebar");
const chatMessages = document.getElementById("chatMessages");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const newChatBtn = document.getElementById("newChatBtn");
const chatTabs = document.getElementById("chatTabs");
const themeToggle = document.getElementById("themeToggle");
const memoryPanel = document.getElementById("memoryPanel");
const memorySearch = document.getElementById("memorySearch");
const memoryList = document.getElementById("memoryList");
const memoryClear = document.getElementById("memoryClear");
const memoryExport = document.getElementById("memoryExport");
const voiceBtn = document.getElementById("voiceBtn");
const attachBtn = document.getElementById("attachBtn");
const fileInput = document.getElementById("fileInput");

// --- Sidebar ---
toggleSidebar.addEventListener("click", ()=>{ sidebar.classList.toggle("collapsed"); });

// --- Theme ---
themeToggle.addEventListener("click", ()=>{
  app.state.theme = app.state.theme==="dark"?"light":"dark";
  document.documentElement.setAttribute("data-theme", app.state.theme);
  localStorage.setItem("nova_theme", app.state.theme);
});

// --- Chats ---
function createChat(id){ app.state.chats.push({id,messages:[]}); app.state.activeChatId=id; renderChatTabs(); renderMessages(); }
function renderChatTabs(){
  chatTabs.innerHTML="";
  app.state.chats.forEach(c=>{
    const li=document.createElement("li");
    li.textContent=`Chat ${c.id}`;
    li.className=c.id===app.state.activeChatId?"active":"";
    li.onclick=()=>{ app.state.activeChatId=c.id; renderMessages(); renderChatTabs(); };
    chatTabs.appendChild(li);
  });
}
newChatBtn.addEventListener("click",()=>{ createChat(app.state.chats.length+1); });

// --- Messages ---
sendBtn.addEventListener("click", sendMessage);
function sendMessage(){
  const txt = messageInput.value.trim(); if(!txt) return;
  appendMessage("user", txt);
  messageInput.value="";
  // simulate AI response
  appendMessage("assistant","Typing response..."); 
  const msgEl = chatMessages.lastChild;
  let i=0;
  const text="Hello! This is Nova Ultimate response.";
  const interval = setInterval(()=>{
    msgEl.textContent=text.slice(0,i+1);
    i++; if(i>=text.length) clearInterval(interval);
  },30);
}
function appendMessage(role,text){
  const div = document.createElement("div");
  div.className="message "+role; div.textContent=text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  if(app.state.activeChatId){
    const chat = app.state.chats.find(c=>c.id===app.state.activeChatId);
    chat.messages.push({role,text});
  }
}

// --- Memory ---
function renderMemory(){
  const q = memorySearch.value.toLowerCase();
  memoryList.innerHTML="";
  app.state.memory.filter(m=>m.includes(q)).forEach(m=>{
    const li = document.createElement("li");
    li.textContent=m;
    memoryList.appendChild(li);
  });
}
memorySearch.addEventListener("input", renderMemory);
memoryClear.addEventListener("click", ()=>{ app.state.memory=[]; renderMemory(); });
memoryExport.addEventListener("click", ()=>{
  const blob = new Blob([JSON.stringify(app.state.memory,null,2)],{type:"application/json"});
  const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download="memory.json"; a.click();
});

// --- Voice ---
voiceBtn.addEventListener("click", ()=>{
  if(!window.SpeechRecognition && !window.webkitSpeechRecognition) return alert("No SpeechRecognition");
  const SR = window.SpeechRecognition||window.webkitSpeechRecognition;
  const rec = new SR(); rec.lang="en-US"; rec.start();
  rec.onresult=e=>{ messageInput.value=e.results[0][0].transcript; }; 
});

// --- File Attach ---
attachBtn.addEventListener("click",()=>fileInput.click());
fileInput.addEventListener("change", e=>{
  Array.from(e.target.files).forEach(f=>{
    appendMessage("user","[Attached file: "+f.name+"]");
  });
});
})();