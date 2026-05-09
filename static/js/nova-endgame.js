(() => {
"use strict";

/* ---------------------------------------------------
   Helper functions
--------------------------------------------------- */
function $(id){ return document.getElementById(id); }
function addClass(el, cls){ if(el) el.classList.add(cls); }
function removeClass(el, cls){ if(el) el.classList.remove(cls); }
function toggleClass(el, cls, force){ if(el) el.classList.toggle(cls, force); }
function escapeHtml(value){ return String(value ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;"); }
function nowIso(){ return new Date().toISOString(); }
function makeId(prefix="id"){ return window.crypto?.randomUUID ? `${prefix}_${window.crypto.randomUUID()}` : `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`; }

/* ---------------------------------------------------
   Nova Chat State (local memory)
--------------------------------------------------- */
const STORAGE_KEYS={ACTIVE_CHAT_ID:"nova_active_chat_id",THEME:"nova_theme"};
const state={activeChatId:null,chats:[],messages:[],pendingAttachments:[],memoryItems:[],ui:{sidebarOpen:true,memoryOpen:false,filesOpen:false}};

function createChat(title="New Chat"){
  const id=makeId("chat"); const ts=nowIso();
  const chat={id,title,created_at:ts,updated_at:ts,messages:[]};
  state.chats.unshift(chat); state.activeChatId=id; state.messages=chat.messages; return chat;
}
function getChatById(chatId){ return state.chats.find(c=>c.id===chatId)||null; }
function ensureActiveChat(){ if(state.activeChatId){ const c=getChatById(state.activeChatId); if(c){state.messages=c.messages;return c} } return state.chats.length? (state.activeChatId=state.chats[0].id,state.messages=state.chats[0].messages,state.chats[0]):createChat("New Chat"); }
function setActiveChat(chatId){ const chat=getChatById(chatId); if(!chat) return null; state.activeChatId=chat.id; state.messages=chat.messages; chat.updated_at=nowIso(); return chat; }
function updateActiveChatTitle(title){ const chat=ensureActiveChat(); if(!title?.trim()) return chat; chat.title=title.trim(); chat.updated_at=nowIso(); return chat; }
function deleteChat(chatId){ const index=state.chats.findIndex(c=>c.id===chatId); if(index===-1) return false; state.chats.splice(index,1); if(state.activeChatId===chatId){ state.activeChatId=null; state.messages=[]; ensureActiveChat() } return true; }
function getActiveChat(){ return ensureActiveChat(); }

window.NovaChatState={state,STORAGE_KEYS,makeId,nowIso,createChat,getChatById,setActiveChat,updateActiveChatTitle,deleteChat,getActiveChat};

/* ---------------------------------------------------
   Attachments Service
--------------------------------------------------- */
const NovaAttachmentsService=(function(){
  const state=window.NovaChatState.state;
  function ensurePending(){ if(!Array.isArray(state.pendingAttachments)) state.pendingAttachments=[]; return state.pendingAttachments; }
  function makeAttachment(file){ return {id:makeId("attachment"),name:file.name,type:file.type,size:file.size,url:"",content:"",kind:"file"}; }
  async function addFiles(fileList){ const arr=Array.from(fileList||[]).filter(Boolean); const items=[]; for(const f of arr){ items.push(makeAttachment(f)) } state.pendingAttachments=[...ensurePending(),...items]; window.dispatchEvent(new CustomEvent("nova:attachments-changed",{detail:state.pendingAttachments})); return items; }
  function removeAttachmentById(id){ state.pendingAttachments=ensurePending().filter(a=>String(a.id)!==String(id)); return state.pendingAttachments; }
  function clearAttachments(){ state.pendingAttachments=[]; return state.pendingAttachments; }
  return {addFiles,removeAttachmentById,clearAttachments,getAttachments:ensurePending};
})();

/* ---------------------------------------------------
   Composer (messages + attachments)
--------------------------------------------------- */
const NovaComposer=(function(){
  const bootstrap=window.NOVA_BOOTSTRAP||{}; const chatUrl=bootstrap.chatUrl||"/api/chat";
  const state=window.NovaChatState.state;
  const el={composerInput:$("composerInput"),sendBtn:$("sendBtn"),attachBtn:$("attachBtn"),pendingAttachments:$("pendingAttachments"),voiceBtn:$("voiceBtn"),imageBtn:$("imageBtn")};
  function ensureMessages(){ if(!Array.isArray(state.messages)) state.messages=[]; return state.messages; }
  function ensurePendingAttachments(){ if(!Array.isArray(state.pendingAttachments)) state.pendingAttachments=[]; return state.pendingAttachments; }
  function pushMessage(m){ ensureMessages().push(m); window.dispatchEvent(new CustomEvent("nova:messages-changed",{detail:state.messages})) }
  function appendUserMessage(text,attachments=[]){ const msg={id:makeId("user"),role:"user",content:String(text||""),created_at:nowIso(),attachments:attachments||[]}; pushMessage(msg); return msg; }
  function appendThinkingMessage(model){ const msg={id:makeId("assistant"),role:"assistant",content:`Thinking…${model?` (${model})`:""}`,created_at:nowIso(),isThinking:true}; pushMessage(msg); return msg; }
  async function sendMessage(){ const raw=el.composerInput?.value||""; const text=raw.trim(); const attachments=ensurePendingAttachments(); if(!text&&!attachments.length) return; appendUserMessage(text||"[Attachment]",attachments); if(el.composerInput) el.composerInput.value=""; state.pendingAttachments=[]; const thinking=appendThinkingMessage(""); try{ const resp=await fetch(chatUrl,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json","Accept":"application/json"},body:JSON.stringify({chat_id:state.activeChatId,message:text,model:"",attachments})}); const data=await resp.json().catch(()=>({})); if(!resp.ok) throw new Error(data?.error||data?.detail||`HTTP ${resp.status}`); }catch(e){ console.error(e); } }
  return {sendMessage};
})();

/* ---------------------------------------------------
   Endgame UI Polish
--------------------------------------------------- */
(() => {
  const memoryPanel=$("memoryPanel"),filesPanel=$("filesPanel"),memoryBackdrop=$("memoryBackdrop");
  function openPanel(panel){ if(panel){panel.hidden=false;addClass(document.body,"panel-open")} if(memoryBackdrop) memoryBackdrop.hidden=false; }
  function closePanel(panel){ if(panel){panel.hidden=true;} if(memoryBackdrop) memoryBackdrop.hidden=true; removeClass(document.body,"panel-open"); }
  if(memoryBackdrop) memoryBackdrop.addEventListener("click",()=>{ closePanel(memoryPanel); closePanel(filesPanel); });
  const btnMemory=$("btnOpenMemory"); if(btnMemory) btnMemory.addEventListener("click",()=>openPanel(memoryPanel));
  const btnFiles=$("btnOpenFiles"); if(btnFiles) btnFiles.addEventListener("click",()=>openPanel(filesPanel));
  const btnCloseMemory=$("btnCloseMemory"); if(btnCloseMemory) btnCloseMemory.addEventListener("click",()=>closePanel(memoryPanel));
  window.addEventListener("DOMContentLoaded",()=>{ const composerInput=$("composerInput"); if(composerInput) composerInput.focus(); });
  document.addEventListener("keydown",(e)=>{ if(e.key==="Escape"){ closePanel(memoryPanel); closePanel(filesPanel); } });
  addClass(document.body,"endgame-ready");
})();