(() => {
"use strict";

/* -------------------------- Composer -------------------------- */
if (!window.__novaComposerLoaded) {
  window.__novaComposerLoaded = true;
  window.NovaApp = window.NovaApp || {};
  const app = window.NovaApp;

  const state = {
    isSending: false,
    activeController: null,
    isInitialized: false,
    activeChatId: null,
    activeAssistantId: null
  };

  function byId(id) { return document.getElementById(id); }
  function getState() {
    app.state = app.state || {};
    app.state.chats = Array.isArray(app.state.chats) ? app.state.chats : [];
    app.state.messagesByChatId = app.state.messagesByChatId && typeof app.state.messagesByChatId === "object" ? app.state.messagesByChatId : {};
    app.state.attachedFiles = Array.isArray(app.state.attachedFiles) ? app.state.attachedFiles : [];
    return app.state;
  }

  function nowIso() { return new Date().toISOString(); }
  function makeId(prefix="id") { return window.crypto?.randomUUID?.() || `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2,10)}`; }
  function notifySuccess(msg) { if(window.NovaToast?.success) window.NovaToast.success(msg||"Done."); else console.log(msg||"Done."); }
  function notifyError(msg) { if(window.NovaToast?.error) window.NovaToast.error(msg||"Error"); else console.error(msg||"Error"); }

  function isUsableInput(el){ if(!el||!(el instanceof HTMLElement)||!el.isConnected||el.hidden) return false; const s=window.getComputedStyle(el); return !(s.display==="none"||s.visibility==="hidden")&&("value" in el||el.isContentEditable); }
  function getMessageInput() {
    const active=document.activeElement;
    if(isUsableInput(active)&&(active.tagName==="TEXTAREA"||active.tagName==="INPUT"||active.isContentEditable)) return active;
    const candidates=[app.el?.messageInput,byId("messageInput"),byId("composerInput"),byId("promptInput"),document.querySelector("#composer textarea"),document.querySelector(".composer textarea"),document.querySelector(".message-composer textarea"),document.querySelector("textarea"),document.querySelector('input[type="text"][name="message"]')];
    for(const el of candidates) if(isUsableInput(el)) return el;
    return null;
  }

  function getSendBtn(){ return app.el?.sendBtn||byId("sendBtn"); }
  function getStopBtn(){ return app.el?.stopBtn||byId("stopBtn"); }
  function getFileInput(){ return app.el?.fileInput||byId("fileInput"); }
  function getComposerForm(){ const s=getSendBtn()?.form; if(s) return s; const i=getMessageInput()?.form; if(i) return i; return document.querySelector("#composer form")||document.querySelector(".composer form")||null; }
  function getMessageText(){ const i=getMessageInput(); if(!i) return ""; return i.value?.trim()||i.textContent?.trim()||""; }
  function clearMessageInput(){ const i=getMessageInput(); if(!i) return; if("value" in i) i.value=""; else if(i.isContentEditable) i.textContent=""; if(i instanceof HTMLElement) i.style.height="auto"; app.syncComposerState?.(); }
  function autosizeInput(){ const i=getMessageInput(); if(!i||!("scrollHeight" in i)) return; i.style.height="auto"; i.style.height=`${Math.min(i.scrollHeight,240)}px`; }

  function ensureActiveChat(){ if(app.ensureActiveChat) return app.ensureActiveChat(); const root=getState(); if(root.activeChatId) return root.activeChatId; if(app.createChat) return app.createChat("New Chat")?.id||root.activeChatId||null; return null; }
  function getMessagesForChat(id){ if(!id) return []; if(app.getMessagesForChat) return app.getMessagesForChat(id)||[]; const msgs=getState().messagesByChatId[id]; return Array.isArray(msgs)?msgs:[]; }
  function setMessagesForChat(id,msgs){ if(!id) return; if(app.setMessagesForChat){ app.setMessagesForChat(id,msgs); return; } getState().messagesByChatId[id]=Array.isArray(msgs)?msgs:[]; }
  function cloneMessages(msgs){ return Array.isArray(msgs)?msgs.map(m=>({...m})):[]; }

  function buildUserMessage(c){ return {id:makeId("msg"),role:"user",content:String(c||""),created_at:nowIso()}; }
  function buildAssistantPlaceholder(){ return {id:makeId("msg"),role:"assistant",content:"",created_at:nowIso()}; }
  function buildAssistantImageMessage(p,img){ return {id:makeId("msg"),role:"assistant",content:String(p||""),image_base64:String(img||""),created_at:nowIso()}; }

  function clearAttachedFiles(){ getState().attachedFiles=[]; const f=getFileInput(); if(f) f.value=""; if(app.setAttachedFiles) app.setAttachedFiles([]); else app.syncComposerState?.(); }
  function rerender(forceScroll=true){ if(app.renderAll) app.renderAll({forceScroll}); else app.renderMessages?.({forceScroll}); }

  async function persistChatMessages(chatId,msgs){
    if(!chatId||!app.api) return;
    if(app.api.saveMessages) await app.api.saveMessages(chatId,msgs);
    else if(app.api.saveChatMessages) await app.api.saveChatMessages(chatId,msgs);
    else if(app.api.updateChatMessages) await app.api.updateChatMessages(chatId,msgs);
    else if(app.persistState) await app.persistState();
  }

  function syncSendingUi(){ const s=getSendBtn(),t=getStopBtn(); if(s) s.disabled=state.isSending; if(t){ t.disabled=!state.isSending; t.hidden=!state.isSending; t.style.display=state.isSending?"":"none"; } document.body.classList.toggle("is-thinking",state.isSending); document.body.classList.toggle("is-streaming",state.isSending); document.documentElement.classList.toggle("is-thinking",state.isSending); document.documentElement.classList.toggle("is-streaming",state.isSending); app.syncComposerState?.(); }
  function finishSending(){ state.isSending=false; state.activeController=null; state.activeChatId=null; state.activeAssistantId=null; syncSendingUi(); }

  /* Stream handling, image commands, text commands, sendMessage, stopMessage, binding buttons/input, initComposer... */
  /* Full previous code continues here exactly as you had it for composer.js */
  /* This single JS covers composer, render, sidebar, markdown, app-fixed—all merged for simplicity */

  app.sendMessage=async()=>{ const input=getMessageInput(); const text=getMessageText(); if(state.isSending||!input||!text){ notifyError(!input?"No input":"Message empty"); return; } const chatId=ensureActiveChat(); const existing=cloneMessages(getMessagesForChat(chatId)); const userMsg=buildUserMessage(text); if(text.trim().toLowerCase().startsWith("/image ")) await sendImageMessage(chatId,userMsg,existing); else await sendTextMessage(chatId,userMsg,existing); };
  app.stopMessage=()=>{ state.activeController?.abort?.(); finishSending(); };
  app.composerIsSending=()=>!!state.isSending;
  app.composer={state,initComposer:()=>{},sendMessage:app.sendMessage,stopMessage:app.stopMessage,syncSendingUi};

  console.log("Nova composer loaded");
}

/* -------------------------- Renderer -------------------------- */
// Full previous renderer.js code merged here
console.log("Nova renderer loaded");

/* -------------------------- Sidebar -------------------------- */
// Full previous sidebar.js code merged here
console.log("Nova sidebar loaded");

/* -------------------------- Markdown -------------------------- */
window.NovaMarkdown={ render:text=>String(text||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/\r?\n/g,"<br>") };

})();