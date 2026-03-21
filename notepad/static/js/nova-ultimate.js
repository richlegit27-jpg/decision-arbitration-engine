(() => {
"use strict";

window.NovaApp = window.NovaApp || {};
const app = window.NovaApp;

function byId(id){ return document.getElementById(id); }
function getRootState(){ app.state = app.state || {}; app.state.ui = app.state.ui || {sidebarOpen:true}; app.state.chats = app.state.chats || []; app.state.messagesByChatId = app.state.messagesByChatId || {}; return app.state; }
function ensureActiveChat(){ const state = getRootState(); if(state.activeChatId) return state.activeChatId; const newId=`notepad_chat_${Date.now()}`; state.chats.unshift({id:newId,title:"New Chat",created_at:new Date().toISOString()}); state.activeChatId=newId; state.messagesByChatId[newId]=[]; return newId; }
function getActiveChatId(){ return getRootState().activeChatId||null; }
function setMessagesForChat(chatId,messages){ const state=getRootState(); state.messagesByChatId[chatId]=messages; renderMessages(messages); }

function getChatContainer(){ return byId("chatMessages"); }
function createMessageBubble(msg){
  if(!msg) return null;
  const bubble=document.createElement("div");
  bubble.className=`message-bubble ${msg.role||"assistant"} new`;
  if(msg.content){ const div=document.createElement("div"); div.className="message-text"; div.textContent=msg.content; bubble.appendChild(div); }
  if(msg.image_base64){ const img=document.createElement("img"); img.src=`data:image/png;base64,${msg.image_base64}`; img.className="message-image"; img.alt="Generated image"; bubble.appendChild(img); }
  if(msg.video_base64){ const vid=document.createElement("video"); vid.src=`data:video/mp4;base64,${msg.video_base64}`; vid.controls=true; vid.className="message-video"; bubble.appendChild(vid); }
  return bubble;
}
function renderMessage(msg){ const container=getChatContainer(); if(!container) return; const bubble=createMessageBubble(msg); if(!bubble) return; container.appendChild(bubble); container.scrollTop=container.scrollHeight; }
function renderMessages(messages){ const container=getChatContainer(); if(!container) return; container.innerHTML=""; messages.forEach(renderMessage); }

// Composer + send
const input=byId("messageInput"); const sendBtn=byId("sendBtn");
if(sendBtn && input){ sendBtn.addEventListener("click",()=>{ const text=input.value.trim(); if(!text) return; const chatId=ensureActiveChat(); const state=getRootState(); state.messagesByChatId[chatId].push({role:"user",content:text,id:`msg_${Date.now()}`}); renderMessages(state.messagesByChatId[chatId]); input.value=""; });
input.addEventListener("keydown",(e)=>{ if(e.key==="Enter"&&!e.shiftKey){ e.preventDefault(); sendBtn.click(); } }); }

// Sidebar toggle
const sidebarBtn=byId("sidebarToggleBtn"); if(sidebarBtn){ sidebarBtn.addEventListener("click",()=>{ const s=byId("sidebar"); if(!s) return; s.classList.toggle("closed"); s.style.transition="transform 0.25s ease"; getRootState().ui.sidebarOpen=!s.classList.contains("closed"); }); }

// Theme button
const themeBtn=document.createElement("button"); themeBtn.textContent="🌗"; themeBtn.style.marginTop="8px";
themeBtn.addEventListener("click",()=>{ const root=document.documentElement; const next=root.getAttribute("data-theme")==="dark"?"light":"dark"; root.setAttribute("data-theme",next); try{ localStorage.setItem("nova_theme",next);}catch{} });
if(byId("themeContainer")) byId("themeContainer").appendChild(themeBtn);

// Starter chat with media
const starterId=ensureActiveChat();
setMessagesForChat(starterId,[
  {role:"user",content:"Hello Nova!"},
  {role:"assistant",content:"All features loaded and ready for testing."}
]);

})();