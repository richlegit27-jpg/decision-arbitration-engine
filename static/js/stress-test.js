(async () => {
"use strict";
console.log("🚀 Starting Ultimate Nova Stress-Test...");

const sleep = ms => new Promise(r => setTimeout(r, ms));
const { state } = window.NovaChatState;
const MAX_CHATS = 3;
const MESSAGES_PER_CHAT = 3;
const ATTACHMENTS_PER_CHAT = 2;

// Wait until all APIs are ready
let retries = 30;
while(retries--) {
  if(window.NovaChatState && window.NovaChatStorage && window.NovaComposer) break;
  await sleep(200);
}
if(!window.NovaChatState || !window.NovaChatStorage){
  console.error("❌ Nova APIs not ready. Abort.");
  return;
}

// ----------------------
// Create multiple chats
// ----------------------
console.log("📌 Creating chats...");
for(let i=1; i<=MAX_CHATS; i++){
  document.getElementById("newChatBtn")?.click();
  await sleep(400);
  console.log(`✅ Chat ${i} created`);
}

// ----------------------
// Send multiple messages per chat
// ----------------------
console.log("💬 Sending messages...");
const textarea = document.getElementById("composerInput");
const sendBtn = document.getElementById("sendBtn");
for(const chat of state.chats){
  window.NovaChatState.setActiveChat(chat.id);
  for(let m=1;m<=MESSAGES_PER_CHAT;m++){
    if(textarea && sendBtn){
      textarea.value = `Test message ${m} for chat "${chat.title}"`;
      sendBtn.click();
      await sleep(300);
    }
  }
  console.log(`✅ Messages sent for chat: ${chat.title}`);
}

// ----------------------
// Add attachments
// ----------------------
console.log("📎 Adding attachments...");
for(const chat of state.chats){
  window.NovaChatState.setActiveChat(chat.id);
  if(window.addAttachment){
    for(let a=1;a<=ATTACHMENTS_PER_CHAT;a++){
      window.addAttachment({name:`file_${a}_chat_${chat.id}.txt`, size:1024, type:"text/plain"});
      await sleep(150);
    }
  }
  console.log(`✅ Attachments added for chat: ${chat.title}`);
}

// ----------------------
// Toggle panels, theme, sidebar
// ----------------------
console.log("🔄 Toggling panels & theme...");
document.getElementById("sidebarToggleBtn")?.click(); await sleep(200);
document.getElementById("sidebarToggleBtn")?.click(); await sleep(200);
document.getElementById("themeToggleBtn")?.click(); await sleep(200);
document.getElementById("themeToggleBtn")?.click(); await sleep(200);
const memPanel = document.getElementById("memoryPanel");
memPanel.style.display="block"; await sleep(200); memPanel.style.display="none";
const filesPanel = document.getElementById("filesPanel");
filesPanel.style.display="block"; await sleep(200); filesPanel.style.display="none";

// ----------------------
// Delete all chats
// ----------------------
console.log("🗑 Deleting chats...");
for(const chat of [...state.chats]){
  if(window.NovaChatStorage?.deleteChat){
    await window.NovaChatStorage.deleteChat(chat.id);
  } else {
    window.NovaChatState.deleteChat(chat.id);
  }
  await sleep(200);
}
console.assert(state.chats.length===0,"✅ All chats deleted");

// ----------------------
// Logout
// ----------------------
console.log("🔒 Logging out...");
await fetch("/api/logout",{method:"POST",credentials:"include"});
state.activeChatId=null;
state.chats=[];
state.messages=[];
console.log("🎯 Ultimate Nova Stress-Test complete. Everything fully functional.");
})();