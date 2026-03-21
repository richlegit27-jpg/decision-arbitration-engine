(() => {
"use strict";

// --- ELEMENT REFS ---
const memoryPanel      = document.getElementById("memoryPanel");
const memoryBtn        = document.getElementById("btnOpenMemory");
const closeMemoryBtn   = document.getElementById("closeMemoryPanelBtn");
const deleteAllMemoryBtn = document.getElementById("deleteAllMemoryBtn");

const sendBtn          = document.getElementById("sendBtn");
const messageInput     = document.getElementById("messageInput");
const newChatBtn       = document.getElementById("btnNewChat");
const attachBtn        = document.getElementById("attachBtn");
const voiceBtn         = document.getElementById("voiceBtn");
const changeBgBtn      = document.getElementById("changeBgBtn");
const themeBtn         = document.getElementById("themeBtn");
const fileInput        = document.getElementById("fileInput");

const chatMessages     = document.getElementById("chatMessages");

// --- BUTTON EVENTS ---

// Memory panel toggle
memoryBtn.addEventListener("click", () => memoryPanel.classList.toggle("open"));
closeMemoryBtn.addEventListener("click", () => memoryPanel.classList.remove("open"));
deleteAllMemoryBtn.addEventListener("click", () => {
  memoryList.innerHTML = "";
  updateMemoryStats();
});

// Send message
sendBtn.addEventListener("click", sendMessage);
messageInput.addEventListener("keydown", e => {
  if(e.key === "Enter" && !e.shiftKey){
    e.preventDefault();
    sendBtn.click();
  }
});

// New Chat
newChatBtn.addEventListener("click", () => {
  chatMessages.innerHTML = "";
  resetNovaTips();
});

// Attach button
attachBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", async e => {
  const file = e.target.files[0];
  if(!file) return;
  appendMessage("[File selected]", file.name);
});

// Voice button
voiceBtn.addEventListener("click", async () => {
  if(!navigator.mediaDevices?.getUserMedia){
    alert("Voice input not supported");
    return;
  }
  const stream = await navigator.mediaDevices.getUserMedia({audio:true});
  const recorder = new MediaRecorder(stream);
  let chunks = [];

  recorder.ondataavailable = e => chunks.push(e.data);
  recorder.onstop = async () => {
    appendMessage("[Voice recorded]", "");
  };

  recorder.start();
  setTimeout(()=>recorder.stop(),5000); // record 5s
});

// Background / Theme toggle
changeBgBtn.addEventListener("click", () => {
  document.body.classList.toggle("chat-bg-dark");
});
themeBtn.addEventListener("click", () => {
  document.body.classList.toggle("chat-bg-dark");
});

// --- HELPER FUNCTIONS ---

function sendMessage(){
  const text = messageInput.value.trim();
  if(!text) return;
  appendMessage("You", text);
  messageInput.value = "";
  scrollToBottom();
  updateCards();
}

function appendMessage(sender, text){
  const msg = document.createElement("div");
  msg.className = "chat-message";
  msg.innerHTML = `<strong>${sender}:</strong> ${text}`;
  chatMessages.appendChild(msg);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function scrollToBottom(){
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// --- CARDS ---
const novaTipsCard     = document.getElementById("novaTipsCard");
const activeChatCard   = document.getElementById("activeChatCard");
const memoryStatsCard  = document.getElementById("memoryStatsCard");

function updateCards(){
  novaTipsCard.textContent = "Nova Tips: Stay sharp!";
  activeChatCard.textContent = `Active Chat: ${chatMessages.children.length} messages`;
  updateMemoryStats();
}

function updateMemoryStats(){
  const count = memoryList.children.length;
  memoryStatsCard.textContent = `Memory Stats: ${count} items`;
}

function resetNovaTips(){
  novaTipsCard.textContent = "Nova Tips: Ready for new chat!";
}

// --- INIT ---
updateCards();
})();